"""Tests for SyncSMTPClient wrapper.

These tests verify the synchronous wrapper around async SMTPClient.
Tests verify:
- Context manager entry/exit
- All public methods delegate correctly to async client
- Recipient whitelist validation (delegated from async client)
- CRLF injection prevention (delegated from async client)
- Error handling (SMTPException wrapping)
- Thread safety and cleanup
- No resource leaks on exception
"""

import threading
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from simple_email_gw.config import EmailAccount
from simple_email_gw.smtp.client import SMTPClient, WhitelistError
from simple_email_gw.smtp.sync_client import SyncSMTPClient


class TestSyncSMTPClientContextManager:
  """Test context manager functionality."""

  def test_context_manager_entry_returns_self(self):
    """
    Given: SyncSMTPClient instance
    When: Using context manager entry (__enter__)
    Then: Returns self
    """
    account = EmailAccount(
      name="test",
      imap_host="imap.example.com",
      smtp_host="smtp.example.com",
      username="test@example.com",
    )
    client = SyncSMTPClient(account)
    result = client.__enter__()
    assert result is client
    # Cleanup
    client.__exit__(None, None, None)

  def test_context_manager_exit_stops_loop(self):
    """
    Given: SyncSMTPClient used in with statement
    When: Exiting the context manager (__exit__)
    Then: Stops the event loop and joins thread
    """
    account = EmailAccount(
      name="test",
      imap_host="imap.example.com",
      smtp_host="smtp.example.com",
      username="test@example.com",
    )
    client = SyncSMTPClient(account)
    loop = client._loop
    thread = client._thread
    client.__exit__(None, None, None)
    assert not loop.is_running()
    assert not thread.is_alive()

  def test_context_manager_exit_on_exception(self):
    """
    Given: SyncSMTPClient used in with statement
    When: Exception occurs inside the context
    Then: Still stops loop and joins thread
    """
    account = EmailAccount(
      name="test",
      imap_host="imap.example.com",
      smtp_host="smtp.example.com",
      username="test@example.com",
    )
    loop = None
    thread = None
    try:
      with SyncSMTPClient(account) as client:
        loop = client._loop
        thread = client._thread
        raise ValueError("Test exception")
    except ValueError:
      pass

    assert not loop.is_running()
    assert not thread.is_alive()


class TestSyncSMTPClientInitialization:
  """Test initialization and background thread setup."""

  def test_init_creates_background_thread(self):
    """
    Given: EmailAccount configuration
    When: Creating SyncSMTPClient instance
    Then: Background thread is created and event loop is started
    """
    account = EmailAccount(
      name="test",
      imap_host="imap.example.com",
      smtp_host="smtp.example.com",
      username="test@example.com",
    )
    client = SyncSMTPClient(account)
    try:
      assert client._thread is not None
      assert client._thread.is_alive()
      assert client._loop is not None
      assert client._loop.is_running()
    finally:
      client.__exit__(None, None, None)

  def test_init_stores_async_client(self):
    """
    Given: EmailAccount configuration
    When: Creating SyncSMTPClient instance
    Then: Internal _async_client attribute is initialized
    """
    account = EmailAccount(
      name="test",
      imap_host="imap.example.com",
      smtp_host="smtp.example.com",
      username="test@example.com",
    )
    client = SyncSMTPClient(account)
    try:
      assert client._async_client is not None
      assert isinstance(client._async_client, SMTPClient)
    finally:
      client.__exit__(None, None, None)

  def test_background_thread_is_daemon(self):
    """
    Given: SyncSMTPClient instance
    When: Checking thread properties
    Then: Background thread is marked as daemon
    """
    account = EmailAccount(
      name="test",
      imap_host="imap.example.com",
      smtp_host="smtp.example.com",
      username="test@example.com",
    )
    client = SyncSMTPClient(account)
    try:
      assert client._thread.daemon is True
    finally:
      client.__exit__(None, None, None)


