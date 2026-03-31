# Codebase Concerns

**Analysis Date:** 2026-03-31

## Tech Debt

**Model Name Mismatch in Onboarding Pipeline:**
- Issue: `backend/routes/onboarding.py` lines 124 and 167 use incorrect Claude model name `"claude-4-sonnet-20250514"` instead of correct name `"claude-sonnet-4-20250514"`. Correct model used elsewhere in codebase (e.g., `backend/services/llm_client.py`).
- Files: `backend/routes/onboarding.py` (lines 124, 167)
- Impact: Every onboarding persona generation request silently fails LLM call and falls back to mock `_generate_smart_persona()`. All users receive generic, non-personalized persona cards. This destroys the core product value proposition since the Persona Engine is the foundation for all content generation.
- Fix approach: Replace `"claude-4-sonnet-20250514"` with `"claude-sonnet-4-20250514"` in both locations. Verify fallback behavior works correctly by testing onboarding flow end-to-end.

**Duplicate Pattern Fatigue Detection Systems:**
- Issue: Two separate systems detect content repetition but don't communicate. `backend/services/persona_refinement.py` contains `get_pattern_fatigue_shield()` and `backend/agents/anti_repetition.py` implements separate pattern tracking. Only `anti_repetition.py` is called during generation pipeline. `persona_refinement.py` fatigue shield is only exposed via analytics endpoint (`GET /analytics/fatigue-shield`) but never fed back into generation.
- Files: `backend/services/persona_refinement.py`, `backend/agents/anti_repetition.py`, `backend/agents/pipeline.py` (Thinker step)
- Impact: Content generation ignores fatigue data available in the persona refinement system. Users see hook patterns repeat despite analytics warning them of hook fatigue. System wastes compute calculating fatigue data that never influences output.
- Fix approach: In `backend/agents/pipeline.py` during Thinker step, call `get_pattern_fatigue_shield(user_id)` and inject flagged patterns as explicit avoidance instructions in the Thinker prompt. Mark `anti_repetition.py` as deprecated in comments. Plan gradual removal after 2-3 sprints once unified system is stable.

**Vector Store Implementation Dead Code:**
- Issue: `backend/services/vector_store.py` is fully implemented with Pinecone client wrapper and methods `store_content_embedding()`, `find_similar_content()`, `delete_embeddings()`. However, nowhere in the codebase calls these methods. `backend/agents/learning.py` stores approved content only in MongoDB as raw text. `backend/agents/writer.py` never retrieves similar past content before generating new content.
- Files: `backend/services/vector_store.py`, `backend/agents/learning.py`, `backend/agents/writer.py`
- Impact: Expensive Pinecone service is initialized but never used. Memory of similar content cannot improve new generation. Writers cannot learn from past successful content patterns.
- Fix approach: In `backend/agents/learning.py` after storing approval to DB, call `vector_store.store_content_embedding(user_id, content, {topic, platform, performance})`. In `backend/agents/writer.py` at start of generation, call `vector_store.find_similar_content(user_id, topic)` with limit 5, extract style patterns from results, and inject into system prompt as examples. Add error handling so vector store failures don't block content generation.

**Media Upload Fallback to Ephemeral Storage:**
- Issue: `backend/routes/uploads.py` lines 156-175 falls back to `/tmp/thookai_uploads/` when R2 is not configured. On cloud deployments (Render, Railway, Vercel), `/tmp` is ephemeral—files are lost on restart. URLs stored in `db.uploads.url` become dead links within hours.
- Files: `backend/routes/uploads.py` (lines 156-175)
- Impact: In production deployments without R2 configured, all user uploads (context images, videos, documents) are lost when containers restart. MongoDB holds invalid URLs pointing to deleted files. Users cannot re-access their uploads or use them for content context.
- Fix approach: In `server.py` lifespan, after loading config, add explicit check: if `settings.app.is_production` and not `settings.r2.has_r2()`, log ERROR and set startup warning. In `uploads.py`, reject all uploads with HTTP 503 and message "Media storage not configured" if R2 is unavailable in production. Never fall back to `/tmp` in production.

