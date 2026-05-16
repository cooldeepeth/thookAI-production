# Wedge path audit — 2026-04-21

Scope: only the files that the LinkedIn wedge actually touches. Out-of-wedge files are ignored even when in the same directory. Rules: 1–2 sentence summary per file, note existing tests (or "none found"), flag up to three highest-severity issues. Security > correctness > quality. Line numbers are from current HEAD (`d1b6dbc`).

---

## Backend routes (10)

### `backend/routes/auth.py`

**Does**: Cookie+JWT auth (register/login/logout), CSRF token issuance, and GDPR export/delete endpoints.
**Tests**: test_auth.py, test_auth_core.py, test_csrf.py, test_oauth_flows.py, test_rate_limit_concurrent.py, test_error_format.py, test_e2e_critical_path.py, test_e2e_ship.py, test_dead_links.py, security/test_owasp_top10.py, security/test_input_validation.py, integration/test_api_routes_alive.py, test_frontend_quality.py
**Top issues**:

1. **Account-lockout user enumeration** (lines 142–145): entire lockout check wrapped in bare `except Exception: pass`, so any DB hiccup silently disables lockout and lets brute-force continue.
2. **Failed-login counter racy / never reset to zero** (lines 180–194): `return_document=True` defaults to pre-update doc, the lock threshold check is off-by-one, and a concurrent attacker can reach 6+ attempts before lockout triggers.
3. **Login response returns raw JWT alongside httpOnly cookie** (line 177): `token` is echoed in the JSON body, defeating httpOnly protection — any XSS or logging sink captures a long-lived session token.

### `backend/routes/auth_google.py`

**Does**: Native Google OAuth login/callback, creates or links user, issues JWT and redirects to frontend.
**Tests**: test_oauth_flows.py, test_auth_core.py, test_critical_fixes.py, integration/test_api_routes_alive.py
**Top issues**:

1. **JWT leaked via query string** (line 159): the redirect `…/dashboard?token=<jwt>` places the session token in the URL — logged by browser history, referrers, and reverse proxies — in addition to the cookie.
2. **Silent account linking on unverified email match** (lines 123–136): any Google account whose `email` matches an existing email-auth user is linked without checking `email_verified` from the ID token, enabling takeover if Google returns an unverified claim.
3. **OAuth state / nonce not validated** (lines 91–97): `authorize_access_token` is called with no explicit state/nonce verification and the default Starlette session store is in use — if session middleware is misconfigured CSRF on the OAuth callback is not enforced.

### `backend/routes/password_reset.py`

**Does**: Generates/consumes password reset tokens stored hashed in Mongo, sends email via Resend in background.
**Tests**: test_email_password_reset.py, integration/test_api_routes_alive.py
**Top issues**:

1. **No rate limiting on forgot-password** (lines 38–58): endpoint inserts a DB row and sends an email per request with no per-email / per-IP throttle, enabling email bombing and token-table flooding.
2. **`new_password` has no pydantic length bound** (lines 62–65): attacker with a valid token can submit a 10MB string; validation happens only through `validate_password_strength` whose bounds are unknown from this file.
3. **Token consumption not atomic** (lines 66–80): find → expiry check → update runs as three separate calls with no `used: False` filter on the update, so two concurrent reset requests with the same token both succeed in changing the password.

### `backend/routes/onboarding.py`

**Does**: Serves interview questions, analyzes posts via Claude, generates Persona Engine (with smart fallback), and bulk-imports post history.
**Tests**: test_onboarding_core.py, test_onboarding_persona.py, test_auth_guard_coverage.py, test_platform_features.py, test_e2e_critical_path.py, integration/test_api_routes_alive.py
**Top issues**:

1. **Unvalidated question_id used as list index** (line 160): `INTERVIEW_QUESTIONS[q_id]` with caller-supplied integer — negatives wrap to the tail silently; non-int `question_id` raises TypeError and 500s.
2. **LLM failure silently degrades to mock persona and still marks onboarding complete** (lines 192–247): any exception sets `persona_source="smart_fallback"` and `onboarding_completed=True`, so a transient outage permanently installs a generic persona with no retry surface.
3. **`import-history` bypasses its own documented 100-post limit** (lines 95, 265): pydantic caps `posts` at `max_length=50` while runtime check rejects >100 and the docstring claims 100 — real ceiling is 50 with a dead branch.

### `backend/routes/persona.py`

**Does**: Persona CRUD, public share links, regional-English toggle, HeyGen avatar creation, and ElevenLabs voice clone upload/create/delete.
**Tests**: test_onboarding_persona.py, test_sharing_notifications_webhooks.py, test_authenticated_responses.py, test_auth_guard_coverage.py, test_error_format.py, security/test_owasp_top10.py, integration/test_api_routes_alive.py
**Top issues**:

1. **Direct `os.environ.get` for HEYGEN_API_KEY violates config rule and bypasses validation** (line 402): `__import__("os").environ.get("HEYGEN_API_KEY", "")` reads at request time and its `startswith("placeholder")` check lets empty/whitespace keys through in some branches.
2. **SSRF via user-supplied `photo_url` sent to HeyGen** (lines 411–419): `data.photo_url` is an unvalidated string passed straight into the outbound call — no scheme/host allow-list; `file://` and internal IPs are reachable.
3. **Voice-clone upload accepts any `audio/*` MIME without sniffing** (line 549): `content_type` taken from the upload header; a mis-typed MP3 containing arbitrary bytes is stored under a user-controlled `..`-passing filename slice.

