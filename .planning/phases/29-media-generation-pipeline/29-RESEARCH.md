# Phase 29: Media Generation Pipeline - Research

**Researched:** 2026-04-12
**Domain:** Multi-provider media generation (images, video, voice, Remotion rendering, R2 storage)
**Confidence:** HIGH

---

## Summary

Phase 29 activates an already-written but largely untested media generation pipeline. The backend agents, service layer, Celery tasks, and Remotion service are all present. The primary work is: (1) fixing a critical missing class bug in `media_tasks.py`, (2) ensuring the R2 presigned upload flow works end-to-end without CORS errors, (3) wiring the voice narration result into R2 storage (currently returned as a `data:` URI), (4) hooking the Remotion carousel render into the generate-carousel route, and (5) adding Sentry error capture + retry UI to meet the failure-handling success criterion.

The frontend `MediaPanel` component in `ContentOutput.jsx` already calls `/api/content/generate-image` and `/api/content/narrate`, and displays images and an audio player — but the API calls handle 202 async responses incorrectly (they check `data.generated` which will be absent on a queued response). The `MediaUploader` component uses `POST /api/uploads/media` (not the R2 presigned flow described in the success criteria). These two patterns need to be reconciled and verified.

**Primary recommendation:** Fix the `CreativeProvidersService` missing-class bug first, then verify each media endpoint works with real or mocked API keys, then add retry UI and Sentry capture. The Remotion carousel (MDIA-02/MDIA-05) is the only genuinely unimplemented path; everything else is wiring bugs.

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| MDIA-01 | Auto-generate featured image for every post (DALL-E/FAL.ai) | `generate_image` in `agents/designer.py` + `/api/content/generate-image` route exist; `CreativeProvidersService` bug in Celery task must be fixed first |
| MDIA-02 | Generate LinkedIn carousel slides via Remotion | `generate_carousel` in `agents/designer.py` generates per-slide images; Remotion `ImageCarousel` composition exists but is NOT called from the carousel route — orchestrator path must be wired |
| MDIA-03 | Generate short-form video from script (Runway/Luma) | `generate_video` in `agents/video.py` + `/api/content/generate-video` route exist; provider API keys required in Railway env |
| MDIA-04 | Generate voice narration from post text (ElevenLabs/OpenAI TTS) | `generate_voice_narration` in `agents/voice.py` + `/api/content/narrate` route exist; result is currently a `data:` URI, needs R2 upload for stable URL |
| MDIA-05 | Remotion renders compositions into downloadable video files | `remotion-service/server.ts` fully implemented; `_call_remotion()` in `media_orchestrator.py` fully implemented; needs `REMOTION_SERVICE_URL` env var and build/deploy of the Remotion sidecar |
| MDIA-06 | Generated media attached to content jobs and downloadable | `_auto_attach_to_job` in `designer.py` pushes to `content_jobs.media_assets`; `media_tasks.py` also inserts to `db.media_assets`; needs verification both paths fire correctly |
| MDIA-07 | Media display works in content preview (images, videos, audio players) | `MediaPanel` in `ContentOutput.jsx` renders image, audio player; needs 202/async polling support + video display |
| MDIA-08 | R2 upload flow works end-to-end (presigned URL, browser upload, confirm) | `POST /api/media/upload-url` + `POST /api/media/confirm` exist; `MediaUploader.jsx` uses `POST /api/uploads/media` (multipart) — not the R2 presigned flow; success criteria requires presigned URL path verified |
</phase_requirements>

---

## Project Constraints (from CLAUDE.md)

- All settings via `backend/config.py` dataclasses. Never use `os.environ.get()` directly in routes/agents/services.
- Always `from database import db` with Motor async. Never synchronous PyMongo.
- LLM model: `claude-sonnet-4-20250514` (for any LLM calls needed in this phase)
- After any change to `backend/agents/`, verify full content pipeline still flows.
- All new Python packages must be added to `backend/requirements.txt`.
- No hardcoded API keys or secrets.
- Branch from `dev`, PR targets `dev`. Branch naming: `feat/`, `fix/`, `infra/`.
- Config pattern: `from config import settings` always.
- Sentry DSN configured conditionally at startup in `server.py` — `sentry_sdk.capture_exception()` is available when DSN is set.
- Python file naming: `snake_case.py`. React components: `PascalCase.jsx`. Utilities: `camelCase.js`.
- Frontend uses `apiFetch()` from `@/lib/api` — never raw `fetch()`.
- Frontend auth: cookie-based (`session_token` httpOnly cookie). CSRF token injected via `X-CSRF-Token` header.
- Design system: lime (`#D4FF00`) for primary actions, violet (`#7000FF`) for secondary/premium features, surface/surface-2 cards, Clash Display for headings.

