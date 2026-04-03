# Stack Research

**Domain:** AI Content Operating System — v2.0 new integrations only
**Researched:** 2026-04-01
**Confidence:** MEDIUM-HIGH (verified with official docs and PyPI where possible; some integration patterns are inferred from ecosystem evidence)

---

## Context: What This Research Covers

v1.0 stack (FastAPI, Motor, React, Redis, Celery, Pinecone, Anthropic, fal.ai, Luma, Runway, HeyGen, ElevenLabs, Stripe, Cloudflare R2) is validated and NOT re-researched here.

This file covers only the **new additions** required for v2.0:

1. n8n (self-hosted) replacing Celery for workflow orchestration
2. LightRAG knowledge graph layer (complementing Pinecone)
3. Multi-model media orchestration engine + Remotion compositor
4. Strategist Agent intelligence layer
5. Obsidian vault integration for Scout agent

---

## Recommended Stack

### 1. n8n — Workflow Orchestration (Celery Replacement)

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| `n8nio/n8n` (Docker) | `stable` tag | Visual workflow automation, scheduled tasks, webhook triggers, platform OAuth publishing | Replaces Celery's opaque task graph with inspectable, debuggable workflows. Built-in nodes for LinkedIn, Twitter, Instagram OAuth publishing eliminate bespoke Python publisher code. Queue mode with Redis + PostgreSQL matches existing infra. |
| PostgreSQL 15 | 15-alpine | n8n persistent storage | SQLite is explicitly unsupported for n8n queue mode. PostgreSQL required for multi-worker scaling and reliable write concurrency. Existing MongoDB remains for ThookAI application data — PostgreSQL is dedicated to n8n internal state only. |
| Redis 7 | existing | n8n queue broker + result backend | Already in stack. n8n queue mode uses Redis as job broker identical to Celery. No new infra needed. |

**Integration pattern with FastAPI:**

FastAPI triggers n8n workflows via HTTP POST to n8n webhook URLs using `httpx`. This is a fire-and-forget call — FastAPI posts a JSON payload (job_id, user_id, platform, content) and n8n handles the workflow. n8n calls back to FastAPI via HTTP Request node when the step completes, updating job status in MongoDB through a dedicated internal callback endpoint.

No Python SDK needed — the n8n REST API (`POST /api/v1/workflows/{id}/execute`) and Webhook Trigger node are sufficient. Use the webhook trigger for 90% of cases; the REST API only for privileged internal triggers.

**What n8n replaces:**
- `backend/tasks/content_tasks.py` `process_scheduled_posts` task
- `backend/tasks/content_tasks.py` `reset_daily_limits` task
- `backend/tasks/content_tasks.py` `refresh_monthly_credits` task
- `backend/tasks/content_tasks.py` `cleanup_old_jobs` task
- `backend/tasks/content_tasks.py` `aggregate_daily_analytics` task
- `backend/agents/publisher.py` direct platform calls → replaced by n8n LinkedIn/Twitter/Instagram nodes

**What stays in Python/Celery:**
Nothing. Celery is fully retired. FastAPI's own `BackgroundTasks` handles short-lived inline jobs (< 5s). n8n handles everything scheduled or long-running.

**Confidence:** MEDIUM. n8n's queue mode architecture is well-documented and production-proven. The FastAPI ↔ n8n webhook integration pattern is community-validated. Risk area: n8n's native LinkedIn/Instagram nodes may have OAuth scope gaps — verify before relying on them for publishing.

---

### 2. LightRAG — Knowledge Graph Layer

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| `lightrag-hku` | 1.4.12 (latest as of 2026-03-27) | Entity/relationship extraction from approved content, multi-hop retrieval for Thinker agent | Dedicated graph-RAG library with dual-level retrieval (specific + abstract). Complements Pinecone (similarity search) with relationship traversal. Has built-in FastAPI server, MongoDB storage backend, and async Python API. Published in EMNLP 2025 — academic provenance with active maintenance. |
| NetworkXStorage | built-in | Graph storage for development/single-node | In-memory graph backend for local dev and low-volume prod. No additional infra. |
| Neo4j | 5.x (if scaling) | Graph storage for production at scale | Switch from NetworkXStorage when graph exceeds ~100k entities. Deferred — start with NetworkXStorage. |

