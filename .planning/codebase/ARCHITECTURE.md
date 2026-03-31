# Architecture

**Analysis Date:** 2026-03-31

## Pattern Overview

**Overall:** Tiered async microservice architecture with AI agent pipeline orchestration, async task queue processing, and decoupled frontend/backend.

**Key Characteristics:**
- Multi-agent AI pipeline for content generation (Commander → Scout → Thinker → Writer → QC)
- FastAPI backend with Motor async MongoDB driver and Celery task queue
- React frontend with client-side context-based auth and REST API consumption
- Service layer abstraction for external integrations (LLM, media storage, billing, vector embeddings)
- Middleware-based cross-cutting concerns (security, rate limiting, performance optimization)

## Layers

**Presentation Layer:**
- Purpose: Render user interfaces and handle user interactions
- Location: `frontend/src/pages/`, `frontend/src/components/`
- Contains: React page components (Dashboard, Onboarding, ContentStudio), UI components (shadcn/ui), page-level logic
- Depends on: AuthContext for user state, API services for HTTP calls, custom hooks for data fetching
- Used by: End users through the browser

**State Management & Routing Layer:**
- Purpose: Manage application-level state, authentication, and client-side routing
- Location: `frontend/src/context/AuthContext.jsx`, `frontend/src/App.js`, `frontend/src/hooks/`
- Contains: AuthProvider (JWT + localStorage token management), custom hooks (useAuth, useAPI), React Router setup
- Depends on: FastAPI auth endpoints, localStorage for token persistence
- Used by: All pages and components for auth checks, user context, API access

**API Layer (Frontend):**
- Purpose: Abstract HTTP communication with the backend
- Location: `frontend/src/lib/` (likely contains API client utilities)
- Contains: HTTP client configuration, request/response interceptors, endpoint helpers
- Depends on: REACT_APP_BACKEND_URL environment variable, AuthContext token
- Used by: All components that need to call backend endpoints

**HTTP Server (FastAPI):**
- Purpose: Handle incoming HTTP requests and orchestrate business logic
- Location: `backend/server.py`
- Contains: Application instantiation, middleware registration, route mounting, lifespan management (startup/shutdown)
- Depends on: All middleware, all routers, database connection, config validation
- Used by: Frontend clients, external webhooks, scheduled tasks

**Route Layer (Backend):**
- Purpose: Handle HTTP endpoints for specific business domains
- Location: `backend/routes/*.py` (auth.py, content.py, persona.py, billing.py, agency.py, etc.)
- Contains: Request validation, response serialization, authorization checks, delegation to services/agents
- Depends on: get_current_user auth dependency, database, services, agents, Celery tasks
- Used by: FastAPI application through router registration in server.py

**Agent Pipeline Layer:**
- Purpose: Orchestrate multi-stage AI content generation through specialized agents
- Location: `backend/agents/pipeline.py`, `backend/agents/*.py` (commander, scout, thinker, writer, qc, etc.)
- Contains: 
  - `pipeline.py`: Orchestration entry point, context building, stage sequencing
  - `commander.py`: Parse user intent, build content strategy
  - `scout.py`: Research and fact-gathering (Perplexity API)
  - `thinker.py`: Angle/hook selection, structure planning
  - `writer.py`: Final content generation using Claude LLM
  - `qc.py`: Quality control and compliance checking
  - `publisher.py`: Platform publishing (LinkedIn, X, Instagram OAuth)
  - `learning.py`: User feedback capture, persona refinement
  - `anti_repetition.py`: Content diversity and pattern fatigue detection
  - `viral_predictor.py`: Hook scoring and virality prediction
  - `designer.py`, `video.py`, `voice.py`: Media generation agents
- Depends on: LLM clients, vector store, database, external media providers
- Used by: Content generation routes and background tasks

**Service Layer (Business Logic):**
- Purpose: Encapsulate reusable business logic and external integrations
- Location: `backend/services/*.py`
- Contains:
  - `llm_client.py`: LlmChat wrapper (Anthropic/OpenAI/Gemini)
  - `llm_keys.py`: Provider availability checks
  - `credits.py`: Credit system, tier enforcement, operation tracking
  - `stripe_service.py`: Stripe checkout, webhook handling, subscription management
  - `subscriptions.py`: Subscription tier validation
  - `media_storage.py`: Cloudflare R2 upload/download
  - `vector_store.py`: Pinecone embedding store
  - `persona_refinement.py`: Persona evolution, pattern fatigue shield
  - `email_service.py`: Email sending via Resend API
  - `social_analytics.py`: Social platform metrics aggregation
  - `creative_providers.py`: Image/video/voice generation provider abstraction
