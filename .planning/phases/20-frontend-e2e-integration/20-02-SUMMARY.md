---
phase: 20-frontend-e2e-integration
plan: 02
subsystem: testing
tags: [locust, load-testing, docker-compose, smoke-test, integration, pytest, e2e]

# Dependency graph
requires:
  - phase: 20-frontend-e2e-integration-01
    provides: Playwright E2E foundation and test infrastructure

provides:
  - Locust load test with 50 concurrent user simulation for content generation and credit atomicity
  - Docker Compose integration smoke test validating all 7 services healthy within 120s
  - pytest.ini markers config for integration test isolation

affects:
  - CI pipeline — load tests run headlessly with `locust --headless -u 50 -r 10`
  - Docker deployment — smoke test validates compose stack on every release

# Tech tracking
tech-stack:
  added: [locust>=2.43.4 (install separately — not in requirements.txt)]
  patterns:
    - Locust HttpUser with on_start for per-worker JWT auth flow
    - Custom Locust failure events for business-logic assertions (credit atomicity)
    - post-run listener (events.test_stop) for credit health summary
    - pytest.mark.integration with pytestmark.skipif for Docker auto-skip
    - norecursedirs in pytest.ini to exclude tests/load from collection

key-files:
  created:
    - backend/tests/load/__init__.py
    - backend/tests/load/locustfile.py
    - backend/tests/integration/__init__.py
    - backend/tests/integration/test_docker_smoke.py
  modified:
    - backend/pytest.ini

key-decisions:
  - "Locust not added to requirements.txt — it is a dev/CI tool installed separately (pip install locust>=2.43.4)"
  - "norecursedirs used instead of collect_ignore_glob to exclude tests/load (collect_ignore_glob caused PytestConfigWarning)"
  - "Docker smoke test uses class-scoped fixture to bring stack up once for all 3 tests, minimizing compose overhead"
  - "Per-service timeouts vary (mongo/redis 30s, backend 60s, n8n/lightrag/remotion 90s, frontend 120s) to fail fast on infrastructure services"

patterns-established:
  - "Pattern 1: Locust auth flow — register unique user per worker with uuid4 email, capture JWT, fall back to login on 409"
  - "Pattern 2: Credit atomicity check — parse credits field from response, fire custom Locust event on negative balance"
  - "Pattern 3: Integration test isolation — pytestmark = pytest.mark.skipif(not shutil.which('docker')) at module level"
  - "Pattern 4: Docker fixture scope — class-scoped compose_up fixture to amortize docker compose build time"

requirements-completed: [E2E-05, E2E-06]

# Metrics
duration: 4min
completed: 2026-04-03
---

# Phase 20 Plan 02: Load Testing + Docker Compose Smoke Summary

**Locust 50-user load test with credit atomicity guard and Docker Compose smoke test validating all 7 services healthy within 120 seconds**

## Performance

- **Duration:** 4 min
- **Started:** 2026-04-03T07:57:37Z
- **Completed:** 2026-04-03T08:01:00Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments

- Created Locust load test simulating 50 concurrent users hitting content generation, dashboard, and billing endpoints with JWT auth flow per worker
- Added credit atomicity verification: custom Locust failure event fires if any worker detects `credits < 0`, plus a post-run summary listener
- Created Docker Compose smoke test validating 7 services (backend, frontend, mongo, redis, n8n, lightrag, remotion) become healthy within 120 seconds total
- Updated `pytest.ini` with `integration` marker and `norecursedirs` exclusion for `tests/load`

## Task Commits

Each task was committed atomically:

1. **Task 1: Create Locust load test for 50 concurrent users** - `4692953` (feat)
2. **Task 2: Create Docker Compose integration smoke test** - `2876768` (feat)

## Files Created/Modified

- `backend/tests/load/__init__.py` - Empty init for load test package
- `backend/tests/load/locustfile.py` - ThookAIUser Locust class: on_start JWT auth, @task generate_content (weight 3), @task check_dashboard (weight 1), @task check_credits (weight 1), post-run credit health listener
- `backend/tests/integration/__init__.py` - Empty init for integration test package
- `backend/tests/integration/test_docker_smoke.py` - TestDockerComposeSmokeE2E06: 3 tests, class-scoped compose_up fixture, _wait_for_url/_wait_for_port helpers, SERVICES config for all 7 services
- `backend/pytest.ini` - Added `integration` marker, `norecursedirs = tests/load`

## Decisions Made

- Locust excluded from `requirements.txt` — it is a dev/CI standalone tool installed separately. Documented in locustfile docstring: "Install locust before running: pip install locust>=2.43.4"
- Used `norecursedirs` (not `collect_ignore_glob`) to exclude `tests/load` from pytest collection — `collect_ignore_glob` is not a recognized pytest.ini key and caused a warning
- Docker smoke test uses a class-scoped `compose_up` fixture so `docker compose up --build` runs once for all 3 tests, avoiding redundant build overhead
- Per-service timeout budgets are service-specific: infrastructure (mongo/redis) 30s, backend 60s, complex services (n8n/lightrag/remotion) 90s, frontend 120s

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed invalid pytest.ini key `collect_ignore_glob`**
- **Found during:** Task 2 verification (pytest --collect-only)
- **Issue:** `collect_ignore_glob` is not a recognized pytest.ini option; caused `PytestConfigWarning: Unknown config option: collect_ignore_glob` in output
- **Fix:** Replaced with `norecursedirs = tests/load` which is the correct pytest mechanism for excluding directories from recursion
- **Files modified:** `backend/pytest.ini`
- **Verification:** `pytest --collect-only -q` shows no warnings and locustfile.py is not collected
- **Committed in:** `2876768` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 Rule 1 bug fix)
**Impact on plan:** Minor — pytest config key name corrected; functionality equivalent and warning eliminated.

## Issues Encountered

None — both files parse cleanly, pytest collection works correctly, and all verification steps passed.

## User Setup Required

To run load tests (Locust not in requirements.txt):
```bash
pip install locust>=2.43.4
cd backend
locust -f tests/load/locustfile.py --headless -u 50 -r 10 --run-time 60s --host http://localhost:8001 --csv=load-results
```

To run Docker Compose smoke test:
```bash
cd backend
pytest tests/integration/test_docker_smoke.py -v -m integration
```

To skip integration tests in fast CI:
```bash
pytest -m "not integration"
```

## Next Phase Readiness

- Load test ready for CI integration once a running backend URL is available
- Docker smoke test auto-skips without Docker, runs full validation in Docker environments
- Both test types isolated from regular `pytest` runs via markers and norecursedirs

## Self-Check: PASSED

- All 6 files exist on disk
- Commits 4692953 (Task 1) and 2876768 (Task 2) verified in git log

---
*Phase: 20-frontend-e2e-integration*
*Completed: 2026-04-03*
