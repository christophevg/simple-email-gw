"""Tests for async SMTPClient.

These tests verify the SMTP client directly, including Message-ID generation
and the optional auto-append-to-Sent path.
"""

from unittest.mock import AsyncMock, patch

import pytest

from simple_email_gw.config import EmailAccount
from simple_email_gw.smtp.client import SMTPClient


@pytest.fixture
def account():
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


class TestSendEmailMessageId:
  """Tests for Message-ID generation before SMTP submission."""

  @pytest.mark.asyncio
  async def test_send_email_generates_message_id(self, account):
    """A stable Message-ID is added to the message before _send."""
    client = SMTPClient(account)
    with patch.object(client, "_send", new_callable=AsyncMock) as mock_send:
      mock_send.return_value = {
        "status": "sent",
        "recipients": "recipient@example.com",
        "message": "OK",
      }
      await client.send_email(
        to=["recipient@example.com"],
        subject="Test",
        body="Hello",
      )

    msg = mock_send.call_args[0][0]
    assert "Message-ID" in msg
    assert msg["Message-ID"].startswith("<")
    assert msg["Message-ID"].endswith(">")

  @pytest.mark.asyncio
  async def test_send_email_preserves_message_id_in_append(self, account):
    """The Message-ID in the appended copy matches the sent message."""
    client = SMTPClient(account)
    imap_client = AsyncMock()
    imap_client.find_sent_folder = AsyncMock(return_value="Sent")
    imap_client.append_message = AsyncMock(return_value={"status": "appended", "folder": "Sent"})

    with patch.object(client, "_send", new_callable=AsyncMock) as mock_send:
      mock_send.return_value = {
        "status": "sent",
        "recipients": "recipient@example.com",
        "message": "OK",
      }
      await client.send_email(
        to=["recipient@example.com"],
        subject="Test",
        body="Hello",
        append_to_sent=True,
        imap_client=imap_client,
      )

    sent_msg = mock_send.call_args[0][0]
    append_call = imap_client.append_message.call_args
    appended_bytes = append_call.kwargs["message_bytes"]
    assert sent_msg["Message-ID"].encode() in appended_bytes


class TestSendEmailAutoAppend:
  """Tests for the optional auto-append-to-Sent path."""

  @pytest.mark.asyncio
  async def test_send_email_auto_append_success(self, account):
    """When append succeeds, result reports appended True and folder."""
    client = SMTPClient(account)
    imap_client = AsyncMock()
    imap_client.find_sent_folder = AsyncMock(return_value="Sent")
    imap_client.append_message = AsyncMock(return_value={"status": "appended", "folder": "Sent"})

    with patch.object(client, "_send", new_callable=AsyncMock) as mock_send:
      mock_send.return_value = {
        "status": "sent",
        "recipients": "recipient@example.com",
        "message": "OK",
      }
      result = await client.send_email(
        to=["recipient@example.com"],
        subject="Test",
        body="Hello",
        append_to_sent=True,
        imap_client=imap_client,
      )

    assert result["status"] == "sent"
    assert result["appended"] is True
    assert result["append_folder"] == "Sent"
    assert result["append_warning"] is None
    imap_client.find_sent_folder.assert_awaited_once()
    imap_client.append_message.assert_awaited_once()
    append_call = imap_client.append_message.call_args
    assert append_call.kwargs["folder"] == "Sent"
    assert append_call.kwargs["flags"] == ["\\Seen"]

  @pytest.mark.asyncio
  async def test_send_email_auto_append_failure_is_warning(self, account):
    """When append fails, send still succeeds and a warning is returned."""
    client = SMTPClient(account)
    imap_client = AsyncMock()
    imap_client.find_sent_folder = AsyncMock(return_value="Sent")
    imap_client.append_message = AsyncMock(side_effect=RuntimeError("IMAP failure"))

    with patch.object(client, "_send", new_callable=AsyncMock) as mock_send:
      mock_send.return_value = {
        "status": "sent",
        "recipients": "recipient@example.com",
        "message": "OK",
      }
      with patch("simple_email_gw.smtp.client.log_email_appended") as mock_log:
        result = await client.send_email(
          to=["recipient@example.com"],
          subject="Test",
          body="Hello",
          append_to_sent=True,
          imap_client=imap_client,
        )

    assert result["status"] == "sent"
    assert result["appended"] is False
    assert result["append_folder"] is None
    assert result["append_warning"] == "Could not save copy to Sent folder"
    mock_log.assert_called_once()
    assert mock_log.call_args.kwargs["success"] is False
    assert mock_log.call_args.kwargs["auto_append"] is True

  @pytest.mark.asyncio
  async def test_send_email_auto_append_missing_imap_client(self, account):
    """append_to_sent without imap_client returns a safe warning."""
    client = SMTPClient(account)

    with patch.object(client, "_send", new_callable=AsyncMock) as mock_send:
      mock_send.return_value = {
        "status": "sent",
        "recipients": "recipient@example.com",
        "message": "OK",
      }
      with patch("simple_email_gw.smtp.client.log_email_appended") as mock_log:
        result = await client.send_email(
          to=["recipient@example.com"],
          subject="Test",
          body="Hello",
          append_to_sent=True,
        )

    assert result["status"] == "sent"
    assert result["appended"] is False
    assert "no IMAP client" in result["append_warning"]
    mock_log.assert_called_once()

  @pytest.mark.asyncio
  async def test_send_email_auto_append_folder_not_found(self, account):
    """When Sent folder is not found, result includes a warning."""
    client = SMTPClient(account)
    imap_client = AsyncMock()
    imap_client.find_sent_folder = AsyncMock(return_value=None)

    with patch.object(client, "_send", new_callable=AsyncMock) as mock_send:
      mock_send.return_value = {
        "status": "sent",
        "recipients": "recipient@example.com",
        "message": "OK",
      }
      result = await client.send_email(
        to=["recipient@example.com"],
        subject="Test",
        body="Hello",
        append_to_sent=True,
        imap_client=imap_client,
      )

    assert result["status"] == "sent"
    assert result["appended"] is False
    assert result["append_warning"] == "Sent folder not found"

  @pytest.mark.asyncio
  async def test_send_email_auto_append_uses_override_folder(self, account):
    """append_folder bypasses automatic Sent folder detection."""
    client = SMTPClient(account)
    imap_client = AsyncMock()
    imap_client.find_sent_folder = AsyncMock(return_value="Sent")
    imap_client.append_message = AsyncMock(return_value={"status": "appended", "folder": "Custom"})

    with patch.object(client, "_send", new_callable=AsyncMock) as mock_send:
      mock_send.return_value = {
        "status": "sent",
        "recipients": "recipient@example.com",
        "message": "OK",
      }
      result = await client.send_email(
        to=["recipient@example.com"],
        subject="Test",
        body="Hello",
        append_to_sent=True,
        append_folder="Custom",
        imap_client=imap_client,
      )

    assert result["appended"] is True
    assert result["append_folder"] == "Custom"
    imap_client.find_sent_folder.assert_not_awaited()

  @pytest.mark.asyncio
  async def test_send_email_append_disabled_no_append_keys(self, account):
    """When append_to_sent is False, append metadata indicates no append."""
    client = SMTPClient(account)

    with patch.object(client, "_send", new_callable=AsyncMock) as mock_send:
      mock_send.return_value = {
        "status": "sent",
        "recipients": "recipient@example.com",
        "message": "OK",
      }
      result = await client.send_email(
        to=["recipient@example.com"],
        subject="Test",
        body="Hello",
      )

    assert result["appended"] is False
    assert result["append_folder"] is None
    assert result["append_warning"] is None