**Designer Agent Image Generation Blocks Event Loop:**
- Issue: `backend/agents/designer.py` runs image generation polling loop synchronously when Celery is not configured. The polling loop (`while` loop checking status) is synchronous, running in the FastAPI event loop. 5-minute timeout on large image generations blocks all other async operations.
- Files: `backend/agents/designer.py` (polling loop in image generation method)
- Impact: When user requests images during onboarding or content generation, the entire FastAPI server freezes for up to 5 minutes under concurrent load. Other users' requests queue up. Server becomes unresponsive.
- Fix approach: Wrap the polling loop in `asyncio.wait_for(..., timeout=60.0)` to yield control periodically. Better: if Celery is available, always use async task path via `media_tasks.generate_image.apply_async()` and poll task status instead of polling image generation API directly. For non-Celery deployments, implement polling via `asyncio.sleep(1)` instead of busy-wait.

**Email Service Not Implemented:**
- Issue: `RESEND_API_KEY` and `FROM_EMAIL` are defined in `backend/config.py` but never used. `backend/routes/password_reset.py` generates password reset tokens but never emails them. `backend/routes/agency.py` invite endpoint logs "invitation sent" and returns success but sends no actual email.
- Files: `backend/routes/password_reset.py`, `backend/routes/agency.py`, missing: `backend/services/email_service.py`
- Impact: Users cannot reset forgotten passwords—reset tokens are generated but inaccessible. Agency workspace invitations are silent. Team collaboration features appear to work but don't function.
- Fix approach: Create `backend/services/email_service.py` with `send_password_reset_email(to_email, reset_link)` and `send_workspace_invite_email(to_email, workspace_name, invite_link)`. Use `resend` Python package (already in `requirements.txt`). In `password_reset.py`, call email service after token generation. In `agency.py`, call email service when creating invitation. Add test emails to dev `.env` to verify without live API keys.

**Stripe Configuration Validation Missing:**
- Issue: `backend/services/stripe_service.py` lines 48-50 define credit packages that reference `settings.stripe.price_credits_100/500/1000` which are often empty strings in development. When user attempts to purchase credits, Stripe API throws `InvalidRequest` error for empty Price ID. Also, `STRIPE_WEBHOOK_SECRET` is frequently empty—webhook signature verification fails silently in `backend/routes/billing.py`.
- Files: `backend/services/stripe_service.py` (lines 48-50), `backend/routes/billing.py` (webhook endpoint)
- Impact: Credit purchases fail with vague error messages. Subscription upgrades from Stripe don't propagate to database—users appear unpaid after purchase. Billing history is unreliable.
- Fix approach: In `server.py` lifespan, add startup check: if `settings.app.is_production` and any `STRIPE_PRICE_*` vars are missing, log CRITICAL error with list of missing vars. In `stripe_service.py`, add runtime validation in `create_checkout_session()` before calling Stripe API. In `billing.py` webhook endpoint, validate `STRIPE_WEBHOOK_SECRET` is set before accepting requests; return 503 if missing.

**Analytics Data Fabricated, Not Real:**
- Issue: `backend/agents/analyst.py` and `backend/routes/analytics.py` calculate all metrics (engagement, reach, impressions, optimal_posting_times) from internal `db.content_jobs` counts, not actual platform API data. `db.persona_engines.performance_intelligence` is always initialized empty and never populated with real post performance. No code exists to poll LinkedIn/X/Instagram APIs after post publishing.
- Files: `backend/agents/analyst.py`, `backend/routes/analytics.py`, `backend/services/` (missing: social_analytics.py)
- Impact: Analytics dashboard shows zero engagement for all posts. Users cannot see real performance metrics. Persona refinement is blind—system cannot learn which content actually resonates on each platform. Users distrust analytics and churn.
- Fix approach: Create `backend/services/social_analytics.py` with methods to poll platform APIs after post publishing. In `backend/tasks/content_tasks.py`, after publishing succeeds, schedule 24-hour and 7-day polling tasks. Store results in `db.content_jobs.performance_data`. Aggregate into `db.persona_engines.performance_intelligence.optimal_posting_times` and `best_performing_formats`. Fall back to zero if APIs unavailable—show "awaiting platform data" rather than fabricated numbers.