### `backend/routes/content.py`

**Does**: Creates/lists/approves content jobs, orchestrates media (image, carousel, voice, video, avatar) with Celery or sync fallback, and exports jobs to text/JSON/CSV.
**Tests**: test_content_sprint3.py, test_content_phase28.py, test_credit_refund_media.py, test_media_generation.py, test_media_orchestrator.py, test_e2e_critical_path.py, test_e2e_ship.py, test_strategist.py, test_credits_billing.py, test_feature_flags.py, test_dead_links_v2.py, test_auth_guard_coverage.py, security/test_owasp_top10.py, security/test_input_validation.py, test_error_format.py, integration/test_api_routes_alive.py
**Top issues**:

1. **Credit-deduction / pipeline contract drift** (lines 176–186 vs 932–940): `create_content` passes `generate_video` + `video_style` to `run_agent_pipeline`, but `regenerate_content` calls the same function with only 6 positional args — any signature change silently breaks one path.
2. **Celery-async image/voice/video endpoints skip credit deduction entirely** (lines 350–376, 547–573, 735–762): when Redis is configured the queued tasks return 202 without calling `deduct_credits` — credits are deducted only in the sync fallback, so any user with Redis can mint free media generations.
3. **`final_content` treated inconsistently** (lines 543, 829, 988–996, 1014): narrate + export call `.startswith`/`len` on `final_content` without the `_extract_content_text` guard used elsewhere; if the pipeline stores a dict (as `/job/{id}` shim implies) narrate/avatar-video 500 on `len(content)`.

### `backend/routes/platforms.py` (LinkedIn endpoints only)

**Does**: LinkedIn OAuth connect/callback, encrypted token storage, and proactive 24h token refresh.
**Tests**: test_platform_oauth.py, test_oauth_flows.py, test_platform_features.py, test_e2e_ship.py, test_critical_fixes.py, test_analytics_social.py, backend_test_sprint7.py, core/test_analytics_loop.py, integration/test_api_routes_alive.py
**Top issues**:

1. **LinkedIn callback does not validate `state` owner against the current session** (lines 184–197): `find_one_and_delete` verifies state exists but the callback is unauthenticated, so a stolen/guessed state lets an attacker bind THEIR LinkedIn account to the victim's `user_id` (classic OAuth fixation).
2. **`get_platform_token` leaks unrefreshed tokens and swallows refresh failure** (lines 593–612): when refresh fails, it falls back to the encrypted stored token even after `time_until_expiry < 24h`; only `expires_at < now` returns None, so any 12h-expired token with a broken refresh path is still returned and used.
3. **`_refresh_token` overwrites access_token on partial LinkedIn responses** (lines 664–685): if LinkedIn returns 200 with `access_token` but no `expires_in`, the default `3600` may be shorter than the real TTL; combined with a broad `except Exception` at line 687 every refresh error is swallowed to `logger.error` with no user-visible signal.

### `backend/routes/billing.py`

**Does**: Custom plan preview/checkout/modify, credit balance/usage/purchase, subscription status/cancel, Stripe webhook proxy and customer portal.
**Tests**: billing/test_billing_routes.py, billing/test_checkout.py, billing/test_subscriptions.py, test_stripe_e2e.py, test_credits_billing.py, test_csrf.py, test_e2e_ship.py, test_critical_fixes.py, test_auth_guard_coverage.py, security/test_owasp_top10.py, integration/test_api_routes_alive.py
**Top issues**:

1. **Webhook signature verification bypassed when secret is missing in dev/test** (lines 478–483): `settings.app.environment not in {"development","test"}` is the only guard; a production instance mis-configured with `ENVIRONMENT=test` accepts unsigned webhooks.
2. **`success_url` / `cancel_url` forwarded to Stripe without host allow-list** (lines 40–41, 146–205): attackers controlling a checkout URL can trigger Stripe to embed arbitrary post-payment redirect targets, enabling open-redirect phishing.
3. **`simulate_upgrade` / `simulate_credits` guarded only by `settings.app.environment`** (lines 506, 582): if `ENVIRONMENT` is unset or mis-cased these endpoints grant arbitrary credits / custom-tier upgrades to any authenticated user.

### `backend/routes/webhooks.py`

**Does**: Outbound webhook CRUD — register, list, delete, test-fire, and enumerate supported event names.
**Tests**: test_sharing_notifications_webhooks.py, integration/test_api_routes_alive.py
**Top issues**:

1. **`url` accepted as plain `str` with no validation at the route boundary** (lines 28–29, 46–50): comment says "validated in service" but the route will forward `file://`, `http://127.0.0.1`, or non-ASCII URLs; SSRF posture depends entirely on a service-layer check.
2. **No event-name validation against `SUPPORTED_EVENTS`** (lines 28–50): `events: List[str]` is passed through without membership check, so users can register for non-existent events that never fire — silent contract drift.
3. **`test_webhook` error disambiguation via free-form string match** (lines 88–90): `result.get("error") == "Webhook endpoint not found"` is a fragile string compare; any message drift converts a 404 into `success=false` with 200 status.

### `backend/routes/dashboard.py` (schedule/content + schedule/upcoming)

