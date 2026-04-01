---
phase: 12-strategist-agent
verified: 2026-04-01T17:45:00Z
status: gaps_found
score: 4/5 must-haves verified
gaps:
  - truth: "Test suite regression: WORKFLOW_NOTIFICATION_MAP count test breaks after Phase 12 added 5th entry"
    status: failed
    reason: "Phase 12 Plan 03 (commit f01015b) extended WORKFLOW_NOTIFICATION_MAP from 4 to 5 entries. The pre-existing test test_n8n_workflow_status.py::TestWorkflowNotificationMap::test_map_has_exactly_four_entries asserts == 4. This now fails with AssertionError: assert 5 == 4. Plan 04 documented this as a pre-existing failure but it was caused by Phase 12 Plan 03's modification — it is a Phase 12 regression."
    artifacts:
      - path: "backend/tests/test_n8n_workflow_status.py"
        issue: "Line 351 asserts len(WORKFLOW_NOTIFICATION_MAP) == 4 but Phase 12 added a 5th entry — test must be updated to == 5 or refactored to not hard-code count"
    missing:
      - "Update test_map_has_exactly_four_entries assertion from == 4 to == 5 (or rename it to test_map_has_exactly_five_entries for accuracy)"
human_verification:
  - test: "n8n cron workflow exists and is configured to call POST /api/n8n/execute/run-nightly-strategist at 03:00 UTC with correct HMAC header"
    expected: "n8n execution log shows the endpoint receiving a request and returning status='completed' with total_cards > 0 for eligible users"
    why_human: "n8n workflow JSON template can only be verified by actually running the n8n instance and checking workflow configuration — N8N_WORKFLOW_NIGHTLY_STRATEGIST env var is currently empty"
  - test: "Strategy Dashboard (Phase 14) displays recommendation cards from db.strategy_recommendations"
    expected: "After nightly run, user logs in and sees up to 3 recommendation cards with why_now rationale visible"
    why_human: "Phase 14 (Strategy Dashboard) is not yet built — frontend card display cannot be verified at this phase boundary"
---

# Phase 12: Strategist Agent Verification Report

**Phase Goal:** A nightly AI agent synthesizes each user's content history, performance signals, and persona into a ranked list of recommendation cards that appear waiting for them the next morning
**Verified:** 2026-04-01T17:45:00Z
**Status:** gaps_found
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| #  | Truth                                                                                       | Status     | Evidence                                                                                          |
|----|---------------------------------------------------------------------------------------------|------------|---------------------------------------------------------------------------------------------------|
| 1  | StrategistConfig exists in config.py with max_cards=3, suppression_days=14                 | VERIFIED   | `python3 -c "from config import settings; print(settings.strategist.max_cards_per_day)"` → 3     |
| 2  | Strategist agent writes cards to db.strategy_recommendations with status pending_approval  | VERIFIED   | strategist.py line 424 sets `"status": "pending_approval"` on every insert                       |
| 3  | n8n execute endpoint triggers nightly run via HMAC-authenticated bridge                    | VERIFIED   | POST /api/n8n/execute/run-nightly-strategist registered in n8n_bridge.py, wired to server.py     |
| 4  | All 7 STRAT requirements have passing tests covering core behavior                         | VERIFIED   | `pytest tests/test_strategist.py`: 29 passed, 0 failed                                           |
| 5  | Phase 12 introduces no regressions to passing test suite                                   | FAILED     | `pytest tests/test_n8n_workflow_status.py::TestWorkflowNotificationMap::test_map_has_exactly_four_entries` fails — Phase 12 Plan 03 added 5th WORKFLOW_NOTIFICATION_MAP entry without updating the Phase 09 count test |

**Score:** 4/5 truths verified

### Required Artifacts

| Artifact                                      | Expected                                          | Status     | Details                                                                 |
|-----------------------------------------------|---------------------------------------------------|------------|-------------------------------------------------------------------------|
| `backend/config.py`                           | StrategistConfig + N8nConfig workflow field        | VERIFIED   | StrategistConfig at line 268 with all 6 fields; workflow_nightly_strategist at line 231 |
| `backend/db_indexes.py`                       | Indexes for strategy_recommendations + strategist_state | VERIFIED | 6 indexes on strategy_recommendations (incl. compound user_id+topic+status); 3 indexes on strategist_state |
| `backend/.env.example`                        | N8N_WORKFLOW_NIGHTLY_STRATEGIST documented        | VERIFIED   | Line 138: `N8N_WORKFLOW_NIGHTLY_STRATEGIST=` with comment              |
| `backend/agents/strategist.py`                | Core nightly synthesis engine (min 200 lines)     | VERIFIED   | 605 lines; exports run_strategist_for_all_users, run_strategist_for_user, handle_dismissal, handle_approval, _build_generate_payload |
| `backend/routes/n8n_bridge.py`               | Execute endpoint + workflow map + notification map | VERIFIED   | 3 additions confirmed: /execute/run-nightly-strategist, nightly-strategist in both maps |
| `backend/tests/test_strategist.py`           | 29 tests covering STRAT-01 through STRAT-07       | VERIFIED   | 874 lines, 29 tests, 7 test classes, all passing                       |
| `backend/tests/test_n8n_workflow_status.py` | Phase 09 tests not regressed by Phase 12          | FAILED     | test_map_has_exactly_four_entries asserts == 4; Phase 12 made count 5  |