**Inconsistent Error Handling in Media Tasks:**
- Issue: `backend/tasks/media_tasks.py` raises generic `Exception(message)` for credit errors, video generation errors, image generation errors (lines 70, 92, 142, 161, 205, 222, 266, 299, 359). These are caught at task level and cause task retries, but error context is lost. User sees generic "Generation failed" without knowing why.
- Files: `backend/tasks/media_tasks.py`
- Impact: When media generation fails (insufficient credits, API error, timeout), task retries 3 times without user feedback. User never knows request failed. Content job appears stuck in "processing" state forever.
- Fix approach: Define custom exception classes: `InsufficientCreditsError(credit_cost, user_balance)`, `MediaGenerationError(provider, error)`, `TimeoutError`. Catch each specifically. Store error message and type in `db.content_jobs.error` and `db.content_jobs.error_type`. Mark job as failed after final retry with error details visible to frontend. Send notification to user when media generation fails with reason.

**Race Condition in Credit Deduction:**
- Issue: `backend/services/credits.py` deduct_credits() method reads user balance, checks sufficiency, then deducts. Between read and write, another concurrent request can deduct same credits. User can generate more content than balance allows.
- Files: `backend/services/credits.py` (deduct_credits function)
- Impact: Multiple simultaneous requests can exceed user credit limit. Users see negative credit balance. Billing becomes inaccurate.
- Fix approach: Use MongoDB's atomic operations: Replace read-then-check-then-update with `find_one_and_update()` with conditional filter `{"credits": {"$gte": amount}}`. If update returns null, credits were insufficient. Add transaction support if using MongoDB 4.0+.

## Known Bugs

**Celery Tasks Dead on Non-Production Deployments:**
- Symptoms: Scheduled posts never publish. Daily credit limits never reset. Old jobs never clean up.
- Files: `backend/celery_app.py` (created, working), `backend/celeryconfig.py` (created, working), `backend/Procfile` (missing worker/beat entries)
- Trigger: Deploy without adding `worker: celery -A celery_app worker` and `beat: celery -A celery_app beat` to Procfile. Without separate worker/beat processes, `@shared_task` decorators in `backend/tasks/content_tasks.py` and `backend/tasks/media_tasks.py` are never executed.
- Status: Celery app and config files exist and are correctly structured. Issue is operational—Procfile does not spawn worker/beat processes.
- Workaround: Manually start Celery worker and beat processes in separate terminal windows during development: `celery -A celery_app worker` and `celery -A celery_app beat`.

**Publishing Placeholder in Fallback Path:**
- Symptoms: In dev/test without publisher agent, posts appear to publish successfully but are never actually sent to platforms.
- Files: `backend/tasks/content_tasks.py` lines 345-351 (fallback when `agents.publisher` import fails)
- Trigger: Development environment where `agents/publisher.py` doesn't exist or cannot be imported. Code falls back to: `logger.warning("[SIMULATED]..."); return True`. Post marked as published in DB but never reaches platform.
- Workaround: Implement `backend/agents/publisher.py` or ensure import succeeds. Use `is_production` check to fail loudly in production rather than silently simulating.

## Security Considerations

