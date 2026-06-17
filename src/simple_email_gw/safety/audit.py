"""Audit logging for email operations."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

# Configure audit logger
audit_logger = logging.getLogger("simple_email_gw.audit")
audit_logger.setLevel(logging.INFO)

# Add handler if not present
if not audit_logger.handlers:
  handler = logging.StreamHandler()
  handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
  audit_logger.addHandler(handler)


def log_event(
  event: str,
  account: str,
  details: dict[str, Any] | None = None,
  level: int = logging.INFO,
) -> None:
  """Log an audit event.

  Args:
    event: Event type (e.g., EMAIL_SENT, AUTH_SUCCESS)
    account: Account name
    details: Additional event details
    level: Log level (default INFO)
  """
  record = {
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "event": event,
    "account": account,
    "details": details or {},
  }
  audit_logger.log(level, json.dumps(record))


def log_email_sent(
  account: str,
  recipients: list[str],
  subject: str,
  has_attachments: bool = False,
) -> None:
  """Log email send operation."""
  log_event(
    event="EMAIL_SENT",
    account=account,
    details={
      "recipient_count": len(recipients),
      "recipients": ", ".join(recipients[:5]),  # Limit for privacy
      "subject_prefix": subject[:50] if subject else "",
      "has_attachments": has_attachments,
    },
  )


def log_email_appended(
  account: str,
  folder: str,
  success: bool = True,
  message_id: str | None = None,
  subject_prefix: str = "",
  message_size: int = 0,
  auto_append: bool = False,
  error: str | None = None,
) -> None:
  """Log an IMAP APPEND operation."""
  log_event(
    event="EMAIL_APPENDED",
    account=account,
    details={
      "folder": folder,
      "message_id": message_id[:50] if message_id else "",
      "subject_prefix": subject_prefix[:50],
      "message_size": message_size,
      "auto_append": auto_append,
      "success": success,
      "error": error,
    },
    level=logging.INFO if success else logging.WARNING,
  )


def log_auth_attempt(
  account: str,
  success: bool,
  method: str,
  error: str | None = None,
) -> None:
  """Log authentication attempt."""
  log_event(
    event="AUTH_SUCCESS" if success else "AUTH_FAILURE",
    account=account,
    details={
      "method": method,
      "error": error,
    },
    level=logging.INFO if success else logging.WARNING,
  )


def log_rate_limited(
  account: str,
  operation: str,
  limit: int,
  window: int,
) -> None:
  """Log rate limit exceeded."""
  log_event(
    event="RATE_LIMITED",
    account=account,
    details={
      "operation": operation,
      "limit": limit,
      "window_seconds": window,
    },
    level=logging.WARNING,
  )


def log_attachment_download(
  account: str,
  filename: str,
  output_path: str,
) -> None:
  """Log attachment download."""
  log_event(
    event="ATTACHMENT_DOWNLOADED",
    account=account,
    details={
      "filename": filename,
      "output_path": output_path,
    },
  )


def log_folder_created(account_name: str, folder_name: str) -> None:
  """Log a folder creation event."""
  log_event(
    event="FOLDER_CREATED",
    account=account_name,
    details={"folder": folder_name},
  )
