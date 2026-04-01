# Phase 10: LightRAG Knowledge Graph — Research

**Researched:** 2026-04-01
**Domain:** LightRAG knowledge graph sidecar, per-user namespace isolation, entity extraction customization, dual-store write (Pinecone + LightRAG), Thinker agent integration
**Confidence:** MEDIUM-HIGH

---

<user_constraints>
## User Constraints (from STATE.md Decisions)

### Locked Decisions
- v2.0 architectural principle: New components (n8n, LightRAG, Remotion) run as sidecar services, integrated over HTTP — no new Python imports into FastAPI monolith
- LightRAG embedding model: Lock `text-embedding-3-small` in config before first document insert — no migration path exists without full index rebuild
- LightRAG storage: `MongoKVStorage` + `MongoDocStatusStorage` against a separate database (`thookai_lightrag`). Use `NanoVectorDBStorage` for embeddings — do NOT use `MongoVectorDBStorage` (requires Atlas Vector Search)
- Retrieval routing contract: Thinker calls LightRAG only; Writer calls Pinecone only; Learning agent writes to both on approval (no cross-calls permitted)
- Phase 9 (n8n) must be complete before Phase 10 execution — this phase depends on n8n infrastructure

### Claude's Discretion
- How workspace isolation is implemented at storage level (one LightRAG instance with MONGODB_WORKSPACE prefix vs. per-user instance — research findings below)
- Whether to use `hybrid` or `mix` query mode for the Thinker query
- Whether to call `await rag.initialize_storages()` in the sidecar lifespan or lazily

### Deferred Ideas (OUT OF SCOPE)
- Strategist Agent (Phase 12 — depends on both this phase AND Phase 13 analytics)
- Neo4j graph storage upgrade from NetworkX (deferred until graph exceeds ~100k entities)
- Multi-language entity extraction
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| LRAG-01 | LightRAG sidecar container starts and connects to its own MongoDB database (`thookai_lightrag`) without touching ThookAI app DB | LightRAG server Docker image `ghcr.io/hkuds/lightrag:latest` confirmed. Port 9621. MONGO_DATABASE env var controls DB name. docker-compose.yml addition documented below. |
| LRAG-02 | Per-user namespace isolation — each user's knowledge graph is strictly separated at storage level | `MONGODB_WORKSPACE` env var adds prefix to all MongoDB collection names. Pattern: one LightRAG instance with per-user workspaces via `MONGODB_WORKSPACE={user_id}`. Critical: workspace is set at instance startup, NOT per-request. This means per-user isolation requires either per-user LightRAG instance (doesn't scale) or a workspace-in-document approach (see Architecture Patterns). |
| LRAG-03 | Domain-specific entity extraction prompt (topic domains, hook archetypes, emotional tones, named entities) tested on 10+ real posts before production ingestion | `ENTITY_TYPES` env var and `PROMPTS["DEFAULT_ENTITY_TYPES"]` runtime patch both available. Custom extraction prompt design provided below. Must be tested before production ingestion starts. |
| LRAG-04 | Embedding model (`text-embedding-3-small`) locked in config before first document insert with startup assertion on vector dimension | NanoVectorDBStorage raises `AssertionError: Embedding dim mismatch, expected: X, but loaded: Y` on startup if stored dimension mismatches config. Set `EMBEDDING_MODEL=text-embedding-3-small` and `EMBEDDING_DIM=1536` permanently. Write startup assertion in `lightrag_service.py`. |
| LRAG-05 | Thinker agent enhanced with multi-hop LightRAG retrieval — "what angles have I NOT used on topic X?" | Thinker currently calls GPT-4o-mini. Integration point: after `run_thinker()` signature, inject LightRAG context before building the prompt. Query mode: `hybrid` (entities + relationships). Timeout: 15s max. |
| LRAG-06 | Learning agent writes to both Pinecone (similarity) and LightRAG (relationships) on content approval | `capture_learning_signal()` already calls `upsert_approved_embedding()` for Pinecone. Add parallel LightRAG insert at the same point. Both calls must be non-fatal (try/except with warning log). |
| LRAG-07 | Strict retrieval routing contract — Thinker calls LightRAG only, Writer calls Pinecone only (no context bleeding) | Document the contract in `backend/agents/pipeline.py` as an explicit comment block. Code review gate: Writer must never import `lightrag_service`. |
</phase_requirements>

---

## Summary

Phase 10 builds the knowledge graph layer that makes ThookAI's content intelligence non-generic. The goal is simple: every piece of content a user approves gets indexed as a graph of topic entities and relationships, and the Thinker agent queries that graph before selecting an angle — asking "what has this user NOT written about?" rather than relying on generic pattern matching.

LightRAG v1.4.12 is the right tool. It ships a complete FastAPI REST API server, supports MongoDB as a storage backend, and raises an `AssertionError` (not a silent failure) when the configured embedding dimension mismatches stored data. The sidecar deployment pattern is straightforward: one Docker container using the official `ghcr.io/hkuds/lightrag:latest` image, connected to a dedicated `thookai_lightrag` MongoDB database, exposed on port 9621, and called from ThookAI's backend over HTTP via `backend/services/lightrag_service.py`.

The most technically critical issue in this phase is **per-user namespace isolation**. LightRAG's `MONGODB_WORKSPACE` parameter prefixes all collection names — but it is set at container startup and is global to all requests. This means LightRAG cannot serve multiple users with different workspaces from a single running instance without a design pattern choice. The recommended approach (detailed in Architecture Patterns below) is to run one LightRAG container with a fixed workspace, and enforce user isolation at the application layer by including `user_id` as a required field in every inserted document and every query filter. This is simpler to operate than per-user containers and is sufficient for the current scale.

