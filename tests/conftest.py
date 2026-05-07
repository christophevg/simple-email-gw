"""Pytest configuration and fixtures for simple-email-gw tests."""

import asyncio
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from simple_email_gw.config import EmailAccount


@pytest.fixture
def event_loop():
  """Create an event loop for async tests."""
  loop = asyncio.new_event_loop()
  yield loop
  loop.close()


@pytest.fixture
def mock_account():
  """Create a mock email account for testing."""
  return EmailAccount(
    name="test",
    imap_host="imap.test.com",
    imap_port=993,
    smtp_host="smtp.test.com",
    smtp_port=587,
    username="test@test.com",
    password="test_password",
    auth_method="password",
  )


@pytest.fixture
def mock_oauth_account():
  """Create a mock OAuth2 email account for testing."""
  return EmailAccount(
    name="oauth_test",
    imap_host="imap.gmail.com",
    imap_port=993,
    smtp_host="smtp.gmail.com",
    smtp_port=587,
    username="test@gmail.com",
    oauth2_token="test_oauth_token",
    auth_method="oauth2",
  )


@pytest.fixture
def temp_workspace():
  """Create a temporary workspace directory for attachment tests."""
  with tempfile.TemporaryDirectory() as tmpdir:
    yield Path(tmpdir)


@pytest.fixture
def mock_imap_client(mock_account):
  """Create a mock IMAP client."""
  with patch("simple_email_gw.imap.client.IMAP4_SSL") as mock_imap_class:
    mock_client = AsyncMock()
    mock_client.wait_hello_from_server = AsyncMock()
    mock_client.login = AsyncMock(return_value=("OK", [b"Logged in"]))
    mock_client.select = AsyncMock(return_value=("OK", [b"10"]))
    mock_client.list = AsyncMock(return_value=("OK", [b'(\\HasNoChildren) "/" "INBOX"']))
    mock_client.search = AsyncMock(return_value=("OK", [b"1 2 3"]))
    mock_client.fetch = AsyncMock(return_value=("OK", []))
    mock_client.logout = AsyncMock(return_value=("OK", [b"Logged out"]))
    mock_imap_class.return_value = mock_client
    yield mock_client


@pytest.fixture
def mock_smtp_client():
  """Create a mock SMTP client result."""
  with patch("simple_email_gw.smtp.client.aiosmtplib.send") as mock_send:
    mock_send.return_value = (None, "OK")
    yield mock_send


@pytest.fixture(autouse=True)
def reset_connection_pool():
  """Reset connection pool between tests."""
  from simple_email_gw.connections import pool as pool_module
  pool_module._pool = None
  yield
  pool_module._pool = None