### Key Link Verification

| From                             | To                              | Via                                          | Status      | Details                                                                   |
|----------------------------------|---------------------------------|----------------------------------------------|-------------|---------------------------------------------------------------------------|
| `backend/config.py`              | `backend/agents/strategist.py`  | `settings.strategist.max_cards_per_day`       | VERIFIED    | Lines 38-41: MODULE_CONST = settings.strategist.* for all 4 constants     |
| `backend/db_indexes.py`          | MongoDB at startup              | `ensure_indexes()` called in lifespan         | VERIFIED    | strategy_recommendations and strategist_state in INDEXES dict              |
| `backend/agents/strategist.py`   | `backend/services/lightrag_service.py` | lazy import inside `_query_content_gaps` | VERIFIED    | Line 208: `from services.lightrag_service import query_knowledge_graph  # lazy import` — NOT at module level |
| `backend/agents/strategist.py`   | `backend/services/llm_client.py` | LlmChat with claude-sonnet-4-20250514        | VERIFIED    | Line 321: `.with_model("anthropic", "claude-sonnet-4-20250514")`          |
| `backend/agents/strategist.py`   | `db.strategy_recommendations`   | Motor insert_one for card writes              | VERIFIED    | Line 438: `await db.strategy_recommendations.insert_one(card_doc)`        |
| `backend/agents/strategist.py`   | `db.strategist_state`           | find_one_and_update for atomic cap guard      | VERIFIED    | Lines 148-168: two-phase atomic upsert pattern                            |
| `backend/routes/n8n_bridge.py`  | `backend/agents/strategist.py`  | lazy import in execute endpoint               | VERIFIED    | Line ~830: `from agents.strategist import run_strategist_for_all_users`   |
| `backend/routes/n8n_bridge.py`  | `backend/config.py`             | settings.n8n.workflow_nightly_strategist      | VERIFIED    | Line 83: `"nightly-strategist": settings.n8n.workflow_nightly_strategist` |
| `backend/server.py`              | `backend/routes/n8n_bridge.py`  | api_router.include_router                     | VERIFIED    | Line 311: `api_router.include_router(n8n_bridge_router)`                  |

### Data-Flow Trace (Level 4)

| Artifact                                 | Data Variable              | Source                                      | Produces Real Data | Status     |
|------------------------------------------|----------------------------|---------------------------------------------|--------------------|------------|
| `strategist.py:run_strategist_for_user`  | `recommendations`          | LLM synthesis via `_synthesize_recommendations` | Yes (real LLM call, graceful empty on unavailable) | FLOWING |
| `strategist.py:_gather_user_context`     | `persona`, `recent_content` | `db.persona_engines`, `db.content_jobs`    | Yes (Motor async queries) | FLOWING |
| `strategist.py:_query_content_gaps`      | `knowledge_gaps`           | `lightrag_service.query_knowledge_graph`    | Yes (degrades to "" on failure) | FLOWING |
| `strategist.py:handle_dismissal`         | `state.consecutive_dismissals` | `db.strategist_state.find_one_and_update` | Yes (atomic increment) | FLOWING |

### Behavioral Spot-Checks

| Behavior                                      | Command                                                                          | Result                       | Status   |
|-----------------------------------------------|----------------------------------------------------------------------------------|------------------------------|----------|
| strategist.py exports all required functions  | `python3 -c "from agents.strategist import run_strategist_for_all_users, run_strategist_for_user, handle_dismissal, handle_approval; print('OK')"` | OK | PASS |
| StrategistConfig defaults are correct         | `python3 -c "from config import settings; assert settings.strategist.max_cards_per_day == 3; print('OK')"` | OK | PASS |
| n8n execute endpoint is importable            | `python3 -c "import routes.n8n_bridge; print('OK')"` | OK | PASS |
| All 29 strategist tests pass                  | `pytest tests/test_strategist.py -x -v --tb=short`   | 29 passed, 0 failed          | PASS |
| Pre-existing test regression detected         | `pytest tests/test_n8n_workflow_status.py -x --tb=short` | 1 failed (count == 4 but now 5) | FAIL |
| LLM model is correct (claude-sonnet-4-20250514) | `grep "claude-sonnet-4-20250514" backend/agents/strategist.py` | Line 321 | PASS |
| No module-level lightrag import               | `grep -n "^from services.lightrag" backend/agents/strategist.py` | No output | PASS |
| No pipeline/create_content import             | `grep "import pipeline\|from agents.pipeline\|create_content" backend/agents/strategist.py` | No output | PASS |

### Requirements Coverage

