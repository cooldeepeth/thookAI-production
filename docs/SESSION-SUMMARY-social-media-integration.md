# ThookAI Session Summary — Social Media Integration Deep Dive
**Date:** April 9, 2026 | **Session:** Terminal Claude Code (read-only analysis)

---

## 1. What We Did This Session

### 1.1 Observed In-Progress Work (VS Code Session)
Checked the other Claude Code session running in VS Code. Found:
- **Active plan:** "Ship-First Launch Plan" (`virtual-giggling-flute.md`) — 7-phase, ~10-day plan to ship ThookAI
- **Uncommitted changes across 11 files** — executing Phase 1 (Critical Blockers) and Phase 2 (High/Medium Fixes):
  - `backend/agents/pipeline.py` — global pipeline timeout
  - `backend/agents/publisher.py` — real publishing replacing stubs
  - `backend/celeryconfig.py` — Celery beat config
  - `backend/tasks/content_tasks.py` — wiring publishing, stale job cleanup (biggest change: +175/-74 lines)
  - `backend/routes/platforms.py` — ENCRYPTION_KEY enforcement
  - `backend/server.py` — startup validation
  - `frontend/src/pages/LandingPage.jsx` — demo video placeholder fix
  - `frontend/src/pages/Dashboard/Sidebar.jsx`, `TopBar.jsx`, `index.jsx` — mobile responsive sidebar
- **No changes were made** — pure observation only

### 1.2 Deep Analysis: Social Media Integration Status
Ran 3 parallel exploration agents to audit the full social media stack across OAuth, publishing, scheduling, and persona building.

### 1.3 Developer API Setup Guide
Researched current (2025-2026) API requirements, pricing, and step-by-step setup for all 3 platforms.

---

## 2. Social Media Feature — Current State

### What's Already Built (and works)

| Component | Status | Key Files |
|-----------|--------|-----------|
| **LinkedIn OAuth** | Fully implemented (OAuth 2.0) | `backend/routes/platforms.py` (lines 137-248) |
| **X/Twitter OAuth** | Fully implemented (OAuth 2.0 + PKCE) | `backend/routes/platforms.py` (lines 251-412) |
| **Instagram OAuth** | Fully implemented (Meta OAuth) | `backend/routes/platforms.py` (lines 415-550) |
| **Token encryption** | Fernet AES — production-ready | `backend/routes/platforms.py` (lines 64-82) |
| **Token refresh** | LinkedIn + X auto-refresh; Instagram manual (60-day token) | `backend/routes/platforms.py` (lines 579-632) |
| **Platform status API** | Returns connection status for all 3 | `GET /api/platforms/status` |
| **Frontend Connections UI** | Full card-based UI with connect/disconnect/reconnect | `frontend/src/pages/Dashboard/Connections.jsx` (373 lines) |
| **LinkedIn publishing** | Real API — text posts via `/v2/ugcPosts` | `backend/agents/publisher.py` |
| **X publishing** | Real API — tweets + threads with reply chaining | `backend/agents/publisher.py` |
| **Instagram publishing** | Real API — image posts (2-step: container → publish) | `backend/agents/publisher.py` |
| **Scheduling** | Celery Beat every 5 min, processes due posts | `backend/tasks/content_tasks.py`, `backend/celeryconfig.py` |
| **Content Calendar UI** | Calendar grid with scheduled post dots | `frontend/src/pages/Dashboard/ContentCalendar.jsx` |
| **Optimal posting times** | Platform peaks + UOM burnout-aware suggestions | Planner agent |
| **Post-publish analytics** | Auto-polls metrics at 24h and 7d after publish | `backend/tasks/content_tasks.py` |
| **Bulk import (manual)** | Up to 100 posts via paste/CSV | `backend/agents/learning.py` (line 343) |
| **Persona from interview** | 7-question onboarding → Claude generates persona card | `backend/routes/onboarding.py` |
| **Optional post analysis** | Users paste posts → Claude extracts writing patterns | `/onboarding/analyze-posts` |
| **Vector store** | Pinecone integration implemented (not wired to writer) | `backend/services/vector_store.py` |
| **Learning system** | Edit deltas, approval/rejection patterns, voice evolution | `backend/agents/learning.py`, `backend/services/persona_refinement.py` |

### What's NOT Built (the gaps)

