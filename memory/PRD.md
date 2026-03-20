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
| **Sprint 7** | Platform Integrations (Meta/LinkedIn/X) + Planner + Ghost Publisher | ✅ COMPLETE |
| **Sprint 8** | Repurpose Agent + Content Series Planner + Anti-Repetition V2 + Content Library | ✅ COMPLETE |

### PHASE 5: ANALYTICS & GROWTH
| Sprint | Focus | Status |
|--------|-------|--------|
| **Sprint 9** | Analyst Agent + Learning Loops + Persona Refinement + Pattern Fatigue Shield | ✅ COMPLETE |
| **Sprint 10** | Credit System + Pro/Studio/Agency Tiers + Viral Hook Predictor | ✅ COMPLETE |

### PHASE 6: SCALE
| Sprint | Focus | Status |
|--------|-------|--------|
| **Sprint 11** | Shareable Persona Cards + Growth Features + Regional English Format | ✅ COMPLETE |
| Sprint 12 | B2B Agency Workspace + Templates Marketplace + 3rd Party API | 🔜 Next |

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


---

## 19. Sprint 7 Implementation Details — July 2025

### Backend Platform OAuth:

- **Platform Routes** (`routes/platforms.py`)
  - `GET /api/platforms/status` — Returns connection status for all platforms
  - `GET /api/platforms/connect/linkedin` — Initiates LinkedIn OAuth 2.0 flow
  - `GET /api/platforms/connect/x` — Initiates X OAuth 2.0 with PKCE
  - `GET /api/platforms/connect/instagram` — Initiates Instagram/Meta OAuth
  - `GET /api/platforms/callback/{platform}` — Handles OAuth callbacks
  - `DELETE /api/platforms/disconnect/{platform}` — Disconnects platform

- **Token Management**
  - Fernet encryption for stored access tokens
  - Automatic token refresh on expiry
  - PKCE support for Twitter/X OAuth
  - Long-lived token exchange for Instagram

### Backend Planner Agent:

- **Planner Agent** (`agents/planner.py`)
  - `get_optimal_posting_times()` — Returns best times based on platform engagement patterns
  - `get_weekly_schedule()` — Generates weekly posting schedule across platforms
  - `schedule_content()` — Schedules content job for future publishing
  - Platform-specific peak times (weekday/weekend, best days)
  - AI-powered reasoning via GPT-4o-mini
  - UOM-aware burnout risk adjustment

- **Planner API Endpoints** (`routes/dashboard.py`)
  - `GET /api/dashboard/schedule/optimal-times` — Get optimal times for platform
  - `GET /api/dashboard/schedule/weekly` — Generate weekly schedule
  - `POST /api/dashboard/schedule/content` — Schedule content for publishing
  - `GET /api/dashboard/schedule/upcoming` — List scheduled content
  - `DELETE /api/dashboard/schedule/{job_id}` — Cancel scheduled post

### Backend Publisher Agent:

- **Publisher Agent** (`agents/publisher.py`)
  - `publish_to_linkedin()` — Posts via LinkedIn UGC API
  - `publish_to_x()` — Posts tweets/threads via X API v2
  - `publish_to_instagram()` — Posts via Instagram Graph API (media container flow)
  - `publish_content()` — Unified multi-platform publishing

- **Publish API Endpoint**
  - `POST /api/dashboard/publish/{job_id}` — Immediate publishing to selected platforms

### Frontend Components:

- **Connections Page** (`pages/Dashboard/Connections.jsx`)
  - Platform cards with connection status
  - OAuth flow initiation
  - Disconnect functionality
  - Visual feedback for configured/connected states

- **Content Calendar Page** (`pages/Dashboard/ContentCalendar.jsx`)
  - Calendar grid with scheduled content markers
  - AI-powered schedule suggestions
  - Quick publish/cancel actions
  - Upcoming scheduled content list

- **Publish Panel** (`pages/Dashboard/ContentStudio/ContentOutput.jsx`)
  - Publish Now button for approved content
  - Schedule for later with date/time picker
  - Optimal time suggestions from Planner
  - Post-publish status display

### Database Schema Additions:
- `platform_tokens` — Stores encrypted OAuth tokens per user/platform
- `oauth_states` — Temporary storage for OAuth state verification
- `content_jobs.status: "scheduled"` — New status for scheduled posts
- `content_jobs.scheduled_at` — Scheduled publish datetime
- `content_jobs.scheduled_platforms` — Target platforms for scheduled post
- `content_jobs.published_at` — Actual publish timestamp
- `content_jobs.publish_results` — Results from publish attempts
- `users.platforms_connected` — Array of connected platform names


---

