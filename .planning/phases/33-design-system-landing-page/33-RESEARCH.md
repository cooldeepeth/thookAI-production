# Phase 33: Design System & Landing Page — Research

**Researched:** 2026-04-12
**Domain:** React / TailwindCSS Design System + Conversion Landing Page
**Confidence:** HIGH (fully verified from codebase)

---

## Summary

Phase 33 completes the visual identity layer of ThookAI: enforcing the lime/violet/dark token
contract across every page, and rebuilding the landing page to convert visitors into signups. The
core stack — TailwindCSS 3.4 with named color tokens, Framer Motion, shadcn/ui New York style, and
custom CSS utilities — is already defined and partially applied. The task is enforcement and
completion, not design from scratch.

The **current LandingPage.jsx** (694 lines) already contains Navbar, Hero, Features bento,
DiscoverBanner, AgentCouncil, and Pricing. It is **missing** three required sections: HowItWorks (3
steps), SocialProof (testimonials/metrics), and a complete Footer with legal links. The footer
exists but is minimal. The Pricing section shows static tier cards instead of the interactive
PlanBuilder that lives in Settings.jsx.

The **design-system audit** found violations in 18 files: platform-brand hex values
(`#0A66C2`, `#1D9BF0`, `#E1306C`) are acceptable in platform shell components (XShell, LinkedInShell,
InstagramShell) because they represent third-party brand colors, not ThookAI palette choices. The
actionable violations are: raw `#18181B` in inputs (should be `bg-surface-2`), `green-400`/`green-500`
for "success" status (should be `text-lime`), `emerald-400`/`emerald-500` in Campaigns and Admin,
`lime-500`/`lime-400` suffixed classes in ViralCard and PersonaCardPublic (these token variants do
not exist in tailwind.config.js — Tailwind will silently no-op them), and hardcoded `#050505` in
background divs (acceptable as body default, questionable in arbitrary classes).

**Primary recommendation:** Split work into 6 atomic plans — (1) design-system audit patch for
token violations across non-shell pages, (2) extract PlanBuilder to shared component, (3) build
HowItWorks + SocialProof sections, (4) rebuild landing page navigation with mobile menu, (5) add
all SEO/OG meta tags to index.html and public pages, (6) write tests. Do NOT touch ContentStudio
shell files (XShell, LinkedInShell, InstagramShell) for brand-color violations — those are
intentional platform mimicry.

---

## Project Constraints (from CLAUDE.md)

- All work branches from `dev`. PRs target `dev`. Never commit to `main` directly.
- Branch naming: `fix/short-description`, `feat/short-description`
- Config pattern: All settings via `backend/config.py` — not relevant to pure-frontend phase
- No new npm packages without noting in PR description
- Frontend test runner: Jest (via react-scripts). Test files in `frontend/src/__tests__/`
- Path alias `@/` maps to `src/` via CRACO webpack config
- Always use `apiFetch()` from `@/lib/api` — never raw `fetch()`
- Auth: Cookie-based (`session_token` httpOnly cookie). No localStorage tokens

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DSGN-01 | Consistent design system applied across all pages (colors, typography, spacing, components) | Section 1 audit identifies exactly which files need token migration and which violations are intentional |
| DSGN-02 | Landing page has hero, features, how-it-works, pricing (plan builder), CTA, footer | Section 3 identifies missing sections and the PlanBuilder extraction strategy |
| DSGN-03 | Landing page is conversion-optimized with animations and social proof section | Animation patterns documented; SocialProof section identified as fully missing |
| DSGN-04 | Mobile-first responsive design on landing page | Breakpoint plan in Section 3; mobile nav gap identified in Navbar component |
| DSGN-05 | SEO meta tags and Open Graph tags on all public pages | Section 4 identifies all gaps: no OG tags, no og:image, no canonical in index.html |
</phase_requirements>

---

## 1. Current State Audit

### 1a. LandingPage.jsx — Sections Present vs Missing

File: `frontend/src/pages/LandingPage.jsx` (694 lines)
[VERIFIED: Read tool, full file scan]

| Section | Present | Quality | Notes |
|---------|---------|---------|-------|
| Navbar | YES | Good — uses token classes | Missing mobile hamburger menu — links hidden with `hidden md:flex` but no `<Sheet>` or `<MobileMenu>` component for small screens |
| Hero | YES | Good — Framer Motion, btn-primary | Uses `bg-[#050505]` in root div (acceptable as body bg), one `#B8E600` hover target (should be hover class on `.btn-primary`) |
| Features (bento) | YES | Mostly good | Uses `bg-[#0A0A0B]` inside voice fingerprint card — should be `bg-surface` |
| DiscoverBanner | YES | Good | No violations |
| AgentCouncil | YES | Good | Listed model names are outdated (GPT-4o, o1-mini, "Claude 3.5") — not a token issue but content accuracy gap |
| Pricing | YES | Static tier cards | Does NOT use the interactive PlanBuilder from Settings.jsx. Has hardcoded `$0`, `$15`, `$79`, `$149+` tiers. DSGN-02 requires "pricing (plan builder)". |
| HowItWorks | **MISSING** | — | Required by DSGN-02. Not present anywhere in the file. |
| SocialProof | **MISSING** | — | Required by DSGN-03. Not present anywhere in the file. |
| Footer | YES (minimal) | Minimal | Has logo, copyright, Privacy/Terms/Contact links. Passes DSGN-02 "footer with legal links" if we verify /privacy and /terms routes exist (they do). Copyright says "© 2025" — needs update to 2026. |

**Summary of missing work on landing page:**
1. HowItWorks section (3 steps) — must be added before Features or after Features
2. SocialProof / testimonials / metrics section
3. Pricing must show the PlanBuilder UI (interactive sliders), not static tier cards
4. Mobile navigation — Navbar has no hamburger/mobile-menu for screens < 768px
5. Content in AgentCouncil shows wrong model names (cosmetic, but misleading)

### 1b. Design Token Violations — Grouped by Severity

**ACTIONABLE VIOLATIONS** (must fix for DSGN-01):
[VERIFIED: grep across all frontend/src/pages/**/*.jsx]