---

## Standard Stack

### Core (already present in codebase)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| fal-client | 0.10.0 | FAL.ai image generation (Flux Pro 1.1) | Fastest image inference, already installed |
| elevenlabs | 1.50.0 | ElevenLabs TTS via async SDK | Best voice quality, already installed |
| lumaai | 1.0.0 | Luma Dream Machine video API | Official SDK, already installed |
| boto3 | 1.34.129+ | Cloudflare R2 (S3-compatible) uploads | Already wired in `media_storage.py` |
| httpx | 0.28.1 | Async HTTP for all provider polling | Already used throughout agents |
| sentry-sdk | 2.0.0+ | Error tracking | Already configured in `server.py` |
| remotion | 4.0.443 | Remotion render service (sidecar Node.js) | Already built, see `remotion-service/` |
| celery | 5.3.0 | Async media task queue | Already wired in `media_tasks.py` |

### Provider API Key Requirements (Railway env)

| Provider | Env Var | Use | Priority |
|----------|---------|-----|----------|
| FAL.ai | `FAL_KEY` | Image generation (MDIA-01 primary) | HIGH — fastest fallback chain start |
| ElevenLabs | `ELEVENLABS_API_KEY` | Voice narration (MDIA-04 primary) | HIGH |
| OpenAI | `OPENAI_API_KEY` | Image fallback (gpt-image-1) + TTS fallback | MEDIUM |
| Luma | `LUMA_API_KEY` | Video generation (MDIA-03 primary) | MEDIUM — if Runway unavailable |
| Runway | `RUNWAY_API_KEY` | Video generation (MDIA-03 preferred) | MEDIUM |
| Remotion | `REMOTION_SERVICE_URL` | Remotion sidecar base URL | HIGH — required for MDIA-02/05 |

---

## Architecture Patterns

### Existing Flow (what is already built)

```
Content Job (db.content_jobs)
   │
   ├─ POST /api/content/generate-image ──► designer.generate_image()
   │     ├─ Sync path: deduct credits → call provider → return result
   │     └─ Async path (Redis available): Celery task → CreativeProvidersService [BUG: class missing]
   │
   ├─ POST /api/content/generate-carousel ──► designer.generate_carousel()
   │     └─ Sync only: generates per-slide images, returns slides list
   │         └─ MISSING: no Remotion call for rendered carousel PDF/video
   │
   ├─ POST /api/content/narrate ──► voice.generate_voice_narration()
   │     ├─ Sync path: deduct credits → call ElevenLabs → return data: URI
   │     └─ MISSING: no R2 upload for stable URL; audio_url stored as data: URI in DB
   │
   ├─ POST /api/content/generate-video ──► video.generate_video()
   │     └─ Sync + Celery path: proper R2 handling in pipeline task
   │
   └─ POST /api/media/orchestrate ──► Celery orchestrate_media_job task
         └─ MediaOrchestrator.orchestrate() ──► per-media-type handlers
               ├─ _handle_static_image: image → R2 → Remotion StaticImageCard
               ├─ _handle_quote_card: abstract bg → R2 → Remotion (layout="quote")
               └─ 6 more handlers registered via @register_media_handler
```

### R2 Presigned Upload Flow (MDIA-08)

```
Browser → POST /api/media/upload-url  →  { upload_url, storage_key, expires_in }
Browser → PUT <upload_url> (direct to R2, no backend)
Browser → POST /api/media/confirm  →  { media_id, public_url, asset }
```

The `MediaUploader.jsx` component currently uses `POST /api/uploads/media` (multipart through the backend) — not this presigned flow. MDIA-08 success criterion verifies the presigned URL path. The R2 presigned URL route is at `/api/media/upload-url`, not `/api/uploads/media`.

