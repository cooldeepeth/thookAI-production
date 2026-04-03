# Test Infrastructure Architecture

**Domain:** FastAPI + Motor + React — Production Hardening Testing Sprint (v2.1)
**Researched:** 2026-04-01
**Overall confidence:** HIGH

---

## Recommended Architecture

The test infrastructure is organized around four pillars: **layer separation** (unit vs. integration vs. E2E), **isolation contracts** (what each layer is allowed to touch), **speed hierarchy** (fast layers run first, slow layers gate last), and **CI parallelism** (split by domain group across matrix jobs).

### Test Layer Model

```
Layer 1: Unit (pure logic, no I/O)
  - No network, no real DB, no external process
  - Motor mocked via AsyncMock or mongomock-motor
  - Target: ~420 tests (60% of 700)
  - Speed: <1ms per test
  - Scope: services/, agents/ pure functions, middleware logic

Layer 2: Route Integration (FastAPI app, mocked DB)
  - FastAPI via httpx.AsyncClient + ASGITransport — no live server
  - Motor mocked via patch("database.db") or mongomock-motor fixture
  - External APIs mocked via respx or unittest.mock.patch
  - Target: ~210 tests (30%)
  - Speed: 5-50ms per test
  - Scope: routes/, auth flows, billing webhook handlers, n8n bridge

Layer 3: E2E / Smoke (real services, CI-only)
  - Real MongoDB (mongo:7.0 service container in CI)
  - Real Redis (redis:7-alpine service container)
  - FastAPI app running in-process via httpx.AsyncClient
  - Stripe still mocked (no real money)
  - Playwright frontend tests (optional separate job)
  - Target: ~70 tests (10%)
  - Speed: 100ms-5s per test
  - Scope: critical user journeys only
```

---

## Directory Structure

```
backend/
  tests/
    conftest.py                      # Root fixtures: async_client, mongo_db, seeded_user, make_jwt
    factories.py                     # Domain object builders (no assertions, no DB calls)
    markers.py                       # Custom mark registration

    billing/
      conftest.py                    # Stripe fixtures: stripe_env, mock_webhook_valid/invalid
      test_credits_unit.py           # Pure credit math — no DB, no HTTP
      test_stripe_webhooks.py        # Webhook parsing + signature verification
      test_stripe_checkout.py        # Checkout session creation per plan type
      test_subscription_lifecycle.py # Create -> update -> cancel -> downgrade
      test_billing_routes.py         # HTTP-level auth gates + response codes
      test_payment_edge_cases.py     # Idempotency, duplicate events, missing Price IDs

    security/
      conftest.py                    # JWT helpers, OWASP payload catalog
      test_jwt_lifecycle.py          # Issue, verify, expire, tamper, alg confusion
      test_oauth_flows.py            # Google OAuth, platform OAuth token refresh
      test_rate_limiting.py          # Sliding window, Redis fallback, per-IP vs per-user
      test_input_validation.py       # XSS payloads, SQL injection strings, oversized bodies
      test_auth_routes.py            # Register, login, logout, password reset flow
      test_owasp_top10.py            # CSRF tokens, path traversal, auth bypass probes

    pipeline/
      conftest.py                    # LLM mock fixtures, persona fixtures
      test_commander.py              # Job spec building, intent parsing
      test_thinker.py                # UOM injection, fatigue shield injection
      test_writer.py                 # Vector store retrieval, style injection
      test_qc.py                     # Quality gate routing, rewrite threshold
      test_orchestrator.py           # LangGraph compile, fallback on ImportError
      test_learning.py               # Embedding upsert on approval, skip on rejection
      test_anti_repetition.py        # Pattern fatigue de-dup logic

    media/
      conftest.py                    # Mock fal.ai, Luma, HeyGen, ElevenLabs responses
      test_media_orchestrator.py     # 8-format routing, provider selection logic
      test_remotion_assembly.py      # Composition payload construction
      test_voice_clone.py            # ElevenLabs clone flow, async blocking guard
      test_video_pipeline.py         # HeyGen avatar, Runway, Kling routing

    v2_features/
      conftest.py                    # n8n, LightRAG, Obsidian, Strategist mock fixtures
      test_n8n_bridge.py             # HMAC verification, callback routing
      test_lightrag_service.py       # Per-user isolation, health check, insert/query
      test_strategist.py             # Nightly schedule, one-click approve, cadence
      test_obsidian_integration.py   # Vault sync, Scout enrichment signal
      test_strategy_dashboard.py     # SSE feed, recommendation state machine

    e2e/
      conftest.py                    # real_db fixture (session-scoped), live app fixture
      test_signup_to_content.py      # Full journey: register -> onboard -> generate
      test_billing_checkout.py       # Checkout session end-to-end (Stripe test mode mocked)
      test_publish_pipeline.py       # Schedule -> n8n trigger mock -> status update
      test_agency_workspace.py       # Invite -> accept -> generate as member

frontend/
  e2e/
    playwright.config.ts
    fixtures/
      auth.ts                        # Auto-login fixture
      api.ts                         # Backend API seeding helper
    tests/
      auth.spec.ts
      onboarding.spec.ts
      content_studio.spec.ts
      billing.spec.ts
      strategy_dashboard.spec.ts
```

