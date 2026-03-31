# Pitfalls Research

**Domain:** AI content operating system — n8n orchestration, knowledge graph (LightRAG), multi-model media orchestration, proactive strategy agents, analytics feedback loops
**Researched:** 2026-04-01
**Confidence:** MEDIUM-HIGH — n8n queue mode issues and LightRAG initialization constraints verified via official docs + community. Multi-model orchestration patterns from fal.ai official documentation. Celery→n8n migration patterns inferred from architecture knowledge (no direct migration case studies found — treat as MEDIUM confidence).

---

## Critical Pitfalls

### Pitfall 1: Celery Beat and n8n Schedule Running Simultaneously — Duplicate Job Execution

**What goes wrong:**
During migration, both Celery beat (existing) and n8n schedule triggers run concurrently. `process_scheduled_posts` fires from both systems. A single post gets published twice to LinkedIn/X. `reset_daily_limits` runs twice, potentially resetting credits at wrong intervals. `aggregate_daily_analytics` writes duplicate records, corrupting analytics history.

**Why it happens:**
Teams migrate workflow-by-workflow to reduce risk, but forget that the migration window creates a dual-execution period. n8n schedule triggers activate the moment a workflow is published (not when Celery is turned off). There is no deduplication layer between the two systems since they write to the same MongoDB collections independently.

**How to avoid:**
Adopt a hard-cutover strategy per job category, not gradual migration. Before activating any n8n schedule trigger for a job that already exists in Celery beat, disable the corresponding Celery beat schedule entry first. Add an idempotency key on all scheduled-post publishing operations — check `last_published_at` within a 2-minute window before executing. Never run `Procfile` worker + beat processes while n8n schedule workflows are active for the same domain.

**Warning signs:**
- Duplicate entries in `db.content_jobs` or `db.scheduled_posts` with identical `job_id` and timestamps within seconds of each other
- Users report seeing posts published twice on LinkedIn/X
- `db.users.credits` shows double-deduction in audit logs

**Phase to address:**
n8n infrastructure phase (Phase 1). Must define the cutover protocol and idempotency keys before any n8n schedule trigger is published.

---

### Pitfall 2: n8n Worker Not Entering Queue Mode — All Webhooks Silently Stuck

**What goes wrong:**
n8n is deployed in queue mode with Redis, but webhook-triggered workflows never execute. Jobs successfully enqueue in Redis (the main n8n process confirms receipt), but the worker container never dequeues them. The symptom looks identical to a Redis connectivity failure but the root cause is the worker process not recognizing its role despite environment variables being set.

**Why it happens:**
On Render/Railway (where ThookAI is deployed), environment variables can fail to propagate to worker containers if the service type is copied from the main n8n service without explicitly setting `N8N_PROCESS_TYPE=worker`. The worker starts, passes health checks, but never connects to the Bull/BullMQ queue. Manual triggers bypass the queue and succeed, creating false confidence that the deployment is healthy.

**How to avoid:**
After deploying n8n workers, add an explicit health probe: hit `GET /healthz` and separately verify Redis LLEN on the Bull queue key. If the queue depth grows but worker active count stays zero, the worker is not initialized correctly. Add a startup log assertion in the n8n worker service that confirms `EXECUTIONS_MODE=queue` and `N8N_PROCESS_TYPE=worker` are both set. Require PostgreSQL (not SQLite) — queue mode is unsupported with SQLite.

**Warning signs:**
- n8n executions view shows workflows in "Queued" or "Starting soon" indefinitely
- Redis Bull queue depth increases but worker metrics show zero active jobs
- Manual executions succeed but webhook-triggered ones do not

**Phase to address:**
n8n infrastructure phase (Phase 1). Must be verified with a smoke test before any business logic is migrated.

---

### Pitfall 3: LightRAG Embedding Model Lock-In — Cannot Switch Models After Initial Index

