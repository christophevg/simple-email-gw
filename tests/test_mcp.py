"""Tests for MCP tools.

These tests verify the MCP tool wrappers, including:
- Tool delegation to async clients
- Error mapping to ToolError
- Context logging via ctx.info
- Rate limiting and account validation
"""

import base64
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastmcp.exceptions import ToolError

from simple_email_gw.connections.pool import RateLimitError

try:
  from simple_email_gw.mcp import append_email, create_folder, reply_email, send_email
except ImportError:
  append_email = None
  create_folder = None
  send_email = None
  reply_email = None


@pytest.fixture
def mock_ctx():
  """Create a mock MCP Context."""
  ctx = MagicMock()
  ctx.info = AsyncMock()
  return ctx


class TestCreateFolderTool:
  """Tests for create_folder MCP tool."""

  @pytest.mark.asyncio
  async def test_create_folder_tool_success(self, mock_ctx):
    """
    Given: Valid account and folder name
    When: create_folder tool is called
    Then: Returns {"status": "created", "folder": folder_name}
    """
    if create_folder is None:
      pytest.fail("Not implemented: create_folder tool returns success dict")

    with (
      patch("simple_email_gw.mcp.get_pool") as mock_get_pool,
      patch("simple_email_gw.mcp.log_event") as mock_log,
    ):
      pool = AsyncMock()
      client = AsyncMock()
      client.create_folder = AsyncMock(return_value=True)
      pool.get_imap_client = AsyncMock(return_value=client)
      mock_get_pool.return_value = pool

      result = await create_folder(account="test", folder_name="Sent", ctx=mock_ctx)

      assert result == {"status": "created", "folder": "Sent"}
      client.create_folder.assert_called_once_with("Sent")
      mock_log.assert_called_once_with(
        event="FOLDER_CREATED",
        account="test",
        details={"folder": "Sent"},
      )

  @pytest.mark.asyncio
  async def test_create_folder_tool_account_not_found(self, mock_ctx):
    """
    Given: Account name that does not exist in configuration
    When: create_folder tool is called
    Then: Raises ToolError with account not found message
    """
    if create_folder is None:
      pytest.fail("Not implemented: create_folder tool raises ToolError for missing account")

    with patch("simple_email_gw.mcp.get_pool") as mock_get_pool:
      pool = AsyncMock()
      pool.get_imap_client = AsyncMock(side_effect=ValueError("Account not found: missing"))
      mock_get_pool.return_value = pool

      with pytest.raises(ToolError, match="Account not found"):
        await create_folder(account="missing", folder_name="Sent", ctx=mock_ctx)

  @pytest.mark.asyncio
  async def test_create_folder_tool_rate_limited(self, mock_ctx):
    """
    Given: Rate limit exceeded for the account
    When: create_folder tool is called
    Then: Raises ToolError with rate limit message
    """
    if create_folder is None:
      pytest.fail("Not implemented: create_folder tool raises ToolError when rate limited")

    with patch("simple_email_gw.mcp.get_pool") as mock_get_pool:
      pool = AsyncMock()
      pool.get_imap_client = AsyncMock(side_effect=RateLimitError("Rate limit exceeded"))
      mock_get_pool.return_value = pool

      with pytest.raises(ToolError, match="Rate limit exceeded"):
        await create_folder(account="test", folder_name="Sent", ctx=mock_ctx)

  @pytest.mark.asyncio
  async def test_create_folder_tool_logs_via_ctx(self, mock_ctx):
    """
    Given: MCP Context is provided
    When: create_folder tool is called
    Then: Logs operation via ctx.info
    """
    if create_folder is None:
      pytest.fail("Not implemented: create_folder tool logs via ctx.info")

    with (
      patch("simple_email_gw.mcp.get_pool") as mock_get_pool,
      patch("simple_email_gw.mcp.log_event"),
    ):
      pool = AsyncMock()
      client = AsyncMock()
      client.create_folder = AsyncMock(return_value=True)
      pool.get_imap_client = AsyncMock(return_value=client)
      mock_get_pool.return_value = pool

      await create_folder(account="test", folder_name="Sent", ctx=mock_ctx)

      mock_ctx.info.assert_called_once()

  @pytest.mark.asyncio
  async def test_create_folder_tool_propagates_sanitization_error(self, mock_ctx):
    """
    Given: Folder name failing client-side validation (e.g., empty after strip)
    When: create_folder tool is called
    Then: Raises ToolError with empty name message
    """
    if create_folder is None:
      pytest.fail("Not implemented: create_folder tool propagates sanitization ValueError")

    with pytest.raises(ToolError, match="cannot be empty"):
      await create_folder(account="test", folder_name="", ctx=mock_ctx)
    with pytest.raises(ToolError, match="cannot be empty"):
      await create_folder(account="test", folder_name="   ", ctx=mock_ctx)

  @pytest.mark.asyncio
  async def test_create_folder_tool_rejects_quote_in_name(self, mock_ctx):
    """
    Given: Folder name containing double quotes
    When: create_folder tool is called
    Then: Raises ToolError with invalid characters message
    """
    if create_folder is None:
      pytest.fail("Not implemented: create_folder tool rejects quotes in folder name")

    with pytest.raises(ToolError, match="invalid characters"):
      await create_folder(account="test", folder_name='Sent"Bad', ctx=mock_ctx)
    with pytest.raises(ToolError, match="invalid characters"):
      await create_folder(account="test", folder_name="Sent\\Bad", ctx=mock_ctx)

  @pytest.mark.asyncio
  async def test_create_folder_tool_rejects_inbox_name(self, mock_ctx):
    """
    Given: Folder name matching INBOX case-insensitively
    When: create_folder tool is called
    Then: Raises ToolError with reserved name message
    """
    if create_folder is None:
      pytest.fail("Not implemented: create_folder tool rejects INBOX name")

    with pytest.raises(ToolError, match="reserved folder name"):
      await create_folder(account="test", folder_name="inbox", ctx=mock_ctx)
    with pytest.raises(ToolError, match="reserved folder name"):
      await create_folder(account="test", folder_name="INBOX", ctx=mock_ctx)

  @pytest.mark.asyncio
  async def test_create_folder_tool_rejects_traversal(self, mock_ctx):
    """
    Given: Folder name containing path traversal (..)
    When: create_folder tool is called
    Then: Raises ToolError with invalid folder name message
    """
    if create_folder is None:
      pytest.fail("Not implemented: create_folder tool rejects path traversal")

    with pytest.raises(ToolError, match="Invalid folder name"):
      await create_folder(account="test", folder_name="../Bad", ctx=mock_ctx)
    with pytest.raises(ToolError, match="Invalid folder name"):
      await create_folder(account="test", folder_name="foo/../bar", ctx=mock_ctx)

  @pytest.mark.asyncio
  async def test_create_folder_tool_calls_audit_log(self, mock_ctx):
    """
    Given: Valid account and folder name
    When: create_folder tool succeeds
    Then: Calls audit log with FOLDER_CREATED event
    """
    if create_folder is None:
      pytest.fail("Not implemented: create_folder tool calls audit log")

    with (
      patch("simple_email_gw.mcp.get_pool") as mock_get_pool,
      patch("simple_email_gw.mcp.log_event") as mock_log,
    ):
      pool = AsyncMock()
      client = AsyncMock()
      client.create_folder = AsyncMock(return_value=True)
      pool.get_imap_client = AsyncMock(return_value=client)
      mock_get_pool.return_value = pool

      await create_folder(account="test", folder_name="Sent", ctx=mock_ctx)

      mock_log.assert_called_once_with(
        event="FOLDER_CREATED",
        account="test",
        details={"folder": "Sent"},
      )

  @pytest.mark.asyncio
  async def test_create_folder_tool_already_exists(self, mock_ctx):
    """
    Given: Folder already exists on the server
    When: create_folder tool is called
    Then: Raises ToolError with folder already exists message
    """
    if create_folder is None:
      pytest.fail("Not implemented: create_folder tool maps ALREADYEXISTS to ToolError")

    with patch("simple_email_gw.mcp.get_pool") as mock_get_pool:
      pool = AsyncMock()
      client = AsyncMock()
      client.create_folder = AsyncMock(side_effect=RuntimeError("Folder already exists"))
      pool.get_imap_client = AsyncMock(return_value=client)
      mock_get_pool.return_value = pool

      with pytest.raises(ToolError, match="already exists"):
        await create_folder(account="test", folder_name="Sent", ctx=mock_ctx)

  @pytest.mark.asyncio
  async def test_create_folder_tool_permission_denied(self, mock_ctx):
    """
    Given: Server returns permission denied (NOPERM)
    When: create_folder tool is called
    Then: Raises ToolError with generic failure message
    """
    if create_folder is None:
      pytest.fail("Not implemented: create_folder tool maps NOPERM to ToolError")

    with patch("simple_email_gw.mcp.get_pool") as mock_get_pool:
      pool = AsyncMock()
      client = AsyncMock()
      client.create_folder = AsyncMock(
        side_effect=RuntimeError("Failed to create folder. Check server logs for details.")
      )
      pool.get_imap_client = AsyncMock(return_value=client)
      mock_get_pool.return_value = pool

      with pytest.raises(ToolError, match="Failed to create folder"):
        await create_folder(account="test", folder_name="Sent", ctx=mock_ctx)

  @pytest.mark.asyncio
  async def test_create_folder_tool_rejects_too_long(self, mock_ctx):
    """
    Given: Folder name longer than 255 bytes
    When: create_folder tool is called
    Then: Raises ToolError with maximum length message
    """
    if create_folder is None:
      pytest.fail("Not implemented: create_folder tool rejects too long folder name")

    long_name = "x" * 256
    with pytest.raises(ToolError, match="exceeds maximum length"):
      await create_folder(account="test", folder_name=long_name, ctx=mock_ctx)

  @pytest.mark.asyncio
  async def test_create_folder_tool_rejects_leading_delimiter(self, mock_ctx):
    """
    Given: Folder name starting with '/' or '.'
    When: create_folder tool is called
    Then: Raises ToolError with invalid folder name message
    """
    if create_folder is None:
      pytest.fail("Not implemented: create_folder tool rejects leading delimiter")

    with pytest.raises(ToolError, match="Invalid folder name"):
      await create_folder(account="test", folder_name="/Absolute", ctx=mock_ctx)
    with pytest.raises(ToolError, match="Invalid folder name"):
      await create_folder(account="test", folder_name=".Absolute", ctx=mock_ctx)

  @pytest.mark.asyncio
  async def test_create_folder_tool_rejects_deep_nesting(self, mock_ctx):
    """
    Given: Folder name with more than 10 nesting levels
    When: create_folder tool is called
    Then: Raises ToolError with maximum depth message
    """
    if create_folder is None:
      pytest.fail("Not implemented: create_folder tool rejects deep nesting")

    deep_name = "/".join([f"level{i}" for i in range(11)])
    with pytest.raises(ToolError, match="exceeds maximum depth"):
      await create_folder(account="test", folder_name=deep_name, ctx=mock_ctx)
    deep_dot = ".".join([f"level{i}" for i in range(11)])
    with pytest.raises(ToolError, match="exceeds maximum depth"):
      await create_folder(account="test", folder_name=deep_dot, ctx=mock_ctx)

  @pytest.mark.asyncio
  async def test_create_folder_tool_rejects_crlf(self, mock_ctx):
    """
    Given: Folder name containing CR or LF characters
    When: create_folder tool is called
    Then: Raises ToolError with invalid characters message
    """
    if create_folder is None:
      pytest.fail("Not implemented: create_folder tool rejects CRLF in folder name")

    with pytest.raises(ToolError, match="invalid characters"):
      await create_folder(account="test", folder_name="Bad\r\nFolder", ctx=mock_ctx)
    with pytest.raises(ToolError, match="invalid characters"):
      await create_folder(account="test", folder_name="Bad\nFolder", ctx=mock_ctx)


