# Phase 9: n8n Infrastructure + Real Publishing - Research

**Researched:** 2026-04-01
**Domain:** n8n self-hosted orchestration, Celery-to-n8n cutover, FastAPI webhook bridge, idempotency, workflow status visibility
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** n8n runs as a separate Docker container (sidecar) with PostgreSQL 15 for queue mode. Not embedded in the FastAPI process.
- **D-02:** n8n communicates with FastAPI exclusively via webhooks (n8n→FastAPI callback) and HTTP triggers (FastAPI→n8n webhook POST). No shared Python process.
- **D-03:** Redis (existing) serves as n8n queue broker. PostgreSQL is new, dedicated to n8n.
- **D-04:** Hard cutover per job category — disable Celery beat entry before activating n8n schedule equivalent. Never run both simultaneously for the same task.
- **D-05:** Idempotency key on all scheduled-post publish operations — check `last_published_at` within 2-minute window to prevent duplicate social posts.
- **D-06:** 7 beat tasks migrate to n8n: `process_scheduled_posts`, `reset_daily_limits`, `refresh_monthly_credits`, `cleanup_old_jobs`, `cleanup_expired_shares`, `aggregate_daily_analytics`, `cleanup_stale_running_jobs`.
- **D-07:** `run_content_pipeline` and all `tasks.media_tasks.*` stay in Celery — they require Motor async context that can't be replicated in n8n HTTP calls.
- **D-08:** Procfile updated: remove `beat` process. Keep `worker` process for media/content queues only.
- **D-09:** n8n calls existing `backend/agents/publisher.py` logic via FastAPI callback endpoint — do NOT rebuild publishing in n8n nodes.
- **D-10:** n8n workflow for scheduled publishing: trigger on cron → call FastAPI endpoint that fetches due posts → for each post, call publisher.py → callback with result.
- **D-11:** New FastAPI route: `POST /api/n8n/callback` with HMAC-SHA256 signature verification. n8n signs payloads with a shared secret (`N8N_WEBHOOK_SECRET` in config.py).
- **D-12:** New FastAPI route: `POST /api/n8n/trigger/{workflow_name}` — internal endpoint for FastAPI to trigger n8n workflows programmatically via httpx POST.
- **D-13:** Workflow status shown inline on content/scheduling cards (not a separate page). Toast notifications for completion/failure events.

### Claude's Discretion

- n8n Docker Compose configuration details
- Specific n8n workflow JSON structure
- HMAC-SHA256 implementation details
- Error handling and retry logic for webhook failures
- Test structure and coverage approach

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.

</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| N8N-01 | n8n self-hosted deployment with Docker (`stable` tag) + PostgreSQL 15 queue mode | Docker Compose pattern, env vars, healthcheck probe verified from n8n queue mode docs |
| N8N-02 | n8n webhook bridge — FastAPI triggers n8n workflows via POST, n8n calls back via HMAC-SHA256 authenticated endpoint (`POST /api/n8n/callback`) | `webhook_service.py` existing `_sign_payload` pattern directly reusable; n8n webhook trigger/HTTP Request node patterns documented |
| N8N-03 | Celery beat tasks migrated to n8n workflows — publishing, analytics polling, credit resets, cleanup jobs | All 7 beat schedule entries in `celeryconfig.py` mapped to n8n cron triggers; FastAPI callback endpoints designed |
| N8N-04 | Hard Celery→n8n cutover protocol with idempotency keys on all publish operations (no dual execution) | `last_published_at` check pattern, cutover sequence documented, `celeryconfig.py` beat entries to disable identified |
| N8N-05 | Celery retained only for Motor-coupled media generation tasks (image/video rendering) | `tasks/media_tasks.py` confirmed Motor-coupled; worker queue config preserved |
| N8N-06 | User can see workflow status for in-progress operations (publishing countdown, analytics polling status) | SSE pattern from `routes/notifications.py` and `services/notification_service.py` already exists and can be extended with n8n callback events |

</phase_requirements>

---

## Summary

Phase 9 replaces Celery's beat scheduler with n8n as the external workflow orchestrator for all 7 scheduled/external-API tasks in ThookAI. The Celery worker process is retained exclusively for Motor-async-coupled media generation tasks. n8n runs as a sidecar Docker container with PostgreSQL 15 queue mode, communicating with FastAPI only over HTTP.

The FastAPI side requires two new endpoints: `POST /api/n8n/callback` (receives signed results from n8n) and `POST /api/n8n/trigger/{workflow_name}` (dispatches work to n8n). Both follow patterns already established in the codebase — `webhook_service.py` has the complete HMAC-SHA256 signing implementation, and `billing.py` has the inbound webhook verification model. The n8n callback route is the HMAC receiver; it verifies `N8N_WEBHOOK_SECRET` against the `X-ThookAI-Signature` header before processing results.

The hard cutover risk is dual execution: if Celery beat and n8n schedule both fire for the same domain, scheduled posts publish twice. The idempotency guard (check `last_published_at` within 2 minutes before calling `publisher.py`) is the primary defense. The Docker Compose changes (add n8n + postgres, remove `celery-beat`) and the Procfile change (remove `beat` line) must happen atomically as one deployment.