**What goes wrong:**
LightRAG locks the embedding model at index creation time. The vector dimension is baked into the storage schema (especially on PostgreSQL with pgvector). If the team starts with `text-embedding-ada-002` (1536 dims) and later wants to switch to a better model (e.g., `text-embedding-3-large` at 3072 dims), the entire index must be dropped and rebuilt from scratch. All extracted entities and relationships are lost and must be re-extracted — a costly LLM operation that re-processes every approved content item.

**Why it happens:**
LightRAG documentation buries the embedding model constraint. Teams choose "whatever OpenAI embedding model is handy" during initial setup, not realizing the decision is permanent without full re-ingestion. The storage schema creation happens on first `insert()` call, not at configuration time, so the lock-in is invisible until switching is attempted.

**How to avoid:**
Decide the embedding model before writing a single document to the index. For ThookAI's use case (user-specific content, English-primary, ~200-2000 tokens per item), `text-embedding-3-small` is the right choice — best cost/quality for short content at 1536 dims. Document this decision in `backend/config.py` as `LIGHTRAG_EMBEDDING_MODEL = "text-embedding-3-small"` and treat it as permanently frozen. Add a startup assertion that reads the stored embedding dimension from the first stored vector and confirms it matches the configured model's dimension.

**Warning signs:**
- Any proposal to "upgrade the embedding model" mid-production
- Retrieval quality degrades because a different model was used for new inserts than for old ones
- PostgreSQL schema errors mentioning dimension mismatch

**Phase to address:**
LightRAG phase (Phase 2). Model choice must be locked in the config before the first document ingestion in any environment.

---

### Pitfall 4: LightRAG Extracts Persona-Irrelevant Entities from Content — Graph Noise Corrupts Thinker Retrieval

**What goes wrong:**
LightRAG's entity extraction uses an LLM to identify entities and relationships from approved content. For ThookAI, approved content is user-created posts about, for example, "startup fundraising" or "leadership lessons." The LLM will extract all entities it sees, including irrelevant ones: platform names ("LinkedIn"), generic verbs ("announced"), time references ("Q3 2024"), and common nouns ("team"). Over time, the knowledge graph fills with thousands of low-signal nodes that pollute multi-hop retrieval. When the Thinker asks "what topics has this user written about?", the graph returns a noise cloud instead of meaningful topic clusters.

**Why it happens:**
LightRAG's default extraction prompt is domain-agnostic. It is designed for general document corpora, not for personal content fingerprinting. Without a custom entity extraction prompt scoped to ThookAI's domain (user topics, writing patterns, hook strategies, tone descriptors), the graph degrades into a generic index of English words.

**How to avoid:**
Override LightRAG's default entity extraction prompt before any production ingestion. The custom prompt should instruct the model to extract only: (1) topic domains (e.g., "startup fundraising", "leadership"), (2) hook archetypes (e.g., "contrarian take", "personal story"), (3) emotional tones (e.g., "vulnerable", "authoritative"), and (4) named entities that are part of the user's domain expertise. Suppress extraction of: platform names, time references, filler words, and generic nouns. Test entity extraction output on 10 real approved posts before ingesting at scale.

**Warning signs:**
- Knowledge graph node count grows faster than 50 nodes per approved post on average
- Most frequent entities in the graph are generic words, not topic-domain terms
- Thinker agent retrieval returns topics unrelated to user's historical content

**Phase to address:**
LightRAG phase (Phase 2). Custom extraction prompt must be written and tested before the ingestion pipeline is built.

---

### Pitfall 5: Multi-Model Media Orchestration Has No Partial-Failure Rollback — Credits Consumed on Failed Pipelines

**What goes wrong:**
A multi-model media pipeline for a "talking-head with overlays" might call: ElevenLabs (voice) → HeyGen (avatar) → fal.ai (background) → Remotion (assembly). If HeyGen generation succeeds but fal.ai background generation times out, ElevenLabs and HeyGen credits have already been consumed. The pipeline fails, the user gets no output, and the cost was real. Without explicit rollback accounting, this leaks money on every partial failure.