- Depends on: Config settings, external APIs (LLM, Stripe, R2, Pinecone, etc.), database
- Used by: Routes, agents, tasks

**Middleware Layer:**
- Purpose: Handle cross-cutting concerns for all HTTP requests/responses
- Location: `backend/middleware/security.py`, `backend/middleware/performance.py`
- Contains:
  - `SecurityHeadersMiddleware`: XSS, clickjacking, CSP headers
  - `RateLimitMiddleware`: Request rate limiting with Redis fallback
  - `InputValidationMiddleware`: Request payload validation
  - `CompressionMiddleware`: Gzip compression
  - `CacheMiddleware`: Response caching
  - `TimingMiddleware`: Request/response timing
- Depends on: Redis (optional for rate limiting), Starlette middleware base
- Used by: FastAPI application, applied globally to all routes

**Data Layer:**
- Purpose: Database access abstraction and connection pooling
- Location: `backend/database.py`, `backend/db_indexes.py`, `backend/auth_utils.py`
- Contains:
  - `database.py`: MongoDB Motor async client initialization, connection pooling, health checks
  - `db_indexes.py`: MongoDB index definitions (auto-run at startup)
  - `auth_utils.py`: JWT token generation/validation, password hashing
- Depends on: MongoDB (async Motor driver), config settings, FERNET_KEY for encryption
- Used by: All routes, services, agents for data persistence

**Task Queue Layer:**
- Purpose: Async background processing for long-running and scheduled operations
- Location: `backend/tasks/content_tasks.py`, `backend/tasks/media_tasks.py`, `backend/celery_app.py`
- Contains:
  - Celery task definitions: process_scheduled_posts, reset_daily_limits, cleanup_old_jobs, etc.
  - Celery app configuration with Redis broker
  - Task scheduling (beat schedule)
- Depends on: Redis (Celery broker), database, agents, services
- Used by: Routes for async job submission, triggered by Celery beat for scheduled tasks

**Configuration Layer:**
- Purpose: Centralized environment-driven configuration
- Location: `backend/config.py`
- Contains: Dataclass-based config objects (DatabaseConfig, SecurityConfig, LLMConfig, R2Config, StripeConfig, etc.)
- Depends on: Environment variables from .env
- Used by: All modules that need config (imports `from config import settings`)

## Data Flow

**Content Generation Flow (Sync):**

1. Frontend: User submits content request via `POST /api/content/create`
2. Route handler (`backend/routes/content.py`): Validates input, checks credits, creates job record
3. Pipeline orchestrator (`backend/agents/pipeline.py`): Kicks off agent pipeline
4. Commander (`backend/agents/commander.py`): Parses intent, loads persona, builds strategy JSON
5. Scout (`backend/agents/scout.py`): Optional - queries Perplexity for research
6. Thinker (`backend/agents/thinker.py`): Selects angle/hook, applies anti-repetition checks
7. Writer (`backend/agents/writer.py`): Generates final content using Claude LLM with persona voice
8. QC (`backend/agents/qc.py`): Compliance check, quality scoring
9. Database: Save draft to `db.content_jobs` with status="reviewing"
10. Route response: Return job_id and draft to frontend
11. Frontend: Poll `GET /api/content/{job_id}` or WebSocket for status updates until "reviewing"

**Content Approval & Publishing Flow:**

1. Frontend: User reviews draft, clicks approve
2. Route handler: Updates job status to "approved", captures user edit (if any)
3. If scheduled: Job saved to `db.scheduled_posts` for future publishing
4. If immediate: Background task calls `agents/publisher.py` to post to platform via OAuth token
5. Platform tokens: Retrieved from `db.platform_tokens` (LinkedIn, X, Instagram OAuth)
6. Post published: Job status set to "published", performance tracking initiated

**Persona Generation Flow (Onboarding):**

