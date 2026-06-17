"""Tests for async IMAPClient.

These tests verify the async IMAPClient directly, including message parsing
and threading header extraction.
"""

from unittest.mock import AsyncMock, patch

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


class TestCreateFolder:
  """Tests for IMAPClient.create_folder method."""

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
  async def test_create_folder_success(self, account):
    """
    Given: A valid folder name and IMAP server returns OK to CREATE
    When: create_folder() is called
    Then: Returns True and issues CREATE command with sanitized name
    """
    client = IMAPClient(account)
    mock_imap = AsyncMock()
    mock_imap.create = AsyncMock(return_value=("OK", [b"Created"]))

    with patch.object(client, "connect", new_callable=AsyncMock) as mock_connect:
      mock_connect.return_value = mock_imap
      result = await client.create_folder("Archive")

    assert result is True
    mock_imap.create.assert_called_once_with("Archive")

  @pytest.mark.asyncio
  async def test_create_folder_sanitization_rejects_crlf(self, account):
    """
    Given: Folder name containing CR or LF characters
    When: create_folder() is called
    Then: Raises ValueError before issuing any IMAP command
    """
    client = IMAPClient(account)
    with pytest.raises(ValueError, match="invalid characters"):
      await client.create_folder("Bad\r\nFolder")

  @pytest.mark.asyncio
  async def test_create_folder_rejects_quotes_and_backslashes(self, account):
    """
    Given: Folder name containing double quotes or backslashes
    When: create_folder() is called
    Then: Raises ValueError before issuing any IMAP command
    """
    client = IMAPClient(account)
    with pytest.raises(ValueError, match="invalid characters"):
      await client.create_folder('Bad"Folder')
    with pytest.raises(ValueError, match="invalid characters"):
      await client.create_folder("Bad\\Folder")

  @pytest.mark.asyncio
  async def test_create_folder_rejects_path_traversal(self, account):
    """
    Given: Folder name containing '..' in path components
    When: create_folder() is called
    Then: Raises ValueError before issuing any IMAP command
    """
    client = IMAPClient(account)
    with pytest.raises(ValueError, match="Invalid folder name"):
      await client.create_folder("../Other")
    with pytest.raises(ValueError, match="Invalid folder name"):
      await client.create_folder("foo/../bar")

  @pytest.mark.asyncio
  async def test_create_folder_rejects_leading_delimiter(self, account):
    """
    Given: Folder name starting with '/' or '.'
    When: create_folder() is called
    Then: Raises ValueError before issuing any IMAP command
    """
    client = IMAPClient(account)
    with pytest.raises(ValueError, match="Invalid folder name"):
      await client.create_folder("/Absolute")
    with pytest.raises(ValueError, match="Invalid folder name"):
      await client.create_folder(".Absolute")

  @pytest.mark.asyncio
  async def test_create_folder_rejects_inbox(self, account):
    """
    Given: Folder name that is a case-insensitive match for 'INBOX'
    When: create_folder() is called
    Then: Raises ValueError before issuing any IMAP command
    """
    client = IMAPClient(account)
    with pytest.raises(ValueError, match="reserved folder name"):
      await client.create_folder("INBOX")
    with pytest.raises(ValueError, match="reserved folder name"):
      await client.create_folder("inbox")
    with pytest.raises(ValueError, match="reserved folder name"):
      await client.create_folder("Inbox")

  @pytest.mark.asyncio
  async def test_create_folder_rejects_empty_name(self, account):
    """
    Given: Empty folder name
    When: create_folder() is called
    Then: Raises ValueError before issuing any IMAP command
    """
    client = IMAPClient(account)
    with pytest.raises(ValueError, match="cannot be empty"):
      await client.create_folder("")
    with pytest.raises(ValueError, match="cannot be empty"):
      await client.create_folder("   ")

  @pytest.mark.asyncio
  async def test_create_folder_rejects_deep_nesting(self, account):
    """
    Given: Folder name with more than 10 nesting levels
    When: create_folder() is called
    Then: Raises ValueError before issuing any IMAP command
    """
    client = IMAPClient(account)
    deep_name = "/".join([f"level{i}" for i in range(11)])
    with pytest.raises(ValueError, match="exceeds maximum depth"):
      await client.create_folder(deep_name)
    deep_dot = ".".join([f"level{i}" for i in range(11)])
    with pytest.raises(ValueError, match="exceeds maximum depth"):
      await client.create_folder(deep_dot)

  @pytest.mark.asyncio
  async def test_create_folder_rejects_too_long(self, account):
    """
    Given: Folder name longer than 255 bytes
    When: create_folder() is called
    Then: Raises ValueError before issuing any IMAP command
    """
    client = IMAPClient(account)
    long_name = "x" * 256
    with pytest.raises(ValueError, match="exceeds maximum length"):
      await client.create_folder(long_name)

  @pytest.mark.asyncio
  async def test_create_folder_already_exists(self, account):
    """
    Given: Folder name that already exists on server
    When: create_folder() is called
    Then: Raises RuntimeError with 'Folder already exists' message
    """
    client = IMAPClient(account)
    mock_imap = AsyncMock()
    mock_imap.create = AsyncMock(return_value=("NO", [b"[ALREADYEXISTS] Mailbox already exists"]))

    with patch.object(client, "connect", new_callable=AsyncMock) as mock_connect:
      mock_connect.return_value = mock_imap
      with pytest.raises(RuntimeError, match="already exists"):
        await client.create_folder("Sent")

  @pytest.mark.asyncio
  async def test_create_folder_permission_denied(self, account):
    """
    Given: Server returns NO [NOPERM] to CREATE
    When: create_folder() is called
    Then: Raises RuntimeError with generic failure message
    """
    client = IMAPClient(account)
    mock_imap = AsyncMock()
    mock_imap.create = AsyncMock(return_value=("NO", [b"[NOPERM] Permission denied"]))

    with patch.object(client, "connect", new_callable=AsyncMock) as mock_connect:
      mock_connect.return_value = mock_imap
      with pytest.raises(RuntimeError, match="Failed to create folder"):
        await client.create_folder("Sent")

  @pytest.mark.asyncio
  async def test_create_folder_quota_exceeded(self, account):
    """
    Given: Server returns NO [OVERQUOTA] to CREATE
    When: create_folder() is called
    Then: Raises RuntimeError with quota exceeded message
    """
    client = IMAPClient(account)
    mock_imap = AsyncMock()
    mock_imap.create = AsyncMock(return_value=("NO", [b"[OVERQUOTA] Mailbox quota exceeded"]))

    with patch.object(client, "connect", new_callable=AsyncMock) as mock_connect:
      mock_connect.return_value = mock_imap
      with pytest.raises(RuntimeError, match="Mailbox quota exceeded"):
        await client.create_folder("Sent")

  @pytest.mark.asyncio
  async def test_create_folder_generic_no_response(self, account):
    """
    Given: Server returns generic NO response to CREATE
    When: create_folder() is called
    Then: Raises RuntimeError with generic failure message
    """
    client = IMAPClient(account)
    mock_imap = AsyncMock()
    mock_imap.create = AsyncMock(return_value=("NO", []))

    with patch.object(client, "connect", new_callable=AsyncMock) as mock_connect:
      mock_connect.return_value = mock_imap
      with pytest.raises(RuntimeError, match="Failed to create folder"):
        await client.create_folder("Sent")

  @pytest.mark.asyncio
  async def test_create_folder_uses_operation_lock(self, account):
    """
    Given: Multiple concurrent calls to create_folder()
    When: create_folder() is executing
    Then: Operations are serialized via _operation_lock
    """
    client = IMAPClient(account)
    lock_acquired = False

    original_acquire = client._operation_lock.acquire

    async def tracked_acquire():
      nonlocal lock_acquired
      lock_acquired = True
      return await original_acquire()

    with patch.object(client._operation_lock, "acquire", side_effect=tracked_acquire):
      mock_imap = AsyncMock()
      mock_imap.create = AsyncMock(return_value=("OK", [b"Created"]))
      with patch.object(client, "connect", new_callable=AsyncMock) as mock_connect:
        mock_connect.return_value = mock_imap
        await client.create_folder("Test")

    assert lock_acquired is True


