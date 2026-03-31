# Project Research Summary

**Project:** ThookAI v2.0 — Intelligent Content Operating System
**Domain:** AI-powered content platform with proactive intelligence, knowledge graph retrieval, multi-model media orchestration, and workflow automation
**Researched:** 2026-04-01
**Confidence:** MEDIUM-HIGH

## Executive Summary

ThookAI v2.0 transforms from a reactive content creation tool (user asks, AI writes) into a proactive content operating system (AI observes, recommends, and orchestrates). The research confirms that the market window for this positioning is real — no direct competitor (Taplio, Supergrow, Buffer) combines knowledge graph retrieval over personal content history with a proactive strategist agent. The recommended architecture is a sidecar-services pattern: n8n for observable workflow orchestration, LightRAG for entity-relationship knowledge graphs, Remotion for composited video output, and a new Strategist Agent that synthesizes all three into ranked daily recommendations. The existing FastAPI + MongoDB + Redis stack needs no replacement — every new component integrates over HTTP, not Python imports.

The most critical architectural decision is what to keep in Celery versus what to move to n8n. The research is unambiguous: move cron-scheduled tasks and external-API tasks (publishing, analytics polling, credit resets, Strategist triggers) to n8n for auditability; keep Celery for tasks that require tight FastAPI coupling (image/video generation tasks that call Motor async directly). This hybrid approach avoids the anti-pattern of routing Motor async calls through HTTP just to fit the n8n model. The dependency chain is firm: n8n publishing must work before analytics data flows, analytics data must flow before LightRAG has meaningful signal, and LightRAG must be populated before the Strategist produces non-generic recommendations.

The top risks are operational rather than technical. Dual-execution during the Celery-to-n8n migration is the single most likely production failure — a strict one-at-a-time cutover protocol with idempotency keys on every scheduled-post publish operation is mandatory. LightRAG's embedding model lock-in means the OpenAI embedding model must be chosen before the first document is ingested, with no migration path afterwards without full index rebuild. The Strategist Agent's recommendation feed will destroy user trust within days if cadence controls (max 3 cards/day, 14-day dismissal suppression) are not built into the first version. These are not polish items — they are launch blockers.

---

## Key Findings

### Recommended Stack

The v1.0 stack (FastAPI, Motor, React, Redis, Celery, Pinecone, Anthropic, fal.ai, Luma, HeyGen, ElevenLabs, Stripe, Cloudflare R2) is validated and carries forward unchanged. v2.0 adds four new components, all integrated over HTTP rather than as Python dependencies.

**Core new technologies:**

- **n8n (Docker, `stable` tag) + PostgreSQL 15:** Visual workflow orchestrator replacing Celery beat for scheduled/external tasks. Built-in LinkedIn/X/Instagram nodes eliminate custom publisher code. Requires PostgreSQL for queue mode (SQLite is explicitly unsupported). Redis already in stack serves as queue broker with no config change needed.
- **`lightrag-hku==1.4.12` (sidecar container):** Knowledge graph layer with entity/relationship extraction. Runs as a separate FastAPI service to avoid Python dependency conflicts with ThookAI's `fastapi==0.110.1`. Use MongoDB storage backends (`MongoKVStorage`, `MongoDocStatusStorage`) against a separate database (`thookai_lightrag`). Use `NanoVectorDBStorage` for embeddings — do NOT use `MongoVectorDBStorage` (requires Atlas Vector Search). Embedding model must be `text-embedding-3-small` and locked permanently.
- **`remotion@4.0.441` + `@remotion/renderer@4.0.441`:** Video composition service expanding the existing `remotion-service/` directory. Accepts `composition_id` + `inputProps`, renders MP4 via `renderMedia()`, uploads to R2. Requires a Company License for SaaS commercial use — budget for this before launch.
- **`fal-client==0.13.2` (upgrade from 0.10.0):** Upgrade only. Async improvements and queue status streaming. Already in stack.
- **Obsidian Local REST API plugin + custom `httpx` client:** Optional Scout agent enrichment. Store `OBSIDIAN_BASE_URL` and `OBSIDIAN_API_KEY` in a new `ObsidianConfig` dataclass. Feature must fully degrade when absent. Network topology constraint: API runs on user's machine — cloud deployments require user to expose it via Cloudflare Tunnel or ngrok.