class TestAppendEmailTool:
  """Tests for append_email MCP tool."""

  def _make_raw_message(self) -> str:
    """Return a base64-encoded RFC822 message."""
    msg = (
      b"From: sender@example.com\r\n"
      b"To: recipient@example.com\r\n"
      b"Subject: Test\r\n"
      b"Message-ID: <msg123@example.com>\r\n"
      b"\r\n"
      b"Hello"
    )
    return base64.b64encode(msg).decode("ascii")

  def _make_raw_message_with_header(self, header_name: str, header_value: str) -> str:
    """Return a base64-encoded RFC822 message with a folded address header.

    The continuation whitespace keeps the injected CRLF inside the parsed
    header value, which the tool must reject.
    """
    msg = (
      f"{header_name}: {header_value}\r\n"
      "Subject: Test\r\n"
      "Message-ID: <msg123@example.com>\r\n"
      "\r\n"
      "Body"
    )
    return base64.b64encode(msg.encode("utf-8")).decode("ascii")

  @pytest.mark.asyncio
  async def test_append_email_tool_success(self, mock_ctx):
    """
    Given: Valid account, folder, message, and flags
    When: append_email tool is called
    Then: Returns appended status and folder
    """
    if append_email is None:
      pytest.fail("Not implemented: append_email tool")

    with patch("simple_email_gw.mcp.get_pool") as mock_get_pool:
      pool = AsyncMock()
      client = AsyncMock()
      client.append_message = AsyncMock(return_value={"status": "appended", "folder": "Sent"})
      pool.get_imap_client = AsyncMock(return_value=client)
      mock_get_pool.return_value = pool

      raw = self._make_raw_message()
      result = await append_email(account="test", folder="Sent", raw_message=raw, ctx=mock_ctx)

      assert result == {"status": "appended", "folder": "Sent"}
      client.append_message.assert_awaited_once()

  @pytest.mark.asyncio
  async def test_append_email_tool_account_not_found(self, mock_ctx):
    """
    Given: Unknown account
    When: append_email tool is called
    Then: Raises ToolError for account not found
    """
    if append_email is None:
      pytest.fail("Not implemented: append_email tool")

    with patch("simple_email_gw.mcp.get_pool") as mock_get_pool:
      pool = AsyncMock()
      pool.get_imap_client = AsyncMock(side_effect=ValueError("Account not found: missing"))
      mock_get_pool.return_value = pool

      raw = self._make_raw_message()
      with pytest.raises(ToolError, match="Account not found"):
        await append_email(account="missing", folder="Sent", raw_message=raw, ctx=mock_ctx)

  @pytest.mark.asyncio
  async def test_append_email_tool_invalid_folder(self, mock_ctx):
    """
    Given: Folder name with CRLF injection
    When: append_email tool is called
    Then: Raises ToolError
    """
    if append_email is None:
      pytest.fail("Not implemented: append_email tool")

    raw = self._make_raw_message()
    with pytest.raises(ToolError, match="invalid characters"):
      await append_email(account="test", folder="Bad\r\nFolder", raw_message=raw, ctx=mock_ctx)

  @pytest.mark.asyncio
  async def test_append_email_tool_invalid_flags(self, mock_ctx):
    """
    Given: Flag outside allowlist
    When: append_email tool is called
    Then: Raises ToolError
    """
    if append_email is None:
      pytest.fail("Not implemented: append_email tool")

    raw = self._make_raw_message()
    with pytest.raises(ToolError, match="Invalid IMAP flag"):
      await append_email(
        account="test",
        folder="Sent",
        raw_message=raw,
        flags=["\\Deleted"],
        ctx=mock_ctx,
      )

  @pytest.mark.asyncio
  async def test_append_email_tool_rejects_invalid_base64(self, mock_ctx):
    """
    Given: Invalid base64 input
    When: append_email tool is called
    Then: Raises ToolError
    """
    if append_email is None:
      pytest.fail("Not implemented: append_email tool")

    with pytest.raises(ToolError, match="Invalid message content"):
      await append_email(account="test", folder="Sent", raw_message="not-base64!!!", ctx=mock_ctx)

  @pytest.mark.asyncio
  async def test_append_email_tool_rejects_oversized(self, mock_ctx, monkeypatch):
    """
    Given: Message exceeding max size
    When: append_email tool is called
    Then: Raises ToolError
    """
    if append_email is None:
      pytest.fail("Not implemented: append_email tool")

    monkeypatch.setenv("EMAIL_APPEND_MAX_SIZE", "10")
    raw = base64.b64encode(b"x" * 20).decode("ascii")
    with pytest.raises(ToolError, match="exceeds maximum size"):
      await append_email(account="test", folder="Sent", raw_message=raw, ctx=mock_ctx)

  @pytest.mark.asyncio
  async def test_append_email_tool_rejects_invalid_message_id(self, mock_ctx):
    """
    Given: Message with an invalid/injected Message-ID
    When: append_email tool is called
    Then: Raises ToolError during header sanitization
    """
    if append_email is None:
      pytest.fail("Not implemented: append_email tool")

    msg = (
      b"From: sender@example.com\r\n"
      b"To: recipient@example.com\r\n"
      b"Subject: Test\r\n"
      b"Message-ID: evil\r\nBcc: attacker@evil.com\r\n"
      b"\r\n"
      b"Body"
    )
    raw = base64.b64encode(msg).decode("ascii")
    with pytest.raises(ToolError, match="Invalid message content"):
      await append_email(account="test", folder="Sent", raw_message=raw, ctx=mock_ctx)

  @pytest.mark.asyncio
  async def test_append_email_tool_rejects_crlf_in_from(self, mock_ctx):
    """CRLF injection in the From header is rejected."""
    if append_email is None:
      pytest.fail("Not implemented: append_email tool")

    raw = self._make_raw_message_with_header(
      "From", "sender@example.com\r\n Bcc: attacker@evil.com"
    )
    with pytest.raises(ToolError, match="Invalid message content"):
      await append_email(account="test", folder="Sent", raw_message=raw, ctx=mock_ctx)

  @pytest.mark.asyncio
  async def test_append_email_tool_rejects_crlf_in_to(self, mock_ctx):
    """CRLF injection in the To header is rejected."""
    if append_email is None:
      pytest.fail("Not implemented: append_email tool")

    raw = self._make_raw_message_with_header(
      "To", "recipient@example.com\r\n Bcc: attacker@evil.com"
    )
    with pytest.raises(ToolError, match="Invalid message content"):
      await append_email(account="test", folder="Sent", raw_message=raw, ctx=mock_ctx)

  @pytest.mark.asyncio
  async def test_append_email_tool_rejects_crlf_in_cc(self, mock_ctx):
    """CRLF injection in the Cc header is rejected."""
    if append_email is None:
      pytest.fail("Not implemented: append_email tool")

    raw = self._make_raw_message_with_header("Cc", "cc@example.com\r\n Bcc: attacker@evil.com")
    with pytest.raises(ToolError, match="Invalid message content"):
      await append_email(account="test", folder="Sent", raw_message=raw, ctx=mock_ctx)

  @pytest.mark.asyncio
  async def test_append_email_tool_rejects_crlf_in_bcc(self, mock_ctx):
    """CRLF injection in the Bcc header is rejected."""
    if append_email is None:
      pytest.fail("Not implemented: append_email tool")

    raw = self._make_raw_message_with_header("Bcc", "bcc@example.com\r\n X-Injected: evil")
    with pytest.raises(ToolError, match="Invalid message content"):
      await append_email(account="test", folder="Sent", raw_message=raw, ctx=mock_ctx)


