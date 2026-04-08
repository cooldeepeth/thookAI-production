# Phase 11: Multi-Model Media Orchestration - Research

**Researched:** 2026-04-01
**Domain:** Remotion 4.0 SSR API, fal.ai multi-model image generation, HeyGen avatar video, ElevenLabs voice narration, credit ledger design, R2 asset staging
**Confidence:** HIGH for Remotion API (official docs verified); MEDIUM-HIGH for provider integration patterns (official docs + existing codebase); MEDIUM for HeyGen overlay composition pattern (existing code + partial docs)

---

## Summary

Phase 11 builds the media production layer for ThookAI: a `MediaOrchestrator` service that decomposes a `MediaBrief` into per-asset tasks, routes each to the correct provider, stages all assets in Cloudflare R2, then calls the Remotion render service to assemble the final output. The phase expands the `remotion-service/` directory from a single `Procfile` stub into a real Express API with four named compositions.

The existing codebase provides a strong starting point. `backend/agents/designer.py` already handles multi-provider image routing with async timeouts. `backend/agents/video.py` already implements HeyGen and Luma polling patterns. `backend/agents/voice.py` implements ElevenLabs. These agents must be preserved and wired into the new MediaOrchestrator — not rewritten. The Remotion service is the new build: a complete Express API in TypeScript with four compositions, a bundle-caching pattern, and R2 upload on render completion.

The most critical implementation constraint is **asset staging before Remotion render** (MEDIA-13). All assets — HeyGen video output, ElevenLabs audio, fal.ai images — must be downloaded to Cloudflare R2 and only R2 URLs passed to Remotion. The Remotion `timeoutInMilliseconds` default is 30 seconds; external provider CDN URLs routinely exceed this under load. The second critical constraint is the **pipeline credit ledger** (MEDIA-03): per-stage credit tracking in a `media_pipeline_ledger` MongoDB collection is mandatory before the first provider call, not retrofitted after. Partial failure at stage N means stages 0..N-1 already consumed credits with no recovery.

**Primary recommendation:** Build in four waves — (1) Remotion service Express API with all four compositions and bundle caching, (2) MediaOrchestrator with static-image and carousel paths only (MEDIA-04, 05, 06, 07, 08) + pipeline ledger, (3) video paths (MEDIA-09, 10, 11) after image pipelines are stable, (4) Designer agent enhancements (MEDIA-12) and QC extension (MEDIA-14).

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| MEDIA-01 | Media Orchestrator service (`backend/services/media_orchestrator.py`) — decomposes MediaBrief into per-asset tasks, routes to best provider, assembles via Remotion | MediaBrief dataclass pattern; asyncio.gather for parallel asset generation; Remotion POST /render call pattern |
| MEDIA-02 | Remotion render service expanded with Express API (`POST /render`, `GET /render/:id/status`) and R2 upload | Remotion renderMedia() + bundle() API verified; Express async job queue pattern; R2 upload via boto3/S3 |
| MEDIA-03 | Pipeline credit ledger (`media_pipeline_ledger` collection) — per-stage credit tracking, cost caps per job, partial-failure accounting | Existing credits.py CreditOperation enum; MongoDB Motor async update patterns; existing ledger-style collections in codebase |
| MEDIA-04 | Static image with typography — brand-consistent social images via fal.ai/DALL-E + Remotion text overlay | Existing designer.py `generate_image()` → feeds into Remotion StaticImageCard composition |
| MEDIA-05 | Quote cards — styled text-on-background with persona branding, dynamic font/color from persona theme | Remotion composition with text overlay; persona_card visual_aesthetic field exists in DB |
| MEDIA-06 | Meme format — image + top/bottom text overlay with trending template support | Remotion composition for text-on-image; template system via inputProps |
| MEDIA-07 | Image carousel — multi-slide compositions (up to 10 slides) for LinkedIn/Instagram via Remotion | Remotion sequence/series composition; existing designer.py `generate_carousel()` for slide images |
| MEDIA-08 | Infographic — data-driven visual with stats, icons, and structured layout via Remotion composition | Remotion SVG composition pattern; data passed via inputProps |
| MEDIA-09 | Talking-head with overlays — HeyGen avatar + text/graphic overlays via Remotion composition | Existing video.py `_generate_heygen_avatar()` + R2 staging + Remotion OffthreadVideo + overlay layer |
| MEDIA-10 | Short-form video (15-60s) — A-roll (talking-head), B-roll (stock/generated), typography, ElevenLabs, music bed | Multi-source Remotion composition; ElevenLabs existing voice.py; Luma/Runway for B-roll |
| MEDIA-11 | Text-on-video — animated text overlays on user-uploaded or generated video clips | Remotion OffthreadVideo + animated text overlay; R2-hosted video input |
| MEDIA-12 | Designer agent plans composition by format — selects optimal content type per platform and content angle | LLM-based format selection logic extending existing designer.py; platform spec table |
| MEDIA-13 | All external assets pre-downloaded to R2 before Remotion render (timeout prevention) | R2 pre-staging pattern; httpx download + boto3 upload; 120s delayRender timeout |
| MEDIA-14 | QC agent checks brand consistency, anti-AI-slop detection, and platform-specific specs on all media output | Extending existing qc.py; platform spec validation table; Claude vision for slop detection |
</phase_requirements>

---

## Project Constraints (from CLAUDE.md)

