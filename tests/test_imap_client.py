"""Tests for async IMAPClient.

These tests verify the async IMAPClient directly, including message parsing
and threading header extraction.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from simple_email_gw.config import EmailAccount
from simple_email_gw.imap.client import IMAPClient


class TestFetchMessage:
  """Tests for IMAPClient.fetch_message method."""

  @pytest.fixture
  def account(self):
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

  @pytest.mark.asyncio
  async def test_fetch_message_returns_message_id_and_references(self, account):
    """
    Given: An IMAP server returns a message with Message-ID and References headers
    When: fetch_message() is called
    Then: Result dict includes message_id and references fields
    """
    client = IMAPClient(account)

    # Build a raw RFC 822 message with threading headers
    raw_message = (
      b"From: sender@example.com\r\n"
      b"To: recipient@example.com\r\n"
      b"Subject: Test Thread\r\n"
      b"Message-ID: <msg123@example.com>\r\n"
      b"References: <ref1@example.com> <ref2@example.com>\r\n"
      b"Date: Mon, 01 Jan 2024 00:00:00 +0000\r\n"
      b"\r\n"
      b"Hello world"
    )

    mock_imap = AsyncMock()
    mock_imap.select = AsyncMock(return_value=("OK", [b"1 EXISTS"]))
    mock_imap.fetch = AsyncMock(
      return_value=(
        "OK",
        [
          b"1 FETCH (BODY[] {" + str(len(raw_message)).encode() + b"}",
          bytearray(raw_message),
          b" FLAGS (\\Seen)",
          b"FETCH completed",
        ],
      )
    )

    with patch.object(client, "connect", new_callable=AsyncMock) as mock_connect:
      mock_connect.return_value = mock_imap
      result = await client.fetch_message("1", folder="INBOX")

    assert result["message_id"] == "<msg123@example.com>"
    assert result["references"] == ["<ref1@example.com>", "<ref2@example.com>"]
    assert result["subject"] == "Test Thread"
    assert result["from"] == "sender@example.com"

  @pytest.mark.asyncio
  async def test_fetch_message_empty_references_returns_empty_list(self, account):
    """
    Given: An IMAP server returns a message without References header
    When: fetch_message() is called
    Then: Result references field is an empty list
    """
    client = IMAPClient(account)

    raw_message = (
      b"From: sender@example.com\r\n"
      b"To: recipient@example.com\r\n"
      b"Subject: No Refs\r\n"
      b"Message-ID: <msg456@example.com>\r\n"
      b"Date: Mon, 01 Jan 2024 00:00:00 +0000\r\n"
      b"\r\n"
      b"Body text"
    )

    mock_imap = AsyncMock()
    mock_imap.select = AsyncMock(return_value=("OK", [b"1 EXISTS"]))
    mock_imap.fetch = AsyncMock(
      return_value=(
        "OK",
        [
          b"1 FETCH (BODY[] {" + str(len(raw_message)).encode() + b"}",
          bytearray(raw_message),
          b" FLAGS (\\Seen)",
          b"FETCH completed",
        ],
      )
    )

    with patch.object(client, "connect", new_callable=AsyncMock) as mock_connect:
      mock_connect.return_value = mock_imap
      result = await client.fetch_message("1", folder="INBOX")

    assert result["message_id"] == "<msg456@example.com>"
    assert result["references"] == []

  @pytest.mark.asyncio
  async def test_fetch_message_no_message_id_returns_empty_string(self, account):
    """
    Given: An IMAP server returns a message without Message-ID header
    When: fetch_message() is called
    Then: Result message_id field is an empty string
    """
    client = IMAPClient(account)

    raw_message = (
      b"From: sender@example.com\r\n"
      b"To: recipient@example.com\r\n"
      b"Subject: No ID\r\n"
      b"Date: Mon, 01 Jan 2024 00:00:00 +0000\r\n"
      b"\r\n"
      b"Body text"
    )

    mock_imap = AsyncMock()
    mock_imap.select = AsyncMock(return_value=("OK", [b"1 EXISTS"]))
    mock_imap.fetch = AsyncMock(
      return_value=(
        "OK",
        [
          b"1 FETCH (BODY[] {" + str(len(raw_message)).encode() + b"}",
          bytearray(raw_message),
          b" FLAGS (\\Seen)",
          b"FETCH completed",
        ],
      )
    )

    with patch.object(client, "connect", new_callable=AsyncMock) as mock_connect:
      mock_connect.return_value = mock_imap
      result = await client.fetch_message("1", folder="INBOX")

    assert result["message_id"] == ""
    assert result["references"] == []