---

## Component Boundaries

| Component | Responsibility | Communicates With |
|-----------|---------------|-------------------|
| `conftest.py` (root) | Shared fixtures: `async_client`, `mongo_db`, `seeded_user`, `make_jwt` | All test files |
| `conftest.py` (per-suite) | Suite-specific fixtures: `stripe_user`, `mock_checkout_session` | Tests in that suite only |
| `factories.py` | Builder functions for all domain objects (users, jobs, personas, workspaces) | Fixtures only — no assertions |
| `mocks/external.py` | Reusable respx route definitions for Anthropic, Stripe, Pinecone, n8n, LightRAG | Integration test conftest files |
| `markers.py` | Custom pytest marks: `@billing`, `@security`, `@pipeline`, `@e2e`, `@slow` | pytest.ini + CI filter args |
| `.github/workflows/ci.yml` | Splits test execution: billing-security, pipeline-media, v2-features, e2e | GitHub Actions matrix |

---

## Fixture Patterns

### Root `conftest.py`

```python
# backend/tests/conftest.py

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient, ASGITransport
from mongomock_motor import AsyncMongoMockClient


@pytest.fixture(scope="function")
def event_loop():
    """Function-scoped loop prevents loop-reuse bugs across tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def mongo_db():
    """In-memory Motor-compatible DB. Isolated per test, zero network."""
    client = AsyncMongoMockClient()
    db = client["thookai_test"]
    yield db
    await client.drop_database("thookai_test")


@pytest.fixture
async def async_client(mongo_db):
    """
    FastAPI app with database.db replaced by in-memory mock.
    Use for all route integration tests.
    """
    with patch("database.db", mongo_db):
        from server import app
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            yield client


@pytest.fixture
def make_jwt():
    """Factory: make_jwt(user_id, email, expired=False) -> token string."""
    from datetime import datetime, timezone, timedelta
    from jose import jwt

    def _make(user_id: str, email: str, expired: bool = False) -> str:
        from config import settings
        secret = settings.security.jwt_secret_key or "thook-dev-secret"
        delta = timedelta(days=-1 if expired else 7)
        exp = datetime.now(timezone.utc) + delta
        return jwt.encode(
            {"sub": user_id, "email": email, "exp": exp},
            secret,
            algorithm="HS256",
        )

    return _make


@pytest.fixture
async def seeded_user(mongo_db, make_jwt):
    """Insert a minimal user into mongo_db. Returns (user_dict, jwt_token)."""
    import uuid
    from auth_utils import hash_password

    user_id = f"user_{uuid.uuid4().hex[:8]}"
    email = f"{user_id}@test.com"
    user = {
        "user_id": user_id,
        "email": email,
        "hashed_password": hash_password("TestPass123!"),
        "subscription_tier": "starter",
        "credits": 200,
        "credit_allowance": 0,
        "onboarding_completed": False,
    }
    await mongo_db.users.insert_one(user)
    token = make_jwt(user_id, email)
    return user, token
```

