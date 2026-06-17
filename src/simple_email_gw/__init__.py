"""Simple Email Gateway - IMAP/SMTP client with security features."""

from simple_email_gw.config import EmailAccount, RateLimitConfig, RecipientWhitelist, ServerConfig
from simple_email_gw.connections.pool import ConnectionPool, RateLimitError, get_pool
from simple_email_gw.imap.client import IMAPClient, SecurityError
from simple_email_gw.imap.sync_client import SyncIMAPClient
from simple_email_gw.safety.audit import (
  log_attachment_download,
  log_auth_attempt,
  log_email_appended,
  log_email_sent,
  log_event,
  log_rate_limited,
)
from simple_email_gw.safety.rate_limiter import RateLimiter
from simple_email_gw.safety.sanitize import (
  sanitize_header_value,
  sanitize_message_id,
  sanitize_references,
  sanitize_subject,
  validate_append_flags,
)
from simple_email_gw.smtp.client import SMTPClient, WhitelistError, validate_email
from simple_email_gw.smtp.sync_client import SyncSMTPClient

__version__ = "0.3.0"
__all__ = [
  # Clients
  "IMAPClient",
  "SMTPClient",
  "SyncIMAPClient",
  "SyncSMTPClient",
  # Connection management
  "ConnectionPool",
  "RateLimitError",
  "get_pool",
  # Configuration
  "EmailAccount",
  "ServerConfig",
  "RateLimitConfig",
  "RecipientWhitelist",
  # Safety utilities
  "RateLimiter",
  "log_event",
  "log_email_sent",
  "log_email_appended",
  "log_auth_attempt",
  "log_rate_limited",
  "log_attachment_download",
  "sanitize_message_id",
  "sanitize_references",
  "sanitize_header_value",
  "sanitize_subject",
  "validate_append_flags",
  # Errors
  "SecurityError",
  "WhitelistError",
  "validate_email",
]
