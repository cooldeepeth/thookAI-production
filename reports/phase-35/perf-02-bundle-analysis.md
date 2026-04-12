---
report: perf-02-bundle-analysis
phase: 35
plan: 35-02
requirement: PERF-02
status: passed
---

# PERF-02: Bundle Analysis After Code Splitting

**Generated:** 2026-04-13
**Build command:** `CI=true GENERATE_SOURCEMAP=true npm run build` (in `frontend/`)
**Result:** **PASS** — all chunks well under the 500 kB cap, largest initial payload dominated by `main.js` at 107.51 kB gzipped.

## Summary

| Metric | Before 35-02 | After 35-02 | Cap | Status |
|--------|--------------|-------------|-----|--------|
| Initial JS (gzipped) | single monolith | `main.94d9f55a.js` = 107.51 kB | 500 kB | PASS |
| Largest chunk (gzipped) | single monolith | `239.5491b2ce.chunk.js` = 46.35 kB | 500 kB | PASS |
| JS chunk count | 1 | 36 | — | split successful |
| CSS (gzipped) | 16.7 kB | 16.7 kB | — | unchanged |

Raw (uncompressed) numbers for the top 5 chunks, for comparison with gzipped sizes — the gzip ratio is ~3× on these assets:

| File | Raw bytes | ≈ Raw KB | Gzipped |
|------|-----------|----------|---------|
| `main.94d9f55a.js` | 335,122 | 327.3 KB | 107.51 kB |
| `239.5491b2ce.chunk.js` | 202,917 | 198.2 KB | 46.35 kB |
| `724.72495b68.chunk.js` | 104,368 | 101.9 KB | 30.43 kB |
| `582.1c6526c5.chunk.js` | 70,992 | 69.3 KB | 17.6 kB |
| `874.894dfe55.chunk.js` | 50,482 | 49.3 KB | 17.45 kB |

## Chunk size distribution (gzipped)

```
107.51 kB  build/static/js/main.94d9f55a.js         ← initial bundle
 46.35 kB  build/static/js/239.5491b2ce.chunk.js    ← largest dynamic chunk
 30.43 kB  build/static/js/724.72495b68.chunk.js
 17.60 kB  build/static/js/582.1c6526c5.chunk.js
 17.45 kB  build/static/js/874.894dfe55.chunk.js
 16.70 kB  build/static/css/main.6482336b.css
 10.81 kB  build/static/js/871.813bf4ac.chunk.js
 10.22 kB  build/static/js/124.0f382e19.chunk.js
  9.51 kB  build/static/js/706.26501356.chunk.js
  9.48 kB  build/static/js/653.591a2cc9.chunk.js
  8.80 kB  build/static/js/259.6097b5b6.chunk.js
  8.26 kB  build/static/js/312.f277334d.chunk.js
  7.27 kB  build/static/js/681.06e6345c.chunk.js
  7.15 kB  build/static/js/13.667f9825.chunk.js
  6.96 kB  build/static/js/535.9db08b34.chunk.js
  6.71 kB  build/static/js/86.091812b7.chunk.js
  6.26 kB  build/static/js/548.7a63046e.chunk.js
  6.24 kB  build/static/js/767.138b445b.chunk.js
  5.79 kB  build/static/js/542.9180dbc3.chunk.js
  5.46 kB  build/static/js/468.23c5845a.chunk.js
  5.43 kB  build/static/js/934.902303df.chunk.js
  5.36 kB  build/static/js/560.b35105b8.chunk.js
  5.18 kB  build/static/js/53.637cd7c5.chunk.js
  4.96 kB  build/static/js/110.76aff739.chunk.js
  4.53 kB  build/static/js/957.6d8cca5c.chunk.js
  4.48 kB  build/static/js/364.2c5a28c9.chunk.js
  3.83 kB  build/static/js/938.9d4b1702.chunk.js
  3.81 kB  build/static/js/498.99ddc87d.chunk.js
  3.29 kB  build/static/js/806.6eb5b11b.chunk.js
  3.26 kB  build/static/js/147.83a6f3aa.chunk.js
  3.09 kB  build/static/js/813.8111e99d.chunk.js
  3.00 kB  build/static/js/592.677d4082.chunk.js
  1.96 kB  build/static/js/51.e54c4ad5.chunk.js
  1.91 kB  build/static/js/134.e3260457.chunk.js
  1.53 kB  build/static/js/705.f9b4e23a.chunk.js
  1.39 kB  build/static/js/898.4f4c23ce.chunk.js
  584  B   build/static/js/250.6b2ada46.chunk.js
```

## What the split achieves

