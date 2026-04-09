# ThookAI Hardening Plan — Distribution-Ready Platform

## How to Use This Document

This is a **multi-session execution plan** for a fresh Claude Code CLI terminal.
Each session starts by pasting the session prompt into the CLI.
Sessions are designed to be independent — each leaves the platform in a deployable state.

**Prerequisites for every session:**

- Run from repo root: `cd ~/thookAI-production`
- All MCPs connected (Stripe, Sentry, Vercel, Figma, PostHog, Notion, Gmail)
- Railway backend running at `https://gallant-intuition-production-698a.up.railway.app`
- Vercel frontend at `https://www.thook.ai`

---

## Session 0: Full Codebase Audit (run first, one time)

Paste this into a fresh Claude Code CLI:

```
/gsd:new-milestone

Milestone: v3.0 — Production Hardening & Distribution-Ready

Read CLAUDE.md, HARDENING-PLAN.md, and .planning/PROJECT.md completely.
Then run a comprehensive audit of the entire ThookAI platform.

## What to Audit

### Backend (63 dependencies, 22 agents, 27 routes, 19 services)
For EVERY file in backend/routes/*.py, backend/agents/*.py, backend/services/*.py:
1. Read every endpoint. Test it with curl against production.
2. Check: does it handle errors? validate input? check auth? deduct credits?
3. Check: does the response match what the frontend expects?
4. Log every broken endpoint, missing validation, unhandled error.

### Frontend (118 files, 7 pages, 47 UI components, 21 dashboard views)
For EVERY file in frontend/src/pages/, frontend/src/components/:
1. Read the component. Check: what API does it call? Does that endpoint exist?
2. Check: error states handled? loading states? empty states? responsive?
3. Check: does it handle auth expiry? network errors? large data?
4. Log every broken flow, missing state, UI issue.

### Agent Pipeline (22 agents)
Test the full pipeline: Commander -> Scout -> Thinker -> Writer -> QC
1. Generate content for LinkedIn, X, Instagram — check output quality
2. Check prompt engineering — are prompts efficient? Do they hallucinate?
3. Check anti-repetition — does it actually prevent duplicate content?
4. Check credit deduction — is it atomic? are refunds working on failure?

### Security Audit
1. All auth flows (email, Google, LinkedIn, X) — test edge cases
2. Input sanitization on every POST endpoint
3. Rate limiting configuration — is it appropriate per endpoint?
4. CORS configuration — verify all origins
5. Secret management — any hardcoded values?
6. MongoDB injection prevention — parameterized queries?
7. XSS prevention in any HTML rendering
8. CSRF protection verification on every state-changing endpoint

### Database Audit
1. Check all indexes in db_indexes.py match what's needed
2. Check for missing indexes (slow queries)
3. Check for data consistency issues
4. Check TTL indexes are working
5. Verify all collections have proper schema validation

### Infrastructure Audit
1. Railway: worker process running? Beat scheduler active?
2. Redis: connection pooling? memory usage?
3. R2: CORS configured for browser uploads?
4. Stripe: webhook endpoint registered? All events handled?
5. Sentry: capturing errors? Performance monitoring?
6. PostHog: events being tracked? Session recording working?

## Output
Create .planning/AUDIT-REPORT.md with:
- Every bug found (severity: CRITICAL/HIGH/MEDIUM/LOW)
- Every edge case identified
- Every missing feature that blocks launch
- Prioritized fix list grouped into phases
- Estimated session count per phase

Also update .planning/ROADMAP.md with the hardening phases.
```

---

## Session 1: Backend API Hardening (M1-Phase-1)

```
Read CLAUDE.md, HARDENING-PLAN.md, and .planning/AUDIT-REPORT.md.
Use /gsd:execute-phase for the current phase.

## Mission: Make every backend API endpoint bulletproof.

### Step 1: Fix all broken endpoints
Use the audit report. For each broken endpoint:
1. Read the route code
2. Identify the bug
3. Fix it
4. Test with curl against production
5. Commit

### Step 2: Input validation on every POST/PUT/PATCH endpoint
For every route in backend/routes/*.py:
- Add Pydantic request models where missing
- Add field validators (min/max length, format, enum)
- Add rate-appropriate limits (e.g., content field max 50000 chars)
- Return 422 with clear field-level errors

### Step 3: Error handling standardization
Every endpoint must:
- Return consistent error format: {"detail": "message", "code": "ERROR_CODE"}
- Never leak stack traces in production
- Log errors with context (user_id, endpoint, params)
- Return appropriate HTTP status codes (not generic 500)

### Step 4: Auth guard audit
For every endpoint: verify get_current_user dependency is applied.
Check: are any endpoints accidentally public that should be protected?

### Step 5: Test each fix
Run backend/tests/ after all changes.
Hit every fixed endpoint against production with curl.
Commit with clear messages per fix.
```

