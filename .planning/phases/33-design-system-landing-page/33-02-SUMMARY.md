---
phase: 33-design-system-landing-page
plan: 02
status: complete
---

# Plan 33-02: Token Migration — Dashboard + Onboarding — SUMMARY

## Files Modified (13)
- Analytics.jsx (4 changes)
- ContentLibrary.jsx (4 changes)
- ContentCalendar.jsx (2 changes)
- Campaigns.jsx (3 changes)
- Connections.jsx (3 changes)
- StrategyDashboard.jsx (2 changes)
- Admin.jsx (1 change)
- AdminUsers.jsx (4 changes)
- DailyBrief.jsx (2 changes)
- PersonaEngine.jsx (1 change)
- DashboardHome.jsx (1 change)
- Settings.jsx (2 changes)
- ContentStudio/ContentOutput.jsx (5 changes)

**Total: 34 token replacements across 13 files.**

## Files NOT Modified (already clean)
- Onboarding/PhaseTwo.jsx and Onboarding/PhaseThree.jsx — RESEARCH.md flagged these but the actual current state is clean (likely fixed in an earlier phase before Phase 33 was scoped). Verified by grep — zero green/emerald violations.

## Substitution Map Applied
| Wrong | Right |
|-------|-------|
| `text-green-400` / `text-green-500` | `text-lime` |
| `text-green-300` | `text-lime/80` |
| `bg-green-400/10` / `bg-green-500/10` | `bg-lime/10` |
| `bg-green-500/15` | `bg-lime/15` |
| `bg-green-500/20` | `bg-lime/20` |
| `border-green-500/20` | `border-lime/20` |
| `border-green-500/30` | `border-lime/30` |
| `text-emerald-400` | `text-lime` |
| `bg-emerald-500/15` / `bg-emerald-500/10` / `bg-emerald-500/20` | `bg-lime/15` / `bg-lime/10` / `bg-lime/20` |
| `to-green-500/20` (TIER_GRADIENTS) | `to-violet/20` |

## Changes — Settings.jsx TIER_GRADIENTS
- `custom: "from-lime/20 to-green-500/20"` → `custom: "from-lime/20 to-violet/20"`
- `studio: "from-lime/20 to-green-500/20"` → `studio: "from-lime/20 to-violet/20"`

The custom tier (primary paid plan) now uses lime → violet, matching the design-system rule that violet is the premium accent.

## Changes — PersonaEngine.jsx html2canvas option
Line 167's `backgroundColor: "#0A0A0A"` is a JavaScript option passed to the html2canvas() library (NOT a JSX inline style — it tells html2canvas what background to use when rendering the persona card to PNG). There is no Tailwind class equivalent for a JS API parameter, so the fix is to update the hex to match the actual `bg-surface` design token value: `#0A0A0A` → `#0F0F10` (the `bg-surface` token from `tailwind.config.js`).

## Acceptance Criteria — Verification
```
$ grep -rn "text-green-[45]\|bg-green-[45]\|text-emerald-[45]\|bg-emerald-[45]\|to-green-500\|backgroundColor.*#0A0A0A" \
    frontend/src/pages/Dashboard/ frontend/src/pages/Onboarding/ \
    --include="*.jsx" | grep -v "Shells/"
ALL CLEAN

$ grep "custom\|studio" frontend/src/pages/Dashboard/Settings.jsx | grep "from-lime\|to-violet"
  custom: "from-lime/20 to-violet/20",
  studio: "from-lime/20 to-violet/20",

# All 13 files parse cleanly via @babel/parser (no syntax errors).
```

Platform-brand exemptions left untouched as required:
- DashboardHome.jsx `quickActions` data array (LinkedIn `#0A66C2`, X `#1D9BF0`, Instagram `#E1306C`) — verified intact.
- DailyBrief.jsx platform hex array — only the `text-green-400` for the `energized` mood was changed.
- Analytics.jsx `bg-blue-600` and `bg-gradient-to-r from-pink-500 to-orange-400` for platform configs — left intact (out of scope, intentional brand colors).

## Requirements Satisfied
- DSGN-01 — All 13 dashboard/onboarding files now use design-system tokens for status colors. Combined with 33-01, the actionable green/emerald violations across the entire `frontend/src/pages/` tree are zero (excluding `Shells/` exemption).

## Notes
- Originally Wave 1 parallel subagent. Completed inline by the orchestrator using a Python bulk-substitution script for the 12 mechanical files (33 changes), plus a single targeted Edit for the PersonaEngine html2canvas option.
- The Python script was a one-shot tool that ran inline (not committed) — it iterates the substitution map across the file list and writes only when changes occur.
