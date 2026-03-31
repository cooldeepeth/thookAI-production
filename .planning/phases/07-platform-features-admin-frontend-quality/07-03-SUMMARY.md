---
phase: "07"
plan: "03"
subsystem: backend-tests
tags: [testing, admin, agency, workspace, tdd]
dependency_graph:
  requires: []
  provides: [test-coverage-ADMIN-01, test-coverage-ADMIN-02, test-coverage-ADMIN-03, test-coverage-ADMIN-04]
  affects: [backend/tests/test_admin_agency.py]
tech_stack:
  added: []
  patterns: [dependency-override, route-level-db-patch, async-cursor-mock]
key_files:
  created:
    - backend/tests/test_admin_agency.py
  modified: []
decisions:
  - "Patch routes.admin.db and routes.agency.db (not database.db) because modules bind 'db' at import time via 'from database import db'"
  - "Use 'custom' tier for admin tier-change test — TIER_CONFIGS only has starter/custom/free; pro/studio are not separate keys in this codebase"
  - "Implemented proper async cursor mock class with __aiter__/__anext__ protocol instead of assigning bound generator method to MagicMock"
  - "Patch database.db (not auth_utils.db) for require_admin check — auth_utils imports db inside function body as a local import"
metrics:
  duration: "8 minutes"
  completed_date: "2026-03-31"
  tasks_completed: 2
  files_created: 1
  files_modified: 0
requirements_covered:
  - ADMIN-01
  - ADMIN-02
  - ADMIN-03
  - ADMIN-04
---

# Phase 07 Plan 03: Admin Dashboard and Agency Workspace Tests Summary

**One-liner:** 15 passing tests covering admin stats, user management, workspace CRUD with tier enforcement, invitation emails, and role-based access control.

## What Was Built

Created `backend/tests/test_admin_agency.py` with 3 test classes and 15 tests covering all 4 ADMIN requirements.

### TestAdminDashboard (ADMIN-01)
Tests the `/api/admin/` endpoint suite (mounted at `/api/admin` directly on app, not via `api_router`):
- `test_stats_overview_returns_real_counts` — GET `/api/admin/stats/overview` returns `total_users`, `content_jobs_today`, `subscription_breakdown` with real DB query mocks
- `test_stats_overview_403_without_admin_role` — Non-admin gets 403 when `require_admin` dependency runs with role=user
- `test_admin_list_users_returns_paginated_list` — GET `/api/admin/users` returns paginated list with users/total/page keys
- `test_admin_list_users_tier_filter` — `?tier=pro` passes tier to `count_documents` query
- `test_admin_change_tier` — POST `/api/admin/users/{id}/tier` updates tier, returns tier name
- `test_admin_change_tier_invalid_tier_returns_400` — Unknown tier name returns 400
- `test_admin_grant_credits` — POST `/api/admin/users/{id}/credits` calls `add_credits` service, returns `new_balance`

### TestAgencyWorkspace (ADMIN-02)
Tests workspace CRUD at `/api/agency/workspace*`:
- `test_create_workspace_agency_tier_succeeds` — Agency-tier user creates workspace, response includes `workspace_id`
- `test_create_workspace_free_tier_returns_403` — Starter-tier user gets 403 with "team" or "paid plan" message
- `test_list_workspaces_returns_owned_and_member` — GET `/api/agency/workspaces` returns `success: True` with owned workspaces

### TestWorkspaceInvitations (ADMIN-03 + ADMIN-04)
Tests invitation flow and role management:
- `test_invite_sends_email` — POST invite calls `send_workspace_invite_email`, returns invite_id and email
- `test_invite_creates_pending_member_record` — `workspace_members.insert_one` called with `status=pending`
- `test_update_member_role_valid` — PUT role update returns `success: True`
- `test_update_member_role_invalid_returns_400` — Invalid role `superadmin` returns 400
- `test_non_owner_cannot_change_roles` — Creator-role member gets 403 trying to change another member's role

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed patch targets from database.db to routes.admin.db / routes.agency.db**
- **Found during:** Task 1 execution — tests hit real Motor database causing "Event loop is closed" errors
- **Issue:** Both `admin.py` and `agency.py` use `from database import db` at module level, binding `db` to the local namespace at import time. Patching `database.db` at runtime has no effect on the already-bound reference.
- **Fix:** Changed all patches to `routes.admin.db` and `routes.agency.db` respectively.
- **Files modified:** backend/tests/test_admin_agency.py
- **Commit:** 61e98d1

**2. [Rule 1 - Bug] Fixed async cursor mock for Motor cursor iteration**
- **Found during:** Task 1 — `TypeError: _aiter() takes 1 positional argument but 2 were given`
- **Issue:** Assigning `_aiter.__get__(mock_cursor)` to `mock_cursor.__aiter__` on a MagicMock doesn't work correctly because MagicMock wraps it and passes extra args.
- **Fix:** Created a proper `_AsyncCursor` class with `__aiter__` returning `self` and `__anext__` iterating over items, plus `sort()`/`skip()`/`limit()` chainable methods.
- **Files modified:** backend/tests/test_admin_agency.py
- **Commit:** 61e98d1

**3. [Rule 1 - Bug] Fixed tier value in admin_change_tier test**
- **Found during:** Task 1 — test returned 400 instead of 200
- **Issue:** Test used `"tier": "pro"` but `TIER_CONFIGS` in `services/credits.py` only contains `starter`, `custom`, and `free` (alias). The codebase transitioned to custom plan builder; `pro`/`studio` are not valid TIER_CONFIGS keys.
- **Fix:** Changed test to use `"custom"` (valid key in TIER_CONFIGS).
- **Files modified:** backend/tests/test_admin_agency.py
- **Commit:** 61e98d1

**4. [Rule 1 - Bug] Fixed auth_utils.db patch target**
- **Found during:** Task 1 — `AttributeError: module 'auth_utils' does not have attribute 'db'`
- **Issue:** `require_admin` in `auth_utils.py` does `from database import db` INSIDE the function body (local import), so there's no module-level `db` attribute on `auth_utils`.
- **Fix:** Changed patch target to `database.db` which is the actual source module.
- **Files modified:** backend/tests/test_admin_agency.py
- **Commit:** 61e98d1

## Self-Check

- [x] backend/tests/test_admin_agency.py exists (533 lines)
- [x] class TestAdminDashboard present
- [x] class TestAgencyWorkspace present
- [x] class TestWorkspaceInvitations present
- [x] grep "require_admin" matches
- [x] grep "total_users" matches
- [x] grep "send_workspace_invite_email" matches
- [x] grep "403" matches
- [x] All 15 tests pass: `python3 -m pytest tests/test_admin_agency.py -v` → 15 passed
- [x] Commit 61e98d1 exists

## Self-Check: PASSED