**JWT Token Stored in localStorage:**
- Risk: localStorage is vulnerable to XSS attacks. If attacker injects script, token can be stolen.
- Files: `frontend/src/context/AuthContext.jsx` (lines 38, 50), `frontend/src/lib/api.js`
- Current mitigation: Frontend runs within same-origin policy. No `HttpOnly` flag possible for localStorage. Backend validates token signature before accepting requests.
- Recommendations: (1) Add `HttpOnly`, `Secure`, `SameSite=Strict` cookie support to auth endpoints as alternative to localStorage. (2) Implement Content Security Policy (CSP) headers in backend to prevent inline script execution. (3) Add token rotation: issue short-lived access tokens (5-15 min) + refresh tokens (7 days) stored in HttpOnly cookies. (4) Periodically audit frontend dependencies for XSS vulnerabilities (npm audit).

**Password Reset Tokens Not Rate Limited:**
- Risk: Attacker can enumerate password reset tokens via brute force. 6-character alphanumeric token has ~2M combinations.
- Files: `backend/routes/password_reset.py` (token generation)
- Current mitigation: Tokens are UUIDs (128-bit), not short strings. UUID + timestamp hash makes brute force infeasible.
- Recommendations: (1) Add IP-based rate limiting to password reset endpoint (max 5 requests per email per hour). (2) Log reset attempts and flag suspicious patterns. (3) Notify user of reset attempt via backup email if available.

**Stripe Webhook Secret Not Validated in Dev:**
- Risk: If `STRIPE_WEBHOOK_SECRET` is empty, webhook signature verification skipped. Attacker can forge webhook events to upgrade user subscriptions without payment.
- Files: `backend/routes/billing.py` (webhook endpoint)
- Current mitigation: Production deployments require `STRIPE_WEBHOOK_SECRET`. Dev/test deployments may skip validation.
- Recommendations: (1) Fail webhook acceptance if secret is empty and `is_production=true`. (2) Log WARNING if secret is empty in any environment. (3) In test environment, only accept webhooks from test webhook endpoint (use Stripe CLI, not direct HTTP).

**R2 Credentials in Code Path:**
- Risk: `backend/routes/uploads.py` uses `settings.r2.*` which reads from environment. Credentials are never logged, but if `.env` is committed accidentally, credentials leak.
- Files: `backend/routes/uploads.py`, `backend/config.py`
- Current mitigation: `.gitignore` excludes `.env`. `settings` dataclass reads from environment only, never printed.
- Recommendations: (1) Pre-deployment check: scan git history for accidentally committed `.env` files using `git log -p -- .env`. (2) Use Cloudflare's native secret rotation for R2 credentials. (3) In production, use managed secrets via Render/Railway platform rather than `.env` files.

**API Keys in Error Messages:**
- Risk: Generic error messages returned to clients sometimes include API keys in traceback.
- Files: Various agent and service files with `except Exception` handlers
- Current mitigation: Frontend receives generic "Generation failed" message. Backend logs full traceback internally.
- Recommendations: (1) Audit all exception handlers to ensure error messages never contain API key substrings. (2) In `server.py`, add error middleware that sanitizes exception details before returning to client. (3) Log full exception to Sentry for debugging without exposing to frontend.

## Performance Bottlenecks

**Synchronous Polling in Designer Agent:**
- Problem: Image generation polling blocks event loop for up to 5 minutes.
- Files: `backend/agents/designer.py`
- Cause: Polling loop runs synchronously in async context. No `await` or `asyncio.sleep()` to yield control.
- Impact: Under load (10+ concurrent users requesting images), server becomes unresponsive. Latency increases for all endpoints.
- Improvement path: (1) Convert polling to use `asyncio.sleep(1)` instead of busy-wait. (2) Move image generation to Celery task via `backend/tasks/media_tasks.py` to run in background. (3) Implement webhook from image provider (fal.ai) to notify when generation complete instead of polling.

**N+1 Query Pattern in Analytics:**
- Problem: `backend/routes/analytics.py` fetches user's content jobs one at a time in loop. Each job fetch is separate database query.
- Files: `backend/routes/analytics.py` (analytics aggregation endpoint)
- Cause: Code iterates over content list and queries `db.content_jobs.find_one({job_id: ...})` per iteration.
- Impact: Analytics dashboard takes 5-10 seconds to load for users with 100+ content jobs. Blocks UI rendering.
- Improvement path: (1) Replace loop of `find_one()` calls with single `find_many({job_id: {$in: [...]}})` query. (2) Add MongoDB aggregation pipeline to compute stats server-side rather than fetching all docs to Python. (3) Cache analytics results for 1 hour.

