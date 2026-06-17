"""Async IMAP client using aioimaplib."""

from __future__ import annotations

import asyncio
import email
import hashlib
import logging
import os
import re
import socket
import ssl
from datetime import datetime
from email.header import decode_header
from pathlib import Path
from typing import Any

import aioimaplib
from aioimaplib import IMAP4_SSL

from simple_email_gw.config import EmailAccount
from simple_email_gw.safety.audit import (
  log_attachment_download,
  log_auth_attempt,
  log_email_appended,
)
from simple_email_gw.safety.sanitize import (
  get_append_max_size,
  sanitize_folder_name,
  sanitize_message_id_numeric,
  validate_append_flags,
  validate_folder_name,
)

_logger = logging.getLogger(__name__)

# Default workspace for attachment downloads
DEFAULT_WORKSPACE = Path(os.environ.get("EMAIL_WORKSPACE", "/tmp/email_workspace"))

# IMAP search criteria validation
# Single quotes removed - not part of IMAP string syntax (RFC 3501 uses double quotes only)
# Added @ . : % \ for valid IMAP SEARCH syntax (email addresses, dates, flags)
IMAP_CRITERIA_PATTERN = re.compile(r"^[\w\s\(\)\*\<\>\[\]=!\"@\.:%\\-]+$")

# Common IMAP APPEND response codes mapped to generic error messages
_APPEND_ERROR_MESSAGES: dict[str, str] = {
  "[OVERQUOTA]": "Mailbox quota exceeded. Contact administrator.",
  "[NOPERM]": "Permission denied. Check server logs for details.",
  "[TRYCREATE]": "Folder does not exist",
}

# Fallback folder names when the server does not advertise the \Sent special-use flag
SENT_FOLDER_FALLBACKS = ["Sent", "Sent Items", "Sent Messages"]


def _decode_append_error(data: Any) -> str:
  """Extract a sanitized error text from an IMAP APPEND response."""
  if not data or not isinstance(data, list) or len(data) == 0:
    return ""
  first = data[0]
  if isinstance(first, bytes):
    return first.decode(errors="replace")
  if isinstance(first, str):
    return first
  return ""


def _get_append_error_message(error_text: str) -> str | None:
  """Map an IMAP APPEND error text to a generic message if a known code is present."""
  for code, message in _APPEND_ERROR_MESSAGES.items():
    if code in error_text:
      return message
  return None


def _quote_mailbox_name(name: str) -> str:
  """Return an IMAP quoted string for mailbox names that are not atoms.

  RFC 3501 atoms cannot contain spaces, parentheses, braces, wildcards,
  quote/backslash characters, or response specials. Quoting the mailbox name
  ensures the APPEND command is parsed correctly by the server even for
  folder names such as ``Sent Items``.

  Args:
    name: Mailbox name already validated for dangerous characters.

  Returns:
    The original name if it is a valid atom; otherwise a quoted string.
  """
  atom_specials = '(){ %*"\\]'
  if any(ch in name for ch in atom_specials) or any(ord(ch) < 32 for ch in name):
    escaped = name.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'
  return name


class SecurityError(Exception):
  """Raised when a security constraint is violated (e.g., symlink escape)."""

  pass


