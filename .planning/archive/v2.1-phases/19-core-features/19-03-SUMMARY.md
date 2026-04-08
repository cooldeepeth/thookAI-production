---
phase: 19-core-features
plan: "03"
subsystem: testing
tags: [lightrag, security, injection, tdd, python, httpx, per-user-isolation]

requires:
  - phase: 10-lightrag-knowledge-graph
    provides: lightrag_service.py with query_knowledge_graph and insert_content functions

provides:
  - Lambda injection fix in lightrag_service.py (user_id validated to [a-zA-Z0-9_-] before interpolation)
  - Failing injection tests committed before fix (TDD RED phase)
  - 5 injection tests in test_lightrag_lambda_injection.py verifying CORE-09 is closed
  - 26 comprehensive LightRAG tests in test_lightrag_comprehensive.py covering all service functions

affects: [20-advanced-features, any phase touching lightrag_service.py or content generation pipeline]

tech-stack:
  added: []
  patterns:
    - "Sanitize user_id with re.sub(r'[^a-zA-Z0-9_-]', '', user_id) before lambda string interpolation"
    - "Reject user_ids containing special chars — return empty string, log warning at WARNING level"
    - "Comprehensive mock pattern: patch LIGHTRAG_URL and LIGHTRAG_API_KEY as module-level globals, not through settings"

key-files:
  created:
    - backend/tests/core/__init__.py
    - backend/tests/core/test_lightrag_lambda_injection.py
    - backend/tests/core/test_lightrag_comprehensive.py
  modified:
    - backend/services/lightrag_service.py

key-decisions:
  - "Option B chosen (sanitized lambda) over Option A (structured dict filter) — LightRAG REST API format compatibility unknown; sanitization with strict alphanum validation eliminates the attack surface without API contract changes"
  - "user_id must match [a-zA-Z0-9_-] exactly — any deviation causes early return with empty string and WARNING log"
  - "importlib.reload(svc) NOT used in comprehensive tests — module-level LIGHTRAG_URL/API_KEY globals patched directly to avoid reload overriding mock settings"

patterns-established:
  - "TDD injection tests: write test that inspects raw HTTP payload for unsafe interpolation before fixing production code"
  - "Lambda string injection test pattern: check 'or True' and 'import os' patterns in captured doc_filter_func"

requirements-completed: [CORE-05, CORE-09]

duration: 5min
completed: "2026-04-03"
---

# Phase 19 Plan 03: LightRAG Lambda Injection Fix Summary

**TDD fix for f-string user_id injection in LightRAG query filter — user_id validated to [a-zA-Z0-9_-] before lambda interpolation, blocking cross-user data leak via "or True" expansion**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-04-03T07:15:58Z
- **Completed:** 2026-04-03T07:21:27Z
- **Tasks:** 2
- **Files modified:** 4 (lightrag_service.py, 2 new test files, __init__.py)

## Accomplishments
- RED phase: 4 failing tests committed exposing the lambda injection vulnerability before any fix was written
- GREEN phase: production fix committed after tests confirmed the exploit, all 5 injection tests pass
- 26 comprehensive tests cover all 4 public functions across 6 test classes (health, insert, query, isolation, embedding, degradation)
- 31 combined new tests pass; 23 existing LightRAG tests unaffected (regression: all 54 LightRAG-related tests green)

## Task Commits

Each task was committed atomically:

1. **Task 1 RED — Failing injection tests** - `57beadc` (test)
2. **Task 1 GREEN — Lambda injection fix** - `86fdaee` (fix)
3. **Task 2 — Comprehensive LightRAG tests** - `952d27c` (test)

_Note: TDD task split into RED commit (failing test) + GREEN commit (fix)_

## Files Created/Modified
- `backend/services/lightrag_service.py` - Added `import re`, user_id validation with `re.sub`, early return on injection chars, safe `safe_uid` used in both NL query and lambda filter
- `backend/tests/core/__init__.py` - Package init for new core test directory
- `backend/tests/core/test_lightrag_lambda_injection.py` - 5 TDD tests: single-quote injection, "or True" injection, semicolon/code injection, normal user_id happy path, raw f-string payload inspection
- `backend/tests/core/test_lightrag_comprehensive.py` - 26 tests: TestHealthCheck (3), TestInsertContent (5), TestQueryKnowledgeGraph (6), TestPerUserIsolation (5), TestEmbeddingConfig (4), TestGracefulDegradation (3)

## Decisions Made

- **Option B (sanitized lambda) over Option A (structured dict):** The LightRAG REST API format for `doc_filter_func` as a structured dict was not confirmed. Rather than risk breaking the API contract, the lambda string approach was retained but with strict sanitization — `re.sub(r"[^a-zA-Z0-9_-]", "", user_id)` strips all dangerous characters before interpolation. Any user_id that changes after sanitization is rejected entirely.

- **Reject-on-mismatch:** After sanitization, if `safe_uid != user_id`, the function logs a WARNING and returns `""` immediately. This is the safest approach — no partial data, no silently truncated user_id that might collide with another user.

- **Test module reload strategy:** Using `importlib.reload(svc)` caused `LIGHTRAG_URL` and `LIGHTRAG_API_KEY` module-level variables to be re-read from real `settings` (overriding the mock). Fixed by patching module globals directly without reload.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed 5 failing tests in comprehensive test file caused by module reload pattern**
- **Found during:** Task 2 (after first run of test_lightrag_comprehensive.py)
- **Issue:** `importlib.reload(svc)` re-executed `LIGHTRAG_URL = settings.lightrag.url` and `LIGHTRAG_API_KEY = settings.lightrag.api_key` using REAL settings (not the mock), causing URL mismatches and API key not being picked up
- **Fix:** Removed `importlib.reload(svc)` calls; used `from services import lightrag_service as svc` directly. For embedding config tests, used `from services import lightrag_service as svc` without reload.
- **Files modified:** `backend/tests/core/test_lightrag_comprehensive.py`
- **Verification:** All 26 tests pass after fix
- **Committed in:** 952d27c (Task 2 commit includes the fixed test file)

---

**Total deviations:** 1 auto-fixed (Rule 1 — test infrastructure bug)
**Impact on plan:** Auto-fix was necessary to make tests work correctly. No scope creep.

## Issues Encountered

- Module-level constant patching pattern in lightrag_service tests requires patching `services.lightrag_service.LIGHTRAG_URL` and `services.lightrag_service.LIGHTRAG_API_KEY` directly (not just `settings.lightrag.url`) because these are captured at import time. The existing test files (test_lightrag_service.py, test_lightrag_isolation.py) already handle this correctly — new tests needed to follow the same pattern.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- CORE-05 and CORE-09 requirements are both complete
- 31 new tests green, 23 existing LightRAG tests unaffected
- `backend/tests/core/` directory established as home for focused/comprehensive service tests
- Next plan can reference the safe `query_knowledge_graph` user_id validation pattern

---
*Phase: 19-core-features*
*Completed: 2026-04-03*