class TestFindSentFolder:
  """Tests for IMAPClient.find_sent_folder method."""

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
  async def test_find_sent_folder_by_special_use_flag(self, account):
    """Sent folder is detected via the \\Sent special-use flag."""
    client = IMAPClient(account)
    with patch.object(client, "list_folders", new_callable=AsyncMock) as mock_list:
      mock_list.return_value = [
        {"name": "INBOX", "flags": ["\\HasNoChildren"]},
        {"name": "Sent Items", "flags": ["\\Sent", "\\HasNoChildren"]},
      ]
      result = await client.find_sent_folder()

    assert result == "Sent Items"

  @pytest.mark.asyncio
  async def test_find_sent_folder_special_use_case_insensitive(self, account):
    """Sent detection is case-insensitive for the flag name."""
    client = IMAPClient(account)
    with patch.object(client, "list_folders", new_callable=AsyncMock) as mock_list:
      mock_list.return_value = [
        {"name": "INBOX", "flags": ["\\HasNoChildren"]},
        {"name": "Sent", "flags": ["\\sent"]},
      ]
      result = await client.find_sent_folder()

    assert result == "Sent"

  @pytest.mark.asyncio
  async def test_find_sent_folder_fallback_order(self, account):
    """When no \\Sent flag exists, fallback names are tried in order."""
    client = IMAPClient(account)
    with patch.object(client, "list_folders", new_callable=AsyncMock) as mock_list:
      mock_list.return_value = [
        {"name": "INBOX", "flags": []},
        {"name": "Sent Messages", "flags": []},
      ]
      result = await client.find_sent_folder()

    assert result == "Sent Messages"

  @pytest.mark.asyncio
  async def test_find_sent_folder_returns_none_when_missing(self, account):
    """When no Sent candidate exists, return None."""
    client = IMAPClient(account)
    with patch.object(client, "list_folders", new_callable=AsyncMock) as mock_list:
      mock_list.return_value = [{"name": "INBOX", "flags": []}]
      result = await client.find_sent_folder()

    assert result is None


