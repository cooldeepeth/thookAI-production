---
phase: 24-content-download-redirect-to-platform
plan: "01"
subsystem: frontend/content-studio
tags: [download, export, redirect, content-actions, platform-compose]
dependency_graph:
  requires: []
  provides: [content-download, platform-redirect, export-actions-bar]
  affects: [frontend/src/pages/Dashboard/ContentStudio/ContentOutput.jsx]
tech_stack:
  added: [jszip ^3.10.1]
  patterns: [pure-utility-module, conditional-button-rendering, blob-download, platform-compose-urls]
key_files:
  created:
    - frontend/src/lib/contentExport.js
    - frontend/src/pages/Dashboard/ContentStudio/ExportActionsBar.jsx
  modified:
    - frontend/package.json
    - frontend/src/pages/Dashboard/ContentStudio/ContentOutput.jsx
decisions:
  - Used URLSearchParams to build LinkedIn and X URLs — avoids manual encoding bugs and is more readable
  - Carousel detection uses carousel?.generated === true && carousel?.slides?.length > 0 — matches the job shape documented in CLAUDE.md
  - Single image download uses anchor with download attribute rather than fetch+blob — avoids CORS issues with R2 URLs that already have public access
  - downloadImages fetches carousel slides with Promise.all for concurrency — faster than sequential for multi-slide carousels
  - ExportActionsBar is always rendered when bodyText exists (not just for approved jobs) so draft content can also be exported
metrics:
  duration_minutes: 12
  completed_date: "2026-04-03T21:45:26Z"
  tasks_completed: 3
  tasks_total: 3
  files_created: 2
  files_modified: 2
---

# Phase 24 Plan 01: Content Download & Platform Redirect Summary

**One-liner:** Client-side export actions — .txt download, image/zip download, LinkedIn/X compose redirect, and Instagram copy-paste tooltip — wired into ContentStudio via new contentExport.js utility and ExportActionsBar component.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Install JSZip + create contentExport.js | 46c4cfc | frontend/package.json, frontend/src/lib/contentExport.js |
| 2 | Create ExportActionsBar component | cc5d054 | frontend/src/pages/Dashboard/ContentStudio/ExportActionsBar.jsx |
| 3 | Wire ExportActionsBar into ContentOutput | a0ac336 | frontend/src/pages/Dashboard/ContentStudio/ContentOutput.jsx |

## What Was Built

### contentExport.js (`frontend/src/lib/contentExport.js`)
Pure utility module with 4 named exports — no default export, no side effects, no backend calls:

- **`downloadTextFile(text, platform, date)`** — Creates a `text/plain` Blob and triggers a browser download named `{platform}-{YYYY-MM-DD}.txt`. Uses `URL.createObjectURL` + revoke for memory safety.
- **`buildLinkedInUrl(text)`** — Returns `https://www.linkedin.com/shareArticle?mini=true&summary=...` using `URLSearchParams` for safe encoding.
- **`buildXUrl(text)`** — Returns `https://twitter.com/intent/tweet?text=...` with 280-char truncation (slice to 277 + "..." if over limit).
- **`downloadImages(mediaAssets, carousel, jobId)`** — Async. Detects carousel via `carousel?.generated && slides?.length > 0`. Single image: anchor download. Carousel: fetches all slides with `Promise.all`, builds JSZip archive, triggers `carousel-{jobId}.zip` download. Throws on error (never silent-swallow) so ExportActionsBar can display the error message.

### ExportActionsBar component (`frontend/src/pages/Dashboard/ContentStudio/ExportActionsBar.jsx`)
React component rendering all download and redirect buttons with `data-testid="export-actions-bar"`:

- **Download .txt** — Always shown when content exists. Calls `downloadTextFile`.
- **Download Image / Download .zip** — Shown only when `media_assets.length > 0` or carousel is generated. Shows `Loader2` spinner while zip is in flight. Sets `downloadError` state on failure.
- **Open in LinkedIn** — Only for `platform === 'linkedin'`. Opens `buildLinkedInUrl` result in new tab with `noopener,noreferrer`.
- **Open in X** — Only for `platform === 'x'`. Opens `buildXUrl` result in new tab.
- **Post to Instagram** — Only for `platform === 'instagram'`. Toggles inline tooltip explaining the copy-paste workflow. No broken link, no dead button.

### ContentOutput.jsx wiring
Two targeted edits:
1. Added `import { ExportActionsBar } from './ExportActionsBar';` after the existing `apiFetch` import.
2. Inserted `{bodyText && <ExportActionsBar job={job} contentText={bodyText} />}` immediately before the PublishPanel block so export actions appear above the publish controls.

## Success Criteria Met

- [x] DL-01: `downloadTextFile()` creates a .txt blob download with platform+date filename
- [x] DL-02: `downloadImages()` downloads single image via anchor or fetches+zips carousel slides with JSZip
- [x] DL-03: `buildLinkedInUrl()` returns `linkedin.com/shareArticle?mini=true&summary=...` URL; ExportActionsBar opens it in new tab for linkedin platform jobs
- [x] DL-04: `buildXUrl()` returns `twitter.com/intent/tweet?text=...` with 280-char truncation; ExportActionsBar opens it in new tab for x platform jobs
- [x] DL-05: Instagram platform shows info button that toggles an inline tooltip explaining copy-paste workflow — no broken link
- [x] DL-06: ExportActionsBar renders before PublishPanel in ContentOutput — visible alongside the Publish button on the same content detail view
- [x] Build: `CI=false npm run build` exits 0 with no compilation errors

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

None. All export functions perform real operations (Blob creation, fetch, JSZip). Platform URLs use the official LinkedIn shareArticle and Twitter intent endpoints. No hardcoded empty values flow to UI rendering.

## Self-Check: PASSED

Files created:
- frontend/src/lib/contentExport.js — FOUND
- frontend/src/pages/Dashboard/ContentStudio/ExportActionsBar.jsx — FOUND

Files modified:
- frontend/src/pages/Dashboard/ContentStudio/ContentOutput.jsx — FOUND (ExportActionsBar import + render verified)
- frontend/package.json — FOUND (jszip ^3.10.1 present)

Commits:
- 46c4cfc — FOUND
- cc5d054 — FOUND
- a0ac336 — FOUND

Build: Passed with zero errors.