| Missing Feature | Impact | Difficulty |
|----------------|--------|------------|
| **Fetch user's past posts FROM platforms** | Can't auto-import for persona building | Medium (2-3 weeks) |
| **Fetch profile metadata** (bio, followers) | No social proof data in persona | Easy (1-2 days) |
| **LinkedIn post history reading** | **Blocked by API** — requires partner program | Cannot build (free tier limitation) |
| **LinkedIn media upload** | Only text posts work, no images | Medium (2-3 days) |
| **Instagram text-only posts** | Instagram requires an image for every post | Platform limitation — not fixable |
| **Instagram token auto-refresh** | 60-day tokens expire silently | Easy (1 day) |
| **Schedule editing** | Users can't edit scheduled-but-unpublished posts | Easy (1-2 days) |
| **Post analytics exposed to frontend** | Backend fetches metrics but no UI to display | Medium (2-3 days) |
| **Data model sync** | Celery reads `scheduled_posts`, frontend reads `content_jobs` — two unsynchronized collections | Medium (needs architectural decision) |

---

## 3. Exact API Endpoints Used by ThookAI

### LinkedIn
| Action | Method | URL | Scope |
|--------|--------|-----|-------|
| OAuth authorize | GET | `linkedin.com/oauth/v2/authorization` | — |
| Token exchange | POST | `linkedin.com/oauth/v2/accessToken` | — |
| Get profile | GET | `api.linkedin.com/v2/userinfo` | `openid profile email` |
| Create post | POST | `api.linkedin.com/v2/ugcPosts` | `w_member_social` |
| Get engagement | GET | `api.linkedin.com/v2/socialActions/{urn}` | `w_member_social` |
| Get impressions | GET | `api.linkedin.com/v2/organizationalEntityShareStatistics` | `w_member_social` |

### X/Twitter
| Action | Method | URL | Scope |
|--------|--------|-----|-------|
| OAuth authorize | GET | `twitter.com/i/oauth2/authorize` (PKCE) | — |
| Token exchange | POST | `api.twitter.com/2/oauth2/token` | — |
| Get user | GET | `api.twitter.com/2/users/me` | `users.read` |
| Create tweet | POST | `api.twitter.com/2/tweets` | `tweet.write` |
| Get metrics | GET | `api.twitter.com/2/tweets/{id}?tweet.fields=public_metrics` | `tweet.read` |

### Instagram/Meta
| Action | Method | URL | Scope |
|--------|--------|-----|-------|
| OAuth authorize | GET | `facebook.com/v18.0/dialog/oauth` | — |
| Token exchange | GET | `graph.facebook.com/v18.0/oauth/access_token` | — |
| Long-lived token | GET | `graph.facebook.com/v18.0/oauth/access_token` (fb_exchange_token) | — |
| Get pages | GET | `graph.facebook.com/v18.0/me/accounts` | `pages_show_list` |
| Get IG account | GET | `graph.facebook.com/v18.0/{page_id}?fields=instagram_business_account` | `instagram_basic` |
| Create container | POST | `graph.facebook.com/v18.0/{ig_id}/media` | `instagram_content_publish` |
| Poll status | GET | `graph.facebook.com/v18.0/{container_id}?fields=status_code` | `instagram_content_publish` |
| Publish | POST | `graph.facebook.com/v18.0/{ig_id}/media_publish` | `instagram_content_publish` |
| Get insights | GET | `graph.facebook.com/v18.0/{media_id}/insights` | `instagram_basic` |

---

## 4. Developer API Setup — What You Need

### LinkedIn (Easiest — Free, Instant)
1. Create LinkedIn Company Page for ThookAI
2. Create app at developer.linkedin.com
3. Enable **"Sign In with LinkedIn using OpenID Connect"** + **"Share on LinkedIn"** (self-serve, no review)
4. Add redirect URLs, copy Client ID + Secret
5. Set `LINKEDIN_CLIENT_ID` and `LINKEDIN_CLIENT_SECRET`

**Limitation:** Cannot fetch user's post history (requires partner-level access). Workaround: manual paste during onboarding.

### X/Twitter (Pay-Per-Use — Cheap, Same Day)
1. Apply at developer.x.com
2. Create Project + App, permissions: "Read and Write"
3. Enable OAuth 2.0 with PKCE, type: "Web App" (Confidential client)
4. Add callback URLs, copy OAuth 2.0 Client ID + Secret
5. Add prepaid credits ($10-50 for testing)
6. Set `TWITTER_API_KEY` and `TWITTER_API_SECRET`

