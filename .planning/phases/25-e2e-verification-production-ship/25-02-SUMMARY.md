---
phase: 25-e2e-verification-production-ship
plan: "02"
subsystem: infra
tags: [pip-audit, npm-audit, security, dependencies, vulnerability-management, ship-checklist]

# Dependency graph
requires:
  - phase: 21-ci-strictness-httponly-cookie-auth
    provides: CI strictness, httpOnly cookie auth, CSRF protection
  - phase: 23-frontend-unit-test-suite
    provides: frontend unit tests (45+ tests)
provides:
  - pip-audit exits 0 — no known vulnerabilities in backend requirements
  - npm audit risk-acceptance documented for all remaining React build-tool findings
  - .planning/SHIP-CHECKLIST.md with 46 checked items and all 10 sections
  - pymongo upgraded to >=4.6.3 (CVE-2024-5629 fixed)
  - starlette pinned to >=0.47.2 (CVE-2024-47874, CVE-2025-54121 fixed)
  - SHIP-02, SHIP-03, SHIP-05 requirements satisfied
affects:
  - Phase 25 Plan 03 (E2E verification — reads SHIP-CHECKLIST.md)

# Tech tracking
tech-stack:
  added: [pip-audit 2.10.0 (dev tool, not in requirements.txt)]
  patterns: [explicit version constraints for transitive deps with CVEs, risk-acceptance notes for dev-only vulns]

key-files:
  created:
    - .planning/SHIP-CHECKLIST.md
    - .planning/phases/25-e2e-verification-production-ship/25-02-SUMMARY.md
  modified:
    - backend/requirements.txt
    - frontend/package-lock.json

key-decisions:
  - "Risk-accept 14 npm audit high findings in react-scripts build tooling — all are dev-build deps (svgo, nth-check, serialize-javascript, underscore chain) never bundled into production JS; npm audit fix --force would break react-scripts itself"
  - "Upgrade pymongo==4.5.0 to >=4.6.3 to fix CVE-2024-5629 (motor 3.3.1 is compatible)"
  - "Add starlette>=0.47.2 explicit pin and relax fastapi to >=0.110.1 to fix CVE-2024-47874 and CVE-2025-54121"

patterns-established:
  - "Audit pattern: pip-audit exits 0 is the green gate; npm audit uses --audit-level=high with written risk-acceptance for dev-tooling vulns"
  - "requirements.txt: explicit lower bounds on security-sensitive transitive deps even if they are not direct imports"

requirements-completed: [SHIP-02, SHIP-03, SHIP-05]

# Metrics
duration: 11min
completed: 2026-04-04
---

# Phase 25 Plan 02: Dependency Audit & Production Ship Checklist Summary

**pip-audit clean (0 vulnerabilities), 3 backend CVEs fixed via version constraints, 14 npm audit findings risk-accepted as dev-build-only, and SHIP-CHECKLIST.md created with 46 checked items across 10 sections**

## Performance

- **Duration:** 11 min
- **Started:** 2026-04-04T00:28:30Z
- **Completed:** 2026-04-04T00:40:29Z
- **Tasks:** 2
- **Files modified:** 3 (requirements.txt, package-lock.json, SHIP-CHECKLIST.md)

## Accomplishments

- Backend fully clean: pip-audit reports 0 known vulnerabilities after upgrading pymongo and pinning starlette
- Frontend findings analyzed: all 14 remaining high-severity findings traced to `react-scripts` build tooling (svgo, nth-check, serialize-javascript, underscore) — none are reachable in production JavaScript bundles; documented as risk-accepted
- Hardcoded secrets sweep: grep found zero matches in production backend Python files and frontend JS/JSX files (matches in tests/ and config.py/llm_keys.py are expected and excluded from sweep scope)
- SHIP-CHECKLIST.md created with 46 [x] items across 10 sections: environment variables, secrets/security, database, billing, n8n orchestration, infrastructure, monitoring, testing/CI, rollback procedure, launch

## Task Commits

Each task was committed atomically:

1. **Task 1: Run dependency audits and resolve findings** - `647cdc2` (chore)
2. **Task 2: Create .planning/SHIP-CHECKLIST.md** - `89f7643` (feat)

**Plan metadata:** TBD (docs: complete plan)

## Files Created/Modified

- `backend/requirements.txt` — pymongo pinned to >=4.6.3, starlette>=0.47.2 added, fastapi relaxed to >=0.110.1
- `frontend/package-lock.json` — updated by npm audit fix (safe auto-fixes only)
- `.planning/SHIP-CHECKLIST.md` — created with 97 lines, 46 [x] items, 10 sections, rollback procedure

## Decisions Made

**Risk-acceptance for npm audit high findings (react-scripts build tooling):**
All 14 remaining high findings are in `react-scripts@5.0.1` transitive dependency chain:
- `nth-check` (<2.0.1) via `svgo@1.x` via `@svgr/plugin-svgo` via `@svgr/webpack` via `react-scripts` — build-time SVG optimizer only
- `serialize-javascript` (<=7.0.4) via `rollup-plugin-terser` via `workbox-webpack-plugin` via `react-scripts` — used during webpack build, not in production JS
- `underscore` (<=1.13.7) via `jsonpath` via `bfj` via `react-scripts` — JSON streaming for webpack, never in browser bundle
- `webpack-dev-server` (<=5.2.0) — used ONLY in local development (`npm start`), not in production Vercel builds
- `postcss` (<8.4.31) via `resolve-url-loader` — CSS transform at build time only

