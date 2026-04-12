# Phase 30: Social Publishing End-to-End — Research

**Researched:** 2026-04-12
**Domain:** Social platform OAuth, token encryption, publisher agents, analytics polling
**Confidence:** HIGH — all findings sourced directly from existing codebase files

---

## Summary

Phase 30 wires together a largely-implemented backend into a verified, end-to-end publishing system. The OAuth flows for all three platforms (LinkedIn, X/Twitter, Instagram) exist in `backend/routes/platforms.py`. The publisher agent in `backend/agents/publisher.py` has complete LinkedIn and X implementations and a functioning Instagram implementation (not a stub as described — it has the full Media Container flow). The social analytics service `backend/services/social_analytics.py` exists and has all three platform metric fetchers.

The gap between "implemented" and "working end-to-end" is in five specific areas: (1) the scheduled-post publisher (`content_tasks._run_scheduled_posts_inner`) does not pass the rich publish result (post_id, post_url) back to the content_job document — it only sets status, so analytics polling has nothing to query; (2) the proactive 24-hour token refresh before expiry does not exist — `get_platform_token` in `platforms.py` only refreshes on-demand when the token is already expired; (3) the publish status/retry UI in `ContentStudio/ContentOutput.jsx` exists but needs to be verified end-to-end (Sentry event on failure is not called from the publisher path); (4) the frontend Connections page has no "token expiring soon" warning state; and (5) the social_analytics service is a hard dependency from content_tasks but is already complete.

