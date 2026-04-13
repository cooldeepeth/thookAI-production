---
phase: 33-design-system-landing-page
plan: 04
status: complete
---

# Plan 33-04: LandingPage Split + HowItWorks + SocialProof + Mobile Nav — SUMMARY

## Files Created (9 new section components)
- `frontend/src/pages/Landing/Navbar.jsx` (138 lines) — extracted + upgraded with shadcn `Sheet` mobile drawer
- `frontend/src/pages/Landing/Hero.jsx` (109 lines) — extracted as-is
- `frontend/src/pages/Landing/Features.jsx` (183 lines) — extracted as-is (the bento grid)
- `frontend/src/pages/Landing/HowItWorks.jsx` (76 lines) — NEW
- `frontend/src/pages/Landing/DiscoverBanner.jsx` (46 lines) — extracted + token fix (`via-[#0A0A0B]` → `via-surface`)
- `frontend/src/pages/Landing/SocialProof.jsx` (44 lines) — NEW
- `frontend/src/pages/Landing/AgentCouncil.jsx` (70 lines) — extracted + AI model name update
- `frontend/src/pages/Landing/PricingSection.jsx` (30 lines) — NEW (uses `<PlanBuilder mode="landing" />`)
- `frontend/src/pages/Landing/Footer.jsx` (35 lines) — extracted + dynamic year + `data-testid="landing-footer"`

## Files Modified
- `frontend/src/pages/LandingPage.jsx` — 695 lines → 28 lines (composition root only)

## Architectural Changes

### LandingPage.jsx is now a thin composition root
```jsx
import { Navbar } from "@/pages/Landing/Navbar";
import { Hero } from "@/pages/Landing/Hero";
import { Features } from "@/pages/Landing/Features";
import { HowItWorks } from "@/pages/Landing/HowItWorks";
import { DiscoverBanner } from "@/pages/Landing/DiscoverBanner";
import { SocialProof } from "@/pages/Landing/SocialProof";
import { AgentCouncil } from "@/pages/Landing/AgentCouncil";
import { PricingSection } from "@/pages/Landing/PricingSection";
import { Footer } from "@/pages/Landing/Footer";

export default function LandingPage() {
  return (
    <div className="bg-[#050505] min-h-screen text-white overflow-x-hidden" data-testid="landing-page">
      <Navbar />
      <Hero />
      <Features />
      <HowItWorks />
      <DiscoverBanner />
      <SocialProof />
      <AgentCouncil />
      <PricingSection />
      <Footer />
    </div>
  );
}
```

`overflow-x-hidden` on the root prevents horizontal scroll at 375px (DSGN-04 hard requirement).

### Navbar mobile drawer
The desktop nav links remain in `hidden md:flex` form. On mobile, a hamburger button (`data-testid="mobile-menu-btn"`, `aria-label="Open navigation menu"`) opens a shadcn `Sheet` drawer (`data-testid="mobile-nav-drawer"`) sliding in from the right with the same nav links plus the Discover, Sign in, and Get Started actions. Sheet handles focus-trap + scroll-lock automatically via Radix.

### HowItWorks (NEW — DSGN-02 + DSGN-03)
3 numbered steps in a grid:
1. Build Your Persona (Brain icon)
2. Generate Content (Wand2 icon)
3. Publish & Learn (TrendingUp icon)

Each card has `data-testid="how-it-works-step-{1|2|3}"` (literal string in source via `STEPS[i].testId` field — greppable). Animations use `whileInView` + `viewport={{ once: true }}` so they fire once when scrolled into view.

### SocialProof (NEW — DSGN-03)
4 metric cards (factual, no fake testimonials):
- 15+ Specialist AI Agents
- 3 Social Platforms
- 200 Free Credits to Start
- < 5 min To Your First Post

`data-testid="social-proof-section"` on the wrapper.

### PricingSection (NEW — DSGN-02)
Replaces the old static `Pricing()` function (which displayed 4 hardcoded tier cards). The new section imports `PlanBuilder` from Plan 33-03 and renders it with `mode="landing"`. The CTA button navigates to `/auth` (no auth required to play with the slider — `/api/billing/plan/preview` is a public endpoint).

### AgentCouncil model names (content accuracy fix)
Per the plan, replaced incorrect model strings in the `agents` data array:
- `GPT-4o` → `Claude Sonnet 4`
- `o1-mini` → `Claude Haiku`
- `Claude 3.5` → `Claude Sonnet 4`
- `GPT-4o-mini` → `Claude Haiku`

ThookAI's agents use Anthropic models internally; the previous strings were placeholders.

### Footer dynamic year
`© 2025 ThookAI.` → `© {new Date().getFullYear()} ThookAI.` plus `data-testid="landing-footer"`.

## Acceptance Criteria — Verification
```
$ wc -l frontend/src/pages/LandingPage.jsx
28 frontend/src/pages/LandingPage.jsx

$ grep -c "how-it-works-step-" frontend/src/pages/Landing/HowItWorks.jsx
3

$ grep -c "AI Agents\|Free Credits\|Social Platforms" frontend/src/pages/Landing/SocialProof.jsx
3

$ grep -c "Sheet\|mobile-menu-btn" frontend/src/pages/Landing/Navbar.jsx
6

$ grep "getFullYear" frontend/src/pages/Landing/Footer.jsx
© {new Date().getFullYear()} ThookAI. Your AI Creative Agency.

$ grep "PlanBuilder" frontend/src/pages/Landing/PricingSection.jsx
import { PlanBuilder } from "@/components/PlanBuilder";
<PlanBuilder mode="landing" />

# Raw hex audit (excluding #050505 page bg + LinkedIn/X/Instagram brand exemptions)
$ grep -rn "#[0-9A-Fa-f]\{6\}" frontend/src/pages/Landing/ | grep -v "#050505\|#0A66C2\|#1D9BF0\|#E1306C"
ALL CLEAN

# All 10 files parse via @babel/parser → OK
```

## Requirements Satisfied
- DSGN-02 — Landing page now has hero, features, how-it-works, pricing (interactive PlanBuilder), social proof, footer with legal links. No "coming soon" placeholders.
- DSGN-03 — SocialProof section + Framer Motion `whileInView` animations on every section.
- DSGN-04 — `overflow-x-hidden` on root prevents 375px horizontal scroll. Navbar uses shadcn `Sheet` for mobile drawer with focus-trap.

## Notes
- Originally Wave 3 single-plan subagent. Completed inline by the orchestrator.
- The 9 section files were created in a single Python pass that read `LandingPage.jsx`, parsed each top-level function block by depth-counting, attached the appropriate imports, applied the model-name and year/testid updates, and wrote the new files. This avoided 9 sequential Edit calls and ensured the extractions were verbatim (no rewriting introduced bugs).
- Path alias `@/pages/Landing/...` works because CRACO is configured with `@/` → `src/`.
- All 10 files (9 new + the rewritten LandingPage.jsx) parse cleanly via `@babel/parser`.
- The old static `Pricing()` function and its `plans` data array are gone — the interactive PlanBuilder is the single source of truth shared with Settings (Plan 33-03).
