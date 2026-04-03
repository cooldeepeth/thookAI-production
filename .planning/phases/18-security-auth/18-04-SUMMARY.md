---
phase: 18-security-auth
plan: 04
subsystem: testing
tags: [pytest, fastapi, rbac, admin, workspace, authorization, security]

# Dependency graph
requires:
  - phase: 18-01-PLAN
    provides: conftest fixtures and security test patterns for the phase

provides:
  - Admin route authorization tests (7 tests) — all admin endpoints return 403 for non-admin users
  - Workspace RBAC enforcement tests (8 tests) — role boundaries verified for creator/manager/owner

affects: [security-auth, agency, admin]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Patch 'database.db' module attribute for auth_utils lazy imports; patch 'routes.X.db' for module-level imports
    - Agency router carries its own prefix="/agency" — mount under "/api" (not "/api/agency") to avoid double prefix
    - Use dependency_overrides[get_current_user] (not mock patches) for auth bypass in TestClient apps

key-files:
  created:
    - backend/tests/security/__init__.py
    - backend/tests/security/test_admin_rbac.py
  modified: []

key-decisions:
  - "Patch 'database.db' (not 'auth_utils.db') because auth_utils imports db lazily inside function bodies; routes.admin.db and routes.agency.db are module-level imports that need separate patches"
  - "Agency router prefix is '/agency' at declaration; test app must mount it under '/api' prefix to replicate server layout and avoid doubled /agency/agency paths"
  - "test_non_admin_user_gets_403_on_change_tier uses POST not PUT because admin.py uses @router.post for the tier endpoint"

patterns-established:
  - "Pattern: For FastAPI routes using 'from database import db' at module level, patch 'routes.module_name.db'; for lazy imports inside functions, patch 'database.db'"
  - "Pattern: Agency router self-declares prefix so TestClient app factory must NOT re-add the prefix"

requirements-completed: [SEC-06]

# Metrics
duration: 18min
completed: 2026-04-03
---

# Phase 18 Plan 04: Admin RBAC Tests Summary

**15 privilege-escalation tests verifying non-admin users get 403 on all admin endpoints and workspace role boundaries (creator/manager/owner) are enforced via FastAPI dependency_overrides + database.db patching**

## Performance

- **Duration:** 18 min
- **Started:** 2026-04-03T06:31:00Z
- **Completed:** 2026-04-03T06:49:23Z
- **Tasks:** 1
- **Files modified:** 2 (created)

## Accomplishments

- Created `backend/tests/security/` package with 15 tests covering SEC-06
- TestAdminRouteAuthorization (7 tests): every admin endpoint returns 403 for non-admin users; admin user gets 200 on stats; unauthenticated request returns 401
- TestWorkspaceRoleEnforcement (8 tests): non-member denied invite, creator role cannot invite/change-role/remove, owner can perform all operations, non-agency tier blocked from workspace creation, studio tier allowed

## Task Commits

1. **Task 1: Admin route authorization and workspace RBAC tests** - `6d64ce5` (test)

**Plan metadata:** (docs commit follows)

## Files Created/Modified

- `backend/tests/security/__init__.py` - Package marker for security test directory
- `backend/tests/security/test_admin_rbac.py` - 494 lines, 15 tests covering admin authorization and workspace RBAC (SEC-06)

## Decisions Made

- Patch `database.db` (not `auth_utils.db`) because `auth_utils.require_admin` imports `db` lazily inside the function body at runtime; `patch("auth_utils.db", ...)` fails with AttributeError since db is not a module-level attribute there.
- Agency router self-declares `prefix="/agency"` in its `APIRouter(...)` constructor. Test app factory must mount it under `prefix="/api"` only — otherwise paths double to `/api/agency/agency/...`.
- Admin tier change endpoint is `@router.post` not `@router.put` per `routes/admin.py` — test uses POST accordingly.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed route double-prefix in agency app factory**
- **Found during:** Task 1
- **Issue:** Initial `_make_agency_app()` mounted router at `prefix="/api/agency"` but the agency router already declares `prefix="/agency"`. This produced `/api/agency/agency/...` paths causing all route calls to return 404.
- **Fix:** Changed mount prefix from `"/api/agency"` to `"/api"` to replicate the real server layout.
- **Files modified:** `backend/tests/security/test_admin_rbac.py`
- **Verification:** All 8 workspace tests passed after fix
- **Committed in:** 6d64ce5

**2. [Rule 1 - Bug] Switched auth patch from `auth_utils.db` to `database.db`**
- **Found during:** Task 1
- **Issue:** `patch("auth_utils.db", db_mock)` raised `AttributeError: module 'auth_utils' does not have the attribute 'db'` because `db` is imported inside function bodies not at module level.
- **Fix:** Changed all admin test patches to `patch("database.db", db_mock)` with `patch("routes.admin.db", db_mock)` for the module-level import.
- **Files modified:** `backend/tests/security/test_admin_rbac.py`
- **Verification:** All 7 admin tests passed after fix
- **Committed in:** 6d64ce5

---

**Total deviations:** 2 auto-fixed (both Rule 1 - Bug in test code)
**Impact on plan:** Both auto-fixes necessary to resolve FastAPI routing and Python mock patching issues. No scope creep — test logic and intent unchanged.

## Issues Encountered

None beyond the two auto-fixed deviations above.

## Known Stubs

None — this plan delivers tests only, no application logic.

## Next Phase Readiness

- Admin authorization and workspace RBAC are now confirmed to behave correctly under test isolation
- Security test suite ready for 18-05 and later plans to build upon
- Pattern established for patching db in FastAPI test apps with mixed lazy/module-level imports

---
*Phase: 18-security-auth*
*Completed: 2026-04-03*