1. Frontend: User completes 7-question interview
2. Route handler (`backend/routes/onboarding.py`): Collects answers
3. Route calls LLM to generate persona card from interview responses
4. Database: Save persona to `db.persona_engines` with voice_fingerprint, content_identity, etc.
5. User marked as `onboarding_completed=true`

**Credit System Flow:**

1. Content generation initiated
2. `services/credits.py:deduct_credits()` called with operation type
3. Checks user's subscription tier and current balance
4. Deducts credits from `db.users.credits`
5. Records operation in `db.credit_operations` for audit
6. If insufficient credits: Return HTTP 402 Payment Required

**Billing/Subscription Flow:**

1. User initiates upgrade via billing page
2. Route (`backend/routes/billing.py`): Creates Stripe checkout session
3. Frontend redirects to Stripe Hosted Checkout
4. User completes payment
5. Stripe webhook (`POST /api/billing/webhook`) updates subscription in database
6. User tier upgraded in `db.users.subscription_tier`
7. Monthly credits refreshed via Celery task

**State Management:**

- **Frontend state:** User auth via AuthContext (JWT token in localStorage)
- **Backend session state:** JWT claims contain user_id, derived from `get_current_user()` dependency
- **Job state:** Stored in MongoDB (content_jobs collection) with status progression: pending → processing → reviewing → approved → scheduled/published
- **Persona state:** Stored in MongoDB (persona_engines collection), immutable until user explicitly creates new version
- **Credit state:** Stored in MongoDB (users.credits), updated transactionally on content generation
- **Scheduled posts state:** Stored in MongoDB (scheduled_posts collection), polled by Celery beat task

## Key Abstractions

**LlmChat (Service):**
- Purpose: Unified abstraction over multiple LLM providers (Anthropic, OpenAI, Gemini)
- Examples: `backend/services/llm_client.py`, used in all agent files
- Pattern: Constructor takes provider key, provider name, model name; provides `async generate()` method for streaming or full responses

**ContentJob (Data Model):**
- Purpose: Represents a single content generation request through its lifecycle
- Examples: Saved to and queried from `db.content_jobs`
- Pattern: Contains job_id, user_id, platform, status, draft, final_content, edited_content, performance_data, created_at, updated_at

**PersonaEngine (Data Model):**
- Purpose: Represents a user's voice fingerprint and content identity
- Examples: Saved to and queried from `db.persona_engines`
- Pattern: Contains user_id, card (persona descriptors), voice_fingerprint, content_identity, performance_intelligence, learning_signals, uom (Unit of Measure for success)

**Agent Interface:**
- Purpose: Standardize agent function signatures for pipeline composition
- Pattern: All agents export async function like `async def run_agent(input_data, context) -> dict`
- Examples: run_commander, run_scout, run_thinker, run_writer, run_qc in `backend/agents/*.py`

**Service Integration Pattern:**
- Purpose: Uniform interface to external APIs (Stripe, R2, Pinecone, Resend)
- Pattern: Service classes initialize with config, expose async methods for operations
- Examples: StripeService.create_checkout_session(), R2Storage.upload(), PineconeVectorStore.store_embedding()

**Middleware Chain:**
- Purpose: Composable request/response filtering
- Pattern: Each middleware inherits BaseHTTPMiddleware, implements dispatch() async method
- Examples: SecurityHeadersMiddleware, RateLimitMiddleware in `backend/middleware/`

## Entry Points

**Backend Server:**
- Location: `backend/server.py` (main function, lifespan context manager)
- Triggers: `uvicorn server:app` from Procfile
- Responsibilities:
  - Initialize FastAPI app
  - Register all middleware (security, performance)
  - Mount all routers from `backend/routes/`
  - Setup lifespan hooks (startup: Sentry, DB indexes; shutdown: DB cleanup)
  - Start listening on port 8001 (configurable)

**Content Generation Route:**
- Location: `backend/routes/content.py:create_content()` endpoint
- Triggers: `POST /api/content/create` from frontend
- Responsibilities:
  - Validate request (platform, content_type, raw_input)
  - Check user auth and subscription tier
  - Deduct credits
  - Create job record in MongoDB
  - Invoke `run_agent_pipeline()` 
  - Return job_id to frontend

