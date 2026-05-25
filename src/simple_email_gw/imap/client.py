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
from email.header import decode_header
from pathlib import Path
from typing import Any

import aioimaplib
from aioimaplib import IMAP4_SSL

from simple_email_gw.config import EmailAccount
from simple_email_gw.safety.audit import log_attachment_download, log_auth_attempt
from simple_email_gw.safety.sanitize import (
  sanitize_folder_name,
  sanitize_message_id_numeric,
  validate_folder_name,
)

_logger = logging.getLogger(__name__)

# Default workspace for attachment downloads
DEFAULT_WORKSPACE = Path(os.environ.get("EMAIL_WORKSPACE", "/tmp/email_workspace"))

# IMAP search criteria validation
# Single quotes removed - not part of IMAP string syntax (RFC 3501 uses double quotes only)
# Added @ . : % \ for valid IMAP SEARCH syntax (email addresses, dates, flags)
IMAP_CRITERIA_PATTERN = re.compile(r"^[\w\s\(\)\*\<\>\[\]=!\"@\.:%\\-]+$")


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
      status, data = await client.create(safe_folder)

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

  async def select_folder(self, folder: str = "INBOX") -> dict[str, str | int]:
    """Select a folder and return message count."""
    # Sanitize folder name to prevent CRLF injection
    safe_folder = sanitize_folder_name(folder)
    async with self._operation_lock:
      client = await self.connect()
      status, data = await client.select(safe_folder)

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
      status, data = await client.select(safe_folder)
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
      status, data = await client.select(safe_folder)
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
      status, data = await client.select(safe_source)
      if status != "OK":
        raise RuntimeError(f"Failed to select folder {safe_source}: {status}")
      self._selected_folder = safe_source

      # Use atomic MOVE if server supports RFC 6851
      if self.has_capability("MOVE"):
        status, _ = await client.move(safe_message_id, safe_dest)
        if status != "OK":
          raise RuntimeError(f"Failed to move message: {status}")
        return True

      # Fallback: non-atomic COPY+STORE+EXPUNGE
      # WARNING: Not atomic - message may exist in both folders on failure
      status, _ = await client.copy(safe_message_id, safe_dest)
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
      status, data = await client.select(safe_folder)
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
      status, data = await client.select(safe_folder)
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
      status, data = await client.select(safe_folder)
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
