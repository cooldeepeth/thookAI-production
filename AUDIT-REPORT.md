# ThookAI Production Audit Report

**Date:** 2026-04-10
**Scope:** Full static code audit — backend, frontend, config, infrastructure
**Codebase:** ~106K lines Python backend, React frontend, 66 test files (~23K test lines)

---

## Executive Summary

ThookAI production codebase is in **good shape**. No critical security vulnerabilities found. The 12 bugs from the March 2026 audit remain fixed. Architecture is sound — proper separation of concerns, atomic DB operations, CSRF protection, and comprehensive indexing. Three HIGH issues need attention before next deploy.

| Severity | Count | Action                 |
| -------- | ----- | ---------------------- |
| CRITICAL | 0     | None                   |
| HIGH     | 3     | Fix before next deploy |
| MEDIUM   | 5     | Fix this sprint        |
| LOW      | 4     | Backlog                |

---

## HIGH Issues

### H-01: database.py bypasses config.py for MongoDB URL

**File:** `backend/database.py:17-21`
**Risk:** Config divergence — two different connection strings in production

```python
# database.py reads MONGODB_URL first, then MONGO_URL — config.py only reads MONGO_URL
MONGO_URL = (
    os.getenv("MONGODB_URL")          # <-- not in config.py
    or os.getenv("MONGO_URL")
    or "mongodb://localhost:27017/thookai"
)
```

**Fix:** Replace with `settings.database.mongo_url` or add MONGODB_URL fallback to DatabaseConfig.

### H-02: Fernet key regenerated on every call in dev mode

**File:** `backend/auth_utils.py:228-232`
**Risk:** OAuth tokens encrypted in one session silently fail to decrypt after restart

```python
if settings.app.is_production:
    raise ValueError("FERNET_KEY must be configured in production")
key = Fernet.generate_key().decode()  # New key every call — previous tokens unreadable
```

**Fix:** Cache the generated key for the process lifetime, or require FERNET_KEY in dev mode too.

### H-03: Naive datetime in Stripe cancellation message

**File:** `backend/services/stripe_service.py:384`
**Risk:** Timezone-naive datetime could show wrong cancellation date

```python
# Line 352 is correct:
datetime.fromtimestamp(subscription.current_period_end, tz=timezone.utc)

# Line 384 is missing tz:
datetime.fromtimestamp(subscription.current_period_end)  # <-- naive datetime
```

**Fix:** Add `tz=timezone.utc` to the line 384 call.

---

## MEDIUM Issues

### M-01: CSRF exempt path mismatch for Stripe webhook

**File:** `backend/middleware/csrf.py:49` vs `backend/routes/billing.py:408`
**Impact:** Non-breaking (Stripe sends no cookies so CSRF passes through), but misleading

- CSRF exempts: `/api/billing/webhook`
- Actual route: `/api/billing/webhook/stripe`

**Fix:** Update CSRF exempt to `/api/billing/webhook/stripe`.

### M-02: 59 console.log statements in production frontend

**Files:** 22 frontend files (Dashboard, Templates, Analytics, etc.)
**Risk:** Debug information leaking to browser console in production

**Fix:** Replace with proper conditional logging or remove. Prioritize Dashboard pages.

### M-03: requirements.txt lacks upper bounds on most packages

**File:** `backend/requirements.txt`
**Risk:** `pip install` on deploy could pull breaking major versions

Most packages use `>=` (e.g., `openai>=1.40.0`, `stripe>=8.0.0`). Only `pymongo>=4.6.3,<4.8` and `httpx==0.28.1` are properly constrained.

**Fix:** Pin major versions: `openai>=1.40.0,<2`, `stripe>=8.0.0,<9`, etc.

### M-04: Frontend feature flags hardcoded to `true`

**File:** `frontend/src/lib/constants.js:26-31`
**Risk:** Cannot disable features without code deploy

```javascript
export const FEATURE_FLAGS = {
  enableVoiceClone: true,       // Always on
  enableVideoGeneration: true,  // Always on
  ...
};
```

**Fix:** Read from backend `/api/config/flags` endpoint or environment variables.

### M-05: Rate limiter health check path mismatch

**File:** `backend/middleware/security.py:231` vs `backend/server.py:213`
**Impact:** Health check at `/health` is rate-limited; middleware only skips `/api/health`

```python
# security.py skips:
if request.url.path in ['/api/health', '/api/']:

# server.py registers at:
@app.get("/health")  # Not under /api prefix
```

**Fix:** Add `/health` to the skip list in RateLimitMiddleware.

---

## LOW Issues

### L-01: Direct os.environ.get in server.py **main**

**File:** `backend/server.py:404`
**Impact:** Only affects local `python server.py` execution, not production Procfile

### L-02: Session token type detection heuristic is fragile

**File:** `backend/auth_utils.py:178`
**Code:** `if '.' not in token or len(token) < 100` — assumes JWTs are always 100+ chars with dots. Edge case: very short JWTs or session tokens with dots.

### L-03: Two remaining TODO comments

- `backend/services/stripe_service.py:418` — Price cache for subscription modification
- `backend/routes/viral_card.py:41` — IP rate limiting for viral cards

### L-04: Cosmetic blank line in config.py

**File:** `backend/config.py:113-114` — Extra blank line between `@dataclass` and `class EmailConfig`

---

## Positive Findings (Things Done Right)