**Why it happens:**
Each provider call is independent and irreversible — you cannot "cancel" a completed ElevenLabs generation. Teams focus on the happy path and treat partial failures as edge cases, but at scale (100+ media generations per day), partial failure rates of even 3-5% per step compound to significant cost leakage. Additionally, Runway and HeyGen have documented cases where credits are deducted even for failed generations.

**How to avoid:**
Track credit consumption at each pipeline stage in a `media_pipeline_ledger` MongoDB collection: `{job_id, stage, provider, credits_consumed, status}`. On pipeline failure at any stage, mark subsequent stages as `skipped` and record total wasted credits. Implement a cost cap per media job in `backend/services/credits.py`: if cumulative credits consumed across stages exceed the job's credit allocation, abort and refund the delta. Use `asyncio.wait_for()` with conservative timeouts (60s for image, 300s for video) on every provider call. Never treat a provider timeout as a silent exception — always mark the job as `failed` with `failure_stage` recorded.

**Warning signs:**
- `media_assets` collection has records with `status: "failed"` but no `credits_refunded: true` field
- Users report being charged for media they never received
- Provider invoices are growing faster than successful media job counts

**Phase to address:**
Multi-model media orchestration phase (Phase 3). Pipeline ledger and cost-cap must be designed before the first provider integration.

---

### Pitfall 6: Remotion Asset Loading Times Out in Multi-Provider Pipelines — Silent Render Failure

**What goes wrong:**
Remotion's default `delayRender()` timeout is 30 seconds. In a pipeline where Remotion must load a HeyGen video (large file, external URL, cold CDN), an ElevenLabs audio file, and a fal.ai generated image, the combined asset load time routinely exceeds 30 seconds. Remotion aborts with no user-visible error message ("delayRender() called but not cleared after 28000ms"). The render job is marked failed in the Remotion service, but the ThookAI backend — if it only checks the exit code — may misinterpret this as a generic rendering error.

**Why it happens:**
The 30-second timeout is appropriate for self-hosted assets. It becomes a reliability landmine when all assets are fetched from multiple external APIs at render time. Teams deploy Remotion without adjusting `delayRenderTimeoutInMilliseconds` because the default works fine in development (assets are small test files) but fails in production (real multi-provider assets).

**How to avoid:**
In the `remotion-service/`, set `delayRenderTimeoutInMilliseconds: 120000` (120s) on every `<Img>`, `<Audio>`, and `<OffthreadVideo>` component. Pre-download all external assets to Cloudflare R2 before passing URLs to Remotion — Remotion should only fetch from R2, never directly from HeyGen/ElevenLabs/fal.ai CDNs. Pass R2 signed URLs with expiry of 1 hour (not permanent public URLs) to prevent stale asset access. Add a pre-render asset validation step that confirms all URLs are reachable before triggering the Remotion render.

**Warning signs:**
- Remotion render logs contain "delayRender() called but not cleared"
- Render failures are correlated with large asset sizes, not code errors
- Renders succeed in development but fail intermittently in production

**Phase to address:**
Multi-model media orchestration phase (Phase 3). Asset staging to R2 before Remotion render must be a hard architectural requirement.

---

### Pitfall 7: LightRAG + Pinecone Both Active Without Clear Retrieval Routing — Context Bleeding

**What goes wrong:**
ThookAI v1.0 wired Pinecone into `agents/writer.py` (finds similar past content) and `agents/learning.py` (stores approved embeddings). v2.0 adds LightRAG for multi-hop topic retrieval by the Thinker agent. If both systems are active but the routing is unclear, the Writer may receive duplicate context from both Pinecone (vector similarity) and LightRAG (graph relationships) for the same approved content, causing it to over-weight historical style patterns and under-generate fresh angles. Worse, if approved content is written to both stores independently, updates to one store are not reflected in the other, causing staleness divergence.

