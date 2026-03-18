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
| **Sprint 3** | Commander + Scout + Thinker + Writer + QC Agents + Content Studio UI | ✅ COMPLETE |
| **Sprint 4** | Persona Agent (Voice Fingerprint) + UOM Engine + Vector DB (Pinecone) + Dashboard Stats | ✅ COMPLETE |

### PHASE 3: CONTENT PIPELINE
| Sprint | Focus | Status |
|--------|-------|--------|
| **Sprint 5** | Content Pipeline (Raw Input → Draft) + Platform-Native UX Shells + Daily Brief | ✅ COMPLETE |
| **Sprint 6** | Media Agents (Visual/Designer/Voice) + Human Review Workflow | ✅ COMPLETE |

### PHASE 4: PUBLISHING
| Sprint | Focus | Status |
|--------|-------|--------|
| Sprint 7 | Platform Integrations (Meta/LinkedIn/X) + Planner + Ghost Publisher | 🔜 Next |
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
- ~~Onboarding wizard (3-phase: Social Analysis → Adaptive Interview → Persona Card)~~ ✅ DONE
- ~~Persona Engine (voice fingerprint, content identity, learning signals)~~ ✅ DONE
- ~~Agent Council core (Commander + Writer + QC)~~ ✅ DONE
- Content Pipeline (text-first: raw input → draft → human review) — Partially done, needs platform-native UX

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
- ~~Anti-Repetition Engine~~ ✅ DONE (Sprint 4)
- B2B Agency workspace

---

## 14. Sprint 4 Implementation Details — July 2025

### Backend:
- **Persona Learning Agent** (`agents/learning.py`)
  - `capture_learning_signal()` — Analyzes edits using Claude AI, stores patterns
  - `update_uom_after_interaction()` — Updates UOM (trust, maturity, burnout risk)
  - `analyze_edit_delta()` — AI-powered diff analysis
  - `get_learning_insights()` — Aggregated learning data for UI

- **Anti-Repetition Engine** (`agents/anti_repetition.py`)
  - `get_anti_repetition_context()` — Fetches recent patterns to avoid
  - `build_anti_repetition_prompt()` — Generates Commander prompt addition
  - `score_repetition_risk()` — Scores draft similarity to past content

- **Vector Store Service** (`services/vector_store.py`)
  - Pinecone integration with graceful fallback to mock mode
  - `upsert_approved_embedding()` — Stores approved content vectors
  - `query_similar_content()` — Semantic similarity search
  - `get_recent_patterns()` — Retrieves recent topics/hooks/structures

- **Dashboard Stats API** (`routes/dashboard.py`)
  - `GET /api/dashboard/stats` — Live stats (posts, credits, persona score, recent jobs)
  - `GET /api/dashboard/activity` — Activity feed
  - `GET /api/dashboard/learning-insights` — AI learning summary

- **Pipeline Integration**
  - Commander now receives anti-repetition context
  - QC now includes repetition_risk and repetition_level scoring
  - Content approval/rejection triggers learning signal capture

### Frontend:
- **Dashboard Home** (`DashboardHome.jsx`)
  - Live stats fetched from `/api/dashboard/stats`
  - Loading skeletons during data fetch
  - Recent Content section with last 3 jobs
  - Learning Insights banner showing interaction count

### Database Schema Additions:
- `persona_engines.learning_signals` — Stores edit_deltas, approved_count, rejected_count
- `persona_engines.uom` — User Operating Model (trust, maturity, burnout)

---

## 15. Sprint 5 Implementation Details — July 2025

### Backend:
- **Daily Brief API** (`routes/dashboard.py`)
  - `GET /api/dashboard/daily-brief` — Personalized daily content brief with:
    - Trending topics (via Perplexity Scout)
    - AI-generated content ideas (via GPT-4o)
    - UOM-based energy check (low/medium/high burnout)
    - 6-hour caching in MongoDB
  - `POST /api/dashboard/daily-brief/dismiss` — Dismiss brief for today
  - `GET /api/dashboard/daily-brief/status` — Check if brief should be shown