**Primary recommendation:** Build the n8n webhook bridge and Docker Compose config first (Wave 0), test with a single smoke-test workflow, then migrate tasks in beat-schedule order from least-risky (cleanup jobs) to most-critical (scheduled posts), disabling each Celery beat entry immediately before activating its n8n counterpart.

---

## Standard Stack

### Core

| Library / Tool | Version | Purpose | Why Standard |
|----------------|---------|---------|--------------|
| `n8nio/n8n` Docker image | `stable` tag | Visual workflow orchestration, cron schedules, webhook triggers, HTTP Request node for platform APIs | Already decided (D-01). `stable` tag always provides latest stable release without manual pin management |
| PostgreSQL 15 | `postgres:15-alpine` | n8n internal queue-mode database | SQLite is explicitly blocked by n8n for queue mode. PostgreSQL 15 is the minimum recommended version per n8n queue mode docs |
| Redis 7 | existing (redis:7-alpine) | n8n queue broker (BullMQ) | Already in `docker-compose.yml`. No new infra required |
| `httpx` | 0.28.1 (existing) | FastAPI→n8n HTTP trigger calls; n8n HTTP Request nodes call FastAPI callbacks | Already in `backend/requirements.txt` |
| Python `hmac` + `hashlib` | stdlib | HMAC-SHA256 verification of inbound n8n callbacks | No new dependency. Pattern already used in `backend/services/webhook_service.py` |

### Supporting

| Library / Tool | Version | Purpose | When to Use |
|----------------|---------|---------|-------------|
| `psycopg2-binary` | 2.9.x or `asyncpg` | PostgreSQL driver — only needed if FastAPI ever queries n8n's PostgreSQL directly (it should not) | DO NOT add to `requirements.txt` — FastAPI must not share the n8n PostgreSQL database |
| FastAPI `BackgroundTasks` | existing | For any fire-and-forget sub-5s tasks that remain after migration | Already available in FastAPI; no new package needed |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| n8n:stable Docker tag | Pinned version (e.g., 1.116.x) | Pinned version prevents surprise breaks but requires manual tag bumps every release. Use `stable` for this phase; pin only if a breaking change occurs during development |
| n8n queue mode (PostgreSQL) | n8n default mode (SQLite) | SQLite is unsupported for queue mode — multi-worker reliability requires PostgreSQL. Accepted cost: one new Docker service |
| HMAC-SHA256 on n8n callback | JWT bearer token | HMAC is stateless and matches the existing `X-ThookAI-Signature` header pattern already in `webhook_service.py`. JWT would require token management. HMAC is simpler and sufficient |

**Installation (additions to docker-compose.yml only — no new Python packages):**

```bash
# No new Python packages required for this phase.
# n8n runs as Docker container; HMAC uses stdlib.
# PostgreSQL is n8n-internal only; FastAPI does not connect to it.
```

---

## Architecture Patterns

### Recommended Project Structure

```
backend/
├── config.py              # ADD: N8nConfig dataclass (N8N_URL, N8N_WEBHOOK_SECRET, workflow IDs)
├── Procfile               # CHANGE: remove 'beat' line; keep 'worker' and 'web'
├── routes/
│   └── n8n_bridge.py      # NEW: POST /api/n8n/callback + POST /api/n8n/trigger/{workflow_name}
├── tasks/
│   ├── content_tasks.py   # CHANGE: remove 7 beat-scheduled tasks (keep run_content_pipeline,
│   │                      #         update_performance_intelligence, poll_post_metrics_*)
│   └── media_tasks.py     # UNCHANGED: all motor-coupled tasks stay
├── celeryconfig.py        # CHANGE: remove all 7 entries from beat_schedule dict
│                          #         keep task_routes for media and content queues
docker-compose.yml         # CHANGE: add n8n + postgres services; remove celery-beat service
.env.example               # CHANGE: add N8N_URL, N8N_WEBHOOK_SECRET, N8N_API_KEY
```

---

### Pattern 1: n8n Docker Compose (Queue Mode)

**What:** n8n sidecar container with PostgreSQL 15 in queue mode, sharing existing Redis.

**When to use:** This is the deployment topology for the entire phase — everything runs through this.

