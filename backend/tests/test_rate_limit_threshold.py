"""
Phase 26: Rate Limit Threshold Unit Test
Covers: BACK-07 (auth routes have rate limit <= 10/min — numeric assertion, not string grep)

This test imports the RateLimitMiddleware class directly and reads its endpoint_limits
configuration, asserting that auth-route limits are <= 10 requests per minute.
"""
import pytest


def test_auth_route_rate_limit_is_at_most_10_per_minute():
    """
    RateLimitMiddleware must configure auth routes at <= 10 req/min (BACK-07).
    This test reads the actual middleware configuration — not just grepping for a number.
    """
    from middleware.security import RateLimitMiddleware

    # Instantiate with a dummy app to access the configured limits
    middleware = RateLimitMiddleware(app=None)

    # endpoint_limits maps path prefixes or full paths to per-minute limits
    limits = getattr(middleware, "endpoint_limits", None) or getattr(
        middleware, "rate_limits", None
    )

    assert limits is not None, (
        "RateLimitMiddleware has no endpoint_limits or rate_limits attribute — "
        "cannot verify BACK-07 threshold. Check middleware/security.py for the correct attribute name "
        "and update this test accordingly."
    )

    # All auth-related paths must have a limit <= 10
    auth_paths = [
        k for k in limits
        if "auth" in k.lower() or "login" in k.lower() or "register" in k.lower()
    ]
    assert auth_paths, (
        f"No auth-related paths found in rate limit config. Available keys: {list(limits.keys())}. "
        "Update the auth_paths filter to match actual config keys."
    )

    for path in auth_paths:
        limit_value = limits[path]
        assert isinstance(limit_value, (int, float)), (
            f"Rate limit for {path} is not numeric: {limit_value!r}"
        )
        assert limit_value <= 10, (
            f"BACK-07 violation: {path} has rate limit {limit_value}/min, expected <= 10/min"
        )


def test_default_rate_limit_is_reasonable():
    """Default (non-auth) rate limit should be > 10 (distinguishable from auth limit)."""
    from middleware.security import RateLimitMiddleware

    middleware = RateLimitMiddleware(app=None)

    # Check for a default_limit or similar attribute
    default_limit = getattr(middleware, "default_limit", None) or getattr(
        middleware, "rate_limit_per_minute", None
    )

    if default_limit is None:
        pytest.skip("No default_limit attribute found — skip default rate limit check")

    assert isinstance(default_limit, (int, float))
    # Default should be > 10 (auth is special-cased to be strict)
    assert default_limit > 10, f"Default rate limit {default_limit} should be > 10"


def test_auth_limit_constructor_parameter_is_10():
    """
    The auth_limit constructor parameter defaults to 10.
    Confirms the class-level default, not just the instance attribute.
    """
    import inspect
    from middleware.security import RateLimitMiddleware

    sig = inspect.signature(RateLimitMiddleware.__init__)
    params = sig.parameters

    assert "auth_limit" in params, (
        "RateLimitMiddleware.__init__ has no 'auth_limit' parameter — "
        "update this test to match the actual constructor signature."
    )

    auth_limit_default = params["auth_limit"].default
    assert auth_limit_default != inspect.Parameter.empty, (
        "auth_limit parameter has no default value"
    )
    assert isinstance(auth_limit_default, (int, float)), (
        f"auth_limit default is not numeric: {auth_limit_default!r}"
    )
    assert auth_limit_default <= 10, (
        f"BACK-07 violation: auth_limit constructor default is {auth_limit_default}, expected <= 10"
    )
