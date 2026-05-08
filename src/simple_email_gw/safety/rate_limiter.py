"""Rate limiting for email operations."""

from __future__ import annotations

import asyncio
import time
from collections import defaultdict
from dataclasses import dataclass, field


@dataclass
class RateLimiter:
  """Token bucket rate limiter."""

  rate: int  # Max requests per window
  window: int  # Window in seconds

  _requests: dict[str, list[float]] = field(default_factory=lambda: defaultdict(list))
  _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

  async def acquire(self, key: str) -> bool:
    """Check if request is allowed under rate limit.

    Args:
      key: Unique identifier (e.g., account name)

    Returns:
      True if request is allowed, False if rate limited
    """
    async with self._lock:
      now = time.monotonic()
      # Remove requests outside the window
      self._requests[key] = [t for t in self._requests[key] if now - t < self.window]

      if len(self._requests[key]) >= self.rate:
        return False

      self._requests[key].append(now)
      return True

  async def wait_and_acquire(self, key: str, max_wait: float = 60.0) -> bool:
    """Wait until request is allowed or timeout.

    Args:
      key: Unique identifier
      max_wait: Maximum time to wait in seconds

    Returns:
      True if request was acquired, False if timed out
    """
    start = time.monotonic()
    while time.monotonic() - start < max_wait:
      if await self.acquire(key):
        return True
      # Wait for oldest request to expire
      await asyncio.sleep(1.0)
    return False


# Default rate limiters
imap_limiter = RateLimiter(rate=60, window=60)  # 60 requests/minute
smtp_limiter = RateLimiter(rate=100, window=3600)  # 100 sends/hour
