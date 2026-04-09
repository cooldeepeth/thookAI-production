"""
Performance Middleware for ThookAI

Provides:
- Response compression (gzip)
- Response caching (Redis-backed, skips when unavailable)
- Request timing
"""

import gzip
import time
import json
import hashlib
import logging
from typing import Callable, Dict, Optional
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, StreamingResponse

logger = logging.getLogger(__name__)


class CompressionMiddleware(BaseHTTPMiddleware):
    """
    Gzip compression middleware for responses.
    Compresses responses larger than minimum size.
    """
    
    def __init__(self, app, minimum_size: int = 500, compression_level: int = 6):
        super().__init__(app)
        self.minimum_size = minimum_size
        self.compression_level = compression_level
        self.compressible_types = {
            'application/json',
            'text/plain',
            'text/html',
            'text/css',
            'text/javascript',
            'application/javascript',
            'application/xml',
            'text/xml'
        }
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Check if client accepts gzip
        accept_encoding = request.headers.get('Accept-Encoding', '')
        if 'gzip' not in accept_encoding:
            return await call_next(request)
        
        response = await call_next(request)
        
        # Skip streaming responses and already compressed content
        if isinstance(response, StreamingResponse):
            return response
        
        content_encoding = response.headers.get('Content-Encoding')
        if content_encoding:
            return response
        
        # Check content type
        content_type = response.headers.get('Content-Type', '')
        base_type = content_type.split(';')[0].strip()
        if base_type not in self.compressible_types:
            return response
        
        # Get response body
        body = b''
        async for chunk in response.body_iterator:
            body += chunk

        # Preserve all raw headers (including duplicate set-cookie entries)
        # dict(response.headers) deduplicates keys and loses multi-valued
        # headers like set-cookie, so we work with the raw header list instead.
        raw_headers = list(response.raw_headers)

        def _rebuild_response(content: bytes, extra_headers: dict[str, str] | None = None) -> Response:
            """Build a Response from raw_headers, replacing content-length and
            adding any extra headers.  Preserves duplicate set-cookie entries."""
            filtered = [
                (k, v) for k, v in raw_headers
                if k.lower() != b"content-length"
            ]
            filtered.append((b"content-length", str(len(content)).encode("latin-1")))
            if extra_headers:
                for hk, hv in extra_headers.items():
                    filtered.append((hk.lower().encode("latin-1"), hv.encode("latin-1")))
            resp = Response(
                status_code=response.status_code,
                media_type=response.media_type,
            )
            resp.body = content
            resp.raw_headers = filtered
            return resp

        # Skip small responses
        if len(body) < self.minimum_size:
            return _rebuild_response(body)

        # Compress
        compressed = gzip.compress(body, compresslevel=self.compression_level)

        # Only use compressed if it's smaller
        if len(compressed) < len(body):
            return _rebuild_response(
                compressed,
                extra_headers={
                    "content-encoding": "gzip",
                    "vary": "Accept-Encoding",
                },
            )

        return _rebuild_response(body)


