"""Tests for rate limiting."""

import asyncio

import pytest

from simple_email_gw.safety.rate_limiter import RateLimiter


class TestRateLimiter:
  """Tests for RateLimiter class."""

  @pytest.mark.asyncio
  async def test_allows_within_limit(self):
    """Test requests within limit are allowed."""
    limiter = RateLimiter(rate=5, window=60)

    for _ in range(5):
      result = await limiter.acquire("test_key")
      assert result is True

  @pytest.mark.asyncio
  async def test_blocks_over_limit(self):
    """Test requests over limit are blocked."""
    limiter = RateLimiter(rate=2, window=60)

    assert await limiter.acquire("test_key") is True
    assert await limiter.acquire("test_key") is True
    assert await limiter.acquire("test_key") is False

  @pytest.mark.asyncio
  async def test_separate_keys(self):
    """Test different keys have separate limits."""
    limiter = RateLimiter(rate=2, window=60)

    # Exhaust key1
    assert await limiter.acquire("key1") is True
    assert await limiter.acquire("key1") is True
    assert await limiter.acquire("key1") is False

    # key2 should still work
    assert await limiter.acquire("key2") is True

  @pytest.mark.asyncio
  async def test_window_expiry(self):
    """Test requests expire after window."""
    limiter = RateLimiter(rate=1, window=1)  # 1 request per second

    assert await limiter.acquire("test_key") is True
    assert await limiter.acquire("test_key") is False

    # Wait for window to expire
    await asyncio.sleep(1.1)

    assert await limiter.acquire("test_key") is True

  @pytest.mark.asyncio
  async def test_wait_and_acquire_success(self):
    """Test wait_and_acquire succeeds when slot available."""
    limiter = RateLimiter(rate=1, window=1)

    result = await limiter.wait_and_acquire("test_key", max_wait=0.5)
    assert result is True

  @pytest.mark.asyncio
  async def test_wait_and_acquire_timeout(self):
    """Test wait_and_acquire times out."""
    limiter = RateLimiter(rate=1, window=60)

    # Exhaust the limit
    await limiter.acquire("test_key")

    # Should timeout
    result = await limiter.wait_and_acquire("test_key", max_wait=0.1)
    assert result is False
