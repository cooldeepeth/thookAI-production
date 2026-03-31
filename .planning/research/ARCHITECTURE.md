# Architecture Research

**Domain:** AI Content Operating System — n8n + LightRAG + Multi-Model Media Orchestration + Strategist Agent integration onto existing FastAPI platform
**Researched:** 2026-04-01
**Confidence:** HIGH (core integration patterns verified via official docs; specific deployment topology is MEDIUM — ThookAI-specific)

---

## Standard Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        REACT FRONTEND (Vercel)                           │
│  ┌──────────────┐  ┌──────────────────┐  ┌──────────────────────────┐   │
│  │ Content       │  │ Strategy         │  │ Media Preview /          │   │
│  │ Studio        │  │ Dashboard (NEW)  │  │ Progress Tracker         │   │
│  └──────┬───────┘  └────────┬─────────┘  └──────────┬───────────────┘   │
└─────────┼────────────────────┼───────────────────────┼───────────────────┘
          │ REST / SSE          │ SSE push              │ polling
┌─────────▼────────────────────▼───────────────────────▼───────────────────┐
│                       FASTAPI BACKEND (Render)                            │
│                                                                           │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │               EXISTING ROUTES (unchanged)                           │  │
│  │  auth / onboarding / content / persona / billing / agency / ...    │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                                                                           │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │               NEW V2.0 ROUTES                                       │  │
│  │  POST /api/n8n/trigger      — enqueue job to n8n                   │  │
│  │  POST /api/n8n/callback     — receive job result from n8n          │  │
│  │  GET  /api/strategy         — Strategist Agent recommendations     │  │
│  │  POST /api/media/orchestrate — kick off multi-model media job      │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                                                                           │
│  ┌───────────────────────────────────────────────────────────────────┐   │
│  │               AGENT PIPELINE (LangGraph orchestrator)              │   │
│  │  Commander → Scout (+ Obsidian) → Thinker (+ LightRAG) →          │   │
│  │  Writer → QC                                                       │   │
│  └────────────────────────────┬──────────────────────────────────────┘   │
│                               │                                           │
│  ┌────────────────────────────▼──────────────────────────────────────┐   │
│  │               SERVICES LAYER                                       │   │
│  │  lightrag_service.py (NEW)  |  media_orchestrator.py (NEW)        │   │
│  │  strategist_service.py (NEW)|  obsidian_service.py (NEW)          │   │
│  │  llm_client / vector_store / stripe / social_analytics (existing) │   │
│  └────────────────────────────────────────────────────────────────────┘  │
│                                                                           │
│  ┌─────────────────────────────────────────────────────────────────────┐ │
│  │  TASKS LAYER (Celery RETAINED for fast in-process tasks)            │ │
│  │  media_tasks.py (generate_image, generate_video)                   │ │
│  │  analytics feedback tasks (24h / 7d polling)                       │ │
│  └─────────────────────────────────────────────────────────────────────┘ │
└────────────────────────────────────┬──────────────────────────────────────┘
                                     │ webhooks / HTTP triggers
         ┌───────────────────────────▼──────────────────────────────────────┐
         │               n8n ORCHESTRATION LAYER (self-hosted Docker)       │
         │                                                                  │
         │  ┌──────────────────────┐  ┌──────────────────────────────────┐  │
         │  │ Workflow: Publishing  │  │ Workflow: Scheduled Posts        │  │
         │  │  LinkedIn / X / IG   │  │  (replaces Celery beat)          │  │
         │  └──────────────────────┘  └──────────────────────────────────┘  │
         │  ┌──────────────────────┐  ┌──────────────────────────────────┐  │
         │  │ Workflow: Analytics  │  │ Workflow: Strategist Trigger      │  │
         │  │  Ingestion (24h/7d)  │  │  (nightly, trend detection)      │  │
         │  └──────────────────────┘  └──────────────────────────────────┘  │
         │  ┌──────────────────────┐  ┌──────────────────────────────────┐  │
         │  │ Workflow: Credit /   │  │ Workflow: Media Assembly          │  │
         │  │  Maintenance cron    │  │  (Remotion trigger)              │  │
         │  └──────────────────────┘  └──────────────────────────────────┘  │
         └──────────────────────────────────────────────────────────────────┘
                    │                                    │
       ┌────────────▼───────────┐          ┌────────────▼──────────────────┐
       │  LightRAG Service      │          │  Remotion Render Service       │
       │  (separate container)  │          │  (Node.js + @remotion/renderer)│
       │  FastAPI REST API       │          │  POST /render → job_id         │
       │  /documents/insert_text│          │  GET /render/:id/status        │
       │  /query (hybrid mode)  │          │  Uploads final .mp4 to R2      │
       │  /graph/search         │          └───────────────────────────────┘
       │  Storage: MongoDB +    │
       │  NetworkX (graph) +    │
       │  NanoVector (embeds)   │
       └────────────────────────┘
                    │
       ┌────────────▼─────────────────────────────────────────────────────┐
       │                   DATA LAYER (shared)                             │
       │  MongoDB (Motor async) — all collections                          │
       │  Redis — Celery broker + result backend                           │
       │  Cloudflare R2 — rendered media assets                            │
       │  Pinecone — content similarity embeddings (existing)              │
       └──────────────────────────────────────────────────────────────────┘