### Billing Suite `conftest.py`

```python
# backend/tests/billing/conftest.py

import pytest
import stripe
from unittest.mock import MagicMock, patch


@pytest.fixture
def stripe_env(monkeypatch):
    """Inject all Stripe env vars so is_stripe_configured() returns True."""
    vars = {
        "STRIPE_SECRET_KEY": "sk_test_fake",
        "STRIPE_WEBHOOK_SECRET": "whsec_test_fake",
        "STRIPE_PRICE_PRO_MONTHLY": "price_pro_monthly_test",
        "STRIPE_PRICE_STUDIO_MONTHLY": "price_studio_monthly_test",
        "STRIPE_PRICE_AGENCY_MONTHLY": "price_agency_monthly_test",
        "STRIPE_PRICE_CREDITS_100": "price_cred_100_test",
        "STRIPE_PRICE_CREDITS_500": "price_cred_500_test",
        "STRIPE_PRICE_CREDITS_1000": "price_cred_1000_test",
    }
    for k, v in vars.items():
        monkeypatch.setenv(k, v)


@pytest.fixture
def mock_stripe_webhook_valid():
    """Bypass signature verification — return True unconditionally."""
    with patch("stripe.WebhookSignature.verify_header", return_value=True):
        yield


@pytest.fixture
def mock_stripe_webhook_invalid():
    """Force verify_header to raise SignatureVerificationError."""
    with patch("stripe.WebhookSignature.verify_header") as m:
        m.side_effect = stripe.error.SignatureVerificationError(
            "Invalid signature", "test-header"
        )
        yield


@pytest.fixture
def mock_checkout_session():
    """Mock stripe.checkout.Session.create."""
    session = MagicMock()
    session.id = "cs_test_mock_001"
    session.url = "https://checkout.stripe.com/test/cs_test_mock_001"
    with patch("stripe.checkout.Session.create", return_value=session):
        yield session
```

### `factories.py`

```python
# backend/tests/factories.py

import uuid
from datetime import datetime, timezone


def make_user(user_id: str = None, **kwargs) -> dict:
    uid = user_id or f"user_{uuid.uuid4().hex[:8]}"
    return {
        "user_id": uid,
        "email": f"{uid}@test.com",
        "subscription_tier": "starter",
        "credits": 200,
        "credit_allowance": 0,
        "onboarding_completed": False,
        "created_at": datetime.now(timezone.utc),
        **kwargs,
    }


def make_persona(user_id: str, **kwargs) -> dict:
    return {
        "user_id": user_id,
        "card": {"name": "Test Creator", "niche": "tech", "tone": "professional"},
        "voice_fingerprint": {"style": "direct", "avg_sentence_length": 15},
        "content_identity": {"platforms": ["linkedin"], "formats": ["post"]},
        "performance_intelligence": {},
        "learning_signals": {},
        "uom": {"primary_metric": "engagement"},
        **kwargs,
    }


def make_content_job(user_id: str, status: str = "reviewing", **kwargs) -> dict:
    return {
        "job_id": f"job_{uuid.uuid4().hex[:8]}",
        "user_id": user_id,
        "platform": "linkedin",
        "content_type": "post",
        "raw_input": "Test content request",
        "status": status,
        "draft": "This is a test draft",
        "final_content": None,
        "was_edited": False,
        "created_at": datetime.now(timezone.utc),
        **kwargs,
    }


def make_workspace(owner_id: str, **kwargs) -> dict:
    return {
        "workspace_id": f"ws_{uuid.uuid4().hex[:8]}",
        "owner_id": owner_id,
        "name": "Test Agency",
        "settings": {},
        "created_at": datetime.now(timezone.utc),
        **kwargs,
    }
```

---

## Patterns to Follow

### Pattern 1: `patch("database.db")` Must Wrap App Import