**No new npm packages** — the Remotion service exists and only needs version bumps.

---

### Expected Features

The research distinguishes between what any "content operating system" must have (table stakes) and what creates genuine competitive separation (differentiators).

**Must have (table stakes) for v2.0 launch:**
- Proactive content idea recommendations — users now expect AI to surface ideas before being asked
- One-click approve from recommendation feed — zero-friction path from recommendation to generation
- Workflow status visibility — users must see what background workflows are doing ("publishing in 3h")
- Automatic content performance feedback — real engagement data (24h + 7d) must flow back into the platform
- Multi-format media output — carousel and static-image-with-typography are required; talking-head is competitive

**Should have (competitive differentiators):**
- LightRAG knowledge graph over approved content — multi-hop retrieval for "what angles have I NOT used on topic X?" — unique in market
- Strategist Agent with rationale-first recommendation cards — "why this topic now" explanation per card (Smashing Magazine 2026 agentic UX pattern)
- Obsidian vault as Scout research source — personal PKM as content grounding material; no competitor does this
- n8n as observable workflow orchestrator — visual workflow graph auditable by platform owner without code deploys
- Unified fatigue prevention tied to knowledge graph — topic distribution queries prevent persona drift

**Defer to v2.x or later:**
- Talking-head video + overlays (P2 — add after image carousel pipeline is proven)
- Short-form video 15-60s (P2 — most complex Remotion composition; gated on simpler pipelines working)
- Multi-language support / Sarvam AI (v3+ — explicitly deferred per project constraints)
- Real-time collaboration (v3+ — small agencies handled by sequential review)
- Automatic Obsidian write-back (anti-feature — user trust risk; offer explicit export only)

**Anti-features to reject:** Full auto-post without review, general-purpose "write anything" mode bypassing Commander, bulk AI-generate full month unreviewed.

---

### Architecture Approach

The v2.0 architecture is an additive sidecar pattern on top of the existing FastAPI monolith. No existing routes, agents, or services are deleted — only extended. New components (n8n, LightRAG, Remotion) run as separate services and communicate with FastAPI over HTTP using a trigger+callback pattern. Celery is partially retained for fast in-process tasks that require Motor async coupling. The critical path runs left to right: n8n publishes posts → analytics data populates `content_jobs.performance_data` → LightRAG indexes approved content → Strategist synthesizes signal → Strategy Dashboard surfaces recommendations.

**Major components:**

1. **n8n (external orchestrator)** — Handles all cron-scheduled and external-API workflows: publish-post, analytics-poll-24h/7d, reset-daily-limits, refresh-monthly-credits, cleanup-old-jobs, nightly-strategist. FastAPI triggers via `POST /webhook/{workflow_name}` and receives results via authenticated callback at `POST /api/n8n/callback` (HMAC-SHA256 verified).
2. **LightRAG Service (sidecar container)** — Knowledge graph over user-approved content. Thinker agent calls `POST /query` (hybrid mode) before angle selection. Learning agent calls `POST /documents/insert_text` on content approval. Strict per-user namespace isolation mandatory — one LightRAG workspace per user. Separate MongoDB database from ThookAI application data.
3. **Remotion Render Service (Node.js)** — Expands existing `remotion-service/` into a real Express API. Four separate compositions: `StaticImageCard`, `ImageCarousel`, `TalkingHeadOverlay`, `ShortFormVideo`. Accepts R2-hosted asset URLs only — never external CDN URLs (Remotion timeout risk). Returns `render_id` immediately, uploads to R2 asynchronously.
4. **Media Orchestrator (`backend/services/media_orchestrator.py`)** — Decomposes `MediaBrief` into per-asset tasks, routes each to best provider (fal.ai/DALL-E for images, Luma/HeyGen for video, ElevenLabs for audio), runs tasks in parallel via `asyncio.gather`, then calls Remotion for assembly.
5. **Strategist Agent (`backend/agents/strategist.py`)** — Nightly n8n-triggered agent. Reads LightRAG graph for content gaps, MongoDB for performance signals, Obsidian vault for unused ideas, synthesizes with `claude-sonnet-4-20250514`, writes recommendation cards to `db.strategy_recommendations`. Never triggers generation directly — writes `status: "pending_approval"` cards only.
6. **Strategy Dashboard (new React page)** — SSE-driven recommendation card feed. Max 3 active cards shown. "Approve" fires `POST /api/content/generate` with pre-filled payload. Every card includes "Why now: [signal]" rationale.

