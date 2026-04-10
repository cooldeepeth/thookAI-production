"""
Security Middleware for ThookAI

Provides:
- Security headers (similar to Helmet.js)
- Rate limiting (Redis-backed with in-memory fallback)
- Request validation
"""

import time
import logging
from typing import Callable, Dict, Optional, Tuple
from collections import defaultdict
from datetime import datetime, timedelta
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse
from fastapi import FastAPI

from middleware.redis_client import get_redis

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Adds security headers to all responses.
    Similar to Helmet.js for Express.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        
        # Prevent XSS attacks
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"
        
        # XSS Protection (legacy but still useful)
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Referrer Policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Content Security Policy — strict policy for API-only server
        # This backend serves JSON responses, not HTML/JS/CSS, so we deny all resource loading.
        response.headers["Content-Security-Policy"] = (
            "default-src 'none'; "
            "frame-ancestors 'none'"
        )
        
        # Strict Transport Security (HTTPS)
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        # Permissions Policy (formerly Feature-Policy)
        response.headers["Permissions-Policy"] = (
            "accelerometer=(), camera=(), geolocation=(), gyroscope=(), "
            "magnetometer=(), microphone=(), payment=(), usb=()"
        )
        
        return response


class RateLimiter:
    """
    Rate limiter with Redis sliding-window backend.
    Falls back to an in-memory sliding window when Redis is unavailable.
    """

    def __init__(self):
        # In-memory fallback state
        self._mem_requests: Dict[str, list] = defaultdict(list)
        self._cleanup_interval = 60  # seconds
        self._last_cleanup = time.time()

    # ------------------------------------------------------------------
    # In-memory fallback (original implementation)
    # ------------------------------------------------------------------
    def _cleanup_old_requests(self):
        """Remove expired request timestamps from in-memory store"""
        current_time = time.time()
        if current_time - self._last_cleanup < self._cleanup_interval:
            return

        cutoff = current_time - 60  # Keep last minute of data
        for key in list(self._mem_requests.keys()):
            self._mem_requests[key] = [
                ts for ts in self._mem_requests[key] if ts > cutoff
            ]
            if not self._mem_requests[key]:
                del self._mem_requests[key]

        self._last_cleanup = current_time

    def _is_rate_limited_memory(
        self, key: str, limit: int, window_seconds: int = 60
    ) -> Tuple[bool, int]:
        """In-memory sliding window check (fallback)."""
        self._cleanup_old_requests()

        current_time = time.time()
        window_start = current_time - window_seconds

        self._mem_requests[key] = [
            ts for ts in self._mem_requests[key] if ts > window_start
        ]

        request_count = len(self._mem_requests[key])
        remaining = max(0, limit - request_count)

        if request_count >= limit:
            return True, remaining

        self._mem_requests[key].append(current_time)
        return False, remaining - 1

    # ------------------------------------------------------------------
    # Redis sliding window
    # ------------------------------------------------------------------
    async def _is_rate_limited_redis(
        self,
        redis_client,
        key: str,
        limit: int,
        window_seconds: int = 60,
    ) -> Tuple[bool, int]:
        """
        Redis sliding-window rate limit using a sorted set.

        Key pattern: ratelimit:{ip}:{endpoint}
        Each member is a unique timestamp string; the score is the UNIX
        timestamp.  We trim entries outside the window, count what remains,
        and add the current request only if under the limit.
        """
        redis_key = f"ratelimit:{key}"
        now = time.time()
        window_start = now - window_seconds

        pipe = redis_client.pipeline(transaction=True)
        # Remove entries outside the current window
        pipe.zremrangebyscore(redis_key, 0, window_start)
        # Count remaining entries
        pipe.zcard(redis_key)
        results = await pipe.execute()

        request_count = results[1]
        remaining = max(0, limit - request_count)

        if request_count >= limit:
            return True, remaining

        # Record this request — member must be unique so we use the
        # precise timestamp string (float has sub-ms precision).
        pipe2 = redis_client.pipeline(transaction=True)
        pipe2.zadd(redis_key, {str(now): now})
        pipe2.expire(redis_key, window_seconds)
        await pipe2.execute()

        return False, remaining - 1

    # ------------------------------------------------------------------
    # Public API — now async, same return signature
    # ------------------------------------------------------------------
    async def is_rate_limited(
        self, key: str, limit: int, window_seconds: int = 60
    ) -> Tuple[bool, int]:
        """
        Check if request should be rate limited.
        Returns (is_limited, remaining_requests).

        Tries Redis first; falls back to in-memory on any error.
        """
        try:
            redis_client = await get_redis()
            if redis_client is not None:
                return await self._is_rate_limited_redis(
                    redis_client, key, limit, window_seconds
                )
        except Exception as exc:
            logger.warning(
                "Redis rate-limit check failed, using in-memory fallback: %s",
                exc,
            )

        return self._is_rate_limited_memory(key, limit, window_seconds)


