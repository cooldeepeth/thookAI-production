---
phase: 27-onboarding-reimagination
plan: 05
subsystem: backend
tags: [python, fastapi, onboarding, persona, testing, pytest]

# Dependency graph
requires:
  - phase: 27-01
    provides: "GeneratePersonaRequest with 5 fields, persona_doc with 14 keys, _generate_smart_persona with personality_traits and voice_style"
  - phase: 27-04
    provides: "5-step wizard wired end-to-end, wizard marked complete"
provides:
  - "pytest.ini with pythonpath=. so backend tests run without PYTHONPATH env var"
  - "54 passing onboarding tests covering all new fields, LLM passthrough, edge cases"
  - "ONBD-05/ONBD-06/ONBD-08 all traceable to green tests"
affects: [onboarding-e2e, ci-backend, phase-gate]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "pytest pythonpath=. in pytest.ini — avoids PYTHONPATH env var requirement for CI and local runs"
    - "FakeExtendedRequest pattern: test-local Pydantic model mirrors GeneratePersonaRequest for async call injection"

key-files:
  created: []
  modified:
    - backend/pytest.ini
    - backend/tests/test_onboarding_core.py

key-decisions:
  - "pytest.ini gets pythonpath=. (Rule 3 fix) — all tests were failing with ModuleNotFoundError on routes import; adding pythonpath eliminates PYTHONPATH dependency in every test invocation"
  - "6 new edge-case tests added to TestNewPersonaFields and TestGeneratePersonaExtendedRequest — type assertions and LLM-value passthrough verification close ONBD-05/06 traceability gaps"

patterns-established:
  - "Type-assertion pattern: isinstance(doc[field], expected_type) with explicit message gives clearer failures than bare assert"
  - "LLM-passthrough pattern: set MOCK_PERSONA_CARD_EXTENDED[field] and assert doc[field] == expected to verify no field is silently dropped"

requirements-completed: [ONBD-01, ONBD-05, ONBD-06, ONBD-07, ONBD-08]

# Metrics
duration: 20min
completed: 2026-04-12
---

# Phase 27 Plan 05: Backend Audit and Test Hardening Summary

**pytest.ini pythonpath fix + 54 green tests covering all new persona fields, model name correctness, and edge cases for ONBD-05/06/08**

## Performance

- **Duration:** 20 min
- **Started:** 2026-04-11T18:51:52Z
- **Completed:** 2026-04-11T19:11:52Z
- **Tasks:** 2 of 2 complete
- **Files modified:** 2

## Accomplishments

- Audited onboarding.py: model name CLEAN (no claude-4-sonnet-20250514), 2 correct occurrences of claude-sonnet-4-20250514
- Confirmed all 4 new persona fields (voice_style, visual_preferences, writing_samples, personality_traits) present in persona_doc, PERSONA_PROMPT, and _generate_smart_persona
- Fixed blocking test failure: added `pythonpath = .` to pytest.ini so `from routes.onboarding import ...` works without PYTHONPATH env var
- Added 6 missing edge-case tests:
  - TestNewPersonaFields: `test_persona_doc_personality_traits_is_list`, `test_persona_doc_voice_style_is_string`, `test_persona_doc_has_voice_style_from_llm_output`, `test_persona_doc_personality_traits_from_llm_output`
  - TestGeneratePersonaExtendedRequest: `test_generate_persona_writing_samples_stored_in_doc`, `test_generate_persona_visual_preference_stored_in_doc`
- Full suite: 54 tests collected and passing (up from 48)

## Task Commits

Each task was committed atomically:

1. **Task 1: Audit onboarding.py and fix pytest pythonpath** - `165c888` (fix)
2. **Task 2: Add edge case tests for new fields** - `8f867c2` (feat)

## Files Created/Modified

- `backend/pytest.ini` - Added `pythonpath = .` so `routes` module is importable without setting PYTHONPATH externally
- `backend/tests/test_onboarding_core.py` - Added 6 edge-case tests covering type assertions, LLM passthrough, and storage verification for all new persona fields

## Decisions Made

- **pytest.ini pythonpath=.** — All 48 tests were failing with `ModuleNotFoundError: No module named 'routes'`. Root cause: pytest.ini had no `pythonpath` directive and PYTHONPATH was not set in the shell. Fix is minimal and correct — `pythonpath = .` in pytest.ini is the canonical pytest ≥7.0 solution and applies to all test runs including CI.
- **6 new edge-case tests added** — The plan specified these as "add if missing." None were present. Added all 6 to close ONBD-05/06 traceability gaps and verify LLM field passthrough behavior end-to-end.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] pytest.ini missing pythonpath directive**
- **Found during:** Task 1, Step 2 (run full test suite)
- **Issue:** All 48 tests in test_onboarding_core.py failed with `ModuleNotFoundError: No module named 'routes'` because pytest could not find the backend source directory without an explicit pythonpath setting
- **Fix:** Added `pythonpath = .` to `[pytest]` section in `backend/pytest.ini`
- **Files modified:** `backend/pytest.ini`
- **Commit:** `165c888`

## Pre-existing Failures (Out of Scope)

The full backend suite (excluding security/) showed 19 pre-existing failures unrelated to onboarding:
- `test_auth_core.py`, `test_e2e_*.py`, `test_e2e_ship.py`: require `JWT_SECRET_KEY` env var — integration tests need env configuration
- `test_celery_cutover.py`: Procfile assertions conflict with n8n migration state
- `test_dead_links.py`: frontend API reference audit
- `test_email_password_reset.py`: JWT dependency

These are pre-existing and not caused by this plan's changes. Documented here, not fixed.

## Known Stubs

None — all new field values flow from LLM or fallback; no hardcoded placeholder values in production code paths.

---
*Phase: 27-onboarding-reimagination*
*Completed: 2026-04-12*

## Self-Check: PASSED