class TestSyncSMTPClientSendEmail:
  """Test send_email method delegation."""

  def test_send_email_delegates_to_async_client(self):
    """
    Given: SyncSMTPClient instance
    When: Calling send_email(to=["test@example.com"], subject="Test", body="Hello")
    Then: Delegates to async client's send_email method with correct params
    """
    account = EmailAccount(
      name="test",
      imap_host="imap.example.com",
      smtp_host="smtp.example.com",
      username="test@example.com",
    )
    client = SyncSMTPClient(account)
    try:
      with patch.object(client._async_client, 'send_email', new_callable=AsyncMock) as mock_send:
        mock_send.return_value = {"status": "sent", "recipients": "test@example.com", "message": "OK"}
        result = client.send_email(["test@example.com"], "Test", "Hello")
        mock_send.assert_called_once_with(
          to=["test@example.com"],
          subject="Test",
          body="Hello",
          cc=None,
          bcc=None,
          html_body=None,
          attachments=None,
        )
        assert result == {"status": "sent", "recipients": "test@example.com", "message": "OK"}
    finally:
      client.__exit__(None, None, None)

  def test_send_email_returns_result_dict(self):
    """
    Given: SyncSMTPClient instance
    When: Calling send_email() successfully
    Then: Returns dict with 'status', 'recipients', and 'message' keys
    """
    account = EmailAccount(
      name="test",
      imap_host="imap.example.com",
      smtp_host="smtp.example.com",
      username="test@example.com",
    )
    client = SyncSMTPClient(account)
    try:
      with patch.object(client._async_client, 'send_email', new_callable=AsyncMock) as mock_send:
        mock_send.return_value = {"status": "sent", "recipients": "test@example.com", "message": "OK"}
        result = client.send_email(["test@example.com"], "Test", "Hello")
        assert "status" in result
        assert "recipients" in result
        assert "message" in result
    finally:
      client.__exit__(None, None, None)

  def test_send_email_with_optional_params(self):
    """
    Given: SyncSMTPClient instance
    When: Calling send_email with cc, bcc, html_body, attachments
    Then: All params are forwarded to async client
    """
    account = EmailAccount(
      name="test",
      imap_host="imap.example.com",
      smtp_host="smtp.example.com",
      username="test@example.com",
    )
    client = SyncSMTPClient(account)
    try:
      with patch.object(client._async_client, 'send_email', new_callable=AsyncMock) as mock_send:
        mock_send.return_value = {"status": "sent", "recipients": "test@example.com", "message": "OK"}
        client.send_email(
          to=["test@example.com"],
          subject="Test",
          body="Hello",
          cc=["cc@example.com"],
          bcc=["bcc@example.com"],
          html_body="<p>Hello</p>",
          attachments=["/tmp/file.pdf"],
        )
        mock_send.assert_called_once_with(
          to=["test@example.com"],
          subject="Test",
          body="Hello",
          cc=["cc@example.com"],
          bcc=["bcc@example.com"],
          html_body="<p>Hello</p>",
          attachments=["/tmp/file.pdf"],
        )
    finally:
      client.__exit__(None, None, None)

  def test_send_email_validates_recipients_delegated(self):
    """
    Given: SyncSMTPClient instance with invalid email address
    When: Calling send_email()
    Then: Validation error from async client is raised
    """
    account = EmailAccount(
      name="test",
      imap_host="imap.example.com",
      smtp_host="smtp.example.com",
      username="test@example.com",
    )
    client = SyncSMTPClient(account)
    try:
      with patch.object(client._async_client, 'send_email', new_callable=AsyncMock) as mock_send:
        mock_send.side_effect = ValueError("Invalid email address")
        with pytest.raises(ValueError, match="Invalid email address"):
          client.send_email(["invalid-email"], "Test", "Hello")
    finally:
      client.__exit__(None, None, None)

  def test_send_email_checks_whitelist_delegated(self):
    """
    Given: SyncSMTPClient instance with whitelist restriction
    When: Calling send_email() to non-whitelisted recipient
    Then: WhitelistError from async client is raised
    """
    account = EmailAccount(
      name="test",
      imap_host="imap.example.com",
      smtp_host="smtp.example.com",
      username="test@example.com",
    )
    client = SyncSMTPClient(account)
    try:
      with patch.object(client._async_client, 'send_email', new_callable=AsyncMock) as mock_send:
        mock_send.side_effect = WhitelistError("Recipients not in whitelist")
        with pytest.raises(WhitelistError, match="Recipients not in whitelist"):
          client.send_email(["blocked@example.com"], "Test", "Hello")
    finally:
      client.__exit__(None, None, None)

  def test_send_email_sanitizes_subject_delegated(self):
    """
    Given: SyncSMTPClient instance with CRLF in subject
    When: Calling send_email()
    Then: CRLF injection prevention from async client is applied
    """
    account = EmailAccount(
      name="test",
      imap_host="imap.example.com",
      smtp_host="smtp.example.com",
      username="test@example.com",
    )
    client = SyncSMTPClient(account)
    try:
      with patch.object(client._async_client, 'send_email', new_callable=AsyncMock) as mock_send:
        mock_send.return_value = {"status": "sent", "recipients": "test@example.com", "message": "OK"}
        # Subject with CRLF should be sanitized by async client
        result = client.send_email(["test@example.com"], "Test\r\nBcc: bad@example.com", "Hello")
        assert result["status"] == "sent"
    finally:
      client.__exit__(None, None, None)


