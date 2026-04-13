---
doc: user-flows
audience: co-founder + investor (UX comprehension)
voice: company (third-person)
version: v3.0-pre-launch
date: 2026-04-13
companion: PITCH-DECK.md, PROJECT-OVERVIEW.md
---

# ThookAI — User Flows

> Step-by-step walkthroughs of every meaningful user journey. Each flow shows the user action, the screen they see, the system response, and what happens behind the scenes. Written so a non-technical reader understands the product, and a technical reader understands the implementation.

---

## Personas (who actually uses ThookAI)

### Persona 1: The Solo Founder

**Name**: "Alex" (composite). 32, technical co-founder of an early-stage SaaS company. Posts on LinkedIn 2-3x/week and X daily. Spends 4-6 hours/week on content. Writes everything personally because no AI tool has matched his voice. Pain: the time cost is destroying his ability to ship product.

**What ThookAI does for Alex**: Captures his voice in 5 minutes via the persona interview. Generates content that he edits 20% of the time instead of rewriting 80%. The Strategist Agent surfaces recommendations he'd never have thought of. Result: same content output, 1/4 the time.

### Persona 2: The Indie Creator

**Name**: "Priya" (composite). 28, builds in public on X and Instagram. Has 12K followers across platforms. Monetizes via affiliate links, courses, consulting. Pain: she's burning out trying to keep up the posting schedule across 3 platforms with 3 different formats.

**What ThookAI does for Priya**: One topic, 5 platform-native variants in 90 seconds. Auto-generated carousel slides for Instagram. Voice-cloned narration for Reels. Repurpose Agent turns her best posts into 4-week content series automatically.

### Persona 3: The Boutique Agency Owner

**Name**: "Marcus" (composite). 39, owns a 6-person social media agency serving 12 clients. Junior copywriters earn $35/hr, billed at $85. Pain: AI tools haven't preserved client voice well enough to ship without rewriting. So he hires more humans, margins shrink.

**What ThookAI does for Marcus**: Each client gets their own Persona Engine. Junior writers become editors instead of writers. Production cost per post drops 70%. Margin expands. Marcus can take on 3x more clients without hiring.

---

## Flow 1 — First-time signup → first published post

**Goal**: A new user goes from "I just heard of ThookAI" to "I just published my first AI-generated post" in under 15 minutes.

### Step 1: Land on thook.ai

**User sees**: The Hero section ("Your AI Content Team. On Autopilot."), Features grid, How It Works section, Agent Council animation, pricing section, footer with "Get Started" CTA buttons.

**System**: Loads `LandingPage.jsx`. PostHog tracks `$pageview`. Cookie consent banner appears.

**User action**: Clicks "Get Started" or "Try Free".

### Step 2: Sign up

**User sees**: AuthPage with two options: "Continue with Google" or email/password form (Name, Email, Password fields).

**Behind the scenes**:

- **Google path**: Click button → redirect to Google OAuth → user authorizes → Google sends user back to `/api/auth/google/callback` → backend creates user record → JWT issued in httpOnly cookie + CSRF token in second cookie → redirect to `/onboarding`.
- **Email path**: Submit form → frontend validates with React Hook Form + Zod → POST to `/api/auth/register` → backend validates with Pydantic → password policy check → bcrypt hash → insert into `db.users` (with 200 starter credits, `subscription_tier: "starter"`, `auth_method: "email"`, `onboarding_completed: false`) → `create_jwt_token()` → set httpOnly `session_token` cookie + CSRF cookie → response includes user object + token → frontend redirects to `/onboarding`.

**User sees on success**: Loading spinner → onboarding wizard appears.

**User sees on failure**: Toast error: "Email already registered" or "Password must be at least 8 characters with one uppercase, one digit, one special character".

**System guards**:

- Account lockout: 5 failed login attempts → 15-min lockout
- Rate limit: 10 auth requests per minute per IP
- XSS sanitization: name field passed through `sanitize_text()` before insert
- Idempotent: duplicate emails are caught at the unique index level

### Step 3: Onboarding wizard — Phase 1 (Welcome)

**User sees**: 3-phase wizard. Phase 1 is the welcome screen with progress bar (1/3), brand intro, and "Let's go" button.

**Behind the scenes**: `Onboarding/PhaseOne.jsx` renders. Wizard state persisted to `db.onboarding_sessions` (24h TTL) so users can resume.

### Step 4: Onboarding wizard — Phase 2 (The 7 Questions)

**User sees**: 7 questions, presented one at a time with smooth transitions:

| #   | Question                               | Example answer                                                                                                   |
| --- | -------------------------------------- | ---------------------------------------------------------------------------------------------------------------- |
| 1   | What's your main content focus?        | "B2B SaaS marketing, AI tools, founder-led growth"                                                               |
| 2   | Who is your target audience?           | "Solo founders building $0-1M ARR SaaS"                                                                          |
| 3   | What content style resonates with you? | "Story-driven with concrete tactics, not generic advice"                                                         |
| 4   | How often do you want to post?         | "Daily on LinkedIn, 3-5x/week on X, 2x/week on Instagram"                                                        |
| 5   | Which platforms?                       | LinkedIn (selected), X (selected), Instagram (selected)                                                          |
| 6   | What's your goal with content?         | "Build a personal brand that drives inbound leads to my product"                                                 |
| 7   | What's unique about your perspective?  | "I've shipped 4 AI products in 6 months as a solo founder. I write from in-the-trenches experience, not theory." |

**Optional**: "Upload writing samples" — drag-drop 1-5 of the user's previous posts. ThookAI runs a writing analysis pass to extract lexical patterns, sentence rhythm, and signature phrases.

**Behind the scenes**: Each answer saved to `db.onboarding_sessions` immediately (save-as-you-go). Sample analysis runs through `backend/agents/onboarding/voice_analyzer.py`.

### Step 5: Onboarding wizard — Phase 3 (Persona Generation)

**User sees**: Loading animation: "Building your Persona Engine..." (8-15 seconds).

**Behind the scenes**: POST to `/api/onboarding/generate-persona`. Backend:

1. Loads onboarding session from `db.onboarding_sessions`
2. Calls `generate_persona_card()` with all 7 answers + writing samples
3. LLM (Anthropic Claude Sonnet 4.5) generates the Persona Card with archetype, voice descriptor, content pillars, hook style, target audience
4. Inserts into `db.persona_engines` keyed by `user_id`
5. Updates `db.users.onboarding_completed = true`
6. Returns the Persona Card JSON

**User sees**: Persona Card reveal animation. The card displays:

- **Archetype**: "The Builder" (one of: Educator / Storyteller / Provocateur / Builder)
- **Voice descriptor**: "Direct, story-driven, technically grounded with a tendency toward concrete numbers and lived-experience anecdotes"
- **Content pillars**: ["AI product building", "Solo founder economics", "AI tooling reviews", "Bootstrapping playbooks"]
- **Hook style**: "Curiosity-gap with stakes" (e.g. "I shipped 4 AI products in 6 months. Here's what 90% of founders get wrong.")
- **Target audience**: "Solo founders building $0-1M ARR AI/SaaS products who optimize for speed and learning"

**User can edit any field** (inline editing on the Persona Card). Edits are saved via PUT `/api/persona/me`.

**User action**: Clicks "Continue to Dashboard".

### Step 6: First-time dashboard arrival

**User sees**: DashboardHome with:

- Welcome message: "Welcome to ThookAI, [Name]"
- Stats card: "200 credits available", "0 posts created", "0 posts published"
- Daily Brief card with 3 starter recommendations from the Strategist Agent (generated based on the Persona)
- Big primary CTA button: "Create Your First Post"
- Sidebar with all dashboard sections highlighted

**Behind the scenes**:

- GET `/api/dashboard/stats` returns user stats
- GET `/api/dashboard/daily-brief/status` returns the brief
- Strategist Agent runs a "first-time" path that generates 3 generic-but-persona-aware recommendations even before the user has any history

### Step 7: First content generation

**User action**: Clicks "Create Your First Post".

**User sees**: Content Studio. Big text input field "What do you want to write about?". Platform tabs (LinkedIn / X / Instagram). Format dropdown (post / article / carousel for LinkedIn; tweet / thread for X; feed / reel / story for Instagram).

**User types**: "How I shipped 4 AI products in 6 months as a solo founder"

**User selects**: LinkedIn → article

**User clicks**: "Generate"

**Behind the scenes**:

1. POST `/api/content/create` with `{platform: "linkedin", content_type: "article", raw_input: "..."}`
2. Backend validates with Pydantic
3. Sanitizes input via `sanitize_text()`
4. Checks credits (article = ~15 credits)
5. Decrements credits via `db.users.update_one({user_id}, {$inc: {credits: -15}})` (atomic)
6. Inserts a `content_jobs` record with status `pending`
7. Triggers Celery task `tasks.content_tasks.run_pipeline(job_id)` in the `content` queue
8. Returns `{job_id}` to frontend

**User sees**: Loading screen with progress indicator: "Commander parsing intent → Scout researching → Thinker strategizing → Writer generating → QC reviewing". Progress updates via SSE or polling.

**Behind the scenes (the pipeline)**:

1. **Commander** loads the Persona Engine, parses intent, builds JobSpec (5s)
2. **Scout** queries Perplexity for fresh stats on solo founder economics + queries the user's LightRAG for any uploaded notes (8s)
3. **Thinker** chooses angle: "Counter-narrative — most founders fail because they over-engineer; here's the lean playbook". Picks hook variant from 3 options. Anti-repetition check passes (no similar past posts) (4s)
4. **Writer** generates the LinkedIn article (~600 words) using the persona voice fingerprint + "The Builder" archetype + UOM directives (12s)
5. **QC** scores: persona_match=9/10, ai_risk=15/100, platform_fit=10/10, slop_pass=true (3s)
6. **Consigliere** flags no risks, action=approve (4s)
7. Pipeline updates `content_jobs` with status `reviewing`, fills `final_content`, `persona_match_score`, `hook_used`, `predicted_engagement`

**Total wall clock**: ~36 seconds.

### Step 8: First content review

**User sees**: ContentOutput page with:

- The generated LinkedIn article (formatted, ready to publish)
- Persona Match Score: 9/10 with green badge
- Hook variants (3 alternatives shown — user can swap)
- "Edit", "Regenerate", "Approve", "Schedule", "Publish Now" buttons
- "Add Image", "Add Video", "Add Voice" media generation buttons
- Predicted engagement: "Above your average"
- Anti-fatigue check: "Hook style is fresh — your last 5 posts used 'How I' style; this uses counter-narrative"

**User action**: Clicks "Add Image".

**Behind the scenes**:

- POST `/api/content/job/{id}/generate-media` with `{type: "cover_image", style: "professional"}`
- Triggers `tasks.media_tasks.generate_image_for_job(job_id)` in the `media` queue
- Designer agent picks FAL.ai Flux Pro
- Generates image
- Anti-slop vision check passes
- Uploads to R2 via presigned URL
- Updates `media_assets` collection
- Sends SSE notification to frontend

**User sees**: Image preview appears next to the article. Total elapsed: ~25 seconds.

**User action**: Clicks "Publish Now".

**Behind the scenes**:

1. POST `/api/dashboard/publish/{job_id}`
2. Backend checks if user has connected LinkedIn account in `db.platform_tokens`
3. If not connected: returns 400, frontend prompts user to connect

**User sees** (if not connected): Modal: "Connect your LinkedIn account to publish". "Connect LinkedIn" button.

### Step 9: Connect LinkedIn (first time)

**User clicks**: "Connect LinkedIn"

**Behind the scenes**:

1. GET `/api/platforms/connect/linkedin`
2. Backend generates a state token, stores in `db.oauth_states` (10-min TTL)
3. Returns LinkedIn OAuth URL
4. Frontend redirects browser to LinkedIn

**User sees**: LinkedIn OAuth consent screen — "ThookAI wants to access your profile and post on your behalf"

**User clicks**: "Allow"

**Behind the scenes**:

1. LinkedIn redirects to `/api/platforms/callback/linkedin?code=...&state=...`
2. Backend verifies state token
3. Exchanges code for access_token + refresh_token
4. Encrypts tokens via Fernet
5. Stores in `db.platform_tokens` with `user_id + platform: "linkedin"`
6. Updates `db.users.platforms_connected += "linkedin"`
7. Redirects browser to `/dashboard/connections?success=linkedin`

**User sees**: Connections page with green checkmark next to LinkedIn.

### Step 10: Publish

**User action**: Goes back to ContentOutput, clicks "Publish Now" again.

**Behind the scenes**:

1. POST `/api/dashboard/publish/{job_id}`
2. Publisher agent loads the encrypted LinkedIn token
3. Decrypts via Fernet
4. Checks if token expires within 24h → refreshes proactively if so
5. Uploads media asset to LinkedIn (image registration via UGC API)
6. Posts the article via LinkedIn UGC API
7. Captures the LinkedIn post URN
8. Updates `content_jobs.status = "published"`, `published_at = now`, `platform_post_id = urn:li:share:...`
9. Schedules analytics polling jobs: 24h-poll and 7d-poll into `content_jobs.analytics_24h_due_at` and `analytics_7d_due_at`
10. Returns `{success: true, post_url: "https://linkedin.com/posts/..."}`

**User sees**: Toast: "Published to LinkedIn!" with a clickable link. Stats card updates: "1 post published".

### Step 11: 24 hours later — Analytics roll in

**Behind the scenes** (no user action):

1. Celery Beat fires every 5 minutes
2. `process-scheduled-posts` task picks up posts where `analytics_24h_due_at <= now` and `analytics_24h_polled = false`
3. Calls LinkedIn UGC organizational insights API
4. Captures: impressions, engagements, clicks, comments, shares
5. Updates `content_jobs.performance_data.latest`
6. Marks `analytics_24h_polled = true`
7. Sets `analytics_7d_due_at = published_at + 7 days`
8. Triggers persona refinement: `services/persona_refinement.py.update_from_engagement()`
9. If engagement is above the user's average, the hook style gets a positive signal in `learning_signals`
10. Strategist Agent's next nightly run will use this as input

**User sees the next morning**: Daily Brief notification: "Your post yesterday performed 3x your average. Here's what to write next."

