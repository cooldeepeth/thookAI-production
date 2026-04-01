---
gsd_state_version: 1.0
milestone: v2.0
milestone_name: Intelligent Content Operating System
status: verifying
stopped_at: Completed 16-01-PLAN.md — E2E critical path + dead link detection tests
last_updated: "2026-04-01T23:28:42.430Z"
last_activity: 2026-04-01
progress:
  total_phases: 8
  completed_phases: 8
  total_plans: 27
  completed_plans: 27
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-01)

**Core value:** Personalized content creation at scale — every user gets a unique voice fingerprint that drives all content generation, with real social platform publishing and analytics feedback loops.
**Current focus:** Phase 16 — e2e-audit-security-hardening-production-ship

## Current Position

Phase: 16 (e2e-audit-security-hardening-production-ship) — EXECUTING
Plan: 5 of 5
Status: Phase complete — ready for verification
Last activity: 2026-04-01

Progress: [░░░░░░░░░░] 0%

## Performance Metrics

**Velocity:**

- Total plans completed: 0 (v2.0)
- Average duration: -
- Total execution time: 0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| - | - | - | - |

**Recent Trend:**

- Last 5 plans: none yet
- Trend: -

*Updated after each plan completion*
| Phase 09 P01 | 4 | 2 tasks | 5 files |
| Phase 09 P02 | 18 | 3 tasks | 6 files |
| Phase 09 P03 | 22 | 2 tasks | 10 files |
| Phase 10 P01 | 2 | 2 tasks | 6 files |
| Phase 10 P02 | 83s | 2 tasks | 3 files |
| Phase 10-lightrag-knowledge-graph P03 | 225 | 2 tasks | 2 files |
| Phase 11 P01 | 233 | 2 tasks | 14 files |
| Phase 11 P02 | 328 | 2 tasks | 8 files |
| Phase 11 P03 | 135 | 2 tasks | 2 files |
| Phase 11 P04 | 5 | 2 tasks | 2 files |
| Phase 11 P05 | 399 | 2 tasks | 4 files |
| Phase 12 P01 | 1 | 2 tasks | 3 files |
| Phase 12-strategist-agent P03 | 2 | 2 tasks | 1 files |
| Phase 12-strategist-agent P02 | 153 | 1 tasks | 1 files |
| Phase 12-strategist-agent P04 | 12 | 2 tasks | 1 files |
| Phase 13-analytics-feedback-loop P01 | 5 | 2 tasks | 4 files |
| Phase 13 P02 | 285 | 2 tasks | 2 files |
| Phase 14-strategy-dashboard-notifications P01 | 21 | 2 tasks | 3 files |
| Phase 14-strategy-dashboard-notifications P02 | 8 | 2 tasks | 5 files |
| Phase 15-obsidian-vault-integration P01 | 294 | 1 tasks | 4 files |
| Phase 15 P03 | 151 | 1 tasks | 3 files |
| Phase 16 P02 | 3 | 2 tasks | 4 files |
| Phase 16 P04 | 147 | 2 tasks | 2 files |
| Phase 16 P03 | 123 | 2 tasks | 2 files |
| Phase 16 P05 | 299 | 2 tasks | 2 files |
| Phase 16-e2e-audit-security-hardening-production-ship P01 | 600 | 2 tasks | 2 files |

## Accumulated Context

### Decisions