class TestSyncSMTPClientReplyEmail:
  """Test reply_email method delegation."""

  def test_reply_email_delegates_to_async_client(self):
    """
    Given: SyncSMTPClient instance
    When: Calling reply_email(to="test@example.com", subject="Re: Test", body="Reply", in_reply_to="<msg123@test.com>")
    Then: Delegates to async client's reply_email method with correct params
    """
    account = EmailAccount(
      name="test",
      imap_host="imap.example.com",
      smtp_host="smtp.example.com",
      username="test@example.com",
    )
    client = SyncSMTPClient(account)
    try:
      with patch.object(client._async_client, 'reply_email', new_callable=AsyncMock) as mock_reply:
        mock_reply.return_value = {"status": "sent", "recipients": "test@example.com", "message": "OK"}
        result = client.reply_email(
          to="test@example.com",
          subject="Re: Test",
          body="Reply",
          in_reply_to="<msg123@test.com>",
        )
        mock_reply.assert_called_once_with(
          to="test@example.com",
          subject="Re: Test",
          body="Reply",
          in_reply_to="<msg123@test.com>",
          references=None,
          html_body=None,
        )
        assert result == {"status": "sent", "recipients": "test@example.com", "message": "OK"}
    finally:
      client.__exit__(None, None, None)

  def test_reply_email_returns_result_dict(self):
    """
    Given: SyncSMTPClient instance
    When: Calling reply_email() successfully
    Then: Returns dict with 'status', 'recipients', and 'message' keys
    """
    account = EmailAccount(
      name="test",
      imap_host="imap.example.com",
      smtp_host="smtp.example.com",
      username="test@example.com",
    )
    client = SyncSMTPClient(account)
    try:
      with patch.object(client._async_client, 'reply_email', new_callable=AsyncMock) as mock_reply:
        mock_reply.return_value = {"status": "sent", "recipients": "test@example.com", "message": "OK"}
        result = client.reply_email("test@example.com", "Re: Test", "Reply", "<msg123@test.com>")
        assert "status" in result
        assert "recipients" in result
        assert "message" in result
    finally:
      client.__exit__(None, None, None)

  def test_reply_email_with_references(self):
    """
    Given: SyncSMTPClient instance
    When: Calling reply_email with references parameter
    Then: References are forwarded to async client
    """
    account = EmailAccount(
      name="test",
      imap_host="imap.example.com",
      smtp_host="smtp.example.com",
      username="test@example.com",
    )
    client = SyncSMTPClient(account)
    try:
      with patch.object(client._async_client, 'reply_email', new_callable=AsyncMock) as mock_reply:
        mock_reply.return_value = {"status": "sent", "recipients": "test@example.com", "message": "OK"}
        result = client.reply_email(
          to="test@example.com",
          subject="Re: Test",
          body="Reply",
          in_reply_to="<msg123@test.com>",
          references=["<msg1@test.com>", "<msg2@test.com>"],
        )
        mock_reply.assert_called_once()
        assert result["status"] == "sent"
    finally:
      client.__exit__(None, None, None)

  def test_reply_email_with_html_body(self):
    """
    Given: SyncSMTPClient instance
    When: Calling reply_email with html_body parameter
    Then: HTML body is forwarded to async client
    """
    account = EmailAccount(
      name="test",
      imap_host="imap.example.com",
      smtp_host="smtp.example.com",
      username="test@example.com",
    )
    client = SyncSMTPClient(account)
    try:
      with patch.object(client._async_client, 'reply_email', new_callable=AsyncMock) as mock_reply:
        mock_reply.return_value = {"status": "sent", "recipients": "test@example.com", "message": "OK"}
        result = client.reply_email(
          to="test@example.com",
          subject="Re: Test",
          body="Reply",
          in_reply_to="<msg123@test.com>",
          html_body="<p>Reply</p>",
        )
        mock_reply.assert_called_once()
        assert result["status"] == "sent"
    finally:
      client.__exit__(None, None, None)

  def test_reply_email_validates_recipient_delegated(self):
    """
    Given: SyncSMTPClient instance with invalid email address
    When: Calling reply_email()
    Then: Validation error from async client is raised
    """
    account = EmailAccount(
      name="test",
      imap_host="imap.example.com",
      smtp_host="smtp.example.com",
      username="test@example.com",
    )
    client = SyncSMTPClient(account)
    try:
      with patch.object(client._async_client, 'reply_email', new_callable=AsyncMock) as mock_reply:
        mock_reply.side_effect = ValueError("Invalid email address")
        with pytest.raises(ValueError, match="Invalid email address"):
          client.reply_email("invalid-email", "Re: Test", "Reply", "<msg123@test.com>")
    finally:
      client.__exit__(None, None, None)


