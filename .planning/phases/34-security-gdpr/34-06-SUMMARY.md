---
phase: 34-security-gdpr
plan: 06
status: complete
retroactive: true
commit: a92dcd9
requirements:
  - SECR-09
  - SECR-10
---

# Plan 34-06: Settings Data Tab — GDPR Export + Account Deletion UI — SUMMARY

> Retroactive summary reconstructed from `.planning/phases/34-security-gdpr/34-VERIFICATION.md` and commit `a92dcd9` (`feat(34-06): add Settings Data tab with GDPR export and account deletion UI`).

## Files Modified
- `frontend/src/pages/Dashboard/Settings.jsx`

## Changes — Settings.jsx Data tab

New "Data" tab added alongside the existing Profile, Billing, Connections, and Notifications tabs (all preserved from Phase 32 plan 32-03).

### Export Your Data section
- Description text explaining the export scope (500 items per collection).
- Primary button `data-testid="export-data-btn"` labelled "Export My Data" / "Exporting…" during load.
- `handleExport()` calls `apiFetch('/api/auth/export')` via the centralized apiFetch client (cookie auth + CSRF).
- Response JSON is serialized into a `Blob`, wrapped in an object URL, downloaded via a programmatically-created `<a>` click with `download="thookai-export-{Date.now()}.json"`.
- Toast on success: "Export complete — Your data has been downloaded."
- Toast on 429: "Export limit reached (3 per day). Try again tomorrow." (surfaces the per-user rate limit added in 34-05).
- Toast on other errors: destructive variant with the error message.

### Delete Account section
- Red-bordered card with danger styling.
- Input `data-testid="delete-confirm-input"` — user must type literal `DELETE`.
- Button `data-testid="delete-account-btn"` — disabled unless `deleteConfirm === 'DELETE'`.
- `handleDelete()` calls `apiFetch('/api/auth/delete-account', { method: 'POST', body: JSON.stringify({ confirm: 'DELETE' }) })`.
- Two-layer confirmation: frontend input match AND backend `confirm` field match.
- Success path: destructive toast, then `setTimeout(() => navigate('/'), 2000)`.

### Tab trigger
```jsx
<TabsTrigger value="data" data-testid="tab-data">Data</TabsTrigger>
<TabsContent value="data">
  <DataTab user={user} />
</TabsContent>
```

Design system: uses `card-thook`, `btn-primary`, `btn-danger`, `bg-surface-2`, `border-border-subtle`, `text-lime`, `font-display` — all established tokens from Phase 33.

## Verification
```
$ grep -c "tab-data\|export-data-btn\|delete-confirm-input\|delete-account-btn" frontend/src/pages/Dashboard/Settings.jsx
4

$ grep -n "auth/export\|auth/delete-account" frontend/src/pages/Dashboard/Settings.jsx
(2 lines — both apiFetch calls wired)

$ wc -l frontend/src/pages/Dashboard/Settings.jsx
(< 800 lines — under CLAUDE.md file-size ceiling)

$ cd frontend && npm run build
(PASS — Phase 32 and Phase 33 classes still resolve)
```

## Requirements Satisfied
- **SECR-09** — GDPR export UI wired to `/api/auth/export`: PASS
- **SECR-10** — GDPR delete UI wired to `/api/auth/delete-account` with double-confirmation: PASS

## Notes
- All four data-testids are greppable for future E2E coverage.
- Existing Profile/Billing/Connections/Notifications tabs from 32-03 preserved unchanged.
- `useNavigate` from `react-router-dom` imported to handle post-deletion redirect.
- Inline execution by orchestrator.