**New files summary:** `backend/agents/strategist.py`, `backend/services/lightrag_service.py`, `backend/services/media_orchestrator.py`, `backend/services/obsidian_service.py`, `backend/services/strategist_service.py`, `backend/routes/n8n_bridge.py`, `backend/routes/strategy.py`, `backend/routes/media_orchestrate.py`.

---

### Critical Pitfalls

1. **Dual Celery + n8n execution produces duplicate social posts** — Hard-cutover per job category (never gradual). Disable Celery beat entry before activating n8n schedule equivalent. Add idempotency key on all scheduled-post publish operations (check `last_published_at` within 2-minute window). Never run Procfile `beat` while n8n schedule workflows are active for the same domain.

2. **LightRAG embedding model lock-in** — Choose `text-embedding-3-small` before writing one document to the index and freeze it permanently in `backend/config.py` as `LIGHTRAG_EMBEDDING_MODEL`. Add a startup assertion that confirms stored vector dimension matches configured model. Switching models later requires full index rebuild with no migration path.

3. **LightRAG graph fills with noise entities, corrupting Thinker retrieval** — Override LightRAG's default entity extraction prompt before any production ingestion. Scope extraction to: topic domains, hook archetypes, emotional tones, domain-expertise named entities. Suppress: platform names, time references, filler words, generic nouns. Test extraction output on 10 real posts before bulk ingestion.

4. **Strategist recommendation spam destroys user trust within days** — Hard-cap at 3 new recommendation cards per user per day from day one. Track per-user dismissal rate in `db.strategy_recommendations`. If 5 consecutive dismissals, halve generation rate and surface "calibrate preferences" prompt. Never generate for a topic dismissed within last 14 days. These controls must be in v1 of the feature — retrofitting trust is harder than building it.

5. **Multi-model media pipeline leaks credits on partial failure** — Track credit consumption per pipeline stage in `media_pipeline_ledger` collection (`job_id`, `stage`, `provider`, `credits_consumed`, `status`). Implement cost cap per media job in `credits.py`. Pre-download all external assets to R2 before passing to Remotion (`delayRenderTimeoutInMilliseconds: 120000` minimum). Mark every provider timeout as an explicit failure with `failure_stage` recorded.

6. **n8n webhook immediate-response mode silently discards results** — For any workflow ThookAI needs to act on: set webhook response mode to "When last node finishes" + use "Respond to Webhook" terminal node. Test with contract assertion that every ThookAI→n8n call returns non-empty body with expected schema.

7. **Obsidian vault reads private journals/passwords if path not sandboxed** — Require users to designate a specific `/Research` subdirectory. Validate configured path is strictly inside vault root before every file read. Never store vault content in MongoDB. Make integration opt-in with explicit display of "ThookAI will read files from: [path]" before activation.

---

## Implications for Roadmap

The build order is dictated by the dependency chain: n8n must publish successfully before analytics data flows; analytics data must flow before LightRAG has meaningful signal; LightRAG must be populated before Strategist produces non-generic output; Strategist must produce recommendations before Strategy Dashboard has value. Building in the wrong order produces features that appear to work but deliver no user value.

