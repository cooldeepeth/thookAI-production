# ThookAI v3.0 — Platform Rebuild: Distribution-Ready

## CLI Session Initialization Prompt

Copy everything below the `---` line and paste it into a fresh Claude Code CLI terminal.

---

```
/gsd:new-milestone

Milestone Name: v3.0 — Distribution-Ready Platform Rebuild
Milestone Goal: Take ThookAI from "code exists" to "every feature works perfectly, every edge case handled, industry-grade security, polished UI" — ready for real users at scale.

## CRITICAL CONTEXT — READ BEFORE ANYTHING

You are rebuilding ThookAI, an AI-powered content creation platform. The codebase has 571 commits, 181 backend Python files, 37 frontend pages, 47 UI components, 83 test files. It is DEPLOYED and LIVE at:
- Frontend: https://www.thook.ai (Vercel)
- Backend: https://gallant-intuition-production-698a.up.railway.app (Railway)
- MongoDB Atlas, Railway Redis, Cloudflare R2, Stripe (sandbox), Sentry, PostHog

The platform has significant code but many hidden bugs, broken flows, edge cases, and incomplete features. Your job is to find and fix EVERYTHING.

## YOUR APPROACH

You are NOT building new features. You are making EXISTING features work perfectly.

**Decision authority: AUTONOMOUS.** When you find something that needs a design decision (UX, architecture, flow), make the best decision yourself and implement it. Document decisions in .planning/DECISIONS.md.

**Verification standard:** Every fix must be tested against the LIVE production deployment. Use curl for API testing. Use gstack/browser tools for frontend testing. Use Sentry MCP to monitor for new errors. Use PostHog MCP to verify user flows.

**Commit standard:** Atomic commits after every logical fix. Never batch unrelated fixes. Conventional commits (fix:, feat:, refactor:, test:, perf:, security:).

## PHASE BREAKDOWN

Generate phases from this taxonomy. Each phase should be 1 CLI session (~2-4 hours of work). Use /gsd:discuss-phase --auto before planning each phase.

### LAYER 1: DEEP AUDIT (Phases 1-3)
The goal is to build a complete understanding of every line of code before changing anything.

**Phase 1: Backend API Audit**
Read EVERY file in backend/routes/ (26 files). For each file:
- List every endpoint (method, path, auth requirement, request model, response shape)
- Test every endpoint against production with curl
- Log: working / broken / partially working / untested
- Check: input validation, error handling, auth guard, credit check, rate limit
- Check: does the response match what the frontend component expects?
- Output: .planning/audit/BACKEND-API-AUDIT.md — complete endpoint registry with status

Files to read: auth.py, auth_google.py, auth_social.py, password_reset.py, onboarding.py, persona.py, content.py, dashboard.py, platforms.py, repurpose.py, analytics.py, billing.py, viral.py, agency.py, templates.py, media.py, uploads.py, notifications.py, webhooks.py, campaigns.py, uom.py, viral_card.py, n8n_bridge.py, strategy.py, obsidian.py, admin.py

**Phase 2: Frontend Flow Audit**
Read EVERY page and component. For each:
- What API endpoints does it call?
- What state does it manage?
- Test in browser: does it load? does it handle errors? empty states? loading states?
- Check responsive: desktop (1440px), tablet (768px), mobile (375px)
- Check accessibility: keyboard navigation, screen reader, color contrast
- Log every visual bug, broken interaction, missing state
- Output: .planning/audit/FRONTEND-FLOW-AUDIT.md — complete page registry with status

Pages to audit: LandingPage, AuthPage, ResetPasswordPage, Onboarding (PhaseOne/Two/Three), Dashboard (Home, ContentStudio, ContentLibrary, PersonaEngine, Settings, Connections, Templates, TemplateDetail, Analytics, Campaigns, ContentCalendar, DailyBrief, StrategyDashboard, RepurposeAgent, Admin, AdminUsers, AgencyWorkspace, ComingSoon), ViralCard, Public/PersonaCardPublic

Components to audit: MediaUploader, NotificationBell, PersonaShareModal, TemplateCard, CampaignCard, VoiceCloneCard, ErrorBoundary, Sidebar, TopBar

**Phase 3: Agent Pipeline & Services Audit**
Read EVERY agent and service file. For each:
- What does it do? What LLM calls does it make? What prompts does it use?
- Is the prompt efficient? Clear? Does it produce quality output?
- What error handling exists? What happens when the LLM fails?
- What credit cost does it have? Is it deducted correctly?
- Output: .planning/audit/AGENT-PIPELINE-AUDIT.md

Agents to audit: commander.py, scout.py, thinker.py, writer.py, qc.py, designer.py, video.py, voice.py, publisher.py, analyst.py, anti_repetition.py, learning.py, repurpose.py, series_planner.py, strategist.py, viral_predictor.py, visual.py, orchestrator.py, planner.py, consigliere.py, capos/*.py

Services to audit: llm_client.py, llm_keys.py, credits.py, stripe_service.py, subscriptions.py, media_storage.py, media_orchestrator.py, creative_providers.py, email_service.py, notification_service.py, persona_refinement.py, social_analytics.py, vector_store.py, lightrag_service.py, agent_accuracy.py, obsidian_service.py, uom_service.py, webhook_service.py

### LAYER 2: BACKEND FIX (Phases 4-8)
Fix everything found in the audit, backend first.

**Phase 4: Auth & User Management — Bulletproof**
Fix every auth edge case. The complete list:
- Registration: validation, duplicate handling, password policy, email verification
- Login: lockout, auth method check, JWT creation, cookie setting
- Google OAuth: callback handling, account linking, error states
- LinkedIn/X OAuth: callback handling, account creation, token storage
- Password reset: email sending, token validation, password change
- Session management: JWT expiry, refresh, logout, session invalidation
- GDPR: data export, account deletion, data anonymization
- Profile: update name, email, picture, password change
Test EVERY flow against production. Test EVERY edge case.

**Phase 5: Content Pipeline — End-to-End Quality**
Fix the content creation flow from input to published post:
- Content creation form → API call → pipeline → job status → result display
- Fix: job polling, WebSocket/SSE for real-time updates, timeout handling
- Fix: persona-aware content (verify persona is loaded and used)
- Fix: platform-specific formatting (LinkedIn vs X vs Instagram)
- Fix: content editing, approval, scheduling
- Fix: repurposing flow (content → repurpose to other platforms)
- Fix: series planning flow
- Test with 10+ real content generation requests

**Phase 6: Billing & Credits — Zero Leakage**
Fix every billing edge case:
- Plan builder: real-time price calculation, correct credit mapping
- Checkout: Stripe session creation, redirect, return handling
- Webhook: payment success → subscription activation → credit grant
- Credit deduction: atomic, no double-charge, refund on failure
- Credit display: always current, low-balance warning, usage history
- Subscription: upgrade, downgrade, cancel, resume
- Invoice history, payment methods
- Test with Stripe test cards (4242... success, 4000... decline)

**Phase 7: Media & File Management — Upload to Delivery**
Fix the media pipeline:
- File upload: presigned URL flow OR server-proxy flow (pick one, remove the other)
- R2 CORS: configure bucket for browser uploads
- Image generation: test with DALL-E, FAL.ai
- Video generation: test with available providers
- Voice generation: test with ElevenLabs, OpenAI TTS
- Carousel generation: test end-to-end
- Media display: images, videos, audio players in content preview
- Media in published posts: verify media publishes with content

**Phase 8: Platform Connections & Publishing**
Fix social media integration:
- LinkedIn: OAuth connect, token storage, token refresh, publish post
- X/Twitter: OAuth connect, token storage, publish tweet/thread
- Instagram: OAuth connect (Meta), token storage, publish post
- Token encryption: verify Fernet encryption works in production
- Token refresh: automatic refresh before expiry
- Publish flow: scheduled post → publisher agent → platform API → confirm
- Analytics: poll published post metrics (simulated if API not connected)

### LAYER 3: SECURITY HARDENING (Phases 9-10)

**Phase 9: Security — Penetration-Test Ready**
- Input validation: every POST endpoint has Pydantic models with field constraints
- XSS prevention: sanitize all text inputs stored in DB
- MongoDB injection: verify no string interpolation in queries
- CSRF: verify every state-changing endpoint is protected
- Rate limiting: tune per endpoint, add per-user limits
- Auth bypass: test every protected endpoint without auth
- Privilege escalation: test accessing other users' data
- File upload security: validate file types, scan for malware patterns
- API key exposure: grep for any hardcoded secrets
- Error information leakage: no stack traces in production responses
- Dependency audit: check for known vulnerabilities in requirements.txt and package.json
Output: .planning/audit/SECURITY-AUDIT.md with findings and fixes

**Phase 10: GDPR & Privacy — Compliance Ready**
- Cookie consent: implement consent banner (PostHog requires consent in EU)
- Privacy policy: create /privacy page
- Terms of service: create /terms page
- Data processing agreement: document what data is stored and why
- Data export: verify GET /api/auth/export returns all user data
- Account deletion: verify DELETE /api/auth/account anonymizes everything
- Data retention: implement auto-cleanup of old data
- PII in logs: audit all logging for personal data leakage
- Third-party data sharing: document what goes to Stripe, PostHog, Sentry, LLM providers

### LAYER 4: FRONTEND REBUILD (Phases 11-17)

**Phase 11: Design System Foundation**
Use /ui-ux-pro-max skill. Before touching any page:
- Audit current Tailwind config, color palette, typography, spacing
- Define a consistent design system: colors, fonts, spacing, border radius, shadows
- Create/update UIComponents.jsx with standardized primitives
- Define animation constants (Framer Motion presets)
- Define responsive breakpoints and behavior
- Create a component style guide in .planning/DESIGN-SYSTEM.md

**Phase 12: Landing Page — First Impression**
Rebuild LandingPage.jsx to be conversion-optimized:
- Hero: clear value prop, CTA, animated demo/preview
- Features: visualize the 5-agent pipeline
- How it works: 3-step flow (onboard → generate → publish)
- Pricing: interactive plan builder (connect to billing/plan/preview API)
- Social proof: placeholder testimonials section
- Footer: links, legal, social
- Mobile-first, fast loading, SEO meta tags
Test in browser at all breakpoints.

**Phase 13: Auth & Onboarding — Seamless Start**
Rebuild auth and onboarding for zero-friction experience:
- AuthPage: clean login/register tabs, social login buttons, password validation inline
- Onboarding PhaseOne: questions with progress indicator, save-as-you-go
- Onboarding PhaseTwo: post analysis (optional), paste old posts
- Onboarding PhaseThree: persona generation with real-time progress, result preview
- Smooth transitions between phases
- Skip/back navigation
- Error recovery at every step

**Phase 14: Content Studio — Core Product Experience**
Rebuild ContentStudio as the flagship feature:
- InputPanel: topic input, platform selector, content type, template picker, media options
- Real-time credit cost preview before generating
- AgentPipeline: live progress through Commander→Scout→Thinker→Writer→QC
- ContentOutput: platform-specific preview (LinkedIn/X/Instagram shells)
- Edit mode: inline editing with character count, formatting
- Media panel: attach images, generate images, add carousel
- Action bar: approve, schedule, publish now, export, repurpose
- Job history: previous generations with re-use option

**Phase 15: Dashboard & Analytics — Data Visibility**
Rebuild dashboard pages:
- DashboardHome: key stats cards, recent activity, strategy recommendations
- ContentLibrary: grid/list view toggle, filters, search, bulk actions
- Analytics: charts (use Recharts), trends, platform comparison
- ContentCalendar: calendar view of scheduled posts
- DailyBrief: AI-generated daily content strategy
- StrategyDashboard: proactive recommendations from Strategist agent

**Phase 16: Settings & Account Management**
Rebuild Settings.jsx:
- Profile tab: name, email, picture upload, password change
- Billing tab: current plan, plan builder, credit balance, payment history
- Connections tab: platform connect/disconnect with status
- Notifications tab: email preferences, in-app notification settings
- Team tab (if agency): member management, roles, invitations
- Data tab: export data, delete account

**Phase 17: Remaining Pages**
Fix all remaining pages:
- Templates: browse, filter, preview, use in content studio
- RepurposeAgent: select content → choose platforms → generate variants
- Campaigns: create campaign, add content, track performance
- PersonaEngine: view/edit persona, voice samples, style preferences
- Admin: user management, stats, system health (admin-only)
- ViralCard / PersonaCardPublic: public shareable cards

### LAYER 5: PERFORMANCE & POLISH (Phases 18-20)

**Phase 18: Backend Performance**
- Profile every endpoint: identify >500ms responses
- Add database query optimization (compound indexes, projections)
- Add response caching for expensive/static endpoints
- Optimize LLM calls: reduce token usage, add caching for similar prompts
- Add pagination to all list endpoints
- Connection pool tuning (MongoDB, Redis)
- Memory profiling of Celery worker

**Phase 19: Frontend Performance**
- Bundle analysis: identify large dependencies
- Code splitting by route (lazy load dashboard pages)
- Image optimization: lazy loading, WebP, responsive sizes
- API call optimization: debounce search, cancel stale requests
- Skeleton loading states on all pages
- Service worker for offline indicator
- Lighthouse score: aim for 90+ on all metrics

**Phase 20: Final Polish & E2E Test**
- Error boundary on every page (ErrorBoundary.jsx)
- 404 page for unknown routes
- Offline/network error handling
- Browser tab title per page
- Favicon and meta tags
- Open Graph tags for social sharing
- Comprehensive E2E test: register → onboard → generate → schedule → publish
- Load test: 50 concurrent users (use backend/tests/load/locustfile.py)
- Cross-browser test: Chrome, Firefox, Safari, Mobile Safari
- Final security scan
- Pre-launch checklist completion

## TOOLS & MCPs TO USE

For EVERY phase, use these proactively:

| Tool | When |
|------|------|
| code-review-graph MCP | Before changing any file — understand impact radius |
| Sentry MCP | After every deploy — check for new errors |
| PostHog MCP | After frontend changes — verify user flow tracking |
| Stripe MCP | During billing work — verify live Stripe state |
| Vercel MCP | After frontend deploys — verify deployment status |
| Figma MCP | During UI work — generate and review designs |
| /ui-ux-pro-max skill | During all frontend phases — design system guidance |
| /gstack skill | For browser testing — verify frontend flows |
| /caveman skill | When context is getting long — compress to save tokens |
| /engineering:code-review | After each phase — validate code quality |
| /engineering:testing-strategy | Before writing tests — plan test coverage |
| /design:design-critique | After UI changes — validate design decisions |
| /design:accessibility-review | After UI changes — WCAG compliance |

## REQUIREMENTS

### Non-Functional Requirements (apply to ALL phases)
- NFR-1: Every API endpoint responds in <500ms (p95)
- NFR-2: Every page loads in <3s on 3G connection
- NFR-3: Zero unhandled exceptions in production (Sentry clean)
- NFR-4: 80%+ test coverage on critical paths
- NFR-5: WCAG 2.1 AA accessibility compliance
- NFR-6: GDPR compliance (data export, deletion, consent)
- NFR-7: Rate limiting on all endpoints (prevent abuse)
- NFR-8: Input validation on all user inputs (prevent injection)
- NFR-9: Responsive design: works on 375px-2560px screens
- NFR-10: Works in Chrome, Firefox, Safari, Edge (latest 2 versions)

### Success Criteria
The milestone is COMPLETE when:
1. A new user can: register → onboard → generate content → schedule → publish — with zero errors
2. Billing works: subscribe → get credits → use credits → buy more → cancel
3. All 3 platforms work: LinkedIn, X, Instagram (connect, generate, publish)
4. Security audit passes with zero CRITICAL or HIGH findings
5. Lighthouse performance score >90 on all pages
6. Sentry shows zero unresolved errors for 48 hours
7. Load test passes: 50 concurrent users, <2s response time

## CODEBASE INVENTORY

### Backend (181 files, Python 3.11, FastAPI)
- 26 route files (auth, content, billing, platforms, media, etc.)
- 21 agent files (commander, scout, thinker, writer, qc, designer, video, voice, etc.)
- 18 service files (llm_client, credits, stripe, media_storage, etc.)
- 4 middleware files (security, performance, csrf, redis_client)
- 83 test files
- Entry: backend/server.py → uvicorn
- Config: backend/config.py (dataclass-based, reads .env)
- DB: backend/database.py (Motor async MongoDB)
- Tasks: backend/tasks/ (Celery + Beat)

### Frontend (118 files, React 18, CRA + CRACO)
- 37 page files across 7 top-level pages + 21 dashboard views
- 47 shadcn/ui components + 7 custom components
- 3 hooks, 6 lib files, 1 context (AuthContext)
- Entry: frontend/src/App.js
- API client: frontend/src/lib/api.js (apiFetch with CSRF, retry, timeout)
- Config: frontend/src/lib/constants.js

### Infrastructure
- Railway: backend + Celery worker+beat (single process)
- Vercel: frontend (auto-deploy from main)
- MongoDB Atlas: database
- Railway Redis: Celery broker + rate limiting + caching
- Cloudflare R2: media storage
- Stripe: billing (sandbox mode)
- Sentry: error tracking (thook org, python project)
- PostHog: analytics (frontend integrated)

Now generate the ROADMAP.md with all 20 phases, then start Phase 1.
```
