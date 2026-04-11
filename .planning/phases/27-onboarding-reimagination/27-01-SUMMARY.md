---
phase: 27-onboarding-reimagination
plan: "01"
subsystem: backend-onboarding
tags: [tdd, persona, schema-extension, onboarding, python]
dependency_graph:
  requires: []
  provides: [extended-persona-schema, new-persona-fields, GeneratePersonaRequest-extended]
  affects: [backend/routes/onboarding.py, backend/tests/test_onboarding_core.py]
tech_stack:
  added: []
  patterns: [TDD RED-GREEN, Pydantic optional fields, fallback extension]
key_files:
  created: []
  modified:
    - backend/routes/onboarding.py
    - backend/tests/test_onboarding_core.py
decisions:
  - "Updated all FakeRequest fixtures in existing tests to include new optional fields (Rule 1 auto-fix) — generate_persona accesses data.visual_preference and data.writing_samples so all callers must provide Pydantic-compatible objects"
  - "voice_style derived from persona_card.get('voice_style', '') — LLM path provides rich value; smart fallback synthesizes from style_words"
  - "personality_traits and voice_style added to both PERSONA_PROMPT JSON schema and _generate_smart_persona fallback to satisfy ONBD-05 in both execution paths"
metrics:
  duration: "~3 minutes"
  completed_date: "2026-04-11"
  tasks_completed: 2
  files_modified: 2
requirements_satisfied: [ONBD-05, ONBD-06, ONBD-08]
---

# Phase 27 Plan 01: Backend Persona Schema Extension Summary

**One-liner:** Extended `GeneratePersonaRequest` and `persona_doc` with four new persona fields (`voice_style`, `visual_preferences`, `writing_samples`, `personality_traits`) via TDD RED-GREEN cycle; all 48 tests green.

## What Was Built

Extended the backend onboarding route to capture and store four new persona fields introduced by ONBD-05 and ONBD-06:

1. **`GeneratePersonaRequest`** — added three optional input fields: `voice_sample_url`, `visual_preference`, `writing_samples`
2. **`PERSONA_PROMPT` JSON schema** — added `personality_traits` (array) and `voice_style` (string) to the LLM return schema so Claude generates them when available
3. **`generate_persona()` persona_doc** — stores all four new fields on every persona write: `voice_style`, `visual_preferences`, `writing_samples`, `personality_traits`
4. **`_generate_smart_persona()` fallback** — returns sensible defaults: `personality_traits: ["Analytical", "Strategic", "Authentic"]` and `voice_style: f"Professional {style_words} voice with structured insights"`

Tests written first (RED), implementation then made them pass (GREEN). No regressions — all 35 pre-existing tests continue to pass alongside the 13 new tests.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Write failing tests for new persona fields (RED) | 8202c70 | backend/tests/test_onboarding_core.py |
| 2 | Implement backend persona schema extension (GREEN) | 4325c7e | backend/routes/onboarding.py, backend/tests/test_onboarding_core.py |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated existing FakeRequest fixtures to include new optional fields**
- **Found during:** Task 2 GREEN verification
- **Issue:** `generate_persona()` now accesses `data.visual_preference` and `data.writing_samples` on the request object. Four existing test methods (`test_with_model_called_with_correct_args`, `_run_generate_persona` helper, `test_onboarding_completed_flag_set_to_true`, `test_fallback_used_when_llm_raises`) all used a local `FakeRequest(BaseModel)` with only `answers` and `posts_analysis` fields. These raised `AttributeError` when `generate_persona` accessed the new fields.
- **Fix:** Added `voice_sample_url`, `visual_preference`, and `writing_samples` optional fields to all four `FakeRequest` class definitions inside the existing test methods.
- **Files modified:** `backend/tests/test_onboarding_core.py`
- **Commit:** 4325c7e (included in GREEN implementation commit)

## Verification Results

```
48 passed, 3 warnings in 0.29s
```

Field presence in onboarding.py: 10 matches across `GeneratePersonaRequest`, `PERSONA_PROMPT`, `persona_doc`, and `_generate_smart_persona`.

Model name check: `grep -c "claude-sonnet-4-20250514" backend/routes/onboarding.py` → 2 (both `analyze_posts` and `generate_persona` functions use correct model name).

## Known Stubs

None. All four new fields are fully wired:
- `voice_style` — derived from LLM output or synthesized in fallback (non-empty string guaranteed)
- `visual_preferences` — defaults to `"minimal"` when not provided (never null)
- `writing_samples` — defaults to `[]` when not provided (never null)
- `personality_traits` — derived from LLM output or `["Analytical", "Strategic", "Authentic"]` in fallback (non-empty list guaranteed)

## Self-Check: PASSED

- [x] `backend/routes/onboarding.py` modified and committed (4325c7e)
- [x] `backend/tests/test_onboarding_core.py` modified and committed (8202c70, 4325c7e)
- [x] 48 tests pass — `pytest tests/test_onboarding_core.py -x -q` exits 0
- [x] `GeneratePersonaRequest` has 5 fields: answers, posts_analysis, voice_sample_url, visual_preference, writing_samples
- [x] `persona_doc` includes voice_style, visual_preferences, writing_samples, personality_traits
- [x] `_generate_smart_persona` returns personality_traits (list) and voice_style (str)
- [x] PERSONA_PROMPT JSON schema includes personality_traits and voice_style
- [x] No wrong model name "claude-4-sonnet-20250514" in onboarding.py
