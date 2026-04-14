"""
CSRF Protection Middleware — Double-Submit Cookie Pattern

How it works:
1. On login/register, the server sets TWO cookies:
   - session_token (httpOnly=True): the JWT, JS cannot read it
   - csrf_token (httpOnly=False): a random token, JS CAN read it

2. On state-changing requests (POST/PUT/DELETE/PATCH), the browser sends:
   - session_token cookie automatically (browser does this)
   - X-CSRF-Token header (frontend JS must set this from the csrf_token cookie)

3. The middleware verifies that X-CSRF-Token == csrf_token cookie value.
   A cross-site attacker can submit the session_token cookie (browser does it),
   but cannot read the csrf_token cookie to forge the header.

4. Requests using Authorization Bearer header skip CSRF entirely —
   these come from API clients / mobile apps that are not vulnerable to CSRF.

Security guarantee: An attacker-controlled page cannot perform authenticated
state-changing requests on behalf of a victim user.
"""

import logging
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse

logger = logging.getLogger(__name__)

# Safe HTTP methods — never mutate state, therefore never CSRF-checked
SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "TRACE"})

# Paths that are exempt from CSRF checks.
# These are either pre-auth endpoints (login/register) or endpoints that use
# their own out-of-band verification (Stripe webhook signature, n8n HMAC).
_EXEMPT_EXACT: frozenset[str] = frozenset({
    "/api/auth/login",
    "/api/auth/register",
    "/api/auth/google",
    "/api/auth/google/callback",
    "/api/auth/linkedin",
    "/api/auth/linkedin/callback",
    "/api/auth/x",
    "/api/auth/x/callback",
    "/api/auth/logout",
    "/api/auth/forgot-password",
    "/api/billing/webhook/stripe",
    "/health",
})

# Path prefixes that are exempt (e.g. /api/n8n/*)
_EXEMPT_PREFIXES: tuple[str, ...] = (
    "/api/n8n/",
)


def _is_exempt(path: str) -> bool:
    """Return True if the request path should skip CSRF validation."""
    if path in _EXEMPT_EXACT:
        return True
    return any(path.startswith(prefix) for prefix in _EXEMPT_PREFIXES)


class CSRFMiddleware(BaseHTTPMiddleware):
    """
    Double-submit cookie CSRF middleware.

    Decision table:
    | Method         | session_token cookie | X-CSRF-Token header | Result         |
    |----------------|----------------------|---------------------|----------------|
    | GET/HEAD/OPT   | any                  | any                 | pass (exempt)  |
    | POST (exempt)  | any                  | any                 | pass (exempt)  |
    | POST           | absent               | any                 | pass (no cookie→bearer/anon) |
    | POST           | present              | absent              | 403 missing    |
    | POST           | present              | wrong               | 403 invalid    |
    | POST           | present              | matches cookie      | pass           |
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        method = request.method.upper()

        # Safe methods are always exempt
        if method in SAFE_METHODS:
            return await call_next(request)

        # Exempt paths skip CSRF (login, register, webhooks, etc.)
        if _is_exempt(request.url.path):
            return await call_next(request)

        # If no session_token cookie, the client is using Bearer auth (or is
        # unauthenticated). CSRF only applies to cookie-based sessions.
        session_cookie = request.cookies.get("session_token")
        if not session_cookie:
            return await call_next(request)

        # Cookie-based auth detected — enforce double-submit check
        csrf_header = request.headers.get("X-CSRF-Token")
        csrf_cookie = request.cookies.get("csrf_token")

        if not csrf_header:
            logger.warning(
                "CSRF token missing for %s %s (ip=%s)",
                method,
                request.url.path,
                request.client.host if request.client else "unknown",
            )
            return JSONResponse(
                status_code=403,
                content={"detail": "CSRF token missing", "error_code": "CSRF_INVALID"},
            )

        if csrf_header != csrf_cookie:
            logger.warning(
                "CSRF token invalid for %s %s (ip=%s)",
                method,
                request.url.path,
                request.client.host if request.client else "unknown",
            )
            return JSONResponse(
                status_code=403,
                content={"detail": "CSRF token invalid", "error_code": "CSRF_INVALID"},
            )

        return await call_next(request)