```

---

### Component Responsibilities

| Component | Responsibility | Lives In |
|-----------|---------------|----------|
| **n8n** | External workflow orchestrator: cron-based scheduling, publishing to social APIs, analytics polling, Strategist triggers, Remotion job dispatch, error-retry with visual logging | Self-hosted Docker, separate from FastAPI |
| **LightRAG Service** | Knowledge graph + entity/relationship extraction from approved content. Multi-hop retrieval for Thinker agent (replaces raw Pinecone query for structural knowledge) | Separate Docker container, exposes REST |
| **Remotion Render Service** | Accepts a `composition_id` + `inputProps` JSON, calls `bundle()` + `selectComposition()` + `renderMedia()`, uploads .mp4/.mp3 to R2, responds with asset URL | Node.js service in `remotion-service/` |
| **Media Orchestrator** | Decomposes a "media brief" (type, style, content) into per-model tasks, routes to best available provider (fal.ai / DALL-E / Runway / HeyGen), assembles via Remotion | `backend/services/media_orchestrator.py` |
| **Strategist Agent** | Nightly proactive analysis — reads LightRAG knowledge graph + Obsidian vault + persona performance signals → generates ranked recommendation cards stored in MongoDB | `backend/agents/strategist.py` + n8n trigger |
| **Obsidian Service** | Wraps `obsidian-cli` subprocess calls for vault search, note retrieval, and note creation. Called by Scout agent to enrich research with user's personal knowledge | `backend/services/obsidian_service.py` |
| **FastAPI Backend** | All user-facing HTTP routes, auth, billing, content CRUD, SSE notifications. Acts as the command plane — dispatches work to n8n, LightRAG, Remotion | `backend/` (existing, add new routes) |
| **Agent Pipeline** | LangGraph-orchestrated content generation (Commander→Scout→Thinker→Writer→QC). Calls LightRAG and Obsidian during execution | `backend/agents/` (existing, extend Scout + Thinker) |
| **Celery (retained)** | Fast in-process async tasks that need tight FastAPI coupling: generate_image_for_job, generate_video_for_job, and analytics 24h/7d polling fire-and-forget | `backend/tasks/` (kept, reduced scope) |

---

## Recommended Project Structure

The additions are additive. Existing directories are unchanged except for `scout.py`, `thinker.py`, and `tasks/content_tasks.py`.

```
backend/
├── agents/
│   ├── pipeline.py          # unchanged
│   ├── orchestrator.py      # unchanged (LangGraph)
│   ├── scout.py             # EXTEND: add obsidian_service call
│   ├── thinker.py           # EXTEND: add lightrag_service query
│   └── strategist.py        # NEW: proactive recommendation agent
│
├── services/
│   ├── lightrag_service.py  # NEW: HTTP client wrapping LightRAG REST API
│   ├── media_orchestrator.py # NEW: multi-model routing + assembly plan
│   ├── obsidian_service.py  # NEW: subprocess wrapper for obsidian-cli
│   └── strategist_service.py # NEW: recommendation card persistence + ranking
│
├── routes/
│   ├── n8n_bridge.py        # NEW: /api/n8n/trigger + /api/n8n/callback
│   ├── strategy.py          # NEW: /api/strategy GET/POST/approve
│   └── media_orchestrate.py # NEW: /api/media/orchestrate
│
├── tasks/
│   ├── content_tasks.py     # REDUCED: remove publishing/analytics cron (→ n8n)
│   └── media_tasks.py       # RETAINED: image + video async generation
│
remotion-service/
├── src/
│   ├── compositions/
│   │   ├── StaticImageCard.tsx    # text-on-image composition
│   │   ├── ImageCarousel.tsx      # multi-slide carousel
│   │   ├── TalkingHeadOverlay.tsx # HeyGen video + lower-third overlays
│   │   └── ShortFormVideo.tsx     # 15-60s with b-roll + voiceover
│   └── index.ts            # registers all compositions
├── server.ts               # Express HTTP API: POST /render, GET /render/:id/status
├── package.json
└── Procfile                # web: node server.js

