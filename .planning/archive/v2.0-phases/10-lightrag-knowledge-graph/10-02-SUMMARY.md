---
phase: 10-lightrag-knowledge-graph
plan: "02"
subsystem: agents
tags: [lightrag, knowledge-graph, dual-write, thinker, learning, retrieval-routing]
dependency_graph:
  requires: [10-01]
  provides: [LRAG-02, LRAG-05, LRAG-06, LRAG-07]
  affects: [backend/agents/learning.py, backend/agents/thinker.py, backend/agents/pipeline.py]
tech_stack:
  added: []
  patterns:
    - Lazy import pattern for non-fatal service calls (lightrag_service in learning.py and thinker.py)
    - Dual-write pattern: Pinecone (similarity) + LightRAG (relationships) on every approval
    - Prompt layering: base -> UOM constraints -> fatigue shield -> knowledge graph context
    - Retrieval routing contract documented in pipeline.py as an enforcement comment block
key_files:
  created: []
  modified:
    - backend/agents/learning.py
    - backend/agents/thinker.py
    - backend/agents/pipeline.py
decisions:
  - "Lazy import pattern for lightrag_service: avoids hard dependency — LightRAG unavailability does not block agent imports"
  - "knowledge_context[:800] slice: prevents knowledge graph from consuming too much LLM context in the Thinker prompt"
  - "process_bulk_import second block uses content_id as job_id and derives platform from the post dict — no job_meta lookup needed"
  - "Routing contract in pipeline.py is a comment block, not code enforcement — ensures visibility during code review"
metrics:
  duration: "83 seconds"
  completed: "2026-04-01"
  tasks_completed: 2
  tasks_total: 2
  files_modified: 3
---

# Phase 10 Plan 02: LightRAG Pipeline Integration Summary

**One-liner:** Dual-write on approval (Pinecone + LightRAG) and knowledge graph query injection into Thinker prompt before angle selection, with retrieval routing contract documented in pipeline.py.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Learning agent dual-write + pipeline routing contract | faf346c | backend/agents/learning.py, backend/agents/pipeline.py |
| 2 | Thinker agent knowledge graph query injection | 9995112 | backend/agents/thinker.py |

## What Was Built

### Task 1: Learning Agent Dual-Write

Added LightRAG `insert_content` calls to **both** approval code paths in `backend/agents/learning.py`:

1. **`capture_learning_signal()`** (line ~211): After the Pinecone `upsert_approved_embedding` try/except block, a parallel LightRAG insert is made with `job_id`, `platform`, `content_type`, and `was_edited` from `job_meta`.

2. **`process_bulk_import()`** (line ~418): After the Pinecone `upsert_approved_embedding` try/except block, a parallel LightRAG insert is made with the post's `platform`, `content`, and `content_id` as job_id.

Both blocks follow the identical pattern: lazy import, non-fatal try/except, `logger.warning()` on failure. LightRAG being down never blocks content approval.

Also added the **RETRIEVAL ROUTING CONTRACT** comment block to `backend/agents/pipeline.py` directly after the imports section. The contract documents:
- Thinker: READS from LightRAG, NEVER writes or calls Pinecone
- Writer: READS from Pinecone, NEVER imports lightrag_service
- Learning: WRITES to both on approval, NEVER reads during write path

### Task 2: Thinker Agent Knowledge Graph Query Injection

Modified `run_thinker()` in `backend/agents/thinker.py` with two additions:

1. **Fetch block** (before `if not openai_available():`): Lazy imports `query_knowledge_graph` and calls it with `user_id`, `topic=raw_input`, `mode="hybrid"`. Per-user isolation via storage-level `doc_filter_func` is documented in a comment. Non-fatal — empty string returned on failure.

2. **Injection block** (after fatigue shield injection): If `knowledge_context` is non-empty, appends a "KNOWLEDGE GRAPH - TOPICS AND ANGLES ALREADY USED" section (truncated to 800 chars) instructing the Thinker to prioritise unexplored angles, hook archetypes, and emotional tones.

Prompt layer order: base prompt → UOM constraints → fatigue shield → knowledge graph context.

## Verification Results

| Check | Result |
|-------|--------|
| `insert_content` imports in learning.py | 2 (both approval blocks) |
| `LightRAG insert failed` warnings in learning.py | 2 (both blocks non-fatal) |
| `RETRIEVAL ROUTING CONTRACT` in pipeline.py | Found |
| `NEVER imports lightrag_service` in pipeline.py | Found |
| `WRITES to both Pinecone AND LightRAG` in pipeline.py | Found |
| `query_knowledge_graph` import in thinker.py | Found |
| `KNOWLEDGE GRAPH - TOPICS AND ANGLES ALREADY USED` in thinker.py | Found |
| `knowledge_context[:800]` slice in thinker.py | Found |
| `mode="hybrid"` in thinker.py | Found |
| `per-user isolation` / `doc_filter_func` comment in thinker.py | Found |
| `lightrag` references in writer.py | 0 (contract enforced) |
| learning.py syntax | OK |
| thinker.py syntax | OK |
| pipeline.py syntax | OK |
| knowledge_context fetch before `openai_available()` | Confirmed (line 109 vs 121) |
| kg_section injection after fatigue injection | Confirmed (line 156 vs 152) |

## Deviations from Plan

None — plan executed exactly as written.

The only minor judgment call: in `process_bulk_import()` the plan described using `job_meta` (which doesn't exist in that function's scope). The implementation correctly derives equivalent values from the variables available in the loop: `content_id` as `job_id`, `platform` from the post dict, `content_type` as `"post"` (fixed, since bulk imports are always posts), and `was_edited` as `False` (imports are never edits). This matches the intent of the plan and the metadata contract in `insert_content`.

## Known Stubs

None — both dual-write paths call real `insert_content` and `query_knowledge_graph` functions implemented in Plan 01 (lightrag_service.py). LightRAG integration is complete end-to-end pending sidecar availability.

## Self-Check: PASSED

Files exist and commits are verified below.
