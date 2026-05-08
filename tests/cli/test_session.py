"""Tests for Session Manager in cli/session.py."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from simple_email_gw.cli.session import Session
from simple_email_gw.config import EmailAccount


class TestSessionInitialization:
  """Tests for Session initialization."""

  def test_session_initializes_with_no_account(self):
    """
    Given: A new Session instance
    When: Session is created
    Then: current_account is None, current_folder is "INBOX"
    """
    session = Session()
    assert session.current_account is None
    assert session.current_folder == "INBOX"

  def test_session_initializes_with_no_clients(self):
    """
    Given: A new Session instance
    When: Session is created
    Then: _imap_client and _smtp_client are None
    """
    session = Session()
    assert session._imap_client is None
    assert session._smtp_client is None

  def test_session_initializes_with_empty_email_cache(self):
    """
    Given: A new Session instance
    When: Session is created
    Then: _email_cache is empty dict, _cache_folder is None
    """
    session = Session()
    assert session._email_cache == {}
    assert session._cache_folder is None


class TestAccountSelection:
  """Tests for set_account method."""

  def test_set_account_stores_account(self, mock_account):
    """
    Given: A Session instance and a valid EmailAccount
    When: set_account is called
    Then: current_account is set to the provided account
    """
    session = Session()
    session.set_account(mock_account)
    assert session.current_account == mock_account

  def test_set_account_clears_existing_clients(self, mock_account):
    """
    Given: A Session with an active account and clients
    When: set_account is called with a new account
    Then: Existing IMAP and SMTP clients are disconnected and cleared
    """
    session = Session()
    session.set_account(mock_account)
    # Simulate existing clients
    session._imap_client = MagicMock()
    session._smtp_client = MagicMock()
    # Set a new account
    new_account = EmailAccount(
      name="new_test",
      imap_host="imap.new.com",
      imap_port=993,
      smtp_host="smtp.new.com",
      smtp_port=587,
      username="new@test.com",
      password="new_password",
      auth_method="password",
    )
    session.set_account(new_account)
    # Clients should be cleared
    assert session._imap_client is None
    assert session._smtp_client is None

  def test_set_account_clears_email_cache(self, mock_account):
    """
    Given: A Session with cached emails
    When: set_account is called with a new account
    Then: Email cache is cleared
    """
    session = Session()
    session.set_account(mock_account)
    session.cache_email("msg1", {"subject": "Test"})
    new_account = EmailAccount(
      name="new_test",
      imap_host="imap.new.com",
      imap_port=993,
      smtp_host="smtp.new.com",
      smtp_port=587,
      username="new@test.com",
      password="new_password",
      auth_method="password",
    )
    session.set_account(new_account)
    assert session._email_cache == {}

  def test_set_account_resets_folder_to_inbox(self, mock_account):
    """
    Given: A Session with current_folder set to different folder
    When: set_account is called with a new account
    Then: current_folder is reset to "INBOX"
    """
    session = Session()
    session.set_account(mock_account)
    session.set_folder("Sent")
    new_account = EmailAccount(
      name="new_test",
      imap_host="imap.new.com",
      imap_port=993,
      smtp_host="smtp.new.com",
      smtp_port=587,
      username="new@test.com",
      password="new_password",
      auth_method="password",
    )
    session.set_account(new_account)
    assert session.current_folder == "INBOX"

  def test_set_account_to_none_clears_session(self):
    """
    Given: A Session with an active account
    When: set_account is called with None
    Then: current_account is None, clients are disconnected, cache cleared
    """
    session = Session()
    mock_account = EmailAccount(
      name="test",
      imap_host="imap.test.com",
      imap_port=993,
      smtp_host="smtp.test.com",
      smtp_port=587,
      username="test@test.com",
      password="test_password",
      auth_method="password",
    )
    session.set_account(mock_account)
    session.set_account(None)
    assert session.current_account is None
    assert session._imap_client is None
    assert session._smtp_client is None
    assert session._email_cache == {}


class TestFolderManagement:
  """Tests for set_folder method."""

  def test_set_folder_updates_current_folder(self):
    """
    Given: A Session instance
    When: set_folder is called with a folder name
    Then: current_folder is updated to the provided folder name
    """
    session = Session()
    session.set_folder("Sent")
    assert session.current_folder == "Sent"

  def test_set_folder_clears_email_cache(self):
    """
    Given: A Session with cached emails
    When: set_folder is called with a new folder
    Then: Email cache is cleared
    """
    session = Session()
    session.cache_email("msg1", {"subject": "Test"})
    session.set_folder("Sent")
    assert session._email_cache == {}

  def test_set_folder_updates_cache_folder(self):
    """
    Given: A Session instance
    When: set_folder is called with a folder name
    Then: _cache_folder is updated to the new folder name
    """
    session = Session()
    session.set_folder("Sent")
    assert session._cache_folder == "Sent"


class TestIMAPClientCreation:
  """Tests for get_imap_client method."""

  @pytest.mark.asyncio
  async def test_get_imap_client_creates_client_when_none_exists(self, mock_account):
    """
    Given: A Session with an account set but no IMAP client
    When: get_imap_client is called
    Then: A new IMAPClient is created and cached
    """
    session = Session()
    session.set_account(mock_account)

    with patch("simple_email_gw.cli.session.get_pool") as mock_get_pool:
      mock_pool = AsyncMock()
      mock_imap_client = AsyncMock()
      mock_pool.get_imap_client = AsyncMock(return_value=mock_imap_client)
      mock_get_pool.return_value = mock_pool

      client = await session.get_imap_client()
      assert client == mock_imap_client
      mock_pool.get_imap_client.assert_called_once_with(mock_account.name)

  @pytest.mark.asyncio
  async def test_get_imap_client_returns_cached_client(self, mock_account):
    """
    Given: A Session with an existing IMAP client
    When: get_imap_client is called again
    Then: The same cached client is returned
    """
    session = Session()
    session.set_account(mock_account)

    with patch("simple_email_gw.cli.session.get_pool") as mock_get_pool:
      mock_pool = AsyncMock()
      mock_imap_client = AsyncMock()
      mock_pool.get_imap_client = AsyncMock(return_value=mock_imap_client)
      mock_get_pool.return_value = mock_pool

      client1 = await session.get_imap_client()
      client2 = await session.get_imap_client()
      assert client1 == client2
      # Should only call pool.get_imap_client once (second call uses cache)
      mock_pool.get_imap_client.assert_called_once()

  @pytest.mark.asyncio
  async def test_get_imap_client_raises_error_without_account(self):
    """
    Given: A Session with no account set
    When: get_imap_client is called
    Then: RuntimeError is raised with appropriate message
    """
    session = Session()
    with pytest.raises(RuntimeError, match="No account selected"):
      await session.get_imap_client()

  @pytest.mark.asyncio
  async def test_get_imap_client_uses_connection_pool(self, mock_account):
    """
    Given: A Session with an account set
    When: get_imap_client is called
    Then: ConnectionPool is used to get/create the client
    """
    session = Session()
    session.set_account(mock_account)

    with patch("simple_email_gw.cli.session.get_pool") as mock_get_pool:
      mock_pool = AsyncMock()
      mock_imap_client = AsyncMock()
      mock_pool.get_imap_client = AsyncMock(return_value=mock_imap_client)
      mock_get_pool.return_value = mock_pool

      await session.get_imap_client()
      mock_get_pool.assert_called_once()

  @pytest.mark.asyncio
  async def test_get_imap_client_handles_rate_limit_error(self, mock_account):
    """
    Given: A Session with an account and rate limit exceeded
    When: get_imap_client is called
    Then: RateLimitError is handled appropriately
    """
    from simple_email_gw.connections.pool import RateLimitError

    session = Session()
    session.set_account(mock_account)

    with patch("simple_email_gw.cli.session.get_pool") as mock_get_pool:
      mock_pool = AsyncMock()
      mock_pool.get_imap_client = AsyncMock(side_effect=RateLimitError("Rate limit exceeded"))
      mock_get_pool.return_value = mock_pool

      with pytest.raises(RateLimitError):
        await session.get_imap_client()


class TestSMTPClientCreation:
  """Tests for get_smtp_client method."""

  @pytest.mark.asyncio
  async def test_get_smtp_client_creates_client_when_none_exists(self, mock_account):
    """
    Given: A Session with an account set but no SMTP client
    When: get_smtp_client is called
    Then: A new SMTPClient is created and cached
    """
    session = Session()
    session.set_account(mock_account)

    with patch("simple_email_gw.cli.session.get_pool") as mock_get_pool:
      mock_pool = AsyncMock()
      mock_smtp_client = AsyncMock()
      mock_pool.get_smtp_client = AsyncMock(return_value=mock_smtp_client)
      mock_get_pool.return_value = mock_pool

      client = await session.get_smtp_client()
      assert client == mock_smtp_client
      mock_pool.get_smtp_client.assert_called_once_with(mock_account.name)

  @pytest.mark.asyncio
  async def test_get_smtp_client_returns_cached_client(self, mock_account):
    """
    Given: A Session with an existing SMTP client
    When: get_smtp_client is called again
    Then: The same cached client is returned
    """
    session = Session()
    session.set_account(mock_account)

    with patch("simple_email_gw.cli.session.get_pool") as mock_get_pool:
      mock_pool = AsyncMock()
      mock_smtp_client = AsyncMock()
      mock_pool.get_smtp_client = AsyncMock(return_value=mock_smtp_client)
      mock_get_pool.return_value = mock_pool

      client1 = await session.get_smtp_client()
      client2 = await session.get_smtp_client()
      assert client1 == client2
      # Should only call pool.get_smtp_client once (second call uses cache)
      mock_pool.get_smtp_client.assert_called_once()

  @pytest.mark.asyncio
  async def test_get_smtp_client_raises_error_without_account(self):
    """
    Given: A Session with no account set
    When: get_smtp_client is called
    Then: RuntimeError is raised with appropriate message
    """
    session = Session()
    with pytest.raises(RuntimeError, match="No account selected"):
      await session.get_smtp_client()

  @pytest.mark.asyncio
  async def test_get_smtp_client_uses_connection_pool(self, mock_account):
    """
    Given: A Session with an account set
    When: get_smtp_client is called
    Then: ConnectionPool is used to get/create the client
    """
    session = Session()
    session.set_account(mock_account)

    with patch("simple_email_gw.cli.session.get_pool") as mock_get_pool:
      mock_pool = AsyncMock()
      mock_smtp_client = AsyncMock()
      mock_pool.get_smtp_client = AsyncMock(return_value=mock_smtp_client)
      mock_get_pool.return_value = mock_pool

      await session.get_smtp_client()
      mock_get_pool.assert_called_once()

  @pytest.mark.asyncio
  async def test_get_smtp_client_handles_rate_limit_error(self, mock_account):
    """
    Given: A Session with an account and rate limit exceeded
    When: get_smtp_client is called
    Then: RateLimitError is handled appropriately
    """
    from simple_email_gw.connections.pool import RateLimitError

    session = Session()
    session.set_account(mock_account)

    with patch("simple_email_gw.cli.session.get_pool") as mock_get_pool:
      mock_pool = AsyncMock()
      mock_pool.get_smtp_client = AsyncMock(side_effect=RateLimitError("Rate limit exceeded"))
      mock_get_pool.return_value = mock_pool

      with pytest.raises(RateLimitError):
        await session.get_smtp_client()


class TestConnectionCleanup:
  """Tests for disconnect method."""

  @pytest.mark.asyncio
  async def test_disconnect_disconnects_imap_client(self, mock_account):
    """
    Given: A Session with an active IMAP client
    When: disconnect is called
    Then: IMAP client is disconnected and cleared
    """
    session = Session()
    session.set_account(mock_account)

    with patch("simple_email_gw.cli.session.get_pool") as mock_get_pool:
      mock_pool = AsyncMock()
      mock_imap_client = AsyncMock()
      mock_pool.get_imap_client = AsyncMock(return_value=mock_imap_client)
      mock_get_pool.return_value = mock_pool

      await session.get_imap_client()
      await session.disconnect()

      mock_imap_client.disconnect.assert_called_once()
      assert session._imap_client is None

  @pytest.mark.asyncio
  async def test_disconnect_disconnects_smtp_client(self, mock_account):
    """
    Given: A Session with an active SMTP client
    When: disconnect is called
    Then: SMTP client is cleared
    """
    session = Session()
    session.set_account(mock_account)

    with patch("simple_email_gw.cli.session.get_pool") as mock_get_pool:
      mock_pool = AsyncMock()
      mock_smtp_client = AsyncMock()
      mock_pool.get_smtp_client = AsyncMock(return_value=mock_smtp_client)
      mock_get_pool.return_value = mock_pool

      await session.get_smtp_client()
      await session.disconnect()

      assert session._smtp_client is None

  @pytest.mark.asyncio
  async def test_disconnect_handles_no_clients(self):
    """
    Given: A Session with no active clients
    When: disconnect is called
    Then: No errors are raised
    """
    session = Session()
    await session.disconnect()  # Should not raise any errors

  @pytest.mark.asyncio
  async def test_disconnect_clears_email_cache(self):
    """
    Given: A Session with cached emails
    When: disconnect is called
    Then: Email cache is cleared
    """
    session = Session()
    session.cache_email("msg1", {"subject": "Test"})
    await session.disconnect()
    assert session._email_cache == {}

  @pytest.mark.asyncio
  async def test_disconnect_resets_session_state(self):
    """
    Given: A Session with active account and clients
    When: disconnect is called
    Then: Account remains set but clients are cleared
    """
    session = Session()
    mock_account = EmailAccount(
      name="test",
      imap_host="imap.test.com",
      imap_port=993,
      smtp_host="smtp.test.com",
      smtp_port=587,
      username="test@test.com",
      password="test_password",
      auth_method="password",
    )
    session.set_account(mock_account)

    with patch("simple_email_gw.cli.session.get_pool") as mock_get_pool:
      mock_pool = AsyncMock()
      mock_imap_client = AsyncMock()
      mock_pool.get_imap_client = AsyncMock(return_value=mock_imap_client)
      mock_get_pool.return_value = mock_pool

      await session.get_imap_client()
      await session.disconnect()

      # Account should still be set
      assert session.current_account == mock_account
      # But clients should be cleared
      assert session._imap_client is None
      assert session._smtp_client is None


class TestEmailCaching:
  """Tests for email caching functionality."""

  def test_cache_email_stores_email(self):
    """
    Given: A Session instance
    When: cache_email is called with a message ID and email data
    Then: Email is stored in _email_cache under the message ID
    """
    session = Session()
    email_data = {"subject": "Test Email", "from": "sender@example.com"}
    session.cache_email("msg1", email_data)
    assert session._email_cache["msg1"] == email_data

  def test_cache_email_overwrites_existing(self):
    """
    Given: A Session with a cached email
    When: cache_email is called with same message ID but different data
    Then: Existing cache entry is overwritten
    """
    session = Session()
    email_data1 = {"subject": "Test Email 1"}
    email_data2 = {"subject": "Test Email 2"}
    session.cache_email("msg1", email_data1)
    session.cache_email("msg1", email_data2)
    assert session._email_cache["msg1"] == email_data2

  def test_get_cached_email_returns_cached_email(self):
    """
    Given: A Session with cached emails
    When: get_cached_email is called with a message ID
    Then: The cached email data is returned
    """
    session = Session()
    email_data = {"subject": "Test Email"}
    session.set_folder("INBOX")
    session.cache_email("msg1", email_data)
    result = session.get_cached_email("msg1")
    assert result == email_data

  def test_get_cached_email_returns_none_for_missing(self):
    """
    Given: A Session with cached emails
    When: get_cached_email is called with non-existent message ID
    Then: None is returned
    """
    session = Session()
    session.set_folder("INBOX")
    result = session.get_cached_email("nonexistent")
    assert result is None

  def test_get_cached_email_checks_folder_match(self):
    """
    Given: A Session with cached emails from folder "INBOX"
    When: get_cached_email is called after changing to folder "Sent"
    Then: None is returned (cache is invalid for new folder)
    """
    session = Session()
    email_data = {"subject": "Test Email"}
    session.set_folder("INBOX")
    session.cache_email("msg1", email_data)
    # Change folder - this clears the cache
    session.set_folder("Sent")
    result = session.get_cached_email("msg1")
    assert result is None

  def test_clear_cache_empties_cache(self):
    """
    Given: A Session with cached emails
    When: clear_cache is called
    Then: _email_cache becomes empty dict
    """
    session = Session()
    session.cache_email("msg1", {"subject": "Test"})
    session.clear_cache()
    assert session._email_cache == {}

  def test_clear_cache_resets_cache_folder(self):
    """
    Given: A Session with _cache_folder set
    When: clear_cache is called
    Then: _cache_folder is set to None
    """
    session = Session()
    session.set_folder("INBOX")
    session.clear_cache()
    assert session._cache_folder is None


class TestSessionIntegrationWithConnectionPool:
  """Tests for Session integration with ConnectionPool."""

  @pytest.mark.asyncio
  async def test_session_uses_global_connection_pool(self, mock_account):
    """
    Given: A Session instance
    When: get_imap_client or get_smtp_client is called
    Then: The global ConnectionPool singleton is used
    """
    session = Session()
    session.set_account(mock_account)

    with patch("simple_email_gw.cli.session.get_pool") as mock_get_pool:
      mock_pool = AsyncMock()
      mock_client = AsyncMock()
      mock_pool.get_imap_client = AsyncMock(return_value=mock_client)
      mock_get_pool.return_value = mock_pool

      await session.get_imap_client()
      mock_get_pool.assert_called_once()

  @pytest.mark.asyncio
  async def test_session_accounts_match_pool_accounts(self, mock_account):
    """
    Given: A Session with account set
    When: Getting clients
    Then: Account name matches what ConnectionPool expects
    """
    session = Session()
    session.set_account(mock_account)

    with patch("simple_email_gw.cli.session.get_pool") as mock_get_pool:
      mock_pool = AsyncMock()
      mock_client = AsyncMock()
      mock_pool.get_imap_client = AsyncMock(return_value=mock_client)
      mock_get_pool.return_value = mock_pool

      await session.get_imap_client()
      mock_pool.get_imap_client.assert_called_once_with(mock_account.name)

  @pytest.mark.asyncio
  async def test_session_disconnect_delegates_to_pool(self, mock_account):
    """
    Given: A Session with active clients
    When: disconnect is called
    Then: ConnectionPool disconnect_all is not called (only session-level cleanup)
    """
    session = Session()
    session.set_account(mock_account)

    with patch("simple_email_gw.cli.session.get_pool") as mock_get_pool:
      mock_pool = AsyncMock()
      mock_imap_client = AsyncMock()
      mock_pool.get_imap_client = AsyncMock(return_value=mock_imap_client)
      mock_get_pool.return_value = mock_pool

      await session.get_imap_client()
      await session.disconnect()

      # Should not call disconnect_all on the pool
      # Only disconnect on the individual client
      mock_imap_client.disconnect.assert_called_once()
      # Pool should not have disconnect_all called
      assert not hasattr(mock_pool, "disconnect_all") or not mock_pool.disconnect_all.called


class TestSessionEdgeCases:
  """Tests for edge cases and error handling."""

  def test_session_multiple_account_switches(self, mock_account, mock_oauth_account):
    """
    Given: A Session with one account active
    When: set_account is called multiple times with different accounts
    Then: Session state reflects the latest account
    """
    session = Session()
    session.set_account(mock_account)
    assert session.current_account == mock_account

    session.set_account(mock_oauth_account)
    assert session.current_account == mock_oauth_account

    session.set_account(mock_account)
    assert session.current_account == mock_account

  def test_session_folder_with_special_characters(self):
    """
    Given: A Session instance
    When: set_folder is called with folder name containing special chars
    Then: Folder name is stored as-is (sanitization happens in client)
    """
    session = Session()
    session.set_folder("Sent Items/SubFolder")
    assert session.current_folder == "Sent Items/SubFolder"

  @pytest.mark.asyncio
  async def test_session_concurrent_client_requests(self, mock_account):
    """
    Given: A Session instance
    When: Multiple concurrent calls to get_imap_client
    Then: Only one client is created (thread-safe)
    """
    session = Session()
    session.set_account(mock_account)

    with patch("simple_email_gw.cli.session.get_pool") as mock_get_pool:
      mock_pool = AsyncMock()
      mock_client = AsyncMock()
      mock_pool.get_imap_client = AsyncMock(return_value=mock_client)
      mock_get_pool.return_value = mock_pool

      # Make concurrent requests
      import asyncio

      results = await asyncio.gather(
        session.get_imap_client(),
        session.get_imap_client(),
        session.get_imap_client(),
      )

      # All should return the same client
      assert results[0] == results[1] == results[2]

  def test_session_email_cache_size_limit(self):
    """
    Given: A Session with many cached emails
    When: Cache reaches practical limit
    Then: Older entries may be evicted (implementation-defined)
    Note: This is optional behavior - implementation may vary
    """
    session = Session()
    session.set_folder("INBOX")

    # Cache multiple emails
    for i in range(100):
      session.cache_email(f"msg{i}", {"subject": f"Email {i}"})

    # All emails should be cached (no eviction in current implementation)
    assert len(session._email_cache) == 100

  @pytest.mark.asyncio
  async def test_session_client_creation_failure(self, mock_account):
    """
    Given: A Session with an account set
    When: get_imap_client fails due to connection error
    Then: Error is propagated, no client is cached
    """
    session = Session()
    session.set_account(mock_account)

    with patch("simple_email_gw.cli.session.get_pool") as mock_get_pool:
      mock_pool = AsyncMock()
      mock_pool.get_imap_client = AsyncMock(side_effect=Exception("Connection failed"))
      mock_get_pool.return_value = mock_pool

      with pytest.raises(Exception, match="Connection failed"):
        await session.get_imap_client()

      # Client should not be cached
      assert session._imap_client is None

  def test_session_string_representation(self):
    """
    Given: A Session instance
    When: str() or repr() is called
    Then: Returns useful representation with account and folder info
    """
    session = Session()
    assert "none" in str(session).lower()
    assert "INBOX" in str(session)

    mock_account = EmailAccount(
      name="test",
      imap_host="imap.test.com",
      imap_port=993,
      smtp_host="smtp.test.com",
      smtp_port=587,
      username="test@test.com",
      password="test_password",
      auth_method="password",
    )
    session.set_account(mock_account)
    assert "test" in str(session)
    assert "INBOX" in str(session)

    # Test repr
    repr_str = repr(session)
    assert "Session" in repr_str
    assert "current_account" in repr_str
    assert "current_folder" in repr_str