**Does**: Schedules a content job for future publishing and lists upcoming scheduled items for the user.
**Tests**: test_scheduling_phase31.py, test_e2e_critical_path.py, backend_test_sprint7.py
**Top issues**:

1. **Handler name shadowed by import** (lines 542–554): `async def schedule_content(...)` imports `from agents.planner import schedule_content`; inside the body the agent binding wins, so any future recursive/internal reference from this module would call the agent.
2. **No tenant check that `job_id` belongs to the caller** (line 549): route forwards `request.job_id` straight to `agents.planner.schedule_content(user_id, job_id, …)` with no prior `content_jobs.find_one({job_id, user_id})` — tenant isolation depends entirely on the agent.
3. **`upcoming` reads `content_jobs` while `calendar` reads `scheduled_posts`** (lines 566–594 vs 624): two different collections model the same concept, producing divergent UIs; the preview slice `final_content[:100] + "..."` also 500s if `final_content` is a dict.

---

## Backend agents (7)

### `backend/agents/commander.py`

**Does**: Builds a content plan (angle, hook, structure, word count) by prompting an LLM with persona + raw input; also exposes a model-routing helper with provider fallback.
**Tests**: core/test_pipeline_agents.py, test_pipeline_integration.py, test_pipeline_e2e.py, core/test_orchestrator_nodes.py, core/conftest.py
**Top issues**:

1. **Silent mock fallback on any failure** (lines 132–134): bare `except Exception` swallows JSON parse, LLM auth, and timeout errors, returning `_mock_commander` so callers cannot distinguish a real plan from a canned stub.
2. **Prompt injection via raw_input and persona fields** (lines 108–115): `raw_input` and every persona_card field are `str.format`-interpolated straight into the prompt with no escaping, so a user can inject instructions that override COMMANDER_SYSTEM.
3. **`select_optimal_model` returns unavailable provider on exhaustion** (lines 335–350): when no provider has a valid key it still returns the preferred `(provider, model)` tuple, masking missing config and forcing the caller to fail at send time.

### `backend/agents/scout.py`

**Does**: Runs Perplexity Sonar Pro research for a topic, optionally appending Obsidian-vault results; falls back to a canned mock when the key is missing or the call fails.
**Tests**: core/test_pipeline_agents.py, test_pipeline_integration.py, test_pipeline_e2e.py, test_obsidian_agents.py, core/test_orchestrator_nodes.py
**Top issues**:

1. **Mock masquerades as real research** (lines 74–75, 92–104): when Perplexity is missing or fails the agent silently returns fabricated "2025 data" bullets with `sources_found: 0`, and downstream Writer treats it as real research — hallucinated stats ship to users.
2. **Missing Perplexity response validation** (lines 62–70): indexes `data["choices"][0]["message"]["content"]` with no key/length guards, so a 200-status malformed body raises KeyError/IndexError and falls through to mock with only a warning log.
3. **Prompt injection via `research_query`** (lines 44–47): raw query (built from user input upstream) is concatenated directly into the Perplexity user message with no sanitisation.

### `backend/agents/thinker.py`

**Does**: Turns Commander+Scout outputs into a content strategy JSON (angle, hook options, structure, key insight), optionally injecting UOM, fatigue-shield, and knowledge-graph constraints.
**Tests**: core/test_pipeline_agents.py, test_pipeline_integration.py, test_pipeline_e2e.py, core/test_orchestrator_nodes.py
**Top issues**:

1. **Silent mock + unvalidated JSON** (lines 169–172): `json.loads(_clean_json(response))` returned directly; parse error or missing required keys (`hook_options`, `content_structure`) is swallowed and replaced with mock; on success the contract is never validated before Writer indexes into `hook_options[0]`.
2. **Knowledge-graph context not isolation-checked at call site** (lines 111–120): relies on a comment "enforces per-user isolation" — any bug in `query_knowledge_graph` silently leaks another tenant's topics into this user's prompt.
3. **Prompt injection via injected knowledge_context / uom / fatigue strings** (lines 143–166): attacker-controlled vault/KG content is concatenated unescaped into the Thinker prompt.

### `backend/agents/writer.py`

**Does**: Generates the final LinkedIn/X/Instagram draft via Claude using persona voice, research, Thinker strategy, regional-English rules, and optional vector-store style examples.
**Tests**: core/test_pipeline_agents.py, test_pipeline_integration.py, test_pipeline_e2e.py, test_content_phase28.py, test_critical_fixes.py, core/test_orchestrator_nodes.py
**Top issues**:

1. **Return-type contract drift on mock path** (lines 231, 269): real path returns `dict`; `_mock_writer` returns a `dict` but the function is annotated `-> str`, and downstream QC expects a string — mixing dict vs string breaks `draft[:2000]` in `qc.run_qc` (qc.py:96).
2. **Anthropic-only hard dependency** (lines 168–169): if only OpenAI is configured, Writer silently returns the mock draft — pro users get canned content with no error surfaced.
3. **Prompt injection via persona + research fields** (lines 195–211): every persona_card field, `thinker_output.hook_options[0]`, `scout_output.findings`, and vector-store `content_preview` examples are `str.format`-spliced in raw.

### `backend/agents/qc.py`

**Does**: Scores a draft against persona (personaMatch/aiRisk/platformFit) via LLM, recomputes `overall_pass` using UOM thresholds, layers a repetition-risk check, and exposes `validate_media_output`.
**Tests**: core/test_pipeline_agents.py, test_pipeline_integration.py, test_pipeline_e2e.py, test_qc_media.py, core/test_orchestrator_nodes.py, core/test_media_comprehensive.py
**Top issues**:

1. **`overall_pass` trusts unvalidated LLM JSON** (lines 99–105): assumed to be a dict with numeric fields; a string/list payload or missing keys crashes or coerces into a mock pass — bad drafts can score pass.
2. **Anti-slop vision defaults to pass on every failure** (lines 287–303): JSON parse error, timeout, missing vision model, and non-anthropic configs all return `slop_pass = True` — AI-artifact detection is disabled whenever it can't run.
3. **Vision prompt sends URL as text, not image** (lines 276–286): the prompt interpolates `media_url` into the text body instead of attaching it as a `UserMessage(images=[url])` — the check is performative.

### `backend/agents/anti_repetition.py`

**Does**: Exact-content dedup (TF-IDF similarity, phrase overlap), hook-type detection, hook-fatigue and content-diversity scoring over recent `content_jobs`, plus AI-powered variation suggestions.
**Tests**: core/test_pipeline_agents.py, test_pipeline_integration.py, test_pipeline_e2e.py
**Top issues**:

1. **`score_repetition_risk` returns 0/"unknown" on any failure** (lines 173–180): vector-store outage returns `repetition_risk_score: 0` and QC treats it as "fresh" — duplicate posts will pass the repetition gate whenever the vector store is down.
2. **`get_content_diversity_score` off-by-one on chained `.get` fallback** (line 388): `overused_hooks[0].get("percentage", 0)` yields 0 on `[{}]` → `hook_diversity = 100 - 0 = 100` — masks overuse.
3. **No tenant isolation guard on DB queries** (lines 255–261, 351–363): queries scoped by `user_id` from the caller; an empty string or wrong id (agency impersonation, stale session) returns another user's content with no check.

### `backend/agents/publisher.py`

**Does**: Publishes a post to LinkedIn (UGC API + registerUpload), X/Twitter (v2 tweets + v1.1 media), or Instagram (Graph v18) — with thread parsing and a multi-platform dispatcher.
**Tests**: test_publishing.py, test_n8n_bridge.py, test_e2e_ship.py, core/test_n8n_contracts.py
**Top issues**:

1. **Instagram container status polling has unbounded fall-through** (lines 413–430): if status never becomes `FINISHED`/`ERROR` within 30 attempts the loop exits silently and an un-ready container is published — confusing 400 from Graph instead of a clear timeout.
2. **LinkedIn image upload ignores PUT failure** (lines 111–116): PUT to the registerUpload URL has no status check; a failed upload still attaches the asset URN to the UGC post, producing a broken image or LinkedIn reject.
3. **X media/upload v1.1 called with OAuth2 bearer** (lines 234–239): `media/upload.json` requires OAuth1.0a signed requests; sending an OAuth2 bearer will 401/403 and any X media post silently falls back to text-only.

---

## Backend services (6)

### `backend/services/llm_client.py`

**Does**: Multi-provider async LLM chat shim (OpenAI/Anthropic/Google) with constructor-key fallback and transient-error retry on send_message.
**Tests**: none found (no direct unit tests; indirectly exercised via core/test_pipeline_agents.py).
**Top issues**:

1. **Silent fallback to wrong provider key** (lines 117–128, 190–192): `_resolve_key` prefers env `settings.llm.*_key` over constructor `api_key`; if caller passes an OpenAI key but settings has Anthropic set, the provider resolved by `with_model` gets a mismatched key with no warning.
2. **Retry swallows stack, fixed 1s backoff, no jitter** (lines 195–215): fixed `asyncio.sleep(1.0)` on 429/503; concurrent callers all retry together and re-thunder the provider. `_is_transient_error` matches substrings "500"/"502"/"503" anywhere in the message (line 135) — false positives on unrelated errors.
3. **API key leakage risk in exception messages** (lines 204–210, 233, 242, 267): SDK exceptions from OpenAI/Anthropic/Gemini are re-raised untouched; some reprs include request URLs and occasionally key fragments that callers log verbatim.

### `backend/services/credits.py`

**Does**: Credit ledger + plan-builder pricing; atomic `$inc` debit/credit on users collection, starter hard caps via count queries, monthly refresh on read.
**Tests**: billing/test_credits.py, test_credits_billing.py, billing/test_p0_add_credits_atomic.py, test_credit_refund_media.py
**Top issues**:

1. **Monthly refresh race + drift on read path** (lines 317–331): `get_credit_balance` reads `credits_last_refresh` then does a non-atomic `$set` with no guard on the old timestamp. Two concurrent reads both pass `days_since_refresh >= 30` and both overwrite `credits`, wiping in-flight deductions. Also uses calendar-day diff (31-day months lose a day) with no tz-of-record.
2. **Starter hard-cap TOCTOU + counts all history forever** (lines 256–283, 400–408): count query then `find_one_and_update` are separate — two concurrent VIDEO_GENERATE requests both pass and both deduct. Count has no `created_at` filter, so a user who upgraded to custom and downgraded to starter is permanently blocked.
3. **Refund path missing; `add_credits` has no idempotency** (lines 459–504): `add_credits` takes a free-form `source` with no dedup — Stripe webhook retries on `invoice.payment_succeeded` double-credit, and `handle_checkout_completed` credit-purchase path has no per-invoice guard.