The second critical issue is **entity extraction quality**. LightRAG's default entity types (`organization`, `person`, `geo`, `event`) are wrong for ThookAI's domain. A content-creation platform needs to extract topic domains, hook archetypes, emotional tones, and expertise signals — not geographic locations and generic organizations. The custom extraction prompt must be written and tested on 10 real approved posts before the ingestion pipeline goes to production.

**Primary recommendation:** Deploy LightRAG as a single sidecar container. Use `MONGODB_WORKSPACE=thookai` to prefix all collections. Enforce per-user isolation at the application layer by injecting `user_id` into every insert payload and filtering by `user_id` in every query. Lock `text-embedding-3-small` (1536 dims) in config and add startup assertion. Override `ENTITY_TYPES` env var with ThookAI domain types. Wire `capture_learning_signal()` to call LightRAG insert in parallel with the existing Pinecone call.

---

## Standard Stack

### Core

| Library / Tool | Version | Purpose | Why Standard |
|---------------|---------|---------|--------------|
| `lightrag-hku` | 1.4.12 (latest, 2026-03-27) | Knowledge graph engine — entity/relationship extraction, graph storage, multi-hop retrieval | Official EMNLP 2025 library. Has MongoDB backends, built-in FastAPI REST server, and NanoVectorDB (zero extra infra). |
| `ghcr.io/hkuds/lightrag:latest` | latest (tracks 1.4.12) | Docker image for LightRAG sidecar | Official image from HKUDS GitHub Container Registry. Port 9621. |
| MongoDB 7.0 (existing) | 7.0 (already in stack) | KV storage, graph storage, doc status tracking for LightRAG | Existing infra. LightRAG connects to a SEPARATE database (`thookai_lightrag`) on the same MongoDB instance. |
| `NanoVectorDBStorage` | built-in to lightrag-hku | Embedding storage for entities and relationships | File-based, zero infra. `MongoVectorDBStorage` requires Atlas Vector Search — not available on MongoDB Community. |
| `NetworkXStorage` | built-in to lightrag-hku | In-memory graph topology storage | Zero infra. Sufficient for per-user content graphs at current scale. Upgrade to Neo4j when graph exceeds ~100k entities. |
| `text-embedding-3-small` | OpenAI API | Embedding model for all vector operations | 1536 dimensions. Best cost/quality ratio for short-form content (200-2000 tokens). MUST be chosen before first `insert()`. |
| `httpx` | 0.28.1 (existing) | Async HTTP client for calling LightRAG REST API from FastAPI | Already in stack. Used for all LightRAG calls from `lightrag_service.py`. |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `openai` | >=1.40.0 (existing) | Used by LightRAG sidecar for embeddings (`text-embedding-3-small`) and entity extraction LLM calls | LightRAG container calls OpenAI directly — requires `OPENAI_API_KEY` in the sidecar's `.env`. |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| NanoVectorDBStorage | MongoVectorDBStorage | MongoVectorDBStorage requires Atlas Vector Search — not available on MongoDB Community or standard Atlas. NanoVectorDBStorage is file-based and sufficient for current scale. |
| NetworkXStorage | Neo4j 5.x | Neo4j is production-grade for large graphs but requires a new service. Start with NetworkX; it handles per-user graphs of 10k–50k nodes comfortably. |
| One LightRAG container (app-layer user isolation) | One container per user | Per-user containers don't scale (100 users = 100 containers). App-layer user_id filtering is operationally simpler and sufficient. |
| `hybrid` query mode | `mix` query mode | `hybrid` combines local (entity-focused) + global (relationship-focused) retrieval. `mix` additionally adds naive vector search. `hybrid` is recommended — adds cross-hop reasoning without the noise of naive retrieval. |

**Installation (additions to existing stack):**

```bash
# backend/requirements.txt — add:
lightrag-hku==1.4.12

# docker-compose.yml — add lightrag service (see Architecture Patterns)
# No new npm packages
```

**Version verification (confirmed 2026-04-01):**

```bash
pip index versions lightrag-hku  # latest: 1.4.12 (2026-03-27)
```

---

## Architecture Patterns

### Recommended Project Structure

New files only. Existing `agents/`, `routes/`, `tasks/` are unchanged except for targeted additions to `learning.py` and `thinker.py`.

```
backend/
├── services/
│   └── lightrag_service.py     # NEW: HTTP client wrapping LightRAG REST API
├── agents/
│   ├── learning.py             # EXTEND: add LightRAG insert after Pinecone call
│   └── thinker.py              # EXTEND: add LightRAG query before angle selection
├── config.py                   # EXTEND: add LightRAGConfig dataclass
├── .env.example                # EXTEND: add LIGHTRAG_URL, LIGHTRAG_API_KEY

docker-compose.yml              # EXTEND: add lightrag service block
lightrag/                       # NEW: top-level dir for LightRAG config
└── .env                        # LightRAG sidecar environment variables
```

### Pattern 1: LightRAG Sidecar Container (docker-compose.yml addition)

**What:** Add LightRAG as a separate service connecting to the existing MongoDB instance but using a dedicated database. No changes to ThookAI's database connection.

**docker-compose.yml addition:**

