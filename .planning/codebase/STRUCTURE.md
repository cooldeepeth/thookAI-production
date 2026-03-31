# Codebase Structure

**Analysis Date:** 2026-03-31

## Directory Layout

```
thookAI-production/
├── backend/                    # FastAPI Python backend (entry: server.py)
│   ├── server.py              # FastAPI app initialization, middleware, router registration
│   ├── config.py              # Settings dataclasses, environment configuration
│   ├── database.py            # MongoDB Motor async client, connection pooling
│   ├── db_indexes.py          # MongoDB index definitions (auto-run at startup)
│   ├── auth_utils.py          # JWT, password hashing, auth dependency
│   ├── celery_app.py          # Celery app configuration with Redis broker
│   ├── celeryconfig.py        # Celery beat schedule configuration
│   ├── Procfile               # Production start commands (uvicorn, worker, beat)
│   ├── requirements.txt       # Python dependencies
│   ├── runtime.txt            # Python version (3.11)
│   │
│   ├── agents/                # Multi-agent AI pipeline
│   │   ├── pipeline.py        # Orchestrator: runs agents in sequence
│   │   ├── commander.py       # Agent: parse intent, build strategy
│   │   ├── scout.py           # Agent: research (Perplexity API)
│   │   ├── thinker.py         # Agent: angle/hook selection, anti-repetition
│   │   ├── writer.py          # Agent: final content generation (Claude)
│   │   ├── qc.py              # Agent: quality control, compliance
│   │   ├── publisher.py       # Agent: platform publishing (LinkedIn, X, Instagram)
│   │   ├── learning.py        # Agent: persona refinement, feedback capture
│   │   ├── analyst.py         # Agent: analytics and performance insights
│   │   ├── anti_repetition.py # Agent: pattern fatigue detection
│   │   ├── viral_predictor.py # Agent: hook scoring, virality prediction
│   │   ├── designer.py        # Agent: AI image generation (fal.ai, DALL-E)
│   │   ├── video.py           # Agent: video generation (Luma, Kling, Runway)
│   │   ├── voice.py           # Agent: TTS/voice generation (ElevenLabs)
│   │   ├── visual.py          # Agent: brand asset and visual brief management
│   │   ├── repurpose.py       # Agent: cross-platform content repurposing
│   │   ├── series_planner.py  # Agent: multi-post series planning
│   │   ├── consigliere.py     # Agent: strategic advisor (strategy refinement)
│   │   ├── orchestrator.py    # Agent: advanced orchestration logic
│   │   └── planner.py         # Agent: content planning helper
│   │
│   ├── routes/                # FastAPI route handlers (all mounted under /api)
│   │   ├── auth.py            # POST /auth/register, /auth/login
│   │   ├── auth_google.py     # POST /auth/google/callback (Google OAuth)
│   │   ├── password_reset.py  # POST /reset-password, token validation
│   │   ├── onboarding.py      # POST /onboarding/answers, persona generation
│   │   ├── persona.py         # GET/POST/DELETE /persona, sharing, export
│   │   ├── content.py         # POST /content/create, GET /content/{id}, status updates
│   │   ├── dashboard.py       # GET /dashboard/stats, feed, recommendations
│   │   ├── platforms.py       # POST /platforms/{platform}/connect (OAuth), GET /platforms/status
│   │   ├── repurpose.py       # POST /content/repurpose, /content/series
│   │   ├── analytics.py       # GET /analytics/overview, trends, persona evolution
│   │   ├── billing.py         # POST /billing/checkout, webhook, portal, subscription status
│   │   ├── viral.py           # POST /viral/score-hooks, GET /viral/variants
│   │   ├── agency.py          # POST /agency/workspace, members, invitations
│   │   ├── templates.py       # GET /templates (marketplace), POST /templates (create)
│   │   ├── media.py           # GET/DELETE /media/{asset_id}
│   │   ├── uploads.py         # POST /uploads (file/URL), GET /uploads/{id}
│   │   ├── notifications.py   # GET /notifications (SSE or polling)
│   │   ├── webhooks.py        # POST /webhooks/stripe (billing webhooks)
│   │   ├── campaigns.py       # POST/GET /campaigns (project grouping)
│   │   ├── admin.py           # GET /admin/users, /admin/stats (admin only)
│   │   ├── uom.py             # GET/POST /uom (Unit of Measure configuration)
│   │   └── viral_card.py      # GET /viral-card/{share_token} (viral sharing card)
│   │
│   ├── services/              # Reusable business logic and integrations
│   │   ├── llm_client.py      # LlmChat: unified LLM wrapper (Anthropic/OpenAI/Gemini)
│   │   ├── llm_keys.py        # Provider availability checks, key validation
│   │   ├── credits.py         # Credit system: deduction, tier config, operation tracking
│   │   ├── stripe_service.py  # Stripe checkout, webhook handling, subscription mgmt
│   │   ├── subscriptions.py   # Subscription tier validation, feature access
│   │   ├── media_storage.py   # Cloudflare R2 upload/download, S3-compatible API
│   │   ├── vector_store.py    # Pinecone wrapper: embedding store/search
│   │   ├── persona_refinement.py  # Persona evolution, pattern fatigue shield
│   │   ├── email_service.py   # Resend API: password reset, invitations
│   │   ├── social_analytics.py    # Platform metrics aggregation
│   │   ├── creative_providers.py  # Image/video/voice provider abstraction
│   │   ├── notification_service.py  # In-app notification management
│   │   ├── webhook_service.py     # Outbound webhook firing
│   │   ├── agent_accuracy.py      # Agent performance metrics
│   │   └── uom_service.py         # Unit of Measure definitions
│   │
│   ├── tasks/                 # Celery async tasks
│   │   ├── content_tasks.py   # Tasks: process_scheduled_posts, reset_daily_limits, cleanup_old_jobs, aggregate_analytics
│   │   └── media_tasks.py     # Tasks: generate_image, generate_voice, generate_video (async)
│   │
│   ├── middleware/            # FastAPI middleware
│   │   ├── security.py        # SecurityHeadersMiddleware, RateLimitMiddleware, InputValidationMiddleware
│   │   ├── performance.py     # CompressionMiddleware, CacheMiddleware, TimingMiddleware
│   │   └── redis_client.py    # Redis connection for rate limiting backend
│   │
│   ├── scripts/               # One-off scripts (data migration, seeding, admin tasks)
│   │   └── seed_templates.py  # (To be created) Seed community template marketplace
│   │
│   └── tests/                 # Test suite
│       └── [test files]       # Unit/integration tests
│
├── frontend/                  # React SPA (Create React App + CRACO)
│   ├── src/
│   │   ├── App.js            # Main app component, routing, provider setup
│   │   ├── index.js          # React entry point
│   │   ├── index.css         # Global styles
│   │   │
│   │   ├── context/          # React context providers
│   │   │   └── AuthContext.jsx    # JWT auth, user state, login/logout
│   │   │
│   │   ├── hooks/            # Custom React hooks
│   │   │   ├── useAuth.js    # Hook: get auth context
│   │   │   ├── useAPI.js     # Hook: HTTP calls with error handling
│   │   │   └── [others]
│   │   │
│   │   ├── pages/            # Page components (route-level)
│   │   │   ├── LandingPage.jsx    # Public landing page
│   │   │   ├── AuthPage.jsx       # Login/register
│   │   │   ├── ResetPasswordPage.jsx # Password reset flow
│   │   │   ├── ViralCard.jsx      # Shared viral card preview
│   │   │   ├── Dashboard/         # Protected dashboard (requires auth)
│   │   │   │   ├── index.jsx      # Dashboard layout with sidebar/topbar
│   │   │   │   ├── Sidebar.jsx    # Navigation sidebar
│   │   │   │   ├── TopBar.jsx     # Header with user menu
│   │   │   │   ├── PersonaEngine.jsx      # Persona card creation/editing
│   │   │   │   ├── ContentStudio/         # Content generation studio
│   │   │   │   │   ├── AgentPipeline.jsx  # Multi-stage generation UI
│   │   │   │   │   ├── Shells/            # Style templates for generation
│   │   │   │   │   └── [generation views]
│   │   │   │   ├── ContentLibrary.jsx     # View all generated content
│   │   │   │   ├── ContentCalendar.jsx    # Schedule/calendar view
│   │   │   │   ├── Analytics.jsx         # Performance metrics dashboard
│   │   │   │   ├── RepurposeAgent.jsx    # Cross-platform repurposing
│   │   │   │   ├── Campaigns.jsx         # Campaign/project grouping
│   │   │   │   ├── Templates.jsx         # Community template marketplace
│   │   │   │   ├── TemplateDetail.jsx    # Template detail view
│   │   │   │   ├── Connections.jsx       # OAuth platform connections
│   │   │   │   ├── Settings.jsx          # User settings and preferences
│   │   │   │   ├── AgencyWorkspace/      # Multi-user workspace
│   │   │   │   │   └── index.jsx         # Workspace management
│   │   │   │   ├── Admin.jsx             # Admin dashboard (admin only)
│   │   │   │   ├── AdminUsers.jsx        # User management (admin only)
│   │   │   │   └── ComingSoon.jsx        # Placeholder for future features
│   │   │   └── Public/                   # Public routes (no auth required)
│   │   │       └── PersonaCardPublic.jsx # Public persona card view
│   │   │
│   │   ├── components/        # Reusable components
│   │   │   ├── ui/            # shadcn/ui components (dialog, button, input, etc.)
│   │   │   │   ├── dialog.jsx
│   │   │   │   ├── button.jsx
│   │   │   │   ├── input.jsx
│   │   │   │   ├── form.jsx
│   │   │   │   ├── menubar.jsx
│   │   │   │   ├── avatar.jsx
│   │   │   │   ├── toggle-group.jsx
│   │   │   │   ├── command.jsx
│   │   │   │   ├── radio-group.jsx
│   │   │   │   ├── breadcrumb.jsx
│   │   │   │   ├── calendar.jsx
│   │   │   │   ├── switch.jsx
│   │   │   │   ├── carousel.jsx
│   │   │   │   ├── context-menu.jsx
│   │   │   │   ├── skeleton.jsx
│   │   │   │   ├── textarea.jsx
│   │   │   │   ├── select.jsx
│   │   │   │   ├── dropdown-menu.jsx
│   │   │   │   ├── collapsible.jsx
│   │   │   │   ├── checkbox.jsx
│   │   │   │   ├── toast.jsx
│   │   │   │   ├── toggle.jsx
│   │   │   │   └── UIComponents.jsx (ToastProvider)
│   │   │   ├── ErrorBoundary.jsx    # Error boundary wrapper
│   │   │   ├── [feature components]  # Custom components (ContentCard, etc.)
│   │   │   └── [layout components]   # Layout components (Modal, Card, etc.)
│   │   │
│   │   └── lib/               # Utilities and helpers
│   │       ├── api.js         # API client configuration, HTTP helpers
│   │       ├── utils.js       # Common utilities (formatting, parsing)
│   │       └── [other utilities]
│   │
│   ├── public/                # Static assets (favicon, manifest, etc.)
│   ├── craco.config.js        # CRA override config (path aliases @/, TailwindCSS)
│   ├── tailwind.config.js     # TailwindCSS configuration
│   ├── postcss.config.js      # PostCSS setup for TailwindCSS
│   ├── components.json        # shadcn/ui component registry
│   ├── vercel.json            # Vercel deployment config (SPA routing)
│   ├── package.json           # NPM dependencies
│   └── .env.example           # Environment variables template
│
├── remotion-service/          # Separate Node.js service for Remotion video rendering
│   └── [video rendering setup]
│
├── memory/                    # Agent memory/context files
│   └── [memory snapshots]     # Do not auto-delete
│
├── docs/                      # Documentation
│   └── [various docs]
│
├── docker-compose.yml         # Docker Compose for local dev (MongoDB, Redis)
├── CLAUDE.md                  # Agent briefing (authoritative for all Claude sessions)
├── README.md                  # Project overview
├── AUDIT_REPORT.md            # System audit results
└── .planning/                 # GSD planning artifacts
    └── codebase/              # Architecture documents
        ├── ARCHITECTURE.md    # (this file)
        ├── STRUCTURE.md       # Directory structure and file locations
        ├── CONVENTIONS.md     # Code style and naming patterns
        ├── TESTING.md         # Test framework and patterns
        ├── STACK.md           # Technology stack
        ├── INTEGRATIONS.md    # External API integrations
        └── CONCERNS.md        # Technical debt and issues
```

