---
phase: 11-multi-model-media-orchestration
verified: 2026-04-01T05:24:40Z
status: gaps_found
score: 4/5 success criteria verified
re_verification: false
gaps:
  - truth: "User can generate a brand-consistent static image / quote card / meme / infographic — image appears in media assets with correct platform dimensions"
    status: partial
    reason: "All orchestration handlers are implemented and tested but _call_remotion() sends wrong JSON field names to the Remotion server — every render call returns HTTP 400 and fails at raise_for_status()"
    artifacts:
      - path: "backend/services/media_orchestrator.py"
        issue: "_call_remotion sends {composition, inputProps, renderType} but Remotion server (server.ts) expects {composition_id, input_props, render_type} — camelCase vs snake_case mismatch"
    missing:
      - "Fix _call_remotion JSON payload keys: 'composition' -> 'composition_id', 'inputProps' -> 'input_props', 'renderType' -> 'render_type'"

  - truth: "The Designer agent selects the optimal content format for the platform and content angle without user guidance — format choices are explained in the job details"
    status: failed
    reason: "select_media_format() exists in designer.py and is tested, but is never called from pipeline.py, routes/media.py, or any production code path — the function is orphaned"
    artifacts:
      - path: "backend/agents/designer.py"
        issue: "select_media_format() is defined and tested but has no callers in production code"
    missing:
      - "Wire select_media_format() into the content generation flow — either in pipeline.py before Writer step or in the /api/media/orchestrate endpoint to auto-populate media_type when not specified"
      - "Wire validate_media_output() into a post-render step (e.g. media route after Remotion render completes) to satisfy MEDIA-14 end-to-end"

human_verification:
  - test: "Trigger a full render by calling POST /api/media/orchestrate with media_type='static_image' and confirm the resulting job reaches 'done' status with a real R2 URL"
    expected: "Job transitions from queued -> rendering -> done; media asset saved in DB with R2 URL pointing to a valid PNG"
    why_human: "Requires running services (FastAPI, Remotion sidecar, R2 credentials); cannot verify without live infrastructure"
  - test: "Generate a 5-slide carousel and verify all slides share the persona brand color in the rendered output"
    expected: "Rendered Remotion output has consistent brandColor across all slides"
    why_human: "Pixel-level brand consistency requires visual inspection of rendered output"
---

# Phase 11: Multi-Model Media Orchestration Verification Report

