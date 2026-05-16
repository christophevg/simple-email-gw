"""Tests for SyncIMAPClient wrapper.

These tests verify the synchronous wrapper around async IMAPClient.
Tests verify:
- Context manager entry/exit
- All public methods delegate correctly to async client
- Connection lifecycle (connect/disconnect)
- Error handling (timeouts, connection errors wrapped in RuntimeError)
- Thread safety and cleanup
- No resource leaks on exception
"""

import threading
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aioimaplib import IMAP4_SSL

from simple_email_gw.config import EmailAccount
from simple_email_gw.imap.client import IMAPClient
from simple_email_gw.imap.sync_client import SyncIMAPClient


class TestSyncIMAPClientContextManager:
  """Test context manager functionality."""

  def test_context_manager_entry_returns_self(self):
    """
    Given: SyncIMAPClient instance
    When: Using context manager entry (__enter__)
    Then: Returns self
    """
    account = EmailAccount(
      name="test",
      imap_host="imap.example.com",
      smtp_host="smtp.example.com",
      username="test@example.com",
    )
    client = SyncIMAPClient(account)
    result = client.__enter__()
    assert result is client
    # Cleanup
    client.disconnect()

  def test_context_manager_exit_calls_disconnect(self):
    """
    Given: SyncIMAPClient used in with statement
    When: Exiting the context manager (__exit__)
    Then: disconnect() is called
    """
    account = EmailAccount(
      name="test",
      imap_host="imap.example.com",
      smtp_host="smtp.example.com",
      username="test@example.com",
    )
    with patch.object(SyncIMAPClient, "disconnect", autospec=True) as mock_disconnect:
      with SyncIMAPClient(account) as client:
        assert client is not None
      mock_disconnect.assert_called_once()

  def test_context_manager_exit_on_exception(self):
    """
    Given: SyncIMAPClient used in with statement
    When: Exception occurs inside the context
    Then: Still calls disconnect() to cleanup resources
    """
    account = EmailAccount(
      name="test",
      imap_host="imap.example.com",
      smtp_host="smtp.example.com",
      username="test@example.com",
    )
    with patch.object(SyncIMAPClient, "disconnect", autospec=True) as mock_disconnect:
      try:
        with SyncIMAPClient(account):
          raise ValueError("Test exception")
      except ValueError:
        pass
      mock_disconnect.assert_called_once()


class TestSyncIMAPClientInitialization:
  """Test initialization and background thread setup."""

  def test_init_creates_background_thread(self):
    """
    Given: EmailAccount configuration
    When: Creating SyncIMAPClient instance
    Then: Background thread is created and event loop is started
    """
    account = EmailAccount(
      name="test",
      imap_host="imap.example.com",
      smtp_host="smtp.example.com",
      username="test@example.com",
    )
    client = SyncIMAPClient(account)
    try:
      assert client._thread is not None
      assert client._thread.is_alive()
      assert client._loop is not None
      assert client._loop.is_running()
    finally:
      client.disconnect()

  def test_init_stores_async_client(self):
    """
    Given: EmailAccount configuration
    When: Creating SyncIMAPClient instance
    Then: Internal _async_client attribute is initialized
    """
    account = EmailAccount(
      name="test",
      imap_host="imap.example.com",
      smtp_host="smtp.example.com",
      username="test@example.com",
    )
    client = SyncIMAPClient(account)
    try:
      assert client._async_client is not None
      assert isinstance(client._async_client, IMAPClient)
    finally:
      client.disconnect()

  def test_background_thread_is_daemon(self):
    """
    Given: SyncIMAPClient instance
    When: Checking thread properties
    Then: Background thread is marked as daemon
    """
    account = EmailAccount(
      name="test",
      imap_host="imap.example.com",
      smtp_host="smtp.example.com",
      username="test@example.com",
    )
    client = SyncIMAPClient(account)
    try:
      assert client._thread.daemon is True
    finally:
      client.disconnect()