**No Database Indexes on High-Query Collections:**
- Problem: Collections with frequent queries (`content_jobs`, `scheduled_posts`, `platform_tokens`) may lack indexes on common filter fields.
- Files: `backend/db_indexes.py` (defines all indexes at startup)
- Cause: Indexes are created at startup via `db_indexes.py`, but may be incomplete for all queries.
- Impact: Queries without indexes full-scan collections. Latency degrades as data grows.
- Improvement path: Review `backend/db_indexes.py` to ensure indexes exist on: `{user_id, status}` for content jobs; `{user_id, platform}` for platform tokens; `{scheduled_at, status}` for scheduled posts. Add missing indexes.

**Memory Leak in Agent Orchestrator:**
- Problem: `backend/agents/orchestrator.py` maintains long-lived agent state in memory. No cleanup when pipeline completes.
- Files: `backend/agents/orchestrator.py`
- Cause: Orchestrator holds references to all agents' internal state. State is not cleaned up after job completion.
- Impact: Long-running deployment accumulates memory. After 1000+ jobs, memory usage grows to 500MB+.
- Improvement path: (1) Implement `__del__` method on orchestrator to clean up agent references. (2) Use weak references for temporary state. (3) Add memory profiling to CI/CD to catch regressions.

## Fragile Areas

**Pipeline State Machine in Orchestrator:**
- Files: `backend/agents/orchestrator.py`
- Why fragile: Complex state transitions (pending → processing → reviewing → approved → scheduled → published). Edge cases where job status gets stuck if agent crashes mid-execution.
- Safe modification: (1) Before changing any `status` field, write comprehensive unit tests covering all state transitions. (2) Add idempotency: if agent restarts, it should not re-run completed steps. (3) Test with artificially killed agents (simulate crash) to ensure state recovery.
- Test coverage: Gaps in testing state recovery. No tests for "agent crashed, job stuck in 'processing'" scenarios.

**Content Job Editing Logic:**
- Files: `backend/routes/content.py` (content generation and editing endpoints)
- Why fragile: Users can edit generated content after approval. Edits update DB but don't trigger persona learning or update scheduled posts. If user edits then schedules, scheduled post may use unedited content.
- Safe modification: (1) When content is edited, atomically update scheduled posts referencing that job. (2) Add audit trail: log all edits with timestamp and diff. (3) Test edit → schedule → publish flow with multiple platforms.
- Test coverage: No tests for concurrent edit + scheduling. No tests for multi-platform scheduled posts after edit.

**Persona Sharing and Expiry:**
- Files: `backend/routes/persona.py` (persona share endpoints)
- Why fragile: Persona shares have expiry times but no cleanup task (scheduled to exist but may not run). Expired shares remain accessible if cleanup task fails.
- Safe modification: (1) Always check `expires_at > now()` before returning shared persona. (2) Add redundant cleanup via `GET /api/persona/share/{token}` endpoint—check expiry and delete if expired. (3) Test that expired shares cannot be accessed even if database cleanup fails.
- Test coverage: No tests for share expiry. No tests for access attempts on expired shares.

**Workspace Member Removal and Access Control:**
- Files: `backend/routes/agency.py` (workspace member management)
- Why fragile: When member is removed, their active sessions don't immediately expire. Removed member can continue accessing workspace until session token expires (7 days).
- Safe modification: (1) When member is removed, add user_id to blocklist in Redis. (2) In auth middleware, check blocklist before allowing access. (3) Delete all existing sessions for removed user immediately.
- Test coverage: No tests for access control after member removal. No tests for concurrent access during removal.

## Scaling Limits