### Remotion Sidecar API

```
POST /render → { render_id }
GET  /render/{render_id}/status → { status: "queued"|"rendering"|"done"|"failed", url?, error? }
```

- `StaticImageCard`, `Infographic` render as `still` (PNG)
- `ImageCarousel`, `TalkingHeadOverlay`, `ShortFormVideo` render as `video` (MP4)
- First render takes ~30s extra for Webpack bundle warm-up
- Render timeout configured at 300s in `_call_remotion()`
- Remotion sidecar uploads results directly to R2 via `uploadToR2()` in `lib/r2-upload.ts`

---

## Critical Bugs Found (must fix before success criteria are reachable)

### Bug 1: `CreativeProvidersService` class does not exist (BLOCKER for Celery async path)

**Location:** `backend/tasks/media_tasks.py` lines 52, 73, 152, 167, 236, 251, 317, 332
**Problem:** `from services.creative_providers import CreativeProvidersService` — this class is NOT defined in `creative_providers.py`. The file only exports module-level functions (`get_best_available_provider`, etc.). When Redis is available, the Celery tasks for image/voice/video generation will fail with `ImportError` immediately.
**Fix:** Either (a) create the `CreativeProvidersService` class wrapping existing agent functions, or (b) rewrite the four Celery tasks (`generate_image`, `generate_video`, `generate_voice`, `generate_carousel`) to call the agent functions directly (same pattern as `generate_video_for_job` which works correctly).
**Recommendation:** Option (b) — align all four Celery tasks with `generate_video_for_job` pattern. Avoids adding an unnecessary class abstraction.

### Bug 2: Voice narration result stored as `data:` URI (MDIA-04 / MDIA-06 partial)

**Location:** `backend/routes/content.py:narrate_content()` and `backend/agents/voice.py`
**Problem:** `generate_voice_narration()` returns `audio_url` as a `data:audio/mpeg;base64,...` URI. The route stores this in `content_jobs.audio_url`. The frontend `<audio>` tag can play a `data:` URI, but it is:
- Not a stable URL (criterion says "stored in R2 with stable URL")
- Cannot be linked from the media_assets collection as a public URL
- Will bloat MongoDB documents (audio files are large)
**Fix:** After generating audio bytes, upload to R2 using `upload_bytes_to_r2()` from `media_storage.py`, then store the R2 public URL as `audio_url`.

### Bug 3: 202 async response not handled in frontend MediaPanel (MDIA-07)

**Location:** `frontend/src/pages/Dashboard/ContentStudio/ContentOutput.jsx:MediaPanel`
**Problem:** When Redis is available, `/api/content/generate-image` returns HTTP 202 with `{task_id, status: "queued", job_id}`. The frontend checks `data.generated && data.image_url` which is absent on a 202 response — so the image never displays even when generation succeeds.
**Fix:** Check `response.status === 202` and begin polling `GET /api/content/jobs/{job_id}/task-status` until completed, then re-fetch the job to get `media_assets[0].image_url`.

### Bug 4: Carousel route does not call Remotion (MDIA-02 / MDIA-05 incomplete)

**Location:** `backend/routes/content.py:generate_carousel()`
**Problem:** `/api/content/generate-carousel` calls `designer.generate_carousel()` which returns an array of base64 slide images. It does NOT call the Remotion `ImageCarousel` composition to render a proper video/PDF carousel. The success criterion requires "a Remotion-rendered slide deck (3+ slides) with download link."
**Fix:** After generating slide images, stage them to R2, then call `_call_remotion("ImageCarousel", {...})` from `media_orchestrator.py`, return the rendered carousel URL in the response.

### Bug 5: Sentry not capturing media generation failures (MDIA success criteria #5)