class TestSyncIMAPClientConnect:
  """Test connect method delegation."""

  def test_connect_delegates_to_async_client(self):
    """
    Given: SyncIMAPClient instance
    When: Calling connect()
    Then: Delegates to async client's connect method
    """
    account = EmailAccount(
      name="test",
      imap_host="imap.example.com",
      smtp_host="smtp.example.com",
      username="test@example.com",
    )
    client = SyncIMAPClient(account)
    try:
      with patch.object(client._async_client, "connect", new_callable=AsyncMock) as mock_connect:
        mock_connect.return_value = MagicMock()
        client.connect()
        mock_connect.assert_called_once()
    finally:
      client.disconnect()

  def test_connect_returns_imap_connection(self):
    """
    Given: SyncIMAPClient instance
    When: Calling connect() successfully
    Then: Returns IMAP4_SSL connection object
    """
    account = EmailAccount(
      name="test",
      imap_host="imap.example.com",
      smtp_host="smtp.example.com",
      username="test@example.com",
    )
    client = SyncIMAPClient(account)
    try:
      mock_connection = MagicMock(spec=IMAP4_SSL)
      with patch.object(client._async_client, "connect", new_callable=AsyncMock) as mock_connect:
        mock_connect.return_value = mock_connection
        result = client.connect()
        assert result is mock_connection
    finally:
      client.disconnect()

  def test_connect_wraps_timeout_error(self):
    """
    Given: SyncIMAPClient instance
    When: Async client raises TimeoutError
    Then: Wraps in RuntimeError with descriptive message
    """
    account = EmailAccount(
      name="test",
      imap_host="imap.example.com",
      smtp_host="smtp.example.com",
      username="test@example.com",
    )
    client = SyncIMAPClient(account)
    try:
      with patch.object(client._async_client, "connect", new_callable=AsyncMock) as mock_connect:
        mock_connect.side_effect = TimeoutError("Connection timeout")
        with pytest.raises(RuntimeError, match="timed out"):
          client.connect()
    finally:
      client.disconnect()

  def test_connect_wraps_connection_error(self):
    """
    Given: SyncIMAPClient instance
    When: Async client raises ConnectionError
    Then: Wraps in RuntimeError with descriptive message
    """
    account = EmailAccount(
      name="test",
      imap_host="imap.example.com",
      smtp_host="smtp.example.com",
      username="test@example.com",
    )
    client = SyncIMAPClient(account)
    try:
      with patch.object(client._async_client, "connect", new_callable=AsyncMock) as mock_connect:
        mock_connect.side_effect = ConnectionError("Connection lost")
        with pytest.raises(RuntimeError, match="Connection error"):
          client.connect()
    finally:
      client.disconnect()


class TestSyncIMAPClientDisconnect:
  """Test disconnect method delegation."""

  def test_disconnect_delegates_to_async_client(self):
    """
    Given: SyncIMAPClient instance
    When: Calling disconnect()
    Then: Delegates to async client's disconnect method
    """
    account = EmailAccount(
      name="test",
      imap_host="imap.example.com",
      smtp_host="smtp.example.com",
      username="test@example.com",
    )
    client = SyncIMAPClient(account)
    with patch.object(
      client._async_client, "disconnect", new_callable=AsyncMock
    ) as mock_disconnect:
      client.disconnect()
      mock_disconnect.assert_called_once()

  def test_disconnect_stops_event_loop(self):
    """
    Given: SyncIMAPClient instance with active connection
    When: Calling disconnect()
    Then: Stops the event loop
    """
    account = EmailAccount(
      name="test",
      imap_host="imap.example.com",
      smtp_host="smtp.example.com",
      username="test@example.com",
    )
    client = SyncIMAPClient(account)
    loop = client._loop
    client.disconnect()
    assert not loop.is_running()

  def test_disconnect_joins_background_thread(self):
    """
    Given: SyncIMAPClient instance with background thread
    When: Calling disconnect()
    Then: Joins the background thread with timeout
    """
    account = EmailAccount(
      name="test",
      imap_host="imap.example.com",
      smtp_host="smtp.example.com",
      username="test@example.com",
    )
    client = SyncIMAPClient(account)
    thread = client._thread
    client.disconnect()
    # Thread should no longer be alive after join
    assert not thread.is_alive()