All backend code does `from database import db` at module scope. The patch must be active before `server.app` is referenced for the first time in the test process. The shared `async_client` fixture handles this correctly — always use it rather than constructing `TestClient(app)` inline.

```python
# Correct: patch wraps the import
with patch("database.db", mongo_db):
    from server import app   # sees patched db at bind time
    async with AsyncClient(transport=ASGITransport(app=app), ...) as client:
        ...
```

### Pattern 2: AsyncMock for Every Awaited Motor Call

Motor methods return coroutines. `MagicMock` is not awaitable and raises `TypeError` at test time.

```python
mock_db = MagicMock()
mock_db.users.find_one = AsyncMock(return_value=user_dict)
mock_db.users.find_one_and_update = AsyncMock(return_value=updated_user)
mock_db.users.insert_one = AsyncMock(return_value=MagicMock(inserted_id="fake_id"))

# Cursors (find returns an iterable, to_list is awaited):
mock_cursor = MagicMock()
mock_cursor.to_list = AsyncMock(return_value=[job1, job2])
mock_db.content_jobs.find.return_value = mock_cursor
```

For tests heavy on DB interactions, prefer `mongomock-motor` — it implements the full cursor protocol correctly without manual `to_list` wiring.

### Pattern 3: Dependency Override for Auth in Route Tests

For testing route behavior when auth is irrelevant to the assertion:

```python
from auth_utils import get_current_user

async def test_get_dashboard(async_client, seeded_user):
    user, token = seeded_user
    # Use real JWT — auth path is part of what we test
    response = await async_client.get(
        "/api/dashboard",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
```

Use `app.dependency_overrides[get_current_user] = lambda: user` only when the test intentionally bypasses auth to focus on business logic. Never use it in auth-suite tests — those tests exist to verify the auth path.

### Pattern 4: respx for External HTTP Mocking

Use for n8n callbacks, LightRAG HTTP calls, Perplexity Scout, Anthropic API. Transport-layer interception means the real httpx client runs, giving accurate coverage of request-building logic.

```python
import respx
import httpx

@pytest.mark.asyncio
@respx.mock
async def test_scout_enrichment():
    respx.post("https://api.perplexity.ai/chat/completions").mock(
        return_value=httpx.Response(
            200,
            json={"choices": [{"message": {"content": "AI trends research result"}}]}
        )
    )
    result = await run_scout({"topic": "AI trends"}, context={})
    assert "research_summary" in result
```

### Pattern 5: Stripe Webhook Signature Bypass

```python
import json, uuid
from unittest.mock import patch

def _make_stripe_event(event_type: str, data: dict) -> dict:
    return {
        "id": f"evt_test_{uuid.uuid4().hex[:8]}",
        "type": event_type,
        "data": {"object": data},
    }

# In test (uses billing/conftest.py fixture):
async def test_checkout_completed(async_client, mock_stripe_webhook_valid):
    payload = _make_stripe_event("checkout.session.completed", {
        "id": "cs_test_123",
        "metadata": {"user_id": "user_abc", "type": "credits", "credits": "100"},
        "payment_status": "paid",
    })
    with patch("stripe.Webhook.construct_event", return_value=payload):
        response = await async_client.post(
            "/api/billing/webhook",
            content=json.dumps(payload).encode(),
            headers={"Stripe-Signature": "t=1,v1=fake"},
        )
    assert response.status_code == 200
```

### Pattern 6: freezegun for Time-Sensitive Logic

Credit refresh windows, JWT expiry at boundary, scheduled post timing, 24h/7d analytics polling:

```python
from freezegun import freeze_time

@freeze_time("2026-04-01 12:00:00")
async def test_jwt_expiry_boundary():
    from tests.factories import make_user
    token = make_jwt_expiring_in(seconds=1)  # expires at 12:00:01
    with freeze_time("2026-04-01 12:00:02"):  # 1 second past expiry
        result = await verify_token(token)
    assert result is None  # expired
```