- **NEVER commit directly to `main`** — all work branches from `dev`, PRs target `dev`
- **Branch naming**: `fix/`, `feat/`, `infra/` short-description
- **Never hardcode secrets** — all settings via `backend/config.py` dataclasses (`from config import settings`)
- **Never use `os.environ.get()` directly** in route/agent/service files
- **Never introduce new Python package** without adding to `backend/requirements.txt`
- **Never introduce new npm package** without noting in PR description
- **After any change to `backend/agents/`** — verify full pipeline still flows: Commander → Scout → Thinker → Writer → QC
- **Config pattern**: `settings.*` from `backend/config.py` dataclasses exclusively
- **Database access**: `from database import db` with Motor async; never synchronous PyMongo
- **LLM model**: `claude-sonnet-4-20250514` (Anthropic primary)
- **Billing changes**: flag for human review — no auto-merge
- **Do not delete or modify `backend/db_indexes.py`**
- **v2.0 sidecar principle**: New components (Remotion) run as sidecar services, integrated over HTTP — no new Python imports that pull in Node.js into FastAPI

---

## Standard Stack

### Core (Phase 11 additions)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `remotion` | 4.0.443 (latest confirmed 2026-04-01 via npm) | React video composition framework for Remotion service | Only mature React-based SSR video compositor; existing `remotion-service/` already uses this pattern |
| `@remotion/renderer` | 4.0.443 (same as remotion) | Node.js SSR API (`renderMedia`, `bundle`, `selectComposition`) | Required peer for server-side rendering; provides `renderMedia()` and `bundle()` APIs |
| `fal-client` | 0.13.2 (latest on PyPI; currently 0.13.1 installed — bump needed) | fal.ai image generation with async queue API | Existing provider; async improvements in 0.13.1+ include queue streaming |
| `express` | existing in Node ecosystem | HTTP API for Remotion service | Simple REST server for render jobs; no new install needed in Node |
| `boto3` | existing in requirements.txt | R2 asset upload from Remotion service and pre-staging | S3-compatible; already used in `backend/services/media_storage.py` |

### Supporting (Phase 11 — existing, already in stack)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `fal_client` (Python) | 0.13.2 | Image generation routing | All static image asset generation (MEDIA-04 through 08) |
| `lumaai` | >=1.0.0 | Luma Dream Machine B-roll video | MEDIA-10 B-roll segment generation |
| `elevenlabs` | >=1.50.0 | Voice narration generation | MEDIA-10 voice track; output_format pcm_48000 required |
| `httpx` | 0.28.1 | Async HTTP for R2 pre-staging downloads + Remotion service calls | Asset download from HeyGen/fal.ai CDNs before R2 upload |
| `motor` | 3.3.1 | Async MongoDB for pipeline ledger | `media_pipeline_ledger` collection writes |

### Version Verification (confirmed 2026-04-01)

```bash
npm view remotion version        # 4.0.443
npm view @remotion/renderer version  # 4.0.443
pip3 index versions fal-client   # latest: 0.13.2 (installed: 0.13.1 — needs bump)
```

### Installation

```bash
# Python: bump fal-client in backend/requirements.txt
fal-client==0.13.2   # was fal-client>=0.10.0

# Remotion service: initialize package.json and install
cd remotion-service/
npm init -y
npm install remotion@4.0.443 @remotion/renderer@4.0.443 express
npm install --save-dev typescript @types/express @types/node ts-node tsup
```

**New env vars to add to `backend/config.py`:**

```python
# Add to AppConfig dataclass or new RemotionConfig dataclass:
REMOTION_SERVICE_URL  # e.g., http://remotion:3001
REMOTION_LICENSE_KEY  # from remotion.pro (required for SaaS use in v4; mandatory in v5)
```

---

## Architecture Patterns

### Recommended Project Structure

```
remotion-service/
├── src/
│   ├── compositions/
│   │   ├── StaticImageCard.tsx    # MEDIA-04/05/06: image + text overlay
│   │   ├── ImageCarousel.tsx      # MEDIA-07: multi-slide (up to 10 slides)
│   │   ├── Infographic.tsx        # MEDIA-08: data-driven SVG layout
│   │   ├── TalkingHeadOverlay.tsx # MEDIA-09: HeyGen video + lower-third
│   │   └── ShortFormVideo.tsx     # MEDIA-10/11: A-roll + B-roll + audio
│   ├── Root.tsx                   # Registers all compositions
│   └── index.ts                   # Entry point for bundle()
├── server.ts                      # Express API: POST /render, GET /render/:id/status
├── lib/
│   ├── r2-upload.ts               # boto3-compatible R2 upload helper
│   └── job-store.ts               # In-memory job status map (render_id → status/url)
├── package.json
├── tsconfig.json
└── Procfile                       # web: node dist/server.js

backend/
├── services/
│   └── media_orchestrator.py      # NEW: MediaBrief → asset tasks → Remotion assembly
├── routes/
│   └── media_orchestrate.py       # NEW: POST /api/media/orchestrate
├── tasks/
│   └── media_tasks.py             # EXTEND: add orchestrate_media_job() Celery task

frontend/
└── src/pages/
    └── (extend ContentStudio with media format selector)
```

### Pattern 1: Remotion Express API with Bundle Caching

**What:** The Remotion service bundles once at startup (or on first request), caches the bundle path, and reuses it for all subsequent renders. `renderMedia()` is called per-render with different `inputProps`.

**When to use:** Every render request. Never call `bundle()` per-render — it is a webpack compilation and takes 10-30 seconds.

**Key API verified from official docs (Remotion 4.0.443):**