**Location:** All media generation routes in `content.py`
**Problem:** The success criterion requires "Failed media generation logs error to Sentry." The `except` blocks only call `logger.error()`. Sentry SDK is configured at startup but `sentry_sdk.capture_exception(exc)` is not called in any media generation error handler.
**Fix:** Add `sentry_sdk.capture_exception(exc)` in each `except` block, guarded by `if settings.app.sentry_dsn:`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Direct file upload progress tracking | Custom XHR wrapper | Already exists in `MediaUploader.jsx` | Works, has progress bar |
| Image provider retry logic | Custom retry loop | Existing fallback chain in `designer.generate_image()` | Already iterates `["openai", "fal", "stability", "replicate"]` |
| R2 byte upload | Custom S3 client | `upload_bytes_to_r2()` in `media_storage.py` | Already handles boto3 client, error wrapping |
| Remotion polling | Custom async polling | `_call_remotion()` in `media_orchestrator.py` | 300s timeout, exponential backoff |
| Credit deduction/refund | Custom ledger | `deduct_credits()` + `add_credits()` from `services.credits` | Already wired in Phase 26 |
| Audio format conversion | ffmpeg | ElevenLabs returns `mp3_44100_128` directly | Browser `<audio>` plays MP3 natively |

---

## Common Pitfalls

### Pitfall 1: `data:` URI vs stable R2 URL

