# Milestones

## v2.0 Intelligent Content Operating System (Shipped: 2026-04-01)

**Phases completed:** 8 phases, 27 plans, 45 tasks

**Key accomplishments:**

- HMAC-SHA256-authenticated n8n callback endpoint and auth-protected workflow trigger endpoint wired into FastAPI, with N8nConfig dataclass and 12 passing unit tests
- One-liner:
- One-liner:
- One-liner:
- 32 passing tests verifying lightrag_service.py correctness (18 unit), routing contract enforcement via AST (14 integration), per-user isolation at storage-filter level, and entity type semantic validity on real ThookAI content
- One-liner:
- MediaBrief dataclass
- 1. [Rule 2 - Missing] Added `test_infographic_empty_data_points_raises_value_error`
- Carousel, talking_head, short_form_video, and text_on_video handlers wired through MediaOrchestrator with asyncio.gather parallel generation — all 8 media types now fully orchestrated.
- Deterministic media format selection via scoring tables in designer.py and 4-check media validation (dimensions, brand, anti-slop, file-format) in qc.py with 23 unit tests.
- StrategistConfig dataclass with cadence controls (max 3 cards/day, 14-day suppression) plus MongoDB indexes for strategy_recommendations and strategist_state collections
- Nightly Strategist Agent with cadence controls (max 3 cards/day, 14-day suppression), atomic cap guard, dismissal tracking, LightRAG-backed gap analysis, and pre-filled generate_payload for one-click content generation
- n8n trigger path for the Strategist Agent wired in n8n_bridge.py: workflow map entry, notification map entry, and HMAC-authenticated execute endpoint calling `run_strategist_for_all_users`
- 29 tests covering all 7 STRAT requirements — card schema, cadence controls, topic suppression, consecutive dismissal threshold, and generate_payload compatibility. All pass with mocked MongoDB, LLM, and LightRAG.
- Publish write-back wires content_jobs.publish_results[platform] + analytics due-at timestamps to every n8n-published scheduled post, enabling Plan 02 to poll real social metrics
- One-liner:
- One-liner:
- One-liner:
- ObsidianConfig dataclass + obsidian_service.py HTTP client with PurePosixPath path traversal prevention, per-user Fernet-encrypted config, and 30 passing tests.
- Scout vault search merging and Strategist vault signal injection — both non-fatal, 14 tests pass.
- One-liner:
- 617 lines, 10 tests
- One-liner:
- One-liner:
- 5 unit tests (always run in CI):
- 50 tests verifying Stripe billing (checkout, webhooks, subscription lifecycle) and OAuth flows for all 4 platforms (LinkedIn, X/Twitter PKCE, Instagram, Google) — all API calls mocked

---

## v1.0 ThookAI Stabilization (Shipped: 2026-03-31)

**Phases completed:** 8 phases, 22 plans, 23 tasks

**Key accomplishments:**

- Test suite fixed from INTERNALERROR to 95 collected/59 passing via conftest.py exclusions and aiohttp-to-httpx migration; Celery beat schedule hardened with explicit task names and video queue routing
- One-liner:
- 1. [Rule 1 - Bug] JWT secret mismatch between create and decode paths
- One-liner:
- Verified (no change needed):
- 1. [Rule 1 - Bug] Orchestrator module import blocked by langgraph not being installed locally
- One-liner:
- 1. [Rule 1 - Bug] `_publish_to_platform` missing `media_assets` parameter
- `backend/services/credits.py`
- One-liner:
- One-liner:
- One-liner:
- 1. [Rule 1 - Bug] Wrong patch target for services.social_analytics db reference
- backend/tests/test_platform_features.py
- backend/tests/test_sharing_notifications_webhooks.py
- One-liner:
- 26-test pytest suite using Python pathlib to verify 5 frontend quality requirements: mobile sidebar responsive props, error boundary lifecycle methods, empty state CTAs, 401 redirect via ProtectedRoute, and valid imports with no hardcoded localhost URLs
- Problem:
- Eliminated Vite/CRA env var collision in 12 frontend files and corrected 15 stale Pending entries in REQUIREMENTS.md traceability table

---