```typescript
// Source: https://www.remotion.dev/docs/renderer/render-media
// Source: https://www.remotion.dev/docs/bundle

import { bundle } from "@remotion/renderer";
import { selectComposition, renderMedia } from "@remotion/renderer";
import path from "path";

// Called ONCE at startup — cache this result
let bundlePath: string | null = null;

async function getBundlePath(): Promise<string> {
  if (bundlePath) return bundlePath;
  bundlePath = await bundle({
    entryPoint: path.resolve("./src/index.ts"),
    // webpackOverride for custom fonts/assets if needed
  });
  return bundlePath;
}

// Called per-render with different inputProps
async function renderComposition(
  compositionId: string,
  inputProps: Record<string, unknown>,
  outputPath: string
): Promise<void> {
  const serveUrl = await getBundlePath();

  const composition = await selectComposition({
    serveUrl,
    id: compositionId,
    inputProps,
  });

  await renderMedia({
    composition,
    serveUrl,
    codec: "h264",
    outputLocation: outputPath,
    inputProps,
    timeoutInMilliseconds: 120000, // 120s — required for R2-hosted asset loading
    licenseKey: process.env.REMOTION_LICENSE_KEY, // required for SaaS use
  });
}
```

**Critical note on `timeoutInMilliseconds`:** The official parameter name in `renderMedia()` is `timeoutInMilliseconds` (not `delayRenderTimeoutInMilliseconds`). Verified from Remotion 4.0.443 official docs. This controls how long `delayRender()` calls wait before failing.

### Pattern 2: Express Job Queue for Async Renders

**What:** `POST /render` returns a `render_id` immediately. The render runs in the background. `GET /render/:id/status` polls for completion. On success, the final MP4/PNG is uploaded to R2 and the R2 URL is stored in the job store.

**When to use:** All render requests — video renders take 30-300 seconds; never block the HTTP response.

```typescript
// server.ts
import express from "express";
import { v4 as uuidv4 } from "uuid";

const app = express();
app.use(express.json());

const jobs: Map<string, { status: string; url?: string; error?: string }> = new Map();

app.post("/render", async (req, res) => {
  const { composition_id, input_props } = req.body;
  const render_id = uuidv4();
  jobs.set(render_id, { status: "queued" });
  res.json({ render_id });

  // Non-blocking render in background
  runRender(render_id, composition_id, input_props).catch((err) => {
    jobs.set(render_id, { status: "failed", error: err.message });
  });
});

app.get("/render/:id/status", (req, res) => {
  const job = jobs.get(req.params.id);
  if (!job) return res.status(404).json({ error: "not_found" });
  res.json(job);
});
```

### Pattern 3: MediaOrchestrator — Decompose MediaBrief → Parallel Asset Generation → Remotion Assembly

**What:** The Python `MediaOrchestrator` receives a `MediaBrief` dict, decomposes it into per-asset tasks (image, voice, avatar), runs them in parallel via `asyncio.gather`, stages all outputs to R2, then calls the Remotion service.

**When to use:** All media generation requests from `POST /api/media/orchestrate`.

```python
# backend/services/media_orchestrator.py
import asyncio
import httpx
import logging
from typing import Dict, Any
from dataclasses import dataclass
from config import settings
from database import db
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

@dataclass
class MediaBrief:
    """Input to the media orchestrator."""
    job_id: str
    user_id: str
    media_type: str          # "static_image" | "quote_card" | "meme" | "carousel" |
                             # "infographic" | "talking_head" | "short_form_video" | "text_on_video"
    platform: str            # "linkedin" | "instagram" | "x"
    content_text: str        # text content to render
    persona_card: Dict[str, Any]
    style: str               # style preset
    slides: list             # for carousel (list of slide dicts)
    data_points: list        # for infographic
    avatar_id: str           # HeyGen avatar ID (for talking_head)

async def orchestrate(brief: MediaBrief) -> Dict[str, Any]:
    """Decompose brief → parallel asset generation → R2 staging → Remotion render."""

    # 1. Verify cost cap before any provider call
    cost_cap = _get_cost_cap(brief.media_type)
    await _ledger_start(brief.job_id, cost_cap)

    try:
        # 2. Parallel asset generation
        assets = await _generate_assets(brief)

        # 3. Stage all external URLs to R2
        staged = await _stage_assets_to_r2(assets, brief.job_id)

        # 4. Call Remotion to assemble
        render_result = await _call_remotion(brief, staged)

        await _ledger_complete(brief.job_id, render_result["url"])
        return render_result

    except Exception as e:
        await _ledger_fail(brief.job_id, str(e))
        raise
```

### Pattern 4: R2 Pre-Staging of External Assets

**What:** All assets generated by external providers (HeyGen, fal.ai, ElevenLabs, Luma) are downloaded and uploaded to R2 before being passed to Remotion. Remotion only ever fetches from R2.

**When to use:** Mandatory for every provider output. Never pass external CDN URLs directly to Remotion.

```python
# backend/services/media_orchestrator.py (partial)
async def _stage_assets_to_r2(assets: Dict, job_id: str) -> Dict:
    """Download all assets from provider CDNs and upload to R2."""
    staged = {}
    async with httpx.AsyncClient(timeout=90.0) as client:
        for asset_key, asset_url in assets.items():
            if not asset_url or asset_url.startswith("data:"):
                # base64 data URL — upload directly
                staged[asset_key] = await _upload_base64_to_r2(asset_url, job_id, asset_key)
            else:
                # External URL — download then upload
                response = await client.get(asset_url)
                response.raise_for_status()
                r2_url = await _upload_bytes_to_r2(response.content, job_id, asset_key)
                staged[asset_key] = r2_url
    return staged
```

