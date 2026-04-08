---
phase: 11
plan: "01"
subsystem: remotion-service
tags: [remotion, video-rendering, express, typescript, docker, r2-upload, media]
dependency_graph:
  requires: []
  provides: [remotion-render-service, POST-/render, GET-/render/:id/status, StaticImageCard, ImageCarousel, Infographic, TalkingHeadOverlay, ShortFormVideo]
  affects: [docker-compose.yml, media-orchestrator-phase-11-02]
tech_stack:
  added:
    - remotion@4.0.443
    - "@remotion/renderer@4.0.443"
    - "@remotion/cli@4.0.443"
    - express@^4.18.2
    - "@aws-sdk/client-s3@^3.540.0"
    - uuid@^9.0.0
    - typescript@^5.4.5
    - ts-node@^10.9.2
  patterns:
    - Express async render queue with fire-and-forget background jobs
    - Module-level bundle caching (called once at startup, cached for all renders)
    - In-memory Map-backed job store with UUID render IDs
    - R2 upload via S3-compatible SDK with /tmp dev fallback
    - Remotion compositions as typed React components with inputProps
    - docker-compose sidecar pattern (named volume for node_modules isolation)
key_files:
  created:
    - remotion-service/package.json
    - remotion-service/tsconfig.json
    - remotion-service/server.ts
    - remotion-service/lib/job-store.ts
    - remotion-service/lib/r2-upload.ts
    - remotion-service/src/index.ts
    - remotion-service/src/Root.tsx
    - remotion-service/src/compositions/StaticImageCard.tsx
    - remotion-service/src/compositions/ImageCarousel.tsx
    - remotion-service/src/compositions/Infographic.tsx
    - remotion-service/src/compositions/TalkingHeadOverlay.tsx
    - remotion-service/src/compositions/ShortFormVideo.tsx
  modified:
    - remotion-service/Procfile
    - docker-compose.yml
decisions:
  - Bundle caching via module-level `let bundlePath` — bundle() called once on startup pre-warm, never per-render — eliminates 30s startup latency from render hot path
  - renderType inference: StaticImageCard and Infographic default to "still" (renderStill), carousel/talking-head/short-form default to "video" (renderMedia) — overridable via render_type field
  - R2 upload uses /tmp dev fallback with console.warn when R2 env vars missing — consistent with CLAUDE.md principle of startup warning over silent corruption
  - timeoutInMilliseconds=120000 (2 minutes) for renderMedia — Remotion default is 30s which is insufficient for video composition with external assets
  - docker-compose remotion_node_modules as named volume — prevents host node_modules from conflicting with Alpine container node_modules (Linux vs macOS binary incompatibility)
  - StaticImageCard handles 3 layout variants (standard/quote/meme) under single composition ID — reduces composition registry surface while covering MEDIA-04/05/06 requirements
  - ShortFormVideo uses volume=0.15 for background music — follows audio mixing best practice (voice at 1.0, bed at 15%)
metrics:
  duration_seconds: 233
  completed_date: "2026-04-01"
  tasks_completed: 2
  tasks_total: 2
  files_created: 12
  files_modified: 2
---

# Phase 11 Plan 01: Remotion Render Service Summary

**One-liner:** Express/TypeScript Remotion render sidecar with 5 compositions (static image, carousel, infographic, talking-head overlay, short-form video), module-level bundle caching, async job queue, R2 upload via @aws-sdk/client-s3, and docker-compose integration on port 3001.

## What Was Built

The Remotion render service is a complete Express API in TypeScript serving as ThookAI's media composition engine. It runs as a standalone sidecar over HTTP — no Python imports, no direct FastAPI coupling.

**API surface:**
- `POST /render` — accept `{composition_id, input_props, render_type?}`, return `{render_id}` within <1s, execute render in background
- `GET /render/:id/status` — return current job status: `queued | rendering | done | failed`, plus `url` when done
- `GET /health` — return `{status: "ok", bundled: bool}` for docker healthcheck

**Composition registry (5 compositions):**

| ID | Dimensions | FPS | Render Type | Coverage |
|----|-----------|-----|-------------|---------|
| StaticImageCard | 1200x1200 | 30 | still | MEDIA-04 (image), MEDIA-05 (quote), MEDIA-06 (meme) |
| ImageCarousel | 1080x1080 | 30 | video | MEDIA-07 (carousel, max 10 slides) |
| Infographic | 1080x1350 | 30 | still | MEDIA-08 (data visualization) |
| TalkingHeadOverlay | 1080x1920 | 30 | video | MEDIA-09 (HeyGen + overlays) |
| ShortFormVideo | 1080x1920 | 30 | video | MEDIA-10/11 (multi-segment + audio) |

**Infrastructure:**
- `lib/job-store.ts`: `Map<string, JobStatus>` with `createJob/getJob/updateJob`, UUID render IDs
- `lib/r2-upload.ts`: `@aws-sdk/client-s3` `PutObjectCommand`, Cloudflare R2 endpoint, `/tmp` dev fallback
- `docker-compose.yml`: `remotion` service on `node:20-alpine`, port 3001, `remotion_node_modules` named volume, R2 and `REMOTION_LICENSE_KEY` env pass-through

## Decisions Made

1. **Bundle caching via module-level variable** — `bundle()` called once on startup (pre-warm), subsequent renders use cached path. This is the critical performance optimization: Remotion's `bundle()` takes 30-60s, caching ensures render requests return in milliseconds.

2. **renderType inference** — Static compositions (StaticImageCard, Infographic) auto-infer to `renderStill()`, dynamic compositions to `renderMedia()`. Caller can override with `render_type: "still" | "video"`.

3. **120s render timeout** — `timeoutInMilliseconds: 120000` set for `renderMedia()` — Remotion's default 30s is insufficient for video compositions with external asset loading.

4. **StaticImageCard 3-in-1** — Handles standard, quote, and meme layouts via `layout` prop rather than 3 separate composition IDs. Keeps the registry surface minimal.

5. **docker-compose named volume for node_modules** — `remotion_node_modules:/app/node_modules` prevents macOS/Linux binary conflicts when sharing the host filesystem.

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — all compositions render with real logic. The R2 upload has an intentional `/tmp` dev fallback (with console.warn) for environments without R2 configured — this is a documented fallback, not a stub, per CLAUDE.md's pattern for media storage.

## Self-Check: PASSED

**Files created:**
- [x] remotion-service/package.json — FOUND
- [x] remotion-service/tsconfig.json — FOUND
- [x] remotion-service/server.ts — FOUND
- [x] remotion-service/lib/job-store.ts — FOUND
- [x] remotion-service/lib/r2-upload.ts — FOUND
- [x] remotion-service/src/index.ts — FOUND
- [x] remotion-service/src/Root.tsx — FOUND
- [x] remotion-service/src/compositions/StaticImageCard.tsx — FOUND
- [x] remotion-service/src/compositions/ImageCarousel.tsx — FOUND
- [x] remotion-service/src/compositions/Infographic.tsx — FOUND
- [x] remotion-service/src/compositions/TalkingHeadOverlay.tsx — FOUND
- [x] remotion-service/src/compositions/ShortFormVideo.tsx — FOUND

**Commits:**
- [x] 7c92676 — Task 1: scaffold Express API, bundle caching, job store, R2 upload
- [x] ad514b4 — Task 2: 5 compositions, Root registry, docker-compose sidecar
