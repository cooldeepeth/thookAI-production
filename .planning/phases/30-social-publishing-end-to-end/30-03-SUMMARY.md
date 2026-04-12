---
phase: 30-social-publishing-end-to-end
plan: "03"
subsystem: platforms-oauth
tags: [oauth, token-health, ui-warning, encryption, tdd, regression]
dependency_graph:
  requires: [30-01, 30-02]
  provides: [token_expiring_soon API field, Connections.jsx warning badge, Fernet round-trip proof]
  affects: [frontend/src/pages/Dashboard/Connections.jsx, backend/routes/platforms.py]
tech_stack:
  added: []
  patterns:
    - Proactive 24h token health field in REST status response
    - Yellow warning badge using design-system yellow-400 tokens
    - Fernet round-trip test pattern via monkeypatch on module-level ENCRYPTION_KEY
key_files:
  created: []
  modified:
    - backend/routes/platforms.py
    - backend/tests/test_platform_oauth.py
    - frontend/src/pages/Dashboard/Connections.jsx
decisions:
  - "token_expiring_soon defaults to False for all disconnected platforms — field always present to avoid frontend null checks"
  - "Warning badge only renders when token_expiring_soon=true AND needs_reconnect=false — expired tokens show orange 'Token Expired' badge instead"
  - "AlertCircle already imported in Connections.jsx — no new import needed"
  - "Fernet round-trip test uses monkeypatch.setattr on routes.platforms.ENCRYPTION_KEY (module-level var) to ensure cipher uses the test key"
metrics:
  duration: "~5 minutes"
  completed: "2026-04-12"
  tasks_completed: 2
  tasks_total: 3
  files_changed: 3
requirements_satisfied: [PUBL-01, PUBL-02, PUBL-03, PUBL-06, PUBL-07]
---

# Phase 30 Plan 03: Token Expiry Warning + Regression Guard Summary

**One-liner:** Added `token_expiring_soon` API field with yellow warning badge in Connections.jsx, verified via 4 new TDD tests (3 expiry-soon + 1 Fernet round-trip), and confirmed 54 total tests pass across publishing, OAuth, and analytics suites.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add token_expiring_soon to status endpoint + Fernet round-trip test | dc2904d | backend/routes/platforms.py, backend/tests/test_platform_oauth.py |
| 2 | Run full regression suite — OAuth, publish, and analytics tests | (no commit — verification only) | — |

## Checkpoint Reached

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 3 | Add expiring-soon warning to Connections.jsx + visual verification | 85ce4ec | frontend/src/pages/Dashboard/Connections.jsx |

**Status:** Checkpoint `human-verify` reached. Code implemented, awaiting human visual confirmation.

## Implementation Details

### Task 1 — token_expiring_soon API field (TDD)

**RED:** Wrote 4 failing tests in `TestTokenExpiringSoon` and `TestFernetEncryptionRoundTrip` classes before any implementation.

**GREEN:** Added `token_expiring_soon` field to `get_platforms_status` in `backend/routes/platforms.py`:
- Default platform dict now includes `"token_expiring_soon": False` for all 3 platforms
- In the connected-token loop: computes `is_expiring_soon = time_until_expiry < timedelta(hours=24)` (only when token is still valid)
- Field included in every connected platform dict

All 4 new tests pass:
- `TestTokenExpiringSoon::test_status_returns_expiring_soon_true_within_24h` — 10h expiry → True
- `TestTokenExpiringSoon::test_status_returns_expiring_soon_false_beyond_24h` — 48h expiry → False
- `TestTokenExpiringSoon::test_status_always_has_expiring_soon_field` — field present even when no tokens connected
- `TestFernetEncryptionRoundTrip::test_encrypt_decrypt_round_trip` — encrypt→decrypt recovers plaintext (PUBL-06)

### Task 2 — Regression Suite

Full run of `test_publishing.py + test_platform_oauth.py + test_analytics_social.py`:
- **Result: 54 passed, 0 failed**
- Plan 01's publish_results fix unblocks analytics polling (PUBL-07 confirmed)
- Plan 02's platforms.py changes did not break existing OAuth tests (PUBL-01/02/03 regression guard confirmed)
- Task 1's token_expiring_soon addition did not break status endpoint tests

### Task 3 — Connections.jsx Warning Badge (checkpoint)

Added yellow warning badge in the Connection Details section:
```jsx
{platform.token_expiring_soon && !platform.needs_reconnect && (
  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-yellow-400/10 text-yellow-400 border border-yellow-400/20">
    <AlertCircle size={12} />
    Expiring soon — reconnect to keep publishing
  </span>
)}
```
- `AlertCircle` already imported — no new dependency
- Only shows when token is expiring soon but not yet expired (orange "Token Expired" badge handles the expired state)
- Connection details div updated to `flex-wrap` to accommodate multiple badges gracefully

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — all fields are wired to real API data from `/api/platforms/status`.

## Self-Check

Files created/modified:
- [x] `backend/routes/platforms.py` — modified (token_expiring_soon added)
- [x] `backend/tests/test_platform_oauth.py` — modified (4 new tests added)
- [x] `frontend/src/pages/Dashboard/Connections.jsx` — modified (warning badge added)

Commits:
- [x] dc2904d — feat(30-03): add token_expiring_soon to platform status endpoint + Fernet round-trip test
- [x] 85ce4ec — feat(30-03): add expiring-soon warning badge to Connections.jsx

## Self-Check: PASSED
