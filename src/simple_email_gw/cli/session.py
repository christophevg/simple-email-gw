"""
Session state manager for CLI operations.

This module contains the Session class that manages the current state
of the CLI session, including active account, current folder, and cached
connections to IMAP and SMTP clients.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from simple_email_gw.config import EmailAccount
from simple_email_gw.connections.pool import get_pool

if TYPE_CHECKING:
  from simple_email_gw.imap.client import IMAPClient
  from simple_email_gw.smtp.client import SMTPClient


class Session:
  """Manages CLI session state including account, folder, and client connections."""

  def __init__(self) -> None:
    """Initialize a new session with no active account or clients."""
    self.current_account: EmailAccount | None = None
    self.current_folder: str = "INBOX"
    self._imap_client: IMAPClient | None = None
    self._smtp_client: SMTPClient | None = None
    self._email_cache: dict[str, Any] = {}
    self._cache_folder: str | None = None

  def set_account(self, account: EmailAccount | None) -> None:
    """Set the current account and clear any existing connections.

    Args:
      account: The email account to use, or None to clear the session.
    """
    # Update account
    self.current_account = account

    # Clear session state
    # Note: Clients will be disconnected when garbage collected or via disconnect()
    self._imap_client = None
    self._smtp_client = None
    self.clear_cache()

    # Reset folder to default
    self.current_folder = "INBOX"

  def set_folder(self, folder: str) -> None:
    """Set the current folder.

    Args:
      folder: The folder name to select.
    """
    self.current_folder = folder
    # Clear cache when changing folders
    self.clear_cache()
    self._cache_folder = folder

  async def get_imap_client(self) -> IMAPClient:
    """Get or create an IMAP client for the current account.

    Returns:
      The IMAP client for the current account.

    Raises:
      RuntimeError: If no account is set.
      RateLimitError: If rate limit is exceeded.
      ValueError: If account not found in pool.
    """
    if self.current_account is None:
      raise RuntimeError("No account selected. Use 'use <account>' to select an account.")

    # Return cached client if available
    if self._imap_client is not None:
      return self._imap_client

    # Get client from connection pool
    pool = await get_pool()
    client = await pool.get_imap_client(self.current_account.name)
    self._imap_client = client
    return client

  async def get_smtp_client(self) -> SMTPClient:
    """Get or create an SMTP client for the current account.

    Returns:
      The SMTP client for the current account.

    Raises:
      RuntimeError: If no account is set.
      RateLimitError: If rate limit is exceeded.
      ValueError: If account not found in pool.
    """
    if self.current_account is None:
      raise RuntimeError("No account selected. Use 'use <account>' to select an account.")

    # Return cached client if available
    if self._smtp_client is not None:
      return self._smtp_client

    # Get client from connection pool
    pool = await get_pool()
    client = await pool.get_smtp_client(self.current_account.name)
    self._smtp_client = client
    return client

  async def disconnect(self) -> None:
    """Disconnect all clients and clear session state."""
    # Disconnect IMAP client
    if self._imap_client is not None:
      try:
        await self._imap_client.disconnect()
      except Exception:
        # Ignore errors during disconnect
        pass
      self._imap_client = None

    # Clear SMTP client (no disconnect needed)
    self._smtp_client = None

    # Clear email cache
    self.clear_cache()

  def cache_email(self, message_id: str, email_data: Any) -> None:
    """Cache email data for the given message ID.

    Args:
      message_id: The message ID to cache under.
      email_data: The email data to cache.
    """
    self._email_cache[message_id] = email_data

  def get_cached_email(self, message_id: str) -> Any | None:
    """Retrieve cached email data for the given message ID.

    Args:
      message_id: The message ID to retrieve.

    Returns:
      The cached email data, or None if not found or folder mismatch.
    """
    # Check if cache is for current folder
    if self._cache_folder != self.current_folder:
      return None

    return self._email_cache.get(message_id)

  def clear_cache(self) -> None:
    """Clear the email cache."""
    self._email_cache = {}
    self._cache_folder = None

  def __str__(self) -> str:
    """Return a string representation of the session state."""
    account_name = self.current_account.name if self.current_account else "none"
    return f"Session(account={account_name}, folder={self.current_folder})"

  def __repr__(self) -> str:
    """Return a detailed representation of the session state."""
    return (
      f"Session(current_account={self.current_account!r}, "
      f"current_folder={self.current_folder!r}, "
      f"_imap_client={self._imap_client!r}, "
      f"_smtp_client={self._smtp_client!r})"
    )
