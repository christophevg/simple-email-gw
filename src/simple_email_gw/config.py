"""Pydantic configuration for email MCP server."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


# Try to load .env file if it exists
def _load_dotenv() -> None:
  """Load .env file if present."""
  env_file = Path(__file__).parent.parent.parent / ".env"
  if env_file.exists():
    try:
      from dotenv import load_dotenv
      load_dotenv(env_file)
    except ImportError:
      # python-dotenv not installed, read manually
      with open(env_file) as f:
        for line in f:
          line = line.strip()
          if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            if key not in os.environ:
              os.environ[key] = value


_load_dotenv()


class EmailAccount(BaseModel):
  """Configuration for a single email account."""

  name: str = Field(description="Friendly name for the account")
  imap_host: str = Field(description="IMAP server hostname")
  imap_port: int = Field(default=993, description="IMAP server port")
  smtp_host: str = Field(description="SMTP server hostname")
  smtp_port: int = Field(default=587, description="SMTP server port")
  username: str = Field(description="Email address or username")
  password: SecretStr | None = Field(default=None, description="Password or app-specific password")
  oauth2_token: SecretStr | None = Field(default=None, description="OAuth2 access token")
  auth_method: Literal["password", "oauth2"] = Field(
    default="password", description="Authentication method"
  )
  use_ssl: bool = Field(default=True, description="Use SSL/TLS for connections")

  @property
  def use_starttls(self) -> bool:
    """SMTP STARTTLS is used for port 587."""
    return self.smtp_port == 587


class RateLimitConfig(BaseModel):
  """Rate limiting configuration."""

  imap_requests_per_minute: int = Field(default=60, description="IMAP requests per minute per account")
  smtp_sends_per_hour: int = Field(default=100, description="SMTP sends per hour per account")


class RecipientWhitelist(BaseModel):
  """Whitelist configuration for email recipients."""

  enabled: bool = Field(default=False, description="Whether whitelist is enabled")
  domains: list[str] = Field(default_factory=list, description="Allowed domains")
  addresses: list[str] = Field(default_factory=list, description="Allowed email addresses")

  def is_allowed(self, email: str) -> bool:
    """Check if an email address is allowed."""
    if not self.enabled:
      return True

    # Check exact address match
    if email.lower() in [a.lower() for a in self.addresses]:
      return True

    # Check domain match
    domain = email.split("@")[-1].lower() if "@" in email else ""
    if domain in [d.lower() for d in self.domains]:
      return True

    return False

  def filter_recipients(self, recipients: list[str]) -> tuple[list[str], list[str]]:
    """Filter recipients into allowed and blocked lists.

    Returns:
      Tuple of (allowed, blocked) recipient lists.
    """
    allowed = []
    blocked = []
    for recipient in recipients:
      if self.is_allowed(recipient):
        allowed.append(recipient)
      else:
        blocked.append(recipient)
    return allowed, blocked


class ServerConfig(BaseSettings):
  """Main server configuration loaded from environment variables."""

  model_config = SettingsConfigDict(
    env_prefix="EMAIL_",
    env_nested_delimiter="__",
    extra="ignore",
    # Treat empty strings as None
    env_parse_none_str="",
  )

  # Account configuration (JSON string from env)
  accounts_json: str | None = Field(
    default=None, description="JSON array of account configurations"
  )

  # Individual account settings (alternative to JSON)
  account_name: str = Field(default="default", description="Account name")
  imap_host: str | None = Field(default=None, description="IMAP hostname")
  imap_port: int = Field(default=993, description="IMAP port")
  smtp_host: str | None = Field(default=None, description="SMTP hostname")
  smtp_port: int = Field(default=587, description="SMTP port")
  username: str | None = Field(default=None, description="Email username")
  password: SecretStr | None = Field(default=None, description="Password")
  oauth2_token: SecretStr | None = Field(default=None, description="OAuth2 token")
  auth_method: Literal["password", "oauth2"] = Field(default="password")

  # Rate limiting
  rate_limits: RateLimitConfig = Field(default_factory=RateLimitConfig)

  # Recipient whitelist
  recipient_whitelist_json: str | None = Field(
    default=None, description="JSON whitelist config"
  )
  recipient_whitelist_domains: str | None = Field(
    default=None, description="Comma-separated allowed domains"
  )
  recipient_whitelist_addresses: str | None = Field(
    default=None, description="Comma-separated allowed addresses"
  )

  def get_accounts(self) -> list[EmailAccount]:
    """Parse and return configured accounts."""
    if self.accounts_json:
      accounts_data = json.loads(self.accounts_json)
      return [EmailAccount(**acc) for acc in accounts_data]

    # Single account from individual env vars
    if self.imap_host and self.smtp_host and self.username:
      account = EmailAccount(
        name=self.account_name,
        imap_host=self.imap_host,
        imap_port=self.imap_port,
        smtp_host=self.smtp_host,
        smtp_port=self.smtp_port,
        username=self.username,
        password=self.password,
        oauth2_token=self.oauth2_token,
        auth_method=self.auth_method,
      )
      return [account]

    return []

  def get_recipient_whitelist(self) -> RecipientWhitelist:
    """Parse and return recipient whitelist configuration."""
    # JSON configuration takes precedence
    if self.recipient_whitelist_json:
      data = json.loads(self.recipient_whitelist_json)
      whitelist = RecipientWhitelist(**data)
      whitelist.enabled = True
      return whitelist

    # Parse from individual env vars
    domains = []
    addresses = []

    if self.recipient_whitelist_domains:
      domains = [d.strip() for d in self.recipient_whitelist_domains.split(",") if d.strip()]

    if self.recipient_whitelist_addresses:
      addresses = [a.strip() for a in self.recipient_whitelist_addresses.split(",") if a.strip()]

    # Enable whitelist if any domains or addresses are configured
    enabled = bool(domains or addresses)

    return RecipientWhitelist(enabled=enabled, domains=domains, addresses=addresses)


def get_config() -> ServerConfig:
  """Load configuration from environment."""
  return ServerConfig()


def get_accounts() -> list[EmailAccount]:
  """Get configured email accounts."""
  return get_config().get_accounts()


def get_recipient_whitelist() -> RecipientWhitelist:
  """Get recipient whitelist configuration."""
  return get_config().get_recipient_whitelist()
