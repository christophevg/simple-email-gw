"""Connection pool manager for IMAP and SMTP."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from simple_email_gw.config import EmailAccount, get_accounts
from simple_email_gw.imap.client import IMAPClient
from simple_email_gw.safety.audit import log_rate_limited
from simple_email_gw.safety.rate_limiter import imap_limiter, smtp_limiter
from simple_email_gw.smtp.client import SMTPClient

if TYPE_CHECKING:
  pass


class RateLimitError(RuntimeError):
  """Raised when a rate limit is exceeded."""
  pass


class ConnectionPool:
  """Manages connections for multiple email accounts."""

  _instance: ConnectionPool | None = None
  _init_lock: asyncio.Lock = asyncio.Lock()
  _imap_clients: dict[str, IMAPClient]
  _smtp_clients: dict[str, SMTPClient]
  _accounts: list[EmailAccount] | None
  _client_lock: asyncio.Lock

  def __new__(cls) -> ConnectionPool:
    """Create singleton instance with thread-safe initialization."""
    if cls._instance is None:
      cls._instance = super().__new__(cls)
      instance = cls._instance
      instance._imap_clients = {}
      instance._smtp_clients = {}
      instance._accounts = None
      instance._client_lock = asyncio.Lock()
    return cls._instance

  @classmethod
  async def create(cls) -> ConnectionPool:
    """Async factory for thread-safe singleton creation."""
    async with cls._init_lock:
      if cls._instance is None:
        instance = cls()
        cls._instance = instance
      return cls._instance

  async def get_accounts(self) -> list[EmailAccount]:
    """Get list of configured accounts."""
    if self._accounts is None:
      self._accounts = get_accounts()
    return self._accounts

  async def get_imap_client(self, account_name: str) -> IMAPClient:
    """Get or create IMAP client for account.

    Raises:
      ValueError: If account not found
      RateLimitError: If rate limited
    """
    # Check rate limit first
    if not await imap_limiter.acquire(account_name):
      log_rate_limited(account_name, "imap", 60, 60)
      raise RateLimitError("IMAP rate limit exceeded for account")

    async with self._client_lock:
      if account_name not in self._imap_clients:
        accounts = await self.get_accounts()
        account = next((a for a in accounts if a.name == account_name), None)
        if not account:
          raise ValueError(f"Account not found: {account_name}")
        self._imap_clients[account_name] = IMAPClient(account)
      return self._imap_clients[account_name]

  async def get_smtp_client(self, account_name: str) -> SMTPClient:
    """Get or create SMTP client for account.

    Raises:
      ValueError: If account not found
      RateLimitError: If rate limited
    """
    # Check rate limit first
    if not await smtp_limiter.acquire(account_name):
      log_rate_limited(account_name, "smtp", 100, 3600)
      raise RateLimitError("SMTP rate limit exceeded for account")

    async with self._client_lock:
      if account_name not in self._smtp_clients:
        accounts = await self.get_accounts()
        account = next((a for a in accounts if a.name == account_name), None)
        if not account:
          raise ValueError(f"Account not found: {account_name}")
        self._smtp_clients[account_name] = SMTPClient(account)
      return self._smtp_clients[account_name]

  async def disconnect_all(self) -> None:
    """Disconnect all clients."""
    async with self._client_lock:
      for client in self._imap_clients.values():
        await client.disconnect()
      self._imap_clients.clear()
      self._smtp_clients.clear()


# Module-level pool (created on first use)
_pool: ConnectionPool | None = None
_pool_lock: asyncio.Lock = asyncio.Lock()


async def get_pool() -> ConnectionPool:
  """Get the global connection pool (async)."""
  global _pool
  async with _pool_lock:
    if _pool is None:
      _pool = await ConnectionPool.create()
    return _pool