class TestSendEmailTool:
  """Tests for updated send_email MCP tool."""

  @pytest.mark.asyncio
  async def test_send_email_tool_passes_append_params(self, mock_ctx):
    """
    Given: append_to_sent=True and append_folder
    When: send_email tool is called
    Then: Both SMTP and IMAP clients are obtained and params forwarded
    """
    if send_email is None:
      pytest.fail("Not implemented: send_email tool")

    with patch("simple_email_gw.mcp.get_pool") as mock_get_pool:
      pool = AsyncMock()
      smtp_client = AsyncMock()
      imap_client = AsyncMock()
      smtp_client.send_email = AsyncMock(
        return_value={
          "status": "sent",
          "recipients": "to@example.com",
          "message": "OK",
          "appended": True,
          "append_folder": "Sent",
          "append_warning": None,
        }
      )
      pool.get_smtp_client = AsyncMock(return_value=smtp_client)
      pool.get_imap_client = AsyncMock(return_value=imap_client)
      mock_get_pool.return_value = pool

      result = await send_email(
        account="test",
        to=["to@example.com"],
        subject="Test",
        body="Hello",
        append_to_sent=True,
        append_folder="Sent",
        ctx=mock_ctx,
      )

      assert result["appended"] is True
      assert result["append_folder"] == "Sent"
      smtp_client.send_email.assert_awaited_once()
      call = smtp_client.send_email.call_args
      assert call.kwargs["append_to_sent"] is True
      assert call.kwargs["append_folder"] == "Sent"
      assert call.kwargs["imap_client"] is imap_client

  @pytest.mark.asyncio
  async def test_send_email_tool_rejects_invalid_append_folder(self, mock_ctx):
    """
    Given: append_folder containing CRLF injection
    When: send_email tool is called
    Then: Raises ToolError before contacting the SMTP client
    """
    if send_email is None:
      pytest.fail("Not implemented: send_email tool")

    with pytest.raises(ToolError, match="invalid characters"):
      await send_email(
        account="test",
        to=["to@example.com"],
        subject="Test",
        body="Hello",
        append_to_sent=True,
        append_folder="Bad\r\nFolder",
        ctx=mock_ctx,
      )


