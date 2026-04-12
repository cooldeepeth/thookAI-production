---
phase: 33-design-system-landing-page
plan: 03
status: complete
---

# Plan 33-03: Extract PlanBuilder Shared Component — SUMMARY

## Files Created
- `frontend/src/components/PlanBuilder.jsx` (154 lines, exports `PlanBuilder`)

## Files Modified
- `frontend/src/pages/Dashboard/Settings.jsx` (881 → 712 lines, -169 net lines after extraction)

## PlanBuilder Component API
```jsx
<PlanBuilder
  mode="landing" | "settings"
  onCheckout={(planUsage) => ...}     // settings mode only
  subscription={subscription}           // settings mode only — controls "Update vs Customize" CTA label
  upgrading={upgrading}                 // settings mode only — disables CTA during checkout
/>
```

- `mode="landing"` → CTA reads "Get Started Free" and navigates to `/auth`. data-testid `plan-builder-cta`.
- `mode="settings"` → CTA reads "Update My Plan" or "Customize My Plan" depending on `subscription?.tier`. data-testid `plan-builder-checkout`. Calls `onCheckout(planUsage)` with the current usage object.

Internal state (all local to PlanBuilder, not leaked):
- `planUsage` — slider values keyed by feature
- `planPreview` — last result from POST `/api/billing/plan/preview`
- `previewLoading` — pending state for the preview fetch

`fetchPlanPreview` is debounced 400ms via the same `useEffect` pattern that lived in Settings.jsx pre-extraction. Endpoint `/api/billing/plan/preview` is confirmed public (no auth) — works for unauthenticated landing-page visitors.

Component uses shadcn `Slider` (already installed), `apiFetch`, and `useNavigate`. Total 154 lines, well under the 200-line plan cap.

## Settings.jsx Refactor
Removed:
- `PLAN_BUILDER_DEFAULTS` constant
- `PLAN_BUILDER_LABELS` constant
- `planUsage` / `planPreview` / `previewLoading` state
- `fetchPlanPreview` async function
- Debounced `useEffect` for plan preview
- ~120 lines of slider rendering JSX (Card → sliders, Card → price summary)
- All references to `setPlanUsage`, `setPlanPreview`, `setPreviewLoading`

Added:
- `import { PlanBuilder } from "@/components/PlanBuilder";`
- `<PlanBuilder mode="settings" onCheckout={handlePlanCheckout} subscription={subscription} upgrading={upgrading} />` in the BillingTab JSX where the slider Card grid used to be.

`handlePlanCheckout` signature changed from no-arg to `async (planUsage) => { ... }` so the PlanBuilder component can pass the current usage when the user clicks Customize.

Untouched in BillingTab (intentionally — these are settings-specific):
- Subscription status display (tier badge, credit balance)
- Buy Credits modal
- Manage Billing portal button
- Tier upgrade buttons (`handleUpgrade`)
- Loading + error states for the billing data fetch
- TIER_GRADIENTS (with the `to-violet/20` Plan 33-02 fix preserved)

## Acceptance Criteria — Verification
```
$ grep "PLAN_BUILDER_DEFAULTS\|PLAN_BUILDER_LABELS\|fetchPlanPreview" frontend/src/pages/Dashboard/Settings.jsx
(no matches)

$ grep -c "PlanBuilder" frontend/src/pages/Dashboard/Settings.jsx
2

$ wc -l frontend/src/pages/Dashboard/Settings.jsx
712 frontend/src/pages/Dashboard/Settings.jsx

$ wc -l frontend/src/components/PlanBuilder.jsx
154 frontend/src/components/PlanBuilder.jsx

$ node -e "@babel/parser parse" frontend/src/components/PlanBuilder.jsx → OK
$ node -e "@babel/parser parse" frontend/src/pages/Dashboard/Settings.jsx → OK
```

Settings.jsx is now 712 lines (down from 881 — net -169 lines). The 800-line CLAUDE.md soft cap is now satisfied.

## Requirements Satisfied
- DSGN-02 (foundation) — PlanBuilder is now a reusable component that the Plan 33-04 LandingPage rebuild will import for the pricing section, ensuring landing and settings show identical pricing UI from a single source of truth.

## Notes
- Originally Wave 2 single-plan subagent. Completed inline by the orchestrator.
- The shadcn `Slider` (Radix-based) is used instead of the previous raw `<input type="range">` for better keyboard accessibility and consistency with the rest of the design system.
- `handlePlanCheckout` was previously closing over component-scope `planUsage` state. After extraction, it accepts `planUsage` as a parameter — the PlanBuilder component passes its internal state when the user submits.
- The PlanBuilder component preserves the same API endpoint, the same field names, and the same debounce timing as the original — no behavior change for Settings users.
