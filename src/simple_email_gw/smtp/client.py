"""Async SMTP client using aiosmtplib."""

from __future__ import annotations

import asyncio
import logging
import os
import re
import ssl
from email import encoders
from email.message import EmailMessage, Message
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import make_msgid
from typing import Any

import aiosmtplib

from simple_email_gw.config import EmailAccount, get_recipient_whitelist
from simple_email_gw.imap.client import IMAPClient
from simple_email_gw.safety.audit import log_email_appended, log_email_sent
from simple_email_gw.safety.sanitize import (
  sanitize_filename,
  sanitize_message_id,
  sanitize_references,
  sanitize_subject,
)

_logger = logging.getLogger(__name__)

# Email address validation pattern
EMAIL_PATTERN = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")


def validate_email(address: str) -> str:
  """Validate email address format with CRLF protection.

  Validates email address format and rejects addresses containing
  CR or LF characters to prevent header injection attacks.

  Args:
    address: Email address to validate

  Returns:
    The validated email address

  Raises:
    ValueError: If address is invalid or contains CRLF characters
  """
  # Reject CRLF sequences to prevent header injection
  if "\r" in address or "\n" in address:
    raise ValueError(f"Email address contains invalid characters: {address}")
  if not EMAIL_PATTERN.match(address):
    raise ValueError(f"Invalid email address: {address}")
  return address


class WhitelistError(Exception):
  """Raised when recipient is not in whitelist."""

  pass