class TestSyncIMAPClientListFolders:
  """Test list_folders method delegation."""

  def test_list_folders_delegates_to_async_client(self):
    """
    Given: SyncIMAPClient instance
    When: Calling list_folders()
    Then: Delegates to async client's list_folders method
    """
    account = EmailAccount(
      name="test",
      imap_host="imap.example.com",
      smtp_host="smtp.example.com",
      username="test@example.com",
    )
    client = SyncIMAPClient(account)
    try:
      with patch.object(client._async_client, "list_folders", new_callable=AsyncMock) as mock_list:
        mock_list.return_value = [{"name": "INBOX", "flags": "\\HasNoChildren", "delimiter": "/"}]
        result = client.list_folders()
        mock_list.assert_called_once()
        assert result == [{"name": "INBOX", "flags": "\\HasNoChildren", "delimiter": "/"}]
    finally:
      client.disconnect()

  def test_list_folders_returns_folder_list(self):
    """
    Given: SyncIMAPClient instance with folders
    When: Calling list_folders()
    Then: Returns list of folder dictionaries
    """
    account = EmailAccount(
      name="test",
      imap_host="imap.example.com",
      smtp_host="smtp.example.com",
      username="test@example.com",
    )
    client = SyncIMAPClient(account)
    try:
      folders = [
        {"name": "INBOX", "flags": ["\\HasNoChildren"], "delimiter": "/"},
        {"name": "Sent", "flags": ["\\HasNoChildren"], "delimiter": "/"},
      ]
      with patch.object(client._async_client, "list_folders", new_callable=AsyncMock) as mock_list:
        mock_list.return_value = folders
        result = client.list_folders()
        assert isinstance(result, list)
        assert len(result) == 2
    finally:
      client.disconnect()

  def test_list_folders_wraps_errors(self):
    """
    Given: SyncIMAPClient instance
    When: Async client raises error
    Then: Wraps in RuntimeError
    """
    account = EmailAccount(
      name="test",
      imap_host="imap.example.com",
      smtp_host="smtp.example.com",
      username="test@example.com",
    )
    client = SyncIMAPClient(account)
    try:
      with patch.object(client._async_client, "list_folders", new_callable=AsyncMock) as mock_list:
        mock_list.side_effect = Exception("List failed")
        with pytest.raises(RuntimeError, match="Operation failed"):
          client.list_folders()
    finally:
      client.disconnect()


class TestSyncIMAPClientSelectFolder:
  """Test select_folder method delegation."""

  def test_select_folder_delegates_to_async_client(self):
    """
    Given: SyncIMAPClient instance
    When: Calling select_folder(folder="INBOX")
    Then: Delegates to async client's select_folder method
    """
    account = EmailAccount(
      name="test",
      imap_host="imap.example.com",
      smtp_host="smtp.example.com",
      username="test@example.com",
    )
    client = SyncIMAPClient(account)
    try:
      with patch.object(
        client._async_client, "select_folder", new_callable=AsyncMock
      ) as mock_select:
        mock_select.return_value = {"folder": "INBOX", "count": 10}
        result = client.select_folder("INBOX")
        mock_select.assert_called_once_with("INBOX")
        assert result == {"folder": "INBOX", "count": 10}
    finally:
      client.disconnect()

  def test_select_folder_returns_message_count(self):
    """
    Given: SyncIMAPClient instance
    When: Calling select_folder()
    Then: Returns dict with folder name and message count
    """
    account = EmailAccount(
      name="test",
      imap_host="imap.example.com",
      smtp_host="smtp.example.com",
      username="test@example.com",
    )
    client = SyncIMAPClient(account)
    try:
      with patch.object(
        client._async_client, "select_folder", new_callable=AsyncMock
      ) as mock_select:
        mock_select.return_value = {"folder": "Archive", "count": 42}
        result = client.select_folder("Archive")
        assert result["folder"] == "Archive"
        assert result["count"] == 42
    finally:
      client.disconnect()