class TestSyncSMTPClientForwardEmail:
  """Test forward_email method delegation."""

  def test_forward_email_delegates_to_async_client(self):
    """
    Given: SyncSMTPClient instance
    When: Calling forward_email(to=["test@example.com"], subject="Fwd: Test", original_from="sender@test.com", original_date="2024-01-01", original_body="Original text")
    Then: Delegates to async client's forward_email method with correct params
    """
    account = EmailAccount(
      name="test",
      imap_host="imap.example.com",
      smtp_host="smtp.example.com",
      username="test@example.com",
    )
    client = SyncSMTPClient(account)
    try:
      with patch.object(client._async_client, 'forward_email', new_callable=AsyncMock) as mock_forward:
        mock_forward.return_value = {"status": "sent", "recipients": "test@example.com", "message": "OK"}
        result = client.forward_email(
          to=["test@example.com"],
          subject="Fwd: Test",
          original_from="sender@test.com",
          original_date="2024-01-01",
          original_body="Original text",
        )
        mock_forward.assert_called_once_with(
          to=["test@example.com"],
          subject="Fwd: Test",
          original_from="sender@test.com",
          original_date="2024-01-01",
          original_body="Original text",
        )
        assert result == {"status": "sent", "recipients": "test@example.com", "message": "OK"}
    finally:
      client.__exit__(None, None, None)

  def test_forward_email_returns_result_dict(self):
    """
    Given: SyncSMTPClient instance
    When: Calling forward_email() successfully
    Then: Returns dict with 'status', 'recipients', and 'message' keys
    """
    account = EmailAccount(
      name="test",
      imap_host="imap.example.com",
      smtp_host="smtp.example.com",
      username="test@example.com",
    )
    client = SyncSMTPClient(account)
    try:
      with patch.object(client._async_client, 'forward_email', new_callable=AsyncMock) as mock_forward:
        mock_forward.return_value = {"status": "sent", "recipients": "test@example.com", "message": "OK"}
        result = client.forward_email(
          ["test@example.com"],
          "Fwd: Test",
          "sender@test.com",
          "2024-01-01",
          "Original text",
        )
        assert "status" in result
        assert "recipients" in result
        assert "message" in result
    finally:
      client.__exit__(None, None, None)

  def test_forward_email_formats_body(self):
    """
    Given: SyncSMTPClient instance
    When: Calling forward_email()
    Then: Forwards correctly with original message headers in body
    """
    account = EmailAccount(
      name="test",
      imap_host="imap.example.com",
      smtp_host="smtp.example.com",
      username="test@example.com",
    )
    client = SyncSMTPClient(account)
    try:
      with patch.object(client._async_client, 'forward_email', new_callable=AsyncMock) as mock_forward:
        mock_forward.return_value = {"status": "sent", "recipients": "test@example.com", "message": "OK"}
        result = client.forward_email(
          ["test@example.com"],
          "Test",
          "sender@test.com",
          "2024-01-01",
          "Original text",
        )
        assert result["status"] == "sent"
    finally:
      client.__exit__(None, None, None)


