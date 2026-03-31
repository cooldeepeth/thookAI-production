# Phase 9: n8n Infrastructure + Real Publishing - Context

**Gathered:** 2026-04-01
**Status:** Ready for planning

<domain>
## Phase Boundary

Replace Celery beat with self-hosted n8n for all scheduled/external-API workflows. Establish FastAPI-to-n8n webhook bridge with HMAC-SHA256 auth. Execute hard Celery-to-n8n cutover with idempotency keys on publish operations. Retain Celery only for Motor-coupled media generation tasks. Provide user-visible workflow status for in-progress operations.

</domain>

<decisions>
## Implementation Decisions

### n8n Deployment Topology
- **D-01:** n8n runs as a separate Docker container (sidecar) with PostgreSQL 15 for queue mode — per research recommendation. Not embedded in the FastAPI process.
- **D-02:** n8n communicates with FastAPI exclusively via webhooks (n8n→FastAPI callback) and HTTP triggers (FastAPI→n8n webhook POST). No shared Python process.
- **D-03:** Redis (existing) serves as n8n queue broker. PostgreSQL is new, dedicated to n8n.

### Celery Cutover Strategy
- **D-04:** Hard cutover per job category — disable Celery beat entry before activating n8n schedule equivalent. Never run both simultaneously for the same task.
- **D-05:** Idempotency key on all scheduled-post publish operations — check `last_published_at` within 2-minute window to prevent duplicate social posts.
- **D-06:** 7 beat tasks migrate to n8n: `process_scheduled_posts`, `reset_daily_limits`, `refresh_monthly_credits`, `cleanup_old_jobs`, `cleanup_expired_shares`, `aggregate_daily_analytics`, `cleanup_stale_running_jobs`.
- **D-07:** `run_content_pipeline` and all `tasks.media_tasks.*` stay in Celery — they require Motor async context that can't be replicated in n8n HTTP calls.
- **D-08:** Procfile updated: remove `beat` process. Keep `worker` process for media/content queues only.

### n8n Publishing Approach
- **D-09:** n8n calls existing `backend/agents/publisher.py` logic via FastAPI callback endpoint — do NOT rebuild publishing in n8n nodes. The publisher.py already has working LinkedIn/X/Instagram httpx-based publishing from v1.0.
- **D-10:** n8n workflow for scheduled publishing: trigger on cron → call FastAPI endpoint that fetches due posts → for each post, call publisher.py → callback with result.

### Webhook Bridge Design
- **D-11:** New FastAPI route: `POST /api/n8n/callback` with HMAC-SHA256 signature verification. n8n signs payloads with a shared secret (`N8N_WEBHOOK_SECRET` in config.py).
- **D-12:** New FastAPI route: `POST /api/n8n/trigger/{workflow_name}` — internal endpoint for FastAPI to trigger n8n workflows programmatically via httpx POST.

### Workflow Visibility
- **D-13:** Workflow status shown inline on content/scheduling cards (not a separate page). Toast notifications for completion/failure events.

### Claude's Discretion
- n8n Docker Compose configuration details
- Specific n8n workflow JSON structure
- HMAC-SHA256 implementation details
- Error handling and retry logic for webhook failures
- Test structure and coverage approach

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Existing Celery Infrastructure
- `backend/celery_app.py` — Current Celery app factory, broker config, task includes
- `backend/celeryconfig.py` — All 7 beat schedule entries + task routing + queue definitions
- `backend/tasks/content_tasks.py` — All scheduled tasks that will migrate to n8n
- `backend/tasks/media_tasks.py` — Media tasks that stay in Celery

### Publishing System
- `backend/agents/publisher.py` — Real LinkedIn/X/Instagram publishing via httpx (reuse, don't rebuild)
- `backend/routes/platforms.py` — OAuth token management for social platforms

### Configuration
- `backend/config.py` — Settings dataclasses (add N8N config here)
- `backend/server.py` — FastAPI app, router registration, lifespan events
- `backend/Procfile` — Current 3-process deployment (web, worker, beat)

### Research
- `.planning/research/STACK.md` — n8n deployment recommendations, PostgreSQL requirement
- `.planning/research/ARCHITECTURE.md` — Sidecar integration pattern, webhook bridge design
- `.planning/research/PITFALLS.md` — Dual-execution risk, n8n queue mode worker health probe, webhook response mode pitfall

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `backend/agents/publisher.py` — Full LinkedIn/X/Instagram publishing with httpx. Reuse as-is from n8n callbacks.
- `backend/tasks/content_tasks.py:_run_scheduled_posts_inner()` — Extracted module-level function for testable scheduled post processing. Logic can inform n8n workflow design.
- `backend/tasks/content_tasks.py:run_async()` — Helper pattern for running async code in sync context.
- `backend/middleware/security.py` — Rate limiting + input validation middleware. Apply to n8n callback route.

### Established Patterns
- All config via `backend/config.py` dataclasses — new `N8nConfig` dataclass needed
- Route registration in `backend/server.py` — new n8n bridge router follows same pattern
- HMAC verification pattern similar to existing Stripe webhook verification in `backend/services/stripe_service.py`
- `from database import db` for all MongoDB access — n8n callback handler uses same pattern

### Integration Points
- `backend/server.py` — Mount new `n8n_bridge` router
- `backend/config.py` — Add `N8nConfig` dataclass (n8n URL, webhook secret, workflow IDs)
- `backend/Procfile` — Remove `beat` process, potentially add n8n container orchestration note
- `docker-compose.yml` — Add n8n + PostgreSQL services

</code_context>

<specifics>
## Specific Ideas

No specific requirements — research and architecture recommendations guide the approach. User trusts technical judgment on n8n infrastructure decisions.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 09-n8n-infrastructure-real-publishing*
*Context gathered: 2026-04-01*