Set `real_asyncio=False` (the default) for most cases. Use `real_asyncio=True` only when `asyncio.sleep` durations in the code under test must tick in real wall-clock time.

### Pattern 7: Worker-Isolated DB for pytest-xdist Parallel Runs

```python
# conftest.py addition for xdist
import os

@pytest.fixture(scope="session")
def db_name():
    worker = os.environ.get("PYTEST_XDIST_WORKER", "gw0")
    return f"thookai_test_{worker}"

@pytest.fixture
async def mongo_db(db_name):
    client = AsyncMongoMockClient()
    db = client[db_name]
    yield db
    await client.drop_database(db_name)
```

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Session-Scoped Async Client with Per-Test DB Writes

Sharing one `async_client` across the entire session while tests write different data creates hidden ordering dependencies. Test A's inserted user bleeds into Test B.

Use function-scoped fixtures (default). Only scope to `module` when setup cost is proven >200ms per test and the module is explicitly designed for shared state.

### Anti-Pattern 2: `MagicMock()` for Awaited Motor Methods

`mock_db.users.find_one = MagicMock(return_value=user)` is not awaitable. Every call to `await mock_db.users.find_one(...)` raises `TypeError: object MagicMock can't be used in 'await' expression`.

Always use `AsyncMock(return_value=user)` for Motor methods called with `await`.

### Anti-Pattern 3: Importing `app` at Module Level in Test Files

```python
# WRONG — app is bound before patch() runs
from server import app

async def test_something():
    with patch("database.db", mock_db):  # too late, db already bound
        ...
```

Import `app` inside fixtures or test functions, inside the `patch("database.db")` context. The shared `async_client` fixture does this correctly.

### Anti-Pattern 4: Multiple Behaviors in One Test Function

A 100-line test that registers a user, onboards, generates content, pays, and asserts billing provides zero diagnostic signal when it fails. CI wastes 5s on an opaque failure.

One test = one behavior. Compose test state via fixtures, share setup cost via `conftest.py`.

### Anti-Pattern 5: `collect_ignore` as Permanent Organization

The current `collect_ignore` list (8 files) represents accumulated debt — files that hit live servers or lack proper structure. These files need migration to proper suites, not indefinite exclusion.

### Anti-Pattern 6: Mocking `os.environ` Instead of `config.settings`

`config.py` reads env vars at import time via Python dataclasses. Setting `os.environ["STRIPE_SECRET_KEY"] = "sk_test_fake"` after import has no effect on `settings.stripe.secret_key`.

Use `monkeypatch.setattr(settings.stripe, "secret_key", "sk_test_fake")` or the `stripe_env` fixture pattern that sets env vars before the config module is first imported.

---

## CI Pipeline Architecture

### Job Structure

```
CI Pipeline
|
+-- lint (fast gate, parallel with nothing)
|     flake8 backend (F-codes only)
|     eslint frontend
|
+-- test-matrix (3 parallel jobs, needs lint)
|     |
|     +-- billing-security
|     |     Tests: tests/billing/ tests/security/
|     |     Services: mongo:7.0, redis:7-alpine
|     |     Coverage threshold: 95% (billing is highest risk)
|     |     Artifact: coverage-billing-security.xml
|     |
|     +-- pipeline-media
|     |     Tests: tests/pipeline/ tests/media/
|     |     Services: mongo:7.0
|     |     Coverage threshold: 85%
|     |     Artifact: coverage-pipeline-media.xml
|     |
|     +-- v2-features
|           Tests: tests/v2_features/
|           Services: mongo:7.0, redis:7-alpine
|           Coverage threshold: 80%
|           Artifact: coverage-v2-features.xml
|
+-- coverage-merge (needs test-matrix)
|     Download all 3 coverage XML artifacts
|     coverage combine + report --fail-under=85 (global gate)
|     Upload HTML report artifact
|
+-- frontend-build (parallel with test-matrix)
|     npm ci + npm run build
|
+-- e2e (needs test-matrix + frontend-build, push to dev/main only)
      Docker Compose: backend + frontend + mongo + redis
      pytest tests/e2e/ against live stack
      Playwright frontend tests
      Stripe calls mocked, n8n calls mocked via respx
```