| Requirement | Source Plan(s) | Description                                                                                   | Status     | Evidence                                                                    |
|-------------|----------------|-----------------------------------------------------------------------------------------------|------------|-----------------------------------------------------------------------------|
| STRAT-01    | 12-01, 12-02, 12-03 | Strategist Agent (backend/agents/strategist.py) — nightly n8n-triggered                 | SATISFIED  | File exists at 605 lines; n8n endpoint registered; run_strategist_for_all_users exported |
| STRAT-02    | 12-02          | Cards written to db.strategy_recommendations with status "pending_approval" — never triggers generation | SATISFIED | Line 424 sets status="pending_approval"; no pipeline import confirmed via grep |
| STRAT-03    | 12-02          | Every card includes "Why now: [signal]" rationale                                             | SATISFIED  | Lines 417-419 enforce why_now fallback if LLM omits; STRAT-03 comment on line 428 |
| STRAT-04    | 12-01, 12-02   | Max 3 new cards per user per day, hard cap enforced atomically                                | SATISFIED  | MAX_CARDS_PER_DAY from settings; _atomic_claim_card_slot uses find_one_and_update; test TestCadenceControls passes |
| STRAT-05    | 12-01, 12-02   | Dismissal tracking — 14-day topic suppression on dismiss                                      | SATISFIED  | _is_topic_suppressed queries compound index (user_id, topic, status); SUPPRESSION_DAYS = settings.strategist.suppression_days; test TestDismissalTracking passes |
| STRAT-06    | 12-02          | 5 consecutive dismissals halves generation rate and surfaces calibration prompt               | SATISFIED  | handle_dismissal increments consecutive_dismissals; threshold check sets halved_rate=True + needs_calibration_prompt=True; test TestConsecutiveDismissalThreshold passes |
| STRAT-07    | 12-02          | Recommendation cards include pre-filled generate_payload for one-click content generation    | SATISFIED  | _build_generate_payload returns {platform, content_type, raw_input}; handle_approval returns generate_payload; test TestGeneratePayloadSchema passes |

All 7 STRAT requirements are satisfied by the implementation. No orphaned requirements found — all 7 IDs declared across plans 01-04 are accounted for in REQUIREMENTS.md.

### Anti-Patterns Found

| File                                          | Line | Pattern                                       | Severity | Impact                                                              |
|-----------------------------------------------|------|-----------------------------------------------|----------|---------------------------------------------------------------------|
| `backend/tests/test_n8n_workflow_status.py`  | 351  | `assert len(WORKFLOW_NOTIFICATION_MAP) == 4`  | BLOCKER  | Phase 12 added 5th entry — this test now fails, breaking `pytest -x` for the entire suite. Needs to be updated to == 5. |

Note: `return []` and `return {}` patterns in strategist.py (lines 133, 312, 333, 352, 355) are all in error-handling branches (try/except, anthropic_available() guard) — these are intentional graceful degradation paths, not stubs.

### Human Verification Required

#### 1. n8n Cron Workflow Configuration

**Test:** In the n8n admin UI, verify a workflow exists with a cron trigger at 03:00 UTC that POSTs to `POST /api/n8n/execute/run-nightly-strategist` with the correct `X-N8N-Signature` HMAC header
**Expected:** Workflow executes successfully; n8n execution log shows `status: "completed"` and `total_cards > 0` for eligible users
**Why human:** `N8N_WORKFLOW_NIGHTLY_STRATEGIST` env var is currently empty — no workflow ID is configured. The workflow must be created in the n8n instance and the env var populated before the nightly run works end-to-end.

#### 2. Strategy Dashboard Card Display (Phase 14 dependency)

**Test:** Log in as a user with `onboarding_completed: true` and at least 3 approved content jobs. Manually trigger the strategist via `POST /api/n8n/execute/run-nightly-strategist`. Navigate to the Strategy Dashboard (Phase 14).
**Expected:** Up to 3 recommendation cards appear, each showing the topic, hook options, and "Why now:" rationale. Approving a card fires content generation without additional form fields.
**Why human:** Phase 14 (Strategy Dashboard) is not yet built. The backend API is complete but no frontend component renders `db.strategy_recommendations` cards.

### Gaps Summary

**One gap blocks a clean test suite pass.** Phase 12 Plan 03 correctly extended `WORKFLOW_NOTIFICATION_MAP` from 4 to 5 entries (adding `nightly-strategist`), but did not update the Phase 09 test `test_map_has_exactly_four_entries` in `backend/tests/test_n8n_workflow_status.py` (line 351) which hard-codes `== 4`. This causes `pytest -x` to fail on first run.

The fix is minimal: update line 351 from `assert len(WORKFLOW_NOTIFICATION_MAP) == 4` to `assert len(WORKFLOW_NOTIFICATION_MAP) == 5`, or rename the test to `test_map_has_exactly_five_entries` for accuracy. The Plan 04 summary acknowledged this as "pre-existing" but git history confirms the failure was introduced by Phase 12 commit `f01015b`.

**Two items require human verification** (n8n workflow configuration, Phase 14 frontend) but these are expected phase boundary items — the backend is fully ready for both.

---

_Verified: 2026-04-01T17:45:00Z_
_Verifier: Claude (gsd-verifier)_
