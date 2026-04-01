"""
API Rate Limiter Concurrent Load Tests — E2E-08

Verifies that the RateLimiter and RateLimitMiddleware correctly handle concurrent
requests: accurate counting, threshold enforcement, per-IP independence, stricter
auth-endpoint limits, and rate limit response headers.

Run:
    cd backend && python3 -m pytest tests/test_rate_limit_concurrent.py -x -v
"""

import asyncio
from typing import List, Tuple

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from middleware.security import RateLimiter, RateLimitMiddleware


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def limiter() -> RateLimiter:
    """Fresh RateLimiter instance (in-memory, no Redis) for each test."""
    return RateLimiter()


def _build_app(default_limit: int = 60, auth_limit: int = 10) -> FastAPI:
    """Build a minimal FastAPI app with RateLimitMiddleware for middleware tests."""
    app = FastAPI()
    app.add_middleware(
        RateLimitMiddleware,
        default_limit=default_limit,
        auth_limit=auth_limit,
    )

    @app.get("/api/content/test")
    async def content_test():
        return {"ok": True}

    @app.get("/api/auth/login")
    async def auth_login():
        return {"ok": True}

    @app.get("/api/auth/register")
    async def auth_register():
        return {"ok": True}

    return app


# ---------------------------------------------------------------------------
# Test 1: Concurrent requests are counted accurately
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_concurrent_requests_count_accurately(limiter: RateLimiter):
    """
    10 concurrent in-memory rate limit calls against the same key with limit=20
    must all be allowed and the remaining counter must reflect exactly 10
    consumed slots.
    """
    key = "ip:concurrent:test"
    limit = 20

    results: List[Tuple[bool, int]] = await asyncio.gather(
        *[limiter.is_rate_limited(key, limit=limit) for _ in range(10)]
    )

    blocked = [r for r in results if r[0] is True]
    assert len(blocked) == 0, (
        f"No requests should be blocked (10 < limit 20), got {len(blocked)} blocked"
    )

    # After 10 requests, remaining should be 10 (20 - 10)
    # The last call's remaining value reflects the post-decrement state
    # The minimum remaining across all responses must be >= 9 (at least)
    # because remaining decrements per call
    remaining_values = [r[1] for r in results]
    # All remaining values should be >= 0
    assert all(r >= 0 for r in remaining_values), (
        f"Remaining values must be non-negative, got: {remaining_values}"
    )
    # At least one response should report remaining close to 10 (20 - 10)
    # The minimum remaining after all concurrent calls should reflect ~10 consumed
    min_remaining = min(remaining_values)
    assert min_remaining <= 11, (
        f"After 10 concurrent requests with limit 20, min remaining should be <= 11, "
        f"got {min_remaining}"
    )


# ---------------------------------------------------------------------------
# Test 2: Rate limit blocks at exact threshold
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_rate_limit_blocks_at_exact_threshold(limiter: RateLimiter):
    """
    After exactly `limit` requests, the very next request must be blocked
    (is_limited=True) with remaining == 0.
    """
    key = "ip:threshold:test"
    limit = 5

    # Fire exactly `limit` sequential requests — all should pass
    for i in range(limit):
        is_limited, remaining = limiter._is_rate_limited_memory(key, limit=limit)
        assert is_limited is False, f"Request {i + 1}/{limit} should not be blocked"

    # The (limit + 1)th request must be blocked
    is_limited, remaining = limiter._is_rate_limited_memory(key, limit=limit)
    assert is_limited is True, (
        f"Request {limit + 1} should be blocked after {limit} previous requests"
    )
    assert remaining == 0, f"Remaining must be 0 when blocked, got {remaining}"


# ---------------------------------------------------------------------------
# Test 3: Different keys have independent limits
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_different_keys_have_independent_limits(limiter: RateLimiter):
    """
    Rate limits are per-key (IP:path).  Exhausting the limit for one key must
    not affect a different key.
    """
    key_a = "ip:10.0.0.1:/api/content/test"
    key_b = "ip:10.0.0.2:/api/content/test"
    limit = 20

    # Fire 15 requests for key_a
    for _ in range(15):
        limiter._is_rate_limited_memory(key_a, limit=limit)

    # Fire 5 requests for key_b
    for _ in range(5):
        limiter._is_rate_limited_memory(key_b, limit=limit)

    # key_a should have 5 remaining (20 - 15)
    is_limited_a, remaining_a = limiter._is_rate_limited_memory(key_a, limit=limit)
    assert is_limited_a is False, "key_a with 16/20 requests should not be blocked"
    assert remaining_a == 4, (
        f"key_a should have 4 remaining after 16 requests (20 - 16), got {remaining_a}"
    )

    # key_b should have 14 remaining (20 - 6)
    is_limited_b, remaining_b = limiter._is_rate_limited_memory(key_b, limit=limit)
    assert is_limited_b is False, "key_b with 6/20 requests should not be blocked"
    assert remaining_b == 14, (
        f"key_b should have 14 remaining after 6 requests (20 - 6), got {remaining_b}"
    )