---

## Session 2: Backend API Hardening (M1-Phase-2)

```
Read CLAUDE.md, .planning/AUDIT-REPORT.md. Use /gsd:execute-phase.

## Mission: Agent pipeline quality + credit system integrity.

### Step 1: Content pipeline audit
Generate 5 test posts (LinkedIn, X, Instagram, carousel, thread).
For each:
- Check Commander output — is the job spec correct?
- Check Scout output — is research relevant?
- Check Thinker output — is the angle/hook good?
- Check Writer output — is the content publishable quality?
- Check QC output — does it catch real issues?
Record quality scores and identify weak agents.

### Step 2: Prompt engineering improvements
For each agent in backend/agents/:
- Read the system prompt
- Check: is it too long? too vague? does it hallucinate?
- Optimize: clearer instructions, better examples, structured output
- Add output validation (JSON schema check on agent responses)

### Step 3: Credit system integrity
- Verify atomic deduction (no double-charge on retry)
- Verify refund on pipeline failure
- Verify credit check before every expensive operation
- Test: what happens at exactly 0 credits?
- Test: concurrent requests that both check balance
- Verify monthly refresh logic

### Step 4: Onboarding flow
Test the full flow: questions -> analyze posts -> generate persona
- Does persona generation use correct LLM model? (check for claude-4-sonnet bug)
- Is the persona stored correctly?
- Does the dashboard reflect onboarding status?

Commit all fixes. Run tests.
```

---

## Session 3: Security Hardening (M2)

```
Read CLAUDE.md, .planning/AUDIT-REPORT.md. Use /gsd:execute-phase.

## Mission: Make the platform penetration-test ready.

### Step 1: GDPR compliance
- Add privacy policy endpoint or page
- Add data export endpoint (GET /api/user/export — returns all user data as JSON)
- Add account deletion endpoint (DELETE /api/user/account — soft delete + anonymize)
- Add cookie consent mechanism (PostHog requires consent in EU)
- Verify no PII in logs (check all logger.info/warning/error calls)
- Add data retention policy (auto-delete old data per schedule)

### Step 2: Auth hardening
- Add account lockout after 5 failed login attempts (15 min cooldown)
- Add session invalidation on password change
- Add suspicious login detection (new device/location)
- Verify JWT tokens can't be reused after logout
- Add HTTPS-only cookie flags in production

### Step 3: Rate limiting tuning
Review backend/middleware/security.py RateLimitMiddleware:
- Auth endpoints: 5/min (currently 10 — too high)
- Content generation: 10/min (currently 20)
- General API: 60/min (reasonable)
- File uploads: 10/min
- Billing endpoints: 5/min
- Add per-user rate limiting (not just per-IP)

### Step 4: Input sanitization
- Add HTML stripping on all text inputs (prevent stored XSS)
- Add MongoDB injection prevention (check all raw query constructions)
- Add path traversal prevention on file operations
- Add request size limits per endpoint type
- Validate all URL inputs (uploads, callbacks)

### Step 5: Security headers audit
Review backend/middleware/security.py SecurityHeadersMiddleware:
- Verify CSP is appropriate
- Add Permissions-Policy
- Verify HSTS max-age
- Add X-Content-Type-Options

### Step 6: Stripe security
- Verify webhook signature verification is working
- Verify no price manipulation (server-side price calculation only)
- Verify subscription status checks before feature access
- Add Stripe event idempotency checks

Commit all fixes. Run security-focused tests.
```

---

## Session 4: Frontend Audit & Fix (M3-Phase-1)