**Total elapsed from signup to first published post: 12-15 minutes.**

---

## Flow 2 — The Daily Returning User Loop (the core value flywheel)

**Goal**: An existing user opens the app → reviews Strategist recommendations → approves a recommendation → generates content → schedules → closes the app. Total time: 3-5 minutes.

### Step 1: User opens dashboard

**User sees**: DashboardHome with:

- Stats: "147 credits remaining", "23 posts created", "12 posts published"
- Daily Brief: "3 high-priority recommendations based on your week's performance"
- Recent activity feed
- Strategist recommendation cards (3-5 cards visible)

**Behind the scenes**:

- The Strategist Agent ran overnight at 03:00 UTC via Celery Beat
- It synthesized: the user's LightRAG knowledge graph + the past 30 days of analytics + recent content history + UOM behavioral signals
- Generated 5 ranked recommendation cards
- Inserted into `db.strategy_recommendations`
- SSE pushes them to the dashboard on connection

### Step 2: Browse recommendations

**User sees** each card with:

- Topic title: "Counter-narrative on AI hype: why most LLM features ship to dead silence"
- Reasoning: "Your audience engaged 4x more on contrarian posts in the last 14 days. This topic touches on a debate happening in your network this week."
- Suggested platforms: LinkedIn (article) + X (thread)
- Estimated cost: 25 credits
- Buttons: "Approve" / "Modify" / "Dismiss" / "Save for later"

### Step 3: One-click approve

**User clicks**: "Approve" on the top card.

**Behind the scenes**:

1. POST `/api/strategy/recommendations/{id}/accept`
2. Backend creates 2 content_jobs (one per platform) pre-populated with the recommendation's JobSpec
3. Triggers both pipelines in parallel (LinkedIn article + X thread)
4. Returns `{jobs: [job_id_li, job_id_x]}`

**User sees**: Loading screen showing both pipelines running simultaneously.

### Step 4: Review parallel outputs

**User sees**: Two completed content cards side by side:

- LinkedIn article (~600 words, full-length, professional tone)
- X thread (8 tweets, punchy, emoji-light, threaded structure)

Both share the same core insight but are platform-native — not just truncated versions of each other.

**Anti-fatigue check** has been applied to both — the hook for the X thread is different from the LinkedIn opener, ensuring variety even within a single approval action.

### Step 5: Schedule

**User clicks**: "Schedule both" → "Tomorrow at optimal time"

**Behind the scenes**:

1. POST `/api/dashboard/schedule` for each job
2. Backend reads the user's `persona.optimal_posting_times` (computed from past engagement data)
3. For LinkedIn: optimal time = "Tuesday 9:15 AM PST"
4. For X: optimal time = "Tuesday 11:30 AM PST"
5. Inserts into `db.scheduled_posts` with `schedule_id`, `platform`, `scheduled_at`, `status: "scheduled"`
6. Returns confirmation

**User sees**: Toast: "Scheduled. LinkedIn at 9:15 AM, X at 11:30 AM tomorrow. View in calendar."

### Step 6: User closes app

**Total time**: 3-5 minutes for 2 fully-formed pieces of content scheduled to publish at AI-optimized times.

### Step 7: Tomorrow — Celery Beat publishes

**Behind the scenes**:

1. Every 5 minutes, `process-scheduled-posts` Celery task runs
2. Queries `db.scheduled_posts` for `scheduled_at <= now AND status = "scheduled"`
3. For each match, calls Publisher agent
4. Publisher loads encrypted token, refreshes if needed, posts to platform
5. Updates `scheduled_posts.status = "published"`, `published_at = now`
6. Triggers analytics scheduling (24h + 7d polling)

### Step 8: 24 hours later — Learning loop closes

- Analytics flow back into the Persona Engine
- Strategist Agent's next nightly run uses the new data
- Tomorrow's recommendations get smarter

**This is the core flywheel.** The longer a user stays on ThookAI, the smarter the Strategist gets, the more accurate the recommendations become, the higher the engagement, the better the next round of recommendations.

---

## Flow 3 — Repurpose Flow (1 piece of content → 5 platform variants)

**Goal**: A user has a blog post, podcast transcript, or LinkedIn article they want to repurpose across all platforms.

### Step 1: User opens Repurpose Agent

**User action**: Clicks "Repurpose Agent" in the sidebar.

**User sees**: A page with a big text input ("Paste your content here") and platform/format checkboxes:

- ☐ LinkedIn post (300 words)
- ☐ LinkedIn article (800+ words)
- ☐ X tweet (single)
- ☐ X thread (5-15 tweets)
- ☐ Instagram caption (feed)
- ☐ Instagram caption (reel)
- ☐ Carousel slides (5-10 slides)

### Step 2: Paste source content + select targets