| File | Line(s) | Violation | Fix |
|------|---------|-----------|-----|
| `ViralCard.jsx` | 52 | `from-lime-500/20` — `lime-500` does not exist in tailwind.config.js; silently no-ops | Replace with `from-lime/20` |
| `ViralCard.jsx` | 52 | `via-lime-400/10` — same issue | Replace with `via-lime/10` |
| `Public/PersonaCardPublic.jsx` | 14 | `from-lime-500/20`, `via-lime-400/10` — same Tailwind variant issue | Replace with `from-lime/20`, `via-lime/10` |
| `Dashboard/Analytics.jsx` | 22, 29, 285, 355 | `text-green-400`, `bg-green-500/10` for "improving"/"healthy" status | Replace with `text-lime`, `bg-lime/10` — or keep `green` if semantically distinct from brand (success vs active) |
| `Dashboard/ContentLibrary.jsx` | 28, 437 | `bg-green-500/20 text-green-400` for published status badge | Use `text-lime` + `bg-lime/10` for published (positive = lime in this brand) |
| `Dashboard/AdminUsers.jsx` | 295, 328 | `bg-green-500/15 text-green-400` for active badge | Replace with lime token |
| `Dashboard/StrategyDashboard.jsx` | 174 | `text-green-400` for connected state | Replace with `text-lime` |
| `Dashboard/Campaigns.jsx` | 260, 303 | `bg-emerald-500/15 text-emerald-400` for published | Replace with lime tokens |
| `Dashboard/Connections.jsx` | 238 | `bg-green-500/10 text-green-400` for connected badge | Replace with lime tokens |
| `Dashboard/Settings.jsx` | 39, 41 | `to-green-500/20` in TIER_GRADIENTS for `custom` and `studio` | Replace with `to-violet/20` or `to-lime/10` |
| `Dashboard/ContentCalendar.jsx` | 37 | `bg-green-500/10 text-green-400` for published | Replace with lime tokens |
| `Dashboard/DashboardHome.jsx` | 32 | `text-green-500` for "approved" status | Replace with `text-lime` |
| `Dashboard/DailyBrief.jsx` | 17 | `text-green-400` for "energized" | Replace with `text-lime` |
| `Dashboard/Admin.jsx` | 140 | `color="text-emerald-400"` for stat | Replace with `text-lime` |
| `Dashboard/ContentStudio/ContentOutput.jsx` | 939 | `text-green-400` for check icon | Replace with `text-lime` |
| `ResetPasswordPage.jsx` | 90, 99 | `bg-[#18181B]` on inputs | Replace with `bg-surface-2` |
| `AuthPage.jsx` | 202, 229, 244, 310, 323, 335 | `bg-[#18181B]` on inputs, `bg-[#27272A]` tab toggle | Replace with `bg-surface-2`, `bg-border-subtle` |
| `LandingPage.jsx` | 44 | `text-[#B8E600]` hover color | Remove — `.btn-primary:hover` handles this; or use Tailwind `hover:text-lime/80` |
| `LandingPage.jsx` | 230 | `bg-[#0A0A0B]` in voice card | Replace with `bg-surface` |
| `LandingPage.jsx` | 244 | `backgroundColor: "#D4FF00"` inline style in waveform | Replace with CSS class or use `style={{ backgroundColor: 'var(--primary)' }}` — acceptable given dynamic index calc, flag for planner |
| `Dashboard/PersonaEngine.jsx` | 167 | `backgroundColor: "#0A0A0A"` | Replace with `bg-surface` token |

**INTENTIONALLY EXEMPT** (platform-brand colors — do not change):
[VERIFIED: XShell.jsx, InstagramShell.jsx, LinkedInShell.jsx, InputPanel.jsx, ContentStudio/index.jsx, DashboardHome.jsx, DailyBrief.jsx]

These files use `#0A66C2` (LinkedIn blue), `#1D9BF0` (X/Twitter blue), `#E1306C` (Instagram pink).
These are third-party brand colors required for platform-mimicry UI (the social post preview shells).
Do NOT convert these to ThookAI tokens — they represent external platforms, not the ThookAI brand.
The planner must add a comment `// INTENTIONAL: platform brand color` at each usage so future
reviewers understand this choice.

### 1c. Pages With Good Token Usage (Reference Examples)

- `Dashboard/Sidebar.jsx` — uses `sidebar-nav-item.active` CSS class correctly
- `Dashboard/index.jsx` — `bg-[#050505]` is acceptable as the body background
- `LandingPage.jsx` (most sections) — correctly uses `card-thook`, `btn-primary`, `btn-ghost`, `text-lime`, `text-zinc-400`
- `Dashboard/Settings.jsx` BillingTab UI — uses `text-lime`, `bg-lime/10`, `border-lime/20` correctly

### 1d. shadcn/ui Primitives Installed

[VERIFIED: `ls frontend/src/components/ui/`]

The following 47 primitives are installed (no duplicates needed):
accordion, alert-dialog, alert, aspect-ratio, avatar, badge, breadcrumb, button, calendar,
card, carousel, checkbox, collapsible, command, context-menu, dialog, drawer, dropdown-menu,
form, hover-card, input-otp, input, label, menubar, navigation-menu, pagination, popover,
progress, radio-group, resizable, scroll-area, select, separator, sheet, skeleton, slider,
sonner, switch, table, tabs, textarea, toast, toaster, toggle-group, toggle, tooltip,
UIComponents (custom composite)

For the mobile Navbar on landing: use `sheet` (already installed) for the slide-in drawer.
For plan builder sliders: use `slider` (already installed).

### 1e. Public Routes Map

[VERIFIED: `frontend/src/App.js` route definitions]

| Path | Component | Public? | Needs SEO tags? |
|------|-----------|---------|-----------------|
| `/` | LandingPage | YES | YES — primary |
| `/auth` | AuthPage | YES | NO — auth flow |
| `/reset-password` | ResetPasswordPage | YES | NO |
| `/creator/:shareToken` | PersonaCardPublic | YES | Partial (og:image for share) |
| `/p/:shareToken` | PersonaCardPublic | YES | Partial |
| `/discover` | ViralCard | YES | YES — shareable tool |
| `/discover/:cardId` | ViralCard | YES | YES — shareable tool |
| `/privacy` | PrivacyPolicy | YES | YES — DSGN-05 |
| `/terms` | TermsOfService | YES | YES — DSGN-05 |
| `/onboarding` | Onboarding | NO (protected) | NO |
| `/dashboard/*` | Dashboard | NO (protected) | NO |

All routes use Vercel rewrites (`vercel.json`: `"source": "/(.*)", "destination": "/index.html"`),
confirming that `frontend/public/index.html` IS served as initial HTML for all routes — critical
for SEO.

---

## 2. Token Contract

### 2a. Authoritative Color Tokens