- v2.0 architectural principle: New components (n8n, LightRAG, Remotion) run as sidecar services, integrated over HTTP — no new Python imports into FastAPI monolith
- n8n hybrid: Move cron + external-API tasks to n8n; keep Celery for Motor-coupled media generation tasks (no async-over-HTTP anti-pattern)
- LightRAG embedding model: Lock `text-embedding-3-small` in config before first document insert — no migration path exists without full index rebuild
- Strategist cadence controls are launch blockers, not polish — max 3 cards/day, 14-day dismissal suppression must ship in v1 of the feature
- Phase 12 depends on both Phase 10 (LightRAG populated) and Phase 13 (analytics flowing) — plan Phase 13 before Phase 12 execution starts
- [Phase 09]: HMAC-SHA256 over full request body bytes for n8n callback authentication — consistent with existing webhook_service.py pattern
- [Phase 09]: hmac.compare_digest used for constant-time comparison to prevent timing attacks on n8n webhook callbacks
- [Phase 09]: Trigger endpoint returns 404 for unconfigured workflow IDs — explicit failure over silent no-op
- [Phase 09]: D-09 honored: process-scheduled-posts uses agents.publisher.publish_to_platform directly — no content_tasks._publish_to_platform indirection
- [Phase 09]: D-05 honored: idempotency via find_one_and_update atomic claim + 2-minute published_at guard prevents duplicate social posts during overlapping n8n runs
- [Phase 09]: Celery worker retained for media/content tasks; beat schedule fully removed — n8n now owns all periodic scheduling via 7 execute endpoints
- [Phase 09]: WORKFLOW_NOTIFICATION_MAP excludes cleanup tasks — they are infrastructure ops, not user-visible events
- [Phase 09]: process-scheduled-posts callback includes affected_user_ids from result.published_user_ids to close notification loop
- [Phase 09]: _dispatch_workflow_notification uses lazy import pattern consistent with other execute endpoints in n8n_bridge.py
- [Phase 10]: NanoVectorDBStorage over MongoVectorDBStorage in LightRAG: preserves hybrid architecture (Pinecone for persona similarity, NanoVDB for graph-adjacent vectors)
- [Phase 10]: Per-user LightRAG isolation via doc_filter_func lambda in query param — storage-level filter, not just natural language scoping
- [Phase 10]: insert_content metadata header pattern: [CREATOR/PLATFORM/TYPE/EDITED] tags prepended to document text for LightRAG entity extraction context
- [Phase 10]: Lazy import pattern for lightrag_service in agents: avoids hard dependency, LightRAG unavailability does not block agent imports or content generation
- [Phase 10]: knowledge_context[:800] slice in Thinker prompt: prevents knowledge graph from consuming excessive LLM context
- [Phase 10-lightrag-knowledge-graph]: _FakeLightRAGConfig (plain class) used instead of MagicMock to avoid assert_* method collision — Python MagicMock treats methods starting with assert_ as magic assertion helpers
- [Phase 10-lightrag-knowledge-graph]: AST + string scan dual approach for routing contract tests: catches both top-level and lazy function-body imports
- [Phase 11]: Bundle caching via module-level bundlePath: bundle() called once at startup, cached for all renders — eliminates 30s startup latency from render hot path
- [Phase 11]: StaticImageCard 3-in-1 layout: handles standard/quote/meme via layout prop under single composition ID — covers MEDIA-04/05/06 while keeping registry surface minimal
- [Phase 11]: timeoutInMilliseconds=120000 for renderMedia: Remotion default 30s insufficient for video compositions with external asset loading
- [Phase 11]: get_r2_client imported at module-level in media_orchestrator.py for testability — not inside function body
- [Phase 11]: register_media_handler decorator pattern for dispatch table extensibility — Plans 03-04 register handlers without touching orchestrate()
- [Phase 11]: orchestrate_media_job max_retries=1: media orchestration is expensive/long-running, one retry sufficient
- [Phase 11]: Meme handler splits content_text on first double-newline into topText/bottomText; single-line -> bottomText=''
- [Phase 11]: Infographic validates data_points before any ledger entry — ValueError raised early, no orphaned pending ledger records
- [Phase 11]: Carousel truncates to max 10 slides via brief.slides[:10] before any ledger entry — no orphaned pending records
- [Phase 11]: HeyGen video URL staged to R2 immediately after avatar generation (inside try block) before ledger consumed update — prevents CDN URL expiry
- [Phase 11]: _generate_voice_for_video wrapper isolates pcm_48000 intent without modifying shared generate_voice_narration function
- [Phase 11]: select_media_format is deterministic (no LLM call) — scoring table gives stable, explainable results without API cost
- [Phase 11]: anthropic_available imported at qc.py module level (not inside validate_media_output) so unit tests can patch it via unittest.mock.patch
- [Phase 11]: validate_media_output anti_slop check gracefully passes when Anthropic key unavailable — QC does not block delivery
- [Phase 12]: StrategistConfig fields are application constants (not env-driven) — cadence parameters are launch-tuned values, not operator config
- [Phase 12]: Compound index (user_id, topic, status) on strategy_recommendations is MANDATORY — enables STRAT-05 14-day suppression as a single indexed query
- [Phase 12]: strategist_state has unique user_id index — one state document per user, upserted by nightly runner
- [Phase 12-strategist-agent]: nightly-strategist (without run- prefix) is the workflow map key; /execute/run-nightly-strategist (with run- prefix) is the endpoint path — matching existing n8n_bridge.py patterns
- [Phase 12-strategist-agent]: Lazy import for lightrag_service inside _query_content_gaps — consistent with Phase 10 lazy import pattern; LightRAG down at import time must not block agent module imports
- [Phase 12-strategist-agent]: Two-phase atomic upsert for _atomic_claim_card_slot: Phase 1 increments today counter, Phase 2 handles new-day reset via upsert — prevents race condition
- [Phase 12-strategist-agent]: Sequential processing in run_strategist_for_all_users (not asyncio.gather) to avoid LLM provider rate limit bursts during nightly cron runs
- [Phase 12-strategist-agent]: _AsyncIterator class used for Motor async cursor mocking — Python 3.13 requires __anext__ to be a real coroutine, not MagicMock
- [Phase 12-strategist-agent]: patch.dict sys.modules used for lazy-import mocking of services.lightrag_service in strategist tests
- [Phase 13-analytics-feedback-loop]: publish_results stores raw result dict from real_publish_to_platform — preserves post_id/tweet_id needed by social_analytics.update_post_performance()
- [Phase 13-analytics-feedback-loop]: analytics_24h_polled and analytics_7d_polled initialized to False at publish time so sparse compound indexes include them in poll queue queries
- [Phase 13-analytics-feedback-loop]: analytics due-at timestamps computed relative to publish moment (now), not scheduled_at — accurate 24h/7d windows from actual publish
- [Phase 13]: Per-user rate limit (MAX_JOBS_PER_USER=5) in polling endpoints to respect LinkedIn/X/Instagram API rate limits — deferred jobs picked up in next 15-min cron cycle
- [Phase 13]: Jobs marked analytics_Nh_polled=True regardless of API success — no infinite retry; analytics_Nh_error=True set on failure for diagnostics
- [Phase 13]: app.dependency_overrides[_verify_n8n_request] pattern for HMAC bypass in tests — patching settings causes MagicMock TypeError in HMAC function
- [Phase 14-strategy-dashboard-notifications]: Route does NOT call /api/content/create itself — frontend fires that call after receiving generate_payload (thin route wrapper pattern)
- [Phase 14-strategy-dashboard-notifications]: DismissRequest body is Optional — dismiss endpoint works with or without a reason body
- [Phase 14-strategy-dashboard-notifications]: handleApprove validates generate_payload fields before firing /api/content/create to surface backend errors early
- [Phase 14-strategy-dashboard-notifications]: SSE refresh uses useRef seenNotifIds set to prevent stale closure re-fires on already-seen notifications
- [Phase 15-obsidian-vault-integration]: PurePosixPath.parts for vault path traversal prevention — no filesystem access required, works for remote vault paths
- [Phase 15-obsidian-vault-integration]: Per-user obsidian_config in db.users with Fernet-encrypted API key takes precedence over global env fallback
- [Phase 15-obsidian-vault-integration]: is_configured() is synchronous (settings check only); _resolve_config() is async for accurate per-user check
- [Phase 15]: Fernet key normalisation mirrors routes/platforms.py _get_cipher() — SHA-256 hash for non-44-byte keys ensures any FERNET_KEY value works
- [Phase 15]: POST /api/obsidian/test returns connected=false with error message (not 500) for graceful frontend vault-unreachable state handling
- [Phase 16]: Production docker-compose.prod.yml uses ports:[] to remove host-published ports for n8n, lightrag, remotion, mongo, redis, postgres-n8n — defence-in-depth beyond plan spec
- [Phase 16]: thookai-internal network uses internal:true to block external routing at Docker daemon level — structural isolation not just firewall rules
- [Phase 16]: Two-mode test design for Remotion: unit tests mock HTTP and always run in CI; integration tests require REMOTION_URL env var
- [Phase 16]: _poll_until_done helper extracted as reusable coroutine for both unit mock polling and integration real polling
- [Phase 16]: Source inspection (inspect.getsource) used for SSE scoping static analysis — confirms user_id filter present without needing live DB mock
- [Phase 16]: patch.object(google_module.settings, field) preferred over patch('config.settings') for routes that import settings at module level
- [Phase 16]: Real stripe.error.SignatureVerificationError used as mock side_effect — MagicMock TypeError when exception hierarchy inspected
- [Phase 16]: SSE stream test uses inspect.getsource() not client.stream() — infinite polling loop prevents sync TestClient from returning
- [Phase 16]: Lazy import database mocking: patch('database.db') not 'routes.module.db' for n8n_bridge and notifications routes

### Pending Todos

None yet.

### Blockers/Concerns

- Remotion Company License required before Phase 11 launches — budget/procurement must happen before plan execution begins
- n8n LinkedIn/Instagram OAuth node scope needs verification before Phase 9 commits to n8n for publishing (may need custom HTTP Request nodes)
- LightRAG per-user workspace isolation pattern needs code-level verification against v1.4.12 API during Phase 10 planning
- Phase 13 (Analytics) depends on Phase 9 (n8n publishing working) — analytics polling via n8n cannot be validated until real posts flow through n8n

## Session Continuity

Last session: 2026-04-01T12:45:10.171Z
Stopped at: Completed 16-01-PLAN.md — E2E critical path + dead link detection tests
Resume file: None