**Why it happens:**
Each retrieval system was added independently — Pinecone in v1.0, LightRAG in v2.0. Without an explicit retrieval routing contract, agent code accumulates calls to both systems (because "more context is better"), creating redundancy. The two systems model the same data differently (embeddings vs. graph nodes), so they cannot be straightforwardly merged or deduplicated.

**How to avoid:**
Define a strict retrieval contract before implementing LightRAG: Pinecone is the similarity search layer (find stylistically similar past posts), LightRAG is the topic graph layer (find related topic clusters and unexplored angles). Thinker calls LightRAG only. Writer calls Pinecone only. Learning agent writes to both stores on approval, but with different data shapes. Document this routing in `backend/agents/pipeline.py` as an explicit comment block. Never add a second retrieval call to an agent without updating the routing contract.

**Warning signs:**
- `agents/writer.py` has both a Pinecone call and a LightRAG call in the same function
- Agent prompts contain 2000+ tokens of retrieval context (sign of duplication)
- Content generations start repeating the user's own past vocabulary too precisely

**Phase to address:**
LightRAG phase (Phase 2). Retrieval routing contract must be written before any LightRAG retrieval code is added to agent files.

---

### Pitfall 8: Strategist Agent Recommendation Spam Degrades User Trust Within Days

**What goes wrong:**
The Strategist Agent generates proactive content recommendations based on trending topics, persona signals, and analytics. Without frequency throttling, a user who logs in after 48 hours may see 12 new recommendation cards in their Strategy Dashboard. They dismiss all of them. After this happens 2-3 times, they stop checking the dashboard entirely. The feature that was meant to increase engagement becomes a trust-destroying notification flood.

**Why it happens:**
The Strategist agent is optimized for recall (generate many good ideas) rather than precision (surface only the most actionable idea). The first implementation typically has no per-user cadence control because cadence is a UX concern, not a generation concern. The developer mindset during feature build is "more recommendations = more value", which is the opposite of the user experience reality.

**How to avoid:**
Hard-cap Strategist recommendations at 3 new cards per user per day, surfaced as a max-3 "inbox" in the Strategy Dashboard. Track per-user dismissal rate in `db.strategy_recommendations`. If a user dismisses 5 consecutive recommendations without acting on one, halve the daily generation rate for that user and surface a "calibrate my preferences" prompt. Never generate a new recommendation for a topic the user dismissed in the last 14 days. Make the recommendation card UI communicate signal strength ("High opportunity based on 3 signals") not just the idea.

**Warning signs:**
- Strategy Dashboard is loading but user is immediately scrolling past all cards
- Recommendation dismissal rate exceeds 80% across all users in analytics
- Users stop visiting the Strategy Dashboard after the first week

**Phase to address:**
Strategist Agent phase (Phase 4). Cadence controls and dismissal tracking must be built into the first version — retrofitting them after UX trust is damaged is harder.

---

### Pitfall 9: n8n Webhook Immediate-Response Mode Breaks Long-Running Pipeline Flows

**What goes wrong:**
n8n webhook nodes have a "Response" setting that defaults to "Immediately" — the node sends a 200 OK back to the caller the moment the webhook is triggered, before the workflow executes. If ThookAI's FastAPI backend calls n8n to trigger a scheduled-post publishing workflow and expects a result in the response body, it will receive an empty 200 with no data. The actual workflow result is discarded. The backend marks the post as "processed" based on the empty 200, but the post was never actually published.

**Why it happens:**
n8n's default "Immediately" response mode is appropriate for fire-and-forget automation. Content platform teams configuring n8n for the first time copy webhook node defaults. The issue is invisible in testing because the smoke test only checks HTTP status codes, not payload content.

**How to avoid:**
For any n8n workflow that ThookAI triggers and needs to act on the result: set webhook response mode to "When last node finishes" and use the "Respond to Webhook" node as the terminal node. For truly async flows (media generation, analytics collection), implement the two-webhook pattern: FastAPI calls n8n and receives a `workflow_execution_id` immediately, then polls `GET /executions/{id}` or listens to a callback webhook for the result. Add a contract test that asserts every n8n webhook that ThookAI calls returns a non-empty body with the expected schema.

