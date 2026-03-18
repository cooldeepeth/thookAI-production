# ThookAI — Product Requirements Document (PRD)

**Version:** 1.0 — Sprint 1 Complete  
**Last Updated:** March 2026  
**Status:** Active Development

---

## 1. Product Overview

**ThookAI** is a personal AI creative agency platform for content creators. It uses a multi-agent AI system with a Persona Engine that learns each creator's unique voice, style, and strategy — then automates the full content production pipeline for LinkedIn, X (Twitter), and Instagram.

### Core Innovation
- **Persona Engine**: A living digital clone of the creator's voice (voice fingerprint, content identity, performance intelligence)
- **User Operating Model (UOM)**: Hidden behavioral profile that steers AI strategy invisibly
- **Agent Council**: 15+ specialized AI agents working as one coordinated team
- **Platform-Native UX**: Editors that mimic LinkedIn, X, and Instagram composers

### Tagline
> *"Raw in, ready out — without burnout."*

---

## 2. Target Users

- **Primary**: Mid-tier content creators (5K–50K followers) on LinkedIn, Instagram, X
- **Secondary**: Small content agencies managing multiple creator accounts (Studio tier)

---

## 3. Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 19 + Tailwind CSS + shadcn/ui + Framer Motion |
| Backend | FastAPI (Python) + Motor (async MongoDB) |
| Database | MongoDB (thook_database) |
| AI Models | GPT-4o (Commander, Analyst, Planner), Claude 3.5 Sonnet (Writer), Gemini 1.5 Pro (Persona analysis), Perplexity Sonar Pro (Scout), o1-mini (Thinker), GPT-4o Vision (Visual), DALL-E (Designer), ElevenLabs (Voice), HeyGen/Tavus (Clone), Kling/Runway (Director) |
| Vector DB | Pinecone / pgvector |
| Auth | JWT (email/password) + Emergent Google OAuth |
| Hosting | Kubernetes (preview env) |

### Design System
- Background: `#050505` (Deepest Void)
- Primary: `#D4FF00` (Acid Lime)
- Secondary: `#7000FF` (Electric Violet)
- Typography: Clash Display (headings) + Plus Jakarta Sans (body)
- Pattern: Dark-mode native, glassmorphism, bento grids

---

## 4. Agent Council

| Agent | Model | Role |
|-------|-------|------|
| Commander | GPT-4o | Orchestrates all flows |
| Scout | Perplexity Sonar Pro | Research & trend analysis |
| Thinker | o1/o3-mini | Content strategy & reasoning |
| Writer | Claude 3.5 Sonnet | Voice-matched copywriting |
| Persona | GPT-4o + Pinecone | Identity cloning & learning |
| Visual | GPT-4o Vision + Gemini | Media analysis |
| Designer | DALL-E / Midjourney / Flux | Carousels & graphics |
| Director | Kling / Runway / Veo | Video generation |
| Clone | HeyGen / Tavus | AI avatar videos |
| Voice | ElevenLabs / Sarvam | Voice cloning & narration |
| Editor | Vizard / Opus | Video editing & subtitles |
| Sound | Suno / Udio | Audio branding |
| QC | GPT-4o-mini | Quality control (persona match + AI risk) |
| Analyst | GPT-4o | Performance tracking & learning |
| Planner | GPT-4o-mini | Optimal scheduling |

---

## 5. Persona Engine Schema

Stored per user, per channel in vector DB:

```json
{
  "voice_fingerprint": {
    "sentence_length_distribution": {},
    "vocabulary_complexity": 0.0,
    "emoji_frequency": 0.0,
    "punctuation_patterns": [],
    "hook_style_preferences": [],
    "cta_patterns": []
  },
  "content_identity": {
    "topic_clusters": [],
    "tone": "formal|casual|technical|emotional",
    "humor_style": "",
    "regional_english": "AU|US|UK|IN",
    "visual_aesthetic": {}
  },
  "performance_intelligence": {
    "best_performing_formats": {},
    "optimal_posting_times": {},
    "engagement_patterns": {},
    "content_pillar_balance": {}
  },
  "learning_signals": {
    "edit_deltas": [],
    "approved_embeddings": [],
    "rejected_patterns": [],
    "high_performing_amplifications": []
  }
}
```

---

## 6. UOM (User Operating Model) Schema

```json
{
  "burnout_risk": "low|medium|high",
  "focus_preference": "single-platform|multi-platform",
  "risk_tolerance": "conservative|balanced|bold",
  "cognitive_load_tolerance": "low|high",
  "monetization_priority": "low|medium|high",
  "strategy_maturity": 1,
  "trust_in_thook": 0.5
}
```

---

## 7. QC Parameters

- `personaMatch`: 0–10 score (must be ≥7 to auto-pass)
- `aiRiskScore`: 0–100 (must be ≤20 to auto-pass)
- Platform guideline compliance check

---

## 8. Content Pipeline

```
Raw Input → SCOUT → VISUAL → THINKER → PERSONA → WRITER/DESIGNER/DIRECTOR/VOICE → QC → HUMAN REVIEW → PLANNER → GHOST-PUBLISHER
```