**Primary recommendation:** Focus execution on the five gaps above. Do not rebuild OAuth or publisher code — it is already correct. The work is plumbing: store publish results properly in scheduled-post flow, add proactive token refresh, add Sentry events in the failure path, and verify the complete flow with real credentials.

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PUBL-01 | User can connect LinkedIn account via OAuth and publish UGC posts with media | OAuth initiate/callback routes exist and are complete in `routes/platforms.py`. LinkedIn UGC API publish logic exists in `agents/publisher.py`. Media support is text-only (MVP note in code). |
| PUBL-02 | User can connect X account via OAuth and publish tweets/threads with media | PKCE OAuth flow exists in `routes/platforms.py`. Thread parser and v2 API publisher in `agents/publisher.py`. No media upload path exists for X — text only. |
| PUBL-03 | User can connect Instagram account via Meta OAuth and publish posts with media | OAuth + long-lived token exchange in `routes/platforms.py`. Full Media Container flow in `agents/publisher.py`. Requires image_url (public URL from R2). |
| PUBL-04 | OAuth token auto-refresh before expiry for all platforms | On-demand refresh exists in `get_platform_token`. Proactive 24h refresh is MISSING — must be added. Instagram has no refresh_token flow (long-lived token lasts 60 days, must be manually extended). |
| PUBL-05 | Publishing status tracked: pending → publishing → published/failed | Status tracking exists in content_jobs. Scheduled post publisher does NOT store post_id/post_url in content_job after publishing — analytics polling will silently fail. Must be fixed. |
| PUBL-06 | Platform token encryption verified working in production (Fernet) | Fernet encrypt/decrypt in `routes/platforms.py`. ENCRYPTION_KEY env var required in production (raises RuntimeError if missing). Dev uses ephemeral key (tokens won't survive restart). |
| PUBL-07 | Published content shows real engagement metrics when available | `services/social_analytics.py` has fetch functions for all three platforms. Celery tasks `poll_post_metrics_24h` and `poll_post_metrics_7d` schedule polling after publish. Blocked by PUBL-05 gap (no post_id stored). |
</phase_requirements>

---

## Project Constraints (from CLAUDE.md)

- **Branch strategy**: All work branches from `dev`, PRs target `dev`. Never commit to `main`.
- **Branch naming**: `fix/short-description`, `feat/short-description`, `infra/short-description`
- **Config pattern**: All settings via `backend/config.py` dataclasses. Never use `os.environ.get()` directly in route/agent/service files. Always `from config import settings`.
- **Database pattern**: Always `from database import db` with Motor async. Never synchronous PyMongo.
- **LLM model**: `claude-sonnet-4-20250514` (not used in this phase directly)
- **Billing changes**: Flag for human review — not applicable to this phase
- **Agent pipeline**: After any change to `backend/agents/`, verify full pipeline flow
- **New Python packages**: Must add to `backend/requirements.txt`
- **New npm packages**: Must note in PR description
- **Secrets**: Never hardcode. OAuth keys come from `settings.platforms.*`
- **Test runner**: `cd backend && pytest`

---

## Standard Stack

### Core (Already in requirements.txt — no new installs needed)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| httpx | 0.28.1 | Async HTTP client for platform API calls | Already used in publisher.py and platforms.py |
| cryptography | 42.0.8 | Fernet encryption for OAuth tokens | Already used in platforms.py |
| sentry-sdk | 2.0.0+ | Error tracking on publish failures | Already initialized in server.py |
| motor | 3.3.1 | Async MongoDB writes for publish results | Standard DB pattern |
| celery | 5.3.0 | Scheduled post processing | Already configured in celeryconfig.py |

### Environment Variables Required (from PlatformOAuthConfig in config.py)

| Variable | Purpose | Current Status |
|----------|---------|----------------|
| `LINKEDIN_CLIENT_ID` | LinkedIn app client ID | In config, validated by `_valid_key()` |
| `LINKEDIN_CLIENT_SECRET` | LinkedIn app secret | In config |
| `TWITTER_API_KEY` | X/Twitter app key (also used as client_id in OAuth 2.0) | In config |
| `TWITTER_API_SECRET` | X/Twitter app secret | In config |
| `META_APP_ID` | Meta/Facebook app ID | In config |
| `META_APP_SECRET` | Meta/Facebook app secret | In config |
| `ENCRYPTION_KEY` | Fernet key for token encryption | Required in production (RuntimeError if missing) |
| `SENTRY_DSN` | Sentry DSN for error capture | Optional, already guarded |

---

## Architecture Patterns

### Existing Project Structure (do not change)

```
backend/
├── agents/publisher.py          # LinkedIn, X, Instagram publish functions
├── routes/platforms.py          # OAuth initiate, callback, status, disconnect
│                                # get_platform_token() helper (decrypts + refreshes)
├── services/social_analytics.py # fetch_*_post_metrics(), update_post_performance()
├── tasks/content_tasks.py       # _run_scheduled_posts_inner(), poll_post_metrics_24h/7d
└── routes/dashboard.py          # POST /dashboard/publish/{job_id} (immediate publish)

frontend/src/pages/Dashboard/
├── Connections.jsx              # OAuth connect/disconnect UI (complete)
└── ContentStudio/ContentOutput.jsx  # PublishPanel component (exists, needs verify)
```

### Pattern 1: OAuth State Flow (already implemented)

State token → MongoDB `oauth_states` collection → verified on callback → deleted after use. State expires in 10 minutes. X uses PKCE with `code_verifier` stored in oauth_states doc.

### Pattern 2: Token Storage Schema (already implemented)

```python
# platform_tokens collection document shape
{
    "user_id": str,
    "platform": "linkedin" | "x" | "instagram",
    "access_token": str,          # Fernet-encrypted
    "refresh_token": str | None,  # Fernet-encrypted (None for Instagram)
    "expires_at": datetime,       # UTC
    "scope": str,
    "account_name": str,          # "@username" or "Display Name"
    "connected_at": datetime,
    "updated_at": datetime,
    # Instagram only:
    "instagram_account_id": str   # Business account ID for Media Container API
}
```

### Pattern 3: Publish Result Storage (THE CRITICAL GAP — must fix)

When `_run_scheduled_posts_inner` in `content_tasks.py` publishes a post, it calls `_publish_to_platform()` which returns a `bool`. The actual publish result dict (containing `post_id`, `post_url`, `tweet_ids`) is lost — the content_job is not updated with these values.

The `social_analytics.update_post_performance()` function reads `job.get("publish_results", {})` to find the `post_id` for analytics. If `publish_results` is never stored, the 24h and 7d Celery polling tasks silently return False, and no real metrics ever appear.

**Fix pattern:**
```python
# In _run_scheduled_posts_inner, change _publish_to_platform to return the full result dict
# Then store it on the content_job:
await db_handle.content_jobs.update_one(
    {"job_id": job_id_or_schedule_id},
    {"$set": {
        "status": "published",
        "published_at": now,
        "publish_results": {platform: result_dict},  # ADD THIS
    }}
)
```

The `dashboard.publish_content_now` endpoint already stores `publish_results` correctly — match that pattern.

### Pattern 4: Proactive Token Refresh (MISSING — must add)

Current `get_platform_token()` only refreshes when token IS expired. The success criterion requires refresh 24 hours BEFORE expiry. Add a check:

```python
# In get_platform_token() after fetching token doc:
now = datetime.now(timezone.utc)
expires_at = token_doc.get("expires_at")
if expires_at:
    time_until_expiry = expires_at - now
    if time_until_expiry < timedelta(hours=24):  # proactive refresh window
        refresh_token = token_doc.get("refresh_token")
        if refresh_token:
            new_token = await _refresh_token(user_id, platform, _decrypt_token(refresh_token))
            if new_token:
                return new_token
        # If no refresh token or refresh failed, check if still valid
        if expires_at < now:
            return None  # Actually expired
```

**Instagram note**: Instagram long-lived tokens last ~60 days and have NO refresh_token. They must be renewed by calling the graph API with the existing token before expiry. This requires a separate endpoint or Celery beat task.

### Pattern 5: Sentry on Publish Failure (MISSING from publisher path)

`sentry_sdk.capture_exception()` is called from `routes/content.py` for pipeline errors, but NOT from the publish endpoints or `_run_scheduled_posts_inner`. The success criterion requires Sentry event on failed publish.

Add to `_run_scheduled_posts_inner` failure path:
```python
if settings.app.sentry_dsn:
    import sentry_sdk
    sentry_sdk.capture_message(
        f"Scheduled post publish failed: platform={platform}, schedule_id={post['schedule_id']}",
        level="error"
    )
```

### Pattern 6: X Thread Publishing — Bearer Token vs User Token

The current `publish_to_x()` uses `Authorization: Bearer {access_token}`. For OAuth 2.0 user context (posting on behalf of user), this is the correct pattern when using OAuth 2.0 PKCE flow with `tweet.write` scope. The X API v2 `/2/tweets` endpoint with user context requires an OAuth 2.0 user token, NOT an App-only Bearer token. The current implementation is correct IF the token from the PKCE flow is used.

**Verify**: The `TWITTER_SCOPES` in platforms.py includes `tweet.write users.read offline.access` which is correct for v2 user-context posting.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Token encryption | Custom cipher | Fernet from `cryptography` package | Already implemented in platforms.py |
| OAuth state CSRF | Custom session | MongoDB `oauth_states` collection | Already implemented |
| PKCE challenge | Custom crypto | `hashlib.sha256` + `base64.urlsafe_b64encode` | Already implemented in `_generate_pkce()` |
| Media Container polling | Custom retry loop | Existing `asyncio.sleep` loop in `publish_to_instagram` | Already implemented (30 attempts, 2s interval) |
| Platform API HTTP calls | Raw `requests` | `httpx.AsyncClient` | Async, already used throughout |
| Analytics aggregation | Custom math | `services/persona_refinement.py` functions | `calculate_performance_intelligence()` already exists |

---

## Common Pitfalls

### Pitfall 1: Instagram Requires Business/Creator Account

**What goes wrong:** Regular Instagram personal accounts cannot use the Media Container API. The OAuth callback in `platforms.py` fetches Facebook Pages and looks for a linked Instagram Business Account. If the user has no Business/Creator account linked to a Facebook Page, `instagram_account_id` will be `None`, and all publish calls will return an error.

**Why it happens:** Meta restricts the Content Publishing API to Instagram Business and Creator accounts only. Personal accounts have no access.

**How to avoid:** The current callback already warns with "Instagram business account not found. Please reconnect." Ensure the frontend Connections page surfaces this error state clearly.

**Warning signs:** `instagram_account_id` is `None` in the platform_tokens doc after successful OAuth.

### Pitfall 2: X OAuth 2.0 Bearer Token vs User Token Confusion

**What goes wrong:** X API v2 has two auth modes: App-only Bearer Token (read-only, for searching) and OAuth 2.0 User Context Token (for posting). The PKCE flow produces a User Context Token. Using an App-only Bearer Token for `POST /2/tweets` returns 403.

**Why it happens:** The token from the PKCE OAuth callback IS a user context token, but `TWITTER_API_KEY` is also used as the client_id. If someone accidentally uses the API key as a Bearer token, it will fail.

**How to avoid:** The current publisher uses the stored access_token from DB (which is the user context token from PKCE). Do not substitute with `TWITTER_API_KEY`.

### Pitfall 3: LinkedIn Post URL Construction

**What goes wrong:** LinkedIn doesn't return the post URL in the API response. The current code constructs it as `https://www.linkedin.com/feed/update/{post_id}/` using the `x-restli-id` header. This format is correct but the header value must be the full URN (e.g., `urn:li:share:123456`), not a bare numeric ID.

**Why it happens:** The `x-restli-id` header contains the full URN. URL construction with the URN is correct per LinkedIn documentation.

**Warning signs:** Post URL returns 404 — check that `post_id` contains the full URN string.

### Pitfall 4: Scheduled Post Does Not Store post_id for Analytics

**What goes wrong:** `_run_scheduled_posts_inner` calls `_publish_to_platform()` which returns `bool`. The post_id, post_url, and tweet_ids from the real publisher are discarded. When `poll_post_metrics_24h` fires 24 hours later, it reads `job.publish_results` and finds nothing — returns False silently. Real metrics never appear.

**Why it happens:** `_publish_to_platform()` was written to return `bool` for simplicity. The full result dict from `publisher.publish_to_platform()` is available but not surfaced.

**How to avoid:** Change `_publish_to_platform()` to return the full result dict, and update the caller to write `publish_results` to both the `scheduled_posts` document and the linked `content_jobs` document.

### Pitfall 5: Fernet Key Length Validation

**What goes wrong:** `_get_cipher()` in platforms.py checks `if len(key) != 44`. A Fernet key is exactly 44 base64url characters. If `ENCRYPTION_KEY` is set to an arbitrary string (not a proper Fernet key), the code falls back to SHA-256 hashing — this changes the effective key silently. Old tokens encrypted with the old key cannot be decrypted with the hashed version.

**Why it happens:** The code has a silent fallback: `if len(key) != 44: key = base64.urlsafe_b64encode(hashlib.sha256(key).digest())`.

**How to avoid:** Always generate ENCRYPTION_KEY with `python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'`. The key will be exactly 44 chars. Do not set a shorter/longer arbitrary string.

### Pitfall 6: Instagram Token Refresh Not Supported

**What goes wrong:** Instagram long-lived tokens (60 days) do NOT have a `refresh_token`. The `_refresh_token()` function in platforms.py has no Instagram branch — it returns `None` for Instagram. When the token expires, the user must reconnect manually.

**Why it happens:** Meta's token design for Instagram. Long-lived tokens can be refreshed by calling a specific Graph API endpoint with the current valid token, but the code does not implement this.

**How to avoid:** For PUBL-04, document that Instagram auto-refresh works only when the token is still valid (by calling the Graph API exchange endpoint proactively). The proactive refresh for Instagram should call `https://graph.facebook.com/v18.0/oauth/access_token?grant_type=fb_exchange_token` with the existing token BEFORE it expires. Add a branch in `_refresh_token()` for platform == "instagram".

---

## Code Examples

### Fixing _publish_to_platform to return full result (content_tasks.py)

```python
# Source: existing agents/publisher.py return shape
async def _publish_to_platform(
    platform: str,
    content: str,
    token: dict,
    media_assets: Optional[List[Dict[str, Any]]] = None,
) -> dict:
    """Returns full publish result dict including post_id, post_url."""
    # ... (existing token expiry check) ...
    access_token = _decrypt_token_if_needed(token)  # decrypt before passing
    from agents.publisher import publish_to_platform
    result = await publish_to_platform(
        platform=platform,
        content=content,
        access_token=access_token,
        user_id=user_id,
        media_assets=media_assets,
    )
    return result if isinstance(result, dict) else {"success": bool(result)}
```

### Proactive Token Refresh Pattern (platforms.py)

```python
async def get_platform_token(user_id: str, platform: str) -> Optional[str]:
    token_doc = await db.platform_tokens.find_one({"user_id": user_id, "platform": platform})
    if not token_doc:
        return None

    expires_at = token_doc.get("expires_at")
    if expires_at:
        now = datetime.now(timezone.utc)
        time_until_expiry = expires_at - now
        # Proactive refresh: try 24h before expiry
        if time_until_expiry < timedelta(hours=24):
            refresh_token = token_doc.get("refresh_token")
            if refresh_token:
                new_token = await _refresh_token(user_id, platform, _decrypt_token(refresh_token))
                if new_token:
                    return new_token
            # If already expired, return None
            if expires_at < now:
                return None

    return _decrypt_token(token_doc["access_token"])
```

### Instagram Token Refresh (platforms.py _refresh_token)

```python
elif platform == "instagram":
    # Instagram long-lived token renewal — no refresh_token, use existing token
    response = await client.get(
        "https://graph.facebook.com/v18.0/oauth/access_token",
        params={
            "grant_type": "fb_exchange_token",
            "client_id": META_APP_ID,
            "client_secret": META_APP_SECRET,
            "fb_exchange_token": refresh_token,  # Current access token passed as refresh_token
        },
        timeout=30.0
    )
```

### Sentry Capture on Publish Failure

```python
# In _run_scheduled_posts_inner failure branch:
if not success:
    if settings.app.sentry_dsn:
        import sentry_sdk
        sentry_sdk.capture_message(
            f"Scheduled post failed to publish",
            level="error",
            extras={
                "schedule_id": post.get("schedule_id"),
                "platform": platform,
                "user_id": user_id,
            }
        )
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| LinkedIn REST API v1 | LinkedIn UGC API v2 + OpenID Connect userinfo | 2023 | `sub` field for person URN |
| Twitter OAuth 1.0a | X OAuth 2.0 PKCE | 2022 | No consumer key signing required |
| Instagram Basic Display API | Meta Graph API + Content Publishing API | 2020 | Business accounts only |
| Instagram short-lived tokens | Long-lived tokens (60 days via fb_exchange_token) | Standard | No refresh_token; must renew proactively |

**Deprecated/outdated:**
- LinkedIn `r_liteprofile` and `r_emailaddress` scopes: deprecated — replaced by `openid profile email` (OIDC). The current code uses the new scopes. HIGH confidence.
- X v1.1 API: sunset. Current code uses v2 at `api.twitter.com/2/tweets`. Correct.
- Meta Graph API v18.0: Used in current code. Latest stable is v21.0 (as of early 2026). v18.0 still works but consider upgrading the version string in URLs if issues arise. LOW-MEDIUM confidence on exact current version.

---

## Open Questions

1. **Instagram Graph API version**
   - What we know: Code uses `v18.0`. Meta Graph API has quarterly version updates.
   - What's unclear: Whether v18.0 is still supported as of April 2026.
   - Recommendation: Test the OAuth callback and Media Container endpoints. If 400/404, bump to `v20.0` or `v21.0` in `routes/platforms.py` and `agents/publisher.py`.

2. **X API Rate Limits with OAuth 2.0**
   - What we know: X v2 has per-user tweet limits on free/basic tier (500 tweets/month write limit on free tier; Basic tier allows more).
   - What's unclear: Project's X developer account tier.
   - Recommendation: Document in the plan that thread publishing consumes multiple tweet quota slots. If rate limited, the publisher receives HTTP 429 — already handled with logging.

3. **LinkedIn Refresh Token Availability**
   - What we know: LinkedIn standard member tokens (for w_member_social) do NOT include refresh tokens unless the app has the Partner Program refresh token feature enabled.
   - What's unclear: Whether `refresh_token` will actually be present in the token exchange response for this app.
   - Recommendation: The code already handles `refresh_token` being `None`. For the 24h proactive check, if no refresh_token, skip to checking expiry. Log a warning.

4. **Celery Beat Task Name Discrepancy**
   - What we know: `celeryconfig.py` schedules task `tasks.scheduled_tasks.process_scheduled_posts` but `content_tasks.py` defines `@shared_task(name='tasks.content_tasks.process_scheduled_posts')`. These are different names.
   - What's unclear: Whether there is a `tasks/scheduled_tasks.py` module that re-exports these tasks.
   - Recommendation: Verify `backend/tasks/` directory for `scheduled_tasks.py`. If missing, the beat schedule will fail silently. Check as part of Wave 0.

5. **content_tasks._publish_to_platform token decryption**
   - What we know: `_run_scheduled_posts_inner` reads the token doc and passes it directly to `_publish_to_platform`. Inside `_publish_to_platform`, `access_token = token.get("access_token", "")` — this is the ENCRYPTED value from the DB, not decrypted.
   - What's unclear: Whether the call to `publish_to_platform()` in publisher.py correctly uses this encrypted value (it won't — it will send garbage to the platform API).
   - Recommendation: HIGH PRIORITY gap. The scheduled post flow must decrypt the token before passing it. The `get_platform_token()` helper does decryption — should be called instead of reading raw token doc.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|-------------|-----------|---------|----------|
| Python / FastAPI | Backend runtime | Available | Python 3.11 | — |
| MongoDB | Token and job storage | Available | Via Motor | — |
| Redis + Celery | Scheduled publishing | Required for beat | Not verified locally | n8n bridge as alternative |
| LinkedIn OAuth credentials | PUBL-01 | Must be in .env | — | Cannot test without real app |
| X/Twitter OAuth credentials | PUBL-02 | Must be in .env | — | Cannot test without real app |
| Meta OAuth credentials | PUBL-03 | Must be in .env | — | Cannot test without real app |
| ENCRYPTION_KEY (Fernet) | PUBL-06 | Required in production | — | Dev uses ephemeral key (acceptable) |
| SENTRY_DSN | PUBL-05 failure events | Optional | — | Error logged to stdout if not set |

**Missing dependencies with no fallback:**
- Real platform OAuth credentials (LINKEDIN_CLIENT_ID, TWITTER_API_KEY, META_APP_ID) — cannot do end-to-end OAuth test without them. Unit tests can mock httpx calls.

**Missing dependencies with fallback:**
- Redis/Celery: If not running locally, Celery Beat schedule won't fire. Use the `POST /api/n8n/execute/process-scheduled-posts` endpoint as a manual trigger alternative. The n8n_bridge already exists for this purpose.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.0.0 + pytest-asyncio 0.23.0 |
| Config file | `backend/pytest.ini` |
| Quick run command | `cd backend && pytest tests/test_publishing.py tests/test_platform_oauth.py -x -q` |
| Full suite command | `cd backend && pytest -x -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PUBL-01 | LinkedIn OAuth initiate + callback + UGC publish | unit | `pytest tests/test_platform_oauth.py::TestPlatformStatus -x` | Yes |
| PUBL-01 | LinkedIn publish sends correct UGC API request | unit | `pytest tests/test_publishing.py::TestPublishLinkedIn -x` | Yes |
| PUBL-02 | X OAuth PKCE initiate + callback + tweet | unit | `pytest tests/test_platform_oauth.py -x -k "x"` | Yes |
| PUBL-02 | X thread parsing and sequential tweet posting | unit | `pytest tests/test_publishing.py::TestPublishX -x` | Partial |
| PUBL-03 | Instagram OAuth + long-lived token + Media Container | unit | `pytest tests/test_publishing.py::TestPublishInstagram -x` | Partial |
| PUBL-04 | Proactive 24h token refresh before expiry | unit | `pytest tests/test_platform_oauth.py -x -k "refresh"` | Partial |
| PUBL-04 | Instagram token renewal (no refresh_token, use exchange) | unit | New test required | No — Wave 0 gap |
| PUBL-05 | Scheduled post stores post_id and post_url in content_job | unit | `pytest tests/test_publishing.py -x -k "scheduled"` | Partial |
| PUBL-05 | Failed publish sets status=failed + retry UI shows | unit | `pytest tests/test_publishing.py -x -k "failed"` | Partial |
| PUBL-06 | Fernet encryption round-trip verified | unit | `pytest tests/test_platform_oauth.py -x -k "encrypt"` | Partial |
| PUBL-07 | Real metrics fetched after publish and stored on job | unit | `pytest tests/test_analytics_social.py -x` | Yes |

### Sampling Rate

- **Per task commit:** `cd backend && pytest tests/test_publishing.py tests/test_platform_oauth.py -x -q`
- **Per wave merge:** `cd backend && pytest -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/test_publishing.py` — needs new test case: scheduled post stores `publish_results` with `post_id`/`post_url`
- [ ] `tests/test_publishing.py` — needs new test case: proactive 24h refresh fires when `expires_at < now + 24h`
- [ ] `tests/test_publishing.py` — needs new test case: Instagram token renewal via `fb_exchange_token` in `_refresh_token()`
- [ ] `tests/test_publishing.py` — needs new test case: Sentry `capture_message` called on scheduled post failure
- [ ] Verify `backend/tasks/scheduled_tasks.py` exists (Celery beat references it, not `content_tasks`)

---

## Sources

### Primary (HIGH confidence)

- `backend/agents/publisher.py` — Publisher implementations for all three platforms (read directly)
- `backend/routes/platforms.py` — OAuth flows, token encryption, get_platform_token (read directly)
- `backend/services/social_analytics.py` — Metrics fetch functions and update_post_performance (read directly)
- `backend/tasks/content_tasks.py` — Scheduled post processing, poll_post_metrics tasks (read directly)
- `backend/routes/dashboard.py:600-662` — POST /publish/{job_id} (read directly)
- `backend/config.py` — PlatformOAuthConfig dataclass (read directly)
- `backend/celeryconfig.py` — Beat schedule configuration (read directly)
- `frontend/src/pages/Dashboard/Connections.jsx` — OAuth connect UI (read directly)
- `frontend/src/pages/Dashboard/ContentStudio/ContentOutput.jsx:923-1082` — PublishPanel (read directly)

### Secondary (MEDIUM confidence)

- CLAUDE.md — Project constraints, directory structure, coding conventions

### Tertiary (LOW confidence)

- LinkedIn UGC API version stability: assumed still active at `v2/ugcPosts` (consistent with LinkedIn developer docs as of 2025)
- Meta Graph API version `v18.0`: known to be functional but may be dated; current stable is likely v20.0+

---

## Metadata

**Confidence breakdown:**
- What's implemented: HIGH — read directly from source files
- Standard Stack: HIGH — all dependencies already in requirements.txt
- Architecture gaps: HIGH — confirmed by code audit (missing publish_results write, no proactive refresh, missing Sentry events, encrypted token passed raw to platform)
- Pitfalls: HIGH — derived from actual code paths read
- Instagram Graph API version currency: LOW — version string v18.0 may be outdated

**Research date:** 2026-04-12
**Valid until:** 2026-05-12 (platform OAuth APIs change infrequently; Fernet encryption is stable)