## 20. Sprint 8 Implementation Details — July 2025

### Repurpose Agent (`agents/repurpose.py`):

- **repurpose_content()** — Transforms content between platforms
  - Platform-specific format specs (LinkedIn, X, Instagram)
  - Thread creation for X when content exceeds 280 chars
  - Hashtag optimization per platform
  - Voice/tone preservation option
  - Uses Claude Sonnet for AI-powered adaptation

- **bulk_repurpose()** — Repurposes to multiple platforms, creates new jobs
- **get_repurpose_suggestions()** — Finds approved content ready for repurposing

**API Endpoints:**
- `POST /api/content/repurpose` — Repurpose content to multiple platforms
- `GET /api/content/repurpose/preview/{job_id}` — Preview repurposed versions
- `GET /api/content/repurpose/suggestions` — Get content ready to repurpose

### Content Series Planner (`agents/series_planner.py`):

- **6 Series Templates:**
  1. `numbered_tips` — "7 Days of X" style daily tips
  2. `journey` — Personal/professional journey chronicle
  3. `myth_busting` — Debunk misconceptions
  4. `case_study` — Deep dive analysis
  5. `behind_scenes` — Process/routine reveals
  6. `contrarian` — Challenge conventional wisdom

- **create_series_plan()** — AI generates series with:
  - Series title and description
  - Individual post outlines with hooks, key points, CTAs
  - Optimal posting schedule
  - Teasers connecting posts

- **save_series()** — Saves plan with optional start date scheduling
- **create_series_post()** — Creates content job from series post

**API Endpoints:**
- `GET /api/content/series/templates` — List available templates
- `POST /api/content/series/plan` — Create AI-powered series plan
- `POST /api/content/series/save` — Save series to database
- `GET /api/content/series` — List user's series
- `GET /api/content/series/{series_id}` — Get series detail
- `POST /api/content/series/create-post` — Create job from series post

### Anti-Repetition Engine V2 (`agents/anti_repetition.py`):

**New V2 Features:**
- **Hook Pattern Detection** — Categorizes hooks into types:
  - question, number_list, story_start, bold_claim, direct_address, curiosity_gap
  
- **analyze_hook_fatigue()** — Detects overused hook patterns
  - Tracks hook type distribution
  - Identifies overused (>40% usage) and underused hooks
  - Provides specific recommendations

- **get_content_diversity_score()** — Comprehensive diversity analysis:
  - Hook diversity score
  - Topic diversity score
  - Platform diversity score
  - Content type diversity score
  - Overall weighted score with rating

- **get_variation_suggestions()** — AI-powered suggestions to make content unique

**API Endpoints:**
- `GET /api/content/diversity/score` — Get diversity score with breakdown
- `GET /api/content/diversity/hook-analysis` — Analyze hook patterns
- `POST /api/content/diversity/suggestions` — Get AI variation suggestions

### Frontend Components:

- **Repurpose Agent Page** (`RepurposeAgent.jsx`)
  - Content selection from approved items
  - Multi-platform targeting
  - Live preview of adaptations
  - One-click repurpose creation

- **Content Library Page** (`ContentLibrary.jsx`)
  - Grid view of all content
  - Status/platform filtering
  - Search functionality
  - Series tab with progress tracking

### Database Schema Additions:
- `content_series` collection:
  - `series_id`, `user_id`, `title`, `description`
  - `posts[]` — Array of post outlines
  - `schedule[]` — Posting schedule
  - `status` — active/completed/paused
  - `completed_posts`, `total_posts`

- `content_jobs` additions:
  - `is_repurposed: bool` — Flag for repurposed content
  - `source_job_id` — Links to original content
  - `series_id` — Links to series
  - `series_post_number` — Position in series


---

## 21. Sprint 9 Implementation Details — July 2025

### Analyst Agent (`agents/analyst.py`):

- **get_content_analytics()** — Detailed analytics for specific content
  - Performance metrics (impressions, engagements, clicks, shares)
  - Performance score calculation (0-100)
  - Simulated metrics when real platform data unavailable
  - Platform-specific engagement benchmarks

- **get_analytics_overview()** — Aggregated performance summary
  - Total posts, impressions, engagements
  - Average performance score
  - Platform breakdown with per-platform stats
  - Top and bottom performing content

- **get_performance_trends()** — Time-series analysis
  - Weekly or monthly granularity
  - Trend direction detection (improving/stable/declining)
  - Performance trajectory over time

- **generate_insights()** — AI-powered recommendations
  - Key insights with data backing
  - Prioritized recommendations (high/medium/low)
  - Best performing patterns identification
  - 30-day strategic focus suggestion

