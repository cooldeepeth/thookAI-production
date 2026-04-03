---
phase: 19-core-features
plan: 01
subsystem: backend/tests/core
tags: [testing, pipeline-agents, orchestrator, langgraph, mocking]
dependency_graph:
  requires: []
  provides: [core-agent-test-suite, orchestrator-node-tests, pipeline-test-fixtures]
  affects: [backend/tests/core, backend/agents]
tech_stack:
  added: []
  patterns:
    - "Module-level patch target: agents.X.LlmChat not services.llm_client.LlmChat"
    - "LangGraph mock via sys.modules pre-seeding before orchestrator import"
    - "Capturing async side_effect for prompt injection verification"
key_files:
  created:
    - backend/tests/core/__init__.py
    - backend/tests/core/conftest.py
    - backend/tests/core/test_pipeline_agents.py
    - backend/tests/core/test_orchestrator_nodes.py
  modified: []
decisions:
  - "Patch agents.commander.LlmChat (module-level import) not services.llm_client.LlmChat — target the reference used at call time"
  - "Capturing prompt: use side_effect async function with shared dict, not return_value"
  - "Mock run_thinker signature must include all positional and keyword args matching the actual function"
metrics:
  duration_seconds: 477
  completed_date: "2026-04-03"
  tasks_completed: 2
  tasks_total: 2
  files_created: 4
  files_modified: 0
---

# Phase 19 Plan 01: Core Pipeline Agent and Orchestrator Tests Summary

Comprehensive isolated unit tests for all 5 content pipeline agents and the LangGraph orchestrator nodes, using deterministic LLM mocks and zero network calls.

## What Was Built

50 net-new tests in `backend/tests/core/` covering the full agent I/O contract and orchestrator routing logic:

- `conftest.py` — shared fixtures: `mock_llm_generate`, `make_persona_card`, `make_pipeline_state`, `mock_db_collections`
- `test_pipeline_agents.py` — 25 tests across 5 agent classes
- `test_orchestrator_nodes.py` — 25 tests across all orchestrator nodes

## Tasks Completed

| Task | Description | Commit | Status |
|------|-------------|--------|--------|
| 1 | tests/core/ package with fixtures and pipeline agent tests | 50215ab | Done |
| 2 | LangGraph orchestrator node tests and quality gate routing | 452ced6 | Done |

## Test Coverage Summary

**TestCommanderAgent (5 tests)**
- Returns valid JSON keys when LLM available
- Falls back to _mock_commander when no LLM
- Strips markdown code fencing from response
- Falls back gracefully on invalid JSON
- Anti-repetition prompt injected into message

**TestScoutAgent (5 tests)**
- Returns findings with valid Perplexity key (respx mock)
- Falls back to _mock_research with placeholder key
- Handles Perplexity timeout gracefully
- Enriches with Obsidian vault when user_id provided
- Skips Obsidian when user_id is None

**TestThinkerAgent (5 tests)**
- Returns valid strategy JSON keys
- Falls back to _mock_thinker when no LLM
- Injects fatigue constraints into prompt when shield_status=warning
- Skips fatigue injection when status=healthy
- Injects LightRAG knowledge graph context when configured

**TestWriterAgent (5 tests)**
- Returns dict with non-empty draft key
- Falls back to _mock_writer when no Anthropic
- Applies Indian English rules (regional_english=IN)
- Injects vector store style examples into prompt
- Includes X/Twitter 280-char platform rules

**TestQCAgent (5 tests)**
- Returns dict with all 7 score keys
- Falls back to _mock_qc when no OpenAI
- Handles garbled JSON from LLM without raising
- Calls score_repetition_risk when user_id provided
- Skips anti_repetition when user_id is None

**TestCommanderNode (3 tests)**
- Updates state with commander_output and current_agent
- Passes persona_card from state to run_commander
- Re-raises exception (error propagates up)

**TestScoutNode (3 tests)**
- Returns scout_output on success
- Returns graceful fallback on general exception
- Returns fallback on asyncio.TimeoutError

**TestThinkerNode (2 tests)**
- Updates state with thinker_output and current_agent
- Extracts _fatigue_data from commander_output and passes as fatigue_context

**TestWriterNode (2 tests)**
- Sets draft from run_writer result
- Handles empty draft dict without raising

**TestQCNode (3 tests)**
- Updates state with qc_output scores
- Increments qc_loop_count by 1 per call
- Accumulates feedback history with loop tags

**TestQualityGate (5 tests)**
- Returns 'pass' when overall_pass=True
- Returns 'rewrite' when fail and loops remain
- Returns 'accept' when qc_loop_count == MAX_QC_LOOPS
- Returns 'accept' when qc_loop_count > MAX_QC_LOOPS
- Handles missing qc_output (treats as fail)

**TestShouldResearch (3 tests)**
- Returns True when research_needed=True
- Returns False when research_needed=False
- Defaults to True when commander_output absent (safe default)

**TestHookDebateNode (2 tests)**
- Scores multiple hooks via LLM debate, selects winner
- Shortcircuits with single hook (skipped=True)

**TestFinalizeNode (2 tests)**
- Sets final_content equal to state draft
- Calls db.content_jobs.update_one with job_id and status=completed

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Wrong patch target for module-level imports**
- **Found during:** Task 1, first test run (8 failures)
- **Issue:** Tests patching `services.llm_client.LlmChat.send_message` and `services.llm_keys.openai_available` — these are the original modules but agents import these at module load time, so patching the source does not affect already-bound names inside each agent module.
- **Fix:** Changed all patches to target agent module imports: `agents.commander.LlmChat`, `agents.commander.openai_available`, etc. Added `_make_mock_llm_chat()` and `_make_capturing_llm_chat()` helpers to standardize LLM instance mocking.
- **Files modified:** `backend/tests/core/test_pipeline_agents.py`
- **Commit:** 50215ab

**2. [Rule 1 - Bug] Wrong signature in `capture_commander` mock**
- **Found during:** Task 2, first test run (1 failure)
- **Issue:** `capture_commander` defined as `(raw_input, platform, content_type, persona_card, **kwargs)` — missing the explicit `anti_rep_prompt`, `media_system_suffix`, `image_urls` positional-or-keyword args that `asyncio.wait_for` dispatches with positional expansion.
- **Fix:** Added all explicit params to match `run_commander` signature.
- **Files modified:** `backend/tests/core/test_orchestrator_nodes.py`
- **Commit:** 452ced6

## Known Stubs

None — all tests are fully wired, no placeholder assertions or mock data that leaks to UI.

## Self-Check: PASSED

Files exist:
- backend/tests/core/__init__.py — FOUND
- backend/tests/core/conftest.py — FOUND
- backend/tests/core/test_pipeline_agents.py — FOUND
- backend/tests/core/test_orchestrator_nodes.py — FOUND

Commits exist:
- 50215ab — FOUND
- 452ced6 — FOUND

Test count: 50 new tests in tests/core/ (25 + 25), all passing.
Combined tests/core/ suite: 108 passed, 0 failed.