**Storage configuration for ThookAI:**

Use LightRAG's MongoDB storage backends exclusively to avoid a new database:
- `MongoKVStorage` — document chunks, LLM cache (MongoDB collection prefix: `lg_kv_`)
- `MongoDocStatusStorage` — ingestion tracking (prefix: `lg_doc_`)
- `NanoVectorDBStorage` (built-in) — embeddings in local file store initially, migrate to `PGVectorStorage` if needed

**Do NOT use** `MongoVectorDBStorage` — it requires MongoDB Atlas Vector Search, which is not the current deployment target. Use `NanoVectorDBStorage` (file-based, zero infra) for vectors, since Pinecone already handles production-scale similarity search.

**Deployment pattern:**

Run LightRAG as a sidecar FastAPI service (`lightrag-server`) alongside the main ThookAI FastAPI app. LightRAG exposes endpoints at `http://lightrag:9621`. The Thinker agent calls `POST /query` with `mode: "hybrid"` to get multi-hop context. Document ingestion (`POST /documents/text`) is called from `agents/learning.py` when content is approved.

**Why not integrate LightRAG inline into the ThookAI process:** LightRAG's server runs Gunicorn+Uvicorn multi-process for LLM calls which can run 10-150 seconds. Running it inline would exhaust ThookAI's own Uvicorn worker pool. Sidecar pattern keeps resource budgets separate.

**Python async interface:**

```python
# Calling LightRAG from Thinker agent
import httpx

async def query_knowledge_graph(user_id: str, query: str) -> str:
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            "http://lightrag:9621/query",
            json={"query": query, "mode": "hybrid"},
            headers={"X-API-Key": settings.lightrag.api_key}
        )
        return resp.json()["response"]
```

**Confidence:** MEDIUM. LightRAG 1.4.12 is actively maintained with MongoDB backends confirmed. The sidecar pattern is standard and avoids event-loop contention. Risk: LightRAG's graph extraction quality depends on the LLM used for entity extraction — use `claude-sonnet-4-20250514` for extraction to maintain consistent persona voice.

---

### 3. Multi-Model Media Orchestration

#### 3a. fal.ai — Extended Model Coverage

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| `fal-client` | 0.13.2 (latest 2026-03-24) | Access to image, video, and 3D models not covered by dedicated providers | Already in stack. Async via `fal.run_async()`. Central routing hub for models without dedicated SDKs. |

**No version change needed.** The existing `fal-client` at 0.10.0 should be upgraded to 0.13.2 for the async improvements and queue status streaming.

#### 3b. Remotion — Video Compositor

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| `remotion` | 4.0.x (4.0.441 as of 2026-03-28) | Assemble generated media assets (images, audio, overlays, typography) into final video | The only mature React-based video composition framework with Node.js SSR API. Allows component-driven assembly — each content type (talking-head, carousel, static-with-text) is a Remotion composition. Renders via `renderMedia()` in the existing `remotion-service/` directory. |
| `@remotion/renderer` | same as above | Node.js render API (`renderMedia`, `renderStill`, `renderFrames`) | Required peer of `remotion` for server-side rendering. |

**Key architecture decision:**

The existing `remotion-service/` is an Express.js service. It should expose:
- `POST /render/video` — accepts composition name + inputProps → renders MP4 → uploads to R2 → returns URL
- `POST /render/still` — accepts composition name + inputProps → renders PNG → uploads to R2 → returns URL

The FastAPI backend calls this service via `httpx`. The render service is fire-and-forget via a Celery (now n8n) task — FastAPI posts the job, n8n polls the render endpoint, R2 URL is written back to MongoDB when complete.

**Licensing note:** Remotion requires a Company License for SaaS use in organizations with 4+ people. From Remotion 5.0 (anticipated), telemetry with a `licenseKey` is mandatory for commercial automators. Budget for this. The existing `remotion-service/` implementation should add the `licenseKey` to all `renderMedia()` calls before launch.