**Before (implied baseline):** A monolithic `main.js` carrying every route, every Dashboard sub-page, every vendor library, every Radix UI primitive. Any visit to `/` or `/auth` paid the full cost of `ContentStudio`, `StrategyDashboard`, `Campaigns`, and `Analytics` — pages the user may never open.

**After:** 36 independent JS chunks. The browser fetches only what the current route needs:

- **Any first visit** pays `main.94d9f55a.js` (107.51 kB gzipped) — contains React runtime, router, auth context, top-level App shell, and the eagerly-imported `CookieConsent` / `ErrorBoundary` / `ToastProvider` primitives.
- **Landing `/`** additionally fetches only the `LandingPage` chunk and its section components (lazy-loaded in Phase 33's split).
- **Dashboard first-hit** additionally fetches the Dashboard shell chunk, then the chosen sub-page chunk (DashboardHome, ContentStudio, PersonaEngine, etc. — each a separate chunk from the 36).
- **Sub-page navigation** fetches only the next sub-page chunk. The sidebar stays mounted — no full reload, no sidebar flash (see "Suspense placement" below).

**Lighthouse 90+ readiness (qualitative):** The initial transfer is bounded by `main.94d9f55a.js` (107.51 kB) + CSS (16.7 kB) ≈ **124 kB gzipped** for a first landing-page visit, plus the landing page's own chunk. This is comfortably inside the Lighthouse "Avoid enormous network payloads" budget (1.8 MB raw / ~500 kB gzipped) and well below the plan's 500 kB chunk cap for any individual chunk. First Contentful Paint and Largest Contentful Paint should improve proportionally to the payload reduction. Actual Lighthouse scores are validated in plan **35-03** against the deployed Vercel build.

## Suspense placement — sidebar does not flash

The plan called out a specific UX constraint: the Suspense fallback must be **inside** the Dashboard layout so the sidebar never flashes during sub-page transitions. Verified in `frontend/src/pages/Dashboard/index.jsx`:

```jsx
<div className="flex bg-[#050505] min-h-screen">
  <Sidebar ... />                                         {/* OUTSIDE Suspense — stays mounted */}
  <div className="flex-1 md:ml-64 flex flex-col min-h-screen">
    <Suspense fallback={<spinner />}>                     {/* INSIDE layout shell */}
      <Routes>
        <Route path="/" element={<><TopBar /><DashboardHome /></>} />
        ... 16 more sub-pages ...
      </Routes>
    </Suspense>
  </div>
</div>
```

Navigating between `/dashboard/studio` → `/dashboard/persona` shows the spinner in the content area only — the sidebar stays mounted, `useState(sidebarOpen)` stays alive, and the user's open/closed preference persists through the transition.

`App.js` uses a different placement: the Suspense wraps the entire `<Routes>` block, with a full-screen lime spinner fallback. This is correct because top-level routes are mutually exclusive — transitioning from `/` to `/auth` is effectively a page replacement, no shared shell to preserve.

## source-map-explorer integration

`package.json` now includes:

```json
"devDependencies": {
  "source-map-explorer": "^2.5.3",
  ...
},
"scripts": {
  "build": "craco build",
  "analyze": "source-map-explorer 'build/static/js/*.js'",
  ...
}
```

To drill into a specific chunk's composition:

```bash
cd frontend
npm run build                   # produce build/static/js/*.js + *.js.map
npm run analyze                 # opens interactive treemap in browser
```

This is the recommended workflow for any future chunk-size regression — the analyze script lets an operator click through a chunk to see exactly which packages (e.g. `@radix-ui/*`, `framer-motion`, etc.) are contributing to its size.

## Verdict

**PERF-02: PASS**

- [x] Top-level `App.js` routes use React.lazy() with Suspense fallback
- [x] `Dashboard/index.jsx` sub-pages (17 of them) use React.lazy() with Suspense fallback INSIDE the layout shell — sidebar does not flash
- [x] 36 JS chunks produced; largest individual chunk (46.35 kB gzipped) is well under the 500 kB cap
- [x] Initial payload (`main.js` at 107.51 kB gzipped) is bounded and does not carry Dashboard sub-page code
- [x] `source-map-explorer` is installed and `npm run analyze` is available for future regression triage
- [x] Production build succeeds (`Compiled successfully`)

## Next gate (plan 35-03)

Run Lighthouse CI against the deployed Vercel URL for the three required pages (`/`, `/dashboard`, `/dashboard/studio`) and confirm Performance ≥ 90 on each. Local build numbers predict a PASS but the authoritative check is on the production domain, on mobile throttling, measured by Lighthouse.