**Warning signs:**
- n8n execution logs show workflows completing successfully but FastAPI logs show empty response bodies
- Scheduled posts are marked `published` in MongoDB but are not visible on the actual social platform
- Integration test passes but real data shows no side effects

**Phase to address:**
n8n infrastructure phase (Phase 1). The webhook response contract must be defined and tested before any business workflow is migrated.

---

### Pitfall 10: Obsidian Vault Integration Leaks Private Notes Into Scout Context

**What goes wrong:**
The Scout agent is enhanced to read from a user's Obsidian vault for research context. If the vault path is not strictly sandboxed, the Scout agent may traverse into daily journals, personal notes, password-related files, or emotionally sensitive writing that the user never intended to share with the AI pipeline. This content then becomes part of the generation context and may surface in AI-generated content — a catastrophic privacy breach that destroys user trust.

**Why it happens:**
`obsidian-cli` or file-system reading code often uses the vault root path with recursive glob patterns. Developers focus on "give the Scout as much context as possible" without thinking about vault topology. Users organize vaults with `/Research`, `/Journal`, `/Passwords`, `/Work` directories all under the same root. A naive glob on `vault_root/**/*.md` hits everything.

**How to avoid:**
Require users to designate a specific "ThookAI Research" folder within their vault (not the vault root). Only read `.md` files from that explicitly designated folder path. Validate that the configured path is a subdirectory of the vault root (not the root itself, not `..` traversal). Never store vault content in MongoDB or pass it through the LLM for tasks other than the specific Scout research call. Log all vault reads with file paths in an audit trail the user can inspect. Make vault integration opt-in with a clear UI that shows "ThookAI will read files from: [path]" before activation.

**Warning signs:**
- The Scout context includes content from files outside the user's research folder
- Users report seeing references to personal information in generated content
- Vault read logs contain paths outside the configured research directory

**Phase to address:**
Obsidian vault integration phase (Phase 7). Path sandboxing and the opt-in UI flow must be the first things built before any vault reading is implemented.

---

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Run n8n on SQLite during dev/test | Zero setup overhead | Queue mode (required for production scale) is blocked — SQLite unsupported in queue mode | Local dev only, never staging/prod |
| Use LightRAG with default entity extraction prompt | Working index in minutes | Graph fills with noise entities; retrieval degrades over weeks | Never — domain-specific prompt is mandatory |
| Store Remotion assets as external provider URLs | Skip R2 staging step | Remotion timeouts under load; CDN URLs may expire; HeyGen URLs are temporary | Never in production |
| Skip idempotency keys on n8n-triggered publishing | Simpler webhook handlers | Duplicate posts when n8n retries on network blip | Never for social publishing |
| Hard-code media credit costs per provider call | Fast initial implementation | Cost estimates become stale as providers change pricing; no budget enforcement | Prototype only |
| Reuse same LightRAG index across all users | Single index to manage | User A's content concepts bleed into User B's retrieval; persona cross-contamination | Never — per-user graph required |

---

## Integration Gotchas

Common mistakes when connecting to external services.

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| n8n webhook triggers | Assuming the workflow executes synchronously before the webhook responds | Explicitly configure "Response Mode: When last node finishes" or implement async polling pattern |
| LightRAG storage init | Calling `rag.insert()` before `await rag.initialize_storages()` | Always call `initialize_storages()` as part of app startup lifespan, not lazily on first insert |
| HeyGen avatar creation | Assuming video URL is immediately available after API call returns | HeyGen is async — poll `GET /v1/video_status.get?video_id={id}` until status is "completed"; never assume status on first response |
| ElevenLabs voice generation | Using default 44kHz sample rate for all video pipelines | Remotion and most video formats expect 48kHz; resample explicitly or use ElevenLabs `output_format: pcm_48000` |
| fal.ai image generation | Not specifying `seed` for reproducibility | Without seed, same prompt generates different images on retry — inconsistent output on pipeline re-runs; set seed from `job_id` hash |
| Pinecone + LightRAG coexistence | Writing to both with same content encoding | Pinecone expects raw text chunks; LightRAG expects full documents for entity extraction — use different ingestion pipelines per store |
| n8n → FastAPI calls | Not setting `Authorization` header on n8n HTTP nodes | n8n makes outbound HTTP calls without auth headers by default — all FastAPI protected routes will receive 401 from n8n |
| Obsidian CLI vault read | Using vault root as the read path | Only read from a designated subdirectory; vault root includes journals, configs, private notes |
| Strategist Agent + SSE | Pushing recommendation events to all connected users | SSE events must be scoped to `user_id` channel — never broadcast Strategist results to a shared SSE stream |

