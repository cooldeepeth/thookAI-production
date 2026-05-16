# Design review — Day 7

**Branch:** `wedge/linkedin-only`
**Reviewed:** 2026-04-24
**Scope:** Paying-path surfaces only (LandingPage + partials, AuthPage, Onboarding, DashboardHome, ContentStudio, Settings billing).
**Excluded:** code correctness/security (in `WEDGE-AUDIT.md`), dangling routes (in `OPEN-QUESTIONS.md`).

## Theme

Day 6 simplified the backend to a single $19/mo × 500-credits wedge. The **public-facing surfaces have not caught up** — they still promote the old multi-platform, multi-tier, "15 agents" story. A visitor lands, reads value prop + pricing that promise X/Instagram and free-tier + slider-pricing, signs up, discovers LinkedIn-only flat pricing. That mismatch is the single largest wedge conversion risk right now.

All five top issues live on that mismatch.

---

## Top 5 prioritized fixes

### #1 Landing PricingSection still renders the slider PlanBuilder — Landing

- **File:** `frontend/src/pages/Landing/PricingSection.jsx:2,26` (imports + renders `<PlanBuilder mode="landing" />`)
- **Symptom:** Pricing section shows a multi-dimensional slider letting the user dial up "video credits / image credits / voice minutes" and compute a variable monthly price. The product you can actually buy post-Day-6 is a single flat $19/mo × 500 credits (`Settings.jsx:188` calls `/api/billing/wedge/checkout`).
- **Why it hurts conversion:** Prospect computes a plan, clicks "Get started", signs up, lands on a billing tab with a single tier at a different price than they configured. Immediate trust break on the most expensive step of the funnel. Some of the slider inputs (video, image, voice credits) map to features that are flagged off — the prospect is essentially building a plan for a product that doesn't exist.
- **Fix:** Replace `<PlanBuilder mode="landing" />` with a single wedge pricing card: `$19/mo`, `500 credits/month`, "1 credit per published LinkedIn post", single CTA to `/auth`. Remove the "No rigid tiers. Slide the controls…" subhead — same component; same subhead.
- **Effort:** S

### #2 Hero value prop promises LinkedIn + X + Instagram + 15 agents — Landing/Hero

- **File:** `frontend/src/pages/Landing/Hero.jsx:47–50, 87–106`
- **Symptom:** Hero body copy reads "15+ specialized AI agents… craft platform-native content for LinkedIn, X, and Instagram." A dedicated "Publishes to" row below shows three platform logos. The wedge is LinkedIn-only, 6 agents are active (commander, scout, thinker, writer, qc, anti_repetition + publisher), and X/Instagram are flagged off.
- **Why it hurts conversion:** Wrong audience self-qualifies. A content creator who mostly cares about X or IG signs up, finds no X/IG path, and churns in the trial window — inflating CAC without moving the 10-paying-user wedge goal. Also: the "15+ agents" boast reads as hype and clashes with the wedge's actual differentiator ("sounds like you, not ChatGPT"), which is never stated in the hero.
- **Fix:** Rewrite hero to foreground the wedge promise. Headline `Your Voice. LinkedIn Posts That Actually Sound Like You.` Subhead: something like `For non-native-English founders building in public. Paste 10 of your posts, we learn your voice, you publish in your voice — without sounding like ChatGPT.` Drop the "15+ agents" boast. Replace the three-platform logo row with a single LinkedIn logo or remove it.
- **Effort:** S

### #3 Trust line and SocialProof metrics state facts that aren't true — Landing

- **Files:**
  - `frontend/src/pages/Landing/Hero.jsx:82` — "50 free credits on signup · No credit card for Free tier"
  - `frontend/src/pages/Landing/SocialProof.jsx:3–8` — `[{value:"15+",label:"Specialist AI Agents"}, {value:"3",label:"Social Platforms"}, {value:"200",label:"Free Credits to Start"}, {value:"< 5 min",label:"To Your First Post"}]`