**Tier recommendation:** Pay-Per-Use (~$0.01/post write, ~$0.005/read). Avoid Free tier (no refresh tokens). Basic ($200/mo) only if you need heavy tweet history reading.

### Instagram/Meta (Most Complex — Free, 1-4 Weeks)
1. Set up Meta Business Suite at business.facebook.com
2. Create Meta Developer App at developers.facebook.com
3. Add Instagram API product → choose "API setup with Instagram Login"
4. Configure OAuth redirect URIs + data deletion callback
5. Complete **Business Verification** (documents, domain DNS verification — 1-5 business days)
6. Submit **App Review** with screencast video showing every permission in action
7. After approval, switch to Live Mode
8. Set `META_APP_ID` and `META_APP_SECRET`

**Critical:** Personal Instagram accounts have zero API access. Users must have Business or Creator accounts. Your app should detect and guide conversion.

### Cost Summary

| Platform | API Cost | Time to Access |
|----------|---------|---------------|
| LinkedIn | Free | Instant |
| X/Twitter | ~$0.01/post (Pay-Per-Use) | Same day |
| Instagram | Free | 1-4 weeks (App Review) |

---

## 5. Persona Building from Social Data — Strategy

### What Works Today
- **Onboarding interview** (7 questions) → Claude generates persona card
- **Manual post paste** → `/onboarding/analyze-posts` extracts patterns
- **Bulk import** → `learning.py` accepts up to 100 posts (supports `linkedin_export`, `twitter_archive` sources)
- **Edit learning** → system tracks how users modify AI content to refine persona over time
- **Vector store** → Pinecone ready for embedding indexed posts

### What Needs Building for Auto-Import

| Phase | Work | Effort |
|-------|------|--------|
| **Post fetching service** | New `backend/services/social_import.py` — fetch timelines from X and Instagram APIs | 3-5 days |
| **Background processing** | Celery task: fetch → deduplicate → analyze → embed → store in Pinecone | 2-3 days |
| **Enhanced persona generation** | Feed imported posts into persona prompt, extract hooks/vocabulary/tone | 3-4 days |
| **UI integration** | "Import from platform" button in onboarding, progress tracking | 2-3 days |
| **Total** | | ~2-3 weeks |

### Per-Platform Feasibility

| Platform | Auto-Import Possible? | How |
|----------|----------------------|-----|
| LinkedIn | **No** (API restriction) | Manual paste or LinkedIn data export CSV |
| X/Twitter | **Yes** | `GET /2/users/:id/tweets` via Pay-Per-Use (~$0.005/tweet) |
| Instagram | **Yes** (after App Review) | `GET /{user_id}/media` returns all posts |

### Launch Recommendation
1. Ship with manual paste + CSV upload (already works)
2. Post-launch: build X tweet fetching first (cheapest, most creator-relevant data)
3. After Meta App Review: add Instagram post import
4. LinkedIn: guide users to export their data via LinkedIn Settings

---

## 6. Ship-First Launch Plan (from VS Code session)

The other session has a 7-phase plan being executed:

| Phase | What | Status |
|-------|------|--------|
| 0 | Merge M1-M3 PR #25 (CI/CD, Docker, config, rate limiting) | Ready to merge |
| 1 | Fix critical blockers (publishing stubs, pipeline timeout, encryption key) | **In progress** (uncommitted changes) |
| 2 | Fix high/medium issues (Stripe payments, subscriptions, credits, mobile sidebar) | **In progress** (uncommitted changes) |
| 3 | Polish (session expiry, empty states, error boundary, skeleton loaders) | Planned |
| 4 | E2E testing (auth, pipeline, publishing, billing) | Planned |
| 5 | Deploy (Render backend, Vercel frontend, 35 env vars) | Planned |
| 6 | Post-launch monitoring (Sentry, health checks, Flower) | Planned |
| 7 | Post-launch features (analytics, import, templates, vector store, voice clone) | Planned |

**Target:** ~10 days to ship

---

## 7. Code Architecture Notes (for new session context)