**User pastes**: A 1500-word blog post.
**User selects**: LinkedIn post, X thread, Instagram carousel.
**User clicks**: "Repurpose"

### Step 3: Pipeline runs in parallel

**Behind the scenes**:

1. POST `/api/content/repurpose` with the source + 3 targets
2. Backend creates 3 `content_jobs` records with `is_repurposed: true` and `source_content_id` linking to the original
3. Triggers the Repurpose Agent (`backend/agents/repurpose.py`) which runs all 3 in parallel
4. Each variant goes through the standard 5-agent pipeline but with the "repurpose" mode flag, which:
   - Tells Commander the content already has structure — just adapt it to the platform
   - Tells Scout to skip research (the source already provides it)
   - Tells Thinker to find the best 3-7 atomic insights to extract
   - Tells Writer to write platform-native, not summarize
5. Returns 3 job_ids

**User sees**: Loading screen with 3 parallel progress bars.

### Step 4: Review and approve

**User sees**: Three completed variants side by side. Each platform-native, not just truncated.

**User clicks**: "Approve all" → "Schedule across the next 7 days"

**Behind the scenes**: ThookAI distributes the 3 posts across 7 days at each platform's optimal time.

**Total elapsed**: 60 seconds for 3 fully-formed, scheduled posts from one source.

---

## Flow 4 — Media Generation Flow (text post → carousel + video + voice)

**Goal**: A user has a great LinkedIn article and wants to amplify it with multi-format media.

### Step 1: Open existing post

**User action**: From ContentLibrary, opens a previously generated LinkedIn article.

### Step 2: Add image

**User clicks**: "Add Image"
**User sees**: Modal with style options (Professional / Editorial / Bold / Minimalist / Custom prompt).
**User selects**: "Editorial"
**User clicks**: "Generate"

**Behind the scenes**:

1. POST `/api/content/job/{id}/generate-media`
2. Designer agent calls FAL.ai Flux Pro with a prompt derived from the article + style
3. Anti-slop vision check (rejects if image looks AI-generated in a tacky way)
4. Uploads to R2 via presigned URL
5. Inserts into `db.media_assets` with `job_id`, `type: "image"`, `url`, `status: "ready"`
6. Returns the asset

**User sees**: Image appears in 8-15 seconds. Approve / Regenerate / Variations buttons.

### Step 3: Generate carousel

**User clicks**: "Convert to Carousel"
**User sees**: Modal asking how many slides (5-15), style choice.
**User selects**: 7 slides, "Bold typographic"

**Behind the scenes**:

1. POST `/api/content/job/{id}/generate-carousel`
2. Designer + Visual agents collaborate:
   - Visual extracts 7 atomic ideas from the article
   - Designer generates slide compositions via Remotion
   - Each slide is a 1080x1080 PNG with text + accent color
3. Uploads all 7 slides to R2
4. Inserts media_assets row of type "carousel"

**User sees**: 7 slides in 30-60 seconds. Drag to reorder, click to edit text.

### Step 4: Generate short video

**User clicks**: "Convert to Reel"
**User sees**: Modal with provider choice (Runway / Luma / Kling) and length (15s / 30s / 60s).
**User selects**: Luma Dream Machine, 30 seconds.

**Behind the scenes**:

1. POST `/api/content/job/{id}/generate-video`
2. Video agent calls Luma API
3. Polls for completion (Luma takes 60-180s)
4. Downloads the MP4
5. Uploads to R2
6. Inserts media_asset

**User sees**: Video preview in ~2 minutes. Plays inline.

### Step 5: Generate voice narration

**User clicks**: "Add Voice"
**User sees**: Modal — choose from voice library OR use cloned voice (if user uploaded one).
**User selects**: Their cloned voice.

**Behind the scenes**:

1. POST `/api/content/job/{id}/generate-voice`
2. Voice agent calls ElevenLabs with the user's cloned voice ID + the article text (truncated to first 60 seconds of speech)
3. Receives MP3
4. Uploads to R2

**User sees**: Audio waveform appears in 10-30 seconds.

### Step 6: Schedule the multi-format package

**User sees**: All 5 assets attached to the post (article + image + carousel + video + voice).

**User clicks**: "Schedule":

- LinkedIn article + image → LinkedIn at optimal time
- Carousel → Instagram feed
- Video → Instagram Reel + LinkedIn (as native upload)
- Voice → repackaged as standalone "audio note" content type

**Total elapsed**: 5-10 minutes for a complete multi-format content package across 4 platforms.

---

## Flow 5 — Billing Flow (free → paid via Custom Plan Builder)

**Goal**: A user has used most of their starter credits and wants to upgrade.

### Step 1: User hits credit limit

**User sees**: After clicking "Generate" on a post, a modal: "You have 8 credits remaining. This action requires 15 credits. Add credits to continue."

**Buttons**: "Buy Credits" / "Upgrade Plan"