**Confidence:** HIGH. Remotion is the established standard for programmatic React video. The existing service directory confirms the pattern is already chosen. Version 4.0.441 is confirmed active via npm.

---

### 4. Strategist Agent — Intelligence Layer

No new libraries. The Strategist Agent is a new Python agent (`backend/agents/strategist.py`) that orchestrates existing services:

| Data source | Access method | What it provides |
|-------------|--------------|-----------------|
| LightRAG | `httpx` → `POST /query` | Entity graph patterns, topic relationships, what angles have been used |
| Pinecone | existing `vector_store.py` | Similar past content, style exemplars |
| MongoDB `persona_engines` | existing `db` | Voice fingerprint, content_identity, performance_intelligence |
| Obsidian vault | new `ObsidianClient` (see §5) | User's own research notes, bookmarked articles, ideas |
| Real analytics | existing analytics service | Which post formats, topics, times perform best |

The Strategist calls all sources, synthesizes with `claude-sonnet-4-20250514`, and writes recommendation objects to `db.strategy_recommendations`. n8n triggers the Strategist on a schedule (daily) and also after analytics ingestion events.

**No new packages.** All synthesis is via the existing `LlmClient`. The only new code is orchestration logic.

**Confidence:** HIGH. This is a pure composition of existing services, not a new technology.

---

### 5. Obsidian Vault Integration

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Obsidian Local REST API (community plugin) | current (maintained by coddingtonbear) | Read user's Obsidian vault notes, search, retrieve tagged content | Provides authenticated HTTPS REST API at `https://127.0.0.1:27124`. The Scout agent calls it to enrich topic research with the user's own notes and bookmarks. |
| `httpx` (async) | existing in stack | HTTP client for calling the Obsidian REST API | Already in stack (`httpx 0.28.1`). Use `verify=False` or pass the Obsidian self-signed cert. |

**Integration approach:**

Create `backend/services/obsidian_client.py` — a thin async wrapper around the Obsidian Local REST API. Scout agent calls it optionally (feature-gated by `OBSIDIAN_API_KEY` env var presence). If the user hasn't configured Obsidian, Scout falls back to Perplexity as today.

```python
# backend/services/obsidian_client.py (sketch)
class ObsidianClient:
    base_url = "https://127.0.0.1:27124"

    async def search(self, query: str) -> list[dict]:
        # GET /search/simple/?q={query}&contextLength=200

    async def get_note(self, path: str) -> str:
        # GET /vault/{path}
```

**What NOT to use:**
- `obsidian-cli` Python PyPI package — it wraps local file system access, not the REST API. It does not work for a deployed server scenario where Obsidian runs on the user's machine.
- Obsidian's official CLI (v1.12+, released Feb 2026) — designed for terminal automation on the user's machine, not for remote server access. REST API is the correct approach for ThookAI's server-side Scout agent.

**Important constraint:** The Obsidian Local REST API runs on the user's machine (`127.0.0.1:27124`). A deployed ThookAI server cannot call it directly. The realistic integration path for v2.0 is:
1. User self-hosts ThookAI or runs it locally, OR
2. The user's machine runs an ngrok/Cloudflare Tunnel that exposes the Obsidian REST API to a stable URL, which they register in ThookAI settings as `OBSIDIAN_BASE_URL`

Store `OBSIDIAN_BASE_URL` and `OBSIDIAN_API_KEY` in `backend/config.py` under a new `ObsidianConfig` dataclass. Make the feature entirely optional and gracefully degrade when absent.