class TestSyncIMAPClientSearch:
  """Test search method delegation."""

  def test_search_delegates_to_async_client(self):
    """
    Given: SyncIMAPClient instance
    When: Calling search(folder="INBOX", criteria="ALL", limit=50)
    Then: Delegates to async client's search method with correct params
    """
    account = EmailAccount(
      name="test",
      imap_host="imap.example.com",
      smtp_host="smtp.example.com",
      username="test@example.com",
    )
    client = SyncIMAPClient(account)
    try:
      with patch.object(client._async_client, "search", new_callable=AsyncMock) as mock_search:
        mock_search.return_value = ["1", "2", "3"]
        result = client.search(folder="INBOX", criteria="ALL", limit=50)
        mock_search.assert_called_once_with("INBOX", "ALL", 50)
        assert result == ["1", "2", "3"]
    finally:
      client.disconnect()

  def test_search_returns_message_ids(self):
    """
    Given: SyncIMAPClient instance with messages
    When: Calling search()
    Then: Returns list of message ID strings
    """
    account = EmailAccount(
      name="test",
      imap_host="imap.example.com",
      smtp_host="smtp.example.com",
      username="test@example.com",
    )
    client = SyncIMAPClient(account)
    try:
      with patch.object(client._async_client, "search", new_callable=AsyncMock) as mock_search:
        mock_search.return_value = ["10", "20", "30"]
        result = client.search()
        assert isinstance(result, list)
        assert all(isinstance(msg_id, str) for msg_id in result)
    finally:
      client.disconnect()


class TestSyncIMAPClientFetchMessage:
  """Test fetch_message method delegation."""

  def test_fetch_message_delegates_to_async_client(self):
    """
    Given: SyncIMAPClient instance
    When: Calling fetch_message(message_id="1", folder="INBOX")
    Then: Delegates to async client's fetch_message method with correct params
    """
    account = EmailAccount(
      name="test",
      imap_host="imap.example.com",
      smtp_host="smtp.example.com",
      username="test@example.com",
    )
    client = SyncIMAPClient(account)
    try:
      msg = {"id": "1", "folder": "INBOX", "subject": "Test"}
      with patch.object(
        client._async_client, "fetch_message", new_callable=AsyncMock
      ) as mock_fetch:
        mock_fetch.return_value = msg
        result = client.fetch_message("1", "INBOX")
        mock_fetch.assert_called_once_with("1", "INBOX")
        assert result == msg
    finally:
      client.disconnect()

  def test_fetch_message_returns_message_dict(self):
    """
    Given: SyncIMAPClient instance
    When: Calling fetch_message()
    Then: Returns dict with message details (id, folder, subject, from, to, etc.)
    """
    account = EmailAccount(
      name="test",
      imap_host="imap.example.com",
      smtp_host="smtp.example.com",
      username="test@example.com",
    )
    client = SyncIMAPClient(account)
    try:
      msg = {
        "id": "1",
        "folder": "INBOX",
        "subject": "Test Subject",
        "from": "sender@example.com",
        "to": "recipient@example.com",
      }
      with patch.object(
        client._async_client, "fetch_message", new_callable=AsyncMock
      ) as mock_fetch:
        mock_fetch.return_value = msg
        result = client.fetch_message("1")
        assert "id" in result
        assert "folder" in result
    finally:
      client.disconnect()


class TestSyncIMAPClientMoveMessage:
  """Test move_message method delegation."""

  def test_move_message_delegates_to_async_client(self):
    """
    Given: SyncIMAPClient instance
    When: Calling move_message(message_id="1", source_folder="INBOX", dest_folder="Archive")
    Then: Delegates to async client's move_message method with correct params
    """
    account = EmailAccount(
      name="test",
      imap_host="imap.example.com",
      smtp_host="smtp.example.com",
      username="test@example.com",
    )
    client = SyncIMAPClient(account)
    try:
      with patch.object(client._async_client, "move_message", new_callable=AsyncMock) as mock_move:
        mock_move.return_value = True
        result = client.move_message("1", "INBOX", "Archive")
        mock_move.assert_called_once_with("1", "INBOX", "Archive")
        assert result is True
    finally:
      client.disconnect()

  def test_move_message_returns_true_on_success(self):
    """
    Given: SyncIMAPClient instance
    When: Calling move_message() successfully
    Then: Returns True
    """
    account = EmailAccount(
      name="test",
      imap_host="imap.example.com",
      smtp_host="smtp.example.com",
      username="test@example.com",
    )
    client = SyncIMAPClient(account)
    try:
      with patch.object(client._async_client, "move_message", new_callable=AsyncMock) as mock_move:
        mock_move.return_value = True
        result = client.move_message("1", "INBOX", "Archive")
        assert result is True
    finally:
      client.disconnect()