### GitHub Actions Workflow (key job)

```yaml
test-matrix:
  name: Tests (${{ matrix.suite }})
  needs: lint
  runs-on: ubuntu-latest
  strategy:
    fail-fast: false
    matrix:
      include:
        - suite: billing-security
          test_paths: "tests/billing tests/security"
          cov_fail: 95
        - suite: pipeline-media
          test_paths: "tests/pipeline tests/media"
          cov_fail: 85
        - suite: v2-features
          test_paths: "tests/v2_features"
          cov_fail: 80
  services:
    mongo:
      image: mongo:7.0
      ports: ["27017:27017"]
      options: >-
        --health-cmd "mongosh --eval 'db.runCommand({ ping: 1 })'"
        --health-interval 10s --health-timeout 5s --health-retries 5
    redis:
      image: redis:7-alpine
      ports: ["6379:6379"]
      options: >-
        --health-cmd "redis-cli ping"
        --health-interval 10s --health-timeout 5s --health-retries 5
  steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-python@v5
      with:
        python-version: "3.11"
        cache: pip
        cache-dependency-path: backend/requirements.txt
    - run: pip install -r backend/requirements.txt
    - name: Run tests with coverage
      env:
        MONGO_URL: mongodb://localhost:27017
        DB_NAME: thookai_test
        REDIS_URL: redis://localhost:6379/0
        JWT_SECRET_KEY: ci-test-secret-key
        FERNET_KEY: 7X2PqyChA8TwDuzvdaeX_0Yh0SbmvZzxrjDXDwjCRCI=
        ENVIRONMENT: test
      run: |
        cd backend
        python -m pytest ${{ matrix.test_paths }} \
          -v --tb=short \
          --cov=. --cov-branch \
          --cov-report=xml:coverage-${{ matrix.suite }}.xml \
          --cov-fail-under=${{ matrix.cov_fail }} \
          -x
    - uses: actions/upload-artifact@v4
      if: always()
      with:
        name: coverage-${{ matrix.suite }}
        path: backend/coverage-${{ matrix.suite }}.xml
```

---

## Coverage Configuration

Add to `backend/pyproject.toml` (create if absent):

```toml
[tool.coverage.run]
source = ["."]
branch = true
omit = [
  "tests/*",
  "scripts/*",
  "db_indexes.py",
  "*/__pycache__/*",
]

[tool.coverage.report]
fail_under = 85
show_missing = true
exclude_lines = [
  "pragma: no cover",
  "if TYPE_CHECKING:",
  "raise NotImplementedError",
  "if __name__ == .__main__.:",
]
```

**Per-suite thresholds** are enforced at CI job level via `--cov-fail-under=N`. Coverage.py does not support per-module minimums natively — the matrix job split achieves domain-level enforcement (billing at 95%, others at 80-85%) without custom tooling.

---

## `pytest.ini` Updates

```ini
[pytest]
asyncio_mode = auto
testpaths = tests
markers =
    billing: Billing and payment tests
    security: Auth, JWT, OWASP tests
    pipeline: Content generation pipeline tests
    media: Media orchestration tests
    v2: v2.0 feature tests (n8n, LightRAG, Strategist, Obsidian)
    e2e: End-to-end tests requiring live services
    slow: Tests that take >1s
filterwarnings =
    ignore::DeprecationWarning:langgraph
    ignore::DeprecationWarning:mongomock
```

---

## Required New Dependencies

Add to `backend/requirements.txt`:

```
mongomock-motor>=0.0.36
respx>=0.21.0
freezegun>=1.5.0
pytest-cov>=6.0.0
pytest-xdist>=3.6.0
```

Add to `frontend/package.json` devDependencies:

```json
"@playwright/test": "^1.44.0"
```

---

## Migration Plan for Existing Tests

### Step 1 — Reorganize Without Breaking