### Step 2: User clicks "Upgrade Plan"

**User sees**: Custom Plan Builder page (no traditional 4-tier pricing). It looks like a calculator:

| Operation                  | Per month       |
| -------------------------- | --------------- |
| Text posts (full pipeline) | [slider: 0-200] |
| Text regenerations         | [slider: 0-100] |
| AI images                  | [slider: 0-100] |
| Carousel slides            | [slider: 0-50]  |
| Short videos               | [slider: 0-30]  |
| Voice narrations           | [slider: 0-50]  |
| Series plans               | [slider: 0-20]  |
| Repurposes                 | [slider: 0-100] |

As the user moves sliders, the bottom of the page updates in real time:

- Total credits/month
- Volume tier (Starter / Growth / Scale / Enterprise)
- Price per credit at this volume
- Total monthly cost

**Example**: 50 text posts (500 cr) + 30 images (240 cr) + 10 carousels (150 cr) + 5 videos (125 cr) = 1015 credits → Scale tier @ $0.045/credit = **$45.68/month**

### Step 3: User clicks "Subscribe"

**Behind the scenes**:

1. POST `/api/billing/plan/checkout` with the plan config
2. Backend calls `services/stripe_service.create_checkout_session()`
3. Creates a Stripe Checkout Session with line items derived from the plan
4. Returns Stripe Checkout URL

**User sees**: Redirected to Stripe Checkout (hosted by Stripe).

### Step 4: User completes payment

**Behind the scenes**:

1. Stripe processes payment
2. Stripe sends webhook to `/api/billing/webhook/stripe`
3. Backend verifies signature
4. Idempotency check via `db.stripe_events`
5. Looks up `customer_id` → maps to `user_id`
6. Updates `db.users`:
   - `subscription_tier: "custom"`
   - `plan_config: {...}`
   - `monthly_credits: 1015`
   - `credits: 1015`
   - `credit_allowance: 1015`
   - `subscription_status: "active"`
   - `stripe_subscription_id: "sub_..."`
7. Inserts into `subscription_history`
8. Returns 200 to Stripe
9. Stripe redirects user back to ThookAI success page

**User sees**: "Welcome to your custom plan. 1015 credits available." Confetti animation.

### Step 5: First post on the new plan

Everything works as before, but the credit counter is now much higher. Monthly auto-renewal happens via Stripe with no further action from the user.

### Step 6: Mid-month — user wants more credits

**User clicks**: "Add Credits" (smaller one-time top-up).
**User sees**: Three packs: 100 / 500 / 1000 credits (each a Stripe Price ID).
**User clicks**: "500 credits — $25"
**Behind the scenes**: Same Stripe Checkout flow but for a one-time payment. Webhook handler increments `db.users.credits` without changing the subscription.

---

## Flow 6 — Connect Social Platforms (LinkedIn / X / Instagram)

**Goal**: A user connects all 3 social platforms so ThookAI can publish on their behalf.

### Step 1: Open Connections page

**User sees**: Connections page with 3 cards: LinkedIn, X, Instagram. Each shows status: "Not connected" with a "Connect" button.

### Step 2: Connect LinkedIn (described in Flow 1, Step 9)

After clicking through LinkedIn OAuth, the user returns to the Connections page with LinkedIn now showing:

- ✅ Connected
- Account name: "Alex Founder"
- Connected: 2 days ago
- Token expires: in 60 days
- Disconnect button

### Step 3: Connect X

**User clicks**: "Connect" next to X.

**Behind the scenes** (X requires OAuth 2.0 PKCE):

1. GET `/api/platforms/connect/x`
2. Backend generates state token + PKCE code_verifier + code_challenge
3. Stores state + verifier in `db.oauth_states`
4. Redirects to X OAuth URL with code_challenge

**User sees**: X authorization page → grants access → redirects back.

**Behind the scenes**:

1. Callback `/api/platforms/callback/x?code=...&state=...`
2. Backend retrieves verifier from oauth_states
3. Exchanges code + verifier for access_token + refresh_token via X v2 token endpoint
4. Encrypts tokens via Fernet
5. Stores in `db.platform_tokens`
6. Updates `db.users.platforms_connected += "x"`

**User sees**: X card now shows ✅ Connected.

### Step 4: Connect Instagram

**User clicks**: "Connect" next to Instagram.

**Behind the scenes** (Instagram requires Meta Graph + business account):

1. GET `/api/platforms/connect/instagram`
2. Backend redirects to Facebook OAuth URL (Meta sits in front)
3. User authorizes
4. Callback `/api/platforms/callback/instagram?code=...`
5. Backend exchanges code for short-lived token
6. Exchanges short-lived for long-lived (60-day) via `fb_exchange_token`
7. Lists user's Facebook Pages
8. For the first page with an Instagram business account, gets the Instagram business account ID
9. Encrypts and stores: long-lived token + Instagram account ID
10. Updates `db.users.platforms_connected += "instagram"`