```yaml
# docker-compose.yml additions
  n8n:
    image: n8nio/n8n:stable
    restart: unless-stopped
    ports:
      - "5678:5678"
    environment:
      - DB_TYPE=postgresdb
      - DB_POSTGRESDB_HOST=postgres-n8n
      - DB_POSTGRESDB_PORT=5432
      - DB_POSTGRESDB_DATABASE=n8n
      - DB_POSTGRESDB_USER=n8n
      - DB_POSTGRESDB_PASSWORD=${N8N_POSTGRES_PASSWORD}
      - EXECUTIONS_MODE=queue
      - QUEUE_BULL_REDIS_HOST=redis
      - QUEUE_BULL_REDIS_PORT=6379
      - N8N_ENCRYPTION_KEY=${N8N_ENCRYPTION_KEY}
      - WEBHOOK_URL=${N8N_WEBHOOK_URL}  # public URL for inbound webhooks
      - N8N_BLOCK_ENV_ACCESS_IN_NODE=true  # security: Code nodes cannot read process.env
      - EXECUTIONS_DATA_MAX_AGE=336        # 14-day execution history pruning
      - EXECUTIONS_DATA_PRUNE_MAX_COUNT=10000
    depends_on:
      postgres-n8n:
        condition: service_healthy
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "wget", "--spider", "-q", "http://localhost:5678/healthz"]
      interval: 30s
      timeout: 10s
      retries: 3

  n8n-worker:
    image: n8nio/n8n:stable
    restart: unless-stopped
    command: worker
    environment:
      - DB_TYPE=postgresdb
      - DB_POSTGRESDB_HOST=postgres-n8n
      - DB_POSTGRESDB_PORT=5432
      - DB_POSTGRESDB_DATABASE=n8n
      - DB_POSTGRESDB_USER=n8n
      - DB_POSTGRESDB_PASSWORD=${N8N_POSTGRES_PASSWORD}
      - EXECUTIONS_MODE=queue
      - N8N_PROCESS_TYPE=worker          # CRITICAL: must be set on worker containers
      - QUEUE_BULL_REDIS_HOST=redis
      - QUEUE_BULL_REDIS_PORT=6379
      - N8N_ENCRYPTION_KEY=${N8N_ENCRYPTION_KEY}
      - N8N_BLOCK_ENV_ACCESS_IN_NODE=true
    depends_on:
      - n8n
      - redis
      - postgres-n8n

  postgres-n8n:
    image: postgres:15-alpine
    restart: unless-stopped
    environment:
      - POSTGRES_DB=n8n
      - POSTGRES_USER=n8n
      - POSTGRES_PASSWORD=${N8N_POSTGRES_PASSWORD}
    volumes:
      - n8n_postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U n8n"]
      interval: 10s
      timeout: 5s
      retries: 5
```

**Confidence:** HIGH — n8n queue mode env vars verified from official docs.

---

### Pattern 2: N8nConfig Dataclass

**What:** New configuration dataclass following the project's established `backend/config.py` pattern.

**When to use:** Any code that references n8n URLs, secrets, or workflow IDs must import from `settings.n8n`.

```python
# backend/config.py — new dataclass (follows established pattern)
@dataclass
class N8nConfig:
    """n8n workflow orchestration configuration"""
    n8n_url: str = field(default_factory=lambda: os.environ.get('N8N_URL', 'http://n8n:5678'))
    webhook_secret: str = field(default_factory=lambda: os.environ.get('N8N_WEBHOOK_SECRET', ''))
    api_key: Optional[str] = field(default_factory=lambda: os.environ.get('N8N_API_KEY'))
    # Workflow IDs populated after workflows are created in n8n UI
    workflow_scheduled_posts: Optional[str] = field(
        default_factory=lambda: os.environ.get('N8N_WORKFLOW_SCHEDULED_POSTS'))
    workflow_reset_daily_limits: Optional[str] = field(
        default_factory=lambda: os.environ.get('N8N_WORKFLOW_RESET_DAILY_LIMITS'))
    workflow_refresh_monthly_credits: Optional[str] = field(
        default_factory=lambda: os.environ.get('N8N_WORKFLOW_REFRESH_MONTHLY_CREDITS'))
    workflow_cleanup_old_jobs: Optional[str] = field(
        default_factory=lambda: os.environ.get('N8N_WORKFLOW_CLEANUP_OLD_JOBS'))
    workflow_cleanup_expired_shares: Optional[str] = field(
        default_factory=lambda: os.environ.get('N8N_WORKFLOW_CLEANUP_EXPIRED_SHARES'))
    workflow_aggregate_daily_analytics: Optional[str] = field(
        default_factory=lambda: os.environ.get('N8N_WORKFLOW_AGGREGATE_DAILY_ANALYTICS'))
    workflow_cleanup_stale_jobs: Optional[str] = field(
        default_factory=lambda: os.environ.get('N8N_WORKFLOW_CLEANUP_STALE_JOBS'))

    def is_configured(self) -> bool:
        return bool(self.n8n_url and self.webhook_secret)
```

Add `n8n: N8nConfig = field(default_factory=N8nConfig)` to the `Settings` dataclass.

---

### Pattern 3: HMAC-SHA256 Inbound Callback Verification

**What:** `POST /api/n8n/callback` verifies the `X-ThookAI-Signature` header before processing any result. Mirrors the existing `webhook_service.py` signing pattern.

**When to use:** Every inbound POST from n8n to FastAPI must go through this verification.