---

## 9. Platform Integrations

| Platform | API | Features |
|----------|-----|---------|
| LinkedIn | LinkedIn API | Posts, carousels, videos |
| X (Twitter) | X API v2 | Tweets, threads, image posts |
| Instagram | Meta API | Feed posts, reels, stories, carousels |

---

## 10. Monetization

- **Credits System**: Each content type uses credits proportional to agents involved
- **Free Tier**: 100 credits/month, 1 platform, basic persona
- **Pro Tier**: $29/mo, 1,000 credits, all 3 platforms, full persona, video
- **Studio Tier**: $99/mo, 5,000 credits, 10 creator accounts, agency dashboard

---

## 11. Sprint Roadmap

### PHASE 1: FOUNDATION
| Sprint | Focus | Status |
|--------|-------|--------|
| **Sprint 1** | Infrastructure + Design System + Auth (JWT + Google OAuth) + Landing Page + Dashboard Shell | ✅ COMPLETE |
| **Sprint 2** | Onboarding Wizard (3-phase) + Persona Engine Core + AI Persona Card Reveal | ✅ COMPLETE |

### PHASE 2: AGENT COUNCIL
| Sprint | Focus | Status |
|--------|-------|--------|
| Sprint 3 | Commander + Scout + Thinker + Writer + QC Agents | 🔜 Next |
| Sprint 4 | Persona Agent (Voice Fingerprint) + UOM Engine + Vector DB (Pinecone) | Planned |

### PHASE 3: CONTENT PIPELINE
| Sprint | Focus | Status |
|--------|-------|--------|
| Sprint 5 | Content Pipeline (Raw Input → Draft) + Platform-Native UX Shells | Planned |
| Sprint 6 | Media Agents (Visual/Designer/Voice) + Human Review Workflow | Planned |

### PHASE 4: PUBLISHING
| Sprint | Focus | Status |
|--------|-------|--------|
| Sprint 7 | Platform Integrations (Meta/LinkedIn/X) + Planner + Ghost Publisher | Planned |
| Sprint 8 | Repurpose Agent + Daily Brief + Content Series Planner + Anti-Repetition Engine | Planned |

### PHASE 5: ANALYTICS & GROWTH
| Sprint | Focus | Status |
|--------|-------|--------|
| Sprint 9 | Analyst Agent + Learning Loops + Persona Refinement + Pattern Fatigue Shield | Planned |
| Sprint 10 | Credit System + Pro/Studio/Agency Tiers + Viral Hook Predictor | Planned |

### PHASE 6: SCALE
| Sprint | Focus | Status |
|--------|-------|--------|
| Sprint 11 | Shareable Persona Cards + Growth Features + Regional English Format | Planned |
| Sprint 12 | B2B Agency Workspace + Templates Marketplace + 3rd Party API | Planned |

---

## 12. What's Been Implemented

### Sprint 1 — March 2026
**Backend:**
- FastAPI modular architecture (`server.py` → `routes/auth.py`)
- `database.py` for MongoDB connection
- `auth_utils.py` for JWT + session validation
- Auth endpoints: register, login, /me, Google OAuth session, logout
- Environment variables: all AI/platform API key placeholders added

**Frontend:**
- Design system: Tailwind dark theme, Clash Display font, Acid Lime palette
- `AuthContext.jsx` for global auth state
- Landing page (Navbar, Hero, Features Bento, Agent Council, Pricing, Footer)
- Auth page (Login/Register tabs, Google OAuth, email/password form)
- AuthCallback (handles Google OAuth session_id exchange)
- Dashboard shell (Sidebar, TopBar, DashboardHome, ComingSoon)
- Protected routes with loading states
- 9 sidebar nav items with placeholder routes

---

## 13. Backlog (Prioritized)

### P0 (Critical for core value)
- Onboarding wizard (3-phase: Social Analysis → Adaptive Interview → Persona Card)
- Persona Engine (voice fingerprint, content identity, learning signals)
- Agent Council core (Commander + Writer + QC)
- Content Pipeline (text-first: raw input → draft → human review)

### P1 (Essential for launch)
- Platform-native UX shells (LinkedIn/X/IG editors)
- Platform publishing (Meta/LinkedIn/X OAuth + auto-publish)
- Planner Agent (optimal timing)
- Analytics basic (post performance tracking)
- Credit system + monetization

### P2 (Growth features)
- Media agents (Visual, Designer, Voice, Director)
- Repurpose Agent
- Daily Brief
- Content Series Planner
- Shareable Persona Cards
- Anti-Repetition Engine
- B2B Agency workspace

---

## 14. Environment Variables

See `/app/backend/.env` for all API key placeholders. User must fill in:
- `OPENAI_API_KEY`
- `ANTHROPIC_API_KEY`
- `GEMINI_API_KEY`
- `PERPLEXITY_API_KEY`
- `ELEVENLABS_API_KEY`
- Social platform credentials (LinkedIn, Meta, Twitter)
- `PINECONE_API_KEY`
- Video/Avatar API keys (Kling, Runway, HeyGen)