### Phase 1: n8n Infrastructure + Celery Migration

**Rationale:** Everything downstream depends on n8n. Publishing must work before analytics can be collected. This is the foundation that unblocks all later phases. Celery cutover is a risk-amplifier — it must happen cleanly before any other new systems are added.
**Delivers:** Observable, debuggable workflow orchestration; working social publishing via n8n nodes; all Celery cron tasks migrated; n8n webhook response contracts verified.
**Addresses:** Table-stakes workflow status visibility; fixes BUG-2 (Celery app not configured) and BUG-3 (placeholder publisher) from CLAUDE.md.
**Avoids:** Dual Celery+n8n execution producing duplicate posts (hard-cutover protocol + idempotency keys built here).
**Research flag:** STANDARD — n8n queue mode architecture is well-documented. Verify LinkedIn/Instagram OAuth node scope coverage before committing to n8n for publishing.

### Phase 2: LightRAG Knowledge Graph

**Rationale:** LightRAG is the intelligence substrate that enables the Strategist's differentiated capability. Without a populated knowledge graph, the Strategist degrades to generic trending-topics recommendations that Taplio already does better. Must be built and populated before Phase 4 (Strategist) produces value.
**Delivers:** Per-user knowledge graph with domain-specific entity extraction; Thinker agent enhanced with multi-hop topic retrieval; Learning agent writing to both Pinecone (similarity) and LightRAG (relationships) on content approval.
**Uses:** `lightrag-hku==1.4.12` sidecar container; MongoDB `thookai_lightrag` database; `NanoVectorDBStorage`; embedding model `text-embedding-3-small` locked permanently.
**Implements:** LightRAG sidecar pattern; retrieval routing contract (Thinker calls LightRAG only; Writer calls Pinecone only).
**Avoids:** Embedding model lock-in (lock model in config before first insert); graph noise (custom extraction prompt tested on 10 posts before bulk ingestion); LightRAG+Pinecone context bleeding (strict routing contract documented in `pipeline.py`).
**Research flag:** NEEDS RESEARCH — custom entity extraction prompt for ThookAI's domain (topic domains, hook archetypes, tones) needs to be written and tested before implementation begins. LightRAG's workspace isolation pattern for per-user graphs needs validation.

### Phase 3: Multi-Model Media Orchestration

**Rationale:** Multi-format media output is table stakes for 2026 social platforms. Image carousels show 44% higher engagement on LinkedIn. This phase unlocks the visual content dimension that text-only posts cannot compete on. Remotion service already scaffolded — needs expansion into four named compositions.
**Delivers:** Static image + typography pipeline; image carousel pipeline; media orchestrator routing to best provider; Remotion assembly with R2-staging of all external assets; credit ledger for partial-failure accounting.
**Uses:** `remotion@4.0.441`, `@remotion/renderer@4.0.441`; `fal-client==0.13.2`; existing fal.ai/DALL-E/ElevenLabs/HeyGen providers; `media_pipeline_ledger` MongoDB collection.
**Implements:** Media Orchestrator service; four Remotion compositions (StaticImageCard, ImageCarousel, TalkingHeadOverlay as stretch, ShortFormVideo as stretch).
**Avoids:** Remotion asset timeout (pre-download all assets to R2 before render; `delayRenderTimeoutInMilliseconds: 120000`); credit leakage on partial failure (pipeline ledger + cost cap per job); blocking event loop in Designer agent (asyncio.wait_for with 60s timeout).
**Research flag:** NEEDS RESEARCH — Remotion Company License cost and procurement timeline. HeyGen API async polling pattern for avatar video status. ElevenLabs `output_format: pcm_48000` requirement for video pipeline compatibility.

### Phase 4: Strategist Agent + Analytics Feedback Loop