```python
# backend/routes/n8n_bridge.py
import hashlib
import hmac
import logging
from fastapi import APIRouter, HTTPException, Request
from config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/n8n", tags=["n8n"])


def _verify_n8n_signature(body_bytes: bytes, signature_header: str) -> bool:
    """Verify HMAC-SHA256 signature from n8n. Uses constant-time comparison."""
    if not settings.n8n.webhook_secret:
        logger.error("N8N_WEBHOOK_SECRET not configured — rejecting all n8n callbacks")
        return False
    expected = hmac.new(
        settings.n8n.webhook_secret.encode("utf-8"),
        body_bytes,
        hashlib.sha256,
    ).hexdigest()
    # hmac.compare_digest prevents timing attacks
    return hmac.compare_digest(expected, signature_header)


@router.post("/callback")
async def n8n_callback(request: Request):
    """
    Receive workflow completion callbacks from n8n.
    n8n signs payloads with N8N_WEBHOOK_SECRET → X-ThookAI-Signature header.
    """
    body_bytes = await request.body()
    signature = request.headers.get("X-ThookAI-Signature", "")

    if not _verify_n8n_signature(body_bytes, signature):
        logger.warning("n8n callback rejected: invalid signature")
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    import json
    payload = json.loads(body_bytes)
    workflow_type = payload.get("workflow_type")
    # Dispatch to appropriate handler based on workflow_type
    # ... handler routing logic ...
    return {"status": "accepted"}
```

**Confidence:** HIGH — `_sign_payload` from `webhook_service.py` (line 53-59) is the identical signing pattern, just inverted for verification.

---

### Pattern 4: FastAPI→n8n HTTP Trigger

**What:** FastAPI POSTs to n8n's webhook trigger URL to initiate a workflow. Returns immediately (fire-and-forget). Results arrive via the callback endpoint.

**When to use:** Any time FastAPI needs to dispatch a task to n8n programmatically.

```python
# backend/routes/n8n_bridge.py (continued)
import httpx

@router.post("/trigger/{workflow_name}")
async def trigger_n8n_workflow(workflow_name: str, payload: dict, _: str = Depends(get_current_user)):
    """
    Trigger an n8n workflow via webhook POST.
    Internal endpoint — not exposed to end users, only called by other FastAPI routes.
    """
    workflow_url = _get_workflow_url(workflow_name)
    if not workflow_url:
        raise HTTPException(status_code=404, detail=f"Unknown workflow: {workflow_name}")

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.post(
                workflow_url,
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            logger.error("n8n trigger failed for %s: %s", workflow_name, e)
            raise HTTPException(status_code=502, detail="n8n workflow trigger failed")
    return {"status": "triggered", "workflow": workflow_name}
```

**Confidence:** HIGH — n8n webhook trigger nodes accept plain POST JSON, verified from n8n webhook docs.

---

### Pattern 5: Idempotency Guard on Scheduled Posts

**What:** Before calling `publisher.py`, check that the post was not already published within the last 2 minutes. Prevents dual execution during the Celery→n8n cutover window and on n8n retry.

**When to use:** In the FastAPI endpoint that n8n calls during the scheduled-post publishing workflow.

```python
# backend/routes/n8n_bridge.py (or a new endpoint in content routes)
from datetime import datetime, timezone, timedelta

async def _is_recently_published(schedule_id: str, db_handle) -> bool:
    """Return True if this post was published within the last 2 minutes."""
    post = await db_handle.scheduled_posts.find_one({"schedule_id": schedule_id})
    if not post:
        return False
    published_at = post.get("published_at")
    if not published_at:
        return False
    if isinstance(published_at, str):
        published_at = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
    return (datetime.now(timezone.utc) - published_at) < timedelta(minutes=2)
```

**Confidence:** HIGH — `_run_scheduled_posts_inner` in `content_tasks.py` already has all DB access patterns; this is a direct extension.

---

### Pattern 6: n8n Workflow Response Mode — Webhook Contract

**What:** All n8n webhook nodes called by FastAPI MUST have response mode set to "When last node finishes" with a "Respond to Webhook" terminal node. Never use the default "Immediately" mode for workflows where FastAPI needs a result.

**When to use:** Configuring every n8n workflow that ThookAI triggers and acts on the response from.

```
n8n Workflow Structure (for each migrated task):

  [Cron Trigger / Webhook Trigger]
       ↓
  [HTTP Request node] → POST {N8N_BACKEND_URL}/api/n8n/execute/{task_name}
       ↓
  [IF node] → success / failure branch
       ↓
  [HTTP Request node] → POST {N8N_BACKEND_URL}/api/n8n/callback
       ↓
  [Respond to Webhook node] → returns {status, executed_at, result}

Response Mode on Webhook Trigger node: "When Last Node Finishes"
```

For cron-triggered workflows (which have no caller waiting), the callback to FastAPI is still needed to update MongoDB job status.

**Confidence:** HIGH — "Immediately" vs "When last node finishes" pitfall is verified from n8n webhook node docs and `.planning/research/PITFALLS.md` Pitfall 9.

---

### Pattern 7: Workflow Status Visibility via Existing SSE

**What:** n8n callbacks write workflow status events to MongoDB via `services/notification_service.py:create_notification()`. The frontend's existing SSE stream on `GET /api/notifications/stream` delivers status updates inline on content/scheduling cards.

**When to use:** Whenever n8n completes or fails a publishing or analytics task, it calls back to FastAPI, which calls `create_notification(user_id, type="workflow_status", ...)`.

This reuses:
- `backend/services/notification_service.py` — `create_notification()` already exists
- `backend/routes/notifications.py` — SSE stream already exists (`GET /api/notifications/stream`)
- Frontend — existing notification display components

No new backend SSE infrastructure needed. Only the `notification_type` enum needs a new value: `"workflow_status"`.

