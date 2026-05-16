# ThookAI — Root Instructions for Claude Code

## Mission

ThookAI v1 helps non-native-English founders building in public generate LinkedIn posts in their authentic voice — so they build audience without hiring a ghostwriter or sounding like ChatGPT.

This is the ONLY thing we are shipping this quarter. Everything else is deferred.

## Current active wedge

- **Branch**: `wedge/linkedin-only`
- **Spec**: See `.planning/WEDGE.md`
- **Success criteria**: 10 paying users at $19/mo with stable weekly retention by end of Month 2.

## Stack (actual, not aspirational)

- Backend: FastAPI, Python 3.11, MongoDB (motor async), Celery + Redis
- Frontend: React 18, react-router-dom v6, Tailwind CSS, CRA+CRACO
- LLM: OpenAI, Anthropic, Google SDKs via `backend/services/llm_client.py`
- Storage: Cloudflare R2
- Payments: Stripe (currently sandbox; going live as part of wedge)
- Vector DB: Pinecone (persona embeddings)
- Deployed: Vercel (frontend), Railway (backend + Celery)
- Observability: Sentry, PostHog

## Anti-goals (DO NOT WORK ON)

- X/Twitter integration (OAuth stays, flag off)
- Instagram integration (OAuth stays, flag off)
- Video generation pipeline (Remotion, Runway, etc.)
- Voice generation pipeline (ElevenLabs, OpenAI TTS)
- Image generation for posts (DALL-E, FAL, Stable Diffusion)
- Carousel generation
- Template marketplace
- Campaign engine
- Agency workspace
- Repurpose agent
- Series planner
- Viral card / public persona cards
- New subscription tiers (single $19/mo during wedge)

If any of the above comes up, the answer is "deferred, see `.planning/DEFERRED.md`".

## Conventions

### Commits

- Conventional commits: `feat:`, `fix:`, `refactor:`, `test:`, `perf:`, `security:`, `chore:`
- Atomic: one logical change per commit
- Every commit must pass: typecheck, lint, and the three wedge Playwright tests

### Branches

- Main protected. All work in feature branches off `wedge/linkedin-only`.
- PR required for merge. No direct pushes.

### Testing gates (non-negotiable)

- The three Playwright tests in `e2e/wedge/` MUST pass before merge.
- The eval harness in `backend/tests/evals/` MUST pass before merge to wedge branch.
- Sentry unresolved errors older than 48h block all feature work.

### Documentation

- Any non-trivial decision gets an entry in `.planning/DECISIONS.md`.
- Any feature deferred gets an entry in `.planning/DEFERRED.md` with reason.

## Key paths

- Backend entry: `backend/server.py`
- Frontend entry: `frontend/src/App.js`
- Feature flags: `backend/config.py` (`FEATURES_ENABLED`) + `frontend/src/lib/features.js`
- Wedge spec: `.planning/WEDGE.md`
- Decisions log: `.planning/DECISIONS.md`
- Deferred list: `.planning/DEFERRED.md`

## Rules for Claude Code when working in this repo

1. **Never add a feature without citing a specific paying-user request or failed conversion reason.** If no such citation exists, propose adding to `.planning/DEFERRED.md` instead of building.
2. **Never edit disabled code paths.** If a route is flagged off in `FEATURES_ENABLED`, do not touch its implementation — even if you see bugs.
3. **Audit before fixing.** When asked to fix something, first read the relevant files, report what you found, and propose the smallest possible fix. Wait for approval before implementing unless the user says "proceed autonomously".
4. **Test every change.** Run the three wedge Playwright tests and the eval harness after every non-trivial change. Report results.
5. **Atomic commits.** Never batch unrelated changes.
6. **Stop on error budget exceeded.** If Sentry shows a new unresolved error caused by your change, revert immediately and report.
7. **Office Hours only for decisions.** If a decision is needed (architecture, UX, scope), log it in `.planning/OPEN-QUESTIONS.md` for weekly Office Hours. Do not decide autonomously on anything outside the wedge spec.

## Preferred tools

- `gstack /autoplan` — for multi-step work that spans several files
- `gstack /qa` — before any PR
- `gstack /design-review` — when touching frontend/auth, onboarding, content studio
- `gstack /ship` and `/land-and-deploy` — for releases
- `graphify /graphify` query — when exploring unfamiliar code paths
- `claude-mem` — runs automatically, don't invoke

## Office Hours

- Once a week, Sunday evening Sydney time.
- All open questions from `.planning/OPEN-QUESTIONS.md` resolved here.
- No decisions outside Office Hours.

## When in doubt

Re-read `.planning/WEDGE.md`. If the work isn't on the wedge, it doesn't get done.