**MongoDB Connection Pool Exhaustion:**
- Current capacity: `max_pool_size: 100` (from `backend/config.py` line 28)
- Limit: Under sustained load with 200+ concurrent requests, connection pool exhausts. Subsequent requests queue or timeout.
- Impact: Response time degrades. Requests timeout after 5 seconds. Users see 503 errors.
- Scaling path: (1) Increase `MONGO_MAX_POOL_SIZE` to 200-300 (requires MongoDB cluster to support). (2) Implement connection pooling proxy (PgBouncer for Postgres, but not available for MongoDB). (3) Implement circuit breaker: if connection pool < 10%, return 503 and reject requests gracefully. (4) Monitor connection pool usage and add alerting at >80%.

**Celery Task Queue Backlog:**
- Current capacity: Redis default memory 256MB, no task queue size limit.
- Limit: With 500+ scheduled tasks queued (users scheduling posts during day), Redis memory fills. Task enqueueing fails.
- Impact: Scheduled posts stop queueing. Users' scheduled posts never publish.
- Scaling path: (1) Set Redis `maxmemory` policy to `allkeys-lru` to evict old tasks. (2) Move from Redis to RabbitMQ as broker (more stable under load). (3) Implement task rate limiting: drop low-priority tasks if queue size > 1000. (4) Add alerting when task backlog > 500.

**Vector Store (Pinecone) Cost:**
- Current capacity: Pinecone starter tier—10GB, 100K vectors.
- Limit: Each user content generates 1-2 embeddings (topic + full text). 10K users × 100 posts = 1M embeddings = exhausts free tier.
- Impact: Vector searches fail. New content cannot be compared to similar past content.
- Scaling path: (1) Upgrade to Pinecone production tier (pay-as-you-go). (2) Implement tiered embeddings: only embed top 50 posts per user. (3) Switch to self-hosted Milvus or Weaviate if cost prohibitive.

**Media Storage (R2) Egress Bandwidth:**
- Current capacity: Unlimited (Cloudflare R2 has no egress cost, only storage and API calls).
- Limit: Storage size not enforced. No quota per user.
- Impact: Malicious user could upload terabytes of data, inflating storage costs.
- Scaling path: (1) Add storage quota per subscription tier (free: 1GB, pro: 100GB, studio: 500GB). (2) Implement automatic deletion of media older than 90 days. (3) Add pre-upload size check and reject uploads exceeding quota.

## Dependencies at Risk

**Claude Model Version Drift:**
- Risk: `backend/services/llm_client.py` hardcodes `claude-sonnet-4-20250514`. When Anthropic releases newer model (e.g., `claude-sonnet-4-20260515`), codebase continues using old model. Performance degrades, new features unavailable.
- Impact: Content generation quality falls behind competition. Onboarding persona generation uses older model.
- Migration plan: (1) Add `LLM_MODEL_NAME` env var to `backend/config.py`. Default to `claude-sonnet-4-20250514`. (2) Allow runtime override via setting. (3) In CLAUDE.md briefing, document how to upgrade model globally.

**Stripe API Version Pinning:**
- Risk: `backend/services/stripe_service.py` depends on Stripe API version specified in `requirements.txt`. If major version released (stripe v10 → v11), breaking API changes may occur.
- Impact: Payment processing fails. Webhooks may not deserialize correctly.
- Migration plan: (1) Add integration tests for all Stripe endpoints using Stripe test API keys. (2) When updating `stripe` package major version, run full test suite. (3) Pin to minor version in `requirements.txt` (e.g., `stripe==10.2.*`) to allow patch updates but catch major changes.

**Resend Email Service Provider:**
- Risk: Resend is a new service provider (founded 2023). If service shuts down or becomes unreliable, email functionality breaks.
- Impact: Password resets and invitations fail. Users cannot recover accounts.
- Migration plan: (1) Implement email service abstraction: `backend/services/email_service.py` with provider interface. (2) Support fallback providers: Resend primary, SendGrid secondary. (3) Implement dry-run mode: log emails instead of sending in development.