docker-compose.yml          # adds: n8n + lightrag containers
.env.example                # adds: N8N_URL, N8N_WEBHOOK_SECRET, LIGHTRAG_URL,
                            #       OBSIDIAN_VAULT_PATH, OBSIDIAN_CLI_PATH,
                            #       REMOTION_SERVICE_URL
```

### Structure Rationale

- **`services/lightrag_service.py`:** LightRAG runs as a separate service (its own uvicorn process). The FastAPI backend never imports LightRAG directly — it calls it over HTTP. This keeps the Python dependency tree clean and allows LightRAG to be scaled or swapped independently.
- **`routes/n8n_bridge.py`:** n8n is external. FastAPI only speaks to it via HTTP POST (trigger) and receives POST callbacks (result). A dedicated bridge route isolates all n8n coupling.
- **`services/media_orchestrator.py`:** The orchestrator is a pure service (no route) — it is called by the media route and by the Strategist. It returns a structured `MediaPlan` dict, not side effects, making it testable.
- **`remotion-service/server.ts`:** Remotion's `renderMedia()` is Node.js-only. It cannot run inside FastAPI. The existing `remotion-service/` directory already exists but only has a Procfile — expand it into a real Express service with REST endpoints.
- **Celery retained:** Celery is NOT fully replaced by n8n. Celery remains for tasks that need to run inside the FastAPI process boundary (e.g., `generate_image_for_job` which directly accesses MongoDB via Motor async). n8n replaces the cron-scheduled and external-API tasks (publishing, analytics polling, credit resets).

---

## Architectural Patterns

### Pattern 1: FastAPI-n8n Bridge (Trigger + Callback)

**What:** FastAPI fires a webhook to n8n to start a workflow, then n8n POSTs back a callback when done. FastAPI stores a `workflow_run_id` in MongoDB so the callback can be matched to the originating job.

**When to use:** Any task that involves external API calls with retry logic, long polling, or multi-step conditional logic (publishing, analytics ingestion, Strategist pipeline).

**Trade-offs:** Decouples long-running work from FastAPI's async event loop. Adds HTTP round-trip latency (~50ms). Requires n8n to be reachable from FastAPI.

**Integration flow:**
```python
# backend/routes/n8n_bridge.py

async def trigger_n8n_workflow(workflow_name: str, payload: dict) -> str:
    """Fire-and-forget trigger to n8n. Returns workflow_run_id for callback matching."""
    webhook_url = f"{settings.app.n8n_url}/webhook/{workflow_name}"
    payload["callback_url"] = f"{settings.app.backend_url}/api/n8n/callback"
    async with httpx.AsyncClient() as client:
        resp = await client.post(webhook_url, json=payload, timeout=5.0)
    return resp.json().get("run_id", "")

# n8n calls back:
# POST /api/n8n/callback
# body: { "run_id": "...", "job_id": "...", "status": "success", "result": {...} }
```

### Pattern 2: LightRAG as a Sidecar Service

**What:** LightRAG runs as a separate Docker container exposing its own FastAPI REST API. The ThookAI backend calls it via an HTTP client abstraction (`lightrag_service.py`). Two operations are used: `insert_text` (on content approval) and `query` (during Thinker execution).

**When to use:** Any time the Thinker needs to know what concepts, entities, or relationships a user has previously written about. Also used by the Strategist to find content gaps in the user's knowledge graph.

**Trade-offs:** Separate process means independent scaling and zero Python dependency pollution. Adds network hop. LightRAG maintains its own storage (MongoDB KV + NetworkX graph + NanoVector embeddings) — this is a separate MongoDB database, NOT the ThookAI application database.

**Integration points:**
```python
# backend/services/lightrag_service.py

