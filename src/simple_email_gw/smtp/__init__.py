"""SMTP client operations."""

from simple_email_gw.smtp.client import SMTPClient, WhitelistError, validate_email

__all__ = ["SMTPClient", "WhitelistError", "validate_email"]