# Global rate limiter instance
_rate_limiter = RateLimiter()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware with configurable limits per endpoint.
    Uses Redis when available; falls back to in-memory automatically.
    """
    
    def __init__(self, app, default_limit: int = 60, auth_limit: int = 10):
        super().__init__(app)
        self.default_limit = default_limit
        self.auth_limit = auth_limit
        
        # Endpoint-specific limits
        self.endpoint_limits = {
            '/api/auth/login': auth_limit,
            '/api/auth/register': auth_limit,
            '/api/auth/forgot-password': auth_limit,
            '/api/auth/reset-password': auth_limit,
            '/api/content/create': 20,
            '/api/viral/predict': 30,
            '/api/viral/improve': 20,
        }
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address, handling proxies"""
        # Check for forwarded IP (behind proxy/load balancer)
        forwarded = request.headers.get('X-Forwarded-For')
        if forwarded:
            return forwarded.split(',')[0].strip()
        
        real_ip = request.headers.get('X-Real-IP')
        if real_ip:
            return real_ip
        
        return request.client.host if request.client else 'unknown'
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip rate limiting for health checks
        if request.url.path in ['/health', '/api/health', '/api/']:
            return await call_next(request)
        
        client_ip = self._get_client_ip(request)
        path = request.url.path
        
        # Determine rate limit for this endpoint
        limit = self.endpoint_limits.get(path, self.default_limit)
        
        # Create rate limit key (IP + endpoint)
        rate_key = f"{client_ip}:{path}"
        
        is_limited, remaining = await _rate_limiter.is_rate_limited(rate_key, limit)
        
        if is_limited:
            logger.warning(f"Rate limit exceeded for {client_ip} on {path}")
            retry_seconds = 60
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Too many requests. Please wait.",
                    "retry_after": retry_seconds
                },
                headers={
                    "Retry-After": str(retry_seconds),
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0"
                }
            )
        
        response = await call_next(request)
        
        # Add rate limit headers to response
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        
        return response


def setup_rate_limiting(app: FastAPI, default_limit: int = 60, auth_limit: int = 10):
    """
    Setup rate limiting middleware on the FastAPI app.
    
    Args:
        app: FastAPI application instance
        default_limit: Default requests per minute
        auth_limit: Requests per minute for auth endpoints
    """
    app.add_middleware(
        RateLimitMiddleware,
        default_limit=default_limit,
        auth_limit=auth_limit
    )
    logger.info(f"Rate limiting enabled: {default_limit}/min default, {auth_limit}/min auth")


class InputValidationMiddleware(BaseHTTPMiddleware):
    """
    Additional input validation and sanitization.
    """
    
    # Maximum request body size (10MB)
    MAX_BODY_SIZE = 10 * 1024 * 1024
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Check content length
        content_length = request.headers.get('content-length')
        if content_length and int(content_length) > self.MAX_BODY_SIZE:
            return JSONResponse(
                status_code=413,
                content={"detail": "Request body too large"}
            )
        
        # Validate content type for POST/PUT/PATCH
        if request.method in ['POST', 'PUT', 'PATCH']:
            content_type = request.headers.get('content-type', '')
            if content_type and not any(ct in content_type for ct in ['application/json', 'multipart/form-data', 'application/x-www-form-urlencoded']):
                # Allow but log unexpected content types
                logger.debug(f"Unexpected content-type: {content_type}")
        
        return await call_next(request)
