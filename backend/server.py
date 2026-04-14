"""
ThookAI API Server

Production-ready FastAPI application with:
- Security middleware (headers, rate limiting)
- Performance optimization (compression, caching)
- Configuration validation at startup
- Comprehensive logging
"""

# Startup diagnostics — print to stderr before ANY other import so we can
# distinguish "server.py never loaded" from "something in imports hung".
# Remove these once Railway boot is stable.
import sys as _boot_sys
_boot_sys.stderr.write("[boot] server.py: starting import chain\n")
_boot_sys.stderr.flush()

from fastapi import FastAPI, APIRouter, Request, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, RedirectResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
import os
import logging
import asyncio
from pathlib import Path
from contextlib import asynccontextmanager

def _boot(msg: str) -> None:
    _boot_sys.stderr.write(f"[boot] {msg}\n")
    _boot_sys.stderr.flush()

# Import configuration first
_boot("importing config")
from config import settings, get_settings
_boot("config imported")

# Import middleware
_boot("importing middleware.security")
from middleware.security import SecurityHeadersMiddleware, RateLimitMiddleware, InputValidationMiddleware
_boot("importing middleware.performance")
from middleware.performance import CompressionMiddleware, CacheMiddleware, TimingMiddleware
_boot("importing middleware.csrf")
from middleware.csrf import CSRFMiddleware
_boot("middleware imports done")

# Import routes
_boot("importing routes.auth")
from routes.auth import router as auth_router
_boot("importing routes.password_reset")
from routes.password_reset import router as password_reset_router
_boot("importing routes.auth_google")
from routes.auth_google import router as google_auth_router
_boot("importing routes.auth_social")
from routes.auth_social import router as social_auth_router
_boot("importing routes.onboarding")
from routes.onboarding import router as onboarding_router
_boot("importing routes.persona")
from routes.persona import router as persona_router
_boot("importing routes.content")
from routes.content import router as content_router
_boot("importing routes.dashboard")
from routes.dashboard import router as dashboard_router
_boot("importing routes.platforms")
from routes.platforms import router as platforms_router
_boot("importing routes.repurpose")
from routes.repurpose import router as repurpose_router
_boot("importing routes.analytics")
from routes.analytics import router as analytics_router
_boot("importing routes.billing")
from routes.billing import router as billing_router
_boot("importing routes.viral")
from routes.viral import router as viral_router
_boot("importing routes.agency")
from routes.agency import router as agency_router
_boot("importing routes.templates")
from routes.templates import router as templates_router
_boot("importing routes.media")
from routes.media import router as media_router
_boot("importing routes.uploads")
from routes.uploads import router as uploads_router
_boot("importing routes.notifications")
from routes.notifications import router as notifications_router
_boot("importing routes.webhooks")
from routes.webhooks import router as webhooks_router
_boot("importing routes.campaigns")
from routes.campaigns import router as campaigns_router
_boot("importing routes.admin")
from routes.admin import router as admin_router
_boot("importing routes.uom")
from routes.uom import router as uom_router
_boot("importing routes.viral_card")
from routes.viral_card import router as viral_card_router
_boot("importing routes.n8n_bridge")
from routes.n8n_bridge import router as n8n_bridge_router
_boot("importing routes.strategy")
from routes.strategy import router as strategy_router
_boot("importing routes.obsidian")
from routes.obsidian import router as obsidian_router
_boot("all route imports done")


