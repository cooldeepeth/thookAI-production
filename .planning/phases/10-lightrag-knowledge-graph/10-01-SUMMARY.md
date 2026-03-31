---
phase: 10-lightrag-knowledge-graph
plan: "01"
subsystem: infrastructure
tags: [lightrag, knowledge-graph, config, docker, sidecar]
dependency_graph:
  requires: []
  provides: [lightrag-config, lightrag-service-client, lightrag-docker-service]
  affects: [backend/agents/thinker.py, backend/agents/learning.py]
tech_stack:
  added: [lightrag-sidecar, httpx-lightrag-client]
  patterns: [sidecar-service-pattern, non-fatal-degradation, embedding-config-assertion]
key_files:
  created:
    - backend/services/lightrag_service.py
    - lightrag/.env.example
  modified:
    - backend/config.py
    - backend/.env.example
    - docker-compose.yml
    - backend/server.py
decisions:
  - "LightRAG uses NanoVectorDBStorage (not MongoVectorDBStorage) — maintains hybrid architecture (Pinecone for persona similarity, LightRAG NanoVDB for graph-adjacent vectors)"
  - "lightrag/.env is gitignored (contains OPENAI_API_KEY) — lightrag/.env.example committed instead"
  - "Per-user isolation via doc_filter_func lambda in query param — not just natural language scoping"
  - "insert_content metadata header includes CREATOR/PLATFORM/TYPE/EDITED tags for entity extraction context"
  - "Startup assertion: production blocks on AssertionError, dev mode warns and continues"
metrics:
  duration_minutes: 2
  completed_date: "2026-04-01"
  tasks_completed: 2
  files_changed: 6
---

# Phase 10 Plan 01: LightRAG Infrastructure Foundation Summary

LightRAG sidecar infrastructure deployed: Docker service using ghcr.io/hkuds/lightrag with MongoKVStorage + NanoVectorDBStorage + NetworkXStorage, LightRAGConfig dataclass in config.py with frozen embedding assertion, and HTTP service client with 4 async functions (health_check, assert_lightrag_embedding_config, insert_content, query_knowledge_graph) with non-fatal degradation pattern.

## What Was Built

### Task 1: LightRAGConfig dataclass + docker-compose service + lightrag/.env

Added `LightRAGConfig` dataclass to `backend/config.py` following the existing N8nConfig pattern. The dataclass has 4 fields (`url`, `api_key`, `embedding_model`, `embedding_dim`), `is_configured()` for feature-gating, and `assert_embedding_config()` which enforces the frozen embedding model decision (text-embedding-3-small, 1536 dims) with explicit AssertionErrors.

Added `lightrag: LightRAGConfig` to the `Settings` dataclass after the `n8n` field.

Added the `lightrag` service to `docker-compose.yml` with:
- `ghcr.io/hkuds/lightrag:latest` image
- MongoDB storage backends: `MongoKVStorage` (KV), `MongoDocStatusStorage` (doc status)
- `NanoVectorDBStorage` for vector storage (NOT MongoVectorDBStorage — preserves hybrid architecture)
- `NetworkXStorage` for graph traversal
- `MONGO_DATABASE=thookai_lightrag` — isolated from the ThookAI app database
- Domain-specific `ENTITY_TYPES`: topic_domain, hook_archetype, emotional_tone, expertise_signal, content_format
- `lightrag_data` named volume for NanoVectorDB file persistence

Created `lightrag/.env.example` with frozen embedding config documentation (actual `lightrag/.env` is gitignored via `*.env` rule since it contains `OPENAI_API_KEY`).

Documented all `LIGHTRAG_*` env vars in `backend/.env.example`.

### Task 2: lightrag_service.py HTTP client + server.py startup assertion

Created `backend/services/lightrag_service.py` with the RETRIEVAL ROUTING CONTRACT documented in the module docstring:
- **Thinker agent**: calls `query_knowledge_graph()` (READ)
- **Learning agent**: calls `insert_content()` (WRITE)
- **Writer agent**: Pinecone only (never imports this module)

**`health_check()`**: 5s timeout, returns bool. Non-fatal on any exception.

**`assert_lightrag_embedding_config()`**: Validates embedding model and dimensions match frozen config. Raises `AssertionError` on mismatch (blocking). Returns gracefully if LightRAG is not configured or unreachable.

**`insert_content()`**: 30s timeout, non-fatal. Builds a metadata header (`[CREATOR:{user_id}] [PLATFORM:...] [TYPE:...] [EDITED:...]`) prepended to the content text so LightRAG entity extraction gets structured context. Full metadata dict also passed in the payload for storage-level filtering.

**`query_knowledge_graph()`**: 15s timeout (aggressive — must not slow Thinker prompt building), non-fatal. Passes `doc_filter_func: "lambda meta: meta.get('user_id') == '{user_id}'"` in the `param` dict for storage-level per-user isolation. Returns empty string on any failure so Thinker proceeds without graph context.

Added LightRAG startup assertion to `server.py` lifespan, after DB index creation:
```python
try:
    from services.lightrag_service import assert_lightrag_embedding_config
    await assert_lightrag_embedding_config()
except AssertionError:
    if settings.app.is_production:
        raise  # Block startup in production
    logger.warning("LightRAG embedding config invalid - knowledge graph disabled in dev mode")
```

## Decisions Made

1. **NanoVectorDBStorage over MongoVectorDBStorage**: Preserves the hybrid architecture principle (Pinecone for persona similarity, LightRAG NanoVDB for graph-adjacent vector retrieval). MongoVectorDB would require Atlas Vector Search and adds operational complexity.

2. **lightrag/.env gitignored, .env.example committed**: The `*.env` gitignore rule already covers `lightrag/.env`. Created `lightrag/.env.example` as the canonical template so the frozen embedding config decision is visible in source control.

3. **Storage-level user isolation via doc_filter_func**: Natural language scoping in the query string is insufficient for true isolation. The `doc_filter_func` lambda in the `param` dict provides filter-based isolation at the retrieval layer. If LightRAG REST API does not support serialized lambdas, fallback is the `ids` prefix pattern (`CREATOR:{user_id}_*`).

4. **Metadata header in insert_content**: The `[CREATOR:...] [PLATFORM:...] [TYPE:...] [EDITED:...]` prefix in the document text gives LightRAG's entity extraction LLM (gpt-4o-mini) structured context about the content's provenance without requiring schema changes.

5. **15s query timeout**: Thinker agent must remain fast. Knowledge graph enrichment is an enhancement, not a hard dependency — 15s is aggressive enough to prevent pipeline slowdown.

## Deviations from Plan

None - plan executed exactly as written. The `doc_filter_func` approach for user isolation was explicitly specified in the plan as the primary strategy, with the `ids` prefix fallback noted as contingency.

## Known Stubs

None. This plan is infrastructure-only (config, Docker service, HTTP client). No agent wiring occurs in this plan — that is Phase 10, Plans 02 and 03.

## Self-Check: PASSED