### `backend/services/stripe_service.py`

**Does**: Stripe checkout/subscription orchestration, webhook dispatch with event-ID dedup, custom plan activation, customer portal session.
**Tests**: test_stripe_billing.py, test_stripe_e2e.py, billing/test_checkout.py, billing/test_webhooks.py, billing/test_p0_webhook_dedup.py
**Top issues**:

1. **Webhook idempotency inserts BEFORE handler runs — failures permanently lock out retries** (lines 511–546): event row is created before `handle_*` executes; if the handler raises, the function returns `{success: False}` but the row remains, so Stripe's retry hits `DuplicateKeyError` and returns `success=true, duplicate=true` — the event is silently lost.
2. **Untrusted webhook metadata controls credit grants** (lines 559–567, 586–588, 608, 650, 689): `handle_checkout_completed` and `handle_subscription_*` trust `session.metadata.credits`/`monthly_credits` from the webhook; `monthly_credits` defaults to `500` on missing (lines 608, 650, 689), so a malformed `custom_plan` subscription grants 500 free credits/month. `handle_payment_succeeded` also defaults to 500 and re-credits past-due users whose allowance was cleared.
3. **Stripe SDK import bug + customer-retrieve swallows deleted customers** (lines 87–88, 115–119, 504): `except ImportError` silently leaves `stripe = None`; subsequent `stripe.error.SignatureVerificationError` references on `None` raise AttributeError in that branch. `get_or_create_stripe_customer` catches any exception retrieving a customer and returns the stale customer_id (a deleted Stripe customer stays wired, breaking all future checkouts).

### `backend/services/subscriptions.py`

**Does**: Tier lookup, upgrade/downgrade, daily content limit check, feature-limit aggregation reading from `users.plan_config` or `TIER_CONFIGS`.
**Tests**: billing/test_subscriptions.py, test_credits_billing.py
**Top issues**:

1. **Downgrade wipes balance but doesn't cancel Stripe subscription** (lines 131–149, 169): `upgrade_subscription(new_tier="starter")` sets `credits: 0` and clears `plan_config` but `stripe_subscription_id` stays on the user; Stripe keeps charging and `handle_payment_succeeded` restores credits to the (default 500) allowance — user is downgraded in Mongo, still billed, and auto-restored.
2. **Daily-limit check uses UTC midnight regardless of user timezone** (lines 244, 286): a PST user resets at 4–5pm local, effectively halving the 50/day cap; eastern-timezone users can double-dip around midnight UTC. No per-user tz stored.
3. **`check_daily_limit` counts all content_jobs incl failed/pending** (lines 246–249): filter is `user_id + created_at >= today_start` with no `status` filter — errored, cancelled, and never-deducted jobs still count toward the daily cap. Inconsistent with credit ledger.

### `backend/services/vector_store.py`

**Does**: Pinecone persona embedding store — OpenAI text-embedding-3-small via raw httpx, per-user namespace, upsert + similarity query, mock embedding fallback on missing key.
**Tests**: none found.
**Top issues**:

1. **Sync httpx call inside async context blocks event loop** (lines 97–109, 131–178): `generate_embedding` uses sync `httpx.post(...)` with 30s timeout; upsert/query are `async def` and call it directly — every embedding generation serializes all FastAPI requests for up to 30s.
2. **Silent mock embedding on API failure stored as real** (lines 113–115, 164–172): on OpenAI embeddings error, falls back to a sha256-derived deterministic vector and writes it to Pinecone with no flag — poisons similarity queries indefinitely, so anti-repetition returns bogus matches against hash vectors.
3. **Unbounded `top_k` and namespace injection risk** (lines 149, 169, 181–208): `top_k` is caller-controlled with no clamp (Pinecone accepts 10000 and burns query units); `namespace=f"user_{user_id}"` and `vector_id=f"{user_id}_{content_id}"` are unvalidated — a user_id containing spaces/slashes/Unicode can collide namespaces across users.

### `backend/services/persona_refinement.py`

**Does**: LLM-driven voice evolution + persona card refinement suggestions; aggregates `content_jobs.performance_data` into `optimal_posting_times` and `performance_intelligence` on `persona_engines`.
**Tests**: none found (no direct tests for these public functions).
**Top issues**:

1. **Hardcoded `gpt-4o-mini` / `claude-sonnet-4-20250514` with silent mock fallback labeled `success: True`** (lines 106, 148–150, 240, 289–291): on any LLM exception, returns `_mock_persona_suggestions`/`_mock_evolution_analysis` wrapped in `{"success": True, "is_mock": true}` — callers checking only `result["success"]` treat mocks as real AI analysis. Also bypasses the CLAUDE.md "always Anthropic primary" rule for persona suggestions.
2. **Evolution & intelligence aggregates read `performance_data` with no simulation filter** (lines 491–511, 603–624): only filters `"error" not in performance_data` — the `analyst._simulate_engagement()` path writes performance_data without an `error` key, so simulated engagement is persisted into `persona_engines.performance_intelligence` and treated as ground truth.
3. **`apply_persona_refinements` mutates `card.*` without version guard; drops falsy updates** (lines 362–392): no optimistic concurrency — two concurrent applications race. `update.get("value")` at line 366 drops empty-string/0/False updates silently, so valid "clear this field" operations are lost.

---

## Frontend pages

### `frontend/src/pages/AuthPage.jsx`

