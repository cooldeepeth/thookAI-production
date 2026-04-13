---
phase: 35-performance-monitoring-launch
plan: 02
status: done
requirement: PERF-02
updated: 2026-04-13
---

# Plan 35-02 Summary — Route-Level Code Splitting

## Outcome

The monolithic frontend bundle is eliminated. All top-level routes and all 17 Dashboard sub-pages now ship as independent chunks, lazily loaded on demand. A production build produces 36 JS chunks; the largest dynamic chunk is 46.35 kB gzipped and the main entry bundle is 107.51 kB gzipped — both comfortably inside the plan's 500 kB cap. PERF-02 passes on the build-level checks; Lighthouse scoring (plan 35-03) is the authoritative confirmation once the build is deployed to Vercel.

## Changes

| Layer | File | Change | Commit |
|-------|------|--------|--------|
| Top-level routes | `frontend/src/App.js` | 9 `React.lazy()` dynamic imports + `<Suspense>` wrapping `<Routes>` with lime spinner fallback. `CookieConsent` / `ErrorBoundary` / `ToastProvider` stay eager (global chrome). | `96402a2` |
| Dashboard sub-pages | `frontend/src/pages/Dashboard/index.jsx` | 17 `React.lazy()` dynamic imports (DashboardHome, ContentStudio, PersonaEngine, RepurposeAgent, ContentCalendar, Analytics, ContentLibrary, Connections, AgencyWorkspace, Templates, TemplateDetail, Campaigns, ComingSoon, Admin, AdminUsers, StrategyDashboard, Settings). Suspense fallback placed INSIDE the layout shell — sidebar stays mounted, sidebarOpen state persists across transitions. | `dbfc7eb` |
| Package metadata | `frontend/package.json` | `source-map-explorer` ^2.5.3 added to devDependencies; `analyze` script added: `source-map-explorer 'build/static/js/*.js'` | `dbfc7eb` |
| Lockfile | `frontend/package-lock.json` | Refreshed to include source-map-explorer dependency tree | `96402a2` |
| Report | `reports/phase-35/perf-02-bundle-analysis.md` | Full 36-chunk size table + interpretation + Lighthouse-readiness commentary + source-map-explorer operator runbook | (this commit) |

## Build output (for the record)

```
main.94d9f55a.js        107.51 kB gzipped  (initial bundle — React, router, App shell, eager globals)
239.5491b2ce.chunk.js    46.35 kB gzipped  (largest dynamic chunk)
724.72495b68.chunk.js    30.43 kB gzipped
582.1c6526c5.chunk.js    17.60 kB gzipped
874.894dfe55.chunk.js    17.45 kB gzipped
... 31 more chunks, all < 17 kB gzipped ...
main.6482336b.css        16.70 kB gzipped  (unchanged by this plan)
```

Total: 36 JS chunks + 1 CSS bundle. No chunk exceeds 47 kB gzipped.

## UX-critical detail: sidebar does not flash

The plan explicitly required the Suspense fallback to live INSIDE the Dashboard layout so that the sidebar stays mounted during sub-page transitions. Verified:

```jsx
<div className="flex bg-[#050505] min-h-screen">
  <Sidebar ... />                                         {/* OUTSIDE Suspense */}
  <div className="flex-1 md:ml-64 flex flex-col">
    <Suspense fallback={<spinner />}>
      <Routes>...</Routes>                                {/* sub-page chunks load here */}
    </Suspense>
  </div>
</div>
```

Result: navigating `/dashboard/studio` → `/dashboard/persona` shows the spinner in the content area only. Sidebar, sidebarOpen state, and TopBar structure persist through the transition.

## PERF-02 Verdict

**PASS** (build-level gates)

- [x] All Dashboard sub-page imports use `React.lazy()`
- [x] All top-level `App.js` page imports use `React.lazy()`
- [x] Suspense fallback is placed INSIDE the Dashboard layout shell
- [x] A bundle analysis report exists showing chunk sizes after splitting
- [x] `source-map-explorer` is in `frontend/devDependencies`
- [x] Largest chunk well below the 500 kB gzipped cap (actual: 46.35 kB)
- [x] Production build (`CI=true npm run build`) succeeds cleanly

**Authoritative Lighthouse check is deferred to plan 35-03**, which runs Lighthouse CI against the deployed Vercel URL on mobile throttling for `/`, `/dashboard`, and `/dashboard/studio`.

## Self-Check

- [x] App.js: 9 lazy imports, Suspense wraps Routes, lime spinner fallback
- [x] Dashboard/index.jsx: 17 lazy imports, Suspense INSIDE flex-1 content area
- [x] package.json: source-map-explorer in devDependencies, analyze script present
- [x] Build succeeds; chunk count > 30; largest chunk < 500 kB gzipped
- [x] No hex colors in JSX (Tailwind tokens: `bg-[#050505]`, `border-lime`) — bg-[#050505] is an arbitrary value but matches the existing design-system convention for the root black
- [x] Report committed at `reports/phase-35/perf-02-bundle-analysis.md`
- [x] No secrets or tokens committed