**Confidence:** HIGH — `notifications.py` SSE stream and `notification_service.py:create_notification()` are confirmed implemented and in production.

---

### Celery Beat Cutover Map

The table below maps each of the 7 Celery beat entries (from `celeryconfig.py`) to their n8n equivalent. Cutover order is least-risk first.

| Celery Beat Entry | Current Schedule | n8n Cron Equivalent | FastAPI Endpoint n8n Calls | Cutover Risk |
|-------------------|-----------------|---------------------|---------------------------|--------------|
| `cleanup-stale-jobs` | every 10 min | `*/10 * * * *` | `POST /api/n8n/execute/cleanup-stale-jobs` | LOW |
| `cleanup-old-jobs` | daily 02:00 UTC | `0 2 * * *` | `POST /api/n8n/execute/cleanup-old-jobs` | LOW |
| `cleanup-expired-shares` | daily 02:30 UTC | `30 2 * * *` | `POST /api/n8n/execute/cleanup-expired-shares` | LOW |
| `reset-daily-limits` | daily 00:00 UTC | `0 0 * * *` | `POST /api/n8n/execute/reset-daily-limits` | MEDIUM |
| `refresh-monthly-credits` | 1st of month 00:05 UTC | `5 0 1 * *` | `POST /api/n8n/execute/refresh-monthly-credits` | MEDIUM |
| `aggregate-daily-analytics` | daily 01:00 UTC | `0 1 * * *` | `POST /api/n8n/execute/aggregate-daily-analytics` | MEDIUM |
| `process-scheduled-posts` | every 5 min | `*/5 * * * *` | `POST /api/n8n/execute/process-scheduled-posts` | HIGH (idempotency guard required) |

**Recommended cutover order:** LOW → MEDIUM → HIGH. Never activate n8n schedule for a task until its Celery beat entry is removed from `celeryconfig.py`.

---

### Anti-Patterns to Avoid

- **Gradual migration (running both simultaneously):** If both `celery-beat` container AND n8n schedule are active for the same task, posts will be published twice. The Celery beat entry MUST be deleted from `celeryconfig.py` before the n8n workflow is published with its schedule trigger active.
- **Using n8n "Immediately" response mode:** Default webhook response returns empty 200 before the workflow executes. FastAPI will receive no result data. Always set "When Last Node Finishes" on trigger nodes that FastAPI acts on.
- **Rebuilding publisher logic in n8n nodes:** Decision D-09 is locked — n8n calls FastAPI which calls `publisher.py`. Do not attempt to replicate LinkedIn/X/Instagram API calls inside n8n HTTP Request nodes.
- **SQLite for n8n:** Unsupported in queue mode. PostgreSQL 15 is non-negotiable per n8n docs.
- **`N8N_PROCESS_TYPE=worker` missing on worker containers:** Worker containers start, pass health checks, but never dequeue jobs. Symptom: Redis Bull queue depth grows while worker active count stays zero. This env var is mandatory on every `n8n-worker` container.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| HMAC-SHA256 signature verification | Custom crypto implementation | Python stdlib `hmac.compare_digest()` | Already used in `webhook_service.py`; constant-time comparison prevents timing attacks |
| n8n workflow cron scheduling | Custom Python cron in FastAPI | n8n Cron Trigger node | n8n provides visual schedule editing, execution history, retry logic, and failure alerting |
| n8n queue broker | New queue infrastructure | Existing Redis 7 (already in stack) | n8n queue mode uses BullMQ on Redis — no new broker needed |
| Workflow execution status tracking | Custom status collection in MongoDB | n8n execution history + FastAPI callback events | n8n stores full execution history in PostgreSQL; callbacks write only final status to MongoDB |
| Retry logic for n8n→FastAPI calls | Custom retry code | n8n HTTP Request node built-in retry settings (max retries, wait between retries) | n8n handles retry at the workflow level; FastAPI callback endpoint just needs to be idempotent |
| SSE notifications for workflow status | New SSE endpoint | Existing `GET /api/notifications/stream` + `create_notification()` | SSE stream and notification service are fully implemented; just add `workflow_status` notification type |

**Key insight:** The n8n→FastAPI integration is thin by design. n8n handles scheduling, retries, and execution history. FastAPI handles business logic, database writes, and user auth. The boundary is HTTP + HMAC.

---

## Common Pitfalls

### Pitfall 1: Dual Execution — Celery Beat and n8n Both Active
**What goes wrong:** `process_scheduled_posts` fires from both Celery beat AND n8n cron. Posts are published twice to LinkedIn/X. `reset_daily_limits` runs twice.
**Why it happens:** n8n schedule activates the moment a workflow is published (not when Celery is stopped). Migration window creates a dual-execution period.
**How to avoid:** Delete the Celery beat entry from `celeryconfig.py` FIRST, deploy the Celery worker without it, THEN publish the n8n workflow with its schedule enabled. Never do the reverse.
**Warning signs:** Duplicate `published_at` timestamps in `db.scheduled_posts` within 2-5 seconds of each other.

