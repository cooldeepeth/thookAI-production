# Wedge Audit Plan — 2026-04-21

## Scope (frozen)

**Backend routes** (10 files):
auth.py, auth_google.py, password_reset.py, onboarding.py, persona.py, content.py, platforms.py (LinkedIn endpoints only), billing.py, webhooks.py, dashboard.py (schedule endpoints only).

**Backend agents** (7 files):
commander.py, scout.py, thinker.py, writer.py, qc.py, anti_repetition.py, publisher.py.

**Backend services** (6 files):
llm_client.py, credits.py, stripe_service.py, subscriptions.py, vector_store.py, persona_refinement.py.

**Frontend pages**:
AuthPage.jsx, Onboarding/ (6 files), Dashboard/index.jsx, Dashboard/DashboardHome.jsx, Dashboard/ContentStudio/ (4 + Shells/3), Dashboard/Settings.jsx, Dashboard/Connections.jsx.

## Method

For each file:

1. Read source
2. Summarise in 1–2 sentences
3. Look for a matching test file in `backend/tests/` or `frontend/src/__tests__/`
4. Flag up to 3 top bugs/issues (correctness, security, failure-modes, dead code, unguarded inputs, silent failures)

## Out of scope

- All other files in `backend/routes/`, `backend/agents/`, `backend/services/`, `backend/middleware/`, frontend components, tests themselves, infra, etc.
- No fixes. Audit only.

## Output

- `.planning/audit/WEDGE-AUDIT.md` — the audit itself
- Commit: `docs(audit): add wedge path audit`

## Execution strategy

Batch reads in parallel where possible. Findings written directly into final doc as each section is read.