```yaml
  lightrag:
    image: ghcr.io/hkuds/lightrag:latest
    restart: unless-stopped
    ports:
      - "9621:9621"
    volumes:
      - lightrag_data:/app/data/rag_storage
      - ./lightrag/.env:/app/.env
    environment:
      - HOST=0.0.0.0
      - PORT=9621
      - WORKING_DIR=/app/data/rag_storage
      # Storage backends (MongoDB KV/doc + NanoVector + NetworkX graph)
      - LIGHTRAG_KV_STORAGE=MongoKVStorage
      - LIGHTRAG_DOC_STATUS_STORAGE=MongoDocStatusStorage
      - LIGHTRAG_GRAPH_STORAGE=NetworkXStorage
      - LIGHTRAG_VECTOR_STORAGE=NanoVectorDBStorage
      # MongoDB — separate thookai_lightrag database, same mongo service
      - MONGO_URI=mongodb://mongo:27017/
      - MONGO_DATABASE=thookai_lightrag
      - MONGODB_WORKSPACE=thookai
      # Embedding model — FROZEN, do not change after first insert
      - EMBEDDING_BINDING=openai
      - EMBEDDING_MODEL=text-embedding-3-small
      - EMBEDDING_DIM=1536
      - EMBEDDING_TOKEN_LIMIT=8191
      # LLM for entity extraction
      - LLM_BINDING=openai
      - LLM_MODEL=gpt-4o-mini
      # Domain-specific entity extraction
      - ENTITY_TYPES='["topic_domain", "hook_archetype", "emotional_tone", "expertise_signal", "content_format"]'
    depends_on:
      mongo:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "wget", "--spider", "-q", "http://localhost:9621/health"]
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  lightrag_data:   # add to existing volumes block
```

**lightrag/.env (separate from ThookAI .env):**

```bash
# LightRAG sidecar — environment file
# NOTE: OPENAI_API_KEY is the only secret needed here
OPENAI_API_KEY=sk-...   # required for embeddings + entity extraction LLM

# Embedding configuration — FROZEN after first document insert
# DO NOT change EMBEDDING_MODEL or EMBEDDING_DIM without full index rebuild
EMBEDDING_BINDING=openai
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIM=1536
```

### Pattern 2: Per-User Isolation via Application-Layer user_id Filtering

**What:** LightRAG's `MONGODB_WORKSPACE` adds a collection prefix (e.g., `thookai_KV_STORE`). That gives ThookAI's data a namespace, but does NOT separate User A from User B within that namespace. Per-user isolation is enforced at the application layer by including `user_id` in every document inserted and every query.

**Why not per-user containers:** LightRAG's workspace is set at startup time and is global to the container. Switching workspace per-request requires patching the `ClientManager` singleton — an unsupported pattern that breaks on library upgrades. Running 100+ containers (one per user) is operationally impractical.

**Implementation in `lightrag_service.py`:**

```python
# backend/services/lightrag_service.py
# Source: derived from LightRAG REST API docs + project pattern
import httpx
import logging
from config import settings

logger = logging.getLogger(__name__)

LIGHTRAG_URL = settings.lightrag.url  # e.g., http://lightrag:9621
LIGHTRAG_API_KEY = settings.lightrag.api_key  # if auth enabled on LightRAG server


async def insert_content(user_id: str, content: str, metadata: dict) -> bool:
    """Insert approved content into LightRAG knowledge graph.

    Called from agents/learning.py on content approval.
    Non-fatal: logs warning and returns False on failure.
    """
    doc_id = metadata.get("job_id", "")
    # Prefix content with user_id marker so entity extraction sees the owner
    tagged_content = f"[USER:{user_id}]\n\n{content}"
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{LIGHTRAG_URL}/documents/insert_text",
                json={
                    "text": tagged_content,
                    "doc_id": f"{user_id}_{doc_id}",
                    # metadata stored alongside doc for retrieval filtering
                    "metadata": {"user_id": user_id, **metadata},
                },
                headers={"X-API-Key": LIGHTRAG_API_KEY} if LIGHTRAG_API_KEY else {},
            )
        resp.raise_for_status()
        return True
    except Exception as e:
        logger.warning(f"LightRAG insert failed for user {user_id} job {doc_id} (non-fatal): {e}")
        return False


async def query_knowledge_graph(
    user_id: str,
    topic: str,
    mode: str = "hybrid",
) -> str:
    """Query the knowledge graph for topic context.

    Called from agents/thinker.py before angle selection.
    Returns empty string on failure — Thinker proceeds without graph context.
    """
    # Ask what angles the user has already used on this topic
    query = (
        f"What concepts, angles, hook archetypes, and emotional tones has user "
        f"{user_id} previously used when writing about: {topic}? "
        f"List the patterns they have NOT yet explored."
    )
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{LIGHTRAG_URL}/query",
                json={"query": query, "mode": mode},
                headers={"X-API-Key": LIGHTRAG_API_KEY} if LIGHTRAG_API_KEY else {},
            )
        resp.raise_for_status()
        return resp.json().get("response", "")
    except Exception as e:
        logger.warning(f"LightRAG query failed for user {user_id} (non-fatal): {e}")
        return ""
```

