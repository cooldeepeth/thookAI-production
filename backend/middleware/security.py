"""
Security Middleware for ThookAI

Provides:
- Security headers (similar to Helmet.js)
- Rate limiting
- Request validation
"""

import time
import logging
from typing import Callable, Dict, Optional
from collections import defaultdict
from datetime import datetime, timedelta
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse
from fastapi import FastAPI

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
        
        # Content Security Policy (adjust as needed)
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self' data:; "
            "connect-src 'self' https:;"
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
    In-memory rate limiter using sliding window algorithm.
    For production, consider using Redis for distributed rate limiting.
    """
    
    def __init__(self):
        self.requests: Dict[str, list] = defaultdict(list)
        self.cleanup_interval = 60  # seconds
        self.last_cleanup = time.time()
    
    def _cleanup_old_requests(self):
        """Remove expired request timestamps"""
        current_time = time.time()
        if current_time - self.last_cleanup < self.cleanup_interval:
            return
        
        cutoff = current_time - 60  # Keep last minute of data
        for key in list(self.requests.keys()):
            self.requests[key] = [ts for ts in self.requests[key] if ts > cutoff]
            if not self.requests[key]:
                del self.requests[key]
        
        self.last_cleanup = current_time
    
    def is_rate_limited(self, key: str, limit: int, window_seconds: int = 60) -> tuple[bool, int]:
        """
        Check if request should be rate limited.
        Returns (is_limited, remaining_requests)
        """
        self._cleanup_old_requests()
        
        current_time = time.time()
        window_start = current_time - window_seconds
        
        # Filter to requests within window
        self.requests[key] = [ts for ts in self.requests[key] if ts > window_start]
        
        request_count = len(self.requests[key])
        remaining = max(0, limit - request_count)
        
        if request_count >= limit:
            return True, remaining
        
        # Record this request
        self.requests[key].append(current_time)
        return False, remaining - 1


# Global rate limiter instance
_rate_limiter = RateLimiter()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware with configurable limits per endpoint.
    """
    
    def __init__(self, app, default_limit: int = 60, auth_limit: int = 10):
        super().__init__(app)
        self.default_limit = default_limit
        self.auth_limit = auth_limit
        
        # Endpoint-specific limits
        self.endpoint_limits = {
            '/api/auth/login': auth_limit,
            '/api/auth/register': auth_limit,
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
        if request.url.path in ['/api/health', '/api/']:
            return await call_next(request)
        
        client_ip = self._get_client_ip(request)
        path = request.url.path
        
        # Determine rate limit for this endpoint
        limit = self.endpoint_limits.get(path, self.default_limit)
        
        # Create rate limit key (IP + endpoint)
        rate_key = f"{client_ip}:{path}"
        
        is_limited, remaining = _rate_limiter.is_rate_limited(rate_key, limit)
        
        if is_limited:
            logger.warning(f"Rate limit exceeded for {client_ip} on {path}")
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Too many requests. Please try again later.",
                    "retry_after": 60
                },
                headers={
                    "Retry-After": "60",
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