### Pattern 5: Pipeline Credit Ledger

**What:** Every provider call is recorded in `media_pipeline_ledger` before it is made. On success, credit cost is marked `consumed`. On failure, subsequent stages are marked `skipped`. This enables cost auditing and partial-failure refund accounting.

```python
# Collection: media_pipeline_ledger
# Document schema:
{
    "ledger_id": str,         # uuid
    "job_id": str,            # content_jobs.job_id
    "user_id": str,
    "stage": str,             # "image_generation" | "voice_generation" | "avatar_generation" | "remotion_render"
    "provider": str,          # "fal" | "elevenlabs" | "heygen" | "remotion"
    "credits_consumed": int,
    "cost_cap": int,          # total job budget
    "status": str,            # "pending" | "consumed" | "failed" | "skipped"
    "failure_reason": str,    # null unless failed
    "created_at": datetime,
    "completed_at": datetime
}
```

### Pattern 6: HeyGen Avatar — Async Polling Wrapped in asyncio.wait_for

**What:** The existing `_generate_heygen_avatar()` in `backend/agents/video.py` polls `GET /v1/video_status.get` synchronously in a loop. For the media pipeline, wrap this in `asyncio.wait_for()` with a 300s timeout and add the result to the R2 staging step.

**When to use:** MEDIA-09, MEDIA-10 avatar segments.

The existing HeyGen implementation polls correctly via `GET /v1/video_status.get?video_id={id}` and checks `status == "completed"`. No changes needed to the existing polling logic — the MediaOrchestrator calls the existing `generate_avatar_video()` function wrapped in a timeout.

### Anti-Patterns to Avoid

- **Calling `bundle()` per render:** `bundle()` is a webpack compilation (10-30s). Cache the bundle path at startup; reuse for all renders. Only re-bundle when composition source code changes.
- **Passing external CDN URLs to Remotion:** HeyGen video URLs are temporary (~1h). fal.ai image URLs expire. Luma CDN URLs have rate limits. Always pre-stage to R2.
- **Generating all slides sequentially in carousel:** Use `asyncio.gather()` to generate all slide images in parallel — a 5-slide carousel takes the same time as a 1-slide image with parallel generation.
- **No timeout on Remotion service HTTP call from FastAPI:** The Remotion render can take 60-300s. FastAPI must call Remotion as a fire-and-forget via Celery task, not a blocking HTTP call in a route handler.
- **Using `data:` base64 URLs as Remotion inputProps:** Pass them as R2 URLs only. Large base64 strings in `inputProps` inflate the webpack bundle and cause render failures.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Video composition assembly | Custom FFmpeg timeline | Remotion `renderMedia()` | FFmpeg requires imperative frame-by-frame control; Remotion uses React component tree — composable, testable |
| Image generation | Direct Stability AI API calls | `backend/agents/designer.py` + `get_best_available_provider()` | Existing multi-provider fallback chain already handles 7 providers |
| Voice narration | ElevenLabs HTTP client from scratch | `backend/agents/voice.py` + existing SDK | Existing `_generate_elevenlabs()` handles async SDK, voice selection, and base64 encoding |
| Avatar video | HeyGen HTTP client from scratch | `backend/agents/video.py` `_generate_heygen_avatar()` | Existing polling implementation is correct; just wrap in `asyncio.wait_for()` |
| R2 upload | Custom boto3 setup | `backend/services/media_storage.py` existing helpers | `media_storage.py` already configures boto3 with R2 endpoint, bucket, presigned URLs |
| Credit deduction | New credit system | `backend/services/credits.py` `CreditOperation` enum | Existing `deduct_credits()` function; add `MEDIA_ORCHESTRATION` operations to enum |
| Async job queue (Remotion service) | Redis queue in Node | In-memory Map with `render_id` as key | Single-process Remotion service; memory map is sufficient at current scale; add Redis only if horizontal scaling needed |

**Key insight:** This phase is primarily wiring together existing provider implementations (`designer.py`, `video.py`, `voice.py`) through a new orchestrator layer + Remotion assembly. The value is in the composition pattern and ledger, not in new provider code.

---

## Common Pitfalls

### Pitfall 1: Remotion `bundle()` Called Per-Render — Server Hangs Under Load

**What goes wrong:** Each render request triggers a 10-30s webpack compilation. Under 3+ concurrent requests, the Remotion service becomes unresponsive.

**Why it happens:** Official docs note this is "an anti-pattern." Development setup calls `bundle()` inline because renders are infrequent.

**How to avoid:** Call `bundle()` once at Express server startup and cache the path in a module-level variable. Re-bundle only if the `src/` directory changes (not needed in production).

**Warning signs:** `POST /render` requests start taking >20s. Server CPU spikes for every render request, not just the first.

---

### Pitfall 2: Remotion Asset Timeout — `timeoutInMilliseconds` Insufficient

**What goes wrong:** Remotion fails with "delayRender called but not cleared" when loading assets from R2 under load. Default `timeoutInMilliseconds` in `renderMedia()` is 30 seconds.

**Why it happens:** R2 GET latency to Remotion container varies. Under concurrent renders, S3-compatible request queuing adds 10-60s.

**How to avoid:** Set `timeoutInMilliseconds: 120000` in every `renderMedia()` call. Pre-stage all assets to R2 before triggering Remotion (MEDIA-13) — this removes external CDN latency from the render path entirely.

**Warning signs:** Remotion render failures correlated with large assets (>10MB video files). Renders pass in development but fail intermittently in production.