class TestSyncIMAPClientDeleteMessage:
  """Test delete_message method delegation."""

  def test_delete_message_delegates_to_async_client(self):
    """
    Given: SyncIMAPClient instance
    When: Calling delete_message(message_id="1", folder="INBOX", expunge=True)
    Then: Delegates to async client's delete_message method with correct params
    """
    account = EmailAccount(
      name="test",
      imap_host="imap.example.com",
      smtp_host="smtp.example.com",
      username="test@example.com",
    )
    client = SyncIMAPClient(account)
    try:
      with patch.object(
        client._async_client, "delete_message", new_callable=AsyncMock
      ) as mock_delete:
        mock_delete.return_value = True
        result = client.delete_message("1", "INBOX", expunge=True)
        mock_delete.assert_called_once_with("1", "INBOX", True)
        assert result is True
    finally:
      client.disconnect()

  def test_delete_message_returns_true_on_success(self):
    """
    Given: SyncIMAPClient instance
    When: Calling delete_message() successfully
    Then: Returns True
    """
    account = EmailAccount(
      name="test",
      imap_host="imap.example.com",
      smtp_host="smtp.example.com",
      username="test@example.com",
    )
    client = SyncIMAPClient(account)
    try:
      with patch.object(
        client._async_client, "delete_message", new_callable=AsyncMock
      ) as mock_delete:
        mock_delete.return_value = True
        result = client.delete_message("1")
        assert result is True
    finally:
      client.disconnect()


class TestSyncIMAPClientMarkMessage:
  """Test mark_message method delegation."""

  def test_mark_message_delegates_to_async_client(self):
    """
    Given: SyncIMAPClient instance
    When: Calling mark_message(message_id="1", folder="INBOX", flag="\\Seen", action="add")
    Then: Delegates to async client's mark_message method with correct params
    """
    account = EmailAccount(
      name="test",
      imap_host="imap.example.com",
      smtp_host="smtp.example.com",
      username="test@example.com",
    )
    client = SyncIMAPClient(account)
    try:
      with patch.object(client._async_client, "mark_message", new_callable=AsyncMock) as mock_mark:
        mock_mark.return_value = True
        result = client.mark_message("1", "INBOX", "\\Seen", "add")
        mock_mark.assert_called_once_with("1", "INBOX", "\\Seen", "add")
        assert result is True
    finally:
      client.disconnect()

  def test_mark_message_returns_true_on_success(self):
    """
    Given: SyncIMAPClient instance
    When: Calling mark_message() successfully
    Then: Returns True
    """
    account = EmailAccount(
      name="test",
      imap_host="imap.example.com",
      smtp_host="smtp.example.com",
      username="test@example.com",
    )
    client = SyncIMAPClient(account)
    try:
      with patch.object(client._async_client, "mark_message", new_callable=AsyncMock) as mock_mark:
        mock_mark.return_value = True
        result = client.mark_message("1", "INBOX", "\\Seen")
        assert result is True
    finally:
      client.disconnect()