**Rationale:** The Strategist is the core v2.0 differentiator — the feature that makes ThookAI a content operating system rather than a content creation tool. It requires LightRAG (Phase 2) populated with approved content AND real analytics data flowing in. Both must exist before Strategist output has signal quality worth showing users.
**Delivers:** Nightly n8n-triggered Strategist agent; real social analytics ingestion (24h + 7d post-publish polling via n8n); `db.strategy_recommendations` collection; cadence controls (max 3/day, 14-day dismissal suppression, dismissal rate tracking).
**Uses:** `backend/agents/strategist.py`; n8n `nightly-strategist` cron workflow; `backend/services/strategist_service.py`; existing `llm_client.py` with `claude-sonnet-4-20250514`.
**Implements:** Strategist Agent pattern; Analytics Feedback Loop data flow.
**Avoids:** Recommendation spam destroying user trust (cadence controls in v1, not retrofitted); Strategist writing directly to pipeline (writes `status: "pending_approval"` cards only); analytics data being fabricated from internal DB (real social API polling with exponential backoff).
**Research flag:** STANDARD for analytics polling patterns. NEEDS RESEARCH for LinkedIn UGC API metrics endpoint scope and rate limits; Instagram Insights API limitations for personal vs business accounts.

### Phase 5: Strategy Dashboard

**Rationale:** The user-facing surface for Strategist output. Cannot deliver value until Phase 4 Strategist is producing recommendations with real LightRAG + analytics signal. Building the dashboard before the backend has signal produces an empty page that damages perception of the feature.
**Delivers:** New React page with SSE-driven recommendation card feed (max 3 active); "Why now: [signal]" rationale on every card; one-click approve triggering `POST /api/content/generate` with pre-filled payload; dismissed cards archived to History tab.
**Implements:** Strategy Dashboard frontend; `GET /api/strategy` and `POST /api/strategy/:id/approve` routes; SSE push on Strategist completion.
**Avoids:** Dashboard showing all recommendation history at once (overwhelming after 2 weeks); recommendations without rationale (users don't trust what they can't understand).
**Research flag:** STANDARD — React SSE patterns and shadcn/ui card components are well-documented.

### Phase 6: Obsidian Vault Integration

**Rationale:** Power-user differentiator that makes ThookAI genuinely unique. No competitor ingests personal PKM. Positioned after core intelligence loop (Phases 1-5) so Scout enrichment enhances an already-working pipeline rather than being a dependency.
**Delivers:** Scout agent enriched with vault search results; Strategist using recent vault files as recommendation trigger signal; `backend/services/obsidian_service.py` with strict path sandboxing; opt-in UI with explicit "ThookAI will read from: [path]" display.
**Uses:** Obsidian Local REST API plugin + custom `httpx` client; `ObsidianConfig` dataclass in `backend/config.py`; feature gate on `OBSIDIAN_API_KEY` presence.
**Avoids:** Vault reading private journals/passwords (designated subdirectory only; path traversal validation on every read); prompt injection from vault content (sanitize YAML frontmatter before LLM injection); implicit feature activation (explicit opt-in UI required).
**Research flag:** NEEDS RESEARCH — production deployment topology for cloud-hosted ThookAI requires user to expose Obsidian REST API via Cloudflare Tunnel or ngrok. Document this user-facing setup requirement clearly before building the feature.

### Phase 7: E2E Hardening + Production Readiness

**Rationale:** System integration phase. All components are running individually — this phase verifies the critical path end-to-end and addresses the security hardening items identified in pitfall research.
**Delivers:** n8n instance behind private VPC or basic auth (not publicly accessible); `N8N_BLOCK_ENV_ACCESS_IN_NODE=true` in production; n8n execution history pruning configured (`EXECUTIONS_DATA_MAX_AGE=336`, `EXECUTIONS_DATA_PRUNE_MAX_COUNT=10000`); LightRAG per-user graph namespace enforcement verified; SSE event user-id scoping verified; load test confirming Remotion render queue at 5+ concurrent requests.
**Avoids:** n8n publicly accessible (arbitrary workflow execution risk); LightRAG graph exposed across users (competitor intel leakage); Strategist SSE events broadcast to wrong users.
**Research flag:** STANDARD — security patterns well-documented in research.