| Area                    | Assessment                                                         |
| ----------------------- | ------------------------------------------------------------------ |
| **Credit system**       | Atomic `find_one_and_update` prevents race conditions (BILL-07)    |
| **CSRF protection**     | Double-submit cookie pattern properly implemented                  |
| **Stripe webhooks**     | Idempotency via unique index on event_id (BILL-08)                 |
| **Pipeline resilience** | 180s global timeout + per-agent timeouts + auto credit refund      |
| **Password security**   | bcrypt hashing, policy enforcement, SHA-256 reset tokens           |
| **JWT handling**        | Refuses to operate without JWT_SECRET_KEY, no hardcoded fallback   |
| **XSS prevention**      | Zero `dangerouslySetInnerHTML` usage in entire frontend            |
| **Secret management**   | No .env files committed, proper .gitignore                         |
| **Database indexes**    | 65+ indexes across 23 collections, TTL indexes for cleanup         |
| **Config validation**   | Startup guards for production, detailed config report              |
| **Frontend API client** | Centralized apiFetch with CSRF injection, timeout, retry           |
| **Error handling**      | Global exception handler, Sentry integration, structured logging   |
| **Test coverage**       | 66 test files, ~23K lines (unit, integration, security, e2e, load) |
| **Middleware stack**    | Security headers, rate limiting, compression, input validation     |
| **LLM abstraction**     | Multi-provider (Anthropic/OpenAI/Gemini) with consistent interface |

---

## Endpoint Wiring Verification

All 27 routers registered in server.py are accounted for:

| Router         | Prefix             | Status                     |
| -------------- | ------------------ | -------------------------- |
| auth           | /api/auth          | Wired                      |
| password_reset | /api/auth          | Wired                      |
| google_auth    | /api/auth/google   | Wired                      |
| social_auth    | /api/auth          | Wired                      |
| onboarding     | /api/onboarding    | Wired                      |
| persona        | /api/persona       | Wired                      |
| content        | /api/content       | Wired                      |
| dashboard      | /api/dashboard     | Wired                      |
| platforms      | /api/platforms     | Wired                      |
| repurpose      | /api/content       | Wired                      |
| analytics      | /api/analytics     | Wired                      |
| billing        | /api/billing       | Wired                      |
| viral          | /api/viral         | Wired                      |
| agency         | /api/agency        | Wired                      |
| templates      | /api/templates     | Wired                      |
| media          | /api/media         | Wired                      |
| uploads        | /api/uploads       | Wired                      |
| notifications  | /api/notifications | Wired                      |
| webhooks       | /api/webhooks      | Wired                      |
| campaigns      | /api/campaigns     | Wired                      |
| admin          | /api/admin         | Wired (hidden from schema) |
| uom            | /api/uom           | Wired                      |
| viral_card     | /api/viral-card    | Wired                      |
| n8n_bridge     | /api/n8n           | Wired                      |
| strategy       | /api/strategy      | Wired                      |
| obsidian       | /api/obsidian      | Wired                      |

---

## Config Pattern Compliance

| File             | os.environ.get usage     | Verdict     |
| ---------------- | ------------------------ | ----------- |
| config.py        | Expected (config module) | PASS        |
| database.py      | os.getenv("MONGODB_URL") | FAIL (H-01) |
| server.py        | **main** block only      | PASS (L-01) |
| auth_google.py   | Fixed (comment confirms) | PASS        |
| vector_store.py  | Fixed (comment confirms) | PASS        |
| All other routes | None found               | PASS        |
| All services     | None found               | PASS        |
| All agents       | None found               | PASS        |

---

## Pipeline Integrity Check

| Agent     | Timeout | Error Handling                 | Model                    |
| --------- | ------- | ------------------------------ | ------------------------ |
| Commander | 25s     | Propagates to pipeline catch   | claude-sonnet-4-20250514 |
| Scout     | 25s     | Returns empty findings on fail | claude-sonnet-4-20250514 |
| Thinker   | 30s     | Propagates to pipeline catch   | claude-sonnet-4-20250514 |
| Writer    | 40s     | Propagates to pipeline catch   | claude-sonnet-4-20250514 |
| QC        | 25s     | Propagates to pipeline catch   | claude-sonnet-4-20250514 |
| Global    | 180s    | Error status + credit refund   | N/A                      |

**Known CLAUDE.md bug (model name in onboarding):** FIXED. Both `analyze-posts` and `generate-persona` now use correct model `claude-sonnet-4-20250514`.

---

## Security Checklist

| Check                                  | Status                                      |
| -------------------------------------- | ------------------------------------------- |
| No hardcoded secrets in source         | PASS                                        |
| JWT secret required in production      | PASS                                        |
| Password hashing (bcrypt)              | PASS                                        |
| Rate limiting on auth endpoints        | PASS                                        |
| CSRF protection (double-submit cookie) | PASS                                        |
| Security headers (HSTS, CSP, X-Frame)  | PASS                                        |
| Input validation middleware            | PASS                                        |
| Stripe webhook signature verification  | PASS                                        |
| OAuth token encryption (Fernet)        | PASS (production only; H-02 in dev)         |
| No SQL/NoSQL injection vectors         | PASS (parameterized queries throughout)     |
| No XSS vectors in frontend             | PASS                                        |
| Production docs URL disabled           | PASS                                        |
| Session fixation prevention            | PASS (new token on login)                   |
| Timing-safe token comparison           | PARTIAL (CSRF uses `!=`, not constant-time) |

---

## Recommendations

### Immediate (before next deploy)

1. Fix H-01 (database.py config bypass)
2. Fix H-03 (naive datetime in stripe_service.py:384)
3. Fix M-05 (health check rate limiting)

### This sprint

4. Fix M-01 (CSRF exempt path)
5. Pin dependency upper bounds (M-03)
6. Audit and remove console.log statements (M-02)

### Backlog

7. Cache Fernet key in dev mode (H-02)
8. Implement server-driven feature flags (M-04)
9. Add constant-time CSRF token comparison
10. Implement Stripe Price object cache (TODO in stripe_service.py)