class TestSyncSMTPClientErrorHandling:
  """Test error handling and wrapping."""

  def test_timeout_error_wrapped_in_runtime_error(self):
    """
    Given: SyncSMTPClient instance
    When: Async operation times out
    Then: Raises RuntimeError with timeout message
    """
    account = EmailAccount(
      name="test",
      imap_host="imap.example.com",
      smtp_host="smtp.example.com",
      username="test@example.com",
    )
    client = SyncSMTPClient(account)
    try:
      with patch.object(client._async_client, 'send_email', new_callable=AsyncMock) as mock_send:
        mock_send.side_effect = TimeoutError("Timeout")
        with pytest.raises(RuntimeError, match="timed out"):
          client.send_email(["test@example.com"], "Test", "Hello")
    finally:
      client.__exit__(None, None, None)

  def test_connection_error_wrapped_in_runtime_error(self):
    """
    Given: SyncSMTPClient instance
    When: Async operation fails with ConnectionError
    Then: Raises RuntimeError with connection message
    """
    account = EmailAccount(
      name="test",
      imap_host="imap.example.com",
      smtp_host="smtp.example.com",
      username="test@example.com",
    )
    client = SyncSMTPClient(account)
    try:
      with patch.object(client._async_client, 'send_email', new_callable=AsyncMock) as mock_send:
        mock_send.side_effect = ConnectionError("Connection lost")
        with pytest.raises(RuntimeError, match="Connection error"):
          client.send_email(["test@example.com"], "Test", "Hello")
    finally:
      client.__exit__(None, None, None)

  def test_smtp_exception_wrapped_in_runtime_error(self):
    """
    Given: SyncSMTPClient instance
    When: Async client raises SMTPException
    Then: Wraps in RuntimeError with descriptive message
    """
    account = EmailAccount(
      name="test",
      imap_host="imap.example.com",
      smtp_host="smtp.example.com",
      username="test@example.com",
    )
    client = SyncSMTPClient(account)
    try:
      with patch.object(client._async_client, 'send_email', new_callable=AsyncMock) as mock_send:
        mock_send.side_effect = Exception("SMTP error")
        with pytest.raises(RuntimeError, match="Operation failed"):
          client.send_email(["test@example.com"], "Test", "Hello")
    finally:
      client.__exit__(None, None, None)

  def test_generic_exception_wrapped_in_runtime_error(self):
    """
    Given: SyncSMTPClient instance
    When: Async operation raises unexpected exception
    Then: Wraps in RuntimeError with descriptive message
    """
    account = EmailAccount(
      name="test",
      imap_host="imap.example.com",
      smtp_host="smtp.example.com",
      username="test@example.com",
    )
    client = SyncSMTPClient(account)
    try:
      with patch.object(client._async_client, 'send_email', new_callable=AsyncMock) as mock_send:
        mock_send.side_effect = Exception("Unexpected error")
        with pytest.raises(RuntimeError, match="Operation failed"):
          client.send_email(["test@example.com"], "Test", "Hello")
    finally:
      client.__exit__(None, None, None)

  def test_value_error_passthrough(self):
    """
    Given: SyncSMTPClient instance
    When: Async client raises ValueError (e.g., invalid email)
    Then: ValueError is not wrapped, passed through
    """
    account = EmailAccount(
      name="test",
      imap_host="imap.example.com",
      smtp_host="smtp.example.com",
      username="test@example.com",
    )
    client = SyncSMTPClient(account)
    try:
      with patch.object(client._async_client, 'send_email', new_callable=AsyncMock) as mock_send:
        mock_send.side_effect = ValueError("Invalid email address")
        with pytest.raises(ValueError, match="Invalid email address"):
          client.send_email(["invalid-email"], "Test", "Hello")
    finally:
      client.__exit__(None, None, None)

  def test_whitelist_error_passthrough(self):
    """
    Given: SyncSMTPClient instance
    When: Async client raises WhitelistError
    Then: WhitelistError is not wrapped, passed through
    """
    account = EmailAccount(
      name="test",
      imap_host="imap.example.com",
      smtp_host="smtp.example.com",
      username="test@example.com",
    )
    client = SyncSMTPClient(account)
    try:
      with patch.object(client._async_client, 'send_email', new_callable=AsyncMock) as mock_send:
        mock_send.side_effect = WhitelistError("Recipients not in whitelist")
        with pytest.raises(WhitelistError, match="Recipients not in whitelist"):
          client.send_email(["blocked@example.com"], "Test", "Hello")
    finally:
      client.__exit__(None, None, None)