**Celery Workers:**
- Location: Worker processes (defined in `backend/celery_app.py`)
- Triggers: Celery Beat scheduler (cron-based) or explicit task.delay() calls
- Responsibilities:
  - Process scheduled posts (run every minute)
  - Reset daily/monthly limits (scheduled)
  - Cleanup old jobs (scheduled)
  - Generate media async (image, video, voice)

**Frontend App:**
- Location: `frontend/src/App.js` (main component)
- Triggers: Browser navigation to frontend URL
- Responsibilities:
  - Initialize React Router
  - Wrap app in AuthProvider for JWT auth
  - Mount Error Boundary
  - Route to appropriate page (Landing, Auth, Dashboard, Onboarding)

**Frontend Auth Flow:**
- Location: `frontend/src/context/AuthContext.jsx`
- Triggers: App mount, manual login, Google OAuth callback
- Responsibilities:
  - Load JWT from localStorage
  - Validate token with GET /api/auth/me
  - Maintain user state across page reloads
  - Provide login/logout functions

## Error Handling

**Strategy:** Layered error handling with specific HTTP status codes, fallback behavior, and structured error logging.

**Patterns:**

**Backend - Route Level:**
- Catch request validation errors: Return `422 Unprocessable Entity` with field errors
- Catch auth errors: Return `401 Unauthorized` if no token or token invalid
- Catch permission errors: Return `403 Forbidden` if user lacks required role/workspace access
- Catch not-found errors: Return `404 Not Found` if resource doesn't exist
- Catch credit errors: Return `402 Payment Required` if insufficient credits
- Catch Stripe errors: Return `402 Payment Required` with specific error message
- Generic server errors: Return `500 Internal Server Error`, log full traceback with Sentry

**Backend - Agent Level:**
- LLM API failures: Log error, return default/fallback response (e.g., mock persona in onboarding)
- Database failures: Raise exception caught by route handler, return `500`
- External API timeouts (Perplexity, R2, Stripe): Log, return partial data or skip enrichment

**Backend - Middleware Level:**
- Request too large: RateLimitMiddleware returns `429 Too Many Requests`
- Invalid JSON: InputValidationMiddleware returns `400 Bad Request`
- Missing security headers: SecurityHeadersMiddleware still returns OK but logs warning

**Frontend:**
- API call fails: useAPI hook catches error, sets error state, displays toast notification
- Auth token invalid: AuthContext logs user out, redirects to /auth
- Network timeout: Show retry button or "offline" message
- Form validation: Show field-level errors, disable submit until fixed

**Monitoring:**
- Sentry DSN configured in server.py if `SENTRY_DSN` env var set
- Logs written to stdout with timestamp, level, module name, message
- Database errors logged to database error collection (if configured)

## Cross-Cutting Concerns

**Logging:**
- Approach: Python logging module configured in `backend/server.py` with standard format
- Pattern: `logger = logging.getLogger(__name__)` at module level, log at appropriate levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- Front-end: Browser console logging via window.console, no centralized logging yet

**Validation:**
- Backend: Pydantic BaseModel for request validation (declared in route handler), custom validators for complex rules (password policy, credit sufficiency)
- Frontend: React Hook Form for form validation, client-side checks before submission

**Authentication:**
- Backend: JWT tokens (HS256 algorithm, configurable expiry days), validated by `get_current_user()` dependency in all protected routes
- Token payload: Contains user_id, issued_at, expiry
- Token storage: Frontend localStorage, passed as `Authorization: Bearer <token>` header
- Refresh: No refresh token flow yet; token expires based on JWT_EXPIRE_DAYS config

**Authorization:**
- Backend: Role-based checks (admin, user, workspace_member) in route handlers
- Workspace context: Some routes check user is member of workspace and has appropriate role
- API key checks: Some routes (webhooks) verify Stripe webhook signature

**Performance:**
- Backend: Middleware-level compression (gzip), response caching headers
- Frontend: Code splitting by route, lazy loading of Dashboard components
- Database: MongoDB indexes created at startup (db_indexes.py)
- Connection pooling: Motor async client configured with minPoolSize=10, maxPoolSize=100
- Rate limiting: Configurable per-minute limits (RATE_LIMIT_PER_MINUTE=60, auth-specific lower limit)

---

*Architecture analysis: 2026-03-31*