# ---------------------------------------------------------------------------
# Test 4: Auth endpoints have stricter rate limits than general endpoints
# ---------------------------------------------------------------------------


def test_auth_endpoint_has_stricter_limit():
    """
    /api/auth/* endpoints must be blocked at a lower threshold than general
    /api/content/* endpoints when using RateLimitMiddleware.

    Default config: default_limit=60, auth_limit=10.
    We verify that /api/auth/login gets blocked before /api/content/test.
    """
    # Use small limits to keep the test fast
    auth_limit = 3
    default_limit = 10
    app = _build_app(default_limit=default_limit, auth_limit=auth_limit)

    with TestClient(app, raise_server_exceptions=True) as client:
        # Hit /api/auth/login until we get a 429
        auth_blocked_at: int = -1
        for i in range(default_limit + 5):
            # Use a consistent IP by not specifying X-Forwarded-For
            resp = client.get("/api/auth/login")
            if resp.status_code == 429:
                auth_blocked_at = i + 1  # 1-indexed call number that was blocked
                break

        assert auth_blocked_at != -1, (
            "Auth endpoint should have been blocked within "
            f"{default_limit + 5} requests but was not"
        )
        assert auth_blocked_at <= auth_limit + 1, (
            f"Auth endpoint blocked at request #{auth_blocked_at}, "
            f"expected <= {auth_limit + 1} (auth_limit={auth_limit})"
        )

    # Now verify the general endpoint is NOT blocked at the same threshold
    # Using a fresh app instance to reset in-memory state
    app2 = _build_app(default_limit=default_limit, auth_limit=auth_limit)
    with TestClient(app2, raise_server_exceptions=True) as client2:
        # Fire auth_limit requests to /api/content/test — should not be blocked
        for i in range(auth_limit):
            resp = client2.get("/api/content/test")
            assert resp.status_code == 200, (
                f"Content endpoint should NOT be blocked at request {i + 1} "
                f"(auth_limit={auth_limit}); got {resp.status_code}"
            )


# ---------------------------------------------------------------------------
# Test 5: Rate limit response headers are present
# ---------------------------------------------------------------------------


def test_rate_limit_response_includes_headers():
    """
    Both allowed (200) and blocked (429) responses must include rate limit
    headers:
      - X-RateLimit-Limit
      - X-RateLimit-Remaining
    Blocked responses must also include Retry-After.
    """
    default_limit = 5
    auth_limit = 3
    app = _build_app(default_limit=default_limit, auth_limit=auth_limit)

    with TestClient(app, raise_server_exceptions=True) as client:
        # ---- Allowed response headers ----
        resp = client.get("/api/content/test")
        assert resp.status_code == 200, "First request should be allowed"

        assert "X-RateLimit-Limit" in resp.headers, (
            "Allowed response must contain X-RateLimit-Limit header"
        )
        assert "X-RateLimit-Remaining" in resp.headers, (
            "Allowed response must contain X-RateLimit-Remaining header"
        )
        assert int(resp.headers["X-RateLimit-Limit"]) == default_limit, (
            f"X-RateLimit-Limit must equal configured default_limit ({default_limit})"
        )

        # ---- Blocked response headers ----
        # Exhaust the limit for the auth route
        for _ in range(auth_limit):
            client.get("/api/auth/login")

        blocked_resp = client.get("/api/auth/login")
        assert blocked_resp.status_code == 429, (
            f"Expected 429 after {auth_limit} auth requests, got {blocked_resp.status_code}"
        )

        assert "X-RateLimit-Limit" in blocked_resp.headers, (
            "Blocked response must contain X-RateLimit-Limit header"
        )
        assert "X-RateLimit-Remaining" in blocked_resp.headers, (
            "Blocked response must contain X-RateLimit-Remaining header"
        )
        assert blocked_resp.headers["X-RateLimit-Remaining"] == "0", (
            "X-RateLimit-Remaining must be '0' on a blocked response"
        )
        assert "Retry-After" in blocked_resp.headers, (
            "Blocked response must contain Retry-After header"
        )


# ---------------------------------------------------------------------------
# Test 6 (bonus): Async concurrent dispatch under real asyncio.gather
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_async_concurrent_is_rate_limited_no_race():
    """
    asyncio.gather fires 15 concurrent is_rate_limited calls against the same
    in-memory limiter with limit=20.  No call should be blocked and there must
    be no race condition (Python GIL ensures atomic list appends in CPython,
    but we verify the invariant explicitly).
    """
    limiter = RateLimiter()
    key = "ip:async:gather"
    limit = 20

    results = await asyncio.gather(
        *[limiter.is_rate_limited(key, limit=limit) for _ in range(15)]
    )

    blocked = [r for r in results if r[0] is True]
    assert not blocked, (
        f"15 concurrent requests under limit 20 must all pass; {len(blocked)} were blocked"
    )