### Pitfall 2: n8n Worker Not Entering Queue Mode
**What goes wrong:** n8n worker container starts and passes health checks but never processes queued webhooks. Redis Bull queue depth grows; worker active count stays zero.
**Why it happens:** `N8N_PROCESS_TYPE=worker` not set on the worker container. Environment variables fail to propagate if the worker service is copied from the main n8n service definition without updating this env var.
**How to avoid:** After deploying, run `redis-cli LLEN bull:jobs:wait` — if this grows while `GET http://n8n:5678/healthz` reports healthy workers, the worker is misconfigured. Add explicit env var assertion in the smoke test.
**Warning signs:** n8n UI shows executions stuck in "Queued" or "Starting soon" indefinitely.

### Pitfall 3: n8n Webhook "Immediately" Response Mode
**What goes wrong:** FastAPI triggers an n8n workflow and receives an empty 200. The actual workflow result is discarded. FastAPI marks the post as processed but the post was never published.
**Why it happens:** n8n's default response mode is "Immediately" — sends HTTP 200 to caller before the workflow executes.
**How to avoid:** Every n8n workflow triggered by FastAPI must have: (1) Webhook Trigger response mode = "When Last Node Finishes", and (2) a "Respond to Webhook" node as the terminal step returning `{status, result}`.
**Warning signs:** n8n execution logs show workflows completing with non-empty results, but FastAPI logs show empty response bodies from httpx POST calls.

### Pitfall 4: Missing `last_published_at` on Idempotency Check
**What goes wrong:** The 2-minute idempotency guard passes for the same post on parallel n8n retry + original execution because the guard checks `last_published_at` which is only written AFTER the publish succeeds. Two concurrent requests both see the field as null and both call `publisher.py`.
**Why it happens:** No pessimistic lock on the scheduled post document during publishing.
**How to avoid:** Use a MongoDB findOneAndUpdate with `$set: {status: "processing", processing_started_at: now}` as an atomic claim operation before calling `publisher.py`. If the post's status is already "processing" and `processing_started_at` is less than 5 minutes ago, skip. This is an optimistic lock on the status field.
**Warning signs:** Two entries in `db.scheduled_posts` with the same `schedule_id` and both showing `status: "published"`.

### Pitfall 5: Celery Worker Still Running Beat Schedule
**What goes wrong:** After removing beat entries from `celeryconfig.py`, the deployed Celery worker is still running an old cached version of `celeryconfig.py`. Beat tasks continue from the worker process (not from `celery-beat` container).
**Why it happens:** Render/Railway deployments may cache the old container image. `celery worker` only runs tasks, but the `PersistentScheduler` embedded option can cause the worker to also act as a beat scheduler if `--beat` flag is accidentally included.
**How to avoid:** Confirm the Procfile `worker:` line does NOT include `--beat`. After deployment, verify with `celery -A celery_app inspect active_queues` that no beat-scheduled tasks are visible.
**Warning signs:** `cleanup_stale_running_jobs` fires from the Celery worker even though the beat entry was removed from `celeryconfig.py`.

---

## Code Examples

### Verified Pattern: HMAC Signing (from `webhook_service.py` line 53-59)

```python
# Source: backend/services/webhook_service.py — _sign_payload()
import hashlib
import hmac

def _sign_payload(payload_bytes: bytes, secret: str) -> str:
    """Compute HMAC-SHA256 signature for a payload."""
    return hmac.new(
        secret.encode("utf-8"),
        payload_bytes,
        hashlib.sha256,
    ).hexdigest()

# For VERIFICATION (receiver side — n8n_bridge.py):
def _verify_n8n_signature(body_bytes: bytes, received_sig: str, secret: str) -> bool:
    expected = hmac.new(
        secret.encode("utf-8"),
        body_bytes,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, received_sig)  # constant-time
```

### Verified Pattern: Async DB Access (from `content_tasks.py` — `_run_scheduled_posts_inner`)

```python
# Source: backend/tasks/content_tasks.py — established Motor async pattern
from database import db

async def handle_n8n_publish_callback(schedule_id: str, result: dict) -> None:
    now = datetime.now(timezone.utc)
    if result.get("success"):
        await db.scheduled_posts.update_one(
            {"schedule_id": schedule_id},
            {"$set": {
                "status": "published",
                "published_at": now,
                "processed_at": now,
            }}
        )
```

### Verified Pattern: create_notification (from `services/notification_service.py`)

```python
# Source: backend/tasks/content_tasks.py — existing call pattern
from services.notification_service import create_notification

await create_notification(
    user_id=user_id,
    type="workflow_status",           # new type for n8n workflow events
    title=f"Your {platform} post was published",
    body=content_preview,
    metadata={
        "platform": platform,
        "schedule_id": schedule_id,
        "workflow_type": "process_scheduled_posts",
    },
)
```

### Verified Pattern: httpx fire-and-forget trigger