---

## Performance Traps

Patterns that work at small scale but fail as usage grows.

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Synchronous LightRAG `insert()` on every content approval | Approval API endpoint becomes slow (5-30s) as graph grows | Move LightRAG inserts to a background Celery task or n8n workflow triggered on approval | When knowledge graph exceeds ~500 nodes |
| Single LightRAG graph for all users | Query response time degrades as all-user content accumulates | One LightRAG instance (or one storage namespace) per user from day one | At 100+ active users with 50+ approved posts each |
| Remotion renders blocking the remotion-service event loop | Concurrent render requests queue up; users wait minutes for video previews | Run Remotion renders in child processes or use `@remotion/lambda` for true parallelism | At 5+ concurrent video render requests |
| n8n workflows with no execution history pruning | n8n PostgreSQL database grows unboundedly; query performance degrades | Configure `EXECUTIONS_DATA_MAX_AGE=336` (14 days) and `EXECUTIONS_DATA_PRUNE_MAX_COUNT=10000` | After 30 days of production traffic |
| Analytics feedback loop polling social APIs on a tight schedule | LinkedIn/X API rate limits hit; all analytics jobs start failing | Use exponential backoff with jitter; stagger polling by user with random offset; cache 24h results aggressively | At 50+ users with connected social accounts |
| Strategist Agent runs full LLM generation for every user on every beat | LLM costs scale linearly with user count | Only run Strategist for users active in last 7 days; use lightweight scoring pass before full generation | At 200+ users |

---

## Security Mistakes

Domain-specific security issues beyond general web security.

| Mistake | Risk | Prevention |
|---------|------|------------|
| n8n instance publicly accessible without authentication | Anyone can trigger workflows, exfiltrate data, or run arbitrary code in Code nodes | Deploy n8n behind a private VPC or require `N8N_BASIC_AUTH_ACTIVE=true`; never expose n8n UI on public internet |
| n8n Code nodes can access `process.env` | API keys in env vars are readable inside Code nodes — insider threat vector | Set `N8N_BLOCK_ENV_ACCESS_IN_NODE=true` in production; pass secrets via n8n Credentials only |
| Vault integration with unsandboxed file paths | Path traversal: `../../../etc/passwd` or journal exposure | Validate resolved path is strictly inside the designated research directory before every file read |
| Strategist Agent recommendations embedded with unsanitized vault content | Prompt injection via user's own vault notes into Strategist LLM call | Sanitize vault content before injecting into LLM prompts; strip YAML frontmatter keys that look like instructions |
| LightRAG graph exposed across users | User A's entity graph reveals User B's content strategy (competitor intel) | Enforce per-user graph namespace at storage level; include `user_id` as a required filter on all LightRAG queries |
| n8n webhook URLs are unauthenticated by default | External parties can trigger content publishing or analytics collection by guessing URLs | Use n8n webhook authentication (header auth or JWT); validate `X-ThookAI-Webhook-Secret` on every inbound n8n webhook |

---

## UX Pitfalls