---

### Pitfall 3: Pipeline Credit Leak on Partial Failure

**What goes wrong:** ElevenLabs voice generation (12 credits) succeeds, HeyGen avatar (50 credits) times out. 12 credits are consumed with no deliverable output. No refund mechanism exists.

**Why it happens:** Multi-stage pipelines call providers in sequence or parallel without tracking per-stage cost before calling.

**How to avoid:** Write a `media_pipeline_ledger` record with `status: "pending"` before each provider call. On success, update to `consumed`. On failure/timeout, mark remaining stages as `skipped` and record `failure_reason`. Implement `cost_cap_credits` per job — if cumulative consumption reaches cap, abort remaining stages.

**Warning signs:** `media_pipeline_ledger` has `status: "failed"` records with no `credits_refunded: true`. Provider invoices grow faster than successful media job count.

---

### Pitfall 4: ElevenLabs Audio Sample Rate Mismatch

**What goes wrong:** ElevenLabs default output is 44.1kHz. Remotion and most MP4 containers expect 48kHz. Audio-video sync drifts in the final rendered video.

**Why it happens:** ElevenLabs API default `output_format` is `mp3_44100_128`. The difference is invisible in isolated audio playback but causes sync issues over 30+ second videos.

**How to avoid:** Always pass `output_format: "pcm_48000"` to ElevenLabs API for video pipeline use. Convert with `ffmpeg -ar 48000` if you must use a different format. Verify sample rate of generated audio before staging to R2.

**Warning signs:** Audio/video sync drift increasing over the duration of rendered videos. Sync is fine for short clips (<10s) but drifts for 30-60s clips.

---

### Pitfall 5: HeyGen Video URL Expiry Before R2 Stage

**What goes wrong:** HeyGen `video_url` from `GET /v1/video_status.get` expires after approximately 1 hour. If R2 staging is delayed (Celery queue backlog, slow network), the download fails with a 403/404.

**Why it happens:** HeyGen hosts output videos on a time-limited CDN URL. The URL appears valid in the JSON response but becomes inaccessible before being staged.

**How to avoid:** Stage HeyGen video to R2 immediately after the polling loop confirms `status == "completed"` — within the same async call, before returning from `_generate_heygen_avatar()`. Do not pass HeyGen URLs through multiple async boundaries before downloading.

**Warning signs:** R2 pre-staging fails with HTTP 403 or 404 specifically for `cdn.heygen.com` URLs. Failure rate increases with queue depth.

---

### Pitfall 6: fal.ai `submit_async` + `handler.get()` Pattern With Old Client

**What goes wrong:** `fal_client 0.10.0` (current spec in `requirements.txt`) uses `fal_client.submit_async()` with a handler object. `0.13.x` changed the API to `fal.run()` / `fal.subscribe()` patterns. Upgrading without reading the changelog breaks existing `_generate_fal()` in `designer.py`.

**Why it happens:** `requirements.txt` has `fal-client>=0.10.0` (unpinned lower bound). The installed version is 0.13.1 and the latest is 0.13.2. The `submit_async` handler pattern still works in 0.13.x but the import path changed.

**How to avoid:** Pin `fal-client==0.13.2` in `requirements.txt`. Run the existing `test_media_generation.py` tests after the version bump to confirm no regressions. The existing `designer.py` code uses `fal_client.submit_async()` which is still valid in 0.13.x.

**Warning signs:** ImportError or AttributeError on `fal_client.submit_async` after version bump.

---

### Pitfall 7: Designer Agent `generate_image()` Returns `data:` Base64 URL — Remotion Cannot Load It

**What goes wrong:** `designer.py` returns `image_url` as `data:image/png;base64,...` (base64-encoded data URL). Remotion compositions using `<Img>` or `<OffthreadVideo>` do not support data URLs — they require HTTP/HTTPS URLs pointing to actual files.

**Why it happens:** `designer.py` was built for frontend display where data URLs work. The Remotion pipeline requires actual HTTP URLs.

**How to avoid:** In the `_stage_assets_to_r2()` function of `media_orchestrator.py`, detect data URLs and decode/upload them to R2 before passing to Remotion. Pattern: `if asset_url.startswith("data:") → base64.decode + upload bytes to R2 → return R2 https URL`.

**Warning signs:** Remotion composition throws "Failed to load image" or "Could not load asset" when `<Img src>` or `<OffthreadVideo src>` receives a data URL.

---

### Pitfall 8: Remotion `selectComposition()` Returns Wrong Duration for Dynamic Compositions

**What goes wrong:** A `ShortFormVideo` composition has dynamic `durationInFrames` based on audio length. If `selectComposition()` is called with incorrect `inputProps`, it returns the default composition duration (e.g., 150 frames / 5s) instead of the actual audio-matched duration. The render produces a video cut at 5s even if audio is 45s.

**Why it happens:** Remotion determines composition duration at bundle time from the default props, but dynamic durations require the composition to compute `durationInFrames` from `inputProps`. The caller must pass the correct `inputProps` to `selectComposition()` — the same props used for `renderMedia()`.

**How to avoid:** Always pass `inputProps` to both `selectComposition()` and `renderMedia()`. For audio-matched durations: calculate `durationInFrames = Math.ceil(audioDurationSeconds * fps)` in the server before calling Remotion, then pass `durationInFrames` explicitly as an input prop.

**Warning signs:** Rendered video is exactly 5s regardless of content length. Audio is truncated at render time.

---

## Code Examples

### Verified: Remotion renderMedia() with R2 assets

