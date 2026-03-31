---
phase: 03-auth-onboarding-email
plan: 03
subsystem: onboarding
tags: [auth, onboarding, persona, llm, tests, bug-fix]
requirements: [AUTH-05, AUTH-06]

dependency_graph:
  requires:
    - backend/routes/onboarding.py (pre-existing)
    - backend/services/llm_client.py (pre-existing)
    - backend/services/llm_keys.py (pre-existing)
  provides:
    - 35 unit tests covering onboarding correctness
    - Verified correct Claude model name (AUTH-05)
    - Verified persona Engine document structure (AUTH-06)
    - Source transparency field in generate-persona response
  affects:
    - backend/routes/onboarding.py (minor: source field added to response)

tech_stack:
  added: []
  patterns:
    - pytest unit tests with unittest.mock.patch for LlmChat isolation
    - AsyncMock for async DB operations
    - Source inspection via inspect.getsource() for model name verification

key_files:
  created:
    - backend/tests/test_onboarding_core.py
  modified:
    - backend/routes/onboarding.py

decisions:
  - Archetype priority order (Storyteller > Provocateur > Builder > Educator) validated by tests — test inputs must use neutral styles when testing Builder to avoid Provocateur trigger
  - Added persona_source tracking variable; returned as source field in response so frontend can conditionally show "demo mode" notice when smart_fallback used
  - Source inspection test (test_correct_model_name_in_generate_persona_source) provides regression protection — any future wrong-model-name edit will break CI

metrics:
  duration_minutes: 8
  completed_date: "2026-03-31"
  tasks_completed: 2
  tasks_total: 2
  files_created: 1
  files_modified: 1
---

# Phase 03 Plan 03: Onboarding Model Fix & Persona Tests Summary

35 unit tests verifying onboarding uses `claude-sonnet-4-20250514` (not wrong name), persona Engine has personalized fields, smart fallback produces archetype-specific personas, and UOM fields are populated.

## What Was Built

### Task 1: Unit tests for onboarding and persona generation
Created `backend/tests/test_onboarding_core.py` with 35 tests organized across 4 classes:

**TestOnboardingQuestions** — 5 tests verifying the questions structure:
- 7 questions total
- Required fields (id, type, question, hint) on each question
- Both "text" and "multi_choice" types present
- Sequential IDs 0-6

**TestModelCorrectness (AUTH-05)** — 3 tests:
- Source inspection confirms `claude-4-sonnet-20250514` is absent from `onboarding.py`
- Source inspection confirms `claude-sonnet-4-20250514` appears at least twice (both endpoints)
- Mock-based test: `.with_model("anthropic", "claude-sonnet-4-20250514")` called during generation

**TestPersonaGeneration (AUTH-06)** — 13 tests:
- persona_engines document has voice_fingerprint with sentence_length_distribution and vocabulary_complexity
- content_identity has topic_clusters, tone, regional_english
- uom has burnout_risk, risk_tolerance, strategy_maturity
- learning_signals initialized with empty lists
- users.update_one sets onboarding_completed to True
- Auth dependency verified via source inspection
- Markdown-wrapped JSON response parsed correctly
- Fallback called when LLM raises exception

**TestSmartFallback** — 14 tests:
- Builder archetype: "founder"/"startup"/"build"/"create"/"launch" in about (with neutral style)
- Storyteller archetype: "story"/"journey"/"experience"/"life" in about
- Provocateur archetype: "bold"/"provocative"/"challenge"/"disrupt" in style
- Default archetype: Educator
- burnout_risk: "Under 1 hour" → high, "1–3 hours" → medium, "5+ hours" → low
- Platform parsing: "All three" → 3-element list, "+" split, single platform
- Empty answers: produces valid persona without exceptions
- All 15 required persona fields present in result

### Task 2: Fix onboarding issues found by tests

**Verified (no change needed):**
- Both endpoints use `claude-sonnet-4-20250514` — grep returns 2 matches, zero wrong-name matches

**Added:**
- `persona_source` tracking variable (`"llm"` or `"smart_fallback"`)
- `source` field in generate-persona response for frontend transparency

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Test inputs needed neutral style for Builder archetype test**
- **Found during:** Task 1 — first test run
- **Issue:** `test_founder_in_about_gives_builder_archetype` used default style "Bold, Clear, Strategic" which triggered Provocateur check before Builder check (correct behavior, wrong test expectation)
- **Fix:** Updated test helper to use neutral style "Clear, Strategic, Analytical" when testing Builder archetype specifically
- **Files modified:** backend/tests/test_onboarding_core.py
- **Commit:** e048aea (included in test commit)

## Known Stubs

None — all fields are wired to actual data from the LLM response or smart fallback. The `source` field is not a stub: it accurately reflects whether the LLM or fallback was used.

## AUTH-05 / AUTH-06 Status

- **AUTH-05:** VERIFIED — `claude-sonnet-4-20250514` used in both `analyze-posts` and `generate-persona` endpoints. Source inspection test provides regression protection.
- **AUTH-06:** VERIFIED — Persona Engine document has all required fields: `voice_fingerprint`, `content_identity`, `uom`, `learning_signals`. Smart fallback produces archetype-specific, non-generic personas.

## Self-Check: PASSED

- `backend/tests/test_onboarding_core.py` exists
- Commits e048aea (test) and 4f35d60 (feat) exist in git log
- 35 tests pass, 0 failures, 0 regressions
