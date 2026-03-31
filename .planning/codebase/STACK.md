# Technology Stack

**Analysis Date:** 2026-03-31

## Languages

**Primary:**
- Python 3.11.11 - Backend API, agents, task processing
- JavaScript/React 18.3.1 - Frontend application (CRA + CRACO)
- TypeScript - Frontend tooling (with ESLint plugin support)

**Secondary:**
- HTML/CSS - Frontend via TailwindCSS 3.4.17
- SQL/MongoDB Query Language - Database operations via Motor async driver

## Runtime

**Environment:**
- Python 3.11.11 (specified in `backend/runtime.txt`)
- Node.js 18+ (frontend uses `react-scripts` 5.0.1)

**Package Manager:**
- pip (Python) - `backend/requirements.txt` with 52 dependencies
- npm (JavaScript) - `frontend/package.json` with 99 dependencies
- Lockfiles: package-lock.json (frontend), pip freeze equivalent in requirements.txt

## Frameworks

**Core Backend:**
- FastAPI 0.110.1 - REST API framework, async request handling
- Uvicorn 0.25.0 - ASGI server for FastAPI

**Frontend:**
- React 18.3.1 - UI framework
- React Router DOM 7.5.1 - Client-side routing
- React Hook Form 7.56.2 - Form state management
- Zod 3.24.4 - TypeScript-first schema validation

**UI Components:**
- Radix UI (33 components) - Headless component library (accordion, dialog, dropdown, etc.)
- shadcn/ui - Composable React components built on Radix UI (referenced via `components.json`)
- TailwindCSS 3.4.17 - Utility-first CSS framework
- Lucide React 0.507.0 - Icon library
- Framer Motion 12.38.0 - Animation library
- Embla Carousel React 8.6.0 - Carousel component
- Sonner 2.0.3 - Toast notification system

**Task Queue/Async:**
- Celery 5.3.0 - Distributed task queue
- Redis 7+ - Message broker and result backend

**Testing:**
- pytest 8.0.0 - Python test framework
- pytest-asyncio 0.23.0 - Async test support
- No frontend test framework detected in package.json

**Build/Dev Tools:**
- Craco 7.1.0 - CRA configuration override (webpack)
- Black 24.1.1 - Python code formatter
- isort 5.13.2 - Python import sorter
- flake8 7.0.0 - Python linter
- mypy 1.8.0 - Python type checker
- ESLint 8.57.1 - JavaScript linter
- TypeScript ESLint (5.62.0) - TS-aware linting
- PostCSS 8.4.49 - CSS preprocessor (with autoprefixer)
- Jest (via react-scripts) - JavaScript test runner (CRA default)

## Key Dependencies

**Critical Backend:**
- motor 3.3.1 - Async MongoDB driver (uses PyMongo 4.5.0 under the hood)
- anthropic 0.34.0 - Anthropic Claude API client (primary LLM)
- openai 1.40.0 - OpenAI API client (fallback LLM)
- boto3 1.34.129+ - AWS S3 / Cloudflare R2 client
- stripe 8.0.0 - Payment processing

**LLM & AI:**
- google-generativeai 0.8.0 - Google Gemini support (optional)
- langgraph 0.2.0 - LangChain-based agent orchestration
- langchain-core 0.3.0 - LangChain framework

**Media & Creative Providers:**
- fal-client 0.10.0 - FAL.ai image generation
- lumaai 1.0.0 - Luma Dream Machine video API
- elevenlabs 1.50.0 - ElevenLabs voice/TTS API
- pinecone 5.0.0 - Vector database for embeddings

**Infrastructure:**
- redis 5.0.0 - Redis Python client with hiredis speedup
- kombu 5.6.0 - Celery message transport
- billiard 4.2.1 - Celery task execution backend

**Authentication & Authorization:**
- authlib 1.3.2 - OAuth client for Google, LinkedIn, Twitter, Instagram
- pyjwt 2.10.1 - JWT token creation/verification
- python-jose 3.3.0 - JOSE token support
- bcrypt 4.1.3 - Password hashing
- passlib 1.7.4 - Password utilities
- cryptography 42.0.8 - Encryption (Fernet for token encryption)
- itsdangerous 2.2.0 - Secure signing for tokens

**Utilities:**
- pydantic 2.6.4+ - Data validation and settings management
- email-validator 2.2.0 - Email format validation
- python-multipart 0.0.9 - Multipart form data parsing
- httpx 0.28.1 - HTTP client (sync+async)
- requests 2.31.0 - HTTP client (synchronous)
- pandas 2.2.0 - Data manipulation
- numpy 1.26.0 - Numerical computing
- typer 0.9.0 - CLI utilities
- jq 1.6.0 - JSON query tool
- python-dotenv 1.0.1 - .env file loading

**Monitoring & Observability:**
- sentry-sdk 2.0.0+ - Error tracking and performance monitoring

**Email:**
- resend 2.0.0 - Transactional email service

**Data Processing:**
- tzdata 2024.2 - Timezone database
- tzlocal 5.0 - Local timezone detection

## Configuration

**Environment:**
All configuration managed via `backend/config.py` dataclasses:
- `DatabaseConfig` - MongoDB connection (MONGO_URL, DB_NAME, pool sizing)
- `SecurityConfig` - JWT, CORS, rate limiting
- `LLMConfig` - API keys for all LLM providers
- `R2Config` - Cloudflare R2 credentials
- `EmailConfig` - Resend email configuration
- `GoogleConfig` - Google OAuth
- `StripeConfig` - Stripe API keys and price IDs
- `VideoProviderConfig` - Video generation API keys (Runway, Kling, Luma, HeyGen, D-ID, FAL)
- `VoiceProviderConfig` - Voice/TTS API keys (Play.ht, Google TTS)
- `PlatformOAuthConfig` - LinkedIn, Meta/Instagram, Twitter OAuth
- `PineconeConfig` - Vector store configuration
- `AppConfig` - Environment, debug, logging, URLs

Environment variables loaded from `.env` file at startup. See `backend/.env.example` for full reference.

**Build:**
- Frontend: `frontend/tsconfig.json` (TypeScript config)
- Frontend: `frontend/tailwind.config.js` - TailwindCSS customization
- Frontend: `frontend/craco.config.js` - CRA webpack overrides
- Frontend: `frontend/postcss.config.js` - PostCSS plugins
- Frontend: `components.json` - shadcn/ui component configuration
- Backend: `backend/celeryconfig.py` - Celery task routing and beat schedule
- Backend: `pytest.ini` - Pytest configuration
- Docker: `docker-compose.yml` - Local development services

## Platform Requirements

**Development:**
- Python 3.11+
- Node.js 18+ (for frontend)
- MongoDB 7.0+ (local or Atlas)
- Redis 7+ (for Celery)
- Git
- API keys: At least one LLM provider (Anthropic preferred, OpenAI fallback)

**Production:**
- Deployment targets: Backend on Render/Railway/Heroku (via Procfile), Frontend on Vercel
- MongoDB Atlas (cloud managed)
- Redis Cloud or AWS ElastiCache
- Cloudflare R2 (media storage)
- All external API credentials (Stripe, Resend, video/voice providers)

**Deployment Entry Points:**
- Backend: `uvicorn server:app --host 0.0.0.0 --port $PORT` (Procfile `web` process)
- Background worker: `celery -A celery_app:celery_app worker` (Procfile `worker` process)
- Beat scheduler: `celery -A celery_app:celery_app beat` (Procfile `beat` process)
- Frontend: `npm start` (Vercel or local development)

---

*Stack analysis: 2026-03-31*