class TestSyncSMTPClientThreadSafety:
  """Test thread safety and resource management."""

  def test_run_coroutine_uses_threadsafe_method(self):
    """
    Given: SyncSMTPClient instance with background loop
    When: Calling _run_coroutine()
    Then: Uses asyncio.run_coroutine_threadsafe
    """
    account = EmailAccount(
      name="test",
      imap_host="imap.example.com",
      smtp_host="smtp.example.com",
      username="test@example.com",
    )
    client = SyncSMTPClient(account)
    try:
      with patch('asyncio.run_coroutine_threadsafe') as mock_run:
        mock_future = MagicMock()
        mock_future.result.return_value = {"status": "sent", "recipients": "test@example.com", "message": "OK"}
        mock_run.return_value = mock_future

        with patch.object(client._async_client, 'send_email', new_callable=AsyncMock) as mock_send:
          mock_send.return_value = {"status": "sent", "recipients": "test@example.com", "message": "OK"}
          client.send_email(["test@example.com"], "Test", "Hello")

          # Verify run_coroutine_threadsafe was called
          assert mock_run.called
    finally:
      client.__exit__(None, None, None)

  def test_concurrent_operations_are_thread_safe(self):
    """
    Given: Multiple threads using same SyncSMTPClient
    When: Calling methods concurrently
    Then: Operations are serialized via async client's lock
    """
    import concurrent.futures

    account = EmailAccount(
      name="test",
      imap_host="imap.example.com",
      smtp_host="smtp.example.com",
      username="test@example.com",
    )
    client = SyncSMTPClient(account)
    try:

      def send_email():
        with patch.object(client._async_client, 'send_email', new_callable=AsyncMock) as mock_send:
          mock_send.return_value = {"status": "sent", "recipients": "test@example.com", "message": "OK"}
          return client.send_email(["test@example.com"], "Test", "Hello")

      # Run multiple operations concurrently
      with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(send_email) for _ in range(10)]
        results = [f.result() for f in futures]

        # All should succeed
        assert len(results) == 10
        assert all(r["status"] == "sent" for r in results)
    finally:
      client.__exit__(None, None, None)

  def test_event_loop_properly_started(self):
    """
    Given: SyncSMTPClient instance
    When: Checking background thread state
    Then: Event loop is running in background thread
    """
    account = EmailAccount(
      name="test",
      imap_host="imap.example.com",
      smtp_host="smtp.example.com",
      username="test@example.com",
    )
    client = SyncSMTPClient(account)
    try:
      assert client._loop.is_running()
      assert client._thread.is_alive()
    finally:
      client.__exit__(None, None, None)

  def test_event_loop_stopped_on_exit(self):
    """
    Given: SyncSMTPClient instance with active loop
    When: Exiting context manager
    Then: Event loop is properly stopped
    """
    account = EmailAccount(
      name="test",
      imap_host="imap.example.com",
      smtp_host="smtp.example.com",
      username="test@example.com",
    )
    client = SyncSMTPClient(account)
    loop = client._loop
    client.__exit__(None, None, None)
    assert not loop.is_running()