### Key Patterns
- **Config:** All settings via `backend/config.py` dataclasses. Never `os.environ.get()` directly.
- **Database:** Always `from database import db` with Motor async. Never synchronous PyMongo.
- **Auth:** JWT via `get_current_user()` dependency. Tokens in localStorage.
- **LLM:** `backend/services/llm_client.py` wraps Anthropic/OpenAI/Gemini. Use `claude-sonnet-4-20250514`.
- **Agents:** All export `async def run_agent(input_data, context) -> dict`
- **Pipeline:** Commander → Scout → Thinker → Writer → QC (orchestrated in `backend/agents/pipeline.py`)

### Key Files for Social Media
```
backend/routes/platforms.py       # 631 lines — all OAuth flows + token mgmt
backend/agents/publisher.py       # 440 lines — real publishing per platform
backend/tasks/content_tasks.py    # Celery tasks — scheduling, publishing, metrics
backend/agents/learning.py        # Bulk import + learning signals
backend/services/social_analytics.py  # Post-publish metrics fetching
backend/services/persona_refinement.py # Persona evolution from user actions
backend/services/vector_store.py  # Pinecone — embedding storage/query
backend/routes/onboarding.py      # 7-question interview + persona generation
frontend/src/pages/Dashboard/Connections.jsx  # 373 lines — connect UI
frontend/src/pages/Dashboard/ContentCalendar.jsx  # Calendar + scheduling UI
```

### Environment Variables for Social Media
```bash
# LinkedIn (free, instant)
LINKEDIN_CLIENT_ID=
LINKEDIN_CLIENT_SECRET=

# X/Twitter (pay-per-use or $200/mo)
TWITTER_API_KEY=              # OAuth 2.0 Client ID
TWITTER_API_SECRET=           # OAuth 2.0 Client Secret

# Instagram/Meta (free, requires App Review)
META_APP_ID=
META_APP_SECRET=

# Token encryption (required in production)
ENCRYPTION_KEY=               # python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

---

## 8. Known Issues / Tech Debt (relevant to social features)

1. **LinkedIn uses legacy `/v2/ugcPosts`** — should migrate to `/rest/posts` (Posts API)
2. **Instagram uses Facebook Login path** — consider switching to Instagram Login path (simpler, no Facebook Page required)
3. **Instagram has no token auto-refresh** — 60-day tokens expire silently, user must reconnect
4. **No token revocation on disconnect** — only deletes local record, platform token stays valid
5. **Data model split** — `scheduled_posts` vs `content_jobs` are unsynchronized collections
6. **Instagram polling blocks Celery worker** — 60-second blocking loop should be async
7. **X thread rate limiting** — 0.5s delay between tweets may not be sufficient under load
8. **LinkedIn media upload not implemented** — only text posts work

---

## 9. Decisions Made / Recommendations

| Decision | Recommendation | Rationale |
|----------|---------------|-----------|
| API tier for X | Pay-Per-Use | Cheapest for launch volume (~$0.01/post) |
| Instagram OAuth path | Keep Facebook Login for now, switch to Instagram Login post-launch | Less code change pre-launch |
| LinkedIn post import | Manual paste + CSV export guide | API restriction, not fixable |
| Persona building priority | Ship with interview-based, add auto-import post-launch | Not a launch blocker |
| Setup order | LinkedIn + X Day 1, Instagram ASAP (App Review bottleneck) | Instagram takes 1-4 weeks |
| Post history for persona | X tweets first, Instagram posts second | X has richest text data for voice analysis |

---

## 10. Memory Index (Cross-Session Context)

From persistent memory (`MEMORY.md`):
- **Founder:** Solo founder (Kuldeepsinh), full PRD vision, debt-first approach, GSD methodology
- **GTM:** Soft launch, freemium, $100-500/mo, targeting solo creators/founders
- **Pricing:** Custom plan builder with starter credits, replaces 4-tier model
- **Framework:** Open to LangChain or best framework for agent orchestration
- **Tooling:** All 6 phases installed (ui-ux-pro-max, superpowers, ECC rules, claude-mem, obsidian-skills, n8n-mcp)
- **Team agents:** /team:* commands with 3 specialists (backend/frontend/AI) on top of GSD
- **Multi-language:** Indian languages via Sarvam AI, global languages planned for later milestones
- **TRIBE v2:** Neural scoring deferred to v3.0 (requires GPU infra)
- **Workspace:** MCPs, skills, Notion hub, project directory all configured