## Directory Purposes

**backend/**
- Purpose: Python FastAPI application serving REST API endpoints
- Contains: Routes, services, agents, middleware, database configuration
- Key files: `server.py` (entry point), `config.py` (settings), `database.py` (MongoDB)

**backend/agents/**
- Purpose: AI agent pipeline for multi-stage content generation
- Contains: Specialized agents (commander, writer, qc, etc.), orchestration logic
- Key files: `pipeline.py` (orchestrator), `writer.py` (LLM-powered content generation)

**backend/routes/**
- Purpose: HTTP endpoint handlers grouped by business domain
- Contains: Request/response models, route handlers, authorization checks
- Key files: `content.py` (content generation), `auth.py` (authentication), `billing.py` (Stripe)

**backend/services/**
- Purpose: Reusable business logic and external API integrations
- Contains: LLM client, credit system, Stripe wrapper, media storage, vector embeddings
- Key files: `llm_client.py` (LLM abstraction), `credits.py` (credit system), `stripe_service.py` (billing)

**backend/tasks/**
- Purpose: Celery async tasks for background processing
- Contains: Scheduled tasks (post publishing, cleanup), media generation
- Key files: `content_tasks.py` (scheduled posts), `media_tasks.py` (async media generation)

**backend/middleware/**
- Purpose: Cross-cutting HTTP concerns (security, rate limiting, compression)
- Contains: Middleware classes for all requests/responses
- Key files: `security.py` (headers, rate limiting, validation)

**frontend/src/**
- Purpose: React SPA source code
- Contains: Pages, components, hooks, context, utilities
- Key files: `App.js` (routing), `index.js` (entry point), `context/AuthContext.jsx` (auth state)

**frontend/src/pages/**
- Purpose: Top-level route components
- Contains: Page layouts, page-level logic
- Key files: `Dashboard/index.jsx` (dashboard layout), `Dashboard/ContentStudio/` (generation UI)

**frontend/src/components/**
- Purpose: Reusable UI components
- Contains: shadcn/ui library components, custom feature components
- Key files: `ui/` (design system), `ErrorBoundary.jsx` (error handling)

**memory/**
- Purpose: Agent memory and context snapshots
- Contains: Persistent memory files (do not auto-delete)
- Pattern: Used by agents for learning and context between sessions

## Key File Locations

**Entry Points:**
- `backend/server.py`: FastAPI app initialization and middleware setup
- `frontend/src/App.js`: React router and provider setup
- `frontend/src/index.js`: React DOM rendering

**Configuration:**
- `backend/config.py`: All settings dataclasses (environment-driven)
- `frontend/src/context/AuthContext.jsx`: Frontend auth configuration
- `frontend/craco.config.js`: Path aliases and build config

**Core Logic:**
- `backend/agents/pipeline.py`: Content generation orchestration
- `backend/routes/content.py`: Content creation endpoint
- `backend/services/llm_client.py`: LLM provider abstraction
- `backend/services/credits.py`: Credit deduction and tier logic
- `frontend/src/pages/Dashboard/ContentStudio/`: Generation UI

**Testing:**
- `backend/tests/`: Test files (pytest)
- No frontend tests currently tracked

**Authentication:**
- `backend/auth_utils.py`: JWT token handling, password hashing
- `backend/routes/auth.py`: Login/register endpoints
- `frontend/src/context/AuthContext.jsx`: Client-side auth state

**Database:**
- `backend/database.py`: MongoDB Motor async client
- `backend/db_indexes.py`: MongoDB index definitions
- Collections: users, personas, content_jobs, scheduled_posts, platform_tokens, etc.

## Naming Conventions

**Files:**
- Python files: `snake_case.py` (e.g., `content_tasks.py`, `auth_utils.py`)
- React files: `PascalCase.jsx` (e.g., `AuthContext.jsx`, `Dashboard.jsx`)
- Utilities: `camelCase.js` (e.g., `api.js`, `utils.js`)
- Config files: `lowercase.config.js` (e.g., `craco.config.js`, `tailwind.config.js`)

**Directories:**
- Backend modules: lowercase (e.g., `agents/`, `services/`, `routes/`)
- React components: `PascalCase` for feature/page directories (e.g., `Dashboard/`, `ContentStudio/`)
- Utilities: lowercase (e.g., `ui/`, `hooks/`, `lib/`)

**Functions:**
- Backend async functions: `async def run_agent_name(...)` (agents), `async def handler_name(...)` (routes)
- Frontend hooks: `useHookName()` (e.g., `useAuth()`, `useAPI()`)
- Utilities: `camelCase()` (e.g., `formatDate()`, `parseJSON()`)

**Variables:**
- Backend: `snake_case` for variables, `UPPER_CASE` for constants
- Frontend: `camelCase` for variables and functions, `UPPER_CASE` for constants
- React components: `PascalCase` for component names, `camelCase` for props

**Types & Models:**
- Pydantic models: `PascalCase` (e.g., `ContentCreateRequest`, `PersonaCard`)
- MongoDB collections: `lowercase_plural` (e.g., `users`, `content_jobs`, `persona_engines`)
- TypeScript/JSDoc: `PascalCase` for types (when used)

## Where to Add New Code

**New Feature (API endpoint):**
1. Create or extend route handler in `backend/routes/[domain].py`
2. Define Pydantic request/response models in the same file
3. Add database operations (queries/writes) directly or via services
4. If adding business logic: create service in `backend/services/[service].py`
5. Tests: Add to `backend/tests/test_[domain].py`

**New Component/Module:**
- Frontend component: Add to `frontend/src/components/[FeatureName].jsx`
- Frontend hook: Add to `frontend/src/hooks/use[HookName].js`
- Backend service: Add to `backend/services/[service].py`
- Backend agent: Add to `backend/agents/[agent_name].py` and wire into pipeline

**Utilities:**
- Frontend utility: Add to `frontend/src/lib/[utility].js`
- Backend utility: Add to `backend/[utility].py` or new `backend/services/[utility].py`

**Async Tasks:**
- Long-running task: Add function to `backend/tasks/[domain]_tasks.py`
- Decorate with `@shared_task` and call via `.delay()` from route handlers
- Register in Celery beat schedule in `backend/celeryconfig.py`

**Database:**
- New collection: Declare as `db.collection_name` when first used
- Indexes: Add to `backend/db_indexes.py` create_indexes() function
- Migrations: Manual (MongoDB has no migrations; alter schema at runtime)

## Special Directories

**backend/.pytest_cache/**
- Purpose: Pytest cache for test discovery
- Generated: Yes (created by pytest on first run)
- Committed: No (in .gitignore)

**backend/__pycache__/**
- Purpose: Python bytecode cache
- Generated: Yes (created by Python interpreter)
- Committed: No (in .gitignore)

**frontend/node_modules/**
- Purpose: NPM package dependencies
- Generated: Yes (created by npm install)
- Committed: No (in .gitignore)

**frontend/build/**
- Purpose: Production build output
- Generated: Yes (created by npm run build)
- Committed: No (in .gitignore)

**memory/**
- Purpose: Agent memory and context snapshots
- Generated: Yes (created by learning agents)
- Committed: Yes (intentionally committed for persistence)
- Policy: Do not auto-delete; used across sessions

**.planning/codebase/**
- Purpose: GSD mapping artifacts (architecture, structure, conventions, testing)
- Generated: Yes (created by /gsd:map-codebase command)
- Committed: Yes (these are reference documents for future Claude instances)

## Build & Deployment Structure

**Backend Deployment:**
- Entry: `uvicorn server:app --host 0.0.0.0 --port 8001` (from Procfile)
- Workers: `celery -A celery_app worker --loglevel=info` (background tasks)
- Scheduler: `celery -A celery_app beat --loglevel=info` (scheduled tasks)
- Platform: Render/Railway/Heroku with Procfile

**Frontend Deployment:**
- Build: `npm run build` (CRA with CRACO override)
- Output: `frontend/build/` (SPA static files)
- Platform: Vercel (configured in `vercel.json`)
- Routing: SPA routing configured (fallback to index.html for all routes)

---

*Structure analysis: 2026-03-31*