```python
# Source: backend/services/webhook_service.py — httpx POST pattern
import httpx

async def trigger_n8n_workflow(workflow_url: str, payload: dict) -> None:
    """Fire-and-forget trigger. Results arrive via /api/n8n/callback."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(workflow_url, json=payload)
            resp.raise_for_status()
    except httpx.HTTPStatusError as e:
        logger.error("n8n trigger failed: %s", e)
        # Do not raise — caller should not block on n8n availability
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Celery beat with `PersistentScheduler` for all cron tasks | n8n cron trigger nodes with visual execution history | Phase 9 (this phase) | Celery beat entries become observable in n8n UI; failed executions are visible without log tailing |
| `celery-beat` Docker container (3rd process) | Removed — n8n handles all scheduling | Phase 9 | Procfile shrinks from 3 processes to 2; Docker Compose gains n8n + postgres, removes celery-beat |
| `_publish_to_platform` called from Celery task in-process | `_publish_to_platform` called from FastAPI endpoint triggered by n8n HTTP Request node | Phase 9 | Publisher logic stays in Python/Motor; n8n only orchestrates the trigger timing and retry |
| No idempotency on publish operations | `processing_started_at` atomic claim + `last_published_at` 2-minute guard | Phase 9 | Prevents duplicate social posts on n8n retry or Celery/n8n overlap during cutover |

**Note on STACK.md discrepancy:** The v2.0 STACK.md research recommends removing Celery entirely. CONTEXT.md decision D-07 overrides this — Celery worker is retained for Motor-coupled media tasks (`tasks/media_tasks.py`). This is the correct decision for this codebase; the STACK.md recommendation was for a greenfield scenario.

---

## Open Questions

1. **n8n worker in cloud deployment (Render/Railway)**
   - What we know: n8n queue mode requires PostgreSQL + Redis + `N8N_PROCESS_TYPE=worker` on the worker container
   - What's unclear: Render and Railway may require separate service definitions for the n8n main process vs n8n worker. The docker-compose pattern works locally but production deployment topology on Render needs explicit service separation
   - Recommendation: The planner should add a task to verify the Render deployment supports multi-container Docker Compose, or document that n8n is docker-compose-local only (with Render running the FastAPI app separately)

2. **n8n → FastAPI internal URL resolution**
   - What we know: n8n HTTP Request nodes need to call back to FastAPI (`POST /api/n8n/callback`). In docker-compose, this is `http://backend:8001`. In production (Render), this is the public Render URL.
   - What's unclear: Whether the `WEBHOOK_URL` n8n env var and the backend callback URL should be the same or different variables
   - Recommendation: Add two separate env vars — `N8N_WEBHOOK_URL` (public URL for inbound webhooks FROM external) and `N8N_BACKEND_CALLBACK_URL` (URL for n8n to call FastAPI, may be internal Docker network address)

3. **n8n workflow IDs at first boot**
   - What we know: Workflow IDs are not known until workflows are created in the n8n UI or imported via JSON. The `N8nConfig` dataclass stores them as optional env vars.
   - What's unclear: Whether to use n8n's REST API to auto-create/import workflows at startup, or require manual workflow creation and ID entry
   - Recommendation: For Phase 9, manually create workflows in n8n UI and record IDs in `.env`. Document the workflow JSON for reproducibility. Auto-import via REST API is a Phase 9+ improvement.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Docker | n8n + PostgreSQL containers | Not detected on this machine | — | Must be available in deployment environment (Render/Railway has Docker) |
| PostgreSQL | n8n internal state | psql 14.12 (Homebrew) | 14.12 | n8n requires PostgreSQL for queue mode; no fallback |
| Redis 7 | n8n queue broker | Not probed (uses docker-compose) | — | Already in docker-compose.yml; available in deployment |
| Python 3.11 | FastAPI backend | 3.13.5 (local) | 3.13.5 | `runtime.txt` pins 3.11 for Render deployment |
| `hmac` (stdlib) | HMAC-SHA256 verification | Built into Python | stdlib | No fallback needed |
| `httpx` 0.28.1 | FastAPI→n8n trigger | In requirements.txt | 0.28.1 | Already installed |

**Missing dependencies with no fallback:**
- Docker: Required to run n8n and PostgreSQL containers. Not installed on this dev machine, but confirmed available on Render/Railway deployment targets. Development testing of n8n workflows requires Docker to be installed locally.

**Missing dependencies with fallback:**
- None that affect Phase 9 core logic.

**Note on local development:** n8n can be run via `docker run` or `docker-compose up n8n` for local workflow development. Without Docker locally, n8n workflow JSON can be authored in n8n Cloud (free tier) and exported for self-hosted deployment.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.0.0 + pytest-asyncio 0.23.0 |
| Config file | `backend/pytest.ini` (`asyncio_mode = auto`) |
| Quick run command | `cd backend && pytest tests/test_n8n_bridge.py -x` |
| Full suite command | `cd backend && pytest tests/ -x` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| N8N-01 | n8n container starts and `/healthz` returns 200 | smoke | Manual docker-compose smoke test | Wave 0 task |
| N8N-02 | `POST /api/n8n/callback` with valid HMAC-SHA256 returns 200; invalid sig returns 401 | unit | `pytest tests/test_n8n_bridge.py::TestN8nCallback -x` | Wave 0 task |
| N8N-02 | `POST /api/n8n/trigger/{workflow_name}` dispatches httpx POST to correct n8n URL | unit | `pytest tests/test_n8n_bridge.py::TestN8nTrigger -x` | Wave 0 task |
| N8N-03 | All 7 beat entries removed from `celeryconfig.py` | unit | `pytest tests/test_celery_config.py -x` | Wave 0 task |
| N8N-03 | n8n cron workflows fire FastAPI endpoints matching old task logic | integration | Manual n8n execution test + DB state check | Manual only (requires running n8n) |
| N8N-04 | Submitting same publish operation twice within 2 min produces exactly one post | unit | `pytest tests/test_n8n_bridge.py::TestIdempotency -x` | Wave 0 task |
| N8N-04 | Celery beat process removed from Procfile | unit | `pytest tests/test_procfile.py -x` | Wave 0 task |
| N8N-05 | `tasks/media_tasks.py` tasks are unchanged; Celery worker still processes them | unit | `pytest tests/test_media_tasks_assets.py -x` | Exists |
| N8N-06 | `create_notification()` called with `type=workflow_status` on n8n callback | unit | `pytest tests/test_n8n_bridge.py::TestWorkflowStatus -x` | Wave 0 task |

