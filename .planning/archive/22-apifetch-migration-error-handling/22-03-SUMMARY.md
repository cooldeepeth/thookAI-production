---
phase: 22-apifetch-migration-error-handling
plan: "03"
subsystem: frontend
tags: [apiFetch, migration, auth, dashboard]
dependency_graph:
  requires: [22-01]
  provides: [API-05, API-06]
  affects: [frontend/src/pages/Dashboard]
tech_stack:
  added: []
  patterns: [apiFetch centralized client, cookie-based auth, CSRF injection]
key_files:
  created: []
  modified:
    - frontend/src/pages/Dashboard/Settings.jsx
    - frontend/src/pages/Dashboard/ContentStudio/index.jsx
    - frontend/src/pages/Dashboard/ContentStudio/ContentOutput.jsx
    - frontend/src/pages/Dashboard/AdminUsers.jsx
    - frontend/src/pages/Dashboard/AgencyWorkspace/index.jsx
    - frontend/src/pages/Dashboard/ContentCalendar.jsx
    - frontend/src/pages/Dashboard/Analytics.jsx
    - frontend/src/pages/Dashboard/PersonaEngine.jsx
    - frontend/src/pages/Dashboard/DailyBrief.jsx
    - frontend/src/pages/Dashboard/DashboardHome.jsx
    - frontend/src/pages/Dashboard/Sidebar.jsx
    - frontend/src/pages/Dashboard/Connections.jsx
    - frontend/src/pages/Dashboard/RepurposeAgent.jsx
    - frontend/src/pages/Dashboard/StrategyDashboard.jsx
    - frontend/src/pages/Dashboard/Templates.jsx
    - frontend/src/pages/Dashboard/Admin.jsx
    - frontend/src/pages/Dashboard/ContentLibrary.jsx
decisions:
  - "Migrated all 17 Dashboard page files to apiFetch — zero raw fetch() calls now remain in frontend/src/ except the two internal lines inside api.js itself"
  - "Deleted getHeaders() helper in AdminUsers.jsx — replaced with apiFetch which handles auth uniformly"
  - "Kept all response handling (.ok, .json(), .status) intact — apiFetch is backward-compatible"
metrics:
  duration: "30 minutes"
  completed: "2026-04-03T21:28:51Z"
  tasks: 2
  files: 17
---

# Phase 22 Plan 03: Dashboard apiFetch Migration Summary

**One-liner:** Migrated all 17 Dashboard pages (~79 raw fetch() calls) to the centralized apiFetch client, achieving API-05 and API-06 — zero raw fetch calls remain in frontend/src/ outside api.js.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Migrate all 17 Dashboard page files to apiFetch | f972f62 | 17 Dashboard .jsx files |
| 2 | Final grep verification — zero raw fetch() in frontend/src/ | f972f62 | (verification only, no files) |

## What Was Done

### Task 1: 17-File Dashboard Migration

Every file in `frontend/src/pages/Dashboard/` (and its subdirectories) was migrated from the old raw fetch pattern to apiFetch.

**Migration pattern applied to each file:**
1. Added `import { apiFetch } from '@/lib/api';` at top
2. Removed `const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;` (or `const API_URL = ...`)
3. Removed all `const token = localStorage.getItem("thook_token");` lines
4. Removed all `const headers = { Authorization: \`Bearer ${token}\` };` inline auth objects
5. Replaced every `fetch(\`${BACKEND_URL}/api/...\`, { credentials, headers })` with `apiFetch('/api/...')`
6. Removed `credentials: "include"` from all options (apiFetch adds it automatically)
7. Removed inline auth headers (apiFetch injects CSRF and handles auth via cookies)
8. Kept all response handling unchanged (.ok, .json(), .status checks)

**Files migrated and fetch call counts:**

| File | apiFetch calls |
|------|---------------|
| Settings.jsx | 12 |
| ContentStudio/index.jsx | 7 |
| ContentStudio/ContentOutput.jsx | 6 |
| PersonaEngine.jsx | 7 |
| AdminUsers.jsx | 5 |
| AgencyWorkspace/index.jsx | 5 |
| ContentCalendar.jsx | 5 |
| Analytics.jsx | 5 |
| RepurposeAgent.jsx | 4 |
| Connections.jsx | 4 |
| DailyBrief.jsx | 4 |
| ContentLibrary.jsx | 4 |
| Admin.jsx | 3 |
| Sidebar.jsx | 2 |
| StrategyDashboard.jsx | 2 |
| Templates.jsx | 2 |
| DashboardHome.jsx | 2 |
| **Total** | **79** |

### Task 2: Final Verification — API-06 Gate

```
grep -rn "fetch(" frontend/src/ --include="*.js" --include="*.jsx" | grep -v apiFetch | grep -v node_modules | grep -v "//"
```
**Result:** Only `frontend/src/lib/api.js` lines 51 and 58 (the internal fetch() calls that apiFetch itself uses).

```
grep -rn "localStorage.getItem" frontend/src/
```
**Result:** ZERO matches.

```
grep -rn "const BACKEND_URL = process.env|const API_URL = process.env" frontend/src/
```
**Result:** ZERO matches.

**Build result:** `CI=false npm run build` (craco) exits 0 with no warnings.

## Totals Across Plans 02 + 03

| Metric | Plan 02 | Plan 03 | Total |
|--------|---------|---------|-------|
| Files migrated | ~8 | 17 | 25 |
| Raw fetch() calls replaced | ~25 | ~79 | ~104 |
| localStorage references removed | ~10 | 17+ | 27+ |
| BACKEND_URL declarations removed | ~8 | 17 | 25 |

## Requirements Fulfilled

- **API-05:** Every Dashboard page uses apiFetch instead of raw fetch() — COMPLETE
- **API-06:** Zero raw fetch() calls anywhere in frontend/src/ except api.js internal — COMPLETE

## Deviations from Plan

None — plan executed exactly as written. Every file was migrated with the exact pattern specified, the build passed, and all grep checks returned zero unexpected matches.

## Known Stubs

None. All fetch calls are wired to real API endpoints. No placeholder data or stub responses.

## Self-Check: PASSED

Files exist:
- [x] frontend/src/pages/Dashboard/Settings.jsx — FOUND
- [x] frontend/src/pages/Dashboard/ContentStudio/index.jsx — FOUND
- [x] frontend/src/pages/Dashboard/ContentStudio/ContentOutput.jsx — FOUND
- [x] All 17 files confirmed modified and present

Commits exist:
- [x] f972f62 — feat(22-03): migrate all 17 Dashboard pages from raw fetch to apiFetch
