# ThookAI — AI-Powered Content Creation Platform

ThookAI is a sophisticated AI platform that helps creators generate, schedule, and publish content across social media platforms. It uses a multi-agent AI system that learns your unique voice and style.

## Tech Stack

| Component | Technology |
|-----------|------------|
| **Backend** | FastAPI, MongoDB (motor async), Celery + Redis |
| **Frontend** | React 18, react-router-dom v6, Tailwind CSS |
| **AI** | emergentintegrations (multi-LLM), Claude, GPT-4o, Perplexity |
| **Media Storage** | Cloudflare R2 (S3-compatible) |
| **Creative AI** | DALL-E, Stable Diffusion, ElevenLabs, Runway |
| **Payments** | Stripe (subscriptions + one-time credits) |
| **Vector DB** | Pinecone (persona embeddings) |

## Project Structure

```
/app/
├── backend/                 # FastAPI backend
│   ├── agents/              # AI agent modules (Commander, Scout, Writer, etc.)
│   ├── middleware/          # Security & performance middleware
│   ├── routes/              # API endpoints
│   ├── services/            # Business logic (credits, stripe, media storage)
│   ├── tasks/               # Celery background tasks
│   ├── tests/               # Backend tests
│   ├── server.py            # Main FastAPI app
│   ├── config.py            # Environment configuration
│   └── database.py          # MongoDB connection
├── frontend/                # React frontend
│   ├── src/
│   │   ├── components/      # Reusable UI components
│   │   ├── pages/           # Page components
│   │   ├── context/         # React context (Auth)
│   │   └── App.jsx          # Main app with routing
│   └── package.json
├── docs/                    # Documentation
└── README.md
```

## Setup & Running Locally

### Prerequisites
- Python 3.11+
- Node.js 18+
- MongoDB (local or Atlas)
- Redis (optional, for Celery)

### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys

# Run backend
uvicorn server:app --reload --port 8001
```

### Frontend Setup

```bash
cd frontend

# Install dependencies
yarn install

# Configure environment
# REACT_APP_BACKEND_URL is already set

# Run frontend
yarn dev
```

### Running Celery Workers (Optional)

For async video/voice generation:

```bash
# Terminal 1: Worker
celery -A tasks.celery_app worker --loglevel=info

# Terminal 2: Beat scheduler
celery -A tasks.celery_app beat --loglevel=info
```

## Environment Variables

See `backend/.env.example` for the complete list. Key variables:

| Variable | Description |
|----------|-------------|
| `MONGO_URL` | MongoDB connection string |
| `JWT_SECRET_KEY` | 64+ char random secret |
| `EMERGENT_LLM_KEY` | Universal LLM key |
| `STRIPE_SECRET_KEY` | Stripe API key |
| `R2_*` | Cloudflare R2 credentials |

## Subscription Tiers

| Tier | Price | Credits/Month | Features |
|------|-------|---------------|----------|
| Free | $0 | 50 | 1 platform, basic persona |
| Pro | $19/mo* | 500 | All platforms, voice narration |
| Studio | $49/mo* | 2,000 | Video generation, API access |
| Agency | $129/mo* | 10,000 | Team workspaces, white-label |

*Early bird pricing (35% off)

## Credit Costs

| Operation | Credits |
|-----------|---------|
| Content Create | 10 |
| Image Generate | 8 |
| Voice Narration | 12 |
| Video Generate | 50 |
| Repurpose | 3 |

## API Documentation

Available at `/api/docs` in development mode.

Key endpoints:
- `POST /api/auth/register` - User registration
- `POST /api/content/create` - Create content with AI
- `GET /api/persona/me` - Get user's persona
- `POST /api/media/upload-url` - Get presigned upload URL

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Frontend  │────▶│   FastAPI   │────▶│   MongoDB   │
│   (React)   │     │   Backend   │     │             │
└─────────────┘     └──────┬──────┘     └─────────────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
        ┌─────▼─────┐ ┌────▼────┐ ┌─────▼─────┐
        │  AI Agents │ │  Celery │ │ Cloudflare│
        │  (Claude,  │ │ Workers │ │    R2     │
        │  GPT-4o)   │ └─────────┘ └───────────┘
        └───────────┘
```

## License

Proprietary - All rights reserved.
