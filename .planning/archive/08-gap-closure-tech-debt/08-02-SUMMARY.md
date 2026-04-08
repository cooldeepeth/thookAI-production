---
phase: 08-gap-closure-tech-debt
plan: 02
subsystem: ui
tags: [react, cra, env-vars, frontend, requirements]

# Dependency graph
requires:
  - phase: 07-platform-features-admin-frontend-quality
    provides: Completed frontend feature implementations these files belong to

provides:
  - CRA-only env var syntax in all 12 Dashboard frontend files
  - Accurate REQUIREMENTS.md traceability table with all 52 requirements marked Complete

affects:
  - frontend builds (Vercel deploy will no longer have Vite env syntax warnings)
  - REQUIREMENTS.md consumers (all 15 previously-Pending requirements now show correct status)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "CRA env var pattern: process.env.REACT_APP_BACKEND_URL (no import.meta.env fallback)"

key-files:
  created: []
  modified:
    - frontend/src/pages/Dashboard/DailyBrief.jsx
    - frontend/src/pages/Dashboard/AdminUsers.jsx
    - frontend/src/pages/Dashboard/DashboardHome.jsx
    - frontend/src/pages/Dashboard/ContentLibrary.jsx
    - frontend/src/pages/Dashboard/Admin.jsx
    - frontend/src/pages/Dashboard/ContentStudio/ContentOutput.jsx
    - frontend/src/pages/Dashboard/Analytics.jsx
    - frontend/src/pages/Dashboard/RepurposeAgent.jsx
    - frontend/src/pages/Dashboard/Settings.jsx
    - frontend/src/pages/Dashboard/Sidebar.jsx
    - frontend/src/pages/Dashboard/Connections.jsx
    - frontend/src/pages/Dashboard/ContentCalendar.jsx
    - .planning/REQUIREMENTS.md

key-decisions:
  - "Keep original variable names (API_URL vs BACKEND_URL) per file — no variable renaming"
  - "Admin.jsx and AdminUsers.jsx had multi-line declarations collapsed to single-line process.env form"

patterns-established:
  - "CRA env pattern: all frontend files declare backend URL as const X = process.env.REACT_APP_BACKEND_URL"

requirements-completed: [MEDIA-05]

# Metrics
duration: 8min
completed: 2026-03-31
---

# Phase 08 Plan 02: Gap Closure Tech Debt — Env Var Fix & Requirements Drift Summary

**Eliminated Vite/CRA env var collision in 12 frontend files and corrected 15 stale Pending entries in REQUIREMENTS.md traceability table**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-03-31T13:16:00Z
- **Completed:** 2026-03-31T13:24:19Z
- **Tasks:** 2
- **Files modified:** 13 (12 frontend + 1 planning)

## Accomplishments

- Replaced Vite fallback pattern (`import.meta.env.REACT_APP_BACKEND_URL || process.env.REACT_APP_BACKEND_URL`) with CRA-only syntax in all 12 targeted Dashboard files — zero `import.meta.env` occurrences remain in `frontend/src/`
- Corrected 15 traceability rows in REQUIREMENTS.md from "Pending" to "Complete" (GIT-01 through GIT-04, INFRA-01 through INFRA-07, AUTH-01 through AUTH-04)
- Updated 15 requirement checkboxes from `[ ]` to `[x]` at the top of REQUIREMENTS.md — all 52 v1 requirements now show correct status

## Task Commits

Each task was committed atomically:

1. **Task 1: Replace import.meta.env with process.env in all frontend files** - `a6ec3d6` (fix)
2. **Task 2: Fix REQUIREMENTS.md traceability table doc drift** - `481455d` (docs)

**Plan metadata:** (docs commit below)

## Files Created/Modified

- `frontend/src/pages/Dashboard/DailyBrief.jsx` - env var: `const API_URL = process.env.REACT_APP_BACKEND_URL`
- `frontend/src/pages/Dashboard/DashboardHome.jsx` - env var: `const API_URL = process.env.REACT_APP_BACKEND_URL`
- `frontend/src/pages/Dashboard/ContentStudio/ContentOutput.jsx` - env var: `const API_URL = process.env.REACT_APP_BACKEND_URL`
- `frontend/src/pages/Dashboard/Analytics.jsx` - env var: `const BACKEND_URL = process.env.REACT_APP_BACKEND_URL`
- `frontend/src/pages/Dashboard/RepurposeAgent.jsx` - env var: `const BACKEND_URL = process.env.REACT_APP_BACKEND_URL`
- `frontend/src/pages/Dashboard/Settings.jsx` - env var: `const BACKEND_URL = process.env.REACT_APP_BACKEND_URL`
- `frontend/src/pages/Dashboard/Sidebar.jsx` - env var: `const BACKEND_URL = process.env.REACT_APP_BACKEND_URL`
- `frontend/src/pages/Dashboard/Connections.jsx` - env var: `const BACKEND_URL = process.env.REACT_APP_BACKEND_URL`
- `frontend/src/pages/Dashboard/ContentCalendar.jsx` - env var: `const BACKEND_URL = process.env.REACT_APP_BACKEND_URL`
- `frontend/src/pages/Dashboard/ContentLibrary.jsx` - env var: `const BACKEND_URL = process.env.REACT_APP_BACKEND_URL`
- `frontend/src/pages/Dashboard/Admin.jsx` - env var: `const BACKEND_URL = process.env.REACT_APP_BACKEND_URL` (collapsed multi-line)
- `frontend/src/pages/Dashboard/AdminUsers.jsx` - env var: `const BACKEND_URL = process.env.REACT_APP_BACKEND_URL` (collapsed multi-line)
- `.planning/REQUIREMENTS.md` - 15 traceability rows Pending→Complete, 15 checkboxes [ ]→[x]

## Decisions Made

- Preserved original variable names per file (some use `API_URL`, others `BACKEND_URL`) — renaming would risk breaking downstream references
- Admin.jsx and AdminUsers.jsx had multi-line declarations — collapsed to single-line form for consistency with other files

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None. The plan note about Admin.jsx using `API_URL` was inaccurate — the file actually uses `BACKEND_URL`. The correct variable name was preserved, which is the right behavior.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 08 Plan 02 complete
- All 52 v1 requirements now correctly show Complete status in REQUIREMENTS.md
- Frontend build no longer carries Vite-syntax env var declarations that would be silently undefined in CRA builds
- Phase 08 stabilization gap closure is now complete (both plans done)

---
*Phase: 08-gap-closure-tech-debt*
*Completed: 2026-03-31*
