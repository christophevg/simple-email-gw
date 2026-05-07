"""Simple Email Gateway - IMAP/SMTP client with security features."""

from simple_email_gw.config import EmailAccount, RateLimitConfig, RecipientWhitelist, ServerConfig
from simple_email_gw.connections.pool import ConnectionPool, RateLimitError, get_pool
from simple_email_gw.imap.client import IMAPClient, SecurityError
from simple_email_gw.safety.audit import (
  log_attachment_download,
  log_auth_attempt,
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
)
from simple_email_gw.smtp.client import SMTPClient, WhitelistError, validate_email

__version__ = "0.1.0"
__all__ = [
  # Clients
  "IMAPClient",
  "SMTPClient",
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
  "log_auth_attempt",
  "log_rate_limited",
  "log_attachment_download",
  "sanitize_message_id",
  "sanitize_references",
  "sanitize_header_value",
  "sanitize_subject",
  # Errors
  "SecurityError",
  "WhitelistError",
  "validate_email",
]