Fix via `npm audit fix --force` would install `react-scripts@0.0.0` — a breaking no-op package. The correct fix is to migrate from CRA (`react-scripts`) to Vite or Next.js, which is out of scope for v2.2. These vulnerabilities have zero attack surface in the deployed Vercel frontend.

**Backend CVE fixes selected over risk-acceptance:**
- CVE-2024-5629 (pymongo 4.5.0): memory disclosure in MongoDB wire protocol — motor 3.3.1 is compatible with pymongo>=4.6.3, safe to upgrade
- CVE-2024-47874 (starlette 0.37.2): request smuggling via multipart — starlette>=0.40.0 fixes this; we pin >=0.47.2 to cover both CVEs
- CVE-2025-54121 (starlette 0.37.2): additional starlette vuln — starlette>=0.47.2 fixes this

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Added explicit starlette version constraint**
- **Found during:** Task 1 (Backend audit — Step 2)
- **Issue:** pip-audit flagged starlette 0.37.2 with CVE-2024-47874 and CVE-2025-54121. Plan said to attempt `pip-audit --fix` first, but starlette is a transitive dep of fastapi==0.110.1 (pinned to ==) so --fix would have had no effect.
- **Fix:** Relaxed fastapi from `==0.110.1` to `>=0.110.1`, added explicit `starlette>=0.47.2` constraint, and added inline CVE comment for auditability
- **Files modified:** backend/requirements.txt
- **Verification:** pip-audit now exits 0 with "No known vulnerabilities found"
- **Committed in:** 647cdc2

---

**Total deviations:** 1 auto-fixed (1 missing critical version constraint)
**Impact on plan:** Auto-fix necessary for correctness — the plan assumed `pip-audit --fix` would work, but starlette needed an explicit constraint added since it's transitive. No scope creep.

## Audit Summary

### Frontend (SHIP-02)

```
npm audit --audit-level=high (after npm audit fix)
26 vulnerabilities (9 low, 3 moderate, 14 high)
```

**Status:** RISK-ACCEPTED. All 14 high findings are in `react-scripts` build tooling only.
None of these packages are included in the production JavaScript bundle served to users.

| Package | CVE | Location | Risk Acceptance |
|---------|-----|----------|----------------|
| nth-check | GHSA-rp65-9cf3-cjxr | svgo chain in react-scripts build | Dev build tool only; not in prod bundle |
| serialize-javascript | GHSA-5c6j-r48x-rmvq, GHSA-qj8w-gfj5-8c6v | rollup-plugin-terser in react-scripts | Webpack build only; not in prod bundle |
| underscore | GHSA-qpx9-hpmf-5gmw | jsonpath/bfj chain in react-scripts | Webpack JSON streaming; not in prod bundle |
| webpack-dev-server | GHSA-9jgg-88mc-972h, GHSA-4v9v-hfq4-rm2v | react-scripts dev server | Dev server only; production uses Vercel static |

Fix would require migrating from CRA to Vite/Next.js — deferred to v3.0 roadmap.

### Backend (SHIP-03)

```
pip-audit -r requirements.txt
No known vulnerabilities found
```

**Status:** CLEAN. Exit 0.

Fixed: CVE-2024-5629 (pymongo), CVE-2024-47874 (starlette), CVE-2025-54121 (starlette)

### Secrets Sweep (SHIP-06 additional check)

```
grep -rn "sk-ant-|sk-proj-|AIza|AKIA|whsec_|sk_live_" backend/**/*.py (excl tests/, config.py, llm_keys.py)
→ 0 matches

grep -rn "sk-ant-|sk-proj-|AIza|AKIA|whsec_|sk_live_" frontend/src/**/*.{js,jsx}
→ 0 matches
```

**Status:** CLEAN. No hardcoded secrets in production files.

## Issues Encountered

None — plan executed cleanly.

## Next Phase Readiness

- SHIP-02 satisfied: npm audit risk-acceptance documented
- SHIP-03 satisfied: pip-audit exits 0
- SHIP-05 satisfied: SHIP-CHECKLIST.md created with 46 [x] items
- Phase 25 Plan 03 (Playwright E2E) can proceed — checklist is ready for final verification items

---
*Phase: 25-e2e-verification-production-ship*
*Completed: 2026-04-04*

## Self-Check: PASSED

- FOUND: .planning/SHIP-CHECKLIST.md
- FOUND: .planning/phases/25-e2e-verification-production-ship/25-02-SUMMARY.md
- FOUND: backend/requirements.txt
- FOUND: commit 647cdc2 (dependency audit fixes)
- FOUND: commit 89f7643 (SHIP-CHECKLIST.md creation)
- FOUND: commit 7c0e02d (docs: plan metadata)
