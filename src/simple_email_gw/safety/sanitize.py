"""Input sanitization for CRLF injection prevention.

This module provides sanitization functions to prevent CRLF injection attacks
in email headers. CRLF injection can allow attackers to inject arbitrary headers
or manipulate email content.

Security Note:
  All user-controlled header values should be sanitized before being used in
  email headers. This includes Message-IDs, subjects, and email addresses.
"""

from __future__ import annotations

import os

# Default maximum size for IMAP APPEND (25 MB)
APPEND_MAX_SIZE_DEFAULT = 25 * 1024 * 1024

# Allowlisted IMAP APPEND flags
APPEND_FLAG_ALLOWLIST = {"\\Seen", "\\Draft", "\\Answered", "\\Flagged"}


def sanitize_message_id(message_id: str) -> str:
  """Validate and sanitize Message-ID for header safety.

  Prevents CRLF injection by rejecting newline characters and validating
  RFC 5322 Message-ID format. Message-IDs must be angle-bracketed strings
  containing an email-like identifier (<id@domain>).

  Args:
    message_id: A Message-ID string (should be angle-bracketed)

  Returns:
    The validated Message-ID (unchanged if valid)

  Raises:
    ValueError: If the Message-ID contains newlines, is not angle-bracketed,
                or has invalid format

  Examples:
    >>> sanitize_message_id("<abc123@mail.example.com>")
    '<abc123@mail.example.com>'

    >>> sanitize_message_id("<valid@id.com>\\r\\nBcc: evil")
    ValueError: Message-ID contains invalid newline characters
  """
  if not message_id:
    raise ValueError("Message-ID cannot be empty")

  # Reject CRLF sequences explicitly - this is the security fix
  if "\r" in message_id or "\n" in message_id:
    raise ValueError("Message-ID contains invalid newline characters")

  # Validate format: Message-IDs must be angle-bracketed
  if not message_id.startswith("<") or not message_id.endswith(">"):
    raise ValueError(f"Message-ID must be angle-bracketed: {message_id}")

  # Ensure no embedded angle brackets (prevents <a<b>@domain.com>)
  inner = message_id[1:-1]
  if "<" in inner or ">" in inner:
    raise ValueError(f"Message-ID contains invalid characters: {message_id}")

  # Ensure the inner content is not empty
  if not inner:
    raise ValueError(f"Message-ID has empty content: {message_id}")

  return message_id


def sanitize_references(references: list[str]) -> list[str]:
  """Validate and sanitize a list of Message-ID references.

  Each Message-ID in the list is validated using sanitize_message_id().
  This prevents CRLF injection through the References header.

  Args:
    references: List of Message-ID strings

  Returns:
    List of validated Message-IDs (unchanged if all valid)

  Raises:
    ValueError: If any Message-ID in the list is invalid

  Examples:
    >>> sanitize_references(["<msg1@id.com>", "<msg2@id.com>"])
    ['<msg1@id.com>', '<msg2@id.com>']

    >>> sanitize_references(["<msg1@id.com>", "invalid\\r\\nEvil: yes"])
    ValueError: Message-ID contains invalid newline characters
  """
  return [sanitize_message_id(ref) for ref in references]


def sanitize_header_value(value: str) -> str:
  """Sanitize a generic header value by removing CRLF sequences.

  This function removes CR, LF, and CRLF sequences from header values
  to prevent header injection attacks. Unlike sanitize_message_id(),
  this does not validate format - it simply removes dangerous characters.

  Args:
    value: A header value string

  Returns:
    The sanitized header value with CRLF sequences removed

  Raises:
    ValueError: If the value is empty or contains only invalid characters

  Examples:
    >>> sanitize_header_value("Normal Header")
    'Normal Header'

    >>> sanitize_header_value("Test\\r\\nInjected: evil")
    'TestInjected: evil'
  """
  if not value:
    raise ValueError("Header value cannot be empty")

  # Remove CR, LF, and CRLF sequences
  sanitized = value.replace("\r", "").replace("\n", "")

  if not sanitized:
    raise ValueError("Header value contains only invalid characters")

  return sanitized


def sanitize_subject(subject: str) -> str:
  """Sanitize email subject line for header safety.

  Removes CRLF sequences from subject lines to prevent header injection
  attacks. CR and LF characters are replaced with spaces to preserve
  readability while preventing injection.

  Args:
    subject: An email subject line

  Returns:
    The sanitized subject with CRLF sequences replaced by spaces

  Raises:
    ValueError: If the subject is empty or contains only invalid characters

  Examples:
    >>> sanitize_subject("Normal Subject")
    'Normal Subject'

    >>> sanitize_subject("Test\\r\\nBcc: attacker@evil.com")
    'Test Bcc: attacker@evil.com'
  """
  if not subject:
    raise ValueError("Subject cannot be empty")

  # Replace CR, LF, and CRLF with spaces to preserve readability
  # First replace CRLF sequences with a single space
  sanitized = subject.replace("\r\n", " ")
  # Then replace any remaining CR or LF with spaces
  sanitized = sanitized.replace("\r", " ").replace("\n", " ")

  # Collapse multiple spaces that may have been created
  while "  " in sanitized:
    sanitized = sanitized.replace("  ", " ")

  sanitized = sanitized.strip()

  if not sanitized:
    raise ValueError("Subject contains only invalid characters")

  return sanitized