### Sampling Rate

- **Per task commit:** `cd backend && pytest tests/test_n8n_bridge.py -x`
- **Per wave merge:** `cd backend && pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `backend/tests/test_n8n_bridge.py` — covers N8N-02 (HMAC verification), N8N-04 (idempotency), N8N-06 (workflow status notification)
- [ ] `backend/tests/test_celery_config.py` — covers N8N-03 (all 7 beat entries removed), N8N-05 (media task routes preserved)
- [ ] `backend/tests/test_procfile.py` — covers N8N-04 (beat process removed from Procfile)
- [ ] `backend/routes/n8n_bridge.py` — the route module itself (new file)
- [ ] `backend/config.py` additions — `N8nConfig` dataclass + `Settings.n8n` field

---

## Project Constraints (from CLAUDE.md)

These directives govern all implementation in this phase.

| Constraint | Applies To |
|------------|------------|
| Never commit directly to `main` — branch from `dev`, PR targets `dev` | Git workflow for all Phase 9 files |
| Branch naming: `feat/n8n-infrastructure` or `infra/n8n-celery-cutover` | Branch creation |
| Never hardcode secrets — use `settings.n8n.*` from `backend/config.py` | `N8N_WEBHOOK_SECRET`, `N8N_API_KEY`, `N8N_POSTGRES_PASSWORD` |
| Never introduce new Python packages without adding to `backend/requirements.txt` | No new packages expected; verify before adding |
| Never use `os.environ.get()` directly in route/agent/service files — always `from config import settings` | `n8n_bridge.py` router must use `settings.n8n.webhook_secret` |
| Database access: always `from database import db` with Motor async | All callback handlers that write to MongoDB |
| After any change to `backend/agents/`, verify full pipeline still flows | N/A for Phase 9 (no agent changes) |
| Config pattern: all settings via `backend/config.py` dataclasses | `N8nConfig` dataclass required |
| After any change to billing routes, flag for human review | N/A for Phase 9 |

---

## Sources

### Primary (HIGH confidence)
- `.planning/research/STACK.md` — n8n deployment recommendations, PostgreSQL requirement, Redis queue mode
- `.planning/research/PITFALLS.md` — Pitfalls 1, 2, 9 directly apply to Phase 9; dual execution, worker queue mode, webhook response mode
- `backend/services/webhook_service.py` — HMAC-SHA256 signing pattern (lines 53-59), `_sign_payload` and `_deliver_webhook`
- `backend/tasks/content_tasks.py` — all 7 task implementations, `_run_scheduled_posts_inner`, `run_async` helper
- `backend/celeryconfig.py` — complete beat_schedule (7 entries) + task_routes to preserve
- `backend/routes/notifications.py` — SSE pattern for workflow status delivery
- [n8n Queue Mode docs](https://docs.n8n.io/hosting/scaling/queue-mode/) — PostgreSQL required, SQLite unsupported, worker architecture, `N8N_PROCESS_TYPE=worker`
- [n8n Webhook Node docs](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.webhook/) — "When last node finishes" response mode

### Secondary (MEDIUM confidence)
- `.planning/research/ARCHITECTURE.md` — sidecar integration topology, component responsibility map
- `backend/celery_app.py` — Celery app factory; confirmed `app = celery_app` alias required for CLI
- `backend/Procfile` — current 3-line deployment; `beat` line to be removed
- `docker-compose.yml` — current 5-service compose; n8n + postgres additions, celery-beat removal

### Tertiary (LOW confidence)
- n8n workflow JSON export format — verified patterns exist but specific ThookAI workflow JSON must be authored during implementation

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all tools are pre-decided (CONTEXT.md), confirmed in STACK.md and official docs
- Architecture: HIGH — all patterns derived from existing codebase code (webhook_service.py, content_tasks.py, notifications.py); n8n sidecar pattern confirmed
- Pitfalls: HIGH — dual execution, queue mode, webhook response mode pitfalls verified in PITFALLS.md from official n8n docs + community reports

**Research date:** 2026-04-01
**Valid until:** 2026-05-01 (n8n releases minor versions weekly but breaking changes are rare on `stable` tag)