Common user experience mistakes in this domain.

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Strategy Dashboard shows all recommendation history, not just active ones | Dashboard is overwhelming after 2 weeks; users can't find actionable items | Show max 3 active recommendations; archive dismissed/acted-on to a separate "History" tab |
| Multi-model media pipeline shows no intermediate progress | User waits 3-5 minutes with spinner; assumes the page hung | Show stage-by-stage progress: "Generating voice... Done. Creating avatar... 40%..." via SSE events from each pipeline stage |
| Obsidian vault sync shows no indication of what was read | User is anxious about what private data the AI accessed | Show "Last synced: 12 notes from /Research/Competitors" in the Scout UI — explicit, auditable, reassuring |
| Strategist recommendations lack explanation for why they were surfaced | Users don't trust recommendations they can't understand | Every recommendation card must show "Why now: [signal]" — e.g., "Your last 3 posts on fundraising got 2x avg engagement" |
| Analytics feedback loop takes 24h to appear — no intermediate state | Dashboard shows no post-publish data; users think analytics are broken | Show "Pending — checking again in 22 hours" with a timestamp; never show empty analytics state without explaining the delay |

---

## "Looks Done But Isn't" Checklist

Things that appear complete but are missing critical pieces.

- [ ] **n8n infrastructure:** n8n deploys and UI is accessible — verify workers are actually dequeuing by triggering a test webhook and confirming it executes (not just enqueues)
- [ ] **LightRAG integration:** First `insert()` succeeds — verify entity extraction produced domain-relevant entities (not generic words) by inspecting graph node names
- [ ] **Multi-model media pipeline:** "Talking-head video" generates successfully in dev — verify asset staging to R2 works, Remotion loads from R2 (not external URLs), and partial failure records the failure stage correctly
- [ ] **Strategist Agent:** Recommendations appear in dashboard — verify cadence controls are active (max 3/day), dismissal is persisted to DB, and dismissed topics are suppressed for 14 days
- [ ] **Analytics feedback loop:** 24h polling task is scheduled — verify it actually fetches from LinkedIn/X API (not from internal DB), writes to `content_jobs.performance_data`, and handles API rate limit errors without crashing
- [ ] **Obsidian integration:** Vault notes appear in Scout context — verify only files from the designated subdirectory are read (test with a file planted outside the directory)
- [ ] **Celery→n8n migration:** n8n schedule triggers are running — verify Celery beat is stopped and that no scheduled tasks are running from both systems simultaneously
- [ ] **SSE notifications:** Notifications appear in the frontend — verify events are scoped to the correct `user_id` and a test of two concurrent users does not cross-contaminate their notification streams

---

## Recovery Strategies

When pitfalls occur despite prevention, how to recover.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Duplicate posts published to LinkedIn/X | HIGH | Delete duplicates via platform API immediately; add idempotency keys retroactively; audit all published posts from migration window; send user apology if public post was duplicated |
| LightRAG graph filled with noise entities | MEDIUM | Drop and rebuild graph with corrected entity extraction prompt; re-ingest all approved content; no user data loss since source is MongoDB |
| Embedding model switch needed post-index creation | HIGH | Drop vector tables; rebuild LightRAG index from scratch; downtime period required; this is why the model choice must be locked upfront |
| n8n worker stuck in queue mode | LOW | Redeploy worker service with corrected `N8N_PROCESS_TYPE=worker` env var; queued jobs will resume automatically once worker connects |
| Media pipeline partial failure leaks credits | MEDIUM | Implement `media_pipeline_ledger` retroactively; manually audit provider invoices vs. successful media job counts to estimate leak; issue credits to affected users |
| Obsidian vault reads files outside designated folder | CRITICAL | Immediately disable vault integration feature flag; audit which content was used in LLM calls; delete contaminated LightRAG graph entries; notify affected users; rebuild vault reading with strict path validation |

---

## Pitfall-to-Phase Mapping