**User sees**: Instagram card now shows ✅ Connected with the Instagram account name.

### Step 5: ThookAI proactively manages tokens

**Behind the scenes** (no user action):

- Every time `get_platform_token()` is called, it checks if the token expires within 24h
- If yes, it triggers a proactive refresh BEFORE the platform sees a stale token
- For LinkedIn/X: standard refresh_token grant
- For Instagram: `fb_exchange_token` with the current access token
- Updates `db.platform_tokens.expires_at` and `db.platform_tokens.access_token`

**User never sees a "your token expired" error.** This is a quiet differentiator.

---

## Flow 7 — GDPR Self-Service (Export & Delete)

**Goal**: A user wants to export all their data, or permanently delete their account.

### Flow 7a — Data export

**User action**: Settings → Data tab → "Export My Data" button.

**Behind the scenes**:

1. GET `/api/auth/export`
2. Backend reads from 12 collections:
   - `users` (without password hash)
   - `persona_engines` (full)
   - `content_jobs` (last 500)
   - `credit_transactions` (last 500)
   - `platform_tokens` (REDACTED — only platform name + connected_at)
   - `user_feedback` (last 100)
   - `uploads` (last 200)
   - `scheduled_posts` (last 500)
   - `media_assets` (last 500)
   - `workspace_memberships`
   - `templates` (authored)
3. Serializes to JSON
4. Returns as `Content-Disposition: attachment; filename=thookai-export-{user_id}.json`

**User sees**: Browser download dialog. JSON file saved.

### Flow 7b — Account deletion

**User action**: Settings → Data tab → "Delete Account" button.

**User sees**: Confirmation dialog: "This will permanently anonymize your account. Type DELETE to confirm." Plus a checkbox: "I understand this is irreversible".

**User types**: "DELETE", clicks Confirm.

**Behind the scenes**:

1. POST `/api/auth/delete-account` with `{confirm: "DELETE"}`
2. Backend confirms the literal string match
3. Anonymizes `db.users`:
   - `email = "deleted-{user_id}@anonymized.thookai"`
   - `name = "Deleted User"`
   - `hashed_password = ""`
   - `picture = null`
   - `active = false`
   - `deleted_at = now`
   - `google_id = null`
   - `stripe_customer_id = null`
4. Deletes `db.persona_engines` for this user
5. Deletes `db.platform_tokens` for this user (revokes social access)
6. Deletes `db.user_sessions` (logs them out everywhere)
7. Anonymizes content jobs (keeps for analytics, removes PII): `user_id = "deleted-{first_8_chars}"`, `raw_input = "[deleted]"`
8. Deletes `db.uploads`
9. Deletes `db.user_feedback`
10. Clears auth + CSRF cookies in response
11. Returns 200

**User sees**: Logged out, redirected to landing page with message: "Your account has been deleted. All personal data has been anonymized."

### What's preserved (anonymized, not deleted)

- Aggregated content statistics (used for platform-wide analytics)
- Stripe payment history (legal requirement for tax records)
- R2 media files (currently retained — flagged for v3.1 cleanup batch job)

### What's NOT preserved

- Personal identity (email, name, picture)
- Persona Engine
- Platform tokens (revoked + deleted)
- Uploaded context files
- Direct user feedback

---

## Flow 8 — Agency Workspace Flow (multi-user)

**Goal**: A boutique agency owner wants to manage 5 client personas in one ThookAI account.

### Step 1: Create workspace

**User action**: Settings → Agency tab → "Create Workspace"
**User sees**: Modal: "Workspace name", "Plan size estimate"
**User submits**: "Acme Marketing Agency", "5 clients"

**Behind the scenes**:

1. POST `/api/agency/workspaces`
2. Backend creates `db.workspaces` record with `owner_id = current_user.user_id`
3. Adds the owner as the first `db.workspace_members` with role: `owner`

### Step 2: Invite team members

**User clicks**: "Invite Team Member"
**User submits**: `john@acme.com`, role: `editor`

**Behind the scenes**:

1. POST `/api/agency/workspaces/{ws_id}/invite`
2. Backend creates pending `db.workspace_members` row with `email`, `status: "pending"`, `invite_id`
3. Sends invite email via Resend with a signed invite link
4. John receives email, clicks link → account creation flow → joined the workspace

### Step 3: Create client persona

**User action**: Inside the workspace, clicks "Add Client"
**User sees**: Each client gets their OWN onboarding flow — separate from the user's personal persona.
**User runs through**: 7 questions for Client 1, then Client 2, etc.

**Behind the scenes**: Each client persona is a separate `persona_engines` record scoped to the workspace.

### Step 4: Generate content for a specific client

**User action**: Inside the workspace, switches client context via dropdown.
**User sees**: Client-specific Persona Card + Content Studio operating in that client's voice.