**Confidence:** MEDIUM. The Local REST API plugin is actively maintained and the integration pattern is straightforward. The network topology constraint (user's machine vs. server) is a real limitation that must be communicated to users. For cloud deployments, this feature requires a tunnel setup.

---

## Supporting Libraries — New Additions Only

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `lightrag-hku` | 1.4.12 | LightRAG core — graph extraction, query, document ingestion | Add to `backend/requirements.txt`. Run as separate sidecar service. |
| `fal-client` | 0.13.2 | fal.ai model access (upgrade from 0.10.0) | Already in requirements — bump version only |
| `httpx` | 0.28.1 (existing) | Async HTTP client for LightRAG sidecar, Obsidian, n8n webhooks, Remotion service | Already in stack. No change. |

**No new npm packages** for the Remotion service — it already exists. Upgrade `remotion` and `@remotion/renderer` in `remotion-service/package.json` to 4.0.441.

---

## Installation

```bash
# Backend: add to backend/requirements.txt
lightrag-hku==1.4.12
# (fal-client already present — bump to 0.13.2)

# Remotion service: in remotion-service/
npm install remotion@4.0.441 @remotion/renderer@4.0.441

# n8n: run via Docker Compose (no Python package)
# docker-compose.yml addition — see Architecture section
```

---

## Alternatives Considered

| Recommended | Alternative | Why Not |
|-------------|-------------|---------|
| n8n (self-hosted Docker) | Temporal.io | Temporal is powerful but Go-based and heavyweight; n8n has built-in platform OAuth nodes that eliminate custom publisher code |
| n8n replacing Celery | Keep Celery, add n8n alongside | Two task systems create synchronization complexity and double the infra. Clean cut is better. |
| LightRAG sidecar FastAPI | Inline LightRAG in ThookAI process | LightRAG's LLM calls (entity extraction) are slow and CPU-bound; inline risks blocking ThookAI's async event loop |
| LightRAG + NetworkXStorage | GraphRAG (Microsoft) | GraphRAG requires Azure and is 10x slower to build; LightRAG is designed for fast incremental ingestion |
| LightRAG + NetworkXStorage | LangChain GraphRAG | LangChain adds abstraction layers with version instability; lightrag-hku is standalone and simpler |
| Pinecone (existing) + LightRAG | Replace Pinecone with LightRAG vectors | LightRAG's MongoVectorDBStorage requires Atlas — not current target. Pinecone stays for embedding similarity; LightRAG adds graph traversal. Complementary, not competitive. |
| Obsidian Local REST API | Obsidian official CLI | Official CLI runs on user's machine (terminal commands), not callable from a deployed server. REST API is the only viable remote integration. |
| Remotion (existing service) | FFmpeg-based assembly | FFmpeg requires imperative timeline programming; Remotion compositions are component-driven and match the existing service architecture |
| n8n:stable Docker tag | Pinned version (e.g., 1.116.x) | n8n releases minor versions weekly; :stable always gives the latest stable without manual tag management. Pin to specific version only if a breaking change occurs. |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| SQLite for n8n | Incompatible with queue mode (multi-worker); file locking causes write failures under concurrent load | PostgreSQL 15 (dedicated to n8n internal state) |
| `MongoVectorDBStorage` in LightRAG | Requires MongoDB Atlas Vector Search — not available on standard MongoDB Community or Atlas free tier | `NanoVectorDBStorage` (built-in file-based) for vectors; Pinecone for production-scale similarity |
| `obsidian-cli` PyPI package | Wraps local filesystem access, not the REST API; will not work when ThookAI is deployed remotely | `obsidian-local-rest-api` plugin + custom `httpx` client |
| Celery alongside n8n | Creates two competing task systems with no clear ownership; operational complexity doubles | Remove Celery entirely; use n8n for all scheduled/long-running tasks |
| `n8n:latest` Docker tag | Being phased out in n8n v2.0 breaking changes | Use `n8n:stable` |
| Remotion Lambda | Vendor lock-in to AWS; adds billing complexity; existing `remotion-service/` is already a self-hosted render server | `@remotion/renderer` in the existing Express service |
| Inline LightRAG in backend process | LightRAG entity extraction uses LLM calls (10-150s); running inline blocks FastAPI async workers | Sidecar service communicating over localhost HTTP |

---

## Integration Points With Existing Stack

| New Component | Connects To | How |
|--------------|-------------|-----|
| n8n | Redis (existing) | Broker for queue mode — no config change needed |
| n8n | PostgreSQL (new, dedicated) | n8n internal DB — separate from MongoDB |
| n8n | MongoDB (existing) | n8n HTTP Request node calls FastAPI endpoints which read/write MongoDB |
| n8n | LinkedIn/X/Instagram OAuth | n8n native nodes replace `backend/agents/publisher.py` |
| LightRAG sidecar | MongoDB (existing) | Uses MongoKVStorage + MongoDocStatusStorage on existing connection |
| LightRAG sidecar | `backend/agents/thinker.py` | Thinker calls `POST /query` via httpx |
| LightRAG sidecar | `backend/agents/learning.py` | Learning calls `POST /documents/text` after content approval |
| Remotion service | Cloudflare R2 (existing) | Render service uploads output to R2 using existing boto3 config |
| Remotion service | FastAPI backend | FastAPI POSTs render jobs; n8n polls completion; R2 URL stored in MongoDB |
| Obsidian client | `backend/agents/scout.py` | Scout calls ObsidianClient.search() before Perplexity |
| Strategist agent | All above | Orchestrates LightRAG + Pinecone + persona + analytics |

---

## Version Compatibility

| Package | Compatible With | Notes |
|---------|----------------|-------|
| `lightrag-hku==1.4.12` | Python 3.10+ | ThookAI uses Python 3.11.11 — compatible |
| `fal-client==0.13.2` | Python >=3.8 | Upgrade from 0.10.0; async API is backward-compatible |
| `remotion@4.0.441` | Node.js 18+ | `remotion-service/` already targets Node 18 |
| n8n:stable | PostgreSQL 13+, Redis 7+ | PostgreSQL 15 recommended; Redis 7 already in stack |
| `lightrag-hku[api]` | FastAPI already in requirements | LightRAG's API server pins its own FastAPI version internally; run it in an isolated venv/container to avoid conflicts with ThookAI's FastAPI version |

**Critical compatibility note:** Install LightRAG in its own virtual environment or Docker container. It pins internal dependencies (including its own FastAPI version) that may conflict with ThookAI's `fastapi==0.110.1`. The sidecar Docker deployment naturally handles this isolation.

---

## Sources

- [lightrag-hku on PyPI](https://pypi.org/project/lightrag-hku/) — Version 1.4.12 confirmed, storage backends verified (HIGH confidence)
- [HKUDS/LightRAG GitHub](https://github.com/HKUDS/LightRAG) — Architecture, MongoDB storage options (HIGH confidence)
- [LightRAG API README](https://github.com/HKUDS/LightRAG/blob/main/lightrag/api/README.md) — FastAPI server deployment, workspace isolation (HIGH confidence)
- [fal-client on PyPI](https://pypi.org/project/fal-client/) — Version 0.13.2, async capabilities (HIGH confidence)
- [Remotion SSR docs](https://www.remotion.dev/docs/ssr) — renderMedia(), Node.js API (HIGH confidence)
- [Remotion licensing docs](https://www.remotion.dev/docs/licensing/) — Commercial SaaS requirements (HIGH confidence)
- [n8n Docker Hub](https://hub.docker.com/r/n8nio/n8n) — :stable vs :latest tags (HIGH confidence)
- [n8n queue mode docs](https://docs.n8n.io/hosting/scaling/queue-mode/) — PostgreSQL requirement confirmed (HIGH confidence)
- [obsidian-local-rest-api GitHub](https://github.com/coddingtonbear/obsidian-local-rest-api) — API endpoints, auth, HTTPS on 27124 (HIGH confidence)
- [n8n REST API docs](https://docs.n8n.io/api/) — Webhook trigger vs management API (HIGH confidence)
- [LightRAG multi-hop issue #1629](https://github.com/HKUDS/LightRAG/issues/1629) — Hybrid query mode for multi-hop retrieval (MEDIUM confidence)
- WebSearch results for n8n + FastAPI integration patterns — Multiple corroborating sources (MEDIUM confidence)

---

*Stack research for: ThookAI v2.0 — Intelligent Content Operating System*
*Researched: 2026-04-01*
