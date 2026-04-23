# Open questions — resolved at weekly Office Hours

Format: `[Question] — [context] — [date raised]`

(Add as they come up. Resolve weekly. Log resolutions in DECISIONS.md.)

## Day 2 (2026-04-21)

- test_error_format.py::test_unauthenticated_analytics_returns_401_with_error_code now returns 404 (flag guard runs before auth). Does this test need updating to expect 404, or do we want auth to run first? — 2026-04-21

- Dangling route links exist in: Landing/DiscoverBanner.jsx, Landing/Navbar.jsx, DashboardHome.jsx, ContentLibrary.jsx, TemplateCard.jsx — they navigate into unregistered routes. Mop-up needed. When? — 2026-04-21

## Day 7 (2026-04-24)

- Eval baseline not yet generated. Harness is live (`backend/tests/evals/`) but `baseline.json` requires an operator run with a real `ANTHROPIC_API_KEY`: `cd backend && python -m tests.evals.runner --update-baseline`. Commit the result. Until then, CI runs the eval and archives the report artifact but cannot gate on regressions. — 2026-04-24

- `ANTHROPIC_API_KEY` must be added to GitHub repository secrets for the `.github/workflows/evals.yml` workflow to run on PRs. — 2026-04-24
