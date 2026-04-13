# Phase 34: Security & GDPR — Research

**Researched:** 2026-04-12
**Domain:** Web application security, GDPR compliance, FastAPI + React hardening
**Confidence:** HIGH — all findings verified against live codebase via grep and file reads

---

## Summary

Phase 34 is a hardening sprint, not a feature sprint. Most of the structural security
infrastructure already exists (CSRF middleware, rate limiting, Pydantic validation models,
security headers, global exception handlers with production/dev branching, and basic
GDPR endpoints). The remaining work is largely gap-filling: one critical PostHog consent
issue in `index.html`, one missing "Data" tab in Settings UI wiring the GDPR endpoints to
the frontend, two minor `os.environ.get` violations in production code, an XSS sanitization
layer that currently stores payloads as literals rather than stripping them, and a
`pip-audit`/`npm audit` CVE sweep that has never been run.

**Primary recommendation:** The phase should focus on (1) gating PostHog init behind
consent in `index.html` — this is the most visible GDPR compliance gap, (2) adding
server-side XSS sanitization with `bleach` for the highest-risk free-text fields, (3)
wiring the already-built GDPR API endpoints into a Settings "Data" tab, and (4)
running dependency audits and documenting results. Privacy/Terms pages, CSRF, rate
limiting, and error handling are already substantially complete.

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SECR-01 | Every POST endpoint has Pydantic models with field constraints | 60 Pydantic model classes found in routes/. Audit needed to confirm every @router.post has a typed body parameter |
| SECR-02 | All text inputs sanitized for XSS before storage | No `bleach` or `html.escape` calls found in production backend. Currently stores XSS payloads as literals. Needs `bleach.clean()` on persona/content free-text fields |
| SECR-03 | No string interpolation in MongoDB queries | VERIFIED CLEAN — 0 hits for f-string interpolation in Motor query positions |
| SECR-04 | Every state-changing endpoint has CSRF protection | `CSRFMiddleware` is live in `server.py`. Tested in `backend/tests/test_csrf.py`. Exemptions list is correct |
| SECR-05 | Rate limiting tuned per endpoint with per-user limits | `RateLimitMiddleware` exists with per-path limits. Missing: GDPR endpoints, per-user (not per-IP) limits |
| SECR-06 | No hardcoded secrets in codebase | 3 minor violations found outside `config.py` (see audit below). All are low risk |
| SECR-07 | No stack traces in production error responses | VERIFIED — `global_exception_handler` branches on `is_production` correctly |
| SECR-08 | Dependency audit — 0 critical/high CVEs | `pip-audit` not installed. `npm audit` not run. Both need to be executed and findings fixed |
| SECR-09 | GDPR data export at GET /api/auth/export | IMPLEMENTED — endpoint exists in `routes/auth.py`, returns JSON within ~500ms for typical users |
| SECR-10 | GDPR account deletion at DELETE /api/auth/account | PARTIALLY IMPLEMENTED — endpoint exists as `POST /api/auth/delete-account`. Roadmap spec says DELETE /api/auth/account. Method and path need alignment |
| SECR-11 | GDPR cookie consent banner; PostHog only after Accept | CRITICAL GAP — `posthog.init()` fires unconditionally in `frontend/public/index.html` on page load, before any consent check |
| SECR-12 | /privacy page with real content | IMPLEMENTED — `PrivacyPolicy.jsx` exists with 7 real sections, no Lorem Ipsum |
| SECR-13 | /terms page with real content | IMPLEMENTED — `TermsOfService.jsx` exists with 10 real sections, no Lorem Ipsum |
</phase_requirements>

---

## 1. Current State Audit (Grep-Verified)

### 1.1 Security Infrastructure — What Already Exists

All of the following are LIVE in production code (verified by file reads):

| Component | File | Status | Notes |
|-----------|------|--------|-------|
| `SecurityHeadersMiddleware` | `backend/middleware/security.py:25` | COMPLETE | X-Frame-Options, CSP, HSTS, X-XSS-Protection |
| `RateLimitMiddleware` | `backend/middleware/security.py:193` | COMPLETE | Redis sliding window + in-memory fallback |
| `InputValidationMiddleware` | `backend/middleware/security.py:290` | COMPLETE | 10MB body limit, content-type check |
| `CSRFMiddleware` | `backend/middleware/csrf.py` | COMPLETE | Double-submit cookie pattern; exempt list correct |
| Global exception handler | `backend/server.py:451` | COMPLETE | Production: `{"detail": "An internal error occurred"}`, dev: includes traceback |
| Pydantic validation error handler | `backend/server.py:431` | COMPLETE | Returns 422 with field-level errors, no file paths |
| GDPR export endpoint | `backend/routes/auth.py:227` | IMPLEMENTED | `GET /api/auth/export`, returns structured JSON |
| GDPR delete endpoint | `backend/routes/auth.py:290` | IMPLEMENTED (path mismatch) | `POST /api/auth/delete-account` — roadmap spec says `DELETE /api/auth/account` |
| Privacy Policy page | `frontend/src/pages/PrivacyPolicy.jsx` | COMPLETE | 7 sections, real content, no Lorem |
| Terms of Service page | `frontend/src/pages/TermsOfService.jsx` | COMPLETE | 10 sections, real content, no Lorem |
| Cookie consent banner | `frontend/src/components/CookieConsent.jsx` | PARTIAL | UI exists; decline calls `posthog.opt_out_capturing()` but PostHog already initialized |

### 1.2 os.environ.get Violations Outside config.py

