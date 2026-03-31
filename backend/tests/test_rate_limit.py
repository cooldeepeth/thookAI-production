"""Tests for rate limiting middleware in-memory fallback.

These tests verify the RateLimiter class works correctly without Redis,
using the in-memory sliding window fallback.
"""

import pytest
from middleware.security import RateLimiter


@pytest.mark.asyncio
async def test_rate_limiter_in_memory_allows_under_limit():
    """Requests under the limit should be allowed with correct remaining count."""
    limiter = RateLimiter()
    is_limited, remaining = limiter._is_rate_limited_memory("test:key", limit=5)
    assert is_limited is False
    assert remaining == 4


@pytest.mark.asyncio
async def test_rate_limiter_in_memory_blocks_over_limit():
    """Requests exceeding the limit should be blocked with 0 remaining."""
    limiter = RateLimiter()
    for i in range(5):
        limiter._is_rate_limited_memory("test:block", limit=5)
    is_limited, remaining = limiter._is_rate_limited_memory("test:block", limit=5)
    assert is_limited is True
    assert remaining == 0


@pytest.mark.asyncio
async def test_rate_limiter_async_fallback_without_redis():
    """When Redis is unavailable, is_rate_limited falls back to in-memory."""
    limiter = RateLimiter()
    is_limited, remaining = await limiter.is_rate_limited("test:async", limit=10)
    assert is_limited is False
    assert remaining >= 0