def validate_folder_name(name: str) -> str:
  """Validate and normalize a folder name for IMAP CREATE.

  Args:
    name: Raw folder name.

  Returns:
    Stripped, validated folder name.

  Raises:
    ValueError: If the folder name is invalid (with descriptive message).
  """
  folder = name.strip()
  if not folder:
    raise ValueError("Folder name cannot be empty")
  if len(folder.encode("utf-8")) > 255:
    raise ValueError("Folder name exceeds maximum length")
  if "\r" in folder or "\n" in folder:
    raise ValueError("Folder name contains invalid characters")
  if "\x00" in folder or '"' in folder or "\\" in folder:
    raise ValueError("Folder name contains invalid characters")
  if ".." in folder.split("/") or ".." in folder.split(".") or ".." in folder:
    raise ValueError("Invalid folder name")
  if folder.startswith(("/", ".")):
    raise ValueError("Invalid folder name")
  if len(folder.split("/")) > 10 or len(folder.split(".")) > 10:
    raise ValueError("Folder nesting exceeds maximum depth")
  if folder.upper() == "INBOX":
    raise ValueError("INBOX is a reserved folder name")
  return folder


def sanitize_folder_name(folder: str) -> str:
  """Sanitize IMAP folder name to prevent CRLF injection.

  Validates that folder names do not contain CR or LF characters
  which could be used for IMAP command injection.

  Args:
    folder: IMAP folder name

  Returns:
    The validated folder name (unchanged if valid)

  Raises:
    ValueError: If folder name contains CRLF characters

  Examples:
    >>> sanitize_folder_name("INBOX")
    'INBOX'

    >>> sanitize_folder_name("Sent\\r\\nNoop")
    ValueError: Folder name contains invalid characters
  """
  if "\r" in folder or "\n" in folder:
    raise ValueError("Folder name contains invalid characters")
  return folder


def sanitize_filename(filename: str) -> str:
  """Sanitize attachment filename to prevent CRLF injection.

  Validates that filenames do not contain CR, LF, or null characters
  which could be used for header injection attacks.

  Args:
    filename: Attachment filename

  Returns:
    The validated filename (unchanged if valid)

  Raises:
    ValueError: If filename contains invalid characters

  Examples:
    >>> sanitize_filename("document.pdf")
    'document.pdf'

    >>> sanitize_filename("test.txt\\r\\nBcc: evil")
    ValueError: Filename contains invalid characters
  """
  if "\r" in filename or "\n" in filename or "\x00" in filename:
    raise ValueError("Filename contains invalid characters")
  return filename


def validate_append_flags(flags: list[str] | None) -> list[str]:
  """Validate IMAP APPEND flags against the allowlist.

  Args:
    flags: Optional list of IMAP flags.

  Returns:
    The validated flags as a list.

  Raises:
    ValueError: If any flag is not in the allowlist.
  """
  if flags is None:
    return []
  for flag in flags:
    if flag not in APPEND_FLAG_ALLOWLIST:
      raise ValueError(f"Invalid IMAP flag: {flag}")
  return list(flags)


def get_append_max_size() -> int:
  """Return the maximum allowed size for IMAP APPEND in bytes.

  Defaults to APPEND_MAX_SIZE_DEFAULT (25 MB). Override with the
  EMAIL_APPEND_MAX_SIZE environment variable.
  """
  env_value = os.environ.get("EMAIL_APPEND_MAX_SIZE")
  if env_value:
    try:
      return int(env_value)
    except ValueError:
      pass
  return APPEND_MAX_SIZE_DEFAULT


def sanitize_message_id_numeric(message_id: str) -> str:
  """Validate IMAP message ID is numeric to prevent injection.

  IMAP message IDs (sequence numbers) must be positive integers.
  This prevents IMAP command injection through message ID parameters.

  Args:
    message_id: IMAP sequence number as string

  Returns:
    The validated message ID (unchanged if valid)

  Raises:
    ValueError: If message ID is not numeric

  Examples:
    >>> sanitize_message_id_numeric("123")
    '123'

    >>> sanitize_message_id_numeric("1\\r\\nNoop")
    ValueError: Invalid message ID
  """
  if not message_id.isdigit():
    raise ValueError(f"Invalid message ID: {message_id}")
  return message_id