**Does**: Email/password + Google OAuth + forgot-password form; redirects authenticated users to `/dashboard`.
**Tests**: `frontend/src/__tests__/pages/AuthPage.test.jsx`
**Top issues**:

1. **`apiFetch` 401 global redirect kills login error UX** (line 70): a failed login/register returning 401 navigates to `/auth?expired=1` before the status-based error ("Invalid email or password", line 95) is displayed.
2. **Missing `aria-label`/`htmlFor` on email/password/name inputs** (lines 327–347): accessible name comes only from `placeholder` — screen readers announce nothing for the primary auth form.
3. **Silent swallowing of forgot-password errors** (line 51): `catch { setForgotSent(true); }` treats network/server failures as success; users see "Check your email" even when the request never reached the backend.

### `frontend/src/pages/Onboarding/index.jsx`

**Does**: 5-step onboarding wizard that saves draft to localStorage and POSTs collected data to `/api/onboarding/generate-persona`.
**Tests**: `frontend/src/__tests__/pages/OnboardingWizard.test.jsx`
**Top issues**:

1. **Draft restoration shape mismatch** (lines 59, 102): draft stores `postsAnalysis` (object) but submit payload uses `postsAnalysis?.analysis`. If a restored draft holds a plain analysis string the submit silently sends `null`, losing the user's uploaded writing data.
2. **Generic catch with no detail for non-JSON responses** (lines 108–109): `await res.json()` rejects on HTML error pages and the catch just says "Something went wrong" — no retry affordance.
3. **Stale-closure risk in `useEffect`** (line 64): depends only on `user`; `user` transitioning null→loaded after the user manually advanced steps can re-run and clobber in-progress state.

### `frontend/src/pages/Onboarding/PhaseOne.jsx`

**Does**: Lets user paste past posts, calls `/api/onboarding/analyze-posts`, shows detected style analysis before advancing.
**Tests**: `frontend/src/__tests__/pages/PhaseOne.test.jsx`
**Top issues**:

1. **Unchecked `res.ok`** (line 21): `await res.json()` is called without inspecting `res.ok`; a 4xx/5xx with an error body is rendered in the fingerprint card as if it were real analysis.
2. **Swallowed error masquerades as real analysis** (lines 23–24): catch silently fabricates `"Posts noted. We'll use them to calibrate your voice."` with `demo_mode: true` but nothing in the UI indicates this is a fallback — users proceed believing their posts were analysed.
3. **Missing accessible label on textarea** (line 154): placeholder + testid only; no `aria-label`/`<label htmlFor>`.

### `frontend/src/pages/Onboarding/PhaseTwo.jsx`

**Does**: 7-question interview wizard, collects answers in local state, calls `onComplete(answers)` on last step.
**Tests**: none found (no dedicated test file).
**Top issues**:

1. **Back button removes the wrong answer** (line 45): `setAnswers(answers.slice(0, -1))` drops the LAST entry; after multiple back-forward navigations the last element may not correspond to the question the user returned from, misaligning with `question_id`.
2. **Keyboard shortcut ignores Ctrl+Enter** (line 137): `e.metaKey` triggers only Cmd on macOS; Windows/Linux users get no keyboard submit.
3. **Missing `aria-label` on textarea** (line 132): placeholder + testid only; the ⌘+Enter hint is visual-only.

### `frontend/src/pages/Onboarding/PhaseThree.jsx`

**Does**: Terminal onboarding step — loading shimmer, error retry, or renders the generated Persona Card with nav to `/dashboard/persona` or `/dashboard`.
**Tests**: covered indirectly by `OnboardingWizard.test.jsx`.
**Top issues**:

1. **No type-guard on persona card fields rendered directly** (lines 116, 117, 128, 156): `card.writing_voice_descriptor`, `content_niche_signature`, `item.value`, `writing_style_notes[i]` — if the API returns an object/null React crashes or renders `[object Object]`.
2. **Avatar `<img src={user.picture}>` has no `onError` fallback** (line 97): broken OAuth picture URL shows a broken-image chrome with no fallback to the initial letter.
3. **Empty `alt=""` on identifying profile photo** (line 97): should describe the user; accessibility regression for an identity image.

### `frontend/src/pages/Onboarding/VisualPaletteStep.jsx`

**Does**: Radio-group palette picker; sends selected key to parent on continue.
**Tests**: none found.
**Top issues**:

1. **`role="radio"` buttons lack keyboard arrow navigation** (line 77): ARIA radiogroup semantics expect arrow-key traversal; these are `<motion.button>` with only `onClick`, so SR users get `radio` role without keyboard selection.
2. **Continue button silently no-ops when unselected** (line 125): relies on `disabled` attribute; no error announcement for keyboard users.
3. (No further material issues — file is self-contained.)

### `frontend/src/pages/Onboarding/VoiceRecordingStep.jsx`

**Does**: 30-second browser MediaRecorder capture with playback, retry, skip; releases mic tracks on stop.
**Tests**: none found.
**Top issues**:

1. **Recorded audio blob is never uploaded — `onComplete(null)` discards it** (line 204): the continue handler passes `null` forward; parent stores `voiceSampleUrl = null`, silently losing the user's voice sample.
2. **Cleanup effect captures stale `audioUrl`** (lines 17–26): depends on `audioUrl`, so unmount cleanup revokes only the latest URL — rapid re-records leak earlier object URLs.
3. **Timer `setInterval` not cleared when MediaRecorder `onstop` fires early** (lines 47–55): if the stream ends externally, the timer keeps ticking and calls `setSecondsLeft` on unmounted/reset state.