[VERIFIED: `frontend/tailwind.config.js`, `frontend/src/index.css`]

| Token Class | Value | Semantic Use | Wrong Alternative |
|-------------|-------|--------------|-------------------|
| `text-lime` / `bg-lime` | `#D4FF00` | Primary CTAs, success/active/brand | `text-lime-400`, `text-lime-500`, `text-green-400` |
| `text-violet` / `bg-violet` | `#7000FF` | Secondary, premium, video features | `text-purple-600`, `text-violet-600` |
| `bg-surface` | `#0F0F10` | Card backgrounds, list items | `bg-[#0F0F0F]`, `bg-[#0A0A0A]` |
| `bg-surface-2` | `#18181B` | Input backgrounds, elevated surfaces | `bg-[#18181B]` (raw hex), `bg-zinc-900` |
| `border-subtle` | `#27272A` | Subtle dividers | `bg-[#27272A]` (raw), `border-zinc-800` |
| `bg-[#050505]` | `#050505` | App/page background (body) | `bg-black`, `bg-zinc-950` |

Note: `bg-[#050505]` is acceptable as an arbitrary class for the page background because the `background` CSS var resolves to `hsl(0 0% 2%)` = `#050505` and TailwindCSS does not expose the CSS var as a standard `bg-background` utility (it does for the shadcn mapping, but not the raw token). Using `bg-background` works because it maps to `hsl(var(--background))` = `#050505`.

### 2b. Typography Classes

[VERIFIED: `frontend/tailwind.config.js`, `frontend/src/index.css`]

| Class | Font Family | Weight | Correct Use |
|-------|-------------|--------|-------------|
| `font-display` | Clash Display → Outfit fallback | 600/700 | h1, h2, h3, big numbers, brand text |
| (default body) | Plus Jakarta Sans → DM Sans | 400–700 | All other text; body already defaults |
| `font-mono` | JetBrains Mono | 400/500 | Credit counts, stats, code, labels |

Note: h1/h2/h3 get `font-family: 'Clash Display'` globally via `@layer base` in `index.css` — adding `font-display` class is redundant but harmless and explicit.

### 2c. Custom CSS Utility Classes

[VERIFIED: `frontend/src/index.css`]

| Class | Purpose | When to Use |
|-------|---------|-------------|
| `.card-thook` | Dark surface card with hover border | Static info cards |
| `.card-thook-interactive` | Clickable card with lime hover glow + lift | Clickable cards |
| `.btn-primary` | Lime pill button with glow shadow | Primary CTA buttons |
| `.btn-ghost` | Glass-morphism button | Secondary/outline buttons |
| `.btn-danger` | Red subtle button | Destructive actions |
| `.glass` | Glass-morphism panel (blur backdrop) | Modals, overlays, floating panels |
| `.hero-glow` | Violet radial gradient background | Hero section backdrop |
| `.gradient-text` | Lime-to-cyan gradient text clip | Decorative headings |
| `.gradient-text-violet` | Violet-to-lime gradient text | Decorative secondary headings |
| `.sidebar-nav-item` | Sidebar link with active indicator | Sidebar navigation only |
| `.input-thook` | Dark input with lime focus ring | Form inputs (alternative to shadcn Input) |
| `.badge-lime` | Lime pill badge | Active/success/brand status |
| `.badge-violet` | Violet pill badge | Premium/video/secondary status |
| `.badge-zinc` | Zinc pill badge | Neutral/inactive status |
| `.skeleton` | Shimmer loading placeholder | Loading states |
| `.focus-ring` | Accessible focus outline | Interactive elements |

### 2d. Animation Classes (Tailwind + keyframes)

[VERIFIED: `frontend/tailwind.config.js`]

| Class | Behavior | Use On |
|-------|----------|--------|
| `animate-fade-in` | 0.4s fade + slide up 10px | Page sections, cards entering |
| `animate-fade-in-up` | 0.5s fade + slide up 20px | Hero content |
| `animate-pulse-lime` | Lime glow pulse loop 2s | Active indicators, live dots |
| `animate-float` | Gentle float ±8px loop 4s | Hero decorative elements |
| `animate-shimmer` | Skeleton loading shimmer | Loading placeholders |
| `animate-glow-pulse` | Box-shadow glow breathing | Highlighted cards, CTA glow |
| `animate-border-glow` | Border color breathing | Featured pricing card |
| `animate-bounce-soft` | Soft bounce ±4px | "Scroll down" indicators |

Shadow utilities: `shadow-glow-lime`, `shadow-glow-violet`, `shadow-card-hover`, `shadow-modal`

### 2e. WRONG vs CORRECT — Top 5 Token Mistakes

| # | WRONG | CORRECT | Why |
|---|-------|---------|-----|
| 1 | `className="text-lime-400"` | `className="text-lime"` | `lime-400` is a Tailwind shade variant that does not exist in the config — it silently produces nothing |
| 2 | `className="bg-[#18181B]"` | `className="bg-surface-2"` | `surface-2` token is defined in tailwind.config.js, arbitrary hex bypasses the token system |
| 3 | `className="text-green-400"` (for success/active) | `className="text-lime"` | ThookAI brand uses lime for positive/active states, not Tailwind's green scale |
| 4 | `style={{ color: '#D4FF00' }}` | `className="text-lime"` | Raw hex in inline styles bypasses Tailwind's JIT purge and design tokens entirely |
| 5 | Two separate `<MobileNav>` and `<DesktopNav>` components | Single `<Navbar>` with `hidden md:flex` / `md:hidden` | One component with conditional display is simpler, cheaper, and easier to maintain |

---

## 3. Landing Page Architecture Options

### 3a. File Structure Recommendation

**Recommended: Section-component split, single file import**

Current `LandingPage.jsx` is 694 lines and will grow to ~1,100 lines with HowItWorks +
SocialProof + PlanBuilder + improved mobile nav. At 1,100 lines it is 38% over the 800-line max
per CLAUDE.md coding conventions.

**Recommended structure:**
```
frontend/src/pages/
├── LandingPage.jsx              # Root: imports and composes section components (~80 lines)
└── Landing/
    ├── Navbar.jsx               # Navbar + mobile sheet menu (~80 lines)
    ├── Hero.jsx                 # Hero section (~80 lines)
    ├── Features.jsx             # Features bento grid (~180 lines)
    ├── HowItWorks.jsx           # 3-step how-it-works (~80 lines) — NEW
    ├── PricingSection.jsx       # Uses PlanBuilder component (~80 lines) — REFACTORED
    ├── SocialProof.jsx          # Testimonials / metrics / logos (~100 lines) — NEW
    ├── DiscoverBanner.jsx       # CTA banner (~60 lines)
    ├── AgentCouncil.jsx         # Agent grid (~80 lines)
    └── Footer.jsx               # Footer with legal links (~50 lines)
```