- **Symptom:** The trust row below the primary CTA, and the "By the numbers" strip mid-page, both advertise a free tier (50 or 200 starter credits) and "3 Social Platforms". Neither is true post-Day-6: wedge is a single paid tier, LinkedIn only.
- **Why it hurts conversion:** Post-signup reveal that the free tier doesn't exist feels like bait. "3 Social Platforms" is a concrete, provable false claim on the homepage; flagged-off routes in the codebase prove it. This is the class of detail that makes the rest of the page untrustworthy.
- **Fix:** Delete the "50 free credits" line under the hero CTA (or replace with "7-day money-back guarantee" if we can honour it). Rewrite the four SocialProof tiles to wedge-truthful stats: e.g. `6` Specialist Agents, `LinkedIn` Platform, `500 cr/mo` At $19, `< 5 min` To first post. Or cut the section entirely until we have real proof-worthy numbers.
- **Effort:** XS

### #4 DashboardHome quick-actions include X, Instagram, and a dead route — Dashboard first paint

- **File:** `frontend/src/pages/Dashboard/DashboardHome.jsx:12–17`
- **Symptom:** A freshly-paid user's first authed screen renders four equal-weight quick-action cards: "Write a LinkedIn post", "Write an X thread", "Instagram caption", "Repurpose content". Three of four go to flagged-off surfaces or unregistered routes (`/dashboard/repurpose` has no `<Route>`, per `WEDGE-AUDIT.md`).
- **Why it hurts conversion:** First post-pay moment should be the crispest CTA of the whole product. Instead the user sees four options, three of which either disappear into non-wedge shells or bounce them to the landing page. Even if they pick "Write a LinkedIn post", the noise of the other three dilutes trust.
- **Fix:** Collapse the quick-actions strip to one primary card — "Write a LinkedIn post" — rendered large, plus an optional secondary card for "Import 10 more posts to sharpen your voice". Delete the X, Instagram, Repurpose entries and the `upcomingFeatures` strip (`:19–23`) — it advertises Voice Cloning which is explicitly deferred.
- **Effort:** XS

### #5 Hero "Early Bird Launch — Save up to 38%" badge is unanchored — Landing/Hero

- **File:** `frontend/src/pages/Landing/Hero.jsx:23–29`
- **Symptom:** The top-of-hero pill reads `Early Bird Launch — Save up to 38% for a limited time`. Post-Day-6 we have one price: $19/mo. There is no anchor for the 38% figure; PricingSection (see #1) shows a slider, not a "was/now" comparison. A prospect who notices the pill and looks for the discount cannot find it.
- **Why it hurts conversion:** A percentage discount a user can't locate reads as either a bug or a dark pattern. It also competes with the real message ("your voice, LinkedIn posts that sound like you") for the user's first 2 seconds.
- **Fix:** Either delete the pill entirely, or replace with a concrete, anchored offer that maps to the single tier (e.g. `Launch pricing — $19/mo until 30 June. Lock in forever.`). Do not ship a discount claim that can't be found on the pricing card.
- **Effort:** XS

---

## Notable-but-lower-priority

- **Auth page has no social proof near the form** (`AuthPage.jsx` left column): a line of "Trusted by N founders building in public" or a single testimonial would improve signup conversion; first-time visitors arrive with zero trust anchor. Effort XS.
- **Onboarding PhaseOne silent fallback looks identical to real analysis** (already in `WEDGE-AUDIT.md`, but visual impact is also bad): user sees "Posts noted. We'll use them to calibrate your voice." with no indication whether analysis actually ran. Add a visible "analysis failed — retry" state. Effort S.
- **Hero platform-logos row still shows LinkedIn + X + Instagram icons** (`Hero.jsx:87–106`); aligns with #2 but worth a separate commit for diff clarity. Effort XS.
- **PricingSection subhead contradicts itself** (`PricingSection.jsx:22`): `No rigid tiers. Slide the controls to match your content needs` — the new wedge has precisely one rigid tier. Gets fixed with #1 but call it out so the writer doesn't reuse the string. Effort XS.
- **"15+ Specialist AI Agents" tile** is repeated in SocialProof and implied by the hero copy — both are the same false claim. Pair the fix with #3. Effort XS.

---

## Implementation order for Day 8 (if/when we pick this up)

1. Fix #1 — blocks signup at the pricing step.
2. Fix #2 + #3 + #5 + notable bullet #4 — one commit, all landing-page copy. Biggest conversion impact per hour.
3. Fix #4 — one-file commit, changes first post-pay screen to reflect wedge.
4. Lower-priority items folded in opportunistically.

All five top fixes together are < 4 hours of work and touch 4 files. The value is that the public surfaces finally tell the same story the product now delivers — which is the precondition for any honest conversion measurement during the wedge validation window.