class TestReplyEmailTool:
  """Tests for updated reply_email MCP tool."""

  @pytest.mark.asyncio
  async def test_reply_email_tool_passes_append_params(self, mock_ctx):
    """
    Given: append_to_sent=True
    When: reply_email tool is called
    Then: IMAP client is forwarded to SMTP client
    """
    if reply_email is None:
      pytest.fail("Not implemented: reply_email tool")

    with patch("simple_email_gw.mcp.get_pool") as mock_get_pool:
      pool = AsyncMock()
      smtp_client = AsyncMock()
      imap_client = AsyncMock()
      smtp_client.reply_email = AsyncMock(
        return_value={
          "status": "sent",
          "recipients": "to@example.com",
          "message": "OK",
          "appended": False,
          "append_folder": None,
          "append_warning": "Sent folder not found",
        }
      )
      pool.get_smtp_client = AsyncMock(return_value=smtp_client)
      pool.get_imap_client = AsyncMock(return_value=imap_client)
      mock_get_pool.return_value = pool

      result = await reply_email(
        account="test",
        to="to@example.com",
        subject="Re: Test",
        body="Reply",
        in_reply_to="<original@example.com>",
        append_to_sent=True,
        ctx=mock_ctx,
      )

      assert result["status"] == "sent"
      assert result["append_warning"] == "Sent folder not found"
      smtp_client.reply_email.assert_awaited_once()
      call = smtp_client.reply_email.call_args
      assert call.kwargs["append_to_sent"] is True
      assert call.kwargs["imap_client"] is imap_client

  @pytest.mark.asyncio
  async def test_reply_email_tool_rejects_invalid_append_folder(self, mock_ctx):
    """
    Given: append_folder containing CRLF injection
    When: reply_email tool is called
    Then: Raises ToolError before contacting the SMTP client
    """
    if reply_email is None:
      pytest.fail("Not implemented: reply_email tool")

    with pytest.raises(ToolError, match="invalid characters"):
      await reply_email(
        account="test",
        to="to@example.com",
        subject="Re: Test",
        body="Reply",
        in_reply_to="<original@example.com>",
        append_to_sent=True,
        append_folder="Bad\r\nFolder",
        ctx=mock_ctx,
      )
