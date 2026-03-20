# ThookAI — AI-Powered Content Creation Platform

<div align="center">
  <img src="https://img.shields.io/badge/Status-Production%20Ready-brightgreen" alt="Status" />
  <img src="https://img.shields.io/badge/Version-1.0.0-blue" alt="Version" />
  <img src="https://img.shields.io/badge/License-Proprietary-red" alt="License" />
</div>

## 🚀 Overview

ThookAI is a sophisticated AI-powered content creation platform that helps creators, marketers, and agencies produce authentic, high-performing content at scale. The platform uses a multi-agent AI system to generate content that matches your unique voice and style.

### Key Features

- **🤖 Multi-Agent AI System** — 5 specialized agents (Commander, Scout, Thinker, Writer, QC) work together
- **🎭 Persona Engine** — AI learns your voice, style, and content patterns
- **📱 Multi-Platform Support** — LinkedIn, X (Twitter), Instagram native formatting
- **🎨 Creative AI** — Image, video, and voice generation (20+ provider integrations)
- **📅 Content Calendar** — Schedule and manage content across platforms
- **📊 Analytics** — Track performance and optimize strategy
- **🏢 Agency Workspace** — Manage multiple creators (Studio/Agency tiers)
- **📚 Templates Marketplace** — Community-driven content templates

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend (React)                        │
│  Landing • Auth • Dashboard • Content Studio • Persona Engine   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Backend (FastAPI)                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │   Auth   │  │ Persona  │  │ Content  │  │ Billing  │       │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │ Analytics│  │ Templates│  │  Agency  │  │Platforms │       │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     AI Agent Council                            │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │Commander │  │  Scout   │  │ Thinker  │  │  Writer  │       │
│  │(Strategy)│  │(Research)│  │(Creative)│  │ (Draft)  │       │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘       │
│                      ┌──────────┐                              │
│                      │    QC    │                              │
│                      │ (Review) │                              │
│                      └──────────┘                              │
└─────────────────────────────────────────────────────────────────┘
                              │
          ┌───────────────────┼───────────────────┐
          ▼                   ▼                   ▼
    ┌──────────┐        ┌──────────┐        ┌──────────┐
    │ MongoDB  │        │ Pinecone │        │ External │
    │(Primary) │        │ (Vector) │        │   APIs   │
    └──────────┘        └──────────┘        └──────────┘
```

---

## 📦 Tech Stack

| Layer | Technology |
|-------|------------|
| **Frontend** | React 18, Vite, TailwindCSS, shadcn/ui, Framer Motion |
| **Backend** | Python 3.11+, FastAPI, Pydantic, Motor (async MongoDB) |
| **Database** | MongoDB (primary), Pinecone (vector store) |
| **AI/LLM** | Claude (Anthropic), Perplexity, OpenAI, Gemini |
| **Auth** | JWT + Google OAuth (via Emergent Auth) |
| **Creative AI** | 20+ providers for image/video/voice |

---

## 🚀 Quick Start

### Prerequisites

- Node.js 18+
- Python 3.11+
- MongoDB 6+
- Yarn package manager

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-org/thook-ai.git
   cd thook-ai
   ```

2. **Backend Setup**
   ```bash
   cd backend
   cp .env.example .env
   # Edit .env with your API keys (see API Setup section)
   pip install -r requirements.txt
   ```

3. **Frontend Setup**
   ```bash
   cd frontend
   yarn install
   ```

4. **Start Services**
   ```bash
   # Terminal 1 - MongoDB
   mongod --dbpath /path/to/data
   
   # Terminal 2 - Backend
   cd backend
   uvicorn server:app --reload --port 8001
   
   # Terminal 3 - Frontend
   cd frontend
   yarn dev
   ```

5. **Access the app**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8001/api
   - API Docs: http://localhost:8001/docs

---

## 🔑 API Setup Guide

### Required APIs (Tier 1)

These are essential for core functionality:

| API | Purpose | Get Key |
|-----|---------|---------|
| **Emergent LLM Key** | Powers all AI agents | [Emergent Platform](https://emergentagent.com) → Profile → Universal Key |
| **Perplexity** | Scout agent research | [Perplexity Settings](https://www.perplexity.ai/settings/api) |

### Publishing APIs (Tier 2)

Required to publish content to social platforms:

| API | Purpose | Get Key |
|-----|---------|---------|
| **LinkedIn** | B2B content publishing | [LinkedIn Developers](https://www.linkedin.com/developers/apps) |
| **Twitter/X** | Quick content distribution | [Twitter Developer Portal](https://developer.twitter.com/en/portal/dashboard) |
| **Meta** | Instagram/Facebook | [Meta for Developers](https://developers.facebook.com/apps/) |

### Creative APIs (Tier 3)

For enhanced media content:

| API | Purpose | Get Key |
|-----|---------|---------|
| **ElevenLabs** | Voice generation | [ElevenLabs](https://elevenlabs.io/app/settings/api-keys) |
| **OpenAI/DALL-E** | Image generation | [OpenAI Platform](https://platform.openai.com/api-keys) |
| **Stability AI** | Stable Diffusion images | [Stability Platform](https://platform.stability.ai/account/keys) |

### Advanced APIs (Tier 4)

For full feature set:

| API | Purpose | Get Key |
|-----|---------|---------|
| **Pinecone** | Vector DB for persona learning | [Pinecone Console](https://app.pinecone.io/) |
| **Runway ML** | Video generation | [Runway](https://app.runwayml.com/settings) |
| **FAL AI** | Fast image inference | [FAL Dashboard](https://fal.ai/dashboard/keys) |

> 📝 See `.env.example` for the complete list of 30+ supported API integrations.

---

## 📚 User Guide

### 1. Getting Started

1. **Create Account** — Register with email or Google OAuth
2. **Complete Onboarding** — 7-question AI interview to build your persona
3. **Review Persona Card** — See your AI-generated voice profile

### 2. Creating Content

1. Navigate to **Content Studio**
2. Enter your topic or idea
3. Select target platform (LinkedIn/X/Instagram)
4. Click **Generate with AI**
5. Review and edit the generated content
6. Schedule or publish directly

### 3. Persona Engine

Your persona is your AI voice clone. It includes:

- **Archetype** — Your content personality type
- **Voice Descriptor** — How your writing sounds
- **Content Pillars** — Your main topics
- **Regional English** — US/UK/AU/IN formatting

You can edit any field to fine-tune your voice.

### 4. Content Calendar

- View all scheduled content
- Drag and drop to reschedule
- Bulk scheduling support
- Multi-platform coordination

### 5. Templates Marketplace

- Browse community templates
- Filter by platform, category, hook type
- Upvote favorites
- Use templates as starting points

### 6. Agency Workspace (Studio+ tier)

- Create workspaces for client management
- Invite team members
- Unified content feed across creators
- Role-based permissions

---

## 🔌 API Reference

### Authentication

```bash
# Register
POST /api/auth/register
Body: { "email": "...", "password": "...", "name": "..." }

# Login
POST /api/auth/login
Body: { "email": "...", "password": "..." }

# Google OAuth
GET /api/auth/google
```

### Content

```bash
# Create content
POST /api/content/create
Body: { "topic": "...", "platform": "linkedin", "content_type": "thought_leadership" }

# Poll for status
GET /api/content/poll/{job_id}

# List content
GET /api/content
```

### Persona

```bash
# Get persona
GET /api/persona/me

# Update persona
PUT /api/persona/me
Body: { "card": { "hook_style": "..." } }

# Share persona
POST /api/persona/share

# Public view (no auth)
GET /api/persona/public/{share_token}
```

### Templates

```bash
# Browse templates
GET /api/templates?platform=linkedin&category=thought_leadership&sort=popular

# Use template
POST /api/templates/{id}/use
```

> 📖 Full API documentation available at `/docs` when running the backend.

---

## 🏢 Subscription Tiers

| Feature | Free | Pro | Studio | Agency |
|---------|------|-----|--------|--------|
| Monthly Credits | 100 | 500 | 2,000 | 10,000 |
| Content Generation | ✅ | ✅ | ✅ | ✅ |
| Persona Engine | ✅ | ✅ | ✅ | ✅ |
| Shareable Persona | 30 days | Permanent | Permanent | Permanent |
| Agency Workspace | ❌ | ❌ | 3 workspaces | 10 workspaces |
| Team Members | ❌ | ❌ | 10 per workspace | 50 per workspace |
| Templates Publishing | ❌ | ✅ | ✅ | ✅ |
| Priority Support | ❌ | ✅ | ✅ | ✅ |

---

## 🗂️ Project Structure

```
/app
├── backend/
│   ├── agents/           # AI agent modules
│   │   ├── commander.py  # Strategy & planning
│   │   ├── scout.py      # Research (Perplexity)
│   │   ├── thinker.py    # Creative angles
│   │   ├── writer.py     # Content drafting
│   │   ├── qc.py         # Quality control
│   │   └── ...
│   ├── routes/           # API endpoints
│   │   ├── auth.py
│   │   ├── content.py
│   │   ├── persona.py
│   │   ├── agency.py
│   │   ├── templates.py
│   │   └── ...
│   ├── services/         # Business logic
│   │   ├── credits.py
│   │   ├── subscriptions.py
│   │   ├── creative_providers.py
│   │   └── ...
│   ├── pipelines/        # Async job processing
│   ├── .env.example      # Environment template
│   └── server.py         # FastAPI app
│
├── frontend/
│   ├── src/
│   │   ├── components/   # Reusable UI components
│   │   ├── pages/        # Page components
│   │   │   ├── Dashboard/
│   │   │   ├── Onboarding/
│   │   │   └── Public/
│   │   ├── context/      # React contexts
│   │   ├── hooks/        # Custom hooks
│   │   └── lib/          # Utilities
│   └── .env
│
├── memory/
│   └── PRD.md            # Product Requirements Document
│
└── README.md
```

---

## 🔒 Security Notes

- **JWT Tokens** — Change `JWT_SECRET_KEY` in production (min 32 chars)
- **CORS** — Configure `CORS_ORIGINS` to your domain in production
- **API Keys** — Never commit `.env` files; use `.env.example` as template
- **Database** — Use MongoDB Atlas or secured instance in production
- **OAuth** — Configure proper redirect URLs for social platforms

---

## 🐛 Troubleshooting

### Common Issues

**Content generation stuck at "processing"**
- Check if `EMERGENT_LLM_KEY` is valid
- Verify backend logs for API errors

**Social platform connection fails**
- Ensure OAuth credentials are correct
- Check redirect URL configuration

**Persona not generating**
- Complete all 7 onboarding questions
- Check Claude API connectivity

**Images/videos not generating**
- Verify respective API keys are set
- Check provider-specific rate limits

### Getting Help

1. Check `/var/log/supervisor/backend.err.log` for backend errors
2. Check browser console for frontend errors
3. API docs at `/docs` for endpoint details

---

## 📄 License

Proprietary — All Rights Reserved

---

## 🙏 Acknowledgments

Built with:
- [FastAPI](https://fastapi.tiangolo.com/)
- [React](https://react.dev/)
- [TailwindCSS](https://tailwindcss.com/)
- [shadcn/ui](https://ui.shadcn.com/)
- [Framer Motion](https://www.framer.com/motion/)
- [Emergent Integrations](https://emergentagent.com/)

---

<div align="center">
  <strong>ThookAI</strong> — Your AI Creative Agency
  <br />
  <sub>Built with ❤️ for creators who want to scale authentically</sub>
</div>