class TestAppendMessage:
  """Tests for IMAPClient.append_message method."""

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
  async def test_append_message_success(self, account):
    """A valid append returns the appended status and folder."""
    client = IMAPClient(account)
    mock_imap = AsyncMock()
    mock_imap.append = AsyncMock(return_value=("OK", []))

    message_bytes = (
      b"From: sender@example.com\r\n"
      b"To: recipient@example.com\r\n"
      b"Subject: Test\r\n"
      b"Message-ID: <msg123@example.com>\r\n"
      b"\r\n"
      b"Body"
    )

    with patch.object(client, "connect", new_callable=AsyncMock) as mock_connect:
      mock_connect.return_value = mock_imap
      with patch("simple_email_gw.imap.client.log_email_appended") as mock_log:
        result = await client.append_message("Sent", message_bytes, flags=["\\Seen"])

    assert result == {"status": "appended", "folder": "Sent"}
    mock_imap.append.assert_awaited_once()
    append_call = mock_imap.append.call_args
    assert append_call.kwargs["mailbox"] == "Sent"
    assert append_call.kwargs["flags"] == "(\\Seen)"
    assert append_call.args[0] == message_bytes
    mock_log.assert_called_once()
    assert mock_log.call_args.kwargs["success"] is True

  @pytest.mark.asyncio
  async def test_append_message_rejects_invalid_folder(self, account):
    """Invalid folder names raise ValueError before APPEND."""
    client = IMAPClient(account)
    with pytest.raises(ValueError, match="invalid characters"):
      await client.append_message("Bad\r\nFolder", b"body")

  @pytest.mark.asyncio
  async def test_append_message_rejects_invalid_flags(self, account):
    """Flags outside the allowlist raise ValueError."""
    client = IMAPClient(account)
    with pytest.raises(ValueError, match="Invalid IMAP flag"):
      await client.append_message("Sent", b"body", flags=["\\Deleted"])

  @pytest.mark.asyncio
  async def test_append_message_rejects_nul_bytes(self, account):
    """Messages containing NUL bytes are rejected."""
    client = IMAPClient(account)
    with pytest.raises(ValueError, match="NUL"):
      await client.append_message("Sent", b"\x00body")

  @pytest.mark.asyncio
  async def test_append_message_rejects_oversized(self, account, monkeypatch):
    """Messages exceeding the configured max size are rejected."""
    monkeypatch.setenv("EMAIL_APPEND_MAX_SIZE", "10")
    client = IMAPClient(account)
    with pytest.raises(ValueError, match="exceeds maximum size"):
      await client.append_message("Sent", b"x" * 11)

  @pytest.mark.asyncio
  async def test_append_message_rejects_naive_internal_date(self, account):
    """internal_date must be timezone-aware."""
    from datetime import datetime

    client = IMAPClient(account)
    with pytest.raises(ValueError, match="timezone-aware"):
      await client.append_message("Sent", b"body", internal_date=datetime.now())

  @pytest.mark.asyncio
  async def test_append_message_maps_overquota(self, account):
    """[OVERQUOTA] response is mapped to a generic quota message."""
    client = IMAPClient(account)
    mock_imap = AsyncMock()
    mock_imap.append = AsyncMock(return_value=("NO", [b"[OVERQUOTA] Mailbox full"]))

    with patch.object(client, "connect", new_callable=AsyncMock) as mock_connect:
      mock_connect.return_value = mock_imap
      with pytest.raises(RuntimeError, match="Mailbox quota exceeded"):
        await client.append_message("Sent", b"body")

  @pytest.mark.asyncio
  async def test_append_message_maps_noperm(self, account):
    """[NOPERM] response is mapped to a generic permission message."""
    client = IMAPClient(account)
    mock_imap = AsyncMock()
    mock_imap.append = AsyncMock(return_value=("NO", [b"[NOPERM] Permission denied"]))

    with patch.object(client, "connect", new_callable=AsyncMock) as mock_connect:
      mock_connect.return_value = mock_imap
      with pytest.raises(RuntimeError, match="Permission denied"):
        await client.append_message("Sent", b"body")

  @pytest.mark.asyncio
  async def test_append_message_maps_trycreate(self, account):
    """[TRYCREATE] response is mapped to a folder-not-found message."""
    client = IMAPClient(account)
    mock_imap = AsyncMock()
    mock_imap.append = AsyncMock(return_value=("NO", [b"[TRYCREATE] Folder missing"]))

    with patch.object(client, "connect", new_callable=AsyncMock) as mock_connect:
      mock_connect.return_value = mock_imap
      with pytest.raises(RuntimeError, match="Folder does not exist"):
        await client.append_message("Sent", b"body")

  @pytest.mark.asyncio
  async def test_append_message_generic_error(self, account):
    """Generic NO response is mapped to a generic failure message."""
    client = IMAPClient(account)
    mock_imap = AsyncMock()
    mock_imap.append = AsyncMock(return_value=("NO", []))

    with patch.object(client, "connect", new_callable=AsyncMock) as mock_connect:
      mock_connect.return_value = mock_imap
      with pytest.raises(RuntimeError, match="Failed to append message"):
        await client.append_message("Sent", b"body")

  @pytest.mark.asyncio
  async def test_append_message_uses_operation_lock(self, account):
    """append_message serializes via the operation lock."""
    client = IMAPClient(account)
    lock_acquired = False

    original_acquire = client._operation_lock.acquire

    async def tracked_acquire():
      nonlocal lock_acquired
      lock_acquired = True
      return await original_acquire()

    with patch.object(client._operation_lock, "acquire", side_effect=tracked_acquire):
      mock_imap = AsyncMock()
      mock_imap.append = AsyncMock(return_value=("OK", []))
      with patch.object(client, "connect", new_callable=AsyncMock) as mock_connect:
        mock_connect.return_value = mock_imap
        await client.append_message("Sent", b"body")

    assert lock_acquired is True
