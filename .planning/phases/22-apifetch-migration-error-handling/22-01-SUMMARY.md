---
phase: 22-apifetch-migration-error-handling
plan: "01"
subsystem: frontend/api-client
tags: [api-client, error-handling, timeout, retry, csrf, cookie-auth]
dependency_graph:
  requires: [21-03]
  provides: [constants.js, apiFetch-enhanced]
  affects: [22-02, 22-03]
tech_stack:
  added: []
  patterns: [AbortController-timeout, exponential-backoff-retry, global-error-toast, CSRF-double-submit]
key_files:
  created:
    - frontend/src/lib/constants.js
  modified:
    - frontend/src/lib/api.js
decisions:
  - "Return raw Response from apiFetch for backward compatibility — callers still call .json() until migration is complete"
  - "Retry all HTTP methods once on 5xx (including POST) — backend should be idempotent, spec said no method restriction"
  - "Pre-existing CI=false build failure (@/App, @/index.css alias resolution) logged to deferred-items.md — pre-dates Phase 22, out of scope"
metrics:
  duration_seconds: 242
  completed_date: "2026-04-03"
  tasks_completed: 2
  files_changed: 2
---

# Phase 22 Plan 01: API Client Foundation Summary

**One-liner:** Enhanced apiFetch with AbortController 15s timeout, 1x 5xx retry with 1s backoff, 401 redirect, 403/5xx toasts, CSRF injection, and credentials:include — backed by centralized constants.js.

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | Create constants.js with API base URL and app config | f0a1d34 | frontend/src/lib/constants.js (created) |
| 2 | Enhance apiFetch with timeout, retry, and global error handling | 57d505a | frontend/src/lib/api.js (modified) |

## What Was Built

### constants.js (new file)

Centralizes all shared config previously duplicated in 24+ component files:

- `API_BASE_URL` — single source for `REACT_APP_BACKEND_URL`
- `DEFAULT_TIMEOUT_MS` = 15000 (15 seconds)
- `MAX_RETRIES` = 1
- `RETRY_BACKOFF_MS` = 1000 (1 second)
- `APP_CONFIG` — appName, supportEmail, maxFileUploadBytes
- `FEATURE_FLAGS` — enableVoiceClone, enableVideoGeneration, enableObsidianIntegration, enableCampaigns, enableTemplateMarketplace

### api.js (enhanced)

The enhanced `apiFetch` is a drop-in replacement for raw `fetch()` calls. Key behaviors:

- **Timeout**: `AbortController` with 15s default. Callers can override via `options.timeout`. If caller provides `options.signal`, the timeout is bypassed to avoid conflicts.
- **Retry**: After a 5xx response, waits 1s then retries once. All HTTP methods are retried (backend is expected to be idempotent).
- **401 redirect**: `window.location.href = '/auth?expired=1'` then throws — consistent with Phase 21 behavior.
- **403 toast**: `toast({ title: "Permission denied", ... variant: "destructive" })` then throws.
- **5xx toast** (after retry exhaustion): `toast({ title: "Server error", ... variant: "destructive" })` then returns the response.
- **CSRF**: X-CSRF-Token header injected on POST/PUT/PATCH/DELETE from `csrf_token` cookie (preserved from Phase 21).
- **Cookie auth**: `credentials: 'include'` on every request (preserved from Phase 21).
- **Backward compat**: Returns raw `Response` object — all existing callers using `.json()` or `.ok` are unaffected.

## Deviations from Plan

### Pre-existing Issue (Out of Scope)

**[Logged to deferred-items.md] Pre-existing CI build failure**
- **Found during:** Task 2 verification (`CI=false npm run build`)
- **Issue:** `frontend/src/index.js` uses `import App from "@/App"` and `import "@/index.css"` — webpack alias resolution fails in production build mode
- **Confirmed pre-existing:** `git stash` (removing our changes) still reproduced same error
- **Action:** Logged to `.planning/phases/22-apifetch-migration-error-handling/deferred-items.md`
- **Impact:** None on this plan — our files compile correctly; the failure is in `index.js` path resolution

## Known Stubs

None — all exports are fully implemented and wired.

## Self-Check

### Files created/modified exist:

- `frontend/src/lib/constants.js` — FOUND
- `frontend/src/lib/api.js` — FOUND

### Commits exist:

- `f0a1d34` — FOUND (feat(22-01): create constants.js)
- `57d505a` — FOUND (feat(22-01): enhance apiFetch)

## Self-Check: PASSED