### Frontend:
- **Platform-Native UX Shells** (`ContentStudio/Shells/`)
  - `LinkedInShell.jsx` — LinkedIn-styled composer (3000 char limit, hashtag highlighting, profile header)
  - `XShell.jsx` — X/Twitter-styled composer (280 char limit, thread support, dark theme, char circle)
  - `InstagramShell.jsx` — Instagram-styled composer (2200 char limit, image placeholder, hashtag counter)

- **Daily Brief Component** (`DailyBrief.jsx`)
  - Collapsible card at top of dashboard
  - Trending topics chips
  - 3 clickable content idea cards (navigate to studio with prefill)
  - Energy check based on UOM burnout risk
  - Dismiss/refresh functionality

- **Content Studio Enhancement** (`ContentStudio/index.jsx`)
  - URL params for prefilling: `?platform=x&prefill=content`
  - Platform-specific default content types

- **ContentOutput Update** (`ContentOutput.jsx`)
  - Renders platform-appropriate shell based on job.platform
  - Repetition risk badge in QC display

### Database Schema Additions:
- `daily_briefs` — Cached daily briefs per user/date
- `daily_brief_dismissals` — Tracks dismissed briefs per user/date

---

## 16. Sprint 6 Implementation Details — July 2025

### Backend Media Agents:

- **Visual Agent** (`agents/visual.py`)
  - `run_visual(image_url_or_base64, platform, content_context)` — Analyzes images using GPT-4o Vision
  - Returns: subject, tone, key_message, caption_angles[], is_safe
  - Safety check for NSFW content

- **Designer Agent** (`agents/designer.py`)
  - `generate_image(prompt, style, platform, persona_card)` — Generates images using GPT Image (gpt-image-1)
  - Style presets: minimal, bold, data-viz, personal
  - `generate_carousel(topic, key_points, style, platform)` — Creates carousel slides (cover + content + CTA)
  - Platform-specific aspect ratios

- **Voice Agent** (`agents/voice.py`)
  - `generate_voice_narration(text, voice_id, stability, similarity_boost)` — Converts text to speech via ElevenLabs
  - Default voice: Rachel
  - 5000 character limit per generation
  - Returns audio_base64 and audio_url

### Backend API Endpoints:

- `POST /api/content/generate-image` — Generate image for job (stores in media_assets[])
- `POST /api/content/generate-carousel` — Generate carousel slides
- `POST /api/content/narrate` — Generate voice narration (stores in audio_url)
- `GET /api/content/image-styles` — List available style presets
- `GET /api/content/voices` — List default and user voices
- `PATCH /api/content/job/{job_id}/regenerate` — Create new version (max 5)
- `GET /api/content/job/{job_id}/history` — Get version history

### Frontend Components:

- **MediaPanel** (`ContentOutput.jsx`)
  - Image generation with style selector
  - Voice generation with audio player (waveform visualization)
  - Download button for audio

- **RejectionModal** (`ContentOutput.jsx`)
  - Modal for providing rejection feedback
  - Stores notes with learning signals

- **Version Tracking**
  - Version indicator in ContentOutput
  - Regeneration creates new version with hints

### Database Schema Additions:
- `content_jobs.media_assets[]` — Stores generated images
- `content_jobs.audio_url` — Stores voice narration
- `content_jobs.carousel` — Stores carousel data
- `content_jobs.version` — Version number (1-based)
- `content_jobs.parent_job_id` — Links to original job
- `content_jobs.regeneration_count` — Tracks regenerations
- `content_jobs.video_assets[]` — Stores generated videos
- `content_jobs.avatar_video` — Stores avatar video data

---

## 17. Multi-Provider Creative AI System (Updated Sprint 6)

ThookAI now supports multiple AI providers for diversified load and versatility:

### Image Generation Providers (6 providers):
| Provider | Models | Speed | Quality | Env Key |
|----------|--------|-------|---------|---------|
| **OpenAI** | gpt-image-1, dall-e-3 | Medium | High | `EMERGENT_LLM_KEY` |
| **Stability AI** | sd3-large, sdxl-1.0 | Fast | High | `STABILITY_API_KEY` |
| **FAL AI** | flux-pro, flux-dev, sdxl-lightning | Very Fast | High | `FAL_API_KEY` |
| **Replicate** | sdxl, kandinsky | Medium | Varies | `REPLICATE_API_TOKEN` |
| **Leonardo AI** | leonardo-diffusion-xl | Medium | High | `LEONARDO_API_KEY` |
| **Ideogram** | ideogram-v2 (best for text) | Fast | High | `IDEOGRAM_API_KEY` |