class IMAPClient:
  """Async IMAP client with connection pooling."""

  def __init__(self, account: EmailAccount) -> None:
    self.account = account
    self._client: IMAP4_SSL | None = None
    self._selected_folder: str | None = None
    self._connect_lock = asyncio.Lock()
    self._operation_lock = asyncio.Lock()
    self._capabilities: set[str] = set()

  async def connect(self) -> IMAP4_SSL:
    """Establish IMAP connection with SSL verification."""
    async with self._connect_lock:
      if self._client is not None:
        return self._client

      try:
        # Create SSL context with certificate verification and TLS 1.2 minimum
        context = ssl.create_default_context()
        context.minimum_version = ssl.TLSVersion.TLSv1_2

        self._client = IMAP4_SSL(
          host=self.account.imap_host,
          port=self.account.imap_port,
          ssl_context=context,
        )

        await self._client.wait_hello_from_server()

        # Authenticate
        if self.account.auth_method == "oauth2" and self.account.oauth2_token:
          token = self.account.oauth2_token.get_secret_value()
          auth_string = f"user={self.account.username}\x01auth=Bearer {token}\x01\x01"
          await self._client.authenticate("XOAUTH2", auth_string)
          log_auth_attempt(self.account.name, True, "oauth2")
        elif self.account.password:
          await self._client.login(
            self.account.username,
            self.account.password.get_secret_value(),
          )
          log_auth_attempt(self.account.name, True, "password")
        else:
          raise ValueError("No credentials available")

      except ValueError as e:
        # Configuration error - missing credentials
        log_auth_attempt(self.account.name, False, self.account.auth_method, str(e))
        raise RuntimeError(f"Configuration error: {e}") from e
      except TimeoutError:
        # Connection timeout (asyncio.TimeoutError is an alias for TimeoutError in 3.11+)
        raise RuntimeError("Connection timed out. Check server availability.") from None
      except ConnectionError as e:
        # Network-level disconnection
        raise RuntimeError(f"Connection lost: {e}") from e
      except ssl.SSLError as e:
        # TLS certificate/validation errors
        raise RuntimeError(f"TLS error: {e}. Check server certificate.") from e
      except aioimaplib.Abort as e:
        # Protocol-level abort (server disconnected, protocol error)
        raise RuntimeError(f"Protocol error: {e}") from e
      except aioimaplib.Error as e:
        # IMAP-specific errors (includes authentication failures)
        log_auth_attempt(self.account.name, False, self.account.auth_method, str(e))
        raise RuntimeError("Authentication failed. Check server logs for details.") from e
      except OSError as e:
        # DNS failures, connection refused, etc.
        if isinstance(e, socket.gaierror):
          raise RuntimeError(f"DNS resolution failed for {self.account.imap_host}") from e
        raise RuntimeError(f"Network error: {e}") from e
      except Exception as e:
        # Unexpected errors - preserve for debugging
        raise RuntimeError(f"An unexpected error occurred: {type(e).__name__}: {e}") from e

      # Query and cache server capabilities
      try:
        response = await self._client.capability()
        if response.result == "OK" and response.lines:
          # Parse capability list: "IMAP4REV1 MOVE UIDPLUS ..."
          caps_str = response.lines[0].decode().upper()
          self._capabilities = set(caps_str.split())
      except Exception:
        # Non-fatal: continue without cached capabilities
        self._capabilities = set()

      return self._client

  async def disconnect(self) -> None:
    """Close IMAP connection."""
    async with self._operation_lock:
      if self._client:
        await self._client.logout()
        self._client = None
        self._selected_folder = None
        self._capabilities = set()

  def has_capability(self, name: str) -> bool:
    """Check if server supports a capability."""
    return name.upper() in self._capabilities

  async def list_folders(self) -> list[dict[str, Any]]:
    """List all folders/mailboxes."""
    async with self._operation_lock:
      client = await self.connect()
      # iCloud requires specific quoting format
      status, data = await client.list('""', '"*"')

      if status != "OK":
        raise RuntimeError(f"Failed to list folders: {status}")

      folders = []
      for item in data:
        if isinstance(item, bytes):
          item = item.decode()
        if not item:
          continue
        # Parse: (flags) "delimiter" "name"
        parts = item.split('"')
        if len(parts) >= 3:
          flags_str = parts[0].strip("() ")
          folders.append(
            {
              "flags": flags_str.split() if flags_str else [],
              "delimiter": parts[1],
              "name": parts[3] if len(parts) > 3 else parts[1],
            }
          )

      return folders

  async def create_folder(self, folder_name: str) -> bool:
    """Create a new folder/mailbox on the IMAP server.

    Args:
      folder_name: Name of the folder to create.

    Returns:
      True if the folder was created successfully.

    Raises:
      ValueError: If folder name is invalid.
      RuntimeError: If the IMAP server rejects the CREATE command.
    """
    # Defense-in-depth: shared validation + existing sanitization
    safe_folder = sanitize_folder_name(validate_folder_name(folder_name))

    async with self._operation_lock:
      client = await self.connect()
      status, data = await client.create(_quote_mailbox_name(safe_folder))

      if status == "OK":
        return True

      if status == "NO":
        error_text = ""
        if data and isinstance(data, list) and len(data) > 0:
          first = data[0]
          if isinstance(first, bytes):
            error_text = first.decode(errors="replace")
          elif isinstance(first, str):
            error_text = first

        _logger.warning("IMAP CREATE failed: %s", error_text)

        if "[ALREADYEXISTS]" in error_text:
          raise RuntimeError("Folder already exists")
        if "[OVERQUOTA]" in error_text or "quota" in error_text.lower():
          raise RuntimeError("Mailbox quota exceeded. Contact administrator.")
        if "[NOPERM]" in error_text:
          raise RuntimeError("Failed to create folder. Check server logs for details.")
        if "Invalid mailbox name" in error_text:
          raise RuntimeError("Invalid folder name")
        raise RuntimeError("Failed to create folder")

      raise RuntimeError("Failed to create folder")

  async def find_sent_folder(self) -> str | None:
    """Return the account's Sent folder name.

    Uses the IMAP \\Sent special-use flag if advertised; otherwise tries
    common local names in a documented, deterministic order.

    Returns:
      Sent folder name, or None if no candidate is found.
    """
    folders = await self.list_folders()
    for folder in folders:
      flags = folder.get("flags", [])
      if any(str(flag).upper() == r"\SENT" for flag in flags):
        return folder["name"]

    names = {folder["name"] for folder in folders}
    for candidate in SENT_FOLDER_FALLBACKS:
      if candidate in names:
        return candidate
    return None

  async def append_message(
    self,
    folder: str,
    message_bytes: bytes,
    flags: list[str] | None = None,
    internal_date: datetime | None = None,
  ) -> dict[str, str]:
    """Append a message to an IMAP folder.

    Args:
      folder: Target folder name (e.g., "Sent").
      message_bytes: RFC822 message as bytes.
      flags: Optional IMAP flags from the allowlist.
      internal_date: Optional timezone-aware datetime for the IMAP internal date.

    Returns:
      Dict with 'status' and 'folder' keys.

    Raises:
      ValueError: If folder name, flags, or message content is invalid.
      RuntimeError: If the IMAP server rejects APPEND.
    """
    if not isinstance(message_bytes, bytes):
      raise ValueError("Message must be provided as bytes")

    # Validate folder name and flags
    safe_folder = sanitize_folder_name(validate_folder_name(folder))
    safe_flags = validate_append_flags(flags)

    # Validate message content
    if b"\x00" in message_bytes:
      raise ValueError("Message contains NUL bytes")
    if len(message_bytes) > get_append_max_size():
      raise ValueError("Message exceeds maximum size")

    # Validate internal date: only timezone-aware datetimes are allowed
    if internal_date is not None:
      if internal_date.tzinfo is None or internal_date.utcoffset() is None:
        raise ValueError("internal_date must be timezone-aware")

    flag_str = f"({' '.join(safe_flags)})" if safe_flags else None
    mailbox_arg = _quote_mailbox_name(safe_folder)

    # Extract audit-log metadata before the IMAP call so failures can be logged
    subject_prefix = ""
    message_id: str | None = None
    try:
      parsed = email.message_from_bytes(message_bytes)
      subject_prefix = parsed.get("Subject", "")[:50]
      message_id = parsed.get("Message-ID", "")
    except Exception:
      pass

    async with self._operation_lock:
      client = await self.connect()
      try:
        status, data = await client.append(
          message_bytes,
          mailbox=mailbox_arg,
          flags=flag_str,
          date=internal_date,
        )
      except Exception as e:
        _logger.warning("IMAP APPEND failed: %s", e)
        log_email_appended(
          account=self.account.name,
          folder=safe_folder,
          success=False,
          message_id=message_id,
          subject_prefix=subject_prefix,
          message_size=len(message_bytes),
          error="Failed to append message",
        )
        raise RuntimeError("Failed to append message. Check server logs for details.") from e

      if status != "OK":
        error_text = _decode_append_error(data)
        _logger.warning("IMAP APPEND failed: %s", error_text)

        mapped_message = _get_append_error_message(error_text)
        if mapped_message is not None:
          log_email_appended(
            account=self.account.name,
            folder=safe_folder,
            success=False,
            message_id=message_id,
            subject_prefix=subject_prefix,
            message_size=len(message_bytes),
            error=mapped_message,
          )
          raise RuntimeError(mapped_message)

        log_email_appended(
          account=self.account.name,
          folder=safe_folder,
          success=False,
          message_id=message_id,
          subject_prefix=subject_prefix,
          message_size=len(message_bytes),
          error="Failed to append message",
        )
        raise RuntimeError("Failed to append message")

    # Audit log the successful append
    log_email_appended(
      account=self.account.name,
      folder=safe_folder,
      success=True,
      message_id=message_id,
      subject_prefix=subject_prefix,
      message_size=len(message_bytes),
    )

    return {"status": "appended", "folder": safe_folder}

  async def select_folder(self, folder: str = "INBOX") -> dict[str, str | int]:
    """Select a folder and return message count."""
    # Sanitize folder name to prevent CRLF injection
    safe_folder = sanitize_folder_name(folder)
    async with self._operation_lock:
      client = await self.connect()
      status, data = await client.select(_quote_mailbox_name(safe_folder))

      if status != "OK":
        raise RuntimeError(f"Failed to select folder {safe_folder}: {status}")

      self._selected_folder = safe_folder
      # Parse EXISTS from response - data contains lines like b'2 EXISTS'
      count = 0
      for item in data:
        if isinstance(item, bytes) and b"EXISTS" in item:
          try:
            count = int(item.split()[0])
          except (ValueError, IndexError):
            pass
          break
      return {"folder": safe_folder, "count": count}

  async def search(
    self,
    folder: str = "INBOX",
    criteria: str = "ALL",
    limit: int = 50,
  ) -> list[str]:
    """Search for messages matching criteria."""
    # Sanitize folder name to prevent CRLF injection
    safe_folder = sanitize_folder_name(folder)
    async with self._operation_lock:
      client = await self.connect()
      status, data = await client.select(_quote_mailbox_name(safe_folder))
      if status != "OK":
        raise RuntimeError(f"Failed to select folder {safe_folder}: {status}")
      self._selected_folder = safe_folder

      # Validate criteria to prevent IMAP injection
      if not IMAP_CRITERIA_PATTERN.match(criteria):
        raise ValueError("Invalid search criteria")

      result = await client.search(criteria)

      if result.result != "OK":
        raise RuntimeError("Search failed")

      # Handle response - may be empty or contain message IDs
      # iCloud returns: b'SEARCH completed (took X ms)' when no messages
      # Standard IMAP returns: b'SEARCH 1 2 3' with message IDs
      if not result.lines or not result.lines[0]:
        return []

      # Check if this is iCloud's "no messages" status response
      line = result.lines[0].decode()
      if line.startswith("SEARCH ") and "completed" in line.lower():
        # No actual message IDs, just a status message
        return []

      # Parse message IDs from standard response
      ids = line.split()
      # Remove 'SEARCH' prefix if present (some servers include it)
      if ids and ids[0].upper() == "SEARCH":
        ids = ids[1:]
      return ids[-limit:] if limit else ids

  async def fetch_message(
    self,
    message_id: str,
    folder: str = "INBOX",
  ) -> dict[str, Any]:
    """Fetch a single message by ID."""
    # Sanitize folder name and validate message ID
    safe_folder = sanitize_folder_name(folder)
    safe_message_id = sanitize_message_id_numeric(message_id)
    async with self._operation_lock:
      client = await self.connect()
      status, data = await client.select(_quote_mailbox_name(safe_folder))
      if status != "OK":
        raise RuntimeError(f"Failed to select folder {safe_folder}: {status}")
      self._selected_folder = safe_folder

      # Fetch headers and body
      status, data = await client.fetch(safe_message_id, "(BODY.PEEK[] FLAGS)")

      if status != "OK":
        raise RuntimeError(f"Failed to fetch message {safe_message_id}: {status}")

      # Parse the response
      # Format: [b'1 FETCH (BODY[] {size}', bytearray(content), b' FLAGS (...)', b'FETCH completed']
      result = {"id": safe_message_id, "folder": safe_folder}

      raw_message = None
      flags = {}
      for item in data:
        if isinstance(item, bytearray):
          raw_message = bytes(item)
        elif isinstance(item, tuple) and len(item) == 2:
          # Alternative format
          raw_message = item[1] if isinstance(item[1], (bytes, bytearray)) else None
        elif b"FLAGS" in item:
          # format: b' FLAGS (...)'
          # TODO: extract more flags?
          flags["Seen"] = b"\\Seen" in item

      if raw_message:
        msg = email.message_from_bytes(raw_message)
        result["subject"] = self._decode_header(msg.get("Subject", ""))
        result["from"] = self._decode_header(msg.get("From", ""))
        result["to"] = self._decode_header(msg.get("To", ""))
        result["date"] = msg.get("Date", "")
        result["body"] = self._get_body(msg)
        result["attachments"] = self._list_attachments(msg)
        result["read"] = flags.get("Seen", False)
        result["message_id"] = msg.get("Message-ID", "")
        result["references"] = msg.get("References", "").split()

      return result

  async def move_message(
    self,
    message_id: str,
    source_folder: str,
    dest_folder: str,
  ) -> bool:
    """Move a message between folders atomically if server supports MOVE.

    Uses RFC 6851 MOVE extension when available for atomic operation.
    Falls back to COPY+STORE+EXPUNGE with documented non-atomic limitation
    for legacy servers that don't support MOVE.
    """
    # Sanitize folder names and validate message ID
    safe_source = sanitize_folder_name(source_folder)
    safe_dest = sanitize_folder_name(dest_folder)
    safe_message_id = sanitize_message_id_numeric(message_id)
    async with self._operation_lock:
      client = await self.connect()
      status, data = await client.select(_quote_mailbox_name(safe_source))
      if status != "OK":
        raise RuntimeError(f"Failed to select folder {safe_source}: {status}")
      self._selected_folder = safe_source

      # Use atomic MOVE if server supports RFC 6851
      if self.has_capability("MOVE"):
        status, _ = await client.move(safe_message_id, _quote_mailbox_name(safe_dest))
        if status != "OK":
          raise RuntimeError(f"Failed to move message: {status}")
        return True

      # Fallback: non-atomic COPY+STORE+EXPUNGE
      # WARNING: Not atomic - message may exist in both folders on failure
      status, _ = await client.copy(safe_message_id, _quote_mailbox_name(safe_dest))
      if status != "OK":
        raise RuntimeError(f"Failed to copy message: {status}")

      # IMAP requires flags to be wrapped in parentheses
      await client.store(safe_message_id, "+FLAGS", "(\\Deleted)")
      await client.expunge()

      return True

  async def delete_message(
    self,
    message_id: str,
    folder: str = "INBOX",
    expunge: bool = True,
  ) -> bool:
    """Delete a message."""
    # Sanitize folder name and validate message ID
    safe_folder = sanitize_folder_name(folder)
    safe_message_id = sanitize_message_id_numeric(message_id)
    async with self._operation_lock:
      client = await self.connect()
      status, data = await client.select(_quote_mailbox_name(safe_folder))
      if status != "OK":
        raise RuntimeError(f"Failed to select folder {safe_folder}: {status}")
      self._selected_folder = safe_folder

      # Mark as deleted - IMAP requires flags in parentheses
      await client.store(safe_message_id, "+FLAGS", "(\\Deleted)")

      if expunge:
        await client.expunge()

      return True

  async def mark_message(
    self,
    message_id: str,
    folder: str,
    flag: str,
    action: str = "add",
  ) -> bool:
    """Add or remove flags from a message."""
    # Sanitize folder name and validate message ID
    safe_folder = sanitize_folder_name(folder)
    safe_message_id = sanitize_message_id_numeric(message_id)
    async with self._operation_lock:
      client = await self.connect()
      status, data = await client.select(_quote_mailbox_name(safe_folder))
      if status != "OK":
        raise RuntimeError(f"Failed to select folder {safe_folder}: {status}")
      self._selected_folder = safe_folder

      flag_action = "+FLAGS" if action == "add" else "-FLAGS"
      # IMAP requires flags to be wrapped in parentheses
      status, _ = await client.store(safe_message_id, flag_action, f"({flag})")

      return status == "OK"

  async def download_attachment(
    self,
    message_id: str,
    folder: str,
    filename: str,
    output_dir: str,
  ) -> str:
    """Download an attachment from a message with workspace confinement.

    Uses post-write verification to detect symlink attacks (TOCTOU race).
    """
    # Import sanitize_filename here to avoid circular imports at module level
    from simple_email_gw.safety.sanitize import sanitize_filename as sanitize_fn

    # Sanitize folder name and validate message ID
    safe_folder = sanitize_folder_name(folder)
    safe_message_id = sanitize_message_id_numeric(message_id)

    # Sanitize filename - remove path separators and check for CRLF
    safe_filename = os.path.basename(filename)
    if not safe_filename or safe_filename in (".", ".."):
      raise ValueError("Invalid filename")
    # Additional CRLF check on the basename
    safe_filename = sanitize_fn(safe_filename)

    # Hash for uniqueness and additional safety
    hashed_prefix = hashlib.sha256(filename.encode()).hexdigest()[:16]
    final_filename = f"{hashed_prefix}_{safe_filename}"

    async with self._operation_lock:
      client = await self.connect()
      status, data = await client.select(_quote_mailbox_name(safe_folder))
      if status != "OK":
        raise RuntimeError(f"Failed to select folder {safe_folder}: {status}")
      self._selected_folder = safe_folder

      status, data = await client.fetch(safe_message_id, "(BODY.PEEK[])")

      if status != "OK":
        raise RuntimeError("Failed to fetch message")

      for item in data:
        if isinstance(item, tuple) and len(item) == 2:
          raw_message = item[1]
          if isinstance(raw_message, bytes):
            msg = email.message_from_bytes(raw_message)
            for part in msg.walk():
              if part.get_filename() == filename:
                payload = part.get_payload(decode=True)
                if payload:
                  # Resolve workspace to real path once
                  real_workspace = os.path.realpath(str(DEFAULT_WORKSPACE))

                  # Ensure workspace exists
                  workspace = Path(real_workspace)
                  workspace.mkdir(parents=True, exist_ok=True)

                  # Create output directory
                  output_path = Path(output_dir)
                  output_path.mkdir(parents=True, exist_ok=True)
                  file_path = output_path / final_filename

                  # Write file
                  with open(file_path, "wb") as f:
                    f.write(payload)

                  # POST-WRITE VERIFICATION: Detect symlink escape
                  real_path = os.path.realpath(file_path)

                  try:
                    Path(real_path).relative_to(real_workspace)
                  except ValueError:
                    # Security violation: clean up and raise
                    try:
                      file_path.unlink()
                    except OSError:
                      pass
                    raise SecurityError("Download escaped workspace confinement") from None

                  log_attachment_download(self.account.name, filename, real_path)
                  return str(real_path)

      raise FileNotFoundError("Attachment not found in message")

  def _decode_header(self, header: str) -> str:
    """Decode MIME header."""
    if not header:
      return ""
    decoded_parts = decode_header(header)
    result = []
    for part, charset in decoded_parts:
      if isinstance(part, bytes):
        result.append(part.decode(charset or "utf-8", errors="replace"))
      else:
        result.append(part)
    return "".join(result)

  def _get_body(self, msg: email.message.Message) -> str:
    """Extract plain text body from message."""
    if msg.is_multipart():
      for part in msg.walk():
        content_type = part.get_content_type()
        if content_type == "text/plain":
          payload = part.get_payload(decode=True)
          if payload:
            return payload.decode("utf-8", errors="replace")
      return ""
    else:
      payload = msg.get_payload(decode=True)
      if payload:
        return payload.decode("utf-8", errors="replace")
      return ""

  def _list_attachments(self, msg: email.message.Message) -> list[str]:
    """List attachment filenames."""
    attachments = []
    for part in msg.walk():
      filename = part.get_filename()
      if filename:
        attachments.append(filename)
    return attachments
