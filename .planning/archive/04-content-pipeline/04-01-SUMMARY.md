---
phase: 04-content-pipeline
plan: "01"
subsystem: content-pipeline
tags: [testing, pipeline, orchestrator, uom, fatigue-shield, vector-store, pinecone]
dependency_graph:
  requires: []
  provides:
    - test coverage for PIPE-02 (LangGraph orchestrator)
    - test coverage for PIPE-03 (UOM directive injection)
    - test coverage for PIPE-04 (fatigue shield integration)
    - test coverage for PIPE-05 (vector store enrichment)
  affects:
    - backend/agents/orchestrator.py
    - backend/agents/thinker.py
    - backend/agents/writer.py
    - backend/agents/learning.py
tech_stack:
  added: []
  patterns:
    - langgraph module mock for local-env testing without langgraph installed
    - AsyncMock + patch for isolating agent dependencies from LLM calls
    - _import_orchestrator_module() helper to mock langgraph.graph at module import time
key_files:
  created:
    - backend/tests/test_pipeline_integration.py
  modified: []
decisions:
  - Mock langgraph.graph at sys.modules level to allow testing orchestrator pure functions (quality_gate, should_research) in environments without langgraph installed
  - Verify integration points by checking prompt content rather than call counts alone — more robust against refactoring
  - 29 tests cover both success paths and error-resilience (non-fatal exception handling)
metrics:
  duration: "~5 minutes"
  completed_date: "2026-03-31"
  tasks_completed: 2
  files_modified: 1
---

# Phase 04 Plan 01: Pipeline Integration Tests Summary

29 pytest unit tests proving PIPE-02 through PIPE-05 integration requirements for the LangGraph orchestrator, UOM directive injection, fatigue shield, and Pinecone vector store enrichment.

## What Was Built

`backend/tests/test_pipeline_integration.py` — 29 unit tests using `pytest.mark.asyncio` and `unittest.mock` to verify the content pipeline's four advanced subsystems are correctly wired together.

### PIPE-02: LangGraph Orchestrator (6 tests)
- `build_content_pipeline()` returns a compiled graph with `ainvoke` method
- `PipelineState` TypedDict contains all 17 required keys
- `quality_gate()` returns `"pass"` on `overall_pass=True`, `"rewrite"` when loops not exhausted, `"accept"` when budget exhausted
- `should_research()` correctly reads `commander_output.research_needed` with `True` default
- `_run_agent_pipeline_inner()` falls back to legacy pipeline on `ImportError`
- General exceptions from orchestrator also trigger legacy fallback

### PIPE-03: UOM Directive Injection (5 tests)
- `run_thinker()` calls `get_agent_directives(user_id, "thinker")` and injects `UOM CONSTRAINTS` section into prompt
- `run_writer()` calls `get_agent_directives(user_id, "writer")` and injects `ADAPTIVE STYLE DIRECTIVES` section
- Both agents continue without UOM (non-fatal) when `get_agent_directives` raises any exception

### PIPE-04: Fatigue Shield (7 tests)
- `_build_fatigue_prompt_section()` returns empty string for `shield_status="healthy"` or `None`
- Returns constraint text with risk factor details when `shield_status="warning"` or `"critical"`
- Returns empty when risk_factors have no `detail` key and no recommendations
- `run_thinker()` injects `CONTENT DIVERSITY CONSTRAINTS` section when fatigue is non-healthy
- Legacy pipeline calls `get_pattern_fatigue_shield` before Thinker and passes result as `fatigue_context`

### PIPE-05: Vector Store / Pinecone (11 tests)
- `_fetch_style_examples()` calls `query_similar_content(user_id, raw_input, top_k=3, similarity_threshold=0.65)`
- Returns formatted `PREVIOUSLY APPROVED CONTENT IN THIS VOICE` section with content previews
- Returns empty string when no results, on exceptions (non-fatal), or when `user_id` is empty
- `run_writer()` includes style examples section in generated prompt
- `capture_learning_signal(action="approved")` calls `upsert_approved_embedding` with correct `user_id`, `content_text`, and `content_id`
- `capture_learning_signal(action="rejected")` does NOT call `upsert_approved_embedding`

## Task 2: Verification — No Code Fixes Required

All integration points in `thinker.py`, `writer.py`, `orchestrator.py`, and `learning.py` were already correctly wired. All 29 tests passed on first run after fixing the langgraph import issue in tests (deviation below).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Orchestrator module import blocked by langgraph not being installed locally**
- **Found during:** Task 1 (TDD Red phase)
- **Issue:** `orchestrator.py` imports `from langgraph.graph import END, StateGraph` at module level. In the local Python 3.13 development environment, `langgraph` is not installed. This caused `from agents.orchestrator import quality_gate` to raise `ModuleNotFoundError`, making 9 tests fail.
- **Fix:** Created `_import_orchestrator_module()` helper function in the test file that mocks `langgraph.graph` with a minimal `StateGraph` and `END` stub, then imports the orchestrator module. This allows testing pure functions (`quality_gate`, `should_research`, `PipelineState`) without langgraph installed.
- **Files modified:** `backend/tests/test_pipeline_integration.py` (tests only, no production code changed)
- **Rationale:** This is correct behavior — production environments have langgraph installed (it's in `requirements.txt`). The fix is test-only and doesn't affect production. The `build_content_pipeline()` test now tests with the mock graph, correctly verifying the function returns something with `ainvoke`.

## Known Stubs

None — this plan creates tests only, no stub data or placeholder implementations.

## Self-Check: PASSED

**Files created:**
- backend/tests/test_pipeline_integration.py: FOUND

**Commits:**
- 3f043fd: FOUND (test(04-01): add pipeline integration tests)
- f396017: FOUND (test(04-01): confirm all integration points wired correctly)

**Test count:** 29 tests, all passing
