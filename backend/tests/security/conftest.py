"""
Shared fixtures for security test suite.

Provides minimal app + client helpers so each test file doesn't need
to re-wire the FastAPI test setup.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from jose import jwt

# Fixed test JWT secret — consistent across all security tests.
TEST_JWT_SECRET = "test-security-suite-secret-32chars!!"


def make_user(email: str = None, auth_method: str = "email") -> dict:
    """Return a minimal user document."""
    from auth_utils import hash_password

    email = email or f"sectest_{uuid.uuid4().hex[:8]}@test.com"
    user: dict = {
        "user_id": f"user_{uuid.uuid4().hex[:12]}",
        "email": email,
        "name": "Security Test User",
        "picture": None,
        "auth_method": auth_method,
        "plan": "starter",
        "subscription_tier": "starter",
        "credits": 200,
        "credit_allowance": 0,
        "credits_last_refresh": datetime.now(timezone.utc),
        "credits_refreshed_at": datetime.now(timezone.utc),
        "onboarding_completed": True,
        "platforms_connected": [],
        "created_at": datetime.now(timezone.utc),
    }
    if auth_method == "email":
        user["hashed_password"] = hash_password("TestPass123!")
    return user


def make_valid_jwt(user_id: str, email: str) -> str:
    """Create a valid JWT signed with the test secret."""
    expire = datetime.now(timezone.utc) + timedelta(days=7)
    return jwt.encode(
        {"sub": user_id, "email": email, "exp": expire},
        TEST_JWT_SECRET,
        algorithm="HS256",
    )


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """
    Auto-use fixture that clears the in-memory rate limiter state before each test.

    The RateLimiter in middleware/security.py is a module-level singleton whose
    in-memory store accumulates across tests. When auth endpoints are hit many
    times in a test session, the rate limit triggers (429) before the actual
    validation logic. This fixture resets the state so each test starts fresh.
    """
    import middleware.security as sec_module
    # Clear the in-memory request store on the global rate limiter instance
    sec_module._rate_limiter._mem_requests.clear()
    yield
    # Also clear after each test for cleanliness
    sec_module._rate_limiter._mem_requests.clear()