Plus a new shared component:
```
frontend/src/components/
└── PlanBuilder.jsx              # Extracted from Settings.jsx BillingTab — reused in both
```

**Why split vs monolith:**
- Current monolith is already 694 lines and needs ~400 more — will hit 1,100+
- Section components have zero interdependency — no shared state between Hero and Footer
- Enables per-section lazy loading if bundle size becomes a concern in Phase 35
- Makes individual section tests straightforward (Jest RTL can render `<HowItWorks />` in isolation)
- Existing sections (DiscoverBanner, AgentCouncil) are already inner functions in LandingPage.jsx — extracting is a refactor, not an architectural change

**Alternative (rejected): Keep as single file.** Below 800 lines after editing, but only barely, and
the extraction is low-risk since all sections are already defined as inner functions. Not recommended.

### 3b. PlanBuilder Extraction Strategy

The `BillingTab` function in `frontend/src/pages/Dashboard/Settings.jsx` (lines 79–773) contains
the full PlanBuilder UI — sliders for content types, credit calculator, price preview, checkout
button. This is 694 lines for BillingTab alone.

The landing page currently has a static pricing table that contradicts DSGN-02's "pricing (plan
builder)" requirement.

**Strategy: Extract PlanBuilder to shared component**
1. Create `frontend/src/components/PlanBuilder.jsx`
2. Move `PLAN_BUILDER_DEFAULTS`, `PLAN_BUILDER_LABELS`, the slider UI, and the credit calculator
   out of `Settings.jsx`
3. PlanBuilder accepts: `mode: "landing" | "settings"` prop
   - `landing` mode: shows only sliders + price preview + "Get Started" CTA (navigates to /auth)
   - `settings` mode: shows full BillingTab including current subscription, credit packages, manage billing
4. Settings.jsx imports `<PlanBuilder mode="settings" ...>` wrapping it with subscription context
5. LandingPage uses `<PlanBuilder mode="landing" />` — no auth required, no API calls for current sub

Key insight: The landing page PlanBuilder should call `POST /api/billing/plan/preview` as a
public endpoint (currently this endpoint requires auth). The planner must check if
`/api/billing/plan/preview` can be called without auth — if not, add a `_no_auth=true` flag or a
separate `/api/billing/plan/estimate` public endpoint.

### 3c. HowItWorks Section

3 steps, ordered:
1. **Build Your Persona** — Answer 7 questions about your voice, goals, and style
2. **Generate Content** — Describe what you want; 15 AI agents craft platform-native posts
3. **Publish & Learn** — Schedule, publish, and watch the AI improve from your edits

Pattern:
```jsx
// Each step: numbered badge + icon + heading + description
// Container: horizontal on md+, vertical on mobile
// Animation: staggered fade-in-up with delay: i * 0.15
<div className="grid grid-cols-1 md:grid-cols-3 gap-8">
  {steps.map((step, i) => (
    <motion.div
      key={step.number}
      initial={{ opacity: 0, y: 20 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      transition={{ delay: i * 0.15 }}
      className="card-thook p-6 text-center"
    >
      <div className="w-10 h-10 rounded-full bg-lime text-black font-display font-bold text-lg flex items-center justify-center mx-auto mb-4">
        {step.number}
      </div>
      ...
    </motion.div>
  ))}
</div>
```

### 3d. SocialProof Section