How roadmap phases should address these pitfalls.

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Dual Celery + n8n execution / duplicate jobs | Phase 1: n8n infrastructure | Smoke test: confirm no duplicate entries in `db.scheduled_posts` after publishing one post |
| n8n worker not entering queue mode | Phase 1: n8n infrastructure | Health probe: Redis queue depth vs. worker active count must converge to 0 within 30s of trigger |
| LightRAG embedding model lock-in | Phase 2: LightRAG knowledge graph | Config assertion at startup: `LIGHTRAG_EMBEDDING_MODEL` matches stored vector dimension |
| LightRAG noise entity extraction | Phase 2: LightRAG knowledge graph | Manual review of 10 extracted post graphs; reject if >30% nodes are generic words |
| LightRAG + Pinecone context bleeding | Phase 2: LightRAG knowledge graph | Code review: Writer calls only Pinecone; Thinker calls only LightRAG — no cross-calls |
| Media pipeline partial failure with no cost tracking | Phase 3: Multi-model media orchestration | Every failed pipeline job has `failure_stage` + `credits_consumed` fields in `media_pipeline_ledger` |
| Remotion asset timeout in production | Phase 3: Multi-model media orchestration | Load test: render with 50MB HeyGen video + ElevenLabs audio; confirm completes within 120s |
| Strategist Agent recommendation spam | Phase 4: Strategist Agent | User study proxy: check dismissal rate after 7 days; must be below 50% |
| n8n webhook immediate-response mode | Phase 1: n8n infrastructure | Contract test: every ThookAI→n8n webhook call receives non-empty body with expected schema |
| Obsidian vault private notes exposure | Phase 7: Obsidian vault integration | Security test: plant test file outside designated folder; confirm Scout never reads it |

---

## Sources

- [n8n v2.0 Breaking Changes](https://docs.n8n.io/2-0-breaking-changes/) — Code nodes block `process.env` access, Sub-workflow data flow changes
- [n8n Queue Mode Configuration](https://docs.n8n.io/hosting/scaling/queue-mode/) — PostgreSQL required, SQLite unsupported, worker architecture
- [n8n Community: Worker Not Dequeuing in Queue Mode](https://community.n8n.io/t/self-hosted-n8n-cluster-on-railway-worker-not-dequeuing-jobs-webhook-triggers-stuck-in-queue/209719) — Worker initialization failure pattern
- [n8n Community: All executions stuck in Queued](https://community.n8n.io/t/urgent-all-executions-stuck-in-queued-queue-mode-redis-stack-review-request/225804) — Redis Bull script execution errors in queue mode
- [LightRAG GitHub README — HKUDS/LightRAG](https://github.com/HKUDS/LightRAG) — Embedding model lock-in, initialization requirement, LLM capability requirements (HIGH confidence — official source)
- [Remotion Timeout Documentation](https://www.remotion.dev/docs/timeout) — delayRender timeout failure modes, multi-provider pipeline risks
- [Remotion Production Checklist](https://www.remotion.dev/docs/lambda/checklist) — Lambda timeout configuration, asset loading pitfalls
- [fal.ai: Building Effective Gen AI Model Architectures](https://fal.ai/learn/devs/building-effective-gen-ai-model-architectures) — Multi-model integration layer requirements, data pipeline criticality
- [Production Knowledge Graph Systems 2025 — Medium](https://medium.com/@claudiubranzan/from-llms-to-knowledge-graphs-building-production-ready-graph-systems-in-2025-2b4aff1ec99a) — Entity deduplication, schema over-engineering, chunk overlap pitfalls
- [n8n Webhook Node Documentation](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.webhook/) — Immediate response mode pitfall, async pattern
- [Self-Hosting n8n on Render](https://render.com/articles/self-hosting-n8n-a-production-ready-architecture-on-render) — Queue mode architecture for Render deployments
- [IBM: Agentic Drift — Hidden Risk](https://www.ibm.com/think/insights/agentic-drift-hidden-risk-degrades-ai-agent-performance) — Proactive agent trust degradation patterns

---
*Pitfalls research for: ThookAI v2.0 — n8n orchestration, LightRAG, multi-model media, Strategist Agent*
*Researched: 2026-04-01*