**API Endpoints:**
- `GET /api/analytics/overview` — Aggregated metrics
- `GET /api/analytics/content/{job_id}` — Individual content analytics
- `GET /api/analytics/trends` — Time-series trends
- `GET /api/analytics/insights` — AI-generated insights
- `GET /api/analytics/learning` — Learning signals

### Persona Refinement Service (`services/persona_refinement.py`):

- **analyze_voice_evolution()** — Tracks voice changes over time
  - Compares early vs recent content
  - Identifies tone, structure, vocabulary shifts
  - Consistency scoring
  - Maturity direction assessment

- **suggest_persona_updates()** — AI recommendations for persona card
  - Based on learning signals and performance
  - Specific field-level suggestions
  - Confidence scoring
  - New strengths identification

- **apply_persona_refinements()** — Apply suggested updates
  - Evolution history tracking
  - Timestamp and source logging

- **get_persona_evolution_timeline()** — Full change history
  - All refinement events
  - Before/after values
  - Source of each change

**API Endpoints:**
- `GET /api/analytics/persona/evolution` — Change timeline
- `GET /api/analytics/persona/voice-evolution` — Voice analysis
- `GET /api/analytics/persona/suggestions` — AI suggestions
- `POST /api/analytics/persona/refine` — Apply updates

### Pattern Fatigue Shield:

- **get_pattern_fatigue_shield()** — Comprehensive staleness protection
  - Combines anti-repetition, diversity, trends data
  - Risk score calculation (0-100)
  - Status levels: healthy, caution, warning, critical
  - Risk factors breakdown
  - Actionable recommendations
  - Cooldown suggestions for overused patterns

**API Endpoint:**
- `GET /api/analytics/fatigue-shield` — Full fatigue analysis

### Frontend Components:

- **Analytics Dashboard** (`Analytics.jsx`)
  - Summary cards (posts, impressions, performance, engagement)
  - Pattern Fatigue Shield display
  - AI Insights panel with recommendations
  - Platform breakdown cards
  - Top performing content list

### Database Schema Additions:
- `persona_engines.evolution_history[]` — Array of refinement events
- `persona_engines.card.last_refined` — Last refinement timestamp
- `content_jobs.performance_metrics` — Real platform metrics when available
- `content_jobs.metrics_updated_at` — Last metrics sync time


---

## 22. Sprint 10 Implementation Details — July 2025

### Credit System (`services/credits.py`):

- **Credit Operations** with costs:
  - CONTENT_CREATE: 10 credits
  - CONTENT_REGENERATE: 5 credits
  - IMAGE_GENERATE: 8 credits
  - CAROUSEL_GENERATE: 15 credits
  - VOICE_NARRATION: 5 credits
  - VIDEO_GENERATE: 25 credits
  - REPURPOSE: 3 credits
  - SERIES_PLAN: 5 credits
  - AI_INSIGHTS: 2 credits
  - VIRAL_PREDICT: 1 credit

- **Balance Management**
  - get_credit_balance() — Current balance with tier info
  - deduct_credits() — Deduct for operations with transaction log
  - add_credits() — Add credits (purchase/bonus/refund)
  - get_usage_history() — Transaction history with breakdown

**API Endpoints:**
- `GET /api/billing/credits` — Current balance
- `GET /api/billing/credits/usage` — Usage history
- `GET /api/billing/credits/costs` — Operation costs
- `POST /api/billing/credits/purchase` — Purchase credits (placeholder)

### Subscription Tiers (`services/subscriptions.py`):

- **4 Tiers:**
  1. **Free** — 50 credits/mo, 1 persona, 3 posts/day, LinkedIn only
  2. **Pro** ($29/mo) — 500 credits/mo, 3 personas, 20 posts/day, all platforms, voice
  3. **Studio** ($79/mo) — 2000 credits/mo, 10 personas, 100 posts/day, video, priority support
  4. **Agency** ($199/mo) — 10000 credits/mo, 50 personas, 500 posts/day, API access

- **Feature Gating** by tier:
  - series_enabled, repurpose_enabled, voice_enabled, video_enabled
  - priority_support, api_access
  - analytics_days (7/30/90/365)

**API Endpoints:**
- `GET /api/billing/subscription` — Current subscription
- `GET /api/billing/subscription/tiers` — Available tiers
- `GET /api/billing/subscription/limits` — Feature limits and usage
- `POST /api/billing/subscription/upgrade` — Upgrade tier
- `POST /api/billing/subscription/cancel` — Cancel subscription

### Viral Hook Predictor (`agents/viral_predictor.py`):