class SMTPClient:
  """Async SMTP client with connection management."""

  def __init__(self, account: EmailAccount) -> None:
    self.account = account
    self._lock = asyncio.Lock()

  async def _auto_append(
    self,
    msg: Message,
    safe_subject: str,
    append_to_sent: bool,
    append_folder: str | None,
    imap_client: IMAPClient | None,
  ) -> dict[str, Any]:
    """Optionally append a copy of a sent message to the Sent folder."""
    append_result: dict[str, Any] = {
      "appended": False,
      "append_folder": None,
      "append_warning": None,
    }
    if not append_to_sent:
      return append_result

    message_bytes = msg.as_bytes()
    message_id = msg.get("Message-ID", "")
    message_size = len(message_bytes)

    if imap_client is None:
      append_result["append_warning"] = "append_to_sent requested but no IMAP client provided"
      _logger.warning("Auto-append skipped: no IMAP client provided")
      log_email_appended(
        account=self.account.name,
        folder="",
        success=False,
        message_id=message_id,
        subject_prefix=safe_subject,
        message_size=message_size,
        auto_append=True,
        error="No IMAP client provided",
      )
      return append_result

    target_folder = append_folder or await imap_client.find_sent_folder()
    if target_folder is None:
      append_result["append_warning"] = "Sent folder not found"
      _logger.warning("Auto-append skipped: Sent folder not found")
      log_email_appended(
        account=self.account.name,
        folder="",
        success=False,
        message_id=message_id,
        subject_prefix=safe_subject,
        message_size=message_size,
        auto_append=True,
        error="Sent folder not found",
      )
      return append_result

    try:
      await imap_client.append_message(
        folder=target_folder,
        message_bytes=message_bytes,
        flags=["\\Seen"],
      )
      append_result["appended"] = True
      append_result["append_folder"] = target_folder
      log_email_appended(
        account=self.account.name,
        folder=target_folder,
        success=True,
        message_id=message_id,
        subject_prefix=safe_subject,
        message_size=message_size,
        auto_append=True,
      )
    except Exception as e:
      _logger.warning("Auto-append to Sent folder failed: %s", e)
      append_result["append_warning"] = "Could not save copy to Sent folder"
      log_email_appended(
        account=self.account.name,
        folder=target_folder,
        success=False,
        message_id=message_id,
        subject_prefix=safe_subject,
        message_size=message_size,
        auto_append=True,
        error="Could not save copy to Sent folder",
      )

    return append_result

  async def send_email(
    self,
    to: list[str],
    subject: str,
    body: str,
    cc: list[str] | None = None,
    bcc: list[str] | None = None,
    html_body: str | None = None,
    attachments: list[str] | None = None,
    in_reply_to: str | None = None,
    references: list[str] | None = None,
    append_to_sent: bool = False,
    append_folder: str | None = None,
    imap_client: IMAPClient | None = None,
  ) -> dict[str, Any]:
    """Send an email message with optional HTML body and attachments.

    Validates all recipient addresses, checks whitelist restrictions,
    and sanitizes headers to prevent CRLF injection. The message is sent
    via SMTP with TLS 1.2 minimum encryption. When ``append_to_sent`` is
    True and an IMAP client is provided, a copy of the sent message is
    appended to the account's Sent folder; append failures are surfaced
    as a warning rather than failing the send.

    Args:
      to: List of primary recipient email addresses
      subject: Email subject line (sanitized for CRLF)
      body: Plain text email body
      cc: Optional list of CC recipients
      bcc: Optional list of BCC recipients
      html_body: Optional HTML version of the body
      attachments: Optional list of file paths to attach
      in_reply_to: Optional Message-ID of the original message being replied to
      references: Optional list of Message-IDs in the thread history
      append_to_sent: Whether to append a copy to the Sent folder
      append_folder: Optional override for the Sent folder name
      imap_client: Optional IMAP client for the auto-append operation

    Returns:
      Dict with send status and optional append metadata

    Raises:
      ValueError: If any email address is invalid
      WhitelistError: If any recipient is not in the whitelist
      FileNotFoundError: If an attachment file is not found
      RuntimeError: If SMTP send fails
    """
    # Sanitize subject to prevent CRLF injection
    safe_subject = sanitize_subject(subject)

    # Validate email addresses
    for addr in to:
      validate_email(addr)
    if cc:
      for addr in cc:
        validate_email(addr)
    if bcc:
      for addr in bcc:
        validate_email(addr)

    # Check recipient whitelist
    whitelist = get_recipient_whitelist()
    all_recipients = to + (cc or []) + (bcc or [])
    allowed, blocked = whitelist.filter_recipients(all_recipients)

    if blocked:
      raise WhitelistError(f"Recipients not in whitelist: {', '.join(blocked)}")

    # Create message
    if html_body or attachments:
      msg = MIMEMultipart("alternative" if html_body else "mixed")
    else:
      msg = EmailMessage()

    msg["From"] = self.account.username
    msg["To"] = ", ".join(to)
    msg["Subject"] = safe_subject
    msg["Message-ID"] = make_msgid(domain=self.account.smtp_host)

    if cc:
      msg["Cc"] = ", ".join(cc)
    if bcc:
      msg["Bcc"] = ", ".join(bcc)

    # Set threading headers if provided
    if in_reply_to:
      safe_in_reply_to = sanitize_message_id(in_reply_to)
      msg["In-Reply-To"] = safe_in_reply_to

    if references:
      safe_references = sanitize_references(references)
      msg["References"] = " ".join(safe_references)

    if isinstance(msg, EmailMessage):
      msg.set_content(body)
      if html_body:
        msg.add_alternative(html_body, subtype="html")
    else:
      msg.attach(MIMEText(body, "plain"))
      if html_body:
        msg.attach(MIMEText(html_body, "html"))

    # Add attachments
    has_attachments = bool(attachments)
    if attachments:
      await self._add_attachments(msg, attachments)

    # Send
    result = await self._send(msg, to + (cc or []) + (bcc or []))

    # Optional auto-append to Sent folder
    append_result = await self._auto_append(
      msg=msg,
      safe_subject=safe_subject,
      append_to_sent=append_to_sent,
      append_folder=append_folder,
      imap_client=imap_client,
    )

    # Audit log
    log_email_sent(
      account=self.account.name,
      recipients=to,
      subject=safe_subject,
      has_attachments=has_attachments,
    )

    return {**result, **append_result}

  async def reply_email(
    self,
    to: str,
    subject: str,
    body: str,
    in_reply_to: str,
    references: list[str] | None = None,
    html_body: str | None = None,
    append_to_sent: bool = False,
    append_folder: str | None = None,
    imap_client: IMAPClient | None = None,
  ) -> dict[str, Any]:
    """Send a reply preserving thread context.

    Creates a reply message with proper In-Reply-To and References headers
    to maintain email threading. All headers are sanitized to prevent CRLF
    injection. The message is sent via SMTP with TLS 1.2 minimum encryption.

    Args:
      to: Recipient email address (single recipient for reply)
      subject: Email subject line (sanitized for CRLF)
      body: Plain text email body
      in_reply_to: Message-ID of the original message being replied to
      references: Optional list of Message-IDs in the thread history
      html_body: Optional HTML version of the body
      append_to_sent: Whether to append a copy to the Sent folder
      append_folder: Optional override for the Sent folder name
      imap_client: Optional IMAP client for the auto-append operation

    Returns:
      Dict with send status and optional append metadata

    Raises:
      ValueError: If email address or Message-IDs are invalid
      WhitelistError: If the recipient is not in the whitelist
      RuntimeError: If SMTP send fails
    """
    # Validate email address
    validate_email(to)

    # Sanitize subject to prevent CRLF injection
    safe_subject = sanitize_subject(subject)

    # Sanitize Message-ID headers to prevent CRLF injection
    safe_in_reply_to = sanitize_message_id(in_reply_to)
    safe_references = sanitize_references(references) if references else None

    # Check recipient whitelist
    whitelist = get_recipient_whitelist()
    if not whitelist.is_allowed(to):
      raise WhitelistError(f"Recipients not in whitelist: {to}")

    msg = EmailMessage()

    msg["From"] = self.account.username
    msg["To"] = to
    msg["Subject"] = safe_subject
    msg["Message-ID"] = make_msgid(domain=self.account.smtp_host)
    msg["In-Reply-To"] = safe_in_reply_to

    if safe_references:
      msg["References"] = " ".join(safe_references)

    msg.set_content(body)
    if html_body:
      msg.add_alternative(html_body, subtype="html")

    result = await self._send(msg, [to])

    # Optional auto-append to Sent folder
    append_result = await self._auto_append(
      msg=msg,
      safe_subject=safe_subject,
      append_to_sent=append_to_sent,
      append_folder=append_folder,
      imap_client=imap_client,
    )

    # Audit log
    log_email_sent(
      account=self.account.name,
      recipients=[to],
      subject=safe_subject,
      has_attachments=False,
    )

    return {**result, **append_result}

  async def forward_email(
    self,
    to: list[str],
    subject: str,
    original_from: str,
    original_date: str,
    original_body: str,
  ) -> dict[str, Any]:
    """Forward an email with original content."""
    forward_body = f"\n\n---------- Forwarded message ----------\nFrom: {original_from}\nDate: {original_date}\n\n{original_body}"

    return await self.send_email(
      to=to,
      subject=f"Fwd: {subject}",
      body=forward_body,
    )

  async def _send(self, msg: Message, recipients: list[str]) -> dict[str, str]:
    """Send message via SMTP with TLS 1.2 minimum."""
    async with self._lock:
      # Create SSL context with TLS 1.2 minimum
      context = ssl.create_default_context()
      context.minimum_version = ssl.TLSVersion.TLSv1_2

      try:
        # Connect and send
        if self.account.use_starttls:
          # STARTTLS (port 587)
          result = await aiosmtplib.send(
            msg,
            hostname=self.account.smtp_host,
            port=self.account.smtp_port,
            username=self.account.username,
            password=self.account.password.get_secret_value() if self.account.password else None,
            start_tls=True,
            tls_context=context,
          )
        else:
          # Implicit TLS (port 465)
          result = await aiosmtplib.send(
            msg,
            hostname=self.account.smtp_host,
            port=self.account.smtp_port,
            username=self.account.username,
            password=self.account.password.get_secret_value() if self.account.password else None,
            use_tls=True,
            tls_context=context,
          )

        return {
          "status": "sent",
          "recipients": ", ".join(recipients),
          "message": str(result[1]) if result else "OK",
        }
      except aiosmtplib.SMTPException as e:
        raise RuntimeError("Failed to send email. Check server logs for details.") from e

  async def _add_attachments(
    self,
    msg: MIMEMultipart,
    attachment_paths: list[str],
  ) -> None:
    """Add file attachments to message."""
    for path in attachment_paths:
      if not os.path.exists(path):
        raise FileNotFoundError(f"Attachment file not found: {path}")

      filename = os.path.basename(path)
      # Sanitize filename to prevent CRLF injection
      safe_filename = sanitize_filename(filename)
      with open(path, "rb") as f:
        part = MIMEBase("application", "octet-stream")
        part.set_payload(f.read())
        encoders.encode_base64(part)
        part.add_header(
          "Content-Disposition",
          f'attachment; filename="{safe_filename}"',
        )
        msg.attach(part)