**What goes wrong:** Voice narration works in the UI (audio plays) but fails the success criterion "stored in R2 with stable URL." Frontend audio players stop working if the MongoDB document is cleared (data: URIs don't persist well). Media asset links from `/api/media/assets` show nothing because `url` is a `data:` string.
**Root cause:** `generate_voice_narration()` returns bytes as base64-encoded data URI instead of uploading to storage.
**How to avoid:** Upload bytes to R2 immediately using `upload_bytes_to_r2(storage_key, audio_bytes, "audio/mpeg")` before returning from the route handler.
**Warning signs:** `audio_url` in DB starts with `data:audio/mpeg;base64,`.

### Pitfall 2: Remotion bundle warm-up causes first-request timeout

**What goes wrong:** First carousel render takes 30-60s extra for Webpack bundling. If `_call_remotion()` is called synchronously in a FastAPI background task (not Celery), the FastAPI worker stays occupied.
**Root cause:** Remotion pre-warms bundle on startup but `getBundlePath()` can still take time under cold-start conditions.
**How to avoid:** Carousel generation must go through Celery (not FastAPI `BackgroundTasks`) when Redis is available. The `orchestrate_media_job` Celery task already handles this correctly.
**Warning signs:** Carousel endpoint hangs for >30s on first call.

### Pitfall 3: CORS on direct R2 PUT (MDIA-08)

**What goes wrong:** Browser PUT to R2 presigned URL fails with CORS error because R2 bucket does not have CORS policy allowing `PUT` from frontend origin.
**Root cause:** R2 bucket CORS must be configured via Cloudflare dashboard or R2 API before presigned URL flow works.
**How to avoid:** Configure R2 bucket CORS policy to allow `PUT` from `https://thookai.vercel.app` and `http://localhost:3000`. This is a one-time infrastructure task.
**Warning signs:** Browser console shows "CORS policy: No 'Access-Control-Allow-Origin' header" on the R2 URL.

### Pitfall 4: FAL_KEY vs FAL_API_KEY naming mismatch

**What goes wrong:** FAL.ai image generation silently falls back to mock because key lookup fails.
**Root cause:** In `creative_providers.py`, both `"FAL_KEY"` and `"FAL_API_KEY"` map to `settings.video.fal_key`. But `VideoProviderConfig` has `fal_key` reading from `FAL_KEY` env var. Railway must set `FAL_KEY`, not `FAL_API_KEY`.
**How to avoid:** Verify Railway env uses `FAL_KEY`. Check `config.py` `VideoProviderConfig.fal_key` field default factory.
**Warning signs:** `get_best_available_provider("image")` returns `None` even when FAL key is set in Railway.

### Pitfall 5: `_auto_attach_to_job` stores image in job's `media_assets` array; Celery task also inserts into `db.media_assets` collection

**What goes wrong:** Duplicate entries — the `media_assets` array inside `content_jobs` document (BSON array) and the standalone `db.media_assets` collection both get records. The frontend `MediaPanel` reads from `job.media_assets[0].image_url` but the standalone collection is returned by `/api/media/assets`. These are two different storage paths.
**Root cause:** `_auto_attach_to_job()` in `designer.py` pushes to `content_jobs.media_assets`, while `media_tasks.py` inserts to `db.media_assets` collection with a different schema (has `asset_id`, not `media_id`).
**How to avoid:** Ensure both writes happen and that the frontend reads from the job's inline `media_assets` array for immediate display, and `/api/media/assets` for the library view.

### Pitfall 6: Runway API endpoint mismatch

**What goes wrong:** Runway video generation fails with 404 because the API URL in `video.py` points to `/v1/image_to_video` (for image-to-video) when doing text-to-video generation.
**Root cause:** `_generate_runway()` uses conditional URL: `"/v1/image_to_video" if model != "gen-3-alpha"`. For text-to-video with `gen-3-alpha-turbo`, the correct URL is `/v1/text_to_video`.
**How to avoid:** Verify Runway API endpoint against current RunwayML docs before testing. The Runway API has changed significantly in 2024-2025.

---

## Architecture Patterns (Implementation)

### Pattern 1: Sync + Celery async fallback (used throughout media routes)

```python
# Source: backend/routes/content.py generate_image() (existing pattern)
if is_redis_configured():
    try:
        task = celery_generate_image.apply_async(args=[...])
        await db.content_jobs.update_one({"job_id": job_id}, {"$set": {"image_status": "queued"}})
        return JSONResponse(status_code=202, content={"task_id": task.id, "status": "queued"})
    except Exception:
        logger.warning("Celery dispatch failed, falling back to sync")
# Sync fallback: deduct credits → call agent → return result
```

### Pattern 2: R2 bytes upload for generated media (to implement for voice)

```python
# Source: backend/services/media_storage.py upload_bytes_to_r2() (existing function)
from services.media_storage import upload_bytes_to_r2
import base64, uuid

audio_bytes = base64.b64decode(result["audio_base64"])
storage_key = f"{user_id}/audio/{uuid.uuid4()}.mp3"
public_url = upload_bytes_to_r2(storage_key, audio_bytes, "audio/mpeg")
# Then store public_url in content_jobs.audio_url
```

### Pattern 3: Credit deduction + refund on failure (required for all media endpoints)

```python
# Source: backend/routes/content.py (existing pattern in all media endpoints)
from services.credits import deduct_credits, add_credits, CreditOperation
deduct_result = await deduct_credits(user_id, CreditOperation.IMAGE_GENERATE)
if not deduct_result.get("success"):
    raise HTTPException(status_code=402, detail="Insufficient credits")
try:
    result = await some_operation()
except Exception as exc:
    await add_credits(user_id, CreditOperation.IMAGE_GENERATE.value, source="failure_refund", ...)
    raise HTTPException(status_code=500, detail="Operation failed. Credits refunded.")
```

### Pattern 4: Sentry capture (to add to all media failure paths)

```python
# Source: backend/server.py (Sentry configured at startup)
import sentry_sdk
try:
    result = await generate_something()
except Exception as exc:
    if settings.app.sentry_dsn:
        sentry_sdk.capture_exception(exc)
    await add_credits(...)  # refund
    raise HTTPException(status_code=500, detail="Generation failed. Credits refunded.")
```

### Pattern 5: Frontend polling for async 202 response (to implement in MediaPanel)

```javascript
// Pattern to add to ContentOutput.jsx MediaPanel
const response = await apiFetch('/api/content/generate-image', { method: 'POST', body: JSON.stringify({...}) });
if (response.status === 202) {
  const { job_id } = await response.json();
  // Poll job status
  const poll = setInterval(async () => {
    const jobResp = await apiFetch(`/api/content/job/${job_id}`);
    const job = await jobResp.json();
    if (job.media_assets?.length > 0) {
      setGeneratedImage(job.media_assets[0].image_url);
      clearInterval(poll);
    }
  }, 3000);
} else {
  const data = await response.json();
  if (data.generated) setGeneratedImage(data.image_url);
}
```

---

## Remotion Compositions Reference

| Composition ID | Dimensions | FPS | Render Type | Props |
|----------------|-----------|-----|-------------|-------|
| `StaticImageCard` | 1200x1200 | 30 | still (PNG) | imageUrl, text, brandColor, fontFamily, platform, layout |
| `ImageCarousel` | 1080x1080 | 30 | video (MP4) | slides[], brandColor, fontFamily |
| `Infographic` | 1080x1350 | 30 | still (PNG) | title, dataPoints[], brandColor, style |
| `TalkingHeadOverlay` | 1080x1920 | 30 | video (MP4) | videoUrl, overlayText, lowerThirdName, lowerThirdTitle, brandColor |
| `ShortFormVideo` | 1080x1920 | 30 | video (MP4) | segments[], audioUrl, musicUrl, brandColor, durationInFrames |

The Remotion sidecar service automatically infers still vs video from composition ID (see `inferRenderType()` in `server.ts`). `StaticImageCard` and `Infographic` → still; all others → video.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.11+ | Backend | Present locally (3.13.5) | 3.13.5 | — |
| Node.js 18+ | Remotion sidecar | Present | 20.15.0 | — |
| pytest | Backend tests | Present | Latest | — |
| Redis | Celery async dispatch | Not verified locally | Unknown | Sync fallback path exists in all media routes |
| R2 storage | Media persistence | Not configured locally | — | /tmp fallback in `_stage_asset_to_r2()` |
| FAL_KEY | Image generation | Not configured locally | — | Mock response `generated=False` |
| ELEVENLABS_API_KEY | Voice narration | Not configured locally | — | Mock response `generated=False` |
| LUMA_API_KEY | Video generation | Not configured locally | — | `generated=False` error response |
| REMOTION_SERVICE_URL | Remotion renders | Not configured (defaults to localhost:3001) | — | Remotion calls fail with connection refused |

**Missing dependencies with no fallback:**
- R2 CORS policy (Cloudflare dashboard setting — must be configured for MDIA-08 to work in browser)
- Provider API keys in Railway env (FAL_KEY, ELEVENLABS_API_KEY at minimum for MDIA-01, MDIA-04)

**Missing dependencies with fallback:**
- Redis (all media routes fall back to sync execution)
- R2 credentials (media_orchestrator falls back to /tmp; media_storage returns 503)

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.0.0 + pytest-asyncio 0.23.0 |
| Config file | `backend/pytest.ini` (`pythonpath=.`) |
| Quick run command | `cd backend && pytest tests/test_media_generation.py -x -q` |
| Full suite command | `cd backend && pytest tests/ -x -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| MDIA-01 | Image generation returns `generated=True` + `image_url` | unit (mocked) | `pytest tests/test_media_generation.py -k "image" -x` | YES (`test_media_generation.py`) |
| MDIA-02 | Carousel route calls Remotion and returns download URL | unit (mocked Remotion) | `pytest tests/test_media_orchestrator.py -k "carousel" -x` | YES (need carousel-specific test added) |
| MDIA-03 | Video generation routes to configured provider | unit (mocked) | `pytest tests/test_media_generation.py -k "video" -x` | YES |
| MDIA-04 | Voice narration uploads to R2, returns stable URL | unit (mocked R2) | `pytest tests/test_media_generation.py -k "voice" -x` | YES (needs R2 upload assertion added) |
| MDIA-05 | Remotion sidecar render completes and returns URL | unit (mocked httpx) | `pytest tests/test_media_orchestrator.py -k "remotion" -x` | YES |
| MDIA-06 | Generated media saved to both content_jobs and media_assets | unit (mocked db) | `pytest tests/test_media_tasks_assets.py -x` | YES |
| MDIA-07 | Frontend MediaPanel handles 202 response, polls, displays image | manual (browser) | N/A | N/A — manual only |
| MDIA-08 | R2 presigned URL upload completes, confirm saves asset | unit (mocked R2) | `pytest tests/test_uploads_media_storage.py -x` | YES |

### Sampling Rate

- **Per task commit:** `cd backend && pytest tests/test_media_generation.py tests/test_media_orchestrator.py -x -q`
- **Per wave merge:** `cd backend && pytest tests/ -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/test_media_generation.py` — needs new test: `test_voice_uploads_to_r2_not_data_uri` (MDIA-04)
- [ ] `tests/test_media_orchestrator.py` — needs new test: `test_carousel_calls_remotion` (MDIA-02/05)
- [ ] `tests/test_media_generation.py` — needs new test: `test_celery_task_no_longer_imports_CreativeProvidersService` (Bug 1 regression)

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Synchronous image generation blocking API | Celery async with 202 return + polling | Phase 26+ | Requires frontend polling logic |
| Mock/placeholder video response | Real provider routing (runway/kling/luma/pika) | Pre-Phase 29 | Needs valid API keys to test |
| Audio as data: URI inline | Should be R2 public URL (to implement) | Phase 29 | Enables stable links, reduces MongoDB bloat |
| Carousel as per-slide PNG array | Should be Remotion-rendered video/download (to implement) | Phase 29 | Enables "download carousel" feature |

---

## Open Questions

1. **Remotion license for commercial use**
   - What we know: `remotion-service/server.ts` checks `REMOTION_LICENSE_KEY` env var for log level only
   - What's unclear: Whether a Remotion license is required for production commercial use (Remotion has a license fee for companies with >$1M revenue)
   - Recommendation: Verify Remotion licensing at `remotion.dev/license` — add `REMOTION_LICENSE_KEY` to Railway env if required

2. **Runway API current endpoint URLs**
   - What we know: `video.py` uses `https://api.runwayml.com/v1/image_to_video` and `/v1/generations` 
   - What's unclear: Runway API has changed in 2025; current documented endpoints may differ
   - Recommendation: Verify against current RunwayML API docs before testing video generation

3. **Carousel download format: MP4 vs ZIP of PNGs**
   - What we know: Remotion `ImageCarousel` renders as video (MP4) per `inferRenderType()` in server.ts
   - What's unclear: LinkedIn carousel format — LinkedIn accepts multiple images, not a video, for carousels
   - Recommendation: For MDIA-02, the Remotion MP4 is useful for preview/sharing; actual LinkedIn carousel publishing (Phase 30) will need individual slide images

4. **R2 CORS configuration access**
   - What we know: R2 CORS must be set in Cloudflare dashboard for bucket `thookai-media`
   - What's unclear: Whether R2 CORS is already configured from Phase 26/27 work
   - Recommendation: Verify in Cloudflare dashboard before testing MDIA-08; if not set, add PUT CORS rule for production and localhost origins

---

## Sources

### Primary (HIGH confidence)
- Direct code reading: `backend/agents/designer.py`, `backend/agents/video.py`, `backend/agents/voice.py` — full implementation audit
- Direct code reading: `backend/services/media_orchestrator.py` — complete orchestration pipeline
- Direct code reading: `backend/services/media_storage.py` — R2 presigned URL flow
- Direct code reading: `backend/services/creative_providers.py` — provider abstraction (confirmed class does NOT exist)
- Direct code reading: `backend/tasks/media_tasks.py` — Celery tasks (confirmed Bug 1)
- Direct code reading: `backend/routes/content.py` — media generation routes
- Direct code reading: `backend/routes/media.py` — upload and orchestrate routes
- Direct code reading: `remotion-service/server.ts` — Remotion sidecar API
- Direct code reading: `remotion-service/src/Root.tsx` — composition definitions
- Direct code reading: `frontend/src/components/MediaUploader.jsx` — upload component (uses `/api/uploads/media` multipart, not R2 presigned)
- Direct code reading: `frontend/src/pages/Dashboard/ContentStudio/ContentOutput.jsx` — MediaPanel (confirmed Bug 3)

### Secondary (MEDIUM confidence)
- CLAUDE.md and .planning/REQUIREMENTS.md — project constraints and requirements
- .planning/STATE.md — accumulated decisions and known blockers

### Tertiary (LOW confidence)
- Runway API endpoint paths — training data knowledge, unverified against current docs

---

## Metadata

**Confidence breakdown:**
- Bug identification: HIGH — direct code reading, no ambiguity
- Standard stack: HIGH — all libraries already in requirements.txt and installed
- Architecture patterns: HIGH — copied directly from existing working code in same codebase
- Provider API correctness (Runway, Kling, FAL): MEDIUM — endpoints match SDK docs but may be stale for Runway
- Remotion composition props: HIGH — read directly from Root.tsx
- R2 CORS requirement: MEDIUM — standard AWS S3/R2 pattern, verified to be a known issue in CLAUDE.md status section

**Research date:** 2026-04-12
**Valid until:** 2026-05-12 (provider API endpoints may change; Remotion version locked at 4.0.443)
