"""Tests for MCP tools.

These tests verify the MCP tool wrappers, including:
- Tool delegation to async clients
- Error mapping to ToolError
- Context logging via ctx.info
- Rate limiting and account validation
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastmcp.exceptions import ToolError

from simple_email_gw.connections.pool import RateLimitError

try:
  from simple_email_gw.mcp import create_folder
except ImportError:
  create_folder = None


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