LIGHTRAG_BASE_URL = settings.app.lightrag_url  # e.g., http://lightrag:8080

async def insert_content(user_id: str, content: str, metadata: dict) -> bool:
    """Called from agents/learning.py after content approval."""
    # Namespace per user with a document tag
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{LIGHTRAG_BASE_URL}/documents/insert_text",
            json={"text": content, "metadata": {"user_id": user_id, **metadata}},
            timeout=30.0,
        )
    return resp.status_code == 200

async def query_knowledge(user_id: str, topic: str, mode: str = "hybrid") -> str:
    """Called from agents/thinker.py before angle selection."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{LIGHTRAG_BASE_URL}/query",
            json={"query": topic, "mode": mode, "user_id": user_id},
            timeout=15.0,
        )
    return resp.json().get("response", "")
```

**Scout agent extension (Obsidian):**
```python
# agents/scout.py — add after Perplexity call

from services.obsidian_service import search_vault

async def run_scout(topic, research_query, platform, user_id=None):
    perplexity_result = await _call_perplexity(research_query)
    vault_notes = []
    if user_id:
        vault_notes = await search_vault(query=topic, limit=3)
    return {**perplexity_result, "vault_context": vault_notes}
```

### Pattern 3: Media Orchestrator + Remotion Assembly

**What:** A two-phase media generation pipeline. Phase 1 (Orchestrator) decomposes a `MediaBrief` into per-asset tasks and routes each to the best available provider. Phase 2 (Remotion) assembles the generated assets (images, audio, video clips) into a final composed video using a parametric React composition.

**When to use:** All media generation that requires composition — carousels, talking-head overlays, short-form videos. Static single-image generation skips Remotion and goes directly to fal.ai/DALL-E.

**Trade-offs:** Adds a Node.js service dependency (Remotion). Requires pre-built composition templates in `remotion-service/src/compositions/`. The assembly step adds 30-120 seconds rendering time.

**Two-phase flow:**
```
POST /api/media/orchestrate
  body: { job_id, media_type: "carousel", style: "bold", content_text, slides: 5 }
  ↓
media_orchestrator.py
  → generate_asset_plan(brief)
     → [
         { task: "slide_1_image", provider: "fal", prompt: "..." },
         { task: "slide_2_image", provider: "fal", prompt: "..." },
         ...
       ]
  → run each asset task in parallel (asyncio.gather)
  → collect asset_urls[]
  ↓
POST remotion-service /render
  body: {
    composition_id: "ImageCarousel",
    input_props: { slides: asset_urls, brand_colors: [...], text_overlays: [...] },
    output_format: "mp4"
  }
  → remotion renders → uploads to R2 → returns final_url
  ↓
PATCH db.content_jobs: { media_assets: [final_url], media_status: "ready" }
```

**Remotion service render endpoint pattern:**
```typescript
// remotion-service/server.ts
app.post("/render", async (req, res) => {
  const { composition_id, input_props, output_format = "mp4" } = req.body;
  const render_id = uuid();
  // Enqueue render (non-blocking), respond immediately
  renderQueue.push({ render_id, composition_id, input_props, output_format });
  res.json({ render_id, status: "queued" });
});

// Worker pulls from queue:
// bundle() → selectComposition(input_props) → renderMedia(input_props) → upload to R2
// → PATCH FastAPI /api/n8n/callback with { render_id, status, asset_url }
```

### Pattern 4: Strategist Agent as Nightly n8n Job

**What:** The Strategist Agent runs on a nightly cron schedule triggered by n8n, NOT by user request. It reads LightRAG's graph for content gaps, checks real performance data from `content_jobs.performance_data`, queries Obsidian vault for unused ideas, and generates 3-5 ranked recommendation cards per user. Cards are written to a new `strategy_recommendations` MongoDB collection, then pushed to users via SSE.

**When to use:** Every night. Also triggered on-demand by user action from Strategy Dashboard.

**Trade-offs:** Nightly cron means recommendations may be 12-24h stale for infrequent users. n8n provides built-in retry + execution logs. Running it per-user in series avoids overwhelming the LLM API.

**Agent structure:**
```python
# backend/agents/strategist.py

async def run_strategist(user_id: str) -> list[dict]:
    """Returns list of recommendation cards."""
    # 1. Knowledge gap detection via LightRAG graph query
    gaps = await lightrag_service.query_knowledge(
        user_id, "what topics are underrepresented?", mode="global"
    )
    # 2. Performance signals from MongoDB
    top_performing = await db.content_jobs.find(
        {"user_id": user_id, "performance_data.engagement_rate": {"$gt": 0.05}}
    ).sort("performance_data.engagement_rate", -1).limit(5).to_list(5)
    # 3. Vault context for unused ideas
    vault_ideas = await obsidian_service.search_vault(query="content ideas", limit=5)
    # 4. LLM synthesis → recommendation cards
    cards = await _synthesize_recommendations(gaps, top_performing, vault_ideas, user_id)
    # 5. Persist to MongoDB
    await db.strategy_recommendations.insert_many(cards)
    return cards
```

---

## Data Flow

### Content Generation with LightRAG (Extended Pipeline)

```
User → POST /api/content/generate
         ↓
   FastAPI route (content.py) → create content_job in db → run_agent_pipeline.delay()
         ↓
   Celery worker → run_agent_pipeline (LangGraph orchestrator)
         ↓
   Commander → job spec + angle strategy
         ↓
   Scout (EXTENDED) → Perplexity research + Obsidian vault search
         ↓
   Thinker (EXTENDED) → LightRAG hybrid query(topic) → injects entity context
         ↓ (LightRAG HTTP call → POST lightrag-service/query)
   Writer → voice-matched draft using enriched context
         ↓
   QC → score → "reviewing" status
         ↓
   User approves content
         ↓
   learning.py → Pinecone embedding (existing) +
   lightrag_service.insert_content(text) (NEW)
```

### Publishing Flow via n8n (Replaces Celery Publishing)

```
Celery beat (every 5 min): process_scheduled_posts
  → finds due posts in db.scheduled_posts
  → for each post: trigger_n8n_workflow("publish-post", { post_id, platform, content, token })
         ↓
n8n Workflow: publish-post
  → HTTP Request node → platform API (LinkedIn UGC / X v2 / IG Basic Display)
  → on success: POST /api/n8n/callback { post_id, status: "published", platform_post_id }
  → on failure: retry 3x → POST /api/n8n/callback { post_id, status: "failed", error }
         ↓
FastAPI /api/n8n/callback handler
  → PATCH db.scheduled_posts: { status, platform_post_id }
  → fire SSE notification to user
  → trigger analytics workflow (schedule 24h + 7d callbacks)
```

### Analytics Feedback Loop

```
n8n Workflow: analytics-poll (triggered by publish callback + scheduled 24h/7d)
  → wait 24h (n8n Wait node)
  → HTTP Request → LinkedIn / X / IG metrics API
  → POST /api/n8n/callback { job_id, performance_data: { likes, comments, shares, impressions } }
         ↓
FastAPI callback handler
  → PATCH db.content_jobs: { performance_data }
  → PATCH db.persona_engines: { performance_intelligence } (aggregate)
  → lightrag_service.insert_content(performance summary text)  ← feeds Strategist
```

### Strategy Dashboard Data Flow

```
n8n Workflow: nightly-strategist (cron: 2am UTC)
  → POST /api/n8n/trigger { workflow: "run-strategist", user_ids: [...] }
         ↓ (or FastAPI calls strategist directly for on-demand)
FastAPI → strategist.run_strategist(user_id)
  → LightRAG query (knowledge gaps)
  → MongoDB read (performance signals)
  → Obsidian search (unused ideas)
  → LLM synthesis → recommendation cards
  → INSERT db.strategy_recommendations
  → SSE push to user frontend
         ↓
React Strategy Dashboard
  → GET /api/strategy → list of cards
  → user clicks "Approve" → POST /api/content/generate (pre-filled from card)
```

---

## Component Boundaries

The key boundary rule: **services do not call routes**. Routes call services. Services call external APIs. Tasks call services.

| Boundary | Communication | Constraint |
|----------|---------------|------------|
| FastAPI ↔ n8n | HTTP POST (trigger) + HTTP POST callback | n8n URL + HMAC shared secret for callback auth |
| FastAPI ↔ LightRAG | HTTP REST (lightrag_service.py) | LightRAG on separate Docker network, not exposed to public internet |
| FastAPI ↔ Remotion | HTTP REST (media_orchestrator.py calls remotion-service) | Remotion service internal network only |
| Agent Pipeline ↔ LightRAG | via lightrag_service.py (no direct import) | Always async HTTP, never in-process |
| Agent Pipeline ↔ Obsidian | via obsidian_service.py subprocess | Vault path must be mounted volume in dev; prod uses Obsidian REST plugin |
| Celery ↔ FastAPI | Celery tasks import from `agents/` and `services/` directly | Tasks NEVER import from `routes/` |
| n8n ↔ Social Platform APIs | n8n HTTP Request node | Platform OAuth tokens fetched from FastAPI via n8n credential store or passed in payload |

---

## Build Order Implications

Dependencies determine sequencing. Each component depends on those above it.

```
Wave 1 — Foundation (no inter-dependencies)
  1a. n8n infrastructure (Docker, workflows for existing Celery tasks)
  1b. LightRAG service (container + MongoDB + initial document indexing)
  1c. Remotion service (Express server + base compositions)

Wave 2 — Pipeline Extensions (depends on Wave 1 services running)
  2a. Scout agent Obsidian integration (depends on obsidian-cli setup)
  2b. Thinker agent LightRAG query (depends on 1b LightRAG running)
  2c. learning.py LightRAG insert_content (depends on 1b LightRAG running)
  2d. Media orchestrator + 4 composition types in Remotion (depends on 1c)

Wave 3 — Strategist + Dashboard (depends on Wave 2 data flowing)
  3a. Strategist agent (depends on 2b LightRAG populated + performance_data flowing)
  3b. Strategy Dashboard frontend (depends on 3a backend route + SSE)
  3c. Analytics feedback loop via n8n (depends on 1a n8n + publishing working)

Wave 4 — E2E Audit
  4a. Security hardening, load testing, production deployment
```

Critical path: `n8n publishing working → analytics data flowing → LightRAG populated → Strategist has signal → dashboard has value`.

Do not build the Strategist Dashboard before LightRAG has at least one week of approved content indexed — empty knowledge graph produces generic recommendations that damage trust.

---

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| 0-500 users | All services on single Render host (n8n + FastAPI + LightRAG on Docker Compose). LightRAG uses NetworkX (in-memory graph). Remotion renders synchronously. |
| 500-5k users | Separate n8n to dedicated host. LightRAG migrates to Neo4j for persistent graph. Remotion gets dedicated worker pool (2-3 instances). Celery workers scaled to 3. |
| 5k+ users | LightRAG per-user sharding (namespace by user_id in graph). n8n scaled with separate worker and main instances. Remotion migrates to Remotion Lambda (AWS Lambda rendering). |

### Scaling Priorities

1. **First bottleneck — LightRAG graph queries during Thinker.** NetworkX is in-memory and single-threaded. At ~1k users each with 50+ approved posts, queries slow to 2-3s. Mitigation: cache last 5 query results per user in Redis with 1h TTL. Migration path: Neo4j for persistent graph storage.

2. **Second bottleneck — Remotion rendering queue.** A single `renderMedia()` call takes 30-120s and is CPU-bound. At >10 concurrent renders, queue depth grows. Mitigation: size Remotion service with `--max-concurrency` capped at 4 renders, use n8n to throttle dispatch rate.

---

## Anti-Patterns

### Anti-Pattern 1: Calling LightRAG Synchronously Inside Every Agent Step

**What people do:** Import LightRAG Python library directly into `thinker.py`, call `rag.query()` inline.

**Why it's wrong:** LightRAG with graph traversal can take 3-8 seconds. Calling it synchronously inside the agent pipeline adds that latency to every content generation job, even when the result isn't needed. It also couples the Python dependency tree — LightRAG requires specific versions of networkx, nano-vectordb, and its own LLM client.

**Do this instead:** Run LightRAG as a separate service. Call it via async HTTP with a 10s timeout. Gate the call on `research_needed` from Commander output (same pattern as Perplexity). Cache results per user per topic for 1h.

### Anti-Pattern 2: Replacing Celery Entirely with n8n

**What people do:** Delete all Celery tasks, move `generate_image_for_job` and `generate_video_for_job` to n8n HTTP Request nodes.

**Why it's wrong:** These tasks call `from database import db` (Motor async client) and FastAPI internal services directly. Moving them to n8n means the logic must be exposed as HTTP endpoints (security surface increase) and Motor async context is lost (n8n can only call HTTP, not Python coroutines). Additionally, n8n adds 200-500ms overhead per workflow execution that is acceptable for 5-minute cron jobs but unacceptable for user-facing media generation.

**Do this instead:** Keep Celery for all tasks that require tight FastAPI coupling (image/video generation, media assembly coordination). Move only cron-scheduled and external-API tasks to n8n (publishing, analytics polling, credit resets, Strategist trigger).

### Anti-Pattern 3: Building Remotion Compositions as Generic Templates

**What people do:** Create a single `GenericPost.tsx` composition with many conditional branches — "if type=carousel show slides, else if type=talking-head show video."

**Why it's wrong:** Remotion compositions are React components — conditional branching creates timing issues (duration calculation depends on content type). Debugging a single 800-line composition is difficult. Re-renders when props change affect the wrong frames.

**Do this instead:** Create one composition per content type: `StaticImageCard`, `ImageCarousel`, `TalkingHeadOverlay`, `ShortFormVideo`. Each composition knows exactly its duration, layout, and asset types. The orchestrator selects which composition to use based on `media_type` in the request.

### Anti-Pattern 4: Storing LightRAG Knowledge in the Main MongoDB

**What people do:** Configure LightRAG to use the same `MONGO_URL` and `DB_NAME` as the ThookAI application, to simplify infrastructure.

**Why it's wrong:** LightRAG creates its own collections (kv_store, vector_store, doc_status). These overlap in naming with ThookAI collections and create operational confusion. LightRAG's schema is internal to the library and may change across versions. Mixing them couples upgrade paths.

**Do this instead:** Configure LightRAG with a separate database name (e.g., `thookai_lightrag`). Same MongoDB cluster is fine, different `DB_NAME`. Set this via LightRAG's `MONGO_URI` env var pointing to the same cluster with `?authSource=admin`.

### Anti-Pattern 5: The Strategist Writes Directly to the Content Pipeline

**What people do:** Strategist agent calls `run_agent_pipeline()` directly when it detects a content opportunity, creating content without user approval.

**Why it's wrong:** Unsolicited auto-generated content bypasses the user's voice control and QC approval flow. Users lose trust if they see posts that "appeared" without them requesting them. The core product promise is human-in-the-loop.

**Do this instead:** The Strategist writes recommendation cards to `db.strategy_recommendations` only. Each card has a `status: "pending_approval"` field and a pre-filled `generate_payload` (the exact JSON for `POST /api/content/generate`). The Strategy Dashboard shows these cards — the user clicks "Use This Idea" which fires the generation request with the user's active session.

---

## Integration Points

### n8n Workflow Triggers

| Workflow | Trigger | Replaces |
|----------|---------|---------|
| `publish-post` | Webhook POST from FastAPI | `_publish_to_platform()` in content_tasks.py |
| `analytics-poll-24h` | Callback from publish-post workflow | Celery task (was missing) |
| `analytics-poll-7d` | Webhook POST from FastAPI 7 days after publish | Celery task (was missing) |
| `reset-daily-limits` | Cron (00:00 UTC) | `reset_daily_limits` Celery beat task |
| `refresh-monthly-credits` | Cron (1st of month 00:05 UTC) | `refresh_monthly_credits` Celery beat task |
| `cleanup-old-jobs` | Cron (02:00 UTC) | `cleanup_old_jobs` Celery beat task |
| `nightly-strategist` | Cron (02:00 UTC) | New — no existing equivalent |

### n8n Callback Authentication

n8n callbacks to `/api/n8n/callback` must be authenticated to prevent spoofing. Use HMAC-SHA256 signature verification:

```python
# backend/routes/n8n_bridge.py
import hmac, hashlib

def verify_n8n_callback(payload_bytes: bytes, signature_header: str) -> bool:
    secret = settings.app.n8n_webhook_secret.encode()
    expected = hmac.new(secret, payload_bytes, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature_header)
```

n8n adds the signature via its "Header Auth" credential on the HTTP Request node.

### LightRAG REST Integration Summary

| Operation | Endpoint | Called By | When |
|-----------|----------|-----------|------|
| Insert content | `POST /documents/insert_text` | `agents/learning.py` | After user approves content |
| Query knowledge | `POST /query` (mode: hybrid) | `agents/thinker.py` | Before angle selection |
| Graph search | `GET /graph/search?query=` | `agents/strategist.py` | During Strategist analysis |
| Document status | `GET /documents/status` | Health check endpoint | Startup lifespan check |

### Obsidian CLI Integration

The `obsidian-cli` tool (`github.com/davidpp/obsidian-cli`) exposes vault operations as subprocess JSON output. The `obsidian_service.py` wrapper calls it via `asyncio.create_subprocess_exec()` and parses JSON responses.

```
obsidian_service.search_vault(query) → subprocess: obsidian search "<query>" --json
obsidian_service.get_note(path)      → subprocess: obsidian get "<path>" --json
obsidian_service.create_note(title, body) → subprocess: obsidian create --json
```

This requires `obsidian-cli` binary on PATH of the FastAPI server process. In Docker, mount the vault as a volume and install the CLI in the container.

For production (Render), the vault must be synced via Obsidian Sync or a Git-backed vault. Alternative: expose vault via Obsidian's Local REST API plugin and call HTTP instead of subprocess — removes the binary dependency.

### Remotion Service Integration

| Operation | Endpoint | Called By | Notes |
|-----------|----------|-----------|-------|
| Start render | `POST /render` | `services/media_orchestrator.py` | Returns `render_id` immediately, non-blocking |
| Poll status | `GET /render/:id/status` | Celery task or n8n polling | Returns `{ status, progress, asset_url }` |
| Health check | `GET /health` | FastAPI lifespan startup | Confirms Remotion service is reachable |

The Remotion service uploads final `.mp4` directly to R2 using the same `R2_ACCESS_KEY_ID` / `R2_SECRET_ACCESS_KEY` env vars. FastAPI receives only the final R2 URL via callback — it never handles video binary data.

---

## New Environment Variables Required

| Variable | Purpose | Service |
|----------|---------|---------|
| `N8N_URL` | Base URL of self-hosted n8n (e.g., `http://n8n:5678`) | FastAPI |
| `N8N_WEBHOOK_SECRET` | HMAC secret for callback signature verification | FastAPI + n8n |
| `LIGHTRAG_URL` | Base URL of LightRAG service (e.g., `http://lightrag:8080`) | FastAPI |
| `LIGHTRAG_MONGO_URL` | Separate MongoDB connection for LightRAG storage | LightRAG service |
| `REMOTION_SERVICE_URL` | Base URL of Remotion render service (e.g., `http://remotion:3001`) | FastAPI |
| `OBSIDIAN_VAULT_PATH` | Absolute path to Obsidian vault directory | FastAPI (dev) |
| `OBSIDIAN_CLI_PATH` | Path to `obsidian-cli` binary | FastAPI (dev) |
| `OBSIDIAN_API_URL` | Alternative: Obsidian Local REST API URL (prod) | FastAPI (prod) |

All added to `backend/config.py` as a new `V2Config` dataclass following existing config pattern.

---

## Sources

- [n8n Webhook Node Documentation](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.webhook/) — webhook trigger patterns, MEDIUM confidence
- [n8n as Celery Complement](https://medium.com/@raniurbis/how-n8n-can-complement-backend-implementations-13804550a33a) — architectural guidance, MEDIUM confidence (single source)
- [LightRAG GitHub Repository](https://github.com/HKUDS/LightRAG) — storage architecture, query modes, HIGH confidence (official)
- [LightRAG API Server (DeepWiki)](https://deepwiki.com/HKUDS/LightRAG/4-api-server) — REST endpoint structure, FastAPI server pattern, HIGH confidence
- [Remotion renderMedia() API](https://www.remotion.dev/docs/renderer/render-media) — bundle/selectComposition/renderMedia workflow, HIGH confidence (official)
- [Remotion Server-Side Rendering](https://www.remotion.dev/docs/ssr) — deployment patterns, HIGH confidence (official)
- [obsidian-cli GitHub](https://github.com/davidpp/obsidian-cli) — command structure, JSON output format, HIGH confidence
- [Multi-Model Media Orchestration Architecture](https://medium.com/@cliprise/multi-model-ai-infrastructure-guide-build-production-grade-image-video-systems-that-dont-break-e85aba4e4279) — Director Layer pattern, sequential vs concurrent routing, MEDIUM confidence

---

*Architecture research for: ThookAI v2.0 Intelligent Content Operating System — n8n + LightRAG + Remotion + Strategist Agent integration*
*Researched: 2026-04-01*