### `frontend/src/pages/Dashboard/index.jsx`

**Does**: Lazy-loaded dashboard shell with Sidebar + nested routes for home/studio/persona/library/connections/settings.
**Tests**: none found (Sidebar tested separately).
**Top issues**:

1. **No route for `/dashboard/repurpose`** (lines 25–32): `DashboardHome` quick-action links to this path, but no `<Route>` is registered — falls through to `App.js` wildcard `Navigate to="/"`, bouncing the user to the landing page.
2. **No Suspense error boundary** (line 20): the top-level `<Suspense>` has no inner ErrorBoundary; a lazy-import chunk failure forces the root ErrorBoundary to take over the whole app with no per-route recovery.
3. **Dead page files after wedge cut** (lines 25–32): `StrategyDashboard.jsx`, `Campaigns.jsx`, `Analytics.jsx`, `Templates.jsx` still exist on disk but no route references them — any link into these paths redirects to `/`.

### `frontend/src/pages/Dashboard/DashboardHome.jsx`

**Does**: Greeting, stats row, onboarding banner, Daily Brief, recent jobs grid, quick actions, coming-soon list.
**Tests**: `frontend/src/__tests__/pages/DashboardHome.test.jsx`
**Top issues**:

1. **Broken navigation to a removed route** (line 16): `quickActions[3]` targets `/dashboard/repurpose`, which is not registered in `Dashboard/index.jsx` — clicks bounce the user out of the dashboard.
2. **X and Instagram quick actions still shipped** (lines 13–17): the wedge is LinkedIn-only per `.planning/WEDGE.md`, but these entry points launch Studio pre-selecting platforms that have no shells or publishers wired.
3. **`platformIcons[job.platform]` silently falls back to `PenLine`** (line 51): backend may return `twitter` (vs the `x` key in the icon map), showing a neutral pen icon — minor correctness concern.

### `frontend/src/pages/Dashboard/ContentStudio/index.jsx`

**Does**: Orchestrates content generation: input panel, agent pipeline view, output; polls job status every 2s.
**Tests**: `frontend/src/__tests__/pages/ContentStudio.test.jsx`
**Top issues**:

1. **`await res.json()` on non-JSON responses crashes the UX** (lines 113, 149): for a proxy-returned HTML error page the JSON parse throws and the user sees a cryptic `Unexpected token '<'` rather than the intended `err.detail || "Failed to start generation"`.
2. **Polling never stops on permanent failure** (line 82): `catch {}` in `pollJob` swallows all errors; repeated 500s keep the 2s interval firing indefinitely with no max attempts and no user-visible error.
3. **`handleApprove` / `handleDiscard` have no error handling** (lines 124–131, 162–172): PATCH requests use `await apiFetch(...)` with no `.ok` check and no try/catch — a failed approve sets local state to "Approved" while the job remains `reviewing` server-side.

### `frontend/src/pages/Dashboard/ContentStudio/InputPanel.jsx`

**Does**: Platform/format selectors, content-type textarea, video-generation toggle with tier gating, generate button.
**Tests**: exercised via `ContentStudio.test.jsx`.
**Top issues**:

1. **Platform selector exposes non-LinkedIn wedge features** (lines 4–37): X and Instagram with their content types are still selectable — dead UI lets users generate content for platforms with no routes/shells wired.
2. **No `aria-label` on the main content textarea** (line 140): primary input relies on placeholder only.
3. **Dead import `Info`** (line 1): cosmetic but signals lack of lint gate.

### `frontend/src/pages/Dashboard/ContentStudio/ContentOutput.jsx`

**Does**: Renders QC badges, platform shell preview, scout research, media-generation panel, export/publish panels, copy button, rejection modal.
**Tests**: exercised via `ContentStudio.test.jsx`.
**Top issues**:

1. **`document.getElementById("voice-audio")` collides across instances** (line 456): imperative DOM lookup by static id — multiple MediaPanel instances (tabs, regenerate) toggle the wrong `<audio>` element; should use a ref.
2. **Publish/Schedule don't check `res.ok` before `.json()`** (lines 1070, 1106): on 4xx/5xx (expired LinkedIn token, HTML proxy error) the JSON parse throws into the generic catch, losing the structured `data.results?.[platform]?.error` path.
3. **`onMediaUpdate` callback is a no-op; state lost on navigation** (lines 791–793): generated image/voice/video URLs live only in local MediaPanel state — navigating away and back loses them until a poll refetch completes.

### `frontend/src/pages/Dashboard/ContentStudio/AgentPipeline.jsx`

**Does**: Live progress display of 5 AI agents with status icons and per-agent summaries.
**Tests**: covered indirectly via `ContentStudio.test.jsx`.
**Top issues**:

1. **`getAgentStatus` collapses all post-current agents to "done"** (line 20): once the job is `reviewing`/`completed` every agent shows "done" regardless of whether it ran (e.g. Scout skipped) — misleading.
2. **`rawInput.substring(0, 60)` can split a surrogate pair** (line 38): may render a lone high-surrogate followed by `"..."`.
3. (Display-only; no further material issues.)

### `frontend/src/pages/Dashboard/ContentStudio/ExportActionsBar.jsx`