class TestReplyEmailAutoAppend:
  """Tests for auto-append in reply_email."""

  @pytest.mark.asyncio
  async def test_reply_email_preserves_threading_headers(self, account):
    """Threading headers are preserved in the appended reply copy."""
    client = SMTPClient(account)
    imap_client = AsyncMock()
    imap_client.find_sent_folder = AsyncMock(return_value="Sent")
    imap_client.append_message = AsyncMock(return_value={"status": "appended", "folder": "Sent"})

    with patch.object(client, "_send", new_callable=AsyncMock) as mock_send:
      mock_send.return_value = {
        "status": "sent",
        "recipients": "recipient@example.com",
        "message": "OK",
      }
      await client.reply_email(
        to="recipient@example.com",
        subject="Re: Test",
        body="Reply",
        in_reply_to="<original@example.com>",
        references=["<original@example.com>"],
        append_to_sent=True,
        imap_client=imap_client,
      )

    sent_msg = mock_send.call_args[0][0]
    appended_bytes = imap_client.append_message.call_args.kwargs["message_bytes"]
    assert sent_msg["In-Reply-To"].encode() in appended_bytes
    assert sent_msg["References"].encode() in appended_bytes
    assert sent_msg["Message-ID"].encode() in appended_bytes

  @pytest.mark.asyncio
  async def test_reply_email_auto_append_failure_returns_warning(self, account):
    """When reply append fails, send still succeeds."""
    client = SMTPClient(account)
    imap_client = AsyncMock()
    imap_client.find_sent_folder = AsyncMock(return_value="Sent")
    imap_client.append_message = AsyncMock(side_effect=RuntimeError("fail"))

    with patch.object(client, "_send", new_callable=AsyncMock) as mock_send:
      mock_send.return_value = {
        "status": "sent",
        "recipients": "recipient@example.com",
        "message": "OK",
      }
      result = await client.reply_email(
        to="recipient@example.com",
        subject="Re: Test",
        body="Reply",
        in_reply_to="<original@example.com>",
        append_to_sent=True,
        imap_client=imap_client,
      )

    assert result["status"] == "sent"
    assert result["appended"] is False
    assert result["append_warning"] == "Could not save copy to Sent folder"