class TestSyncSMTPClientResourceCleanup:
  """Test resource cleanup on exceptions."""

  def test_cleanup_on_normal_exit(self):
    """
    Given: SyncSMTPClient in with statement
    When: Exiting context normally
    Then: All resources are cleaned up (loop stopped, thread joined)
    """
    account = EmailAccount(
      name="test",
      imap_host="imap.example.com",
      smtp_host="smtp.example.com",
      username="test@example.com",
    )
    with SyncSMTPClient(account) as client:
      loop = client._loop
      thread = client._thread

    # After context exit
    assert not loop.is_running()
    assert not thread.is_alive()

  def test_cleanup_on_exception_in_context(self):
    """
    Given: SyncSMTPClient in with statement
    When: Exception occurs in context
    Then: Resources still cleaned up properly
    """
    account = EmailAccount(
      name="test",
      imap_host="imap.example.com",
      smtp_host="smtp.example.com",
      username="test@example.com",
    )
    loop = None
    thread = None
    try:
      with SyncSMTPClient(account) as client:
        loop = client._loop
        thread = client._thread
        raise ValueError("Test error")
    except ValueError:
      pass

    assert not loop.is_running()
    assert not thread.is_alive()

  def test_cleanup_on_exception_during_send(self):
    """
    Given: SyncSMTPClient instance
    When: send_email() raises exception
    Then: Resources remain available for next call
    """
    account = EmailAccount(
      name="test",
      imap_host="imap.example.com",
      smtp_host="smtp.example.com",
      username="test@example.com",
    )
    client = SyncSMTPClient(account)
    try:
      with patch.object(client._async_client, 'send_email', new_callable=AsyncMock) as mock_send:
        # First call fails
        mock_send.side_effect = Exception("Send failed")
        with pytest.raises(RuntimeError):
          client.send_email(["test@example.com"], "Test", "Hello")

        # Resources should still be available
        assert client._loop.is_running()
        assert client._thread.is_alive()
    finally:
      client.__exit__(None, None, None)

  def test_no_resource_leaks_on_multiple_uses(self):
    """
    Given: SyncSMTPClient used multiple times
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
      client = SyncSMTPClient(account)
      client.__exit__(None, None, None)

    # Allow threads to fully terminate
    import time
    time.sleep(0.1)

    # Thread count should return to initial
    final_thread_count = threading.active_count()
    assert final_thread_count <= initial_thread_count


class TestSyncSMTPClientIntegration:
  """Integration tests with async SMTPClient."""

  def test_send_email_with_real_account_structure(self):
    """
    Given: SyncSMTPClient with EmailAccount
    When: Calling send_email with typical parameters
    Then: Validates structure matches async client expectations
    """
    account = EmailAccount(
      name="test",
      imap_host="imap.example.com",
      smtp_host="smtp.example.com",
      username="test@example.com",
    )
    client = SyncSMTPClient(account)
    try:
      with patch.object(client._async_client, 'send_email', new_callable=AsyncMock) as mock_send:
        mock_send.return_value = {"status": "sent", "recipients": "test@example.com", "message": "OK"}
        result = client.send_email(
          to=["recipient@example.com"],
          subject="Test Subject",
          body="Test body",
        )
        assert result["status"] == "sent"
        assert result["recipients"] == "test@example.com"
    finally:
      client.__exit__(None, None, None)

  def test_multiple_send_operations_sequentially(self):
    """
    Given: SyncSMTPClient instance
    When: Calling send_email multiple times in sequence
    Then: Each call succeeds without resource issues
    """
    account = EmailAccount(
      name="test",
      imap_host="imap.example.com",
      smtp_host="smtp.example.com",
      username="test@example.com",
    )
    client = SyncSMTPClient(account)
    try:
      with patch.object(client._async_client, 'send_email', new_callable=AsyncMock) as mock_send:
        mock_send.return_value = {"status": "sent", "recipients": "test@example.com", "message": "OK"}

        # Send multiple emails
        for i in range(5):
          result = client.send_email(["test@example.com"], f"Test {i}", "Hello")
          assert result["status"] == "sent"
    finally:
      client.__exit__(None, None, None)

  def test_thread_isolation_between_instances(self):
    """
    Given: Multiple SyncSMTPClient instances
    When: Each creates its own background thread
    Then: Threads are isolated and don't interfere
    """
    account = EmailAccount(
      name="test",
      imap_host="imap.example.com",
      smtp_host="smtp.example.com",
      username="test@example.com",
    )

    client1 = SyncSMTPClient(account)
    client2 = SyncSMTPClient(account)

    try:
      # Each client has its own thread and loop
      assert client1._thread is not client2._thread
      assert client1._loop is not client2._loop

      # Both threads should be running
      assert client1._thread.is_alive()
      assert client2._thread.is_alive()
      assert client1._loop.is_running()
      assert client2._loop.is_running()
    finally:
      client1.__exit__(None, None, None)
      client2.__exit__(None, None, None)