---

### Phase Ordering Rationale

- n8n (Phase 1) first because it unblocks analytics data collection which unblocks LightRAG signal quality which unblocks Strategist value — the entire intelligence stack depends on real data flowing
- LightRAG (Phase 2) before Strategist (Phase 4) because an empty knowledge graph produces generic recommendations that damage trust faster than no recommendations at all
- Media Orchestration (Phase 3) in parallel with LightRAG data population window — it takes days/weeks for the knowledge graph to have enough signal; media work can proceed concurrently
- Strategist + Analytics (Phase 4) only after LightRAG is populated with real content AND n8n is confirmed publishing and collecting analytics
- Strategy Dashboard (Phase 5) only after Strategist has signal — building UI before backend has real data is a trust trap
- Obsidian (Phase 6) last among features — it enhances but is not on the critical path; optional for most users
- E2E hardening (Phase 7) at the end — security review after all integration points are known

---

### Research Flags

Phases needing deeper research during planning:

- **Phase 2 (LightRAG):** Custom entity extraction prompt for ThookAI's domain must be written and tested. Per-user workspace isolation pattern in LightRAG needs validation against v1.4.12 API.
- **Phase 3 (Media Orchestration):** Remotion Company License procurement needed before launch. HeyGen async polling and ElevenLabs audio format requirements need verification. Confirm `delayRenderTimeoutInMilliseconds` is available in Remotion 4.0.441.
- **Phase 4 (Analytics + Strategist):** LinkedIn UGC API metrics scope and rate limits. Instagram Insights API availability for personal vs. business accounts. Confirm n8n Wait node behavior for 24h/7d analytics scheduling.
- **Phase 6 (Obsidian):** Cloud deployment topology — user-facing tunnel setup documentation needed. REST API plugin authentication flow when served over tunnel.

Phases with standard patterns (skip research-phase):

- **Phase 1 (n8n):** Queue mode architecture well-documented in official n8n docs. HMAC callback auth pattern is standard.
- **Phase 5 (Strategy Dashboard):** React + SSE + shadcn/ui card patterns are established.
- **Phase 7 (E2E Hardening):** Security hardening items are well-defined in pitfall research.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | MEDIUM-HIGH | n8n queue mode and LightRAG MongoDB backends verified via official docs + PyPI. Remotion 4.0.441 confirmed via npm. Obsidian REST API confirmed via plugin GitHub. Risk area: n8n LinkedIn/Instagram OAuth node scope coverage — verify before relying on for publishing. |
| Features | HIGH | Competitor analysis verified across Taplio, Supergrow, Buffer. LightRAG academic provenance (EMNLP 2025). Smashing Magazine 2026 UX patterns for agentic AI. LinkedIn carousel engagement data from PostNitro (MEDIUM — vendor source). |
| Architecture | HIGH | Core patterns (sidecar, trigger+callback, per-user graph namespace, Remotion composition separation) verified via official docs. ThookAI-specific deployment topology is MEDIUM — based on architecture reasoning, not a documented case study. |
| Pitfalls | MEDIUM-HIGH | n8n queue mode worker initialization failures verified in community forums. LightRAG embedding lock-in confirmed in GitHub README. Remotion timeout behavior confirmed in official docs. Celery→n8n dual-execution and Strategist trust degradation patterns are architecture-reasoned (no direct case studies found). |

**Overall confidence:** MEDIUM-HIGH

### Gaps to Address

