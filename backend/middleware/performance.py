"""
Performance Middleware for ThookAI

Provides:
- Response compression (gzip)
- Response caching for static data
- Request timing
"""

import gzip
import time
import json
import hashlib
import logging
from typing import Callable, Dict, Optional, Set
from datetime import datetime, timedelta
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, StreamingResponse
from io import BytesIO

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
        
        # Skip small responses
        if len(body) < self.minimum_size:
            return Response(
                content=body,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.media_type
            )
        
        # Compress
        compressed = gzip.compress(body, compresslevel=self.compression_level)
        
        # Only use compressed if it's smaller
        if len(compressed) < len(body):
            headers = dict(response.headers)
            headers['Content-Encoding'] = 'gzip'
            headers['Content-Length'] = str(len(compressed))
            headers['Vary'] = 'Accept-Encoding'
            
            return Response(
                content=compressed,
                status_code=response.status_code,
                headers=headers,
                media_type=response.media_type
            )
        
        return Response(
            content=body,
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type=response.media_type
        )


class CacheEntry:
    """Cache entry with expiration"""
    def __init__(self, content: bytes, headers: dict, status_code: int, expires_at: datetime):
        self.content = content
        self.headers = headers
        self.status_code = status_code
        self.expires_at = expires_at
        self.created_at = datetime.utcnow()
    
    @property
    def is_expired(self) -> bool:
        return datetime.utcnow() > self.expires_at


class CacheMiddleware(BaseHTTPMiddleware):
    """
    In-memory response caching for static/semi-static endpoints.
    For production, consider Redis for distributed caching.
    """
    
    def __init__(self, app, max_entries: int = 1000):
        super().__init__(app)
        self.cache: Dict[str, CacheEntry] = {}
        self.max_entries = max_entries
        
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
    
    def _get_cache_key(self, request: Request) -> str:
        """Generate cache key from request"""
        # Include query params in key
        query = str(sorted(request.query_params.items()))
        key_data = f"{request.method}:{request.url.path}:{query}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def _cleanup_expired(self):
        """Remove expired cache entries"""
        expired_keys = [k for k, v in self.cache.items() if v.is_expired]
        for key in expired_keys:
            del self.cache[key]
        
        # If still over limit, remove oldest entries
        if len(self.cache) > self.max_entries:
            sorted_entries = sorted(self.cache.items(), key=lambda x: x[1].created_at)
            entries_to_remove = len(self.cache) - self.max_entries
            for key, _ in sorted_entries[:entries_to_remove]:
                del self.cache[key]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Only cache GET requests
        if request.method != 'GET':
            return await call_next(request)
        
        # Check if endpoint is cacheable
        path = request.url.path
        ttl = self.cacheable_endpoints.get(path)
        if ttl is None:
            return await call_next(request)
        
        # Check cache
        cache_key = self._get_cache_key(request)
        cached = self.cache.get(cache_key)
        
        if cached and not cached.is_expired:
            logger.debug(f"Cache hit for {path}")
            headers = dict(cached.headers)
            headers['X-Cache'] = 'HIT'
            return Response(
                content=cached.content,
                status_code=cached.status_code,
                headers=headers,
                media_type='application/json'
            )
        
        # Get fresh response
        response = await call_next(request)
        
        # Only cache successful responses
        if response.status_code == 200:
            # Get response body
            body = b''
            async for chunk in response.body_iterator:
                body += chunk
            
            # Store in cache
            self._cleanup_expired()
            self.cache[cache_key] = CacheEntry(
                content=body,
                headers=dict(response.headers),
                status_code=response.status_code,
                expires_at=datetime.utcnow() + timedelta(seconds=ttl)
            )
            
            logger.debug(f"Cached response for {path} (TTL: {ttl}s)")
            
            headers = dict(response.headers)
            headers['X-Cache'] = 'MISS'
            headers['Cache-Control'] = f'public, max-age={ttl}'
            
            return Response(
                content=body,
                status_code=response.status_code,
                headers=headers,
                media_type=response.media_type
            )
        
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
