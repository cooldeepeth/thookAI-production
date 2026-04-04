# Deferred Items — Phase 22

## Pre-existing Build Failure (Out of Scope)

**Discovered during:** 22-01 Task 2 verification
**Severity:** Pre-existing (existed before Phase 22 started)
**Issue:** `CI=false npm run build` fails with:
  - `Module not found: Error: Can't resolve '@/App'`
  - `Module not found: Error: Can't resolve '@/index.css'`

**Root cause:** `frontend/src/index.js` uses `import App from "@/App"` and `import "@/index.css"`. The `@` alias resolves to `src/` via craco.config.js, but the production webpack build is unable to resolve these paths in this build environment.

**Evidence it's pre-existing:** Confirmed by running `git stash` (removing our changes) and running the same build — same error appeared before any Phase 22 edits.

**Recommendation:** Fix in a separate plan. The development server (`npm start`) likely works fine. The production build path needs the craco alias to work consistently.