**Phase Goal:** Users can generate professional-grade social media visuals and video in all major formats — the platform routes each asset to the optimal provider and assembles the final output via Remotion
**Verified:** 2026-04-01T05:24:40Z
**Status:** gaps_found
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (from ROADMAP Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | User can generate brand-consistent static image / quote card / meme / infographic for any approved content job | PARTIAL | Handlers implemented and tested; blocked by _call_remotion field name mismatch |
| 2 | User can generate multi-slide image carousel (up to 10 slides) for LinkedIn/Instagram | PARTIAL | _handle_carousel implemented with asyncio.gather; blocked by same _call_remotion bug |
| 3 | User can generate talking-head video + short-form reel with voice, B-roll, music bed | PARTIAL | _handle_talking_head, _handle_short_form_video implemented; blocked by same _call_remotion bug |
| 4 | If any provider fails mid-pipeline, credit ledger records exact stage of failure — no silent credit drain | VERIFIED | _ledger_stage/update/check_cap/skip_remaining all implemented with 12 passing tests |
| 5 | Designer agent selects optimal content format without user guidance — choices explained | FAILED | select_media_format() exists in designer.py but is orphaned — never called in production code |

**Score:** 4/5 success criteria verifiable at code level, but truths 1-3 are blocked at integration point (Remotion API field name mismatch) and truth 5 has no production call site.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `remotion-service/server.ts` | Express API with POST /render and GET /render/:id/status | VERIFIED | Both endpoints present; accepts {composition_id, input_props, render_type} |
| `remotion-service/src/Root.tsx` | Remotion composition registry with all 5 compositions | VERIFIED | All 5 composition IDs registered: StaticImageCard, ImageCarousel, Infographic, TalkingHeadOverlay, ShortFormVideo |
| `remotion-service/src/index.ts` | Bundle entry point with registerRoot | VERIFIED | Contains `registerRoot(Root)` |
| `remotion-service/lib/job-store.ts` | In-memory render job tracking | VERIFIED | Map<string, JobStatus> with createJob/getJob/updateJob |
| `remotion-service/lib/r2-upload.ts` | R2 upload helper using S3-compatible SDK | VERIFIED | PutObjectCommand, R2_PUBLIC_URL, /tmp dev fallback |
| `backend/services/media_orchestrator.py` | MediaBrief dataclass + orchestrate() + R2 staging + ledger | VERIFIED | 1168 lines, all 8 media-type handlers, full pipeline |
| `backend/config.py` | RemotionConfig dataclass with REMOTION_SERVICE_URL | VERIFIED | Class RemotionConfig at line 267 with remotion_service_url and remotion_license_key |
| `backend/services/credits.py` | MEDIA_ORCHESTRATION credit operation | VERIFIED | MEDIA_ORCHESTRATION = 25 at line 39 |
| `backend/routes/media.py` | POST /orchestrate endpoint | VERIFIED | OrchestrateRequest + @router.post("/orchestrate") at line 184 |
| `backend/tasks/media_tasks.py` | orchestrate_media_job Celery task | VERIFIED | @shared_task decorated function at line 497 |
| `backend/db_indexes.py` | media_pipeline_ledger indexes | VERIFIED | media_pipeline_ledger indexes at line 206 |
| `backend/agents/designer.py` | select_media_format() for automated format selection | PARTIAL | Function exists at line 666; PLATFORM_FORMAT_PREFERENCES and CONTENT_ANGLE_FORMAT_MAP defined; ORPHANED — no callers |
| `backend/agents/qc.py` | validate_media_output() for media quality control | PARTIAL | Function exists at line 182; PLATFORM_MEDIA_SPECS defined; ORPHANED — no callers |
| `backend/tests/test_media_orchestrator.py` | 34 unit tests for orchestrator | VERIFIED | 34 tests, all passing |
| `backend/tests/test_media_pipeline_ledger.py` | 12 unit tests for credit ledger | VERIFIED | 12 tests, all passing |
| `backend/tests/test_designer_format_selection.py` | 13 unit tests for format selection | VERIFIED | 13 tests, all passing |
| `backend/tests/test_qc_media.py` | 10 unit tests for media QC | VERIFIED | 10 tests, all passing |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `remotion-service/server.ts` | `remotion-service/lib/job-store.ts` | import createJob/getJob/updateJob | VERIFIED | Line 11: `import { createJob, getJob, updateJob } from "./lib/job-store"` |
| `remotion-service/server.ts` | `@remotion/renderer bundle()` | getBundlePath() cached call | VERIFIED | Module-level `let bundlePath: string | null = null`; getBundlePath() calls bundle() once |
| `docker-compose.yml` | `remotion-service` | remotion service definition | VERIFIED | Lines 196-221: remotion service on port 3001 with R2 env vars and healthcheck |
| `backend/services/media_orchestrator.py` | `backend/services/media_storage.py` | R2 upload for pre-staging | VERIFIED | Line 25: `from services.media_storage import get_r2_client` |
| `backend/services/media_orchestrator.py` | `media_pipeline_ledger` collection | db.media_pipeline_ledger.insert_one | VERIFIED | _ledger_stage writes to db.media_pipeline_ledger |
| `backend/services/media_orchestrator.py` | Remotion service HTTP | httpx POST to REMOTION_SERVICE_URL/render | BROKEN | POST sends `{"composition": ..., "inputProps": ..., "renderType": ...}` but server expects `{"composition_id": ..., "input_props": ..., "render_type": ...}` — HTTP 400 on every render |
| `backend/agents/designer.py` | `backend/services/media_orchestrator.py` | select_media_format feeds MediaBrief.media_type | NOT_WIRED | select_media_format() has no callers in production code |
| `backend/agents/qc.py` | Remotion output URL | validate_media_output post-render | NOT_WIRED | validate_media_output() has no callers in production code |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `media_orchestrator._call_remotion` | render_id / url | POST /render on Remotion sidecar | No — 400 response due to field name mismatch | HOLLOW — structurally wired but data cannot flow due to API contract mismatch |
| `media_orchestrator._ledger_stage` | ledger_id | db.media_pipeline_ledger.insert_one | Yes | FLOWING |
| `media_orchestrator._stage_asset_to_r2` | R2 URL | get_r2_client() / /tmp fallback | Yes (with /tmp fallback) | FLOWING |
| `routes/media.py` orchestrate_media | {job_id, status} | Brief constructed from persona_engines DB | Yes | FLOWING |
| `agents/designer.py` select_media_format | {media_type, reason, alternatives, confidence} | Deterministic scoring tables | Yes — deterministic, no external call | ORPHANED — data flows through function but function is never called |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| All 69 unit tests pass | `pytest tests/test_media_pipeline_ledger.py tests/test_media_orchestrator.py tests/test_designer_format_selection.py tests/test_qc_media.py` | 69 passed, 0 failed | PASS |
| select_media_format importable and callable | `python3 -c "from agents.designer import select_media_format, PLATFORM_FORMAT_PREFERENCES"` | No error | PASS |
| validate_media_output importable | `python3 -c "from agents.qc import validate_media_output, PLATFORM_MEDIA_SPECS"` | No error | PASS |
| _MEDIA_TYPE_HANDLERS has all 8 types | `python3 -c "from services.media_orchestrator import _MEDIA_TYPE_HANDLERS; assert len(_MEDIA_TYPE_HANDLERS) == 8"` | 8 handlers confirmed | PASS |
| Remotion POST /render field name contract | Inspecting server.ts vs _call_remotion() | Mismatch: "composition" vs "composition_id" | FAIL |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| MEDIA-01 | 11-02 | Media Orchestrator service with MediaBrief | SATISFIED | backend/services/media_orchestrator.py with full orchestrate() |
| MEDIA-02 | 11-01 | Remotion Express API (POST /render, GET /render/:id/status) + R2 upload | SATISFIED | remotion-service/server.ts fully implemented |
| MEDIA-03 | 11-02 | Pipeline credit ledger (media_pipeline_ledger) | SATISFIED | _ledger_stage/update/check_cap/skip_remaining + 12 tests |
| MEDIA-04 | 11-03 | Static image with typography | PARTIAL | _handle_static_image calls _call_remotion("StaticImageCard") but render blocked by field mismatch |
| MEDIA-05 | 11-03 | Quote cards | PARTIAL | _handle_quote_card with layout="quote" implemented; same Remotion API blocker |
| MEDIA-06 | 11-03 | Meme format with top/bottom text | PARTIAL | _handle_meme with topText/bottomText split; same blocker |
| MEDIA-07 | 11-04 | Image carousel up to 10 slides | PARTIAL | _handle_carousel with asyncio.gather; same blocker |
| MEDIA-08 | 11-03 | Infographic (data-driven visual) | PARTIAL | _handle_infographic with data_points validation; same blocker |
| MEDIA-09 | 11-04 | Talking-head with overlays | PARTIAL | _handle_talking_head with immediate R2 staging; same blocker |
| MEDIA-10 | 11-04 | Short-form video (voice + B-roll + music) | PARTIAL | _handle_short_form_video with parallel generation; same blocker |
| MEDIA-11 | 11-04 | Text-on-video with animated overlays | PARTIAL | _handle_text_on_video with video_url staging; same blocker |
| MEDIA-12 | 11-05 | Designer agent format selection | NOT_SATISFIED | select_media_format() implemented but never called in production path |
| MEDIA-13 | 11-02 | External assets pre-downloaded to R2 before Remotion | SATISFIED | _stage_asset_to_r2 called before every _call_remotion invocation in all 8 handlers |
| MEDIA-14 | 11-05 | QC agent brand consistency + anti-slop + platform specs | NOT_SATISFIED | validate_media_output() implemented but never called in production path |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `backend/services/media_orchestrator.py` | 375 | `"composition": composition_id` | BLOCKER | Wrong key name — server expects "composition_id"; causes HTTP 400 on all renders |
| `backend/services/media_orchestrator.py` | 376 | `"inputProps": input_props` | BLOCKER | Wrong key name — server expects "input_props" |
| `backend/services/media_orchestrator.py` | 377 | `"renderType": render_type` | BLOCKER | Wrong key name — server expects "render_type" |
| `backend/agents/designer.py` | 666 | `select_media_format` defined | WARNING | Orphaned function — implemented and tested but never called from production code |
| `backend/agents/qc.py` | 182 | `validate_media_output` defined | WARNING | Orphaned function — implemented and tested but never called from production code |

### Human Verification Required

#### 1. Full End-to-End Render Flow

**Test:** After fixing the _call_remotion field name mismatch, start docker-compose, call `POST /api/media/orchestrate` with `{"media_type": "static_image", "platform": "linkedin", "content_text": "Test post"}`, poll for completion.
**Expected:** Job reaches "done" status with a valid R2 URL pointing to a rendered PNG image with the persona brand color visible.
**Why human:** Requires running infrastructure (FastAPI, Remotion sidecar on port 3001, R2 credentials, FAL API key for image generation).

#### 2. Carousel Visual Consistency

**Test:** Generate a 5-slide carousel and download the Remotion output.
**Expected:** All slides render with consistent brand color, slide number indicators visible, and slides stay within 1080x1080 dimensions.
**Why human:** Pixel-level visual inspection required; cannot verify brand color application programmatically without rendering.

#### 3. Short-Form Video with Audio Sync

**Test:** Call orchestrate with `media_type="short_form_video"` with valid `avatar_id` and check the output MP4.
**Expected:** Voice narration (audioUrl) and video segments play in sync; background music at reduced volume; lower-third appears on talking-head segment.
**Why human:** A/V sync quality requires playback; MP4 output cannot be verified programmatically.

### Gaps Summary

Two gaps block full goal achievement:

**Gap 1 (Blocker): API field name mismatch in `_call_remotion()`**

The Python orchestrator and the Remotion Node.js server were implemented independently and use different JSON key naming conventions. The server (built in Plan 11-01) uses snake_case: `composition_id`, `input_props`, `render_type`. The orchestrator (built in Plan 11-02) sends camelCase: `composition`, `inputProps`, `renderType`. Since the server checks `if (!composition_id)` and returns 400 when missing, every render call fails with an unhandled HTTP error at `response.raise_for_status()`. This breaks truths 1, 2, and 3. Fix requires changing three lines in `_call_remotion()` in `backend/services/media_orchestrator.py`.

**Gap 2 (Partial): `select_media_format()` and `validate_media_output()` are orphaned**

Both functions were built to satisfy MEDIA-12 and MEDIA-14 respectively, but neither has a production call site. `select_media_format()` should be called when a user requests media generation without specifying a format (auto-selection), or as a step in `pipeline.py` before the Writer step. `validate_media_output()` should be called after a Remotion render completes to gate the asset on brand/platform compliance. Without wiring, MEDIA-12 and MEDIA-14 are present in tests only.

---

_Verified: 2026-04-01T05:24:40Z_
_Verifier: Claude (gsd-verifier)_
