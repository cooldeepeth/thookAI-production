"""
Shared async Redis connection for middleware.

Provides a lazily-initialized Redis connection pool used by both
RateLimitMiddleware and CacheMiddleware. If Redis is not configured
or unavailable, callers receive None and should fall back gracefully.
"""

import logging
from typing import Optional

import redis.asyncio as aioredis

logger = logging.getLogger(__name__)

# Module-level connection — initialised lazily on first use
_redis_client: Optional[aioredis.Redis] = None
_redis_init_attempted: bool = False


async def get_redis() -> Optional[aioredis.Redis]:
    """
    Return the shared async Redis client, creating it on first call.

    Returns None (and logs a warning) when:
    - settings.app.redis_url is empty/unset
    - The Redis server is unreachable
    """
    global _redis_client, _redis_init_attempted

    if _redis_client is not None:
        return _redis_client

    if _redis_init_attempted:
        # Already tried and failed — don't retry every request
        return None

    _redis_init_attempted = True

    try:
        from config import settings

        redis_url = settings.app.redis_url
        if not redis_url:
            logger.warning(
                "REDIS_URL not configured — middleware will use in-memory fallback"
            )
            return None

        client = aioredis.from_url(
            redis_url,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
            retry_on_timeout=True,
        )
        # Verify connectivity
        await client.ping()
        _redis_client = client
        logger.info("Middleware Redis connection established")
        return _redis_client

    except Exception as exc:
        logger.warning(
            "Could not connect to Redis for middleware — falling back to "
            "in-memory: %s",
            exc,
        )
        return None


async def close_redis() -> None:
    """Close the shared Redis connection (call during app shutdown)."""
    global _redis_client, _redis_init_attempted
    if _redis_client is not None:
        await _redis_client.aclose()
        _redis_client = None
    _redis_init_attempted = False
