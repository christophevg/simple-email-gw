"""Safety utilities for email operations."""

from simple_email_gw.safety.audit import (
  log_attachment_download,
  log_auth_attempt,
  log_email_sent,
  log_event,
  log_rate_limited,
)
from simple_email_gw.safety.rate_limiter import RateLimiter
from simple_email_gw.safety.sanitize import (
  sanitize_filename,
  sanitize_folder_name,
  sanitize_header_value,
  sanitize_message_id,
  sanitize_message_id_numeric,
  sanitize_references,
  sanitize_subject,
  validate_folder_name,
)

__all__ = [
  # Rate limiting
  "RateLimiter",
  # Audit logging
  "log_event",
  "log_email_sent",
  "log_auth_attempt",
  "log_rate_limited",
  "log_attachment_download",
  # Sanitization
  "sanitize_message_id",
  "sanitize_references",
  "sanitize_header_value",
  "sanitize_subject",
  "sanitize_folder_name",
  "validate_folder_name",
  "sanitize_filename",
  "sanitize_message_id_numeric",
]
