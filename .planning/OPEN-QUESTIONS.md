# Open questions — resolved at weekly Office Hours

Format: `[Question] — [context] — [date raised]`

(Add as they come up. Resolve weekly. Log resolutions in DECISIONS.md.)

## Day 2 (2026-04-21)

- test_error_format.py::test_unauthenticated_analytics_returns_401_with_error_code now returns 404 (flag guard runs before auth). Does this test need updating to expect 404, or do we want auth to run first? — 2026-04-21

- Dangling route links exist in: Landing/DiscoverBanner.jsx, Landing/Navbar.jsx, DashboardHome.jsx, ContentLibrary.jsx, TemplateCard.jsx — they navigate into unregistered routes. Mop-up needed. When? — 2026-04-21