```typescript
// Source: https://www.remotion.dev/docs/renderer/render-media (Remotion 4.0.443)
import { renderMedia, selectComposition } from "@remotion/renderer";

const composition = await selectComposition({
  serveUrl: bundlePath,
  id: "StaticImageCard",
  inputProps: {
    imageUrl: "https://pub-xxx.r2.dev/thookai/media/job_123/bg.png",
    text: "Leadership starts with listening",
    brandColor: "#2563EB",
    fontFamily: "Inter",
  },
});

await renderMedia({
  composition,
  serveUrl: bundlePath,
  codec: "h264",
  outputLocation: "/tmp/output-job123.mp4",
  inputProps: composition.defaultProps, // same props as selectComposition
  timeoutInMilliseconds: 120000,        // 120s — critical for R2 asset loading
  licenseKey: process.env.REMOTION_LICENSE_KEY,
});
```

### Verified: MediaOrchestrator asyncio.gather for parallel asset generation

```python
# Source: codebase pattern + Python asyncio docs
# backend/services/media_orchestrator.py

from agents.designer import generate_image
from agents.voice import generate_voice_narration

async def _generate_assets_parallel(brief: MediaBrief) -> Dict[str, Any]:
    """Generate all required assets in parallel."""
    tasks = {}

    if brief.media_type in ("static_image", "quote_card", "meme"):
        tasks["background_image"] = generate_image(
            prompt=brief.content_text,
            style=brief.style,
            platform=brief.platform,
            persona_card=brief.persona_card,
        )

    if brief.media_type in ("short_form_video", "talking_head"):
        tasks["voice_audio"] = generate_voice_narration(
            text=brief.content_text,
            output_format="pcm_48000",  # Required for video sync
        )

    if not tasks:
        return {}

    keys = list(tasks.keys())
    results = await asyncio.gather(*tasks.values(), return_exceptions=True)
    return dict(zip(keys, results))
```

### Verified: Pipeline ledger write pattern (Motor async)

```python
# backend/services/media_orchestrator.py
from database import db
from datetime import datetime, timezone
import uuid

async def _ledger_stage(
    job_id: str, user_id: str, stage: str,
    provider: str, credits: int
) -> str:
    """Write pending ledger entry before provider call."""
    ledger_id = str(uuid.uuid4())
    await db.media_pipeline_ledger.insert_one({
        "ledger_id": ledger_id,
        "job_id": job_id,
        "user_id": user_id,
        "stage": stage,
        "provider": provider,
        "credits_consumed": credits,
        "status": "pending",
        "created_at": datetime.now(timezone.utc),
    })
    return ledger_id

async def _ledger_update(ledger_id: str, status: str, reason: str = None) -> None:
    """Update ledger entry after provider call completes or fails."""
    update = {"status": status, "completed_at": datetime.now(timezone.utc)}
    if reason:
        update["failure_reason"] = reason
    await db.media_pipeline_ledger.update_one(
        {"ledger_id": ledger_id},
        {"$set": update},
    )
```

### Verified: ElevenLabs `pcm_48000` format for video pipeline

```python
# Source: ElevenLabs SDK patterns + existing backend/agents/voice.py
# Extend existing _generate_elevenlabs() to accept output_format param:

from elevenlabs.client import AsyncElevenLabs

client = AsyncElevenLabs(api_key=api_key)
audio_bytes = await client.generate(
    text=text,
    voice=voice_id,
    model="eleven_monolingual_v1",
    output_format="pcm_48000",  # Required for Remotion video sync
)
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Remotion Lambda for cloud rendering | Self-hosted `@remotion/renderer` Express service | Remotion 4.0 (2024) | Eliminates AWS vendor lock-in; existing `remotion-service/` Procfile confirms this is the chosen pattern |
| Manual FFmpeg video assembly | Remotion React composition + `renderMedia()` | Remotion 3.0+ | Component-driven, testable compositions vs. imperative FFmpeg timelines |
| Single-provider image generation | Multi-provider routing with fallback chain | v1.0 (existing `designer.py`) | Already implemented; MediaOrchestrator builds on top |
| `bundle()` per render (antipattern) | `bundle()` once at startup, cache path | Remotion 4.0 recommendation | 10-30x render throughput improvement |
| `timeoutInMilliseconds` default 30s | Must set to 120000 for multi-provider assets | Remotion 4.0 `renderMedia()` signature | Prevents systematic asset-load timeouts in production |
| `fal-client>=0.10.0` (unpinned) | Pin to `==0.13.2` | 2026-04-01 (latest) | Latest async improvements; matches installed 0.13.1 with one patch bump |
| Remotion `licenseKey` optional | From Remotion 5.0: mandatory for Automators | Remotion v4.0.409+ introduced key support; v5 makes mandatory | Must add `REMOTION_LICENSE_KEY` env var before v5 upgrade |

**Deprecated/outdated:**

- `fal-client` `submit_async()` returning `FalEventHandler` object: still works in 0.13.x but `fal.subscribe()` is the preferred pattern in newer versions — existing `designer.py` code remains valid.
- HeyGen v1 API (`/v2/video/generate`): The existing `_generate_heygen_avatar()` uses `POST /v2/video/generate` + `GET /v1/video_status.get` — this is still the current production API as of 2026-04-01.

---

## Open Questions

1. **Remotion Company License procurement**
   - What we know: Remotion requires a Company License for SaaS use (verified from official docs). `licenseKey` param available from v4.0.409; mandatory in Remotion 5.0 for Automators.
   - What's unclear: Exact cost and procurement timeline. Remotion pricing requires contacting remotion.pro — not publicly listed per the documentation fetched.
   - Recommendation: Kuldeepsinh must visit remotion.pro and purchase license before this phase ships to production. Add `REMOTION_LICENSE_KEY` to `.env.example` with a `# REQUIRED for production` comment. The `licenseKey` field in `renderMedia()` is optional until v5 — development can proceed without it, but the key must be in place before launch.

