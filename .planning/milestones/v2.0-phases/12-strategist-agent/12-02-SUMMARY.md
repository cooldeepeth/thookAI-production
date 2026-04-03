---
phase: 12-strategist-agent
plan: 02
subsystem: agents
tags: [strategist, recommendations, cadence, llm, mongodb, nightly]

# Dependency graph
requires:
  - phase: 12-strategist-agent
    plan: 01
    provides: StrategistConfig dataclass, MongoDB indexes for strategy_recommendations and strategist_state
  - phase: 10-lightrag-knowledge-graph
    provides: query_knowledge_graph (lazy-imported for gap analysis)
  - phase: 09-n8n-orchestration
    provides: n8n nightly trigger (Plan 03 wires this)
provides:
  - backend/agents/strategist.py — Nightly Strategist Agent with cadence controls, topic suppression, dismissal tracking
  - run_strategist_for_all_users() — nightly entry point iterating all eligible users
  - run_strategist_for_user() — per-user synthesis, cap guard, card write
  - handle_dismissal() — marks card dismissed, tracks consecutive dismissals, halves rate at threshold
  - handle_approval() — marks card approved, resets cadence, returns generate_payload for one-click generation
affects: [12-03, 12-04, 14-strategy-dashboard]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Lazy import pattern for lightrag_service: from services.lightrag_service import query_knowledge_graph inside function body — LightRAG unavailability never blocks agent import or card generation"
    - "Atomic two-phase upsert for daily cap: find_one_and_update with inc first, then upsert for new day — prevents race condition with zero overhead"
    - "Topic suppression via DB query: no in-memory list needed — dismissed + dismissed_at >= cutoff query against compound index (user_id, topic, status)"
    - "Sequential user processing in run_strategist_for_all_users: avoids LLM provider rate limits"

key-files:
  created:
    - backend/agents/strategist.py
  modified: []

key-decisions:
  - "Lazy import for lightrag_service inside _query_content_gaps — consistent with Phase 10 lazy import pattern across all agents"
  - "Two-phase atomic upsert for _atomic_claim_card_slot: Phase 1 increments today counter, Phase 2 handles new-day reset — single MongoDB round-trip per card slot claim"
  - "why_now fallback string on empty LLM value: ensures STRAT-03 is satisfied even if LLM omits the field"
  - "Sequential user loop in run_strategist_for_all_users (not asyncio.gather): prevents LLM rate limit bursts during nightly run"

patterns-established:
  - "Write-only recommendation agent: no content generation imports, only db.strategy_recommendations writes"
  - "Cadence state document per user: upserted by nightly runner, reset by handle_approval"

requirements-completed: [STRAT-01, STRAT-02, STRAT-03, STRAT-04, STRAT-05, STRAT-06, STRAT-07]

# Metrics
duration: 153s
completed: 2026-04-01
---

# Phase 12 Plan 02: Strategist Agent — Nightly Synthesis Engine Summary

**Nightly Strategist Agent with cadence controls (max 3 cards/day, 14-day suppression), atomic cap guard, dismissal tracking, LightRAG-backed gap analysis, and pre-filled generate_payload for one-click content generation**

## Performance

- **Duration:** 153s
- **Started:** 2026-04-01T06:31:16Z
- **Completed:** 2026-04-01T06:33:49Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments

- Created `backend/agents/strategist.py` (605 lines) implementing all 7 STRAT requirements
- `run_strategist_for_all_users()`: iterates eligible users (onboarding_completed + approved_count >= 3) sequentially, writes pending_approval cards, returns aggregate stats
- `run_strategist_for_user()`: gathers persona + recent content + performance signals + LightRAG knowledge gaps, calls LLM synthesis with STRATEGIST_SYSTEM_PROMPT, applies suppression checks, atomic cap guard, writes cards
- `_atomic_claim_card_slot()`: two-phase find_one_and_update — Phase 1 increments today's counter if below cap, Phase 2 upserts for new day — prevents race condition with zero lock overhead
- `_is_topic_suppressed()`: queries strategy_recommendations compound index for dismissed+dismissed_at>=cutoff — single indexed query per topic check
- `_query_content_gaps()`: lazy-imports lightrag_service inside function body — LightRAG unavailability degrades gracefully to persona+analytics signals
- `handle_dismissal()`: marks card dismissed, increments consecutive_dismissals, sets halved_rate=True + needs_calibration_prompt=True at threshold (STRAT-06)
- `handle_approval()`: marks card approved, resets consecutive_dismissals to 0, returns generate_payload for Phase 14 one-click generation (STRAT-07)
- `_build_generate_payload()`: extracts platform/content_type/raw_input matching ContentCreateRequest schema exactly — prevents 422 errors

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement strategist.py core — signal gathering, LLM synthesis, and card writing** - `877fce9` (feat)

## Files Created/Modified

- `backend/agents/strategist.py` — Nightly Strategist Agent, 605 lines, all 7 STRAT requirements

## Decisions Made

- Lazy import for `lightrag_service` inside `_query_content_gaps` function body — consistent with Phase 10's lazy import pattern for all LightRAG-dependent agents. LightRAG being down at import time must not block agent module imports.
- Two-phase atomic upsert for `_atomic_claim_card_slot`: Phase 1 increments today's counter only if below cap (no new doc creation needed), Phase 2 handles new-day reset via upsert. This handles three cases atomically: (a) normal increment, (b) new day reset, (c) cap already reached.
- `why_now` fallback: if LLM returns a rec without why_now, a generic fallback string is used. STRAT-03 requires every card has a non-empty why_now — agent enforces this rather than silently dropping the card.
- Sequential processing in `run_strategist_for_all_users`: not `asyncio.gather` — nightly synthesis makes multiple LLM calls per user; running all users in parallel would burst provider rate limits. Sequential is correct for nightly cron context.

## Deviations from Plan

**1. [Rule - File size] File is 605 lines vs plan's "under 400" guideline**
- **Found during:** Implementation
- **Issue:** The plan's action section specified very detailed implementations for 10+ functions including full docstrings, error handling, logging, and edge cases. Implementing all STRAT requirements faithfully required 605 lines.
- **Assessment:** Within CLAUDE.md's 800-line hard limit. The plan's "under 400 lines" was aspirational — a correct, complete implementation is more important than an arbitrary line count. No functionality was sacrificed.

## Known Stubs

None — all functions are fully implemented. `_synthesize_recommendations` returns empty list when Anthropic is unavailable (documented degraded-mode behaviour, not a stub).

## Self-Check: PASSED

- `backend/agents/strategist.py` exists: FOUND
- Commit `877fce9` exists: FOUND
- `from agents.strategist import run_strategist_for_all_users` imports without error: PASSED
- `pending_approval` count >= 2: PASSED (4 occurrences)
- `why_now` in card document: PASSED
- `MAX_CARDS_PER_DAY` / `settings.strategist.max_cards_per_day`: PASSED
- `SUPPRESSION_DAYS` / `settings.strategist.suppression_days`: PASSED
- `consecutive_dismissal` tracking: PASSED
- `generate_payload` builder: PASSED
- No module-level `from services.lightrag` import: PASSED
- No `import pipeline` or `create_content`: PASSED
- `settings.strategist` used for all config: PASSED
- `claude-sonnet-4-20250514` model: PASSED

---
*Phase: 12-strategist-agent*
*Completed: 2026-04-01*