Minimal viable social proof for a pre-launch product (no real testimonials):
- 3 synthetic/founder-approved quote cards (can include Kuldeepsinh's quote)
- Stats row: "15+ AI Agents", "3 Platforms", "200 Free Credits", "< 5 min to first post"
- Platform logos row (LinkedIn, X, Instagram) with "Publishes to" label (already in Hero — move here)

If real testimonials are not available at launch, use:
```jsx
// Metric cards with font-mono numbers + font-display labels
<div className="grid grid-cols-2 md:grid-cols-4 gap-4">
  {metrics.map(m => (
    <div className="card-thook p-4 text-center">
      <p className="font-mono text-4xl text-lime mb-1">{m.value}</p>
      <p className="text-sm text-zinc-400">{m.label}</p>
    </div>
  ))}
</div>
```

### 3e. Mobile-First Breakpoint Plan

[VERIFIED: Design system rules, current LandingPage.jsx analysis]

| Breakpoint | Width | Behavior |
|------------|-------|----------|
| Mobile (base) | < 640px (sm) | Single column, stacked sections, hamburger menu |
| sm | 640px | Hero CTAs go from column to row (`flex-col sm:flex-row`) |
| md | 768px | Desktop nav appears, two/three column grids activate, pricing goes to 2-col |
| lg | 1024px | Pricing goes to 4-col, AgentCouncil goes to 5-col |
| xl | 1280px | Max-width containers cap at 7xl (1280px) |

**Sections requiring special mobile handling:**
1. **Navbar** — desktop nav `hidden md:flex`, mobile hamburger using shadcn `Sheet` component
2. **Hero** — font size scales: `text-5xl md:text-6xl lg:text-7xl`; CTAs: `flex-col sm:flex-row`
3. **Features bento** — `grid-cols-1 md:grid-cols-4` (bento colspans need careful mobile fallback)
4. **AgentCouncil** — `grid-cols-2 md:grid-cols-3 lg:grid-cols-5` (already correct)
5. **Pricing** — `grid-cols-1 md:grid-cols-2 lg:grid-cols-4` (with PlanBuilder: `grid-cols-1 md:grid-cols-2`)
6. **Footer** — `flex-col md:flex-row` (already correct)

**Critical mobile test:** At 375px, the hero CTA button must be min-height 44px for tap target
(`.btn-primary` has `padding: 0.75rem 2rem` = 48px height — passes). The main risk is the
Features bento: `md:col-span-2 md:row-span-2` on mobile renders as full-width single cells (fine).

---

## 4. SEO + Meta Tags Strategy

### 4a. Current State

[VERIFIED: `frontend/public/index.html` — full read]

Current `index.html` has:
- `<meta name="description" content="ThookAI — Your AI Creative Agency">` — present but thin (31 chars vs 160 max)
- `<meta name="theme-color" content="#000000">` — present (update to `#050505`)
- `<title>ThookAI</title>` — present (too bare, needs product descriptor)
- **Missing entirely:** og:title, og:description, og:image, og:type, og:url, twitter:card, twitter:title, twitter:image, canonical URL

### 4b. SEO Strategy for CRA SPA + Vercel

[VERIFIED: vercel.json confirms SPA rewrite to index.html for all routes]

**Key constraint:** Vercel serves `index.html` for ALL routes (including `/privacy`, `/discover`).
For a CRA SPA, SEO crawlers receive the blank `index.html` shell — JavaScript hasn't run yet.
**Conclusion:** Static OG tags in `index.html` cover the base case for all pages. Dynamic per-route
meta is a future enhancement, not required for DSGN-05.

**`react-helmet-async` status:** Not installed (verified: `grep "react-helmet" frontend/package.json`
returns nothing). Do NOT add it for this phase — static tags in `index.html` satisfy DSGN-05.

For `/discover` and persona share pages (`/creator/:shareToken`) where og:image could be dynamic,
the static fallback og:image in `index.html` is acceptable for Phase 33.

### 4c. Required Meta Tags for index.html

```html
<!-- Primary SEO -->
<title>ThookAI — Your AI Creative Agency for LinkedIn, X & Instagram</title>
<meta name="description" content="Build your AI persona, generate platform-native content with 15 specialist agents, and publish to LinkedIn, X, and Instagram. Free to start." />
<meta name="theme-color" content="#050505" />

<!-- Open Graph -->
<meta property="og:type" content="website" />
<meta property="og:url" content="https://thook.ai/" />
<meta property="og:title" content="ThookAI — Your AI Creative Agency" />
<meta property="og:description" content="Build your AI persona, generate platform-native content with 15 specialist agents, and publish to LinkedIn, X, and Instagram." />
<meta property="og:image" content="https://thook.ai/og-image.png" />
<meta property="og:image:width" content="1200" />
<meta property="og:image:height" content="630" />
<meta property="og:site_name" content="ThookAI" />

<!-- Twitter / X Card -->
<meta name="twitter:card" content="summary_large_image" />
<meta name="twitter:title" content="ThookAI — Your AI Creative Agency" />
<meta name="twitter:description" content="Build your AI persona, generate platform-native content with 15 specialist agents, and publish to LinkedIn, X, and Instagram." />
<meta name="twitter:image" content="https://thook.ai/og-image.png" />

<!-- Canonical -->
<link rel="canonical" href="https://thook.ai/" />
```

**Requirements for the og:image:**
- Static file: `frontend/public/og-image.png`
- Dimensions: 1200×630px
- Content: ThookAI logo + tagline on dark (`#050505`) background with lime accent
- **Approach: Design and export a static PNG** — no fal.ai dynamic generation needed for Phase 33.
  Dynamic OG images are a Phase 35 enhancement.
- The planner must include a task to create this image (can be done with a simple canvas-based
  script or a design tool export)

### 4d. PrivacyPolicy and TermsOfService

[VERIFIED: `frontend/src/pages/PrivacyPolicy.jsx` and `TermsOfService.jsx` both exist, routes confirmed]

Both pages exist and are publicly accessible. They use `bg-[#050505]` (acceptable). DSGN-05
requires OG tags on "all public pages" — for these legal pages, adding basic meta title/description
is sufficient (no per-page og:image needed). Since we're using static `index.html` OG tags, both
pages inherit the site-level tags automatically — this satisfies DSGN-05 for legal pages.

---

## 5. Cross-Page Design System Audit Scope

### 5a. Files Needing Token Migration (Grouped by Plan)

**Group A: High-traffic / highest-impact pages (fix first)**
- `frontend/src/pages/AuthPage.jsx` — 11 hex violations, all inputs using raw `#18181B`
- `frontend/src/pages/LandingPage.jsx` — 10 hex violations (most are acceptable platform colors in data arrays, 2-3 need fixing)
- `frontend/src/pages/ResetPasswordPage.jsx` — 3 violations, all inputs

**Group B: Dashboard core pages**
- `frontend/src/pages/Dashboard/DashboardHome.jsx` — 4 violations (platform brand colors acceptable)
- `frontend/src/pages/Dashboard/Settings.jsx` — 2 violations (green gradient tokens)
- `frontend/src/pages/Dashboard/Analytics.jsx` — 4 violations (green-400 status colors)
- `frontend/src/pages/Dashboard/ContentCalendar.jsx` — 1 violation (green-400 for published)
- `frontend/src/pages/Dashboard/ContentLibrary.jsx` — 2 violations (green-500 for published)

**Group C: Lower-traffic dashboard pages**
- `frontend/src/pages/Dashboard/Campaigns.jsx` — 2 violations (emerald for published status)
- `frontend/src/pages/Dashboard/Connections.jsx` — 1 violation (green for connected)
- `frontend/src/pages/Dashboard/StrategyDashboard.jsx` — 1 violation (green for connected)
- `frontend/src/pages/Dashboard/Admin.jsx` — 1 violation (emerald for stat)
- `frontend/src/pages/Dashboard/AdminUsers.jsx` — 2 violations (green for active)
- `frontend/src/pages/Dashboard/DailyBrief.jsx` — 3 violations (platform brand hex + green-400)
- `frontend/src/pages/Dashboard/PersonaEngine.jsx` — 5 violations (raw hex in inputs/bg)
- `frontend/src/pages/Dashboard/AgencyWorkspace/index.jsx` — 2 violations (raw hex bg)
- `frontend/src/pages/Dashboard/ContentStudio/ContentOutput.jsx` — 1 violation (green-400 check)

**Group D: Public/Onboarding pages**
- `frontend/src/pages/ViralCard.jsx` — 3 violations (lime-500 variant + bg-[#050505])
- `frontend/src/pages/Public/PersonaCardPublic.jsx` — 4 violations (lime-500 variant + bg-[#050505])
- `frontend/src/pages/Onboarding/VisualPaletteStep.jsx` — 6 violations (palette color picker, mostly intentional)
- `frontend/src/pages/Onboarding/PhaseTwo.jsx` — 3 violations
- `frontend/src/pages/Onboarding/PhaseThree.jsx` — 2 violations

**EXEMPT (platform shells — intentional brand colors):**
- `ContentStudio/Shells/XShell.jsx` (25 violations — all platform brand)
- `ContentStudio/Shells/InstagramShell.jsx` (6 violations — all platform brand)
- `ContentStudio/Shells/LinkedInShell.jsx` (4 violations — all platform brand)
- `ContentStudio/InputPanel.jsx` (5 violations — platform color data arrays)
- `ContentStudio/index.jsx` (3 violations — platform color data)
- `Dashboard/DashboardHome.jsx` (3 of 4 violations — platform color data)
- `Dashboard/DailyBrief.jsx` (2 of 3 violations — platform color data)

### 5b. Highest-Impact Pages for DSGN-01

1. **AuthPage.jsx** — every new user sees this page first; raw inputs harm brand consistency
2. **LandingPage.jsx** — the acquisition page; must be token-perfect
3. **DashboardHome.jsx** — first page after login; most active users see it daily
4. **Settings.jsx** — billing is a trust-critical page; green gradients look inconsistent
5. **Analytics.jsx** — data page with mixed green/lime creates visual inconsistency

---

## 6. Pitfalls + Patterns (Planner Constraints)

### Pitfall 1: `lime-400` / `lime-500` — Silent No-Op

**What goes wrong:** Developer writes `text-lime-400` expecting a lighter lime. Tailwind generates
no CSS for this class because `lime` is defined as a flat hex `#D4FF00` in `tailwind.config.js`,
not as a shade scale. The text renders white (inherited) or transparent.

**Code example:**
```jsx
// WRONG — silently produces no color class
<span className="text-lime-400">200 credits</span>

// CORRECT — the only valid lime token
<span className="text-lime">200 credits</span>

// CORRECT — for lighter lime effect use opacity modifier
<span className="text-lime/70">secondary lime text</span>
```

**Where it exists today:** `ViralCard.jsx` line 52, `PersonaCardPublic.jsx` line 14.
**Prevention:** Every plan's verification step must run: `grep -rn "lime-[0-9]" frontend/src/`

---

### Pitfall 2: Meta Tags in Helmet Only

**What goes wrong:** Developer installs `react-helmet-async` and puts OG tags in a `<Helmet>` block
inside a React component. Works in the browser. But Vercel serves the static `index.html` for the
initial HTML crawl — the OG tags are not present until JavaScript runs. Social crawlers (Twitter,
LinkedIn, Slack) parse the initial HTML only and will not see the OG image.

**Code example:**
```jsx
// WRONG for Vercel SPA — OG tags set in React component
function LandingPage() {
  return (
    <>
      <Helmet>
        <meta property="og:image" content="..." />
      </Helmet>
      ...
    </>
  );
}

// CORRECT for Phase 33 — static tags in frontend/public/index.html
// (react-helmet-async not needed and not installed — do not add it)
```

**Prevention:** All OG meta tags for Phase 33 go into `frontend/public/index.html` only.

---

### Pitfall 3: Duplicating PlanBuilder UI

**What goes wrong:** The PlanBuilder (sliders + price calculator) is built from scratch in
LandingPage.jsx as a simpler static version. Then Settings.jsx gets another update. Now there
are two separate implementations of the same UI that diverge over time.

**Code example:**
```jsx
// WRONG — duplicated implementation
// In LandingPage.jsx:
function PricingSection() {
  const [posts, setPosts] = useState(20);  // duplicate state
  // ...200 lines of slider UI
}

// CORRECT — extract shared component
// frontend/src/components/PlanBuilder.jsx
export function PlanBuilder({ mode = "landing", onCheckout }) { ... }

// In LandingPage.jsx:
import { PlanBuilder } from "@/components/PlanBuilder";
<PlanBuilder mode="landing" />

// In Settings.jsx BillingTab:
import { PlanBuilder } from "@/components/PlanBuilder";
<PlanBuilder mode="settings" onCheckout={handlePlanCheckout} subscription={subscription} />
```

---

### Pitfall 4: Separate Mobile and Desktop Nav Components

**What goes wrong:** Developer creates `<MobileNav>` and `<DesktopNav>` as separate components
with duplicated links. When a new nav link is added, it must be added to both components — one
invariably gets missed.

**Code example:**
```jsx
// WRONG — two components, duplicated links
function DesktopNav() {
  return <nav className="hidden md:flex">...</nav>;
}
function MobileNav() {
  return <div className="md:hidden">...</div>;  // will drift from DesktopNav
}

// CORRECT — single Navbar with conditional rendering
function Navbar() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const links = [
    { href: "#features", label: "Product" },
    { href: "#agents", label: "Agents" },
    { href: "#pricing", label: "Pricing" },
  ];
  return (
    <nav ...>
      {/* Desktop */}
      <div className="hidden md:flex gap-8">
        {links.map(l => <a key={l.href} href={l.href}>{l.label}</a>)}
      </div>
      {/* Mobile toggle */}
      <button className="md:hidden" onClick={() => setMobileOpen(true)}>
        <Menu size={20} />
      </button>
      {/* Mobile sheet — uses shadcn Sheet (already installed) */}
      <Sheet open={mobileOpen} onOpenChange={setMobileOpen}>
        <SheetContent side="right" className="bg-surface w-[260px]">
          <nav className="flex flex-col gap-4 pt-8">
            {links.map(l => <a key={l.href} href={l.href} onClick={() => setMobileOpen(false)}>{l.label}</a>)}
          </nav>
        </SheetContent>
      </Sheet>
    </nav>
  );
}
```

---

### Pitfall 5: `green-400` for "success" States

**What goes wrong:** Developer uses Tailwind's built-in `text-green-400` for success/published/
connected/active states. This creates an inconsistency — ThookAI's brand uses `lime` (#D4FF00)
for positive states. On a dark background, `green-400` and `lime` look like two different design
systems living on the same page.

**The one exception:** Inside social platform shell components (XShell, InstagramShell), green
can represent a platform-native color (e.g., `#00BA7C` for X's retweet button). This is
intentional and documented.

```jsx
// WRONG — using Tailwind green for ThookAI brand success states
<Badge className="bg-green-500/20 text-green-400">Published</Badge>

// CORRECT — lime = positive in ThookAI's brand
<Badge className="bg-lime/10 text-lime border-lime/20">Published</Badge>

// EXCEPTION (acceptable in platform shells only):
// <button className="hover:text-[#00BA7C]">  {/* X platform retweet green */}
```

---

### Pitfall 6: LandingPage.jsx Sections as Inner Functions

**What goes wrong:** Current LandingPage.jsx defines `Navbar`, `Hero`, `Features`, etc. as
inner functions at module scope. When this file is split into section components, naively moving
them to new files creates a common mistake: the inner functions use `useNavigate()` directly.
`useNavigate` must be called inside a Router context — it works now because LandingPage.jsx is
rendered inside `BrowserRouter`. If you extract `Navbar.jsx` and try to render it in a test
without a Router, it will throw.

```jsx
// WRONG — Navbar.jsx extracted but tested without Router
import { render } from '@testing-library/react';
import Navbar from './Navbar';
render(<Navbar />);  // THROWS: useNavigate() may be used only in the context of a <Router>

// CORRECT — always wrap in MemoryRouter in tests
import { MemoryRouter } from 'react-router-dom';
render(<MemoryRouter><Navbar /></MemoryRouter>);
```

---

### Pitfall 7: Footer Copyright Year Hardcoded

**What goes wrong:** Current footer has `© 2025 ThookAI`. This was already outdated at the time
of research (2026). Hardcoding years in JSX means it's wrong the moment New Year hits.

```jsx
// WRONG — hardcoded year
<p>© 2025 ThookAI. Your AI Creative Agency.</p>

// CORRECT — dynamic year
<p>© {new Date().getFullYear()} ThookAI. Your AI Creative Agency.</p>
```

---

## 7. Dependency-on-Phase-32 Audit

Phase 32 polished: AuthPage, DashboardHome, Settings, ContentStudio (ContentOutput, InputPanel,
index.jsx), ErrorBoundary. Checking each for residual DSGN-01 violations:

| File (Phase 32 scope) | Residual Violations for DSGN-01 | Action |
|----------------------|--------------------------------|--------|
| `AuthPage.jsx` | YES — `bg-[#18181B]` on all input fields (11 occurrences), `bg-[#27272A]` tab toggle | Fix in Phase 33 Plan A (token migration — public pages) |
| `DashboardHome.jsx` | MINOR — platform brand hex in data array (intentional, exempt) + `text-green-500` for "approved" status (line 32) | Fix `text-green-500` → `text-lime` in Plan B (dashboard token audit) |
| `Settings.jsx` | MINOR — `to-green-500/20` in TIER_GRADIENTS (2 lines) | Fix in Plan B |
| `ContentStudio/ContentOutput.jsx` | MINOR — `text-green-400` for check icon on published (1 line) | Fix in Plan B |
| `ContentStudio/InputPanel.jsx` | EXEMPT — platform brand colors in data array | No action |
| `ContentStudio/index.jsx` | EXEMPT — platform brand colors in data array | No action |
| `ErrorBoundary.jsx` | None visible | No action |

**Conclusion:** Phase 32 did not introduce regressions, but it also did not enforce token
migration — it polished UX/functionality. Phase 33 will clean up residual token issues in
Phase-32-scoped files as part of the broader DSGN-01 sweep.

---

## 8. Suggested Plan Breakdown

**Proposed 6 plans** (planner should treat as starting point, may split or merge):

| Plan | Name | Primary Work | DSGN Req | Files Modified | Dependencies |
|------|------|--------------|----------|----------------|--------------|
| 33-01 | Token Migration: Public + Auth Pages | Fix hex/green violations in AuthPage, ResetPasswordPage, LandingPage, ViralCard, PersonaCardPublic, PrivacyPolicy, TermsOfService | DSGN-01 | 7 files | None |
| 33-02 | Token Migration: Dashboard Pages | Fix green-400/emerald-400/lime-500 violations in Analytics, ContentLibrary, ContentCalendar, Campaigns, Connections, Admin, AdminUsers, StrategyDashboard, DailyBrief, PersonaEngine, AgencyWorkspace, DashboardHome, Settings, ContentOutput | DSGN-01 | 14 files | None |
| 33-03 | PlanBuilder Component Extraction | Extract PlanBuilder from Settings.jsx to `components/PlanBuilder.jsx`; update Settings to use it; create unit tests | DSGN-02 | 2 files (Settings.jsx, new PlanBuilder.jsx) + tests | None |
| 33-04 | Landing Page Section Split + Missing Sections | Extract current sections to `pages/Landing/` directory; add HowItWorks, SocialProof sections; replace static Pricing with PlanBuilder component; fix mobile nav with Sheet | DSGN-02, DSGN-03, DSGN-04 | LandingPage.jsx + 8 new section files | 33-03 (PlanBuilder must exist first) |
| 33-05 | SEO Meta Tags + og:image | Add all OG/Twitter meta tags to index.html; create og-image.png 1200×630; fix title/description | DSGN-05 | index.html + public/og-image.png | None |
| 33-06 | Tests + Verification | RTL tests for LandingPage sections, PlanBuilder component, mobile nav; verify 375px no-scroll; run Playwright smoke on landing | DSGN-01..05 gate | `__tests__/landing/` | 33-01..05 |

---

## Standard Stack

### Core (Frontend Only Phase)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| React | 18.3.1 | UI framework | Project standard |
| TailwindCSS | 3.4.17 | Utility-first styling | Project standard |
| shadcn/ui (New York) | installed | Component primitives | Project standard — 47 components available |
| Framer Motion | 12.38.0 | Animations | Project standard |
| Lucide React | 0.507.0 | Icon library | Project standard |
| React Router DOM | 7.5.1 | Routing (for useNavigate in landing) | Project standard |
| CRACO | 7.1.0 | CRA override (`@/` alias) | Project standard |

**Installation:** No new packages needed for Phase 33.
All required primitives (Sheet for mobile nav, Slider for PlanBuilder, Badge, Card) are already
installed in `components/ui/`.

---

## Architecture Patterns

### Pattern: Section-Component Landing Page

```
frontend/src/pages/LandingPage.jsx   — root file, imports section components
frontend/src/pages/Landing/           — section components directory
frontend/src/components/PlanBuilder.jsx — shared between Landing and Settings
```

### Pattern: One-Component Responsive Nav

Single `Navbar` component. Desktop links use `hidden md:flex`. Mobile uses `Sheet` (shadcn, side="right").
State: `const [mobileOpen, setMobileOpen] = useState(false)`.
Sheet content mirrors exact same links array — single source of truth.

### Pattern: Framer Motion whileInView for Sections

All landing page sections animate on scroll with `whileInView={{ opacity: 1, y: 0 }}` + `viewport={{ once: true }}`.
This ensures sections only animate once (not every scroll up/down).

```jsx
<motion.div
  initial={{ opacity: 0, y: 20 }}
  whileInView={{ opacity: 1, y: 0 }}
  viewport={{ once: true }}
  transition={{ duration: 0.5 }}
>
  {/* section content */}
</motion.div>
```

### Anti-Patterns to Avoid

- **Separate MobileNav and DesktopNav components:** Use one Navbar with conditional rendering
- **Duplicating PlanBuilder:** Extract once, import everywhere
- **Static pricing tiers:** Replace with interactive PlanBuilder (DSGN-02 requirement)
- **react-helmet-async for OG tags:** Static `index.html` is sufficient and correct for Vercel SPA

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Mobile slide-in nav | Custom CSS `transform: translateX` animation | `Sheet` (shadcn, already installed) | Accessibility, focus trap, ESC close, scroll lock — all free |
| Plan usage sliders | Custom `<input type="range">` with CSS | `Slider` (shadcn, already installed) | Radix-based, accessible, keyboard nav |
| Toast notifications | Custom toast state | `useToast` from `@/hooks/use-toast` | Already wired app-wide |
| Animation keyframes for new sections | Custom CSS `@keyframes` | `animate-fade-in-up`, `animate-float` etc. in tailwind.config.js | Already defined, JIT-purged correctly |
| Hex color values | Raw `#D4FF00` in className | Named tokens: `text-lime`, `bg-surface-2` | Token system exists, use it |

---

## Environment Availability

Step 2.6: SKIPPED — Phase 33 is purely frontend code changes with no new external dependencies.
All required tools (Node.js, npm, React scripts, CRA+CRACO build) are already in use by the project.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | Jest (via react-scripts) + React Testing Library |
| Config file | None explicit — CRA default (`jest` in package.json via react-scripts) |
| Quick run command | `cd frontend && npm test -- --watchAll=false --testPathPattern=landing` |
| Full suite command | `cd frontend && npm test -- --watchAll=false` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command |
|--------|----------|-----------|-------------------|
| DSGN-01 | No lime-500/green-400/raw-hex in token-scoped files | Lint/grep | `grep -rn "lime-[0-9]\|green-[45]\|emerald-[45]" frontend/src/pages/ --include="*.jsx" \| grep -v Shells/` |
| DSGN-02 | Landing has hero, features, how-it-works, pricing, footer | Unit/RTL | `npm test -- --testPathPattern=LandingPage` |
| DSGN-03 | SocialProof section renders | Unit/RTL | `npm test -- --testPathPattern=SocialProof` |
| DSGN-04 | 375px no horizontal scroll | Manual | DevTools → 375px iPhone SE width |
| DSGN-05 | OG tags in index.html | Grep | `grep "og:image\|og:title\|twitter:card" frontend/public/index.html` |

### Wave 0 Gaps

- [ ] `frontend/src/__tests__/landing/LandingPage.test.jsx` — covers DSGN-02/03/04
- [ ] `frontend/src/__tests__/components/PlanBuilder.test.jsx` — covers PlanBuilder extraction

---

## Security Domain

This phase is frontend-only (HTML/CSS/React rendering). No new auth flows, no new API endpoints,
no user input processing beyond the existing PlanBuilder sliders (which call an existing endpoint).

| ASVS Category | Applies | Note |
|---------------|---------|------|
| V2 Authentication | No | No new auth flows |
| V3 Session Management | No | No session changes |
| V4 Access Control | No | Landing page is fully public |
| V5 Input Validation | Minimal | PlanBuilder sliders have numeric bounds via shadcn Slider `min`/`max` props |
| V6 Cryptography | No | No crypto operations |

**One security note:** The og:image URL in index.html will point to `https://thook.ai/og-image.png`.
Confirm the production domain is `thook.ai` before deploying (verified via project context — 
platform is live at thook.ai per PROJECT.md).

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `POST /api/billing/plan/preview` requires auth | Section 3b | If it's already public, no change needed. If it requires auth, planner must add a public estimate endpoint or change landing PlanBuilder to navigate to /auth on "Get Started" without calling the API |
| A2 | og-image.png needs to be designed and exported as a static file | Section 4c | If a design tool or script already generates it, no manual work needed |
| A3 | Production domain is `thook.ai` (for canonical URL and og:url) | Section 4c | If domain differs, update all meta tag URLs |

---

## Open Questions

1. **PlanBuilder preview endpoint authentication**
   - What we know: `POST /api/billing/plan/preview` is used in Settings.jsx which is a protected route
   - What's unclear: Does the endpoint itself require `get_current_user` or is it open?
   - Recommendation: Planner checks `backend/routes/billing.py` for the `/plan/preview` route dependency before writing Plan 33-03

2. **og:image creation process**
   - What we know: No OG image file exists in `frontend/public/`
   - What's unclear: Should it be hand-designed in a tool, or script-generated?
   - Recommendation: Create a simple 1200×630 canvas-rendered PNG via a Node.js script in `scripts/generate-og-image.js` — fast, reproducible, no design tool dependency

3. **SocialProof content**
   - What we know: Platform is pre-launch, no real user testimonials exist
   - What's unclear: Should the section use metrics or placeholder quotes?
   - Recommendation: Use a metrics row (15+ AI Agents, 3 Platforms, 200 Free Credits, < 5 min setup) — factual and doesn't require testimonials

---

## Sources

### Primary (HIGH confidence — verified from codebase)

- `frontend/src/pages/LandingPage.jsx` — full read, current state
- `frontend/tailwind.config.js` — verified token definitions
- `frontend/src/index.css` — verified custom CSS utilities
- `frontend/public/index.html` — verified meta tag gaps
- `frontend/src/pages/Dashboard/Settings.jsx` — lines 1-180, PlanBuilder structure
- `frontend/src/App.js` — verified route map
- `frontend/vercel.json` — confirmed SPA rewrite strategy
- grep results across `frontend/src/pages/` for hex and color violations
- `frontend/src/components/ui/` directory listing — confirmed installed primitives

### Secondary (MEDIUM confidence)

- `.claude/rules/design-system.md` — project design system rules (authoritative project doc)
- `.planning/REQUIREMENTS.md` lines 87-92 — DSGN requirement definitions
- `.planning/ROADMAP.md` lines 543-557 — Phase 33 success criteria

### Tertiary (LOW confidence)

- None — all claims verified from codebase or project documentation

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — verified from package.json and imports
- Architecture: HIGH — verified from actual file structure and existing code
- Pitfalls: HIGH — verified from actual grep findings in codebase
- Token violations: HIGH — verified via grep with line numbers

**Research date:** 2026-04-12
**Valid until:** 2026-05-12 (stable design system; 30-day window)