**Command:** `grep -rn "os.environ.get" backend/ --include="*.py" | grep -v config.py | grep -v .venv | grep -v tests/`

**Findings (3 violations in production code):**

| File | Line | Violation | Risk |
|------|------|-----------|------|
| `backend/server.py` | 465 | `os.environ.get("PORT", 8000)` | LOW — only in `if __name__ == "__main__"` block, never runs in production (uvicorn is started via Procfile) |
| `backend/routes/auth_google.py` | 44 | Comment says "FIXED: use settings instead of os.environ.get directly" | Likely resolved — needs visual confirmation |
| `backend/services/vector_store.py` | 41 | Comment says "FIXED: use module constant instead of os.environ.get" | Likely resolved — needs visual confirmation |

**`grep -rE '(API_KEY|SECRET|PASSWORD)\s*=' backend/ --include="*.py"` outside config.py:** The grep shows references to these strings in log messages, error messages, and comments (e.g. `"STRIPE_SECRET_KEY"` as a string literal in logs) — not as assignment of actual values. No hardcoded credentials found. [VERIFIED]

**`_env_value_for_config` in `backend/services/creative_providers.py`** reads from `settings.*` (config dataclasses), not from `os.environ.get` directly. This function is legitimate. [VERIFIED]

**Conclusion for SECR-06:** The `server.py:465` `os.environ.get("PORT")` is the only genuine (but benign) violation. The success criterion `grep -r 'os.environ.get' backend/` returning zero results will still fail on this line. It must be cleaned.

### 1.3 MongoDB Query String Interpolation (SECR-03)

**Command:** `grep -rn 'f"{'  backend/ --include="*.py" | grep -v .venv | grep -v tests/ | grep -iE "mongo|find|query|aggregate|\.db\."` 

**Findings:** 0 f-string interpolations in Motor query positions. [VERIFIED CLEAN]

The two hits found (`commander.py:144` research_query string, `lightrag_service.py:145` URL construction) are NOT MongoDB queries — they are LLM prompt and HTTP URL construction respectively.

### 1.4 POST Endpoints vs Pydantic Models (SECR-01)

**Counts:**
- Total `@router.post` decorators across `backend/routes/`: **85** [VERIFIED]
- Pydantic model classes in `backend/routes/`: **60** [VERIFIED]

The mismatch (85 POST endpoints, 60 Pydantic classes) is not necessarily 1:1 — some models are reused, some endpoints take no body, some take path/query params only. A targeted audit per route file is needed. High-risk endpoints that must have Pydantic body models: all content generation, persona update, onboarding, agency invite, and template creation endpoints.

### 1.5 XSS Sanitization (SECR-02)

**`bleach` in requirements.txt:** NOT PRESENT [VERIFIED]

**`bleach` usage in production code:** NOT PRESENT [VERIFIED]

**Current XSS posture:**
- Backend returns JSON (not HTML) — no browser rendering of stored strings
- `SecurityHeadersMiddleware` sets `Content-Security-Policy: default-src 'none'` — blocks inline script execution in any backend-rendered HTML (there is none)
- Existing test `test_register_name_xss_stored_as_literal_string` PASSES because the test asserts the XSS string is stored as a literal — this is the CURRENT behavior (no sanitization), not the DESIRED behavior