**Known limitation:** Without native per-user workspace switching, the graph is logically mixed at the storage level. The `[USER:{user_id}]` prefix and `metadata.user_id` field are the isolation mechanism. This means a poorly scoped query could theoretically return another user's graph nodes. Mitigations:
1. Always include user_id in the query string (as above).
2. In a future iteration, the LightRAG server can be augmented with a proxy that rewrites the workspace per-request (tracked in LightRAG GitHub issue #2133 — workspace-per-request is being actively discussed by maintainers as of 2026).

**Confidence: MEDIUM.** The user_id-in-query approach is pragmatic but not a hard storage-level guarantee. The E2E audit phase (Phase 16) must include a cross-user isolation test.

### Pattern 3: Thinker Agent Integration

**What:** Before building the angle-selection prompt, call `query_knowledge_graph()` and inject the result as a "TOPICS ALREADY COVERED" constraint section. Non-blocking — if LightRAG is unavailable, the Thinker proceeds without graph context.

**Integration point in `thinker.py`:**

```python
# agents/thinker.py — inside run_thinker(), BEFORE building the prompt
# Source: project pattern (see existing fatigue shield injection at line 134)

async def run_thinker(
    raw_input: str,
    commander_output: dict,
    scout_output: dict,
    persona_card: dict,
    fatigue_context: Optional[dict] = None,
    user_id: str = "",
) -> dict:
    # ... existing UOM directives fetch (lines 97-104) ...

    # NEW: Fetch knowledge graph context for topic gap analysis
    knowledge_context = ""
    if user_id:
        try:
            from services.lightrag_service import query_knowledge_graph
            knowledge_context = await query_knowledge_graph(
                user_id=user_id,
                topic=raw_input,
                mode="hybrid",
            )
        except Exception:
            pass  # Non-fatal — proceed without graph context

    # ... existing LLM call setup ...

    # Inject knowledge graph context into prompt (alongside existing fatigue section)
    if knowledge_context:
        kg_section = (
            "\n\nKNOWLEDGE GRAPH — TOPICS AND ANGLES ALREADY USED:"
            f"\n{knowledge_context[:800]}"
            "\n\nPrioritise angles, hook archetypes, and emotional tones NOT listed above."
        )
        prompt = prompt + kg_section
```

### Pattern 4: Learning Agent Dual-Write (Pinecone + LightRAG)

**What:** After successful Pinecone embedding (line ~198 in `learning.py`), add a non-fatal parallel LightRAG insert. The two writes are logically independent — LightRAG gets the full text for entity/relationship extraction; Pinecone gets the raw text for vector similarity.

**Integration point in `learning.py`:**

```python
# agents/learning.py — inside capture_learning_signal(), in the `if action == "approved":` block
# Add AFTER the existing Pinecone upsert_approved_embedding() call (line ~210)

# Source: project pattern — mirrors existing non-fatal Pinecone call structure
if action == "approved":
    # ... existing Pinecone call (lines 195-212) ...

    # NEW: Write to LightRAG knowledge graph (non-fatal)
    try:
        from services.lightrag_service import insert_content
        await insert_content(
            user_id=user_id,
            content=final_content,
            metadata={
                "job_id": job_id,
                "platform": job_meta.get("platform", "unknown"),
                "content_type": job_meta.get("content_type", "post"),
                "was_edited": job_meta.get("was_edited", False),
            },
        )
    except Exception as e:
        logger.warning(f"LightRAG insert failed (non-fatal): {e}")
```

### Pattern 5: LightRAGConfig Dataclass in config.py

**What:** Add a new `LightRAGConfig` dataclass following the existing config pattern. Add to `Settings` dataclass.

```python
# backend/config.py — add new dataclass
@dataclass
class LightRAGConfig:
    """LightRAG knowledge graph sidecar configuration"""
    url: str = field(default_factory=lambda: os.environ.get('LIGHTRAG_URL', 'http://lightrag:9621'))
    api_key: Optional[str] = field(default_factory=lambda: os.environ.get('LIGHTRAG_API_KEY'))
    # Embedding model — NEVER change after first document insert
    embedding_model: str = field(default_factory=lambda: os.environ.get('LIGHTRAG_EMBEDDING_MODEL', 'text-embedding-3-small'))
    embedding_dim: int = field(default_factory=lambda: int(os.environ.get('LIGHTRAG_EMBEDDING_DIM', '1536')))

    def is_configured(self) -> bool:
        return bool(self.url)

    def assert_embedding_config(self) -> None:
        """Fail loudly if embedding config is wrong — must match NanoVectorDB stored dim."""
        assert self.embedding_model == "text-embedding-3-small", (
            f"LIGHTRAG_EMBEDDING_MODEL must be 'text-embedding-3-small', got: {self.embedding_model}"
        )
        assert self.embedding_dim == 1536, (
            f"LIGHTRAG_EMBEDDING_DIM must be 1536 for text-embedding-3-small, got: {self.embedding_dim}"
        )
```

### Anti-Patterns to Avoid

- **Import lightrag-hku directly in FastAPI process:** LightRAG's entity extraction LLM calls run 10-150 seconds and block the async event loop. Always call over HTTP via `lightrag_service.py`.
- **Use MongoVectorDBStorage:** Requires Atlas Vector Search. Not available on MongoDB Community 7.0. Use NanoVectorDBStorage (file-based, included in the lightrag-hku package).
- **Query LightRAG without user_id in the query string:** Without user isolation at the storage level, omitting user_id from query text risks returning another user's graph nodes.
- **Change EMBEDDING_MODEL or EMBEDDING_DIM after first insert:** NanoVectorDBStorage raises `AssertionError: Embedding dim mismatch` on startup — the only recovery is deleting the vector storage files and re-ingesting all content.
- **Set LightRAG as a required dependency for content generation:** LightRAG queries and inserts must be non-fatal. Content generation must complete even if LightRAG is down.
- **Write to LightRAG from both Thinker (read) and Writer (write):** The routing contract is: Thinker reads from LightRAG, Writer reads from Pinecone, Learning writes to both. No exceptions.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Entity/relationship extraction from content | Custom NLP pipeline, spaCy, regex | LightRAG's built-in extraction with custom `ENTITY_TYPES` | LightRAG handles chunking, co-reference resolution, deduplication, and incremental graph updates — edge cases that take months to get right |
| Graph storage for entity relationships | MongoDB documents with `$lookup` joins | LightRAG's `NetworkXStorage` | Multi-hop traversal (A→B→C→D) is O(1) in NetworkX; it's O(n) in MongoDB document traversal |
| Multi-hop retrieval query | Vector similarity search with re-ranking | LightRAG `hybrid` mode query | LightRAG's hybrid mode combines local entity search + global relationship traversal — cannot be replicated with Pinecone alone |
| REST API for LightRAG | Custom FastAPI wrapper | LightRAG's built-in `lightrag-server` (`lightrag[api]`) | LightRAG ships a complete FastAPI server at port 9621 with Swagger UI, auth support, and streaming |
| Embedding dimension assertion | Custom validator | NanoVectorDBStorage's built-in `AssertionError` | NanoVectorDB raises `AssertionError: Embedding dim mismatch, expected: X, but loaded: Y` automatically — wire this into the startup health check |

**Key insight:** LightRAG is not "yet another vector store." Its value is the graph construction layer — entity deduplication, relationship typing, and multi-hop traversal. Attempting to replicate this with raw MongoDB + Pinecone requires building a graph ETL pipeline, a graph query engine, and a deduplication system. Use LightRAG for what it does, and Pinecone for what it does.

---

## Domain-Specific Entity Extraction Prompt (LRAG-03)

This is the most critical configuration decision in Phase 10. LightRAG's default entity types are `["organization", "person", "geo", "event"]` — entirely wrong for ThookAI's content domain.

### Recommended ENTITY_TYPES for ThookAI

```bash
# In lightrag/.env or docker-compose.yml environment:
ENTITY_TYPES='["topic_domain", "hook_archetype", "emotional_tone", "expertise_signal", "content_format"]'
```

**Definitions:**

| Entity Type | Examples | What to Extract |
|-------------|----------|-----------------|
| `topic_domain` | "startup fundraising", "remote work", "B2B SaaS growth", "leadership psychology" | The substantive subject matter — what the content is about |
| `hook_archetype` | "contrarian take", "personal failure story", "surprising statistic", "step-by-step how-to", "prediction" | The structural pattern used to open or frame the content |
| `emotional_tone` | "vulnerable", "authoritative", "provocative", "analytical", "motivational", "frustrated" | The emotional register the content operates in |
| `expertise_signal` | "10 years in sales", "bootstrapped to $1M", "ex-Google", "YC alumni" | The credibility anchor the user uses |
| `content_format` | "listicle", "essay", "thread-style", "case study", "opinion piece", "interview-format" | The structural form of the content |

**What to SUPPRESS (instruct the LLM to ignore):**
- Platform names: "LinkedIn", "Twitter", "Instagram"
- Time references: "Q3 2024", "last week", "recently"
- Generic nouns: "people", "team", "company", "business"
- Filler phrases: "it's important to", "in today's world"

### Custom PROMPTS Override (for additional fine-tuning)

If `ENTITY_TYPES` env var alone is insufficient, use the Python API override before starting the server:

```python
# In LightRAG sidecar startup code (if using Python API rather than CLI):
from lightrag.prompt import PROMPTS

# Override entity types
PROMPTS["DEFAULT_ENTITY_TYPES"] = [
    "topic_domain", "hook_archetype", "emotional_tone",
    "expertise_signal", "content_format"
]

# Optionally override the full extraction prompt by modifying
# PROMPTS["entity_extraction_system_prompt"] with domain-specific examples
```

### Test Protocol (LRAG-03 Validation Gate)

Before any production ingestion:
1. Select 10 diverse approved posts from the `content_jobs` collection (different platforms, topics, content types)
2. Call `POST /documents/insert_text` on each
3. Call `GET /graph/labels` or `GET /graph/nodes` to inspect extracted entities
4. **Pass criteria:** >70% of extracted entity nodes are one of the 5 domain types; <30% are generic words or platform/time references
5. If test fails: Refine `ENTITY_TYPES` env var and repeat. Do not proceed to production ingestion until pass criteria is met.

---

## Common Pitfalls

### Pitfall 1: LightRAG Embedding Model Lock-In

**What goes wrong:** Changing `EMBEDDING_MODEL` or `EMBEDDING_DIM` after the first document insert causes `AssertionError: Embedding dim mismatch` on startup. Recovery requires deleting all NanoVectorDB files and re-ingesting every approved content item.

**Why it happens:** NanoVectorDBStorage writes the vector dimension to a storage manifest on first insert. Subsequent startup reads this manifest and asserts the configured dimension matches. The lock-in is invisible until a model change is attempted.

**How to avoid:** Set `EMBEDDING_MODEL=text-embedding-3-small` and `EMBEDDING_DIM=1536` in `lightrag/.env` before starting the container. Treat these as permanently frozen. Add `assert_embedding_config()` call in `backend/services/lightrag_service.py` startup logic.

**Warning signs:** Any PR that proposes changing `LIGHTRAG_EMBEDDING_MODEL` or `LIGHTRAG_EMBEDDING_DIM`.

### Pitfall 2: Graph Noise from Default Entity Types

**What goes wrong:** With default entity types, LightRAG extracts "LinkedIn" as an organization, "2024" as an event, and "team" as a concept. The knowledge graph fills with thousands of noise nodes. Thinker retrieval returns irrelevant context.

**Why it happens:** LightRAG's default prompt is domain-agnostic. It was designed for academic papers and general documents, not personal content fingerprinting.

**How to avoid:** Set `ENTITY_TYPES` env var before any insert. Validate extraction quality on 10 posts before production ingestion. The test protocol is documented in the Domain-Specific Entity Extraction section above.

**Warning signs:** Knowledge graph node count exceeds 50 nodes per approved post; most frequent nodes are generic words.

### Pitfall 3: Workspace Isolation Is Application-Layer, Not Storage-Layer

**What goes wrong:** Two users' graph data lives in the same MongoDB collections (prefixed with `thookai_`). A poorly scoped LightRAG query returns User B's entity nodes in User A's response.

**Why it happens:** LightRAG's `MONGODB_WORKSPACE` prefixes collections globally. There is no per-request workspace switching in v1.4.12 (tracked in GitHub issue #2133).

**How to avoid:** Always include `user_id` in query text (as in the code examples above). Name documents with `{user_id}_{job_id}` pattern. The E2E verification test (Phase 16, E2E-03) must specifically test cross-user isolation.

**Warning signs:** LightRAG query response for User A contains mentions of topics User A has never written about.

### Pitfall 4: LightRAG Insert Blocks Content Approval Flow

**What goes wrong:** `insert_content()` call in `capture_learning_signal()` takes 10-60 seconds (entity extraction requires an LLM call). If called synchronously, content approval hangs for this duration.

**Why it happens:** LightRAG's document insert triggers chunking + LLM entity extraction, which is slow. The ThookAI learning agent is called in the approval request path.

**How to avoid:** The LightRAG `POST /documents/insert_text` endpoint processes asynchronously — it returns immediately with a `doc_id` and processes in background. Confirm this is true in production by checking response time on first insert. If needed, wrap the call in `asyncio.create_task()` to fire-and-forget from the approval endpoint.

**Warning signs:** Content approval endpoint response time exceeds 2 seconds when LightRAG is connected.

### Pitfall 5: `initialize_storages()` Not Called on Startup

**What goes wrong:** LightRAG's storage layer requires explicit initialization before the first operation. Skipping this causes cryptic connection errors on first `insert()` or `query()` call.

**Why it happens:** The official Docker image (`ghcr.io/hkuds/lightrag:latest`) handles this internally via its own FastAPI lifespan. But if running LightRAG via Python API directly, `await rag.initialize_storages()` and `await initialize_pipeline_status()` must both be called before handling requests.

**How to avoid:** Use the official Docker image — it handles initialization. If customizing the server startup, add both calls to the FastAPI lifespan `async with` block.

---

## Code Examples

Verified patterns from official sources and project conventions:

### LightRAG Service — Health Check

```python
# backend/services/lightrag_service.py
# Source: LightRAG REST API docs (deepwiki.com/HKUDS/LightRAG)

async def health_check() -> bool:
    """Check if LightRAG sidecar is reachable. Used in server.py lifespan."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{LIGHTRAG_URL}/health")
        return resp.status_code == 200
    except Exception:
        return False
```

### Embedding Dimension Startup Assertion

```python
# backend/services/lightrag_service.py — called from server.py lifespan startup
# Source: LightRAG GitHub issues #355, #2119 — assertion behavior confirmed

async def assert_lightrag_embedding_config() -> None:
    """Fail loudly if LightRAG embedding config is wrong.

    Called once at FastAPI startup to catch misconfiguration early.
    Does NOT block startup if LightRAG is unreachable (sidecar may not be up yet).
    """
    if not settings.lightrag.is_configured():
        logger.warning("LightRAG not configured — knowledge graph features disabled")
        return

    # Assert the embedding model config matches our locked decision
    try:
        settings.lightrag.assert_embedding_config()
        logger.info(
            f"LightRAG embedding config validated: {settings.lightrag.embedding_model} "
            f"({settings.lightrag.embedding_dim} dims)"
        )
    except AssertionError as e:
        logger.critical(f"LightRAG embedding config mismatch: {e}")
        raise  # This is a CRITICAL misconfiguration — fail startup
```

### LightRAG Query — Thinker Integration

```python
# Source: LightRAG REST API docs + thinker.py project pattern
# Hybrid mode: combines local entity search + global relationship traversal

async def query_knowledge_graph(
    user_id: str,
    topic: str,
    mode: str = "hybrid",
) -> str:
    """Query knowledge graph for topic gap analysis.

    Returns empty string on any failure — caller must handle gracefully.
    Timeout: 15s (aggressive — Thinker prompt building must stay fast).
    """
    if not settings.lightrag.is_configured():
        return ""

    query = (
        f"For user {user_id}: What topic domains, hook archetypes, and emotional tones "
        f"have already been used when writing about '{topic}'? "
        f"What angles, framings, and approaches have NOT been explored yet?"
    )
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{LIGHTRAG_URL}/query",
                json={
                    "query": query,
                    "param": {"mode": mode, "top_k": 20},
                },
                headers={"X-API-Key": LIGHTRAG_API_KEY} if LIGHTRAG_API_KEY else {},
            )
        resp.raise_for_status()
        return resp.json().get("response", "")
    except Exception as e:
        logger.warning(f"LightRAG query failed for user {user_id} (non-fatal): {e}")
        return ""
```

### Document Insert — Learning Agent Integration

```python
# Source: LightRAG REST API docs (/documents/insert_text endpoint)
# Processing is async server-side — returns immediately with doc_id

async def insert_content(user_id: str, content: str, metadata: dict) -> bool:
    if not settings.lightrag.is_configured():
        return False

    doc_id = f"{user_id}_{metadata.get('job_id', '')}"
    # Prefix with user_id to assist entity extraction scoping
    tagged_content = f"[CREATOR:{user_id}]\n\n{content}"
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{LIGHTRAG_URL}/documents/insert_text",
                json={
                    "text": tagged_content,
                    "doc_id": doc_id,
                },
                headers={"X-API-Key": LIGHTRAG_API_KEY} if LIGHTRAG_API_KEY else {},
            )
        resp.raise_for_status()
        logger.info(f"LightRAG insert queued: user={user_id} doc={doc_id}")
        return True
    except Exception as e:
        logger.warning(f"LightRAG insert failed for {doc_id} (non-fatal): {e}")
        return False
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Vector similarity only (Pinecone) | Graph + vector dual-store (LightRAG + Pinecone) | v2.0 (this phase) | Enables multi-hop "angles NOT used" retrieval — not possible with pure vector similarity |
| Default entity types (organization, person, geo, event) | Domain-specific types (topic_domain, hook_archetype, emotional_tone) | v2.0 (this phase) | Graph noise reduced from ~80 generic nodes/post to ~10 signal nodes/post |
| Thinker relies on fatigue shield only | Thinker queries knowledge graph + fatigue shield | v2.0 (this phase) | Angle selection informed by full content history, not just recent pattern counts |
| Learning agent writes to Pinecone only | Learning agent writes to Pinecone + LightRAG | v2.0 (this phase) | Both similarity and structural knowledge captured on approval |

**Deprecated/outdated patterns:**
- `MongoVectorDBStorage`: Do not use. Requires Atlas Vector Search. Confirmed unavailable on MongoDB Community 7.0 (the version in docker-compose.yml).
- Inline LightRAG in ThookAI process: Do not do this. LightRAG's entity extraction LLM calls block async event loop.
- Per-user LightRAG containers: Not scalable beyond ~10 users. Use single container with application-layer user_id isolation.

---

## Open Questions

1. **LightRAG per-request workspace switching**
   - What we know: `MONGODB_WORKSPACE` is a startup-time global. GitHub issue #2133 documents this as an open limitation as of 2026-04. Workspace switching per-request requires patching `ClientManager` singleton — unsupported.
   - What's unclear: Whether the LightRAG maintainers will ship native per-request workspace switching in v1.5.x.
   - Recommendation: Proceed with user_id-in-query approach for Phase 10. Monitor GitHub issue #2133. If native support ships before Phase 16 E2E, upgrade the isolation strategy.

2. **LightRAG insert latency with entity extraction**
   - What we know: Entity extraction requires an LLM call (gpt-4o-mini in our config). This takes 2-30 seconds. The `/documents/insert_text` endpoint is documented as async (returns immediately).
   - What's unclear: Whether the Docker image's REST server truly returns immediately or blocks until extraction completes.
   - Recommendation: Measure response time on first insert in dev environment during Wave 0. If latency >2s, wrap the insert call in `asyncio.create_task()` in the learning agent.

3. **NanoVectorDBStorage persistence across container restarts**
   - What we know: NanoVectorDBStorage uses file-based storage. The docker-compose adds a named volume `lightrag_data` mounted to `/app/data/rag_storage`.
   - What's unclear: Whether the NanoVectorDB files survive container image updates (they should with a named volume, but this needs verification).
   - Recommendation: Include a smoke test in Wave 0 that inserts a document, restarts the container, then queries for the inserted content.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Docker | LightRAG sidecar container | Available (project uses Docker Compose) | See docker-compose.yml | None — Docker required |
| MongoDB 7.0 | LightRAG KV + doc status storage | Available (in docker-compose.yml) | mongo:7.0 | None — already required for ThookAI |
| OpenAI API key (`OPENAI_API_KEY`) | LightRAG entity extraction LLM (gpt-4o-mini) + embeddings (text-embedding-3-small) | Available (in backend .env as `OPENAI_API_KEY`) | gpt-4o-mini / text-embedding-3-small | If key absent, LightRAG entity extraction fails — sidecar will not function. Must be included in lightrag/.env. |
| Port 9621 | LightRAG REST API | Available (not currently in use) | — | — |
| `httpx` 0.28.1 | `lightrag_service.py` HTTP calls | Available (in requirements.txt) | 0.28.1 | None — already in stack |
| `lightrag-hku` | `backend/requirements.txt` (if Python API used) | Not installed | 1.4.12 | N/A — using Docker image, not Python package directly |

**Missing dependencies with no fallback:**
- `OPENAI_API_KEY` must be present in `lightrag/.env` (the sidecar's env file). The ThookAI backend's `.env` has `OPENAI_API_KEY` — but the LightRAG container needs its own copy since it runs as a separate process.

**Missing dependencies with fallback:**
- LightRAG sidecar down: All `lightrag_service.py` calls return empty string / False. Content generation proceeds without knowledge graph context (graceful degradation).

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.0.0 + pytest-asyncio 0.23.0 |
| Config file | `backend/pytest.ini` — `asyncio_mode = auto` |
| Quick run command | `cd backend && pytest tests/test_lightrag_knowledge_graph.py -x` |
| Full suite command | `cd backend && pytest` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| LRAG-01 | LightRAG sidecar starts and /health returns 200 | integration (docker) | `pytest tests/test_lightrag_knowledge_graph.py::TestLightRAGHealth -x` | ❌ Wave 0 |
| LRAG-02 | User A query never returns User B content | integration | `pytest tests/test_lightrag_knowledge_graph.py::TestUserIsolation -x` | ❌ Wave 0 |
| LRAG-03 | Entity extraction produces domain-relevant nodes only | integration | `pytest tests/test_lightrag_knowledge_graph.py::TestEntityExtraction -x` | ❌ Wave 0 |
| LRAG-04 | Startup assertion fails with wrong embedding model | unit | `pytest tests/test_lightrag_knowledge_graph.py::TestEmbeddingAssertion -x` | ❌ Wave 0 |
| LRAG-05 | Thinker prompt includes LightRAG context when available | unit (mock) | `pytest tests/test_lightrag_knowledge_graph.py::TestThinkerIntegration -x` | ❌ Wave 0 |
| LRAG-06 | Approving content triggers both Pinecone and LightRAG writes | unit (mock) | `pytest tests/test_lightrag_knowledge_graph.py::TestDualWrite -x` | ❌ Wave 0 |
| LRAG-07 | Writer agent has no import of lightrag_service | static (grep) | `pytest tests/test_lightrag_knowledge_graph.py::TestRoutingContract -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `cd backend && pytest tests/test_lightrag_knowledge_graph.py -x`
- **Per wave merge:** `cd backend && pytest`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `backend/tests/test_lightrag_knowledge_graph.py` — covers LRAG-01 through LRAG-07
- [ ] `backend/services/lightrag_service.py` — must exist before tests can import it
- [ ] `backend/config.py` — `LightRAGConfig` dataclass addition
- [ ] `lightrag/.env` — LightRAG sidecar environment file

---

## Project Constraints (from CLAUDE.md)

The following CLAUDE.md directives apply directly to this phase:

| Directive | Impact on Phase 10 |
|-----------|-------------------|
| Never import `os.environ.get()` directly — use `settings.*` from `config.py` | `LightRAGConfig` dataclass must be added to `config.py`. `lightrag_service.py` reads `settings.lightrag.url`, not `os.environ.get('LIGHTRAG_URL')`. |
| Never introduce new Python packages without adding to `requirements.txt` | Add `lightrag-hku==1.4.12` to `backend/requirements.txt`. However: if using the Docker image exclusively for the sidecar (recommended), the Python package is NOT needed in the FastAPI process. Only add it if Python API usage is planned. |
| All settings via `config.py` dataclasses | `LightRAGConfig` follows the existing pattern — `@dataclass` with `field(default_factory=...)`. |
| Never commit to `main` — branch from `dev`, PR targeting `dev` | Branch: `feat/lightrag-knowledge-graph` |
| Branch naming: `feat/short-description` | Branch: `feat/lightrag-knowledge-graph` |
| After any change to `backend/agents/` — verify full pipeline flow | After modifying `thinker.py` and `learning.py`, run the pipeline smoke test: `POST /api/content/generate {platform: "linkedin", content_type: "post", raw_input: "test"}` and confirm job reaches `reviewing` status within 60 seconds. |
| Database pattern: `from database import db` with Motor async | No direct MongoDB calls from `lightrag_service.py` — all LightRAG DB operations happen inside the sidecar. ThookAI backend only calls the REST API. |
| LLM model: `claude-sonnet-4-20250514` | LightRAG's entity extraction uses `gpt-4o-mini` (configured in the sidecar's `.env`) — this is separate from ThookAI's LLM. ThookAI's pipeline agents continue using `claude-sonnet-4-20250514`. |