class CacheMiddleware(BaseHTTPMiddleware):
    """
    Response caching middleware backed by Redis.
    Skips caching gracefully when Redis is unavailable (no fallback cache —
    requests simply pass through uncached).
    """

    def __init__(self, app, max_entries: int = 1000):
        super().__init__(app)
        self.max_entries = max_entries  # kept for API compat; Redis handles eviction via TTL

        # Cacheable endpoints with TTL in seconds
        self.cacheable_endpoints: Dict[str, int] = {
            '/api/templates/categories': 3600,      # 1 hour
            '/api/billing/subscription/tiers': 3600,  # 1 hour
            '/api/billing/credits/costs': 3600,     # 1 hour
            '/api/viral/patterns': 3600,            # 1 hour
            '/api/content/image-styles': 3600,      # 1 hour
            '/api/content/series/templates': 3600,  # 1 hour
            '/api/content/providers/summary': 300,  # 5 minutes
            '/api/persona/regional-english/options': 86400,  # 24 hours
        }

    @staticmethod
    def _get_cache_key(request: Request) -> str:
        """Generate a Redis key from the request.  Pattern: cache:{method}:{path}:{query_hash}"""
        query = str(sorted(request.query_params.items()))
        query_hash = hashlib.md5(query.encode()).hexdigest()
        return f"cache:{request.method}:{request.url.path}:{query_hash}"

    # ------------------------------------------------------------------
    # Redis helpers
    # ------------------------------------------------------------------
    async def _get_from_redis(self, redis_client, cache_key: str) -> Optional[dict]:
        """Fetch a cached response from Redis.  Returns parsed dict or None."""
        raw = await redis_client.get(cache_key)
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return None

    async def _set_in_redis(
        self, redis_client, cache_key: str, data: dict, ttl: int
    ) -> None:
        """Store a serialised response in Redis with the given TTL."""
        await redis_client.set(cache_key, json.dumps(data), ex=ttl)

    # ------------------------------------------------------------------
    # Dispatch
    # ------------------------------------------------------------------
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Only cache GET requests
        if request.method != 'GET':
            return await call_next(request)

        # Check if endpoint is cacheable
        path = request.url.path
        ttl = self.cacheable_endpoints.get(path)
        if ttl is None:
            return await call_next(request)

        cache_key = self._get_cache_key(request)

        # --- Try to serve from Redis cache ---
        redis_client = None
        try:
            from middleware.redis_client import get_redis
            redis_client = await get_redis()
        except Exception as exc:
            logger.warning("Redis unavailable for cache lookup: %s", exc)

        if redis_client is not None:
            try:
                cached = await self._get_from_redis(redis_client, cache_key)
                if cached is not None:
                    logger.debug(f"Cache hit for {path}")
                    headers = cached.get("headers", {})
                    headers['X-Cache'] = 'HIT'
                    return Response(
                        content=cached["body"].encode("utf-8") if isinstance(cached["body"], str) else cached["body"],
                        status_code=cached.get("status_code", 200),
                        headers=headers,
                        media_type='application/json'
                    )
            except Exception as exc:
                logger.warning("Redis cache read failed, skipping cache: %s", exc)

        # --- Cache miss: get fresh response ---
        response = await call_next(request)

        # Only cache successful responses
        if response.status_code == 200:
            body = b''
            async for chunk in response.body_iterator:
                body += chunk

            # Try to store in Redis
            if redis_client is not None:
                try:
                    await self._set_in_redis(
                        redis_client,
                        cache_key,
                        {
                            "body": body.decode("utf-8", errors="replace"),
                            "status_code": response.status_code,
                            "headers": {
                                k: v
                                for k, v in response.headers.items()
                                if k.lower() not in ("content-length", "transfer-encoding")
                            },
                        },
                        ttl,
                    )
                    logger.debug(f"Cached response for {path} in Redis (TTL: {ttl}s)")
                except Exception as exc:
                    logger.warning("Redis cache write failed: %s", exc)

            # Preserve all raw headers (including any duplicate entries)
            raw = list(response.raw_headers)
            # Replace content-length with the actual body length
            raw = [(k, v) for k, v in raw if k.lower() != b"content-length"]
            raw.append((b"content-length", str(len(body)).encode("latin-1")))
            raw.append((b"x-cache", b"MISS"))
            raw.append((b"cache-control", f"public, max-age={ttl}".encode("latin-1")))

            resp = Response(
                status_code=response.status_code,
                media_type=response.media_type,
            )
            resp.body = body
            resp.raw_headers = raw
            return resp

        return response


class TimingMiddleware(BaseHTTPMiddleware):
    """
    Adds request timing headers and logs slow requests.
    """
    
    def __init__(self, app, slow_request_threshold_ms: int = 1000):
        super().__init__(app)
        self.slow_threshold = slow_request_threshold_ms
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.perf_counter()
        
        response = await call_next(request)
        
        duration_ms = (time.perf_counter() - start_time) * 1000
        
        # Add timing header
        response.headers['X-Response-Time'] = f"{duration_ms:.2f}ms"
        
        # Log slow requests
        if duration_ms > self.slow_threshold:
            logger.warning(
                f"Slow request: {request.method} {request.url.path} "
                f"took {duration_ms:.2f}ms (threshold: {self.slow_threshold}ms)"
            )
        
        return response