class TestSyncIMAPClientDownloadAttachment:
  """Test download_attachment method delegation."""

  def test_download_attachment_delegates_to_async_client(self):
    """
    Given: SyncIMAPClient instance
    When: Calling download_attachment(message_id="1", folder="INBOX", filename="test.pdf", output_dir="/tmp")
    Then: Delegates to async client's download_attachment method with correct params
    """
    account = EmailAccount(
      name="test",
      imap_host="imap.example.com",
      smtp_host="smtp.example.com",
      username="test@example.com",
    )
    client = SyncIMAPClient(account)
    try:
      with patch.object(
        client._async_client, "download_attachment", new_callable=AsyncMock
      ) as mock_download:
        mock_download.return_value = "/tmp/test.pdf"
        result = client.download_attachment("1", "INBOX", "test.pdf", "/tmp")
        mock_download.assert_called_once_with("1", "INBOX", "test.pdf", "/tmp")
        assert result == "/tmp/test.pdf"
    finally:
      client.disconnect()

  def test_download_attachment_returns_file_path(self):
    """
    Given: SyncIMAPClient instance with attachment
    When: Calling download_attachment() successfully
    Then: Returns absolute path to downloaded file
    """
    account = EmailAccount(
      name="test",
      imap_host="imap.example.com",
      smtp_host="smtp.example.com",
      username="test@example.com",
    )
    client = SyncIMAPClient(account)
    try:
      with patch.object(
        client._async_client, "download_attachment", new_callable=AsyncMock
      ) as mock_download:
        mock_download.return_value = "/absolute/path/to/file.pdf"
        result = client.download_attachment("1", "INBOX", "file.pdf", "/tmp")
        assert result == "/absolute/path/to/file.pdf"
    finally:
      client.disconnect()


class TestSyncIMAPClientHasCapability:
  """Test has_capability method (sync property)."""

  def test_has_capability_delegates_to_async_client(self):
    """
    Given: SyncIMAPClient instance
    When: Calling has_capability(name="MOVE")
    Then: Delegates to async client's has_capability property (sync call)
    """
    account = EmailAccount(
      name="test",
      imap_host="imap.example.com",
      smtp_host="smtp.example.com",
      username="test@example.com",
    )
    client = SyncIMAPClient(account)
    try:
      with patch.object(client._async_client, "has_capability", return_value=True) as mock_cap:
        result = client.has_capability("MOVE")
        mock_cap.assert_called_once_with("MOVE")
        assert result is True
    finally:
      client.disconnect()

  def test_has_capability_returns_bool(self):
    """
    Given: SyncIMAPClient instance
    When: Calling has_capability()
    Then: Returns boolean indicating capability support
    """
    account = EmailAccount(
      name="test",
      imap_host="imap.example.com",
      smtp_host="smtp.example.com",
      username="test@example.com",
    )
    client = SyncIMAPClient(account)
    try:
      with patch.object(client._async_client, "has_capability", return_value=False):
        result = client.has_capability("NONEXISTENT")
        assert isinstance(result, bool)
        assert result is False
    finally:
      client.disconnect()


class TestSyncIMAPClientErrorHandling:
  """Test error handling and wrapping."""

  def test_timeout_error_wrapped_in_runtime_error(self):
    """
    Given: SyncIMAPClient instance
    When: Async operation times out
    Then: Raises RuntimeError with timeout message
    """
    account = EmailAccount(
      name="test",
      imap_host="imap.example.com",
      smtp_host="smtp.example.com",
      username="test@example.com",
    )
    client = SyncIMAPClient(account)
    try:
      with patch.object(client._async_client, "search", new_callable=AsyncMock) as mock_search:
        mock_search.side_effect = TimeoutError("Timeout")
        with pytest.raises(RuntimeError, match="timed out"):
          client.search()
    finally:
      client.disconnect()

  def test_connection_error_wrapped_in_runtime_error(self):
    """
    Given: SyncIMAPClient instance
    When: Async operation fails with ConnectionError
    Then: Raises RuntimeError with connection message
    """
    account = EmailAccount(
      name="test",
      imap_host="imap.example.com",
      smtp_host="smtp.example.com",
      username="test@example.com",
    )
    client = SyncIMAPClient(account)
    try:
      with patch.object(client._async_client, "search", new_callable=AsyncMock) as mock_search:
        mock_search.side_effect = ConnectionError("Lost connection")
        with pytest.raises(RuntimeError, match="Connection error"):
          client.search()
    finally:
      client.disconnect()

  def test_generic_exception_wrapped_in_runtime_error(self):
    """
    Given: SyncIMAPClient instance
    When: Async operation raises unexpected exception
    Then: Wraps in RuntimeError with descriptive message
    """
    account = EmailAccount(
      name="test",
      imap_host="imap.example.com",
      smtp_host="smtp.example.com",
      username="test@example.com",
    )
    client = SyncIMAPClient(account)
    try:
      with patch.object(client._async_client, "search", new_callable=AsyncMock) as mock_search:
        mock_search.side_effect = Exception("Unexpected error")
        with pytest.raises(RuntimeError, match="Operation failed"):
          client.search()
    finally:
      client.disconnect()


