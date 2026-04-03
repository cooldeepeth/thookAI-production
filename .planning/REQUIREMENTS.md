# Requirements: ThookAI v2.2 — Frontend Hardening & Production Ship

**Defined:** 2026-04-04
**Core Value:** Frontend hardened for production launch — no raw fetch, no localStorage JWT, no CI blind spots, tested and ship-ready.

## v2.2 Requirements

### CI Strictness

- [ ] **CI-01**: Remove all `continue-on-error: true` from `.github/workflows/ci.yml` — all 4 backend test jobs must block on failure
- [ ] **CI-02**: Remove `continue-on-error: true` from `.github/workflows/e2e.yml` — Playwright must block on failure
- [ ] **CI-03**: All CI checks pass green on dev branch after changes

### Auth Migration

- [ ] **AUTH-01**: Backend sets httpOnly secure cookie on login/register (alongside existing JWT response for backward compat)
- [ ] **AUTH-02**: Backend middleware reads auth from cookie first, falls back to Authorization header
- [ ] **AUTH-03**: Frontend AuthContext reads from cookie-based session (no more localStorage.getItem for JWT)
- [ ] **AUTH-04**: Frontend removes `localStorage.setItem("thook_token", ...)` after cookie migration confirmed
- [ ] **AUTH-05**: CSRF protection added for cookie-based auth (double-submit or synchronizer token pattern)

### API Client

- [ ] **API-01**: Create `frontend/src/lib/apiFetch.js` — centralized fetch wrapper with base URL, auth headers, timeout (15s default), JSON parsing
- [ ] **API-02**: Add automatic retry (1 retry on 5xx, exponential backoff) to apiFetch
- [ ] **API-03**: Add global error handler — 401 redirects to /auth, 403 shows permission error, 5xx shows toast
- [ ] **API-04**: Create `frontend/src/lib/constants.js` — API base URL, feature flags, app config
- [ ] **API-05**: Replace all 41 raw `fetch()` calls across frontend with `apiFetch()`
- [ ] **API-06**: Zero raw `fetch()` calls remain in `frontend/src/` (grep verification)

### Frontend Tests

- [ ] **TEST-01**: Install `@testing-library/react`, `@testing-library/jest-dom`, `@testing-library/user-event`, `msw` (v2)
- [ ] **TEST-02**: Configure Jest via CRA defaults — no eject, no custom webpack
- [ ] **TEST-03**: Write 45+ unit/component tests across 10+ test files
- [ ] **TEST-04**: Add `frontend-test` CI job to `.github/workflows/ci.yml`
- [ ] **TEST-05**: Tests cover: AuthContext, apiFetch, StrategyDashboard, ContentStudio, Sidebar, NotificationBell, key hooks

### Content Download & Redirect

- [ ] **DL-01**: Download text content as `.txt` file from content detail view
- [ ] **DL-02**: Download generated images individually or as `.zip` for carousels
- [ ] **DL-03**: "Open in LinkedIn" button with pre-filled compose URL
- [ ] **DL-04**: "Open in X" button with pre-filled tweet intent URL
- [ ] **DL-05**: "Open in Instagram" info tooltip (Instagram has no compose URL — explain copy workflow)
- [ ] **DL-06**: Download/redirect buttons appear alongside existing Publish button

### E2E & Production Ship

- [ ] **SHIP-01**: Full Playwright E2E passes green (critical path, billing, agency, download/redirect)
- [ ] **SHIP-02**: `npm audit` reports 0 critical/high vulnerabilities in frontend
- [ ] **SHIP-03**: `pip-audit` or `safety check` reports 0 critical vulnerabilities in backend
- [ ] **SHIP-04**: All environment variables documented in `.env.example` with descriptions
- [ ] **SHIP-05**: Production deployment checklist document created
- [ ] **SHIP-06**: Final security sweep — no hardcoded secrets, no debug endpoints, no console.log in production

## Future Requirements

- **FE-F01**: Component library documentation (Storybook) — v3.0
- **FE-F02**: Accessibility audit (WCAG 2.1 AA) — v3.0
- **FE-F03**: Progressive Web App (offline support) — v3.0

## Out of Scope

| Feature | Reason |
|---------|--------|
| Backend feature development | Frontend-only milestone |
| Mobile native apps | Web-first, deferred to v3.0 |
| Full UI/UX redesign | Incremental improvements only |
| Multi-language | Deferred to v3.0 |
| Storybook | Deferred to v3.0 |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| CI-01 | Phase 21 | Pending |
| CI-02 | Phase 21 | Pending |
| CI-03 | Phase 21 | Pending |
| AUTH-01 | Phase 21 | Pending |
| AUTH-02 | Phase 21 | Pending |
| AUTH-03 | Phase 21 | Pending |
| AUTH-04 | Phase 21 | Pending |
| AUTH-05 | Phase 21 | Pending |
| API-01 | Phase 22 | Pending |
| API-02 | Phase 22 | Pending |
| API-03 | Phase 22 | Pending |
| API-04 | Phase 22 | Pending |
| API-05 | Phase 22 | Pending |
| API-06 | Phase 22 | Pending |
| TEST-01 | Phase 23 | Pending |
| TEST-02 | Phase 23 | Pending |
| TEST-03 | Phase 23 | Pending |
| TEST-04 | Phase 23 | Pending |
| TEST-05 | Phase 23 | Pending |
| DL-01 | Phase 24 | Pending |
| DL-02 | Phase 24 | Pending |
| DL-03 | Phase 24 | Pending |
| DL-04 | Phase 24 | Pending |
| DL-05 | Phase 24 | Pending |
| DL-06 | Phase 24 | Pending |
| SHIP-01 | Phase 25 | Pending |
| SHIP-02 | Phase 25 | Pending |
| SHIP-03 | Phase 25 | Pending |
| SHIP-04 | Phase 25 | Pending |
| SHIP-05 | Phase 25 | Pending |
| SHIP-06 | Phase 25 | Pending |

**Coverage:**
- v2.2 requirements: 31 total
- Mapped to phases: 31
- Unmapped: 0

---
*Requirements defined: 2026-04-04*
*Last updated: 2026-04-04 — traceability complete, all 31 requirements mapped to phases 21-25*
