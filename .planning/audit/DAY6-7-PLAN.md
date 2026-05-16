# Day 6–7 plan

## Scope check

| Block                                     | Steps   | Est. effort                                         | This session? |
| ----------------------------------------- | ------- | --------------------------------------------------- | ------------- |
| Day 6 billing simplification              | 6.1–6.5 | ~1–2 h                                              | ✅ yes        |
| Day 7 eval harness — seeds + judge prompt | 7.1     | ~1 h                                                | ⏸ defer       |
| Day 7 eval runner                         | 7.2     | ~2 h                                                | ⏸ defer       |
| Day 7 workflow + baseline run             | 7.3–7.4 | ~0.5 h write + 20–40 min runtime + Anthropic tokens | ⏸ defer       |
| Day 7 design review + top-5 fixes         | 7.6     | ~2+ h                                               | ⏸ defer       |

**Context budget decision**: this session is at ~79% usage. Day 6 fits cleanly in the remaining 34%; Day 7 does not. Executing Day 6 end-to-end here, handing off Day 7 to a fresh session.

## Day 6 execution order

1. Add `POST /api/billing/wedge/checkout` in `backend/routes/billing.py`. Hard-coded $19/500. Uses the existing dynamic-pricing pattern, no fixed Price ID.
2. Add `feature_credit_topups: false` to both `backend/config.py:FEATURES_ENABLED` and `frontend/src/lib/features.js`.
3. Simplify `Dashboard/Settings.jsx → BillingTab`: replace `PlanBuilder` with a single fixed-price card + Subscribe button that calls the wedge checkout endpoint; hide one-time credit packages behind `feature_credit_topups`.
4. Run the 3 wedge Playwright tests. If green, commit as one atomic change. Commit message: `refactor(billing): simplify to single wedge tier at $19/mo 500 credits`.
5. Manual smoke check (report-only): hit `POST /api/billing/wedge/checkout` with a test user token, confirm a Stripe checkout URL comes back. Do NOT pay.
6. Push.

## Day 6 explicit non-goals

- No live-mode key flip (Stripe live-mode is the user's manual Railway step).
- Don't delete `PlanBuilder.jsx`; just stop rendering it.
- Don't change the existing `POST /api/billing/plan/*` endpoints — wedge endpoint is additive.

## Day 7 (next session — handoff)

Pick up from `.planning/audit/DAY6-7-PLAN.md` §7 and work through 7.1 → 7.7. Keep a single commit per logical unit.