```
Read CLAUDE.md, .planning/AUDIT-REPORT.md. Use /gsd:execute-phase.
Use Figma MCP to inspect current design and propose improvements.
Use gstack skill for browser testing.

## Mission: Fix every broken frontend flow.

### Step 1: Auth flow (AuthPage.jsx)
Test in browser:
- Register with email → should redirect to onboarding
- Login with email → should redirect to dashboard
- Google OAuth → should work end-to-end
- Forgot password → should send email and reset work
- Edge: wrong password → clear error message
- Edge: existing email → clear error message
- Edge: weak password → validation errors shown
- Edge: network error → graceful handling
Fix every issue found.

### Step 2: Onboarding flow (Onboarding/*.jsx)
Test PhaseOne → PhaseTwo → PhaseThree:
- All 7 questions render and accept input
- Analyze posts works (if user provides them)
- Persona generation completes and shows result
- User is marked as onboarded
- Redirect to dashboard works
Fix every issue found.

### Step 3: Dashboard (Dashboard/*.jsx)
Test every dashboard page:
- DashboardHome: stats load, recommendations show
- ContentStudio: create content flow works end-to-end
- ContentLibrary: past content shows, edit/delete works
- PersonaEngine: persona displays, edit works
- Settings: profile edit, billing, plan builder all work
- Connections: platform connect flows work
- Templates: browse, use template works
- Analytics: charts render, data loads
Fix every broken page.

### Step 4: Error states
For every page, verify:
- Loading spinner shows during API calls
- Error message shows on API failure
- Empty state shows when no data
- Refresh/retry button available on errors

### Step 5: Responsive design
Test every page at:
- Desktop (1440px)
- Tablet (768px)
- Mobile (375px)
Fix layout breaks, overflow, touch targets.

Commit all fixes. Test in browser.
```

---

## Session 5: Frontend Enhancement (M3-Phase-2)

```
Read CLAUDE.md, .planning/AUDIT-REPORT.md. Use /gsd:execute-phase.
Use /ui-ux-pro-max skill for design system improvements.
Use Figma MCP for design reference.

## Mission: Elevate the UI from "works" to "impressive".

### Step 1: Design system audit
Using /ui-ux-pro-max:
- Audit current color palette, typography, spacing
- Check consistency across all pages
- Identify visual hierarchy issues
- Check dark mode readiness (if applicable)
- Propose improvements with specific Tailwind changes

### Step 2: Landing page (LandingPage.jsx)
The landing page is the first impression. Make it:
- Hero section: clear value prop, CTA, social proof
- Features section: 5-agent pipeline visualized
- Pricing section: interactive plan builder
- Testimonials (placeholder for now)
- Footer with links
Must be conversion-optimized and fast-loading.

### Step 3: Content Studio UX
The core product experience. Improve:
- Content creation form: better UX, real-time credit cost display
- Generated content preview: platform-specific rendering
- Edit flow: inline editing with character count
- Scheduling: calendar view, time picker
- Media generation: progress indicators, preview

### Step 4: Billing UX
- Plan builder: real-time price calculation as sliders move
- Checkout: smooth Stripe redirect and return
- Credit balance: always visible, low-balance warning
- Usage history: clear credit transaction log

### Step 5: Toast notifications
Ensure Sonner toasts are used consistently:
- Success: green, auto-dismiss 3s
- Error: red, persistent until dismissed
- Info: blue, auto-dismiss 5s
- Loading: with spinner, dismiss on completion

### Step 6: Animations
Add subtle Framer Motion animations:
- Page transitions
- Card hover effects
- Content generation progress
- Skeleton loading states

Commit all improvements. Screenshot before/after.
```

---

## Session 6: Agent Pipeline Optimization (M4)

```
Read CLAUDE.md, .planning/AUDIT-REPORT.md. Use /gsd:execute-phase.

## Mission: Make generated content actually publishable.

### Step 1: LLM client audit
Read backend/services/llm_client.py:
- Is streaming implemented correctly?
- Are timeouts appropriate? (30s for short, 120s for long generation)
- Is retry logic solid? (exponential backoff)
- Is the fallback chain working? (Claude → OpenAI → mock)
- Is token usage tracked for cost monitoring?

### Step 2: Writer agent prompt optimization
The Writer is the most important agent. Optimize:
- LinkedIn: hooks, formatting, hashtags, CTA
- X/Twitter: thread structure, character limits, engagement bait avoidance
- Instagram: caption style, emoji usage, hashtag strategy
- Test with 10 different topics and score output quality

### Step 3: Media generation pipeline
Test each provider:
- Image: OpenAI DALL-E, FAL.ai — which produces better results?
- Video: Luma, Runway — test with actual prompts
- Voice: ElevenLabs, OpenAI TTS — quality comparison
- Carousel: test slide generation quality
Document which providers to prioritize.

### Step 4: Anti-repetition system
Read backend/agents/anti_repetition.py:
- Does it actually prevent similar hooks/angles?
- Is the similarity threshold appropriate?
- Does it check against user's recent content?

### Step 5: Publishing flow
Test end-to-end: generate → approve → schedule → publish
- LinkedIn publishing via API
- X publishing via API
- Instagram publishing via API
- Verify media attachments publish correctly

Commit all improvements. Generate sample content to verify.
```