2. **HeyGen avatar_id management for user accounts**
   - What we know: `_generate_heygen_avatar()` accepts `avatar_id` param; default is `"default"`. Production users need their own avatar IDs from HeyGen avatar creation flow.
   - What's unclear: Does MEDIA-09 require per-user HeyGen avatar creation as a prerequisite, or does it use HeyGen's stock avatars? The CLAUDE.md roadmap lists "Avatar creation flow" as a future feature (not yet implemented).
   - Recommendation: For MEDIA-09 in Phase 11, use HeyGen's built-in stock avatar IDs. Store `heygen_default_avatar_id` in `VideoProviderConfig` or use a hardcoded default. Per-user avatar creation is deferred (per CLAUDE.md roadmap).

3. **Remotion service deployment topology**
   - What we know: `remotion-service/` has only a `Procfile` — no `package.json`, no source. The Procfile says `web: npm run start`. This is a complete build from scratch.
   - What's unclear: Whether the Remotion service should share the same Render/Railway deployment as the backend or run as a separate service. Remotion renders are CPU-intensive and should not compete with FastAPI workers.
   - Recommendation: Deploy as a separate service on Render/Railway. `remotion-service/` becomes its own `package.json` project with its own Procfile process. FastAPI calls it via `REMOTION_SERVICE_URL` env var (add to `AppConfig` dataclass).

4. **`renderStill()` vs `renderMedia()` for static images**
   - What we know: Remotion provides `renderStill()` for single-frame PNG output. `renderMedia()` produces video (MP4). For MEDIA-04/05/06 (static image + typography), rendering a 1-frame video as MP4 is wasteful.
   - What's unclear: Whether to use `renderStill()` for static compositions and `renderMedia()` for video compositions, or unify on `renderMedia()` with a single-frame composition.
   - Recommendation: Use `renderStill()` for all static image compositions (StaticImageCard, QuoteCard, Meme output, individual carousel slides, Infographic). Use `renderMedia()` for video compositions (TalkingHeadOverlay, ShortFormVideo). The Express API endpoint should accept a `render_type: "still" | "video"` parameter to route to the correct Remotion function.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Node.js | Remotion render service | Yes | v20.15.0 | — |
| npm | Remotion service package install | Yes | 10.7.0 | — |
| Python 3.11+ | Backend FastAPI | Yes (3.13.5 on dev machine; 3.11.11 in runtime.txt) | 3.13.5 local / 3.11.11 prod | — |
| pytest | Backend test suite | Yes | 9.0.2 | — |
| fal-client | Image generation | Yes (installed 0.13.1) | 0.13.1 → bump to 0.13.2 | Fallback to DALL-E / Stability |
| remotion + @remotion/renderer | Video composition | Not installed (remotion-service/ is empty) | 4.0.443 (latest) | — (must install) |
| HeyGen API | MEDIA-09 talking-head | Key in config (HEYGEN_API_KEY) | v2 API active | D-ID as fallback |
| ElevenLabs SDK | MEDIA-10 voice | Key in config (ELEVENLABS_API_KEY) | >=1.50.0 | OpenAI TTS fallback |
| Cloudflare R2 | Asset staging (MEDIA-13) | Configured if R2_ACCESS_KEY_ID set | S3-compatible | Fatal if absent — no fallback for production |
| Remotion Company License | Production SaaS rendering | Not yet procured | — | Devs can proceed without it; production blocked |

**Missing dependencies with no fallback:**
- `remotion@4.0.443` + `@remotion/renderer@4.0.443` — must be installed in `remotion-service/` before any compositions can be written or tested
- Remotion Company License — required for production launch; development can proceed without it

**Missing dependencies with fallback:**
- HeyGen API key not configured → D-ID fallback in `generate_avatar_video()` exists
- ElevenLabs not configured → OpenAI TTS fallback in `voice.py` exists
- fal-client not configured → DALL-E / Stability fallback in `designer.py` exists

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 + pytest-asyncio 0.23.0 |
| Config file | `backend/pytest.ini` |
| Quick run command | `cd backend && pytest tests/test_media_generation.py tests/test_media_tasks_assets.py -x` |
| Full suite command | `cd backend && pytest` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| MEDIA-01 | MediaOrchestrator decomposes brief and calls providers | unit | `pytest tests/test_media_orchestrator.py -x` | Wave 0 |
| MEDIA-02 | Remotion Express API returns render_id on POST /render | unit (Node) | `cd remotion-service && npm test` | Wave 0 |
| MEDIA-03 | Ledger entry written before provider call; updated on fail | unit | `pytest tests/test_media_pipeline_ledger.py -x` | Wave 0 |
| MEDIA-04 | Static image generation returns R2 URL via orchestrator | unit | `pytest tests/test_media_orchestrator.py::test_static_image -x` | Wave 0 |
| MEDIA-05 | Quote card generation uses persona branding | unit | `pytest tests/test_media_orchestrator.py::test_quote_card -x` | Wave 0 |
| MEDIA-06 | Meme format returns text+image composition | unit | `pytest tests/test_media_orchestrator.py::test_meme -x` | Wave 0 |
| MEDIA-07 | Carousel generates up to 10 slides via Remotion | unit | `pytest tests/test_media_orchestrator.py::test_carousel -x` | Wave 0 |
| MEDIA-08 | Infographic renders data_points as Remotion composition | unit | `pytest tests/test_media_orchestrator.py::test_infographic -x` | Wave 0 |
| MEDIA-09 | Talking-head calls HeyGen, stages to R2, calls Remotion | unit (mocked) | `pytest tests/test_media_orchestrator.py::test_talking_head -x` | Wave 0 |
| MEDIA-10 | Short-form video assembles A-roll + B-roll + voice | unit (mocked) | `pytest tests/test_media_orchestrator.py::test_short_form_video -x` | Wave 0 |
| MEDIA-11 | Text-on-video overlays R2 video with animated text | unit (mocked) | `pytest tests/test_media_orchestrator.py::test_text_on_video -x` | Wave 0 |
| MEDIA-12 | Designer agent selects correct format per platform+angle | unit | `pytest tests/test_designer_format_selection.py -x` | Wave 0 |
| MEDIA-13 | External URLs staged to R2 before Remotion render | unit | `pytest tests/test_media_orchestrator.py::test_r2_staging -x` | Wave 0 |
| MEDIA-14 | QC agent validates brand consistency on media output | unit | `pytest tests/test_qc_media.py -x` | Wave 0 |