**OpenAI Fallback Dependency:**
- Risk: `backend/services/llm_client.py` falls back to OpenAI if Anthropic unavailable. OpenAI API costs 3-4x more, and quality varies. Long-term reliance creates cost and quality issues.
- Impact: If Anthropic API flaky, system defaults to expensive OpenAI. User experience degrades (different model = different output style).
- Migration plan: (1) Implement fallback ranking: Anthropic → Gemini → OpenAI (in cost order). (2) Add metrics: track which model used per request. (3) Alert if fallback used more than 5% of requests (indicates primary API issues).

## Missing Critical Features

**Real-Time Collaboration in Content Editor:**
- Problem: Multiple team members cannot edit the same post simultaneously. Last-write-wins, conflicts lost.
- Blocks: Agency feature cannot scale beyond 2 people. Freelancers cannot collaborate with clients on edits.
- Implementation path: (1) Implement Operational Transformation (OT) or CRDT-based conflict resolution for text edits. (2) Use WebSocket for real-time sync. (3) Store edit history with full lineage. Options: self-hosted Yjs + WebSocket server, or Firebase Realtime Database.

**Post Scheduling Timezone Support:**
- Problem: All scheduling uses UTC. User in US timezone sees "scheduled for 5 AM UTC" (9 PM US time). Confusing.
- Blocks: Agencies managing multiple timezones cannot reliably schedule posts.
- Implementation path: (1) Add `user_timezone` field to `db.users`. (2) Store `scheduled_at` in UTC, add `scheduled_at_user_tz` display field. (3) In UI, show both UTC and user timezone. (4) When processing scheduled posts task, convert UTC to user's timezone for display.

**Bulk Content Generation:**
- Problem: User can only request 1 post at a time via `POST /api/content/generate`. Generating week of posts requires 7 API calls.
- Blocks: Content calendar planning is tedious. Batch processing could reduce LLM cost per post.
- Implementation path: (1) Add endpoint `POST /api/content/generate-bulk` accepting array of generation requests. (2) Queue each as Celery task. (3) Return job IDs array. (4) Implement bulk status endpoint returning array of job statuses.

## Test Coverage Gaps

**No E2E Tests for Content Pipeline Failures:**
- What's not tested: Pipeline behavior when individual agents timeout or fail. What happens if Scout agent crashes? Does job recover?
- Files: `backend/agents/pipeline.py`, `backend/agents/*.py` (all agent modules)
- Risk: Changes to error handling in pipeline can break recovery logic. Users experience silent failures.
- Priority: High

**No Tests for Concurrent Credit Deductions:**
- What's not tested: Multiple simultaneous content generation requests from same user. Do credits deduct correctly or allow negative balance?
- Files: `backend/services/credits.py`, `backend/routes/content.py`
- Risk: Billing becomes inaccurate. Users generate unlimited content without cost.
- Priority: High

**No Tests for Database Failover:**
- What's not tested: MongoDB connection loss. Does the application recover or crash? How long are requests blocked?
- Files: `backend/database.py`, `backend/server.py`
- Risk: Brief database outage causes server crash. Requests timeout indefinitely.
- Priority: Medium

**No Tests for Celery Task Retries:**
- What's not tested: Celery task failure and retry behavior. Do tasks retry correct number of times? Are results persisted?
- Files: `backend/tasks/content_tasks.py`, `backend/tasks/media_tasks.py`
- Risk: Failed tasks disappear silently or retry infinitely. User never knows job failed.
- Priority: Medium

**No Frontend Tests for Token Expiry:**
- What's not tested: Frontend behavior when JWT token expires during user session. Can user still navigate? Is logout forced?
- Files: `frontend/src/context/AuthContext.jsx`, `frontend/src/lib/api.js`
- Risk: User session becomes invalid. Frontend continues making requests with expired token. User sees generic error.
- Priority: Medium

---

*Concerns audit: 2026-03-31*