class TestSyncIMAPClientThreadSafety:
  """Test thread safety and resource management."""

  def test_run_coroutine_uses_threadsafe_method(self):
    """
    Given: SyncIMAPClient instance with background loop
    When: Calling _run_coroutine()
    Then: Uses asyncio.run_coroutine_threadsafe
    """
    account = EmailAccount(
      name="test",
      imap_host="imap.example.com",
      smtp_host="smtp.example.com",
      username="test@example.com",
    )
    client = SyncIMAPClient(account)
    try:
      with patch("asyncio.run_coroutine_threadsafe") as mock_run:
        mock_future = MagicMock()
        mock_future.result.return_value = ["1", "2"]
        mock_run.return_value = mock_future

        with patch.object(client._async_client, "search", new_callable=AsyncMock) as mock_search:
          mock_search.return_value = ["1", "2"]
          client.search()

          # Verify run_coroutine_threadsafe was called
          assert mock_run.called

    finally:
      client.disconnect()

  def test_concurrent_operations_are_thread_safe(self):
    """
    Given: Multiple threads using same SyncIMAPClient
    When: Calling methods concurrently
    Then: Operations are serialized via async client's operation lock
    """
    import concurrent.futures

    account = EmailAccount(
      name="test",
      imap_host="imap.example.com",
      smtp_host="smtp.example.com",
      username="test@example.com",
    )
    client = SyncIMAPClient(account)
    try:
      call_count = 0

      def increment_call():
        nonlocal call_count
        with patch.object(client._async_client, "search", new_callable=AsyncMock) as mock_search:
          mock_search.return_value = ["1"]
          return client.search()

      # Run multiple operations concurrently
      with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(increment_call) for _ in range(10)]
        results = [f.result() for f in futures]

        # All should succeed
        assert len(results) == 10
        assert all(r == ["1"] for r in results)
    finally:
      client.disconnect()

  def test_event_loop_properly_started(self):
    """
    Given: SyncIMAPClient instance
    When: Checking background thread state
    Then: Event loop is running in background thread
    """
    account = EmailAccount(
      name="test",
      imap_host="imap.example.com",
      smtp_host="smtp.example.com",
      username="test@example.com",
    )
    client = SyncIMAPClient(account)
    try:
      assert client._loop.is_running()
      assert client._thread.is_alive()
    finally:
      client.disconnect()

  def test_event_loop_stopped_on_disconnect(self):
    """
    Given: SyncIMAPClient instance with active loop
    When: Calling disconnect()
    Then: Event loop is properly stopped
    """
    account = EmailAccount(
      name="test",
      imap_host="imap.example.com",
      smtp_host="smtp.example.com",
      username="test@example.com",
    )
    client = SyncIMAPClient(account)
    loop = client._loop
    client.disconnect()
    assert not loop.is_running()