Create the new directory structure. Move existing `test_*.py` files into correct subdirectories by domain (no renames, moves only). Verify `pytest` still exits 0 after move.

### Step 2 — Standardize Fixtures Across Moved Tests

Replace inline `patch("database.db")` per-test with the shared `async_client` fixture. Replace inline user-creation dicts with `seeded_user` fixture and `factories.py`. Delete or migrate the 8 `collect_ignore` files.

### Step 3 — Add 700 New Tests

Write against established fixture patterns. Every new test file starts with a docstring covering what requirements it addresses. Each test covers one behavior.

---

## Scalability Considerations

| Concern | At 319 tests (current) | At 700 tests (target) | At 1500+ tests (future) |
|---------|------------------------|----------------------|-------------------------|
| Run time (single process) | ~45s | ~90-120s | ~5 min |
| Run time (3 parallel CI jobs) | ~18s | ~35-45s | ~100s |
| DB isolation strategy | `patch("database.db")` per test | Same + mongomock-motor for cursor-heavy cases | Same |
| CI job count | 1 test job | 3 matrix jobs | 5 matrix jobs + nightly full suite |
| Coverage merge | Single XML | 3 XMLs combined in post-job | Same |
| E2E run frequency | Every push | Push to dev/main only | Nightly only |

---

## Key Architecture Decisions

| Decision | Rationale | Confidence |
|----------|-----------|------------|
| `mongomock-motor` for unit/integration | Zero network, full Motor API. Avoids manual `AsyncMock` cursor wiring. | MEDIUM — "best effort mock", may miss `$lookup` or aggregation edge cases. Use real Mongo for E2E. |
| `respx` for external HTTP | Transport-layer interception — real httpx client runs. Better coverage accuracy than `patch("httpx.AsyncClient")`. | HIGH |
| Function-scoped fixtures by default | 700 tests must run in any order and in parallel. Shared state across tests is the primary source of flaky tests. | HIGH |
| Matrix CI jobs by domain | Billing gets independent 95% threshold. Failure in billing does not suppress pipeline test reporting. | HIGH |
| `patch("database.db")` pattern (keep) | Already established in 57 existing test files. Do not migrate to full DI — too large a refactor for a testing sprint. | HIGH |
| freezegun for time | Covers JWT expiry, credit refresh windows, scheduled post 24h/7d polling. Standard, well-understood. | HIGH |
| E2E as separate CI job | 700 unit/integration tests must complete in <3 min for fast PR feedback. E2E runs on push to dev/main only. | HIGH |
| No pytest-django-style rollbacks | Motor is async, no single-connection ACID rollback available. Function-scoped mongomock-motor achieves equivalent isolation. | HIGH |

---

## Sources

- [FastAPI Async Testing — Official Docs](https://fastapi.tiangolo.com/advanced/async-tests/) (HIGH — official, current)
- [mongomock-motor 0.0.36 — PyPI](https://pypi.org/project/mongomock-motor/) (HIGH — actively maintained, released May 2025)
- [respx — PyPI](https://pypi.org/project/respx/) (HIGH — standard httpx mock library)
- [pytest-xdist Documentation](https://pytest-xdist.readthedocs.io/) (HIGH — official docs)
- [pytest-split with GitHub Actions — Jerry Codes blog](https://blog.jerrycodes.com/pytest-split-and-github-actions/) (MEDIUM — community, patterns verified against official docs)
- [freezegun — GitHub](https://github.com/spulec/freezegun) (HIGH — standard datetime mocking library)
- [Coverage.py Configuration Reference](https://coverage.readthedocs.io/en/latest/config.html) (HIGH — official docs)
- [Simon Willison — Mocking Stripe Signatures in pytest](https://til.simonwillison.net/pytest/pytest-stripe-signature) (MEDIUM — matches Stripe SDK source)
- [Stripe Automated Testing Docs](https://docs.stripe.com/automated-testing) (HIGH — official)
- [Playwright CI Setup](https://playwright.dev/docs/ci-intro) (HIGH — official Playwright docs)