**Behind the scenes**: Every content_job has `workspace_id` + `client_persona_id` to scope the persona used.

### Step 5: Approval workflow (Pro feature)

**Editor generates content** → status: `awaiting_approval`
**Owner reviews** → clicks Approve → status: `approved` → can then schedule/publish
**Editor cannot publish directly without approval.**

### Step 6: Workspace billing

**Behind the scenes**: Workspace usage is billed to the owner's account. Volume tier pricing applies — agency workspaces typically operate at 5000-20000+ credits/month, deep into the Scale or Enterprise tier ($0.045 or $0.035/credit).

---

## Flow 9 — Admin Flow (admin role only)

**Goal**: A platform admin wants to view system health, user counts, and recent activity.

### Step 1: Admin navigates to /admin

**User sees**: Admin Dashboard with:

- System health card (DB / Redis / R2 / LLM all green)
- Total users
- Active users (24h / 7d / 30d)
- Daily content jobs created
- Daily revenue (from Stripe)
- Recent errors (Sentry summary)
- User search

**Behind the scenes**:

- GET `/api/admin/system-health` returns service status
- GET `/api/admin/daily-stats?days=30` returns aggregated counts
- GET `/api/admin/users?search=...` returns user list
- All admin endpoints check `current_user.role == "admin"` — non-admins get 403

### Step 2: Admin investigates a user

**Admin clicks**: A user in the list.
**Admin sees**: User detail page with: account info, subscription tier, credits, content count, last login, action history.

### Step 3: Admin support actions

**Available actions** (audit-logged):

- Reset user password (sends new reset link)
- Refund credits
- Comp credits (give free credits)
- Mark user as banned
- View Sentry events for this user

---

## Flow Summary

| Flow                             | Steps | Time               | Frontend file                                     | Backend route                                                                                                                      | Notes                                     |
| -------------------------------- | ----- | ------------------ | ------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------- |
| 1. Signup → first published post | 11    | 12-15 min          | AuthPage, Onboarding/, ContentStudio, Connections | /api/auth/register, /api/onboarding/generate-persona, /api/content/create, /api/platforms/connect/linkedin, /api/dashboard/publish | The make-or-break first impression        |
| 2. Daily returning user loop     | 8     | 3-5 min            | DashboardHome, StrategyDashboard, ContentOutput   | /api/strategy/recommendations, /api/strategy/.../accept                                                                            | The core flywheel                         |
| 3. Repurpose flow                | 5     | 60s for 3 variants | RepurposeAgent                                    | /api/content/repurpose                                                                                                             | Massive time-saver                        |
| 4. Media generation              | 7     | 5-10 min           | ContentOutput                                     | /api/content/job/{id}/generate-media (image / carousel / video / voice)                                                            | The amplification feature                 |
| 5. Billing flow                  | 6     | 3 min              | PlanBuilder, Stripe Checkout                      | /api/billing/plan/checkout, /api/billing/webhook/stripe                                                                            | Custom plan builder is the differentiator |
| 6. Connect platforms             | 5     | 5 min              | Connections                                       | /api/platforms/connect/{platform}, callbacks                                                                                       | OAuth round-trip for all 3                |
| 7. GDPR self-serve               | 2     | <1 min             | Settings/Data                                     | /api/auth/export, /api/auth/delete-account                                                                                         | Compliance + trust                        |
| 8. Agency workspace              | 6     | 15 min setup       | Agency Workspace                                  | /api/agency/workspaces                                                                                                             | Pro tier feature                          |
| 9. Admin flow                    | 3     | varies             | Admin                                             | /api/admin/\*                                                                                                                      | Admin role only                           |

---

## Cross-flow notes

### Loading + error states

Every flow has loading states (spinners, skeletons, animated progress bars) and error states (toasts, modal dialogs, retry buttons). Verified across 38 pages in the Phase 32 frontend audit.

### Mobile responsive

All flows work at 375px (iPhone SE), 768px (iPad), and 1440px (desktop). Verified in Phase 32.

### Empty states

First-time users see helpful empty state messages on every page (e.g., "No content yet — create your first post" with a CTA button).

### Keyboard navigation

All flows are keyboard accessible (Tab, Enter, Esc) — important for power users and accessibility.

### Notifications

Important events (job complete, scheduled post published, billing event) trigger an in-app SSE notification in the bell icon. Optional email digest available.

### Audit trail

Every meaningful user action is captured in either `db.content_jobs`, `db.scheduled_posts`, `db.credit_transactions`, or `db.workspace_members`. This means we can always reconstruct what happened to any user account.

---

_This document maps every meaningful user journey through ThookAI v3.0. Pair it with `PITCH-DECK.md` (narrative) and `PROJECT-OVERVIEW.md` (architecture) for a complete picture._

_Last updated: 2026-04-13_