- **Pattern Detection:**
  - Positive patterns: curiosity_gap, contrarian, number_hook, story_hook, direct_address, result_hook
  - Negative patterns: generic_opener, weak_language, clickbait_overload

- **Virality Scoring (0-100):**
  - Rule-based pattern analysis
  - AI-enhanced scoring via GPT-4.1-mini
  - Combined weighted score

- **Hook Improvement:**
  - 4 styles: curiosity, contrarian, story, number
  - Generates 3 improved versions per request
  - Predicted scores for each alternative

**API Endpoints:**
- `POST /api/viral/predict` — Predict virality score
- `POST /api/viral/improve` — Generate improved hooks
- `POST /api/viral/batch-predict` — Compare multiple hooks (A/B testing)
- `GET /api/viral/patterns` — Get pattern information

### Frontend Components:

- **Settings Page** (`Settings.jsx`)
  - Current plan display with credits bar
  - Feature limits and usage
  - Tier comparison cards
  - Upgrade/downgrade buttons

### Database Schema Additions:
- `users.credits` — Current credit balance
- `users.subscription_tier` — Current tier (free/pro/studio/agency)
- `users.subscription_started` — Subscription start date
- `users.subscription_expires` — Expiry date
- `users.subscription_auto_renew` — Auto-renewal flag
- `users.credits_last_refresh` — Last monthly credit refresh
- `credit_transactions` collection — Transaction history
- `subscription_history` collection — Tier change history



---

## 23. Sprint 11 Implementation Details — July 2025

### Shareable Persona Cards:

**Backend (`routes/persona.py`):**
- `POST /api/persona/share` — Generate public share token
  - Creates 16-byte URL-safe token
  - Default 30-day expiry (free tier), permanent for Pro+
  - Tracks view count
  - Returns share_url format: `/creator/{share_token}`

- `GET /api/persona/share/status` — Current share status
  - Returns is_shared, share_token, expires_at, view_count

- `DELETE /api/persona/share` — Revoke share link
  - Sets is_active=False on all user shares

- `GET /api/persona/public/{share_token}` — **NO AUTH REQUIRED**
  - Returns safe persona data (excludes UOM internals)
  - Includes: creator info, card, voice_metrics, share_info
  - Increments view_count on each access
  - Handles timezone-aware expiry checking

**Frontend (`pages/Public/PersonaCardPublic.jsx`):**
- Standalone public page (no sidebar, no auth)
- Beautiful gradient card design per archetype
- Displays: creator name, avatar, archetype, voice descriptor, content pillars, platforms
- Voice fingerprint visualization bars
- "Powered by ThookAI" watermark
- "Create Your Persona Card" CTA with UTM tracking
- Error states for expired/revoked/not-found links

**Frontend (`pages/Dashboard/PersonaEngine.jsx`):**
- "Share Card" button — Opens modal with share link
- Copy button with clipboard fallback for cross-browser support
- "Download" button — Uses html2canvas to export as PNG
- Share modal shows: URL input, Copy/Preview/Revoke buttons

### Regional English Formatter:

**Backend (`routes/persona.py`):**
- `GET /api/persona/regional-english/options` — Returns 4 options:
  - **US**: American spellings (-ize), MM/DD dates, standard expressions
  - **UK**: British spellings (-ise), DD/MM dates, whilst/amongst usage
  - **AU**: Australian spellings, DD/MM dates, colloquialisms (arvo, brekkie)
  - **IN**: British spellings, DD/MM dates, lakh/crore numbers, formal register

- `PUT /api/persona/regional-english` — Update preference
  - Validates code (US/UK/AU/IN only)
  - Updates persona card with regional_english field

**Backend (`agents/writer.py`):**
- `REGIONAL_ENGLISH_RULES` dict with detailed rules per region
- `_get_regional_rules()` — Returns formatted rules for writer prompt
- Writer system prompt now includes: "STRICTLY FOLLOW the regional English rules provided"
- Regional rules cover: spellings, date formats, number formats, colloquialisms

**Frontend (`pages/Dashboard/PersonaEngine.jsx`):**
- Globe icon dropdown in persona card header
- Shows flags (🇺🇸 🇬🇧 🇦🇺 🇮🇳) with region names
- Selection updates persona via API call
- Animated dropdown with checkmark for current selection

### Database Schema Additions:
- `persona_shares` collection:
  - `share_id`, `share_token`, `user_id`
  - `expires_at` — Expiry timestamp (null for permanent)
  - `created_at`, `revoked_at`
  - `view_count` — Public access counter
  - `is_active` — Active/revoked status

- `persona_engines.card.regional_english` — User's regional preference (US/UK/AU/IN)

### New Routes Added:
- `/creator/:shareToken` — Public persona card page (no auth)