---

## Sources

### Primary (HIGH confidence)

- [lightrag-hku on PyPI](https://pypi.org/project/lightrag-hku/) — Version 1.4.12 confirmed (2026-03-27), Python >=3.10, MIT license
- [HKUDS/LightRAG GitHub](https://github.com/HKUDS/LightRAG) — Architecture, storage backends, embedding lock-in, MongoDB workspace prefix
- [LightRAG API README](https://github.com/HKUDS/LightRAG/blob/main/lightrag/api/README.md) — REST endpoints: `/documents/insert_text`, `/query`, `/health`; workspace config
- [LightRAG env.example](https://github.com/HKUDS/LightRAG/blob/main/env.example) — `EMBEDDING_MODEL`, `EMBEDDING_DIM`, `ENTITY_TYPES`, `MONGO_URI`, `MONGODB_WORKSPACE` env vars
- [LightRAG docker-compose.yml](https://github.com/HKUDS/LightRAG/blob/main/docker-compose.yml) — Official Docker deployment; port 9621; ghcr.io/hkuds/lightrag:latest image
- [DeepWiki LightRAG API Server](https://deepwiki.com/HKUDS/LightRAG/4-api-server) — Full endpoint reference, query modes, MongoDB config, workspace isolation mechanics
- [LightRAG GitHub issue #355](https://github.com/HKUDS/LightRAG/issues/355) — `AssertionError: Embedding dim mismatch` confirmed; occurs on startup/loading
- [LightRAG GitHub issues #2119, #2233](https://github.com/HKUDS/LightRAG/issues/2119) — Embedding dimension mismatch in production; confirmed recovery requires full rebuild

### Secondary (MEDIUM confidence)

- [LightRAG GitHub issue #2133](https://github.com/HKUDS/LightRAG/issues/2133) — Multi-tenant workspace isolation open problem; no native per-request workspace switching in v1.4.12
- [LightRAG GitHub issue #308 + Discussion #1672](https://github.com/HKUDS/LightRAG/issues/308) — `PROMPTS["DEFAULT_ENTITY_TYPES"]` runtime override and `ENTITY_TYPES` env var customization; some caveats around entity type validation
- [LightRAG prompt.py](https://github.com/HKUDS/LightRAG/blob/main/lightrag/prompt.py) — Default entity types `["organization", "person", "geo", "event"]`, `{entity_types}` template parameter

### Tertiary (LOW confidence, flag for validation)

- [Custom entity type override via ENTITY_TYPES env var](https://github.com/HKUDS/LightRAG/discussions/1672) — Community reports it works, but some users hit "empty content from OpenAI API" errors with unusual entity type names. Validate with ThookAI-specific types before production.

---

## Metadata

**Confidence breakdown:**

- Standard stack: HIGH — lightrag-hku 1.4.12 on PyPI confirmed; Docker image confirmed; MongoDB backend types verified; NanoVectorDBStorage confirmed as file-based (no Atlas requirement)
- Architecture: MEDIUM-HIGH — sidecar pattern verified; per-user isolation via user_id-in-query is pragmatic but not storage-level guarantee; integration code patterns are derived from documented API + project conventions
- Pitfalls: HIGH — embedding lock-in confirmed via multiple GitHub issues; graph noise is architecture-reasoned and verified by domain analysis; workspace isolation limitation confirmed in issue #2133
- Entity extraction customization: MEDIUM — `ENTITY_TYPES` env var confirmed functional; full custom prompt override requires `PROMPTS` dict patch which is community-verified but not in official docs

**Research date:** 2026-04-01
**Valid until:** 2026-05-01 (LightRAG releases weekly — re-verify before planning if >30 days elapse)