class TestSyncIMAPClientResourceCleanup:
  """Test resource cleanup on exceptions."""

  def test_cleanup_on_normal_exit(self):
    """
    Given: SyncIMAPClient in with statement
    When: Exiting context normally
    Then: All resources are cleaned up (loop stopped, thread joined)
    """
    account = EmailAccount(
      name="test",
      imap_host="imap.example.com",
      smtp_host="smtp.example.com",
      username="test@example.com",
    )
    with SyncIMAPClient(account) as client:
      loop = client._loop
      thread = client._thread

    # After context exit
    assert not loop.is_running()
    assert not thread.is_alive()

  def test_cleanup_on_exception_in_context(self):
    """
    Given: SyncIMAPClient in with statement
    When: Exception occurs in context
    Then: Resources still cleaned up properly
    """
    account = EmailAccount(
      name="test",
      imap_host="imap.example.com",
      smtp_host="smtp.example.com",
      username="test@example.com",
    )
    try:
      with SyncIMAPClient(account) as client:
        loop = client._loop
        thread = client._thread
        raise ValueError("Test error")
    except ValueError:
      pass

    # After exception
    assert not loop.is_running()
    assert not thread.is_alive()

  def test_cleanup_on_exception_during_connect(self):
    """
    Given: SyncIMAPClient instance
    When: connect() raises exception
    Then: Partial resources are cleaned up
    """
    account = EmailAccount(
      name="test",
      imap_host="imap.example.com",
      smtp_host="smtp.example.com",
      username="test@example.com",
    )
    client = SyncIMAPClient(account)
    try:
      with patch.object(client._async_client, "connect", new_callable=AsyncMock) as mock_connect:
        mock_connect.side_effect = Exception("Connect failed")
        with pytest.raises(RuntimeError):
          client.connect()
      # Resources should still be available for cleanup
      assert client._loop is not None
      assert client._thread is not None
    finally:
      client.disconnect()

  def test_no_resource_leaks_on_multiple_uses(self):
    """
    Given: SyncIMAPClient used multiple times
    When: Creating and destroying instances repeatedly
    Then: No thread/loop leaks occur
    """
    account = EmailAccount(
      name="test",
      imap_host="imap.example.com",
      smtp_host="smtp.example.com",
      username="test@example.com",
    )

    initial_thread_count = threading.active_count()

    # Create and destroy multiple instances
    for _ in range(5):
      client = SyncIMAPClient(account)
      client.disconnect()

    # Allow threads to fully terminate
    import time

    time.sleep(0.1)

    # Thread count should return to initial
    final_thread_count = threading.active_count()
    assert final_thread_count <= initial_thread_count


class TestSyncIMAPClientCreateFolder:
  """Test create_folder method delegation."""

  def test_create_folder_delegates_to_async_client(self):
    """
    Given: SyncIMAPClient instance
    When: Calling create_folder(folder_name="Sent")
    Then: Delegates to async client's create_folder method with correct params
    """
    account = EmailAccount(
      name="test",
      imap_host="imap.example.com",
      smtp_host="smtp.example.com",
      username="test@example.com",
    )
    client = SyncIMAPClient(account)
    try:
      with patch.object(
        client._async_client, "create_folder", new_callable=AsyncMock
      ) as mock_create:
        mock_create.return_value = True
        result = client.create_folder("Sent")
        mock_create.assert_called_once_with("Sent")
        assert result is True
    finally:
      client.disconnect()

  def test_create_folder_returns_true_on_success(self):
    """
    Given: SyncIMAPClient instance
    When: Calling create_folder() successfully
    Then: Returns True
    """
    account = EmailAccount(
      name="test",
      imap_host="imap.example.com",
      smtp_host="smtp.example.com",
      username="test@example.com",
    )
    client = SyncIMAPClient(account)
    try:
      with patch.object(
        client._async_client, "create_folder", new_callable=AsyncMock
      ) as mock_create:
        mock_create.return_value = True
        result = client.create_folder("Archive")
        assert result is True
    finally:
      client.disconnect()

  def test_create_folder_wraps_errors(self):
    """
    Given: SyncIMAPClient instance
    When: Async client raises RuntimeError or ValueError
    Then: Error is propagated through sync wrapper
    """
    account = EmailAccount(
      name="test",
      imap_host="imap.example.com",
      smtp_host="smtp.example.com",
      username="test@example.com",
    )
    client = SyncIMAPClient(account)
    try:
      with patch.object(
        client._async_client, "create_folder", new_callable=AsyncMock
      ) as mock_create:
        mock_create.side_effect = RuntimeError("Folder already exists")
        with pytest.raises(RuntimeError, match="already exists"):
          client.create_folder("Sent")
    finally:
      client.disconnect()
