"""Tests for configuration module."""

import json
import os

from simple_email_gw.config import EmailAccount, RateLimitConfig, ServerConfig


class TestEmailAccount:
  """Tests for EmailAccount model."""

  def test_password_account(self):
    """Test creating account with password."""
    account = EmailAccount(
      name="test",
      imap_host="imap.test.com",
      smtp_host="smtp.test.com",
      username="test@test.com",
      password="secret",
    )
    assert account.name == "test"
    assert account.password.get_secret_value() == "secret"
    assert account.auth_method == "password"
    assert account.use_starttls is True  # Port 587 default

  def test_oauth2_account(self):
    """Test creating account with OAuth2."""
    account = EmailAccount(
      name="oauth",
      imap_host="imap.gmail.com",
      smtp_host="smtp.gmail.com",
      username="test@gmail.com",
      oauth2_token="token123",
      auth_method="oauth2",
    )
    assert account.oauth2_token.get_secret_value() == "token123"

  def test_implicit_ssl_port(self):
    """Test that port 465 uses implicit SSL."""
    account = EmailAccount(
      name="ssl",
      imap_host="imap.test.com",
      smtp_host="smtp.test.com",
      smtp_port=465,
      username="test@test.com",
      password="secret",
    )
    assert account.use_starttls is False

  def test_secrets_not_in_repr(self):
    """Test that secrets are not exposed in string representation."""
    account = EmailAccount(
      name="test",
      imap_host="imap.test.com",
      smtp_host="smtp.test.com",
      username="test@test.com",
      password="secret",
    )
    repr_str = repr(account)
    assert "secret" not in repr_str
    assert "********" in repr_str or "SecretStr" in repr_str


class TestServerConfig:
  """Tests for ServerConfig model."""

  def test_individual_env_vars(self, monkeypatch):
    """Test configuration from individual environment variables."""
    monkeypatch.setenv("EMAIL_IMAP_HOST", "imap.test.com")
    monkeypatch.setenv("EMAIL_SMTP_HOST", "smtp.test.com")
    monkeypatch.setenv("EMAIL_USERNAME", "test@test.com")
    monkeypatch.setenv("EMAIL_PASSWORD", "secret")

    config = ServerConfig()
    accounts = config.get_accounts()

    assert len(accounts) == 1
    assert accounts[0].name == "default"
    assert accounts[0].imap_host == "imap.test.com"

  def test_json_env_vars(self, monkeypatch):
    """Test configuration from JSON environment variable."""
    accounts_json = json.dumps(
      [
        {
          "name": "work",
          "imap_host": "imap.work.com",
          "smtp_host": "smtp.work.com",
          "username": "work@example.com",
          "password": "secret1",
        },
        {
          "name": "personal",
          "imap_host": "imap.gmail.com",
          "smtp_host": "smtp.gmail.com",
          "username": "personal@gmail.com",
          "password": "secret2",
        },
      ]
    )
    monkeypatch.setenv("EMAIL_ACCOUNTS_JSON", accounts_json)

    config = ServerConfig()
    accounts = config.get_accounts()

    assert len(accounts) == 2
    assert accounts[0].name == "work"
    assert accounts[1].name == "personal"

  def test_empty_config(self, monkeypatch):
    """Test empty configuration returns empty list."""
    # Clear all EMAIL_ environment variables to ensure clean state
    for key in list(os.environ.keys()):
      if key.startswith("EMAIL_"):
        monkeypatch.delenv(key, raising=False)

    config = ServerConfig()
    accounts = config.get_accounts()
    assert len(accounts) == 0


class TestRateLimitConfig:
  """Tests for rate limit configuration."""

  def test_defaults(self):
    """Test default rate limits."""
    config = RateLimitConfig()
    assert config.imap_requests_per_minute == 60
    assert config.smtp_sends_per_hour == 100