---

## Session 7: Performance & Monitoring (M5)

```
Read CLAUDE.md, .planning/AUDIT-REPORT.md. Use /gsd:execute-phase.

## Mission: Production-grade performance and observability.

### Step 1: API performance
- Profile slow endpoints (>500ms)
- Add database query optimization (check explain plans)
- Add response caching where appropriate
- Optimize serialization (avoid re-fetching full documents)
- Add pagination to all list endpoints

### Step 2: Frontend performance
- Bundle size analysis (npm run build -- --stats)
- Code splitting by route
- Image optimization (lazy loading, WebP)
- Remove unused dependencies
- Add service worker for offline support (optional)

### Step 3: Monitoring setup
- Sentry: verify error grouping, set up alerts
- PostHog: verify event tracking, set up funnels
- Add uptime monitoring (Railway health check)
- Add API latency tracking (already have TimingMiddleware)
- Set up error budget alerts

### Step 4: Database optimization
- Review all indexes for query patterns
- Add compound indexes for common queries
- Check for N+1 query patterns
- Add connection pool monitoring
- Set up slow query alerts

### Step 5: Edge case handling
For every feature, test:
- What happens with 0 items?
- What happens with 1000 items?
- What happens with special characters in input?
- What happens with very long input?
- What happens with concurrent requests?
- What happens when external API is down?

### Step 6: Pre-launch checklist
- [ ] All endpoints return correct responses
- [ ] All frontend flows complete without errors
- [ ] Error tracking captures all unhandled errors
- [ ] Rate limiting prevents abuse
- [ ] GDPR compliance implemented
- [ ] Stripe live mode tested
- [ ] DNS/SSL configured correctly
- [ ] Backup strategy in place
- [ ] Incident response plan documented

Commit all improvements. Run final E2E test.
```

---

## Quick Reference: What's Already Working

| Component          | Status     | Notes                                           |
| ------------------ | ---------- | ----------------------------------------------- |
| Backend deployed   | Working    | Railway, all services connected                 |
| Frontend deployed  | Working    | Vercel at thook.ai                              |
| Auth (email)       | Working    | CORS fixed, bcrypt fixed                        |
| Auth (Google)      | Working    | Authlib OAuth                                   |
| Auth (LinkedIn/X)  | Code ready | Needs OAuth app credentials                     |
| Onboarding         | Partially  | Persona generation needs LLM model fix          |
| Content generation | Working    | Pipeline runs, credits deducted                 |
| Billing (Stripe)   | Working    | Sandbox mode, checkout flows work               |
| Templates          | Working    | 20 templates seeded                             |
| Scheduled tasks    | Working    | Celery Beat, 10 tasks configured                |
| Media uploads      | Partially  | CSRF fixed, R2 configured, needs CORS on bucket |
| Image generation   | Code ready | Needs provider API keys                         |
| Video generation   | Code ready | Needs provider API keys                         |
| Voice generation   | Code ready | Needs ElevenLabs key                            |

## Changes Made in Current Session (April 10, 2026)

1. Fixed Railway $PORT expansion → python server.py
2. Deferred slow startup tasks to background
3. Fixed CompressionMiddleware duplicate Content-Length → auth 502
4. Replaced passlib with direct bcrypt
5. Fixed CORS rejecting frontend origin
6. Fixed DB_NAME default mismatch
7. Added LinkedIn + X social login (auth_social.py)
8. Restored Celery Beat (10 scheduled tasks, no n8n needed)
9. Fixed OAuth silent account hijack (auth_method check)
10. Fixed missing credit deduction in sync fallback (4 endpoints)
11. Fixed index name conflict (Sentry error)
12. Fixed registration race condition (DuplicateKeyError)
13. Enforced PasswordPolicy on registration + reset
14. Fixed MediaUploader CSRF token on XHR
15. Fixed confirm_upload IDOR vulnerability
16. Added media_assets indexes