### Video Generation Providers (7 providers):
| Provider | Models | Duration | Quality | Env Key |
|----------|--------|----------|---------|---------|
| **Runway** | gen-3-alpha, gen-3-alpha-turbo | 5-10s | Cinematic | `RUNWAY_API_KEY` |
| **Kling AI** | kling-v1, kling-v1.5 | 5-10s | High | `KLING_API_KEY` |
| **Pika Labs** | pika-1.0 | 3-4s | Good | `PIKA_API_KEY` |
| **Luma AI** | dream-machine | 5s | High | `LUMA_API_KEY` |
| **HeyGen** | avatar-v2 | Unlimited | High | `HEYGEN_API_KEY` |
| **D-ID** | talks | Unlimited | Good | `DID_API_KEY` |
| **Synthesia** | studio | Unlimited | Enterprise | `SYNTHESIA_API_KEY` |

### Voice/TTS Providers (6 providers):
| Provider | Models | Languages | Quality | Env Key |
|----------|--------|-----------|---------|---------|
| **ElevenLabs** | eleven_multilingual_v2 | 29 | Premium | `ELEVENLABS_API_KEY` |
| **OpenAI TTS** | tts-1, tts-1-hd | 50+ | High | `EMERGENT_LLM_KEY` |
| **Play.ht** | playht2.0, playht2.0-turbo | 142 | Premium | `PLAYHT_API_KEY` |
| **Murf AI** | murf-studio | 20 | Studio | `MURF_API_KEY` |
| **Resemble AI** | resemble-v3 | 24 | High | `RESEMBLE_API_KEY` |
| **Google TTS** | neural2, wavenet | 220+ | Good | `GOOGLE_TTS_API_KEY` |

### New API Endpoints:
- `GET /api/content/providers` — Get status of all configured providers
- `GET /api/content/providers/image` — Image providers list
- `GET /api/content/providers/video` — Video providers list
- `GET /api/content/providers/voice` — Voice providers list
- `POST /api/content/generate-video` — Generate video with provider selection
- `POST /api/content/generate-avatar-video` — Generate avatar video

### Style Presets (8 styles):
- minimal, bold, data-viz, personal, cinematic, illustration, 3d, retro

---

## 18. Environment Variables

See `/app/backend/.env` for all API key placeholders:

### LLM Providers:
- `EMERGENT_LLM_KEY` (Universal key for OpenAI/Anthropic/Google)
- `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`, `PERPLEXITY_API_KEY`

### Image Generation:
- `STABILITY_API_KEY`, `FAL_API_KEY`, `REPLICATE_API_TOKEN`
- `LEONARDO_API_KEY`, `IDEOGRAM_API_KEY`, `MIDJOURNEY_API_KEY`
- `GOOGLE_IMAGEN_API_KEY`

### Video Generation:
- `RUNWAY_API_KEY`, `KLING_API_KEY`, `PIKA_API_KEY`, `LUMA_API_KEY`
- `HEYGEN_API_KEY`, `DID_API_KEY`, `SYNTHESIA_API_KEY`

### Voice/Audio:
- `ELEVENLABS_API_KEY`, `PLAYHT_API_KEY`, `PLAYHT_USER_ID`
- `MURF_API_KEY`, `RESEMBLE_API_KEY`, `GOOGLE_TTS_API_KEY`
- `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` (for Polly)

### Social Platforms:
- `LINKEDIN_CLIENT_ID`, `LINKEDIN_CLIENT_SECRET`
- `META_APP_ID`, `META_APP_SECRET`
- `TWITTER_API_KEY`, `TWITTER_API_SECRET`, `TWITTER_ACCESS_TOKEN`, `TWITTER_ACCESS_SECRET`

### Other:
- `PINECONE_API_KEY`, `PINECONE_ENVIRONMENT`
