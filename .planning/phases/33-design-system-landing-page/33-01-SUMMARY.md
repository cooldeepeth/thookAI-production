---
phase: 33-design-system-landing-page
plan: 01
status: complete
---

# Plan 33-01: Token Migration — Public + Auth Pages — SUMMARY

## Files Modified
- `frontend/src/pages/AuthPage.jsx`
- `frontend/src/pages/ResetPasswordPage.jsx`
- `frontend/src/pages/LandingPage.jsx`
- `frontend/src/pages/ViralCard.jsx`
- `frontend/src/pages/Public/PersonaCardPublic.jsx`

## Changes — AuthPage.jsx
- 5 occurrences of `bg-[#18181B]` → `bg-surface-2` (5 form inputs and the tab toggle wrapper)
- 1 occurrence of `bg-[#27272A]` → `bg-border-subtle` (active tab background)

## Changes — ResetPasswordPage.jsx
- 2 occurrences of `bg-[#18181B]` → `bg-surface-2` (password and confirm-password inputs)

## Changes — LandingPage.jsx
- Discover nav link: `text-lime hover:text-[#B8E600]` → `text-lime hover:text-lime/80`
- Voice fingerprint card: `bg-[#0A0A0B]` → `bg-surface`
- Pricing CTA button highlight branch: `bg-lime text-black hover:bg-[#B8E600]` → `bg-lime text-black hover:bg-lime/90`
- Waveform visualization (lines 238–251): converted dynamic `style={{ backgroundColor: '#D4FF00' / '#27272A' }}` to conditional Tailwind classes (`bg-lime` / `bg-border-subtle`); kept `height` and `opacity` as inline style since they're per-bar dynamic computations.

## Changes — ViralCard.jsx
- Builder archetype gradient: `from-lime-500/20 via-lime-400/10` → `from-lime/20 via-lime/10` (the `lime-500`/`lime-400` variants don't exist in `tailwind.config.js` and silently no-op'd, making the gradient invisible).

## Changes — PersonaCardPublic.jsx
- Builder archetype gradient: same fix as ViralCard — `from-lime-500/20 via-lime-400/10` → `from-lime/20 via-lime/10`.

## Acceptance Criteria — Verification
```
$ grep -rn "bg-\[#18181B\]\|bg-\[#27272A\]\|lime-[0-9]\|#B8E600\|bg-\[#0A0A0B\]" \
    frontend/src/pages/AuthPage.jsx \
    frontend/src/pages/ResetPasswordPage.jsx \
    frontend/src/pages/LandingPage.jsx \
    frontend/src/pages/ViralCard.jsx \
    frontend/src/pages/Public/PersonaCardPublic.jsx
(no matches — exit 1)

$ grep -c "bg-surface-2" frontend/src/pages/AuthPage.jsx
5
```

## Requirements Satisfied
- DSGN-01 — Five highest-impact public/auth pages now use design-system tokens; no actionable raw-hex or non-existent token variants remain. Platform-brand exemptions (LinkedIn `#0A66C2`, X `#1D9BF0`, Instagram `#E1306C`) untouched as required.

## Notes
- Originally Wave 1 parallel subagent. Completed inline by the orchestrator.
- The waveform visualization in LandingPage.jsx originally used the inline style approach because the pattern is index-driven (`j < 5 + i ? lime : dark`). The fix uses Tailwind class composition `${j < 5 + i ? "bg-lime" : "bg-border-subtle"}` which is both token-correct and JIT-compiler-safe.
- One non-actionable hex remains in `LandingPage.jsx` line 368 inside a gradient class `via-[#0A0A0B]`. Out of scope for 33-01 (not specified in plan); will be naturally replaced when 33-04 rebuilds the LandingPage in Wave 3.
