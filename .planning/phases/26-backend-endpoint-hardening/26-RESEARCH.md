# Phase 26: Backend Endpoint Hardening — Research

**Researched:** 2026-04-12
**Domain:** FastAPI backend audit, Pydantic validation, error standardization, auth guards, credit safety, rate limiting
**Confidence:** HIGH

---

## Project Constraints (from CLAUDE.md)

- Branch all work from `dev`, PRs target `dev`. Never commit to `main`.
- Branch naming: `fix/short-description`, `feat/short-description`, `infra/short-description`
- All settings via `backend/config.py` dataclasses. Never use `os.environ.get()` directly.
- Database access: always `from database import db` with Motor async. Never synchronous PyMongo.
- LLM model: `claude-sonnet-4-20250514` (Anthropic primary)
- Billing changes: flag for human review — no auto-merge on billing code
- After any change to `backend/agents/`, verify full pipeline flow
- All config lives in `backend/config.py`. Required `from config import settings` everywhere.

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| BACK-01 | Every route file (26 files) tested against production with curl — each endpoint returns correct data | Existing BACKEND-API-AUDIT.md covers 70 endpoints across v2.2 routes; 26 route files now exist (audit pre-dates campaigns.py, admin.py, etc.); needs re-audit with updated file list |
| BACK-02 | Every endpoint has Pydantic input validation with field constraints | Most POST endpoints already use BaseModel; gaps exist in routes without Field() constraints (e.g., billing POST models use Field but many others don't); audit needed |
| BACK-03 | All error responses follow standardized format (status code, detail message, error_code) | Currently zero routes emit `error_code` field — HTTPException only uses `detail`; global exception handler exists but doesn't add error_code; new standard must be defined and applied |
| BACK-04 | Every protected endpoint rejects unauthenticated requests with 401 | `get_current_user` raises 401 but detail is "Not authenticated" — not the required `{"detail": "...", "error_code": "UNAUTHORIZED"}` format; admin routes use `require_admin` |
| BACK-05 | Every endpoint handles missing/malformed request body gracefully (400, not 500) | FastAPI + Pydantic 2.x returns 422 (not 500) for missing/invalid body by default; 422 is acceptable per success criteria; gap is consistent field-level error messages |
| BACK-06 | Credit-consuming endpoints check balance before executing and refund on failure | Pipeline (`/content/create`) has full deduct-before + auto-refund-on-failure pattern; media endpoints (image/carousel/voice/video) deduct but have NO refund on pipeline failure |
| BACK-07 | Rate limiting configured per endpoint (auth endpoints stricter) | `RateLimitMiddleware` already exists with per-endpoint dict; auth endpoints at 10/min; 429 response exists but doesn't include `error_code` in response body |
| BACK-08 | Endpoint registry document (.planning/audit/BACKEND-API-AUDIT.md) with status per endpoint | Existing BACKEND-API-AUDIT.md from v2.2 covers 70 endpoints; 26 current route files have grown since then; document needs updating with all current endpoints and hardening status |
</phase_requirements>

---

## Summary

Phase 26 audits and hardens all 26 FastAPI route files. The codebase is well-structured — it has a `RateLimitMiddleware` (Redis-backed with in-memory fallback), a `get_current_user` JWT auth dependency, Pydantic 2.x models on most routes, a global exception handler that strips tracebacks in production, and `deduct_credits` with atomic MongoDB `find_one_and_update`. The infrastructure is sound; the gaps are surgical.

The three most impactful gaps are: (1) `error_code` field is entirely absent from all error responses — success criteria requires `{"detail": "...", "error_code": "UNAUTHORIZED"}` for 401s; (2) media endpoints (`/generate-image`, `/generate-carousel`, `/narrate`, `/generate-video`) deduct credits before async work but have no refund path if the downstream call fails; (3) the existing BACKEND-API-AUDIT.md was created for 70 endpoints during v2.2 and does not cover the newer route files (`admin.py`, `campaigns.py`, `obsidian.py`, `strategy.py`, `n8n_bridge.py`, etc.) and lacks hardening-status columns.

**Primary recommendation:** Add a single `ThookErrorCode` enum + a custom `http_exception_handler` in `server.py` that wraps all HTTPExceptions to include `error_code`. Then fix media endpoint refunds, verify auth coverage across all 26 files, add missing field constraints, and produce an updated audit document.

---

## Standard Stack

### Core (already in use — verify, do not replace)
| Library | Version | Purpose | Notes |
|---------|---------|---------|-------|
| FastAPI | 0.110.1 | Route registration, dependency injection, OpenAPI | `@app.exception_handler` for custom error shaping |
| Pydantic | 2.6.4 | Request body validation, field constraints | Use `Field(ge=0, le=500)`, `Field(min_length=1)` |
| python-jose | 3.3.0 | JWT decode in `auth_utils.py` | Already in use via `get_current_user` |
| motor | 3.3.1 | Async MongoDB — atomic credit ops via `find_one_and_update` | Already in use in `services/credits.py` |
| redis | 5.0.0 | Rate limit sliding window backend in `RateLimiter` | Already in use in `middleware/security.py` |
| pytest | 8.0.0 | Test framework | `pytest.ini` present, `asyncio_mode = auto` |
| httpx | 0.28.1 | `ASGITransport` for route liveness tests | Already used in `tests/integration/test_api_routes_alive.py` |

### Key Patterns Already Established
- **Auth guard**: `Depends(get_current_user)` — 155 protected endpoints already use this
- **Admin guard**: `Depends(require_admin)` — all admin routes use this (correct)
- **Credit deduction**: `await deduct_credits(user_id, CreditOperation.X)` in `services/credits.py` — atomic via MongoDB filter `{"credits": {"$gte": amount}}`
- **Credit refund**: `await add_credits(user_id, amount, source="pipeline_failure_refund")` — used in `agents/pipeline.py:_refund_credits_on_failure()`
- **Rate limiting**: `RateLimitMiddleware` with `endpoint_limits` dict in `middleware/security.py`

---

## Architecture Patterns

### Gap 1: Error Code Standardization (BACK-03, BACK-04)

**Current state:** All `HTTPException` calls use `detail="..."` only. No `error_code` field exists anywhere in application code. The global exception handler in `server.py` does not inject `error_code`.

**Required output format:**
```json
{"detail": "Authentication required", "error_code": "UNAUTHORIZED"}
```

**Pattern to implement:** Add a custom `HTTPException` handler in `server.py` that maps status codes to standard `error_code` strings. Do NOT change every individual `raise HTTPException(...)` call — instead intercept at the exception handler level:

```python
# In server.py — add BEFORE the global Exception handler
from fastapi.exceptions import RequestValidationError
from fastapi import Request
from fastapi.responses import JSONResponse

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
    error_code = STATUS_TO_ERROR_CODE.get(exc.status_code, "ERROR")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "error_code": error_code}
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    # Produce field-level messages: [{"field": "email", "message": "..."}]
    errors = []
    for e in exc.errors():
        errors.append({
            "field": ".".join(str(loc) for loc in e["loc"] if loc != "body"),
            "message": e["msg"],
            "type": e["type"]
        })
    return JSONResponse(
        status_code=422,
        content={"detail": "Validation failed", "error_code": "VALIDATION_ERROR", "errors": errors}
    )
```

**Note:** FastAPI's built-in exception handlers for `HTTPException` and `RequestValidationError` must be overridden — custom handlers take precedence when registered with `@app.exception_handler`.

**Confidence:** HIGH — verified via FastAPI 0.110 official docs pattern.

### Gap 2: Credit Refund on Media Endpoint Failure (BACK-06)

**Current state (content.py):**
- `/api/content/create` — deducts BEFORE pipeline runs; pipeline's `_refund_credits_on_failure()` auto-refunds if pipeline raises. GOOD.
- `/api/content/generate-image` — deducts synchronously, then calls `designer_generate()`; if that raises an exception the credits are gone. NO REFUND.
- `/api/content/generate-carousel` — same pattern, NO REFUND.
- `/api/content/narrate` (sync fallback path) — same pattern, NO REFUND.
- `/api/content/generate-video` (sync fallback path) — same pattern, NO REFUND.
- Async Celery path for narrate/video deducts credits INSIDE the Celery task (separate from the HTTP handler). Credits deducted in task worker context — refund logic must also live there.

**Fix pattern for sync media endpoints:**
```python
@router.post("/generate-image")
async def generate_image(data: ImageGenerateRequest, current_user: dict = Depends(get_current_user)):
    # ... existing job lookup ...
    deduct_result = await deduct_credits(current_user["user_id"], CreditOperation.IMAGE_GENERATE)
    if not deduct_result.get("success"):
        raise HTTPException(status_code=402, detail="Insufficient credits for image generation")
    
    try:
        result = await designer_generate(...)
    except Exception as exc:
        # Refund on failure
        await add_credits(
            current_user["user_id"],
            CreditOperation.IMAGE_GENERATE.value,
            source="image_generation_failure_refund",
            description=f"Refund for failed image generation job {data.job_id}"
        )
        logger.error(f"Image generation failed for job {data.job_id}: {exc}")
        raise HTTPException(status_code=500, detail="Image generation failed")
    
    # ... existing result storage ...
    return result
```

**Import required:** `from services.credits import deduct_credits, add_credits, CreditOperation`

### Gap 3: Pydantic Field Constraints Audit (BACK-02)

**Current state:** Billing models already use `Field(ge=0, le=500)` correctly. Many other POST endpoints use bare `BaseModel` without constraints. Key gaps to verify:

- `ContentCreateRequest.raw_input` — length validated manually in handler (lines 100-103); add `Field(min_length=5, max_length=50000)` to Pydantic model instead and remove manual checks
- `ContentCreateRequest.platform` — validated manually; add `Literal["linkedin", "x", "instagram"]`
- `ContentCreateRequest.content_type` — validated against `PLATFORM_CONTENT_TYPES` manually; keep manual (cross-field validation)
- `RegisterRequest.name` — no length constraint; add `Field(min_length=1, max_length=100)`
- `GeneratePersonaRequest` fields — check for min/max constraints
- `VoiceGenerateRequest.stability`, `.similarity_boost` — no range constraint; add `Field(ge=0.0, le=1.0)`

**Pydantic 2.x constraint syntax (verified):**
```python
from pydantic import BaseModel, Field
from typing import Literal, Optional

class ContentCreateRequest(BaseModel):
    platform: Literal["linkedin", "x", "instagram"]
    content_type: str
    raw_input: str = Field(min_length=5, max_length=50000)
    attachment_url: Optional[str] = None
    upload_ids: Optional[list[str]] = None
    campaign_id: Optional[str] = None
    generate_video: bool = False
    video_style: Literal["cinematic", "talking_head", "slideshow", "abstract"] = "cinematic"
```

### Gap 4: Auth Guard Coverage Audit (BACK-04)

The bash analysis found that 155 of 209 endpoint definitions use `Depends(get_current_user)` — leaving 54 endpoints without the dependency. Not all of these are bugs (public endpoints are intentional), but they require auditing.

**Legitimate public endpoints (no auth required):**
- `POST /api/auth/login`, `POST /api/auth/register`, `POST /api/auth/forgot-password`
- `GET /api/auth/google`, `GET /api/auth/google/callback`, OAuth initiation endpoints
- `GET /api/content/platform-types`, `GET /api/content/image-styles`, `GET /api/content/providers`
- `GET /api/billing/config`, `POST /api/billing/plan/preview`, `GET /api/billing/credits/costs`
- `GET /api/onboarding/questions`
- `GET /api/persona/public/{token}` (share link)
- `GET /health`, `GET /api/`, `GET /api/config/status` (dev only)
- `POST /api/billing/webhook/stripe` (uses Stripe signature instead of JWT)
- n8n bridge endpoints (use HMAC auth, not JWT)

**Endpoints needing audit:** Routes in `admin.py`, `analytics.py`, `viral_card.py`, and `n8n_bridge.py` that appear in the grep-without-auth results should be verified to confirm they use alternative auth (e.g., `require_admin`, n8n HMAC).

### Gap 5: BACKEND-API-AUDIT.md Update (BACK-08)

The existing `.planning/audit/BACKEND-API-AUDIT.md` (April 2026) covers 70 endpoints across the v2.2 route files. The current codebase has 26 route files with approximately 209 endpoint definitions — the difference includes routes added since v2.2 (`strategy.py`, `obsidian.py`, `n8n_bridge.py`, plus additional endpoints in existing files).

The audit document needs to be rebuilt from the current route files with hardening-status columns:
- `auth_guard`: YES / NO / ALTERNATIVE
- `pydantic_validation`: YES / PARTIAL / NO
- `error_format_compliant`: YES / NO (after error_code handler is added)
- `credit_safety`: N/A / DEDUCT+REFUND / DEDUCT-ONLY / NONE
- `rate_limit`: CUSTOM / DEFAULT / NONE

### Recommended Project Structure for Phase Work

```
backend/
├── server.py              # Add HTTPException + RequestValidationError handlers here
├── routes/
│   ├── content.py         # Add refund logic to generate-image/carousel/narrate/video sync paths
│   ├── auth.py            # Verify auth guard, add field constraints to RegisterRequest/LoginRequest
│   └── [all 26 files]     # Audit each for Pydantic constraints
└── tests/
    ├── test_error_format.py      # New: verify error_code in all 4xx/5xx responses
    ├── test_credit_refund.py     # New: verify refund on image/carousel/voice/video failure
    └── integration/
        └── test_api_routes_alive.py  # Extend with hardening checks
```

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Error code normalization | Custom middleware that rewrites response bodies | `@app.exception_handler(HTTPException)` in server.py | FastAPI's built-in handler override is the correct pattern — middleware body rewriting is fragile with streaming responses |
| Field validation | Manual `if len(x) < 5: raise HTTPException(...)` | Pydantic `Field(min_length=5)` in BaseModel | Pydantic 2.x runs before the handler, returns 422 automatically with field path, removes boilerplate |
| Atomic credit deduction | `find_one` + `update_one` (read-modify-write) | `find_one_and_update({"credits": {"$gte": amount}}, {"$inc": ...})` | Already implemented correctly in `services/credits.py` — do not reimport or duplicate |
| Rate limiting | Thread-local counters, custom Redis scripts | Existing `RateLimitMiddleware` with `endpoint_limits` dict | Already Redis-backed with in-memory fallback — extend the `endpoint_limits` dict to tune |
| Auth testing | Live HTTP requests against Railway | `httpx.AsyncClient(app=app, base_url="http://test")` with `ASGITransport` | Existing test infra pattern in `tests/integration/test_api_routes_alive.py` — follow this |

---

## Common Pitfalls

### Pitfall 1: Overriding FastAPI's Built-In Exception Handlers — Import Order
**What goes wrong:** `@app.exception_handler(HTTPException)` appears to register but has no effect because FastAPI internally already has a default handler.
**Why it happens:** FastAPI uses Starlette's exception handler registry; the LAST registered handler wins only for direct decorators. But FastAPI's default handlers are added at instantiation time. A custom handler added with `@app.exception_handler(HTTPException)` actually DOES override the default — this is the documented pattern.
**How to avoid:** Import `HTTPException` from `fastapi` (not `starlette.exceptions`) when registering the handler. Also import `RequestValidationError` from `fastapi.exceptions`. Register handlers BEFORE `app.include_router()` calls.
**Warning signs:** 401 responses still return `{"detail": "Not authenticated"}` without `error_code` field after adding the handler — check the import path.

### Pitfall 2: Celery Task Credit Deduction Has No HTTP-Layer Refund Path
**What goes wrong:** For narrate/video endpoints, when Redis is available, the HTTP handler queues the job and returns 202 immediately WITHOUT deducting credits (credits are deducted inside the Celery task). If the task fails, the Celery task must handle its own refund — the HTTP handler cannot refund credits it never deducted.
**Why it happens:** Two separate code paths (sync fallback deducts in HTTP handler; async Celery path deducts in task worker).
**How to avoid:** For the sync fallback path only: add `try/except/finally` with `add_credits()` on the except branch. For Celery tasks: verify `content_tasks.py` and `media_tasks.py` have their own refund logic on failure (audit separately).
**Warning signs:** Credits deducted but job shows `status: "failed"` without a corresponding credit transaction of type `"addition"` with `source` containing `"refund"`.

### Pitfall 3: Pydantic 2.x Literal Type Breaks Existing Valid Inputs
**What goes wrong:** Changing `platform: str` to `platform: Literal["linkedin", "x", "instagram"]` causes 422 for clients sending `"LinkedIn"` (capitalized) or `"twitter"` (old name).
**Why it happens:** Pydantic 2.x Literal is case-sensitive. The existing code normalizes with `.lower()` in the handler.
**How to avoid:** Keep `platform: str` in the BaseModel but add a `@field_validator("platform")` that normalizes and validates: `return v.lower()` then check against allowed set. OR use `platform: str` with `Field(pattern="^(linkedin|x|instagram)$")`.
**Warning signs:** Frontend starts getting 422 on previously working requests after adding Literal type.

### Pitfall 4: `HTTPException` `detail` as Dict Breaks `error_code` Injection
**What goes wrong:** Some existing `raise HTTPException(status_code=400, detail={"message": "...", "errors": [...]})` calls pass `detail` as a dict, not a string. The custom exception handler assumes `detail` is always a string.
**Why it happens:** `auth_utils.py:validate_password_strength()` raises `HTTPException(status_code=400, detail={"message": "...", "errors": [...]})` — the detail is a dict. The custom handler must handle both str and dict detail.
**How to avoid:** In the custom `http_exception_handler`, check `isinstance(exc.detail, dict)` and merge `error_code` into the dict rather than wrapping it:
```python
if isinstance(exc.detail, dict):
    content = {**exc.detail, "error_code": error_code}
else:
    content = {"detail": exc.detail, "error_code": error_code}
```
**Warning signs:** `{"detail": {"message": "Password...", "errors": [...]}}` becomes `{"detail": {"message": "...", "errors": [...]}, "error_code": "BAD_REQUEST"}` — this is correct. If the dict gets double-wrapped, the handler has a bug.

### Pitfall 5: Rate Limit 429 Response Missing `error_code`
**What goes wrong:** `RateLimitMiddleware.dispatch()` returns `JSONResponse(status_code=429, content={"detail": "Too many requests.", "retry_after": 60})` directly — this bypasses the `@app.exception_handler(HTTPException)` and won't automatically get `error_code` added.
**Why it happens:** The middleware returns a `JSONResponse` directly, not a raised `HTTPException` — exception handlers only intercept raised exceptions.
**How to avoid:** Add `"error_code": "RATE_LIMITED"` directly to the middleware's JSONResponse content. Also add to `CSRFMiddleware`'s 403 response. These are the two places that bypass the exception handler.

---

## Code Examples

### Custom Exception Handler (verified pattern — FastAPI 0.110.x)
```python
# Source: FastAPI official docs — Custom Exception Handlers
from fastapi import FastAPI, Request, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

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
    error_code = STATUS_TO_ERROR_CODE.get(exc.status_code, "ERROR")
    if isinstance(exc.detail, dict):
        content = {**exc.detail, "error_code": error_code}
    else:
        content = {"detail": exc.detail, "error_code": error_code}
    return JSONResponse(status_code=exc.status_code, content=content)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = [
        {
            "field": ".".join(str(loc) for loc in e["loc"] if loc != "body"),
            "message": e["msg"],
        }
        for e in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content={"detail": "Validation failed", "error_code": "VALIDATION_ERROR", "errors": errors},
    )
```

### Credit Refund Pattern for Sync Media Endpoints
```python
# Pattern to apply to generate-image, generate-carousel, narrate (sync), generate-video (sync)
from services.credits import deduct_credits, add_credits, CreditOperation

async def generate_image(data: ImageGenerateRequest, current_user: dict = Depends(get_current_user)):
    # ... job lookup ...
    deduct_result = await deduct_credits(current_user["user_id"], CreditOperation.IMAGE_GENERATE)
    if not deduct_result.get("success"):
        raise HTTPException(status_code=402, detail="Insufficient credits for image generation")
    
    try:
        result = await designer_generate(...)
    except Exception as exc:
        await add_credits(
            current_user["user_id"],
            CreditOperation.IMAGE_GENERATE.value,
            source="image_generation_failure_refund",
            description=f"Auto-refund for failed image generation on job {data.job_id}",
        )
        logger.error("Image generation failed for job %s: %s", data.job_id, exc)
        raise HTTPException(status_code=500, detail="Image generation failed. Credits refunded.")
    
    return result
```

### Pydantic Field Validator for platform normalization
```python
from pydantic import BaseModel, Field, field_validator
from typing import Literal, Optional

class ContentCreateRequest(BaseModel):
    platform: str
    content_type: str
    raw_input: str = Field(min_length=5, max_length=50000)
    
    @field_validator("platform")
    @classmethod
    def normalize_platform(cls, v: str) -> str:
        normalized = v.lower()
        allowed = {"linkedin", "x", "instagram"}
        if normalized not in allowed:
            raise ValueError(f"platform must be one of {sorted(allowed)}")
        return normalized
```

### Test Pattern for Error Code Verification
```python
# Follows existing test/integration/test_api_routes_alive.py pattern
import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, AsyncMock

@pytest.mark.asyncio
async def test_unauthenticated_protected_endpoint_returns_401_with_error_code():
    from server import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/persona/me")
    assert resp.status_code == 401
    data = resp.json()
    assert "error_code" in data
    assert data["error_code"] == "UNAUTHORIZED"
```

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.0.0 + pytest-asyncio 0.23.0 |
| Config file | `backend/pytest.ini` (asyncio_mode = auto) |
| Quick run command | `cd backend && pytest tests/test_error_format.py tests/test_credit_refund.py -x` |
| Full suite command | `cd backend && pytest -m "not integration"` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| BACK-01 | All 26 route files return correct data | Integration smoke | `pytest tests/integration/test_api_routes_alive.py -x` | Yes |
| BACK-02 | Pydantic validation on all POST endpoints | Unit | `pytest tests/test_error_format.py::test_missing_body_returns_422 -x` | No — Wave 0 |
| BACK-03 | error_code field in all 4xx/5xx responses | Unit | `pytest tests/test_error_format.py -x` | No — Wave 0 |
| BACK-04 | Unauthenticated → 401 with error_code=UNAUTHORIZED | Unit | `pytest tests/test_error_format.py::test_unauthenticated_returns_401_with_error_code -x` | No — Wave 0 |
| BACK-05 | Missing body → 400/422, never 500 | Unit | `pytest tests/test_error_format.py::test_malformed_body_never_500 -x` | No — Wave 0 |
| BACK-06 | Credits deducted before exec, refunded on failure | Unit | `pytest tests/test_credit_refund.py -x` | No — Wave 0 |
| BACK-07 | Auth endpoints enforce 10/min rate limit | Integration | `pytest tests/test_rate_limit_concurrent.py -x` | Yes (partial) |
| BACK-08 | BACKEND-API-AUDIT.md exists with all endpoints | Manual | Manual verification of file existence and content | No — Wave 0 |

### Sampling Rate
- **Per task commit:** `cd backend && pytest tests/test_error_format.py tests/test_credit_refund.py -x`
- **Per wave merge:** `cd backend && pytest -m "not integration" -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `backend/tests/test_error_format.py` — covers BACK-03, BACK-04, BACK-05
- [ ] `backend/tests/test_credit_refund.py` — covers BACK-06 (media endpoint refund)
- [ ] `.planning/audit/BACKEND-API-AUDIT.md` — covers BACK-08 (updated endpoint registry)

*(Existing `test_rate_limit.py`, `test_rate_limit_concurrent.py`, and `tests/integration/test_api_routes_alive.py` cover BACK-01, BACK-07 partially.)*

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Passlib bcrypt | Direct `bcrypt` library | v2.x (BUG-fix) | No action needed |
| `HTTPException` only (no custom handler) | Custom `http_exception_handler` | Phase 26 target | Enables `error_code` across all routes without touching individual raises |
| Manual `if len(x) < N: raise HTTPException` | Pydantic `Field(min_length=N)` | Phase 26 target | 422 with field path replaces 400 with message-only |
| Credit deduction in HTTP handler, no refund | Deduct + try/except + refund on failure | Phase 26 target for media endpoints | Prevents credit loss on provider API failures |

---

## Open Questions

1. **Celery task credit deduction path for media endpoints**
   - What we know: When Redis is available, `/narrate` and `/generate-video` queue Celery tasks and return 202 without deducting credits in the HTTP handler; credits are deducted inside `media_tasks.py`
   - What's unclear: Does `media_tasks.py` have its own refund-on-failure logic? (Not checked yet — `content_tasks.py` was not read in full.)
   - Recommendation: Planner should include a task to read `backend/tasks/media_tasks.py` and `backend/tasks/content_tasks.py` and verify refund logic exists. If not, add it.

2. **Rate limit `error_code` in `RateLimitMiddleware` and `CSRFMiddleware`**
   - What we know: Both return `JSONResponse` directly (not `raise HTTPException`), so the custom exception handler won't intercept them
   - What's unclear: Whether the success criteria's `{"detail": "...", "error_code": "UNAUTHORIZED"}` format requirement extends to 403 CSRF and 429 rate limit responses specifically
   - Recommendation: Planner should include tasks to add `"error_code": "RATE_LIMITED"` to `RateLimitMiddleware` 429 response and `"error_code": "CSRF_INVALID"` to `CSRFMiddleware` 403 response to be consistent.

3. **`/api/auth/delete-account` billing flag**
   - What we know: CLAUDE.md says billing changes need human review and no auto-merge; `delete_account` in `auth.py` is not technically billing but involves account data cleanup
   - Recommendation: No change needed to delete-account for this phase; flag the PR for informational review if any changes touch `auth.py`.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.11 | Backend tests | Yes | 3.11.x | — |
| pytest | Test execution | Yes | 8.0.0 | — |
| pytest-asyncio | Async test support | Yes | 0.23.0 | — |
| httpx | ASGI test transport | Yes | 0.28.1 | — |
| MongoDB | Integration tests | Yes (Railway) | 7.0+ | Mock with AsyncMock |
| Redis | Rate limit tests | Optional | — | In-memory fallback in RateLimiter |

---

## Sources

### Primary (HIGH confidence)
- Direct code analysis of `/backend/routes/*.py` (26 files), `/backend/middleware/security.py`, `/backend/auth_utils.py`, `/backend/services/credits.py`, `/backend/agents/pipeline.py`, `/backend/server.py` — all read directly
- `/backend/pytest.ini` — test configuration
- `/backend/requirements.txt` — confirmed FastAPI 0.110.1, Pydantic 2.6.4, pytest 8.0.0
- `.planning/audit/BACKEND-API-AUDIT.md` — existing endpoint audit (v2.2 coverage)
- `CLAUDE.md` — project constraints
- `.planning/REQUIREMENTS.md` — BACK-01 through BACK-08 definitions

### Secondary (MEDIUM confidence)
- FastAPI 0.110 custom exception handler pattern — consistent with code structure and verified as the correct override mechanism for `HTTPException` and `RequestValidationError`
- Pydantic 2.x `Field()` constraint syntax — consistent with existing `billing.py` usage of `Field(ge=0, le=500)` confirming Pydantic 2.x is active

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — directly read from requirements.txt and code
- Architecture patterns: HIGH — code read directly, gaps identified from source inspection
- Pitfalls: HIGH — derived from actual code divergences found during analysis (dict detail, middleware bypass)
- Credit refund gaps: HIGH — confirmed by tracing all `deduct_credits` calls in routes and absence of `add_credits` in catch blocks

**Research date:** 2026-04-12
**Valid until:** 2026-05-12 (stable codebase — no fast-moving dependencies)