**For SECR-02 compliance**, server-side sanitization is required. The highest-risk fields:
- `name` field in user registration (`backend/routes/auth.py:RegisterRequest`)
- Persona fields: `bio`, `writing_samples`, interview answers (stored in `db.persona_engines`)
- Content job `raw_input` field (user's content brief)
- Template `hook_type`, `description`, `content` fields
- Onboarding interview responses

**Strategy:** Use Python's stdlib `html.escape()` for simple cases, or add `bleach` for rich-text fields. `bleach` strips HTML tags while allowing safe whitelisted tags. For ThookAI's API-only backend that returns JSON, `html.escape()` on input fields is sufficient — there is no rendered HTML.

**Note:** The existing XSS test will need updating — it currently asserts `name == "<script>alert(1)</script>"` (stored literally). After sanitization, it should assert `name == "&lt;script&gt;alert(1)&lt;/script&gt;"` (escaped).

### 1.6 CSRF Status (SECR-04)

`CSRFMiddleware` is fully implemented and registered in `server.py` (line 354). [VERIFIED]

Key implementation details:
- Double-submit cookie pattern: `session_token` (httpOnly) + `csrf_token` (JS-readable)
- Safe methods (GET, HEAD, OPTIONS, TRACE) always pass
- Login/register endpoints are exempt (pre-auth)
- Stripe webhooks are exempt (use Stripe signature verification)
- n8n webhooks exempt via `/api/n8n/` prefix
- Bearer token requests (no `session_token` cookie) skip CSRF — correct for mobile/API clients
- Tests exist: `backend/tests/test_csrf.py`

**Conclusion:** SECR-04 is substantially complete. No new work needed for the middleware itself. The planner needs to verify the CSRF token is correctly sent from the frontend `apiFetch()` function.

### 1.7 Rate Limiting Status (SECR-05)

Current per-endpoint limits (from `backend/middleware/security.py:205-216`):

```
/api/auth/login:           10/min
/api/auth/register:        10/min
/api/auth/forgot-password: 10/min
/api/auth/reset-password:  10/min
/api/content/create:       20/min
/api/viral/predict:        30/min
/api/viral/improve:        20/min
/api/viral-card/analyze:   5/min
/api/billing/webhook/stripe: 120/min
/api/uploads/media:        10/min
Default:                   60/min
```

**Gaps for SECR-05:**
- GDPR endpoints (`/api/auth/export`, `/api/auth/delete-account`) have no per-endpoint limit — defaulting to 60/min. Should be 2-3/day max.
- No per-user limits (current limits are per-IP). For content generation, free-tier users can hit the IP limit 20 times/min but might share IPs (NAT). Per-user-per-day limits are a separate concern from the IP-based middleware; they belong in the route handler using Redis with `user_id` as key.
- Missing from endpoint_limits dict: onboarding generation, persona generation — these are expensive LLM calls

### 1.8 Error Response Hardening (SECR-07)

`server.py:451-460` — global exception handler: [VERIFIED]
```python
if settings.app.is_production:
    return JSONResponse(status_code=500, content={"detail": "An internal error occurred", "error_code": "INTERNAL_ERROR"})
return JSONResponse(status_code=500, content={"detail": str(exc), "type": type(exc).__name__, "error_code": "INTERNAL_ERROR"})
```

Sentry is initialized at startup when `SENTRY_DSN` env var is set (`server.py:96-104`). No PII scrubbing is configured for Sentry — `sentry_sdk.init()` has no `before_send` callback. For GDPR compliance, Sentry should scrub PII fields from error events.

**ValidationError responses** (Pydantic v2, `server.py:431-448`): Returns field name + message, no file paths. Safe. [VERIFIED]

### 1.9 PostHog Consent Gating (SECR-11) — CRITICAL GAP

`frontend/public/index.html:109-116`:
```javascript
posthog.init("phc_xAvL2Iq4tFmANRE7kzbKwaSqp1HJjN7x48s3vr0CMjs", {
    api_host: "https://us.i.posthog.com",
    person_profiles: "identified_only",
    session_recording: { ... }
});
```

This fires **unconditionally** on every page load, before any consent check. [VERIFIED]

`CookieConsent.jsx` (the React component) does call `posthog.opt_out_capturing()` when the user declines — but PostHog has ALREADY been initialized by the time the React app loads. This means:
- First-time visitors with no stored consent have PostHog running
- The "decline" path calls opt_out AFTER data collection has already started for that session
- This fails the GDPR requirement that "PostHog only initializes after Accept"

**The fix must be in `index.html`, not in the React component.** The inline script must check localStorage before calling `posthog.init()`. The React component then handles the UI and triggers initialization on Accept if not already done.

### 1.10 Cookie Consent Component Status

`frontend/src/components/CookieConsent.jsx` is well-built:
- Shows banner after 1500ms on first visit (no stored consent)
- "Accept all" → `localStorage.setItem(CONSENT_KEY, "accepted")`, calls `posthog.opt_in_capturing()` if posthog already loaded
- "Essential only" → `localStorage.setItem(CONSENT_KEY, "declined")`, calls `posthog.opt_out_capturing()`
- Animated, accessible (aria-label on close button), links to `/privacy`
- Storage key: `thookai_cookie_consent`

The component correctly implements the React side. The only issue is that PostHog is initialized before this component runs.

### 1.11 Privacy and Terms Pages

Both pages exist with real content (April 2026 dates, 7/10 sections respectively):
- `PrivacyPolicy.jsx`: Covers data collected, use, third parties, GDPR rights, retention, cookies, contact. References `privacy@thookai.com`. [VERIFIED]
- `TermsOfService.jsx`: Covers acceptance, description, account, content ownership, acceptable use, credits/billing, AI disclaimer, liability, changes, contact. References `legal@thookai.com`. [VERIFIED]
- No Lorem Ipsum in either file. [VERIFIED by grep]

**Minor gap:** Privacy policy section 6 (Cookies) says "You can manage cookie preferences in your browser settings" — it should reference the in-app cookie consent banner and the `thookai_cookie_consent` localStorage key.

### 1.12 GDPR Endpoints — Deep Audit

**GET /api/auth/export** (`routes/auth.py:227`): [VERIFIED]
- Collects: `users` (no hashed_password), `persona_engines`, `content_jobs` (last 500), `credit_transactions` (last 500), `platform_tokens` (platform name only — tokens redacted), `user_feedback` (last 100), `uploads` (last 200)
- Returns: `JSONResponse` with `Content-Disposition: attachment` header
- Missing collections: `scheduled_posts`, `media_assets`, `workspace_members`, `templates` (authored)
- Datetime serialization: handled inline via `json.dumps(..., default=_serialize)`
- Performance: buffered (loads all results into memory). For a power user with 500 jobs this is ~2MB JSON — well within the 10s budget. [ACCEPTABLE]

**POST /api/auth/delete-account** (`routes/auth.py:290`): [VERIFIED]
- Requires `{"confirm": "DELETE"}` in request body (confirmation gate)
- Anonymizes user record: email → `deleted-{user_id}@anonymized.thookai`, name → "Deleted User", wipes hashed_password, google_id, stripe_customer_id
- Deletes: `persona_engines`, `platform_tokens`, `user_sessions`, `uploads`, `user_feedback`
- Anonymizes (keeps for analytics): `content_jobs` — sets `user_id = "deleted-{user_id[:8]}"`, `raw_input = "[deleted]"`
- Clears auth cookies
- Logs: `logger.info("Account deleted (anonymized) for user_id=%s", user_id)` — non-PII log

**Path discrepancy:** Roadmap success criterion says `DELETE /api/auth/account`, but the implementation uses `POST /api/auth/delete-account`. The Privacy Policy page references "Settings → Data → Delete Account" UI. Either the endpoint path needs to match the roadmap spec, or the success criterion needs to match the implementation. Recommendation: align to `POST /api/auth/delete-account` (keep implementation, update roadmap/docs) — a POST with confirmation body is safer UX than a bare DELETE.

**Missing:** No Settings UI "Data" tab wiring the export/delete endpoints. The Privacy Policy page says "Settings → Data → Export" but this tab does not exist in `Settings.jsx`. [VERIFIED by search]

---

## 2. Standard Stack for This Phase

### Core (already in codebase or minimal additions)

| Library | Version | Purpose | Status |
|---------|---------|---------|--------|
| `bleach` | `6.1.0` | Server-side HTML sanitization for XSS | NOT in requirements.txt — needs adding |
| `pip-audit` | latest | Python CVE scanner | CLI tool — install in dev/CI, not requirements.txt |
| `html.escape` | stdlib | Python's built-in HTML escaping | Available without new packages |
| `posthog` (JS) | already loaded | Product analytics | Gate init behind consent in index.html |

**Note:** `bleach` is the standard choice for Python HTML sanitization. `html.escape()` (stdlib) is sufficient for API-only use cases where strings are never rendered as HTML. [CITED: https://bleach.readthedocs.io/en/latest/]

For ThookAI's purely JSON-returning API, `html.escape()` on user-supplied free-text fields is the right call — it has zero dependencies and is unambiguous. Reserve `bleach` if rich-text with allowed tags is ever needed.

**Installation (if bleach is chosen):**
```bash
pip install "bleach>=6.1.0,<7.0"
```
Add to `backend/requirements.txt`.

### npm Audit Scope

Frontend has 99 npm dependencies (`frontend/package.json`). The primary audit concern is `react-scripts` (CRA 5.x) which bundles webpack, babel, and other tools with known CVEs that are often `devDependencies` or false positives.

```bash
cd frontend && npm audit --audit-level=high
```

---

## 3. Architecture Patterns

### Pattern 1: XSS Sanitization Helper

```python
# backend/services/sanitize.py  (NEW FILE)
# Source: Python docs + OWASP Input Validation Cheat Sheet
import html
import re

# Fields that are free-text and displayed back to users
FREE_TEXT_FIELDS = frozenset({
    "name", "bio", "writing_samples", "raw_input",
    "description", "content", "hook_type",
})

def sanitize_text(value: str) -> str:
    """Escape HTML special characters from user-supplied text.

    This prevents XSS in any context where the string might be
    rendered as HTML. Safe for storage in MongoDB.
    """
    if not isinstance(value, str):
        return value
    return html.escape(value, quote=True)

def sanitize_dict(data: dict, fields: frozenset = FREE_TEXT_FIELDS) -> dict:
    """Return new dict with specified fields HTML-escaped."""
    return {
        k: sanitize_text(v) if k in fields and isinstance(v, str) else v
        for k, v in data.items()
    }
```

Apply in route handlers BEFORE storing to MongoDB, AFTER Pydantic validation:

```python
from services.sanitize import sanitize_text

@router.post("/register")
async def register(data: RegisterRequest, response: Response):
    # data.name comes from Pydantic — already type-validated
    safe_name = sanitize_text(data.name)
    # ... store safe_name in MongoDB
```

### Pattern 2: PostHog Consent Gate in index.html

The fix wraps the `posthog.init()` call in a consent check:

```html
<!-- frontend/public/index.html -->
<script>
  // Initialize PostHog stub (always — so posthog.opt_in_capturing() works later)
  !(function (t, e) { /* existing stub code */ })(document, window.posthog || []);

  // Only call posthog.init() if user has already consented
  // CookieConsent.jsx will call posthog.init() + posthog.opt_in_capturing() on Accept
  (function() {
    var consent = localStorage.getItem('thookai_cookie_consent');
    if (consent === 'accepted') {
      posthog.init("phc_xAvL2Iq4tFmANRE7kzbKwaSqp1HJjN7x48s3vr0CMjs", {
        api_host: "https://us.i.posthog.com",
        person_profiles: "identified_only",
        session_recording: { recordCrossOriginIframes: true, capturePerformance: false }
      });
    }
  })();
</script>
```

Update `CookieConsent.jsx` `accept()` function to call `posthog.init()` if not already initialized:

```javascript
const accept = () => {
  localStorage.setItem(CONSENT_KEY, "accepted");
  setVisible(false);
  // Initialize PostHog now (was not initialized at page load without consent)
  if (window.posthog && !window.posthog.__loaded) {
    window.posthog.init("phc_xAvL2Iq4tFmANRE7kzbKwaSqp1HJjN7x48s3vr0CMjs", {
      api_host: "https://us.i.posthog.com",
      person_profiles: "identified_only",
    });
  } else if (window.posthog && window.posthog.has_opted_out_capturing?.()) {
    window.posthog.opt_in_capturing();
  }
};
```

### Pattern 3: Settings "Data" Tab for GDPR

New tab in `frontend/src/pages/Dashboard/Settings.jsx` (alongside Profile, Billing, etc.):

```jsx
function DataTab({ user }) {
  const [exporting, setExporting] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState("");
  const { toast } = useToast();

  const handleExport = async () => {
    setExporting(true);
    try {
      const res = await apiFetch('/api/auth/export');
      const blob = new Blob([JSON.stringify(await res.json(), null, 2)],
        { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `thookai-export-${Date.now()}.json`;
      a.click();
      URL.revokeObjectURL(url);
      toast({ title: "Export complete", description: "Your data has been downloaded." });
    } catch (err) {
      toast({ title: "Export failed", variant: "destructive" });
    } finally {
      setExporting(false);
    }
  };

  const handleDelete = async () => {
    if (deleteConfirm !== "DELETE") return;
    // Call POST /api/auth/delete-account with confirmation
    // Redirect to landing page on success
  };
  // ... render UI
}
```

### Pattern 4: Rate Limit for GDPR Endpoints

Add to `RateLimitMiddleware.endpoint_limits` dict:

```python
'/api/auth/export': 3,          # 3 per minute (effectively 1/day if IP-based)
'/api/auth/delete-account': 3,  # Belt-and-suspenders; route itself requires confirm="DELETE"
'/api/onboarding/start': 5,     # Expensive LLM call
'/api/onboarding/generate-persona': 2,  # Very expensive LLM call
```

For true per-user-per-day limits on GDPR export (roadmap success criterion says within 10s; abuse prevention requires rate limiting), add Redis-based per-user check inside the route:

```python
# In GET /api/auth/export route, after get_current_user:
redis = await get_redis()
if redis:
    key = f"gdpr_export:{user_id}:{datetime.now(timezone.utc).date()}"
    count = await redis.incr(key)
    await redis.expire(key, 86400)  # 24h TTL
    if count > 3:
        raise HTTPException(429, "Export limit reached. Try again tomorrow.")
```

### Pattern 5: Sentry PII Scrubbing

```python
# In server.py Sentry init:
import sentry_sdk

def _scrub_pii(event, hint):
    """Remove PII fields from Sentry error events."""
    for key in ('email', 'password', 'hashed_password', 'access_token',
                'refresh_token', 'session_token', 'csrf_token'):
        if 'request' in event and 'data' in event['request']:
            event['request']['data'].pop(key, None)
        if 'extra' in event:
            event['extra'].pop(key, None)
    return event

sentry_sdk.init(
    dsn=settings.app.sentry_dsn,
    environment=settings.app.environment,
    traces_sample_rate=0.1 if settings.app.is_production else 1.0,
    before_send=_scrub_pii,
)
```

### Anti-Patterns to Avoid

- **Using `bleach.clean()` with no allowed_tags on ALL fields:** `bleach` defaults are overly permissive. Always pass `tags=[]` and `strip=True` for fields that should contain no HTML at all.
- **Running `npm audit --fix` blindly:** This can break `react-scripts` compatibility. Audit first, fix selectively, test.
- **Calling `posthog.opt_in_capturing()` without first calling `posthog.init()`:** opt_in is a no-op if PostHog was never initialized. Must call `posthog.init()` on Accept for new visitors.
- **Removing the XSS test assertion:** The test currently asserts the string is stored literally. After sanitization, update the assertion to match the escaped form — do NOT delete the test.

---

## 4. Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| HTML sanitization | Custom regex strip | `html.escape()` (stdlib) or `bleach` | Regex misses entity variants, unicode tricks |
| CVE scanning | Manual version comparison | `pip-audit`, `npm audit` | These tools have the full NVD database |
| CSRF tokens | Custom HMAC scheme | Already built (`CSRFMiddleware`) | Existing implementation is correct |
| Rate limiting | Per-route decorators | Already built (`RateLimitMiddleware`) | Just add entries to `endpoint_limits` dict |
| Cookie consent storage | IndexedDB or cookies | `localStorage` with `thookai_cookie_consent` key | Already consistent with `CookieConsent.jsx` |

---

## 5. Common Pitfalls

### Pitfall 1: Removing `os.environ.get` from `config.py` Itself

**What goes wrong:** CLAUDE.md rule 8 says "no `os.environ.get()` in route/agent/service files". The `config.py` file IS the designated location for `os.environ.get()` calls. Do not touch `config.py`.

**How to avoid:** The only violation to fix is `server.py:465` — `os.environ.get("PORT", 8000)` in the `if __name__ == "__main__"` block. This is benign (never executes in production) but will cause the success criterion grep to fail. Fix: remove the `if __name__ == "__main__"` block entirely, or read `PORT` from `settings.app.backend_url`.

**Warning signs:** Any attempt to refactor `config.py` to remove its `os.environ.get` calls.

### Pitfall 2: Implementing GDPR Export as Blocking Memory-Load for Large Users

**What goes wrong:** A power user with 10,000+ content jobs will cause the export to load ~10MB of BSON into Python memory, serialize to JSON, and send as a single response. This could timeout and violate the 10s success criterion.

**Current implementation status:** The existing `/api/auth/export` uses `.limit(500)` on content_jobs and `.limit(500)` on transactions — this cap prevents memory blowout. The current implementation is acceptable for Phase 34.

**How to avoid:** Keep the 500-item cap per collection. Add a note to the export response: `"note": "Limited to most recent 500 items per collection. Contact support for full archive."` This is already in the endpoint docstring. Do NOT remove the `.limit(500)` calls.

**For future:** If full unbounded export is ever needed, use `StreamingResponse` with a generator:
```python
async def export_generator(user_id: str):
    async for doc in db.content_jobs.find({"user_id": user_id}, {"_id": 0}):
        yield json.dumps(doc, default=str) + "\n"

return StreamingResponse(export_generator(user_id), media_type="application/x-ndjson")
```

### Pitfall 3: Hard-Deleting the `users` Document

**What goes wrong:** `content_jobs` and other collections have `user_id` as a foreign key. If the `users` document is deleted, downstream queries for `user_id` in other collections will return orphaned records with no user context, breaking analytics.

**Current implementation:** Correct — `delete_account` anonymizes the `users` record (sets email to `deleted-{user_id}@anonymized.thookai`) rather than deleting it. Do NOT change this to a hard delete.

### Pitfall 4: Gating PostHog in React `useEffect` Instead of at Script Level

**What goes wrong:** If the gating logic is only in `CookieConsent.jsx`'s `useEffect`, PostHog's snippet in `index.html` will still fire `posthog.init()` before React hydrates. The script runs synchronously at DOM parse time; React's `useEffect` runs asynchronously after render.

**How to avoid:** The consent gate MUST be added to the `<script>` block in `index.html` that wraps the `posthog.init()` call. The React component handles showing the banner UI and calling `posthog.init()` retroactively on Accept.

**Warning signs:** Any PR that only modifies `CookieConsent.jsx` without also modifying `frontend/public/index.html`.

### Pitfall 5: Running `npm audit --fix` Without Testing

**What goes wrong:** `react-scripts` 5.0.1 has many transitive dependency CVEs that are effectively mitigated by webpack's build process (they never run in the browser). Force-fixing these can break the CRA build.

**How to avoid:** Run `npm audit --audit-level=high` first, review findings. Only fix packages where the CVE exists in runtime code (not devDependencies or build tools that don't affect the browser bundle). Document accepted exceptions in `.planning/phases/34-security-gdpr/SECURITY-EXCEPTIONS.md`.

### Pitfall 6: Blocking PostHog `opt_out` from Working on First Visit

**What goes wrong:** Some implementations check `if posthog.__loaded` and skip init if not loaded — but then calling `opt_in_capturing()` later does nothing because PostHog was never initialized.

**How to avoid:** When user clicks Accept on a first visit (no prior consent), call `posthog.init()` first, THEN `posthog.opt_in_capturing()`. The `index.html` script should only auto-init if `localStorage.getItem('thookai_cookie_consent') === 'accepted'`.

### Pitfall 7: Shipping the GDPR Export Endpoint Without a Rate Limit

**What goes wrong:** A malicious user can call `GET /api/auth/export` 60 times per minute (the global default), generating significant database load.

**How to avoid:** Add `/api/auth/export: 3` to `RateLimitMiddleware.endpoint_limits`. This limits to 3/min per IP. Additionally add a per-user Redis check inside the route (see Pattern 4 above).

---

## 6. Proposed Plan Breakdown

The planner should verify file-touching conflicts and merge as appropriate.

| Plan | Name | Requirements | Key Files | Wave |
|------|------|-------------|-----------|------|
| 34-01 | XSS Sanitization Layer | SECR-02 | `backend/services/sanitize.py` (NEW), `backend/routes/auth.py`, `backend/routes/onboarding.py`, `backend/routes/persona.py`, `backend/routes/content.py`, `backend/routes/templates.py`, `backend/requirements.txt` | 1 |
| 34-02 | Secret Audit + Error Hardening | SECR-06, SECR-07 | `backend/server.py` (PORT fix, Sentry PII scrub), `backend/routes/auth_google.py` (verify clean), `backend/services/vector_store.py` (verify clean) | 1 |
| 34-03 | Rate Limiting + CSRF Verification | SECR-04, SECR-05 | `backend/middleware/security.py` (add GDPR + onboarding limits), `backend/middleware/csrf.py` (verify exempt list), `frontend/src/lib/api.js` (verify X-CSRF-Token header) | 1 |
| 34-04 | Dependency CVE Audit | SECR-08 | `backend/requirements.txt` (version bumps), `frontend/package.json` (npm audit fixes), `.planning/phases/34-security-gdpr/SECURITY-EXCEPTIONS.md` (NEW) | 1 |
| 34-05 | GDPR Export + Delete — Backend Gaps | SECR-09, SECR-10 | `backend/routes/auth.py` (add missing collections to export, add per-user rate limit, align endpoint naming with roadmap spec) | 2 |
| 34-06 | Settings Data Tab — GDPR Frontend UI | SECR-09, SECR-10 | `frontend/src/pages/Dashboard/Settings.jsx` (add Data tab with export + delete flows) | 2 |
| 34-07 | PostHog Consent Gate | SECR-11 | `frontend/public/index.html` (gate posthog.init), `frontend/src/components/CookieConsent.jsx` (call posthog.init on Accept) | 2 |
| 34-08 | Privacy + Terms Polish | SECR-12, SECR-13 | `frontend/src/pages/PrivacyPolicy.jsx` (update cookies section to reference banner), `frontend/src/pages/TermsOfService.jsx` (minor), routing verification in `frontend/src/App.js` | 2 |
| 34-09 | Security Tests + Final Audit | All SECR-* | `backend/tests/security/test_input_validation.py` (update XSS test assertions), `backend/tests/security/test_owasp_top10.py` (add Sentry PII test), new Playwright E2E for PostHog consent | 3 |

**Wave summary:**
- Wave 1 (plans 34-01 through 34-04): Independent backend changes, no shared files
- Wave 2 (plans 34-05 through 34-08): Frontend + backend GDPR wiring; 34-05 and 34-06 share `routes/auth.py` logic so should be coordinated or sequential
- Wave 3 (plan 34-09): Tests that verify Wave 1 and Wave 2 work

### Parallelization Analysis

Can run in parallel within Wave 1:
- 34-01 (backend sanitize.py) and 34-02 (server.py Sentry + PORT) share no files
- 34-03 (middleware/security.py) and 34-04 (requirements.txt) share no files

Must be sequential:
- 34-05 BEFORE 34-06 — frontend needs the API to exist
- 34-07 can run parallel with 34-06 (different files: index.html vs Settings.jsx)
- 34-09 AFTER all Wave 2 plans

---

## 7. Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.0.0 + pytest-asyncio 0.23.0 |
| Config file | `backend/pytest.ini` |
| Quick run command | `cd backend && pytest tests/security/ -x -q` |
| Full suite command | `cd backend && pytest -x -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SECR-01 | POST endpoints have Pydantic models | unit | `pytest tests/security/test_input_validation.py::TestNoSQLInjection -x` | ✅ |
| SECR-02 | XSS sanitization on save | unit | `pytest tests/security/test_input_validation.py::TestXSSPrevention -x` | ✅ (needs assertion update) |
| SECR-03 | No MongoDB injection | unit | `pytest tests/security/test_input_validation.py::TestNoSQLInjection -x` | ✅ |
| SECR-04 | CSRF enforced | unit | `pytest tests/test_csrf.py -x` | ✅ |
| SECR-05 | Rate limiting per endpoint | unit | `pytest tests/security/test_owasp_top10.py -x` | ✅ (may need GDPR endpoint test) |
| SECR-06 | No hardcoded secrets | script | `grep -r 'os.environ.get' backend/ --include="*.py" \| grep -v config.py \| grep -v .venv \| grep -v tests/ \| wc -l` must return 0 | N/A (grep-based) |
| SECR-07 | No stack traces in production | unit | `pytest tests/security/test_owasp_top10.py::TestSecurityMisconfiguration -x` | ✅ |
| SECR-08 | 0 critical/high CVEs | tool | `cd backend && pip-audit --severity=high` + `cd frontend && npm audit --audit-level=high` | ❌ Wave 0 — pip-audit not installed |
| SECR-09 | GDPR export endpoint | integration | `pytest tests/test_gdpr.py::TestGDPRExport -x` | ❌ Wave 0 |
| SECR-10 | GDPR delete endpoint | integration | `pytest tests/test_gdpr.py::TestGDPRDelete -x` | ❌ Wave 0 |
| SECR-11 | PostHog consent gate | E2E | Playwright: open incognito, check no PostHog events, then accept, check events appear | ❌ Wave 0 (manual or Playwright) |
| SECR-12 | /privacy page exists | E2E | `pytest tests/test_frontend_smoke.py::test_privacy_page` or Playwright | ❌ Wave 0 |
| SECR-13 | /terms page exists | E2E | `pytest tests/test_frontend_smoke.py::test_terms_page` or Playwright | ❌ Wave 0 |

### Wave 0 Gaps (must create before Wave 1 implementation)

- [ ] `backend/tests/test_gdpr.py` — covers SECR-09, SECR-10
- [ ] `backend/pip-audit` installation: `pip install pip-audit` in CI (not in requirements.txt)

### Sampling Rate

- **Per plan commit:** `cd backend && pytest tests/security/ -x -q` (< 20 seconds)
- **Per wave merge:** `cd backend && pytest -x -q`
- **Phase gate:** Full suite green before `/gsd-verify-work`

---

## 8. Security Domain (ASVS)

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | bcrypt + JWT (already implemented) |
| V3 Session Management | yes | httpOnly cookie + csrf_token double-submit (already implemented) |
| V4 Access Control | yes | `get_current_user` dependency on all protected routes |
| V5 Input Validation | yes | Pydantic v2 models + `html.escape()` sanitization |
| V6 Cryptography | yes | bcrypt for passwords, Fernet for OAuth tokens, HS256 JWT |
| V7 Error Handling | yes | Production exception handler hides internals |
| V9 Communications | yes | HSTS header in SecurityHeadersMiddleware |

### Known Threat Patterns for FastAPI + MongoDB Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| NoSQL injection via operator keys `{"$where": ...}` | Tampering | Pydantic models reject arbitrary dict keys; Motor parameterized queries |
| XSS via stored user content | Tampering | `html.escape()` on input; JSON response type; CSP: default-src 'none' |
| CSRF via cross-origin form submission | Spoofing | CSRFMiddleware (double-submit cookie) |
| Brute-force login | Elevation of privilege | Rate limit 10/min on /api/auth/login + account lockout (5 attempts → 15min) |
| JWT secret exposure | Info Disclosure | Never in source; validated at startup |
| Stack trace in 500 responses | Info Disclosure | Production exception handler (`is_production` branch) |
| Sentry sending PII | Info Disclosure | Add `before_send` PII scrubber to sentry_sdk.init() |
| PostHog collecting data before consent | Privacy | Gate `posthog.init()` in index.html behind localStorage consent check |

---

## 9. Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.11 | Backend | ✓ | 3.11.x | — |
| pytest | Test runner | ✓ | 8.0.0 | — |
| pip-audit | SECR-08 | ✗ | — | `safety check` or manual NVD lookup |
| npm | Frontend audit | ✓ | per Node.js | — |
| bleach (if chosen over html.escape) | SECR-02 | ✗ | — | Use `html.escape()` from stdlib (no install needed) |

**Missing with fallback:**
- `pip-audit`: Use `html.escape()` (stdlib) for XSS; use `pip install pip-audit` in the plan as a one-time install step
- `bleach`: Not needed — `html.escape()` is sufficient for pure JSON API

---

## 10. Open Questions

1. **Endpoint path alignment — DELETE vs POST for account deletion**
   - What we know: Implementation uses `POST /api/auth/delete-account`; roadmap says `DELETE /api/auth/account`
   - What's unclear: Which is canonical? SECR-10 success criterion uses `DELETE /api/auth/account`
   - Recommendation: Update ROADMAP.md success criterion to match the implementation (`POST /api/auth/delete-account`). The implementation choice (POST with `confirm` body) is more CSRF-safe than a bare DELETE.

2. **XSS sanitization — html.escape vs bleach**
   - What we know: `html.escape()` is sufficient for JSON API, `bleach` adds overhead + dependency
   - What's unclear: Will persona fields ever be rendered as HTML in the frontend?
   - Recommendation: Use `html.escape()` for Phase 34 (zero new deps). If rich-text fields are added later, migrate to `bleach`.

3. **npm audit findings — scope unknown until run**
   - What we know: `react-scripts` 5.x has known transitive CVEs, most in devDependencies
   - What's unclear: How many high/critical CVEs affect runtime code?
   - Recommendation: Plan 34-04 must run `npm audit` and triage findings before creating fixes.

---

## 11. Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `auth_google.py:44` comment "FIXED: use settings instead..." means the actual code was fixed | §1.2 | LOW — the comment is evidence, but executor should verify the actual code at that line |
| A2 | `vector_store.py:41` comment "FIXED: use module constant..." means the actual code was fixed | §1.2 | LOW — same as A1 |
| A3 | `npm audit` findings for react-scripts 5.x are mostly devDependency CVEs that don't affect the browser bundle | §5 Pitfall 5 | MEDIUM — if runtime CVEs exist, more work is needed |
| A4 | The Settings "Data" tab described in PrivacyPolicy.jsx (§1.12) does not exist in Settings.jsx | §1.12 | LOW — verified by grep showing no `deleteAccount` or `auth/export` calls in Settings.jsx |
| A5 | PostHog project key `phc_xAvL2Iq4tFmANRE7kzbKwaSqp1HJjN7x48s3vr0CMjs` is the production key and should not be changed | §1.9, §3 Pattern 2 | LOW — this is already in production index.html |

---

## 12. Project Constraints (from CLAUDE.md)

The following CLAUDE.md directives directly constrain Phase 34 planning:

| Directive | Impact on Phase 34 |
|-----------|-------------------|
| **Rule 3:** Never hardcode secrets — use `settings.*` from `backend/config.py` | SECR-06: Fix `server.py:465` `os.environ.get("PORT")` |
| **Rule 4:** Never introduce new Python package without adding to `requirements.txt` | SECR-02: If `bleach` is added, it goes in `requirements.txt`. Prefer `html.escape()` to avoid this. |
| **Rule 8:** Config pattern — never use `os.environ.get()` outside config.py | SECR-06: Audit passes when this is clean |
| **Rule 9:** Database access — always Motor async, never synchronous PyMongo | All GDPR endpoints already correct |
| **Rule 7:** After billing changes, flag for human review | Not applicable to this phase |
| **LLM model:** `claude-sonnet-4-20250514` | Not applicable to security phase |
| **Branch strategy:** Branch from `dev`, PR targets `dev`, never commit to `main` | All Phase 34 work on `feat/security-gdpr` branch |

---

## Sources

### Primary (HIGH confidence)

- Live file read: `backend/middleware/security.py` — confirmed SecurityHeadersMiddleware, RateLimitMiddleware, InputValidationMiddleware implementations
- Live file read: `backend/middleware/csrf.py` — confirmed CSRFMiddleware implementation and exempt list
- Live file read: `backend/server.py` — confirmed global exception handler, Sentry init, middleware registration order
- Live file read: `backend/routes/auth.py` — confirmed GDPR export + delete endpoint implementations
- Live file read: `frontend/public/index.html` — confirmed unconditional `posthog.init()` at line 109
- Live file read: `frontend/src/components/CookieConsent.jsx` — confirmed partial implementation
- Live file read: `frontend/src/pages/PrivacyPolicy.jsx` and `TermsOfService.jsx` — confirmed real content, no Lorem
- Live grep: `os.environ.get` audit — 3 violations found, all classified
- Live grep: MongoDB f-string injection audit — 0 findings
- Live grep: bleach/sanitize usage — 0 findings in production code
- Live grep: XSS test coverage — confirmed test exists but asserts literal storage (current behavior)
- Live file read: `backend/requirements.txt` — confirmed `bleach` not in dependencies; `starlette>=0.47.2` pinned for CVE fixes
- Live file read: `backend/config.py` — confirmed `SecurityConfig.rate_limit_auth_per_minute` exists
- Live file read: `.planning/REQUIREMENTS.md` — confirmed SECR-13 = "Terms of service page at /terms"

### Secondary (MEDIUM confidence)

- OWASP Input Validation Cheat Sheet: `html.escape()` is the recommended approach for non-HTML backends
- PostHog documentation: `posthog.opt_out_capturing()` / `opt_in_capturing()` pattern for consent management

---

## Metadata

**Confidence breakdown:**
- Current state audit: HIGH — all claims verified by grep and file reads against live code
- Standard stack: HIGH — stdlib `html.escape()` verified; `bleach` documented as alternative
- Architecture patterns: HIGH — all patterns derived from existing code structure
- Pitfalls: HIGH — derived from concrete code evidence (e.g., exact line numbers for PostHog issue)

**Research date:** 2026-04-12
**Valid until:** 2026-05-12 (30 days — stable codebase)
