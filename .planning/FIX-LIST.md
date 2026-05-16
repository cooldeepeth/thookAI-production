# Fix List — wedge/linkedin-only

Rules: Fix in order. Each fix ≤ 2 hours. Anything larger must be split.
After each fix: run the 3 Playwright tests, commit atomically, report.

## Tier 0 — Security (fix before any user)

FIX-01: OAuth state fixation on LinkedIn callback [S]

- File: backend/routes/platforms.py ~line 184-197
- Problem: callback verifies state row exists but does NOT tie it to the authenticated session that initiated it. Attacker can complete OAuth for victim's user_id.
- Fix: when storing the state, record the authenticated user_id (or session fingerprint). In callback, verify state.user_id matches the currently authenticated user. If unauthenticated initiation is required, bind state to IP+user-agent at minimum.

FIX-02: Google OAuth links on unverified email [S]

- File: backend/routes/auth_google.py ~line 123-136
- Problem: email match to existing user triggers account link with no check on email_verified claim in the ID token.
- Fix: before linking, assert id_token_claims['email_verified'] is True. If False, return 400 with message asking user to verify their Google email.

FIX-03: JWT embedded in redirect URL [XS]

- File: backend/routes/auth_google.py ~line 159
- Problem: raw JWT in query string → browser history, referrer headers, CDN logs.
- Fix: redirect to frontend with a short-lived one-time code, exchange for JWT on a POST from the frontend. Or set as httpOnly cookie. Do not put JWT in URL.

## Tier 1 — Billing (fix before Day 6 Stripe live)

FIX-04: Stripe webhook idempotency swallows handler failures [M]

- File: backend/services/stripe_service.py ~line 511-546
- Problem: idempotency row inserted BEFORE handler runs. If handler throws, event is permanently lost — Stripe retry sees DuplicateKeyError, returns success, stops retrying.
- Fix: insert idempotency row AFTER successful handler completion (or use a two-phase: insert pending, handler runs, mark complete; on retry, if pending → retry handler, if complete → skip).

FIX-05: monthly_credits defaults to 500 on missing metadata [S]

- File: backend/services/stripe_service.py ~line 608, 650, 689
- Problem: malformed subscription metadata mints 500 free credits silently.
- Fix: if monthly_credits is absent from metadata, raise an exception and alert (Sentry) rather than defaulting. For the wedge single-tier, hard-code 500 only for the known product ID.

FIX-06: Downgrade clears credits but does not cancel Stripe subscription [S]

- File: backend/services/subscriptions.py ~line 131-149
- Problem: user sees $0 and 0 credits; Stripe keeps charging; next payment_succeeded restores 500 credits.
- Fix: when downgrading, call stripe.Subscription.modify() or stripe.Subscription.cancel() as appropriate before wiping credits.

## Tier 2 — Tests (fix for 3 Playwright tests to pass)

FIX-07: POST /api/content/draft endpoint missing [S]

- Used by Test 3 beforeAll to create a post without going through full generation.
- Fix: add a minimal draft endpoint in content.py — accepts {content, platform}, stores as status="draft", returns {post_id}. No agent pipeline, no credit deduction. Test-env only is fine; guard with ENVIRONMENT != "production" if preferred.

FIX-08: POST /api/content/publish-now endpoint missing [M]

- Used by Test 3 publish test. Also a genuine wedge feature ("publish-now" is in the wedge spec).
- Fix: add endpoint in content.py that: (a) validates post ownership, (b) calls publisher agent synchronously (or submits Celery task and polls with timeout), (c) on success updates post status to "published" and returns {published_url}.
- Use a mock LinkedIn client when ENVIRONMENT == "test" or LINKEDIN_MOCK == "true".

## Tier 3 — Content integrity (fix before user invites, Day 8)

FIX-09: Pipeline failure modes return mock content wrapped in success=True [L — split into sub-fixes]

- Files: scout.py, writer.py, qc.py, persona_refinement.py, vector_store.py
- Problem: any LLM/API failure returns canned mock content; credits already deducted; caller sees success.
- Fix (split):
  FIX-09a: scout.py — on missing Perplexity key, raise explicit error rather than returning mock research. [XS]
  FIX-09b: writer.py — on LLM failure, raise rather than return \_mock_writer. Caller handles retry. [XS]  
  FIX-09c: qc.py — fix vision call to attach image correctly; make slop_pass fail-closed not fail-open. [S]
  FIX-09d: vector_store.py — on embedding failure, fail the operation rather than upsert sha256 mock vector. [XS]
  FIX-09e: persona_refinement.py — surface is_mock to the caller; caller must reject mock and return error to user. [XS]

## Deferred (do not touch)

- Celery credit-skip for image/video/voice routes: these are flagged off. Not a wedge concern.
- Any file outside the wedge audit scope.