**Does**: Export to .txt, download images/zip, deep-link compose URLs to LinkedIn/X, info tooltip for Instagram.
**Tests**: none found.
**Top issues**:

1. **`contentText` forwarded verbatim to `buildLinkedInUrl` / `buildXUrl`** (lines 51, 57): helpers (out of scope here) must encode the text; if they don't, unescaped `&`/`#` truncate shared content.
2. **`window.open` has no popup-blocker fallback** (lines 52, 58): blocked popups silently succeed as no-ops; no fallback anchor.
3. **Instagram button is a dead-end in a LinkedIn-only wedge** (line 128): ships a surface that has no downstream platform support.

### `frontend/src/pages/Dashboard/ContentStudio/Shells/LinkedInShell.jsx`

**Does**: LinkedIn post mock UI: avatar, header, editable textarea, char counter, attachment bar, Post button.
**Tests**: covered indirectly via `ContentStudio.test.jsx`.
**Top issues**:

1. **Hardcoded fake profile "TC / Test Creator"** (lines 54, 60, 63): production preview shows a dummy persona instead of the authenticated user — misleading mock in a shipped UI.
2. **Silent truncation on paste beyond 3000 chars** (line 17): any paste exceeding the limit is entirely rejected with no user warning; textarea appears unresponsive.
3. **Preview "Post" button mutates parent content state** (line 140): clicking the mock Post button fires `onContentChange?.(text)` on the parent — a preview shouldn't be a functional control.

### `frontend/src/pages/Dashboard/ContentStudio/Shells/XShell.jsx`

**Does**: X thread parser and preview; splits `1/ 2/ 3/` pattern into tweet cards, per-tweet char counter.
**Tests**: covered indirectly via `ContentStudio.test.jsx`.
**Top issues**:

1. **Thread-parsing regex drops preamble before first marker** (lines 17–21): `content.split(tweetPattern)` drops any text preceding `1/` — hashtags or intro above the thread are silently lost.
2. **Keystroke re-numbering breaks custom formats** (line 51): every edit rewrites the whole content with new `${i+1}/` prefixes, clobbering non-sequential numbering the user chose deliberately.
3. **Hardcoded fake "@testcreator" identity** (line 126): preview misidentifies the user.

### `frontend/src/pages/Dashboard/ContentStudio/Shells/InstagramShell.jsx`

**Does**: Instagram post/story mock UI with caption editor, hashtag count, suggested hashtags.
**Tests**: covered indirectly via `ContentStudio.test.jsx`.
**Top issues**:

1. **Out-of-wedge shell still renders** (whole file): Instagram is explicitly deferred; this shell is reachable from the InputPanel platform selector.
2. **Hardcoded generic `suggestedHashtags`** (line 55): presented as AI-powered suggestion but static and persona-unaware.
3. **Silent caption truncation** (line 28): paste exceeding 2200 chars rejected with no feedback.

### `frontend/src/pages/Dashboard/Settings.jsx`

**Does**: Tabbed settings UI (Billing / Connections / Profile / Notifications / Data); BillingTab runs 6 parallel API calls and renders plan/credits/limits/costs.
**Tests**: `frontend/src/__tests__/pages/Settings.test.jsx`
**Top issues**:

1. **`Promise.all` + single catch hides 4xx/5xx responses** (line 107): individual non-ok responses don't throw — catch fires only on total network failure, so silent 4xx leave stale/null state with no error UI.
2. **Inline ConnectionsTab stub contradicts real `Connections.jsx`** (lines 612–624): renders a hardcoded "Not connected" placeholder for all 3 platforms independent of the fetched status on `/dashboard/connections`.
3. **Dead imports** (lines 11–17): `Users`, `ChevronRight`, `Gift`, `ArrowRight`, `Star`, `ExternalLink`, `Calendar`, `SettingsIcon` — maintenance noise.

### `frontend/src/pages/Dashboard/Connections.jsx`

**Does**: Lists social platforms, triggers OAuth connect/disconnect via `/api/platforms/*`, handles callback URL params for toasts.
**Tests**: none found.
**Top issues**:

1. **Unvalidated `success` query param rendered into a trust-indicator toast** (line 59): `?success=<crafted>` plants arbitrary text into a "Successfully connected to <x>" toast — phishing vector.
2. **Wedge exposes X and Instagram connect buttons** (lines 13–41): LinkedIn-only wedge but these entries in `PLATFORM_CONFIG` still render OAuth connect buttons for features not shipped.
3. **Fetch failure leaves `platforms` null forever** (line 91): no error/retry UI; the card then shows "0 of 3 platforms connected" silently.

---

## Coverage summary

Files with NO tests found: `backend/services/llm_client.py`, `backend/services/vector_store.py`, `backend/services/persona_refinement.py`, `frontend/src/pages/Onboarding/PhaseTwo.jsx`, `frontend/src/pages/Onboarding/VisualPaletteStep.jsx`, `frontend/src/pages/Onboarding/VoiceRecordingStep.jsx`, `frontend/src/pages/Dashboard/index.jsx`, `frontend/src/pages/Dashboard/ContentStudio/ExportActionsBar.jsx`, `frontend/src/pages/Dashboard/Connections.jsx`.

Files "indirectly" tested (no dedicated spec) exist for most agent internals — the pipeline tests cover happy-path only, not the silent-mock branches that are the biggest risk.