# Setup logging
logging.basicConfig(
    level=getattr(logging, settings.app.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan management.
    Handles startup and shutdown events.
    """
    # ==================== STARTUP ====================
    logger.info("Starting ThookAI API...")
    
    # Validate configuration
    config_report = settings.log_startup_info()

    # Validate required environment variables and log any that are missing
    from config import validate_required_env_vars
    missing_vars = validate_required_env_vars()
    if missing_vars:
        for var in missing_vars:
            logger.critical(f"MISSING REQUIRED ENV VAR: {var}")
        if settings.app.is_production:
            raise RuntimeError(
                f"Cannot start in production — missing required env vars: {', '.join(missing_vars)}"
            )
        else:
            logger.warning(
                f"Missing {len(missing_vars)} env var(s) — some features will be unavailable in dev mode"
            )

    # Initialize Sentry error tracking (early, before DB, so it catches startup errors)
    if settings.app.sentry_dsn:
        import sentry_sdk

        def _scrub_pii(event, hint):
            """Remove PII fields from Sentry error events (GDPR + SECR-07 compliance)."""
            pii_keys = frozenset({
                "email", "password", "hashed_password", "access_token",
                "refresh_token", "session_token", "csrf_token", "name",
                "google_id", "stripe_customer_id",
            })
            if "request" in event and isinstance(event["request"].get("data"), dict):
                for key in pii_keys:
                    event["request"]["data"].pop(key, None)
            if isinstance(event.get("extra"), dict):
                for key in pii_keys:
                    event["extra"].pop(key, None)
            return event

        sentry_sdk.init(
            dsn=settings.app.sentry_dsn,
            environment=settings.app.environment,
            traces_sample_rate=0.1 if settings.app.is_production else 1.0,
            profiles_sample_rate=0.1 if settings.app.is_production else 1.0,
            before_send=_scrub_pii,
        )
        logger.info("Sentry error tracking initialized")

    # FIXED: fail fast in production if critical config is missing
    if settings.app.is_production:
        if not settings.security.jwt_secret_key:
            raise RuntimeError("JWT_SECRET_KEY must be set in production")
        if config_report['status'] == 'error':
            for err in config_report.get('errors', []):
                logger.critical("CONFIG ERROR: %s", err)
            logger.critical(
                "Configuration errors detected in production — some features may not work. "
                "Fix the issues listed above."
            )

    # Log config warnings (fast, non-blocking)
    if settings.app.is_production and not settings.platforms.encryption_key:
        logger.critical("ENCRYPTION_KEY not set! Platform OAuth tokens will be unreadable after restart!")
    if not settings.r2.has_r2():
        if settings.app.is_production:
            logger.critical("R2 media storage not configured in production! File uploads will fail. Set R2_* environment variables.")
        else:
            logger.warning("R2 media storage not configured — uploads use /tmp fallback in dev mode.")
    if not settings.google.is_configured():
        logger.warning("Google OAuth not configured — GOOGLE_CLIENT_ID or GOOGLE_CLIENT_SECRET missing. Google sign-in will return 503.")
    if settings.app.is_production:
        if not settings.stripe.is_fully_configured():
            logger.critical("Stripe is not fully configured for production! Billing features will fail. Check STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET, and all STRIPE_PRICE_* env vars.")
    elif not settings.stripe.secret_key:
        logger.warning("Stripe secret key not configured — billing features will run in simulated mode.")
    if settings.llm.anthropic_key:
        logger.info("LLM model configured: claude-sonnet-4-20250514")
    else:
        logger.warning("ANTHROPIC_API_KEY not set — LLM features will use fallback/mock responses")

    logger.info("ThookAI API started successfully!")

    # Run slow startup tasks in the background so the server accepts connections immediately.
    # This prevents Railway from killing the container during health check timeout.
    async def _deferred_startup():
        # Create database indexes
        try:
            from database import db
            from db_indexes import create_indexes
            logger.info("Checking database indexes...")
            result = await create_indexes(db)
            logger.info(f"Index check complete: {result['created']} created, {result['skipped']} existing")
            if result['errors']:
                for error in result['errors']:
                    logger.warning(f"Index error: {error}")
        except Exception as e:
            logger.warning(f"Could not check/create indexes: {e}")

        # Validate LightRAG embedding config
        try:
            from services.lightrag_service import assert_lightrag_embedding_config
            await assert_lightrag_embedding_config()
        except AssertionError as e:
            logger.warning("LightRAG embedding config invalid — knowledge graph disabled: %s", e)
        except Exception as e:
            logger.warning("LightRAG startup check skipped: %s", e)

        # Seed templates if collection is empty
        try:
            from database import db
            template_count = await db.templates.count_documents({})
            if template_count == 0:
                from scripts.seed_templates import seed_templates
                await seed_templates()
                logger.info(f"Seeded {await db.templates.count_documents({})} templates")
        except Exception as e:
            logger.warning(f"Could not seed templates: {e}")

        logger.info("Deferred startup tasks complete.")

    asyncio.create_task(_deferred_startup())

    yield
    
    # ==================== SHUTDOWN ====================
    logger.info("Shutting down ThookAI API...")

    try:
        from middleware.redis_client import close_redis
        await close_redis()
        logger.info("Middleware Redis connection closed")
    except Exception as e:
        logger.error(f"Error closing middleware Redis connection: {e}")

    try:
        from database import client
        client.close()
        logger.info("Database connection closed")
    except Exception as e:
        logger.error(f"Error closing database connection: {e}")

    logger.info("ThookAI API shutdown complete")


# ==================== APPLICATION SETUP ====================

app = FastAPI(
    title="ThookAI API",
    version="1.0.0",
    description="AI-powered content creation platform API",
    lifespan=lifespan,
    # Disable docs in production (optional, can be configured via env)
    docs_url="/api/docs" if not settings.app.is_production else None,
    redoc_url="/api/redoc" if not settings.app.is_production else None,
)


@app.get("/health")
async def health_check():
    """Health check for Render/load balancer monitoring.

    Checks: MongoDB, Redis, R2 storage, LLM provider.
    Returns 200 if all critical services are reachable, 503 if any critical service is down.
    """
    from database import db
    from datetime import datetime, timezone

    checks = {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "services": {}
    }
    critical_down = False

    # 1. MongoDB (critical)
    try:
        await db.command("ping")
        checks["services"]["mongodb"] = {"status": "connected"}
    except Exception as e:
        checks["services"]["mongodb"] = {"status": "disconnected", "error": str(e)}
        critical_down = True

    # 2. Redis (critical for task queue)
    try:
        from middleware.redis_client import get_redis
        redis = await get_redis()
        if redis:
            await redis.ping()
            checks["services"]["redis"] = {"status": "connected"}
        else:
            checks["services"]["redis"] = {"status": "not_configured"}
    except Exception as e:
        checks["services"]["redis"] = {"status": "disconnected", "error": str(e)}

    # 3. R2 Storage
    if settings.r2.has_r2():
        checks["services"]["r2_storage"] = {"status": "configured"}
    else:
        checks["services"]["r2_storage"] = {"status": "not_configured"}

    # 4. LLM Provider
    if settings.llm.has_llm_provider():
        checks["services"]["llm"] = {"status": "configured"}
    else:
        checks["services"]["llm"] = {"status": "not_configured"}

    if critical_down:
        checks["status"] = "unhealthy"

    status_code = 200 if not critical_down else 503
    return JSONResponse(content=checks, status_code=status_code)


api_router = APIRouter(prefix="/api")

# ==================== ROUTES ====================

api_router.include_router(auth_router)
api_router.include_router(password_reset_router)
api_router.include_router(google_auth_router)
api_router.include_router(social_auth_router)
api_router.include_router(onboarding_router)
api_router.include_router(persona_router)
api_router.include_router(content_router)
api_router.include_router(dashboard_router)
api_router.include_router(platforms_router)
api_router.include_router(repurpose_router)
api_router.include_router(analytics_router)
api_router.include_router(billing_router)
api_router.include_router(viral_router)
api_router.include_router(agency_router)
api_router.include_router(templates_router)
api_router.include_router(media_router)
api_router.include_router(uploads_router)
api_router.include_router(notifications_router)
api_router.include_router(webhooks_router)
api_router.include_router(campaigns_router)
api_router.include_router(uom_router)
api_router.include_router(viral_card_router)
api_router.include_router(n8n_bridge_router)
api_router.include_router(strategy_router)
api_router.include_router(obsidian_router)

# Admin dashboard — hidden from Swagger, requires admin role
app.include_router(admin_router, prefix="/api/admin", include_in_schema=False)


@api_router.get("/")
async def root():
    """API root endpoint"""
    return {
        "message": "ThookAI API v1.0",
        "status": "running",
        "environment": settings.app.environment
    }


@api_router.get("/config/status")
async def config_status():
    """Configuration status endpoint (development only)"""
    if settings.app.is_production:
        return {"detail": "Not available in production"}
    
    return settings.validate()


app.include_router(api_router)

# ==================== MIDDLEWARE STACK ====================
# Order matters! Middleware is executed in reverse order (bottom to top)

_raw_origins = [o.strip() for o in settings.security.cors_origins if o.strip()]

# When credentials=True, CORSMiddleware rejects wildcard "*".
# Default to known production origins if CORS_ORIGINS is unset or "*".
if _raw_origins == ["*"] or not _raw_origins:
    allowed_origins = [
        "https://www.thook.ai",
        "https://thook.ai",
        "https://thook-ai-production.vercel.app",
        "http://localhost:3000",
    ]
else:
    allowed_origins = _raw_origins

# 1. CORS - must be first (closest to response)
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=allowed_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 1.5. CSRF protection (double-submit cookie) — after CORS, before security headers
# Enforces X-CSRF-Token header for all state-changing cookie-authenticated requests.
app.add_middleware(CSRFMiddleware)

# 2. Security headers
app.add_middleware(SecurityHeadersMiddleware)

# 3. Rate limiting
app.add_middleware(
    RateLimitMiddleware,
    default_limit=settings.security.rate_limit_per_minute,
    auth_limit=settings.security.rate_limit_auth_per_minute
)

# 4. Input validation
app.add_middleware(InputValidationMiddleware)

# 5. Response compression
app.add_middleware(CompressionMiddleware, minimum_size=500, compression_level=6)

# 6. Response caching (for static endpoints)
app.add_middleware(CacheMiddleware, max_entries=1000)

# 7. Request timing (first middleware, closest to request)
app.add_middleware(TimingMiddleware, slow_request_threshold_ms=500)

# OAuth (Authlib) requires server-side session for authorize state / PKCE
if settings.app.is_production and not settings.security.jwt_secret_key:
    raise RuntimeError("JWT_SECRET_KEY is required for session middleware in production")
_session_secret = settings.security.jwt_secret_key or "dev-only-oauth-session-secret"
app.add_middleware(
    SessionMiddleware,
    secret_key=_session_secret,
    same_site="none" if settings.app.is_production else "lax",
    https_only=settings.app.is_production,
)


# ==================== ERROR HANDLERS ====================

STATUS_TO_ERROR_CODE = {
    400: "BAD_REQUEST",
    401: "UNAUTHORIZED",
    402: "PAYMENT_REQUIRED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    409: "CONFLICT",
    413: "PAYLOAD_TOO_LARGE",
    422: "VALIDATION_ERROR",
    429: "RATE_LIMITED",
    500: "INTERNAL_ERROR",
    503: "SERVICE_UNAVAILABLE",
}


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Standardize all HTTPException responses to include error_code field (BACK-03, BACK-04)."""
    error_code = STATUS_TO_ERROR_CODE.get(exc.status_code, "ERROR")
    if isinstance(exc.detail, dict):
        # detail is already a structured dict (e.g., from validate_password_strength)
        # Merge error_code in without wrapping
        content = {**exc.detail, "error_code": error_code}
    else:
        content = {"detail": exc.detail, "error_code": error_code}
    return JSONResponse(status_code=exc.status_code, content=content)


@app.exception_handler(StarletteHTTPException)
async def starlette_http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Standardize Starlette HTTP exceptions (e.g., route-not-found 404) to include error_code."""
    error_code = STATUS_TO_ERROR_CODE.get(exc.status_code, "ERROR")
    if isinstance(exc.detail, dict):
        content = {**exc.detail, "error_code": error_code}
    else:
        content = {"detail": exc.detail, "error_code": error_code}
    return JSONResponse(status_code=exc.status_code, content=content)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Standardize Pydantic validation errors to include error_code and field-level errors (BACK-02, BACK-05)."""
    errors = [
        {
            "field": ".".join(str(loc) for loc in e["loc"] if loc != "body"),
            "message": e["msg"],
        }
        for e in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content={
            "detail": "Validation failed",
            "error_code": "VALIDATION_ERROR",
            "errors": errors,
        },
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled errors"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)

    # In production, don't expose internal error details
    if settings.app.is_production:
        return JSONResponse(status_code=500, content={"detail": "An internal error occurred", "error_code": "INTERNAL_ERROR"})

    return JSONResponse(status_code=500, content={"detail": str(exc), "type": type(exc).__name__, "error_code": "INTERNAL_ERROR"})


# Server is started via Procfile: uvicorn server:app --host 0.0.0.0 --port $PORT
# No __main__ block needed — see backend/Procfile