- **n8n LinkedIn/Instagram publishing node OAuth scope coverage:** Verify that n8n's built-in LinkedIn and Instagram nodes support the exact OAuth scopes needed for UGC posting (not just read access). If gaps exist, custom HTTP Request nodes with manual OAuth token injection may be needed. Address in Phase 1 planning.
- **LightRAG per-user workspace isolation API:** LightRAG v1.4.12's workspace/namespace isolation pattern for multi-tenant use needs code-level verification before Phase 2 implementation. The architecture assumes `user_id` filtering is sufficient — confirm this is enforced at storage level, not just query level.
- **Remotion Company License cost and timeline:** Must be budgeted before Phase 3 launch. The existing `remotion-service/` directory does not include a `licenseKey` — add to all `renderMedia()` calls.
- **Instagram analytics API access level:** Instagram Insights API requires a Business or Creator account. Standard personal accounts may not have metrics access. This affects analytics feedback loop quality for users who haven't upgraded their Instagram account type.
- **Obsidian cloud deployment user experience:** The current Obsidian REST API integration requires the user to run a tunnel. This is a real friction point for non-technical users. The UX for configuring this needs to be designed before building — consider whether to offer a simpler alternative (file upload to ThookAI, manual note paste) as fallback.

---

## Sources

### Primary (HIGH confidence)
- [lightrag-hku on PyPI](https://pypi.org/project/lightrag-hku/) — Version 1.4.12, storage backends
- [HKUDS/LightRAG GitHub](https://github.com/HKUDS/LightRAG) — Architecture, MongoDB backends, embedding model lock-in
- [LightRAG EMNLP 2025 paper](https://arxiv.org/html/2410.05779v1) — Academic provenance, dual-level retrieval
- [Remotion SSR docs](https://www.remotion.dev/docs/ssr) — renderMedia(), Node.js API
- [Remotion licensing docs](https://www.remotion.dev/docs/licensing/) — Commercial SaaS requirements
- [n8n Docker Hub](https://hub.docker.com/r/n8nio/n8n) — stable vs latest tags
- [n8n queue mode docs](https://docs.n8n.io/hosting/scaling/queue-mode/) — PostgreSQL requirement, worker architecture
- [n8n webhook node docs](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.webhook/) — Response mode pitfall
- [obsidian-local-rest-api GitHub](https://github.com/coddingtonbear/obsidian-local-rest-api) — API endpoints, auth, HTTPS on 27124
- [fal-client on PyPI](https://pypi.org/project/fal-client/) — Version 0.13.2, async capabilities
- [Designing For Agentic AI — Smashing Magazine 2026](https://www.smashingmagazine.com/2026/02/designing-agentic-ai-practical-ux-patterns/) — Intent Preview UX pattern

### Secondary (MEDIUM confidence)
- [n8n Community: Worker Not Dequeuing](https://community.n8n.io/t/self-hosted-n8n-cluster-on-railway-worker-not-dequeuing-jobs-webhook-triggers-stuck-in-queue/209719) — Worker initialization failure in Render/Railway deployments
- [Taplio Review 2026 — Brandled](https://brandled.app/blog/taplio-review) — Competitor feature baseline
- [Supergrow vs Taplio — Supergrow](https://www.supergrow.ai/blog/taplio-vs-supergrow) — Feature comparison (vendor-biased but list is accurate)
- [2025 Social Media Algorithm — PostNitro](https://postnitro.ai/blog/post/2025-social-media-algorithm-changes-carousels) — 44% carousel engagement figure
- [fal.ai multi-model architecture](https://fal.ai/learn/devs/building-effective-gen-ai-model-architectures) — Multi-provider integration patterns
- [Self-Hosting n8n on Render](https://render.com/articles/self-hosting-n8n-a-production-ready-architecture-on-render) — Queue mode on Render
- [IBM: Agentic Drift](https://www.ibm.com/think/insights/agentic-drift-hidden-risk-degrades-ai-agent-performance) — Proactive agent trust degradation

### Tertiary (LOW confidence)
- [Future AI Content Tools 2026 — Smartli](https://www.smartli.ai/blog/future-ai-content-tools) — General market predictions, single source

---
*Research completed: 2026-04-01*
*Ready for roadmap: yes*
