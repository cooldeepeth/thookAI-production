---
phase: 29-media-generation-pipeline
plan: "04"
subsystem: media-generation
tags:
  - remotion
  - carousel
  - bug-fix
  - content-route
dependency_graph:
  requires:
    - 29-02
    - 29-03
  provides:
    - generate_carousel wired to Remotion ImageCarousel composition
    - carousel response includes remotion_url field
    - content_jobs.carousel.remotion_url stored in MongoDB
  affects:
    - backend/routes/content.py
tech_stack:
  added: []
  patterns:
    - "Module-level import (import X as _x) rather than from-import inside function body to enable patch interception"
key_files:
  created: []
  modified:
    - backend/routes/content.py
decisions:
  - "Import services.media_orchestrator as module object (not from-import) inside generate_carousel() so unittest.mock.patch on the module attribute is respected at call time"
  - "Remove redundant local 'from services.credits import deduct_credits' inside generate_carousel() — it shadowed the module-level import and broke patch('routes.content.deduct_credits') in tests"
  - "Remotion failure wrapped in bare except Exception — non-fatal, slides always returned"
metrics:
  duration_minutes: 10
  completed_date: "2026-04-12"
  tasks_completed: 2
  files_modified: 1
---

# Phase 29 Plan 04: Wire Remotion ImageCarousel into generate_carousel Route Summary

**One-liner:** Remotion `_call_remotion("ImageCarousel", ...)` wired into `generate_carousel()` route after per-slide image generation, returning `remotion_url` in response and storing it in MongoDB.

## What Was Built

Fixed Bug 4 from 29-RESEARCH.md: the `/api/content/generate-carousel` route called `designer_carousel()` to produce per-slide images but never invoked Remotion to assemble them into a downloadable MP4. The route now:

1. Calls `_media_orch._call_remotion("ImageCarousel", {slides, brandColor, fontFamily}, "video")` after designer_carousel returns slides
2. Wraps the Remotion call in `try/except Exception` — sidecar unavailability is non-fatal; slides are always returned
3. Sets `result["remotion_url"]` (null if Remotion failed) before the DB write
4. Stores both `carousel` (full result with remotion_url) and `carousel.remotion_url` (dotpath for easy querying) in `content_jobs`

## Tasks

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Wire _call_remotion into generate_carousel() route | b8fd5ba | backend/routes/content.py |
| 2 | Run Bug 4 regression test and carousel test suite | b8fd5ba | (verification only) |

## Decisions Made

1. **Module-level import pattern for Remotion call:** Used `import services.media_orchestrator as _media_orch` inside the function body (not `from services.media_orchestrator import _call_remotion`). A `from`-import binds the name to the original function object at import time — `unittest.mock.patch` replaces the module attribute but the local binding already points to the unpatched object. The module-object approach (`_media_orch._call_remotion(...)`) always resolves through the module's current attribute, which the patch does replace.

2. **Removed redundant local credits import:** The `generate_carousel()` function had a local `from services.credits import deduct_credits, CreditOperation` inside the function body that shadowed the module-level import. This prevented `patch("routes.content.deduct_credits")` from working in the test, causing a 402 response before Remotion was ever reached. Removed the local import; the module-level import already provides the name.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Local `from services.credits import deduct_credits` inside generate_carousel() shadowed module-level import**
- **Found during:** Task 2 (test debugging)
- **Issue:** The test patches `routes.content.deduct_credits` but the local re-import inside the function body creates a new local binding that bypasses the patch. Route returned 402 before ever reaching the Remotion call.
- **Fix:** Removed the local `from services.credits import deduct_credits, CreditOperation` inside `generate_carousel()`. The module-level import at line 14 already provides both names.
- **Files modified:** backend/routes/content.py
- **Commit:** b8fd5ba

**2. [Rule 1 - Bug] `from services.media_orchestrator import _call_remotion` inside function body also bypassed test patch**
- **Found during:** Task 1 initial implementation
- **Issue:** Same pattern — `from X import f` binds the local name `f` to the original function object at import time. `patch("services.media_orchestrator._call_remotion")` replaces the module attribute but the local binding is unaffected.
- **Fix:** Changed to `import services.media_orchestrator as _media_orch` and called `_media_orch._call_remotion(...)` so the call always resolves through the module attribute.
- **Files modified:** backend/routes/content.py
- **Commit:** b8fd5ba

## Verification Results

```
# _call_remotion / remotion_url / ImageCarousel in content.py
Line 485: remotion_url = None
Line 489: remotion_result = await _media_orch._call_remotion(
Line 490:     "ImageCarousel",
Line 498: remotion_url = remotion_result.get("url")
Line 499: logger.info(f"Remotion carousel rendered: {remotion_url}")
Line 508: result["remotion_url"] = remotion_url
Line 516: "carousel.remotion_url": remotion_url,

# Bug 4 regression test — PASSED
tests/test_media_orchestrator.py::test_carousel_route_calls_remotion PASSED

# Full suite — no regressions
47 passed, 3 warnings in 0.71s
```

## Known Stubs

None — `remotion_url` is null when the Remotion sidecar is unavailable (dev environment), but this is intentional non-fatal behavior documented in the plan. Slides are always returned.

## Self-Check: PASSED

- [x] backend/routes/content.py exists and modified
- [x] Commit b8fd5ba exists in git log
- [x] `_call_remotion` present (line 489)
- [x] `remotion_url` present (lines 485, 498, 499, 508, 509, 516)
- [x] `ImageCarousel` present (line 490)
- [x] Bug 4 regression test GREEN
- [x] All 47 media orchestrator + ledger tests pass