### Sampling Rate

- **Per task commit:** `cd backend && pytest tests/test_media_orchestrator.py -x`
- **Per wave merge:** `cd backend && pytest tests/test_media_generation.py tests/test_media_orchestrator.py tests/test_media_pipeline_ledger.py`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `backend/tests/test_media_orchestrator.py` — covers MEDIA-01, 03, 04, 05, 06, 07, 08, 09, 10, 11, 12, 13
- [ ] `backend/tests/test_media_pipeline_ledger.py` — covers MEDIA-03 ledger write/update/fail paths
- [ ] `backend/tests/test_designer_format_selection.py` — covers MEDIA-12 format selection logic
- [ ] `backend/tests/test_qc_media.py` — covers MEDIA-14 QC media validation
- [ ] `remotion-service/tests/` — Node.js unit tests for Express API endpoints and render job queue

---

## Sources

### Primary (HIGH confidence)

- [Remotion `renderMedia()` API docs](https://www.remotion.dev/docs/renderer/render-media) — `timeoutInMilliseconds` parameter name, `licenseKey` param, `codec`, `serveUrl` verified
- [Remotion `bundle()` API docs](https://www.remotion.dev/docs/bundle) — bundle-caching anti-pattern warning ("calling bundle() for every render is an anti-pattern"), `entryPoint` param
- [Remotion `delayRender()` docs](https://www.remotion.dev/docs/delay-render) — timeout failure behavior confirmed
- [Remotion licensing docs](https://www.remotion.dev/docs/licensing) — Company License for SaaS; `licenseKey` available from v4.0.409; mandatory in v5 for Automators
- [fal-client on PyPI](https://pypi.org/project/fal-client/) — version 0.13.2 confirmed latest; 0.13.1 currently installed
- npm registry (live check) — `remotion@4.0.443`, `@remotion/renderer@4.0.443` confirmed as latest 2026-04-01
- `backend/agents/designer.py` (codebase) — existing image generation, provider routing, `asyncio.wait_for()` pattern
- `backend/agents/video.py` (codebase) — existing HeyGen polling pattern (`/v1/video_status.get`), Luma async SDK, `_valid_key()` pattern
- `backend/agents/voice.py` (codebase) — existing ElevenLabs async SDK, voice ID list
- `backend/services/credits.py` (codebase) — `CreditOperation` enum, credit cost structure
- `backend/config.py` (codebase) — `VideoProviderConfig`, `R2Config`, existing config dataclass patterns

### Secondary (MEDIUM confidence)

- Project-level ARCHITECTURE.md (`.planning/research/ARCHITECTURE.md`) — MediaOrchestrator pattern, four named compositions, R2 pre-staging requirement — verified consistent with official Remotion docs
- Project-level PITFALLS.md (`.planning/research/PITFALLS.md`) — Remotion asset timeout, credit leak patterns, ElevenLabs 48kHz requirement
- Project-level STACK.md (`.planning/research/STACK.md`) — Remotion version recommendations, fal-client upgrade guidance

### Tertiary (LOW confidence)

- None identified for this phase.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — npm registry confirmed Remotion 4.0.443; PyPI confirmed fal-client 0.13.2; official Remotion docs verified renderMedia() API
- Architecture: HIGH — Remotion bundle/render/still pattern verified from official docs; MediaOrchestrator pattern consistent with existing codebase structure; R2 staging is explicit MEDIA-13 requirement
- Pitfalls: HIGH — Remotion timeout documented in official delayRender docs; credit leakage pattern from existing PITFALLS research; ElevenLabs 48kHz from project pitfalls research (MEDIUM — not independently verified from ElevenLabs docs but consistent with video pipeline conventions); HeyGen URL expiry documented in PITFALLS.md
- Test gaps: HIGH — existing `test_media_generation.py` confirms pytest-asyncio is the standard test pattern; new test files needed follow the same mock pattern

**Research date:** 2026-04-01
**Valid until:** 2026-05-01 (Remotion version; stable APIs; fal-client stable)

**Known gap:** Remotion Company License cost — pricing page requires direct contact with remotion.pro (not published). Must be resolved before production launch. Development can proceed without it in Remotion 4.x (licenseKey is optional until v5).
