# Technology Stack — Testing Tools

**Project:** ThookAI v2.1 — Production Hardening (50x Testing Sprint)
**Researched:** 2026-04-01
**Confidence:** HIGH (all versions verified against PyPI, npm, and official documentation)

---

## Context: Scope of This Research

This file covers only the **new testing tooling** additions required for the v2.1 milestone. The full production stack (FastAPI, Motor, React, Redis, n8n, LightRAG, Stripe, Remotion, etc.) is documented in previous research and is NOT re-researched here.

**Current state of testing tooling:**
- Backend: `pytest>=8.0.0`, `pytest-asyncio>=0.23.0`, `httpx==0.28.1` — in `requirements.txt`
- `pytest.ini` contains only `asyncio_mode = auto` — no coverage config
- No `.coveragerc` or `pyproject.toml` coverage section
- No `pytest-cov` installed
- No `pytest-mock` installed — tests use `unittest.mock` directly
- No fixture data factories (`faker`, `factory_boy`)
- No load testing tool
- No mock for external HTTP calls (`respx` or `pytest-httpx`)
- Frontend: Zero test files, no test framework configured, no `@testing-library/react`
- No Playwright (E2E) installed anywhere

**Target after this milestone:** 1,050+ total tests, 85%+ line coverage, 95%+ billing coverage, zero P0 failures.

---

## Recommended Stack

### Backend Test Infrastructure

#### 1. Coverage Measurement: pytest-cov + coverage.py

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| `pytest-cov` | `>=7.1.0` | Coverage measurement, CI gate, HTML/XML/term reports | Latest stable (released 2026-03-21). Integrates directly with pytest via `--cov` flag. Supports `--cov-fail-under` for CI gate at 85%. Branch coverage via `--cov-branch`. The only standard choice — no meaningful alternative. |
| `coverage` | pulled by pytest-cov | Underlying coverage engine | Installed automatically as a dependency. Do NOT pin separately. |

**Configuration note:** FastAPI's async routes have a known coverage undercounting issue with `asyncio` concurrency. Set `concurrency = greenlet,thread` in `.coveragerc` to prevent false negatives on async handler lines. This is the documented workaround confirmed in the coveragepy issue tracker.

**Required `.coveragerc`** (create at `backend/.coveragerc`):

```ini
[run]
source = .
branch = true
concurrency = greenlet,thread
omit =
    tests/*
    conftest.py
    */__pycache__/*
    */migrations/*
    db_indexes.py

[report]
fail_under = 85
precision = 2
exclude_lines =
    pragma: no cover
    def __repr__
    raise NotImplementedError
    if TYPE_CHECKING:
    @abstractmethod
    if __name__ == .__main__.:

[html]
directory = htmlcov

[xml]
output = coverage.xml
```

**Billing-specific threshold:** The billing files (`services/credits.py`, `services/stripe_service.py`, `routes/billing.py`) need 95%+ coverage enforced separately. Implement this as a second pytest run scoped to those files:

```bash
pytest tests/test_stripe_billing.py tests/test_credits_billing.py \
  --cov=services/credits --cov=services/stripe_service --cov=routes/billing \
  --cov-fail-under=95 --cov-report=term-missing
```

---

#### 2. Upgrade pytest-asyncio: Pin to 1.3.0

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| `pytest-asyncio` | `>=1.3.0` | Async test support | The existing spec (`>=0.23.0`) allows resolving to 1.3.0 (released 2025-11-10) which requires Python 3.10+. ThookAI uses Python 3.11.11 — compatible. Version 1.3.0 stabilized `asyncio_mode = auto` and `asyncio_default_fixture_loop_scope`. Upgrade the pin in `requirements.txt` to `pytest-asyncio>=1.3.0` to prevent accidental downgrade. |

**`pytest.ini` update needed** — the current `asyncio_mode = auto` is correct but needs `asyncio_default_fixture_loop_scope = function` added to suppress the new deprecation warning in 1.3.0:

```ini
[pytest]
asyncio_mode = auto
asyncio_default_fixture_loop_scope = function
```

---

#### 3. Mocking: pytest-mock

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| `pytest-mock` | `>=3.15.1` | `mocker` fixture wrapping `unittest.mock` | Released 2025-09-16. Provides automatic cleanup of mocks after each test (critical for test isolation), pytest-style assertion introspection on mock calls, and `mocker.spy()` for wrapping real functions. The existing tests use `unittest.mock` directly via `patch()` context managers — `pytest-mock` is compatible and additive. Add new tests using `mocker`; no rewrite of existing tests needed. |

**Why not just continue with `unittest.mock` directly:** No automatic cleanup — patches left active across tests cause false positives. This is a real risk at 700+ test scale. `pytest-mock` eliminates this class of flakiness entirely.

---

#### 4. Fake Data Generation: Faker

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| `Faker` | `>=40.12.0` | Realistic test data generation (emails, names, UUIDs, text, dates) | Released 2026-03-30. Pure Python, no infrastructure. Provides a pytest fixture (`faker`) via its built-in plugin. Eliminates the hundreds of `"test@test.com"`, `"test_user_123"` strings scattered across existing tests. Critical for billing tests where realistic email formats, credit card data, and Stripe webhook payloads are needed. |

**Do NOT use factory_boy** for this codebase. `factory_boy` is designed around ORM model classes (SQLAlchemy, Django). ThookAI uses raw MongoDB dicts with no ORM — factory_boy provides no benefit and adds mapping boilerplate. Use `Faker` to generate field values directly in test helper functions (as the existing `make_user()` pattern already does).

**Pattern to follow** (already established in `test_stripe_billing.py`):

```python
from faker import Faker
fake = Faker()

def make_user(**kwargs) -> dict:
    defaults = {
        "user_id": f"user_{fake.uuid4()[:8]}",
        "email": fake.email(),
        "subscription_tier": "starter",
        "credits": 100,
    }
    defaults.update(kwargs)
    return defaults
```

---

#### 5. Async MongoDB Mocking: mongomock-motor

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| `mongomock-motor` | `>=0.0.36` | In-memory async Motor client for unit tests that need real query semantics | Released 2025-05-16. Wraps `mongomock` (sync) with the Motor async interface. Eliminates the need to start a real MongoDB instance for unit tests. Use for tests that need `find_one`, `insert_one`, `update_one` query logic but do NOT need to test indexes or Atlas-specific features. |

**When to use mongomock-motor vs `AsyncMock`:**

| Scenario | Use |
|----------|-----|
| Testing query logic (filters, projections, sorts) | `mongomock-motor` — real query semantics |
| Testing that a function calls `db.collection.find_one()` at all | `AsyncMock` — simpler, faster |
| Testing MongoDB aggregation pipelines | Real MongoDB (CI services block already present in `.github/workflows/ci.yml`) |
| Testing race conditions / atomic updates | Real MongoDB only |

**Integration pattern:**

```python
from mongomock_motor import AsyncMongoMockClient

@pytest.fixture
def mock_db():
    client = AsyncMongoMockClient()
    return client["thookai_test"]
```

**Limitation:** Does not support `$vectorSearch` (Atlas operator), `$search` (Atlas Search), or complex `explain()` plans. For tests involving Pinecone or vector operations, continue using `AsyncMock`.

---

#### 6. External HTTP Call Mocking: respx

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| `respx` | `>=0.22.0` | Mock outbound `httpx` calls (Anthropic, Stripe API, Perplexity, n8n webhooks, LightRAG sidecar, Obsidian client) | Released 2024-12-19. Async-native httpx mocker — the only correct choice when the code under test uses `httpx.AsyncClient`. The alternative (`pytest-httpx`) is an equally valid choice but `respx` has a simpler API for route-based mocking. |

**Why not `unittest.mock.patch` on httpx:** Patching at the `httpx` level is fragile and context-dependent. `respx` intercepts at the transport layer, which is both cleaner and immune to import-path issues.

**Example for mocking the Anthropic API:**

```python
import respx, httpx

@respx.mock
async def test_writer_calls_anthropic(respx_mock):
    respx_mock.post("https://api.anthropic.com/v1/messages").mock(
        return_value=httpx.Response(200, json={"content": [{"text": "Generated content"}]})
    )
    result = await run_writer(job_spec, persona)
    assert result["draft"] is not None
```

---

#### 7. Load Testing: Locust

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| `locust` | `>=2.43.4` | Load testing the FastAPI API under concurrent user load | Released 2026-04-01. Pure Python, gevent-based, runs headless or with a web UI. The project context calls for load testing as part of the 105 frontend/integration tests. Locust is the standard choice for Python-native load testing — no separate service, no YAML DSL, tests are plain Python. |

**Do NOT use k6:** k6 requires JavaScript and a separate binary installation. Locust integrates into the Python test environment without friction.

**Usage pattern** (headless CI mode):

```bash
locust -f tests/locustfile.py \
  --host http://localhost:8000 \
  --users 50 --spawn-rate 5 \
  --run-time 60s --headless \
  --html tests/reports/load-report.html
```

**Place** `backend/tests/locustfile.py` separately from pytest-collected test files (prefixed `test_`) to avoid pytest attempting to collect it.

---

#### 8. Stripe Webhook Testing: stripe-mock (Docker)

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| `stripe/stripe-mock` (Docker image) | latest | Local Stripe API mock for webhook and checkout session tests | Runs as a Docker service at `localhost:12111`. Responds identically to Stripe's API. Eliminates test-mode API key dependency and Stripe rate limits. Already used in the ecosystem — the existing `test_stripe_e2e.py` references live Stripe behavior that should be mocked. |

**For unit tests:** Do NOT use stripe-mock. Instead, mock `stripe.Webhook.construct_event()` and `stripe.PaymentIntent.create()` via `unittest.mock.patch` or `mocker.patch`. This is faster and isolates the Python logic from the HTTP boundary.

**For integration tests only:** Use stripe-mock running as a Docker service in CI. Add to `.github/workflows/ci.yml`:

```yaml
services:
  stripe-mock:
    image: stripe/stripe-mock:latest
    ports:
      - "12111:12111"
```

Then in tests, set `stripe.api_base = "http://localhost:12111"`.

---

### Frontend Test Infrastructure

#### 9. Component Testing: @testing-library/react + Jest (CRA built-in)

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| `@testing-library/react` | `>=16.x` | Render React components and query the DOM | Bundled with CRA (`react-scripts 5.0.1` includes RTL). Zero configuration needed — CRA's Jest runner picks up `*.test.js` files automatically. |
| `@testing-library/user-event` | `>=14.x` | Simulate realistic user interactions (click, type, tab) | NOT bundled with CRA — must install explicitly. v14 is the current major version. Supersedes v13's `fireEvent` patterns with event dispatch that matches browser behavior. |
| `@testing-library/jest-dom` | `>=6.x` | Custom Jest matchers (`toBeInTheDocument`, `toHaveValue`, etc.) | NOT bundled. Requires one import in `src/setupTests.js`: `import '@testing-library/jest-dom'`. CRA generates this file — just add the import. |
| `msw` (Mock Service Worker) | `>=2.7.x` | Intercept API calls from frontend tests | Mocks `axios` calls at the network level (Service Worker in browser, Node interceptor in Jest). Eliminates `jest.mock('./api')` per-file mocking. Use for testing pages that make backend calls. |

**Installation:**

```bash
cd frontend
npm install --save-dev \
  @testing-library/user-event \
  @testing-library/jest-dom \
  msw
```

**Do NOT install Jest separately.** CRA's `react-scripts` ships Jest 29 internally. Installing Jest as a dev dependency causes version conflicts with `react-scripts`'s internal Jest. The CRACO config does not need changes — CRA's Jest runner works out of the box.

**`src/setupTests.js`** — add one line (file already exists in CRA):

```javascript
import '@testing-library/jest-dom';
```

**Test file location:** Place test files adjacent to components as `ComponentName.test.js` or in a `__tests__/` folder within `src/`. CRA's Jest runner discovers both patterns.

---

#### 10. E2E Testing: Playwright

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| `@playwright/test` | `>=1.50.x` (latest stable ~1.50.1) | Full browser E2E testing (auth flows, content generation, billing) | The current industry standard for E2E testing in 2026. Superior to Cypress for: SSE/WebSocket testing (needed for notification system), multi-tab scenarios, network condition simulation, and headless Chrome on Linux CI without Xvfb. Microsoft-maintained, highly active. |

**Install location:** Install Playwright at the **repo root** (not inside `frontend/`). This allows E2E tests to target both the running frontend dev server and the FastAPI backend.

```bash
cd /path/to/thookAI-production
npm init -y  # if no root package.json
npm install --save-dev @playwright/test
npx playwright install chromium  # chromium only — sufficient for CI
```

**Do NOT install Firefox/WebKit browsers in CI.** Chromium alone covers ThookAI's user base (Chrome + Edge). Adding WebKit (Safari) adds 500MB+ to CI runner. Add WebKit locally if cross-browser coverage is a future requirement.

**`playwright.config.js`** at repo root:

```javascript
const { defineConfig } = require('@playwright/test');

module.exports = defineConfig({
  testDir: './e2e',
  timeout: 30 * 1000,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: process.env.CI ? 'github' : 'list',

  use: {
    baseURL: 'http://localhost:3000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },

  webServer: [
    {
      command: 'cd backend && uvicorn server:app --port 8000',
      url: 'http://localhost:8000/health',
      reuseExistingServer: !process.env.CI,
      timeout: 60 * 1000,
    },
    {
      command: 'cd frontend && npm start',
      url: 'http://localhost:3000',
      reuseExistingServer: !process.env.CI,
      timeout: 120 * 1000,
    },
  ],
});
```

**Test directory:** Create `e2e/` at the repo root (sibling to `backend/` and `frontend/`). Playwright tests live there, separate from both the backend pytest suite and the frontend Jest suite.

**Naming convention:** `e2e/auth.spec.js`, `e2e/billing.spec.js`, `e2e/content-pipeline.spec.js` etc.

---

## Installation Commands

### Backend additions (add to `backend/requirements.txt`)

```bash
# Coverage
pytest-cov>=7.1.0

# Mocking improvements
pytest-mock>=3.15.1
respx>=0.22.0
mongomock-motor>=0.0.36

# Test data
Faker>=40.12.0

# Load testing (separate from main test suite)
locust>=2.43.4
```

**Full install:**

```bash
cd backend
pip install pytest-cov>=7.1.0 pytest-mock>=3.15.1 respx>=0.22.0 mongomock-motor>=0.0.36 "Faker>=40.12.0" "locust>=2.43.4"
```

**Also update `pytest-asyncio` in requirements.txt:**

```
pytest-asyncio>=1.3.0
```

### Frontend additions

```bash
cd frontend
npm install --save-dev \
  @testing-library/user-event \
  @testing-library/jest-dom \
  msw
```

### E2E (Playwright) — repo root

```bash
cd /path/to/thookAI-production
npm install --save-dev @playwright/test
npx playwright install chromium
```

---

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Coverage | `pytest-cov 7.1.0` | `coverage` CLI directly | pytest-cov integrates with pytest's exit code; bare `coverage` requires separate run command and doesn't gate on fail_under naturally |
| HTTP mocking (backend) | `respx` | `pytest-httpx` | Functionally equivalent; `respx` has a cleaner route-based API and better async support documentation. Either is acceptable — `respx` chosen for consistency. |
| MongoDB mocking | `mongomock-motor` | Full `AsyncMock` everywhere | `AsyncMock` cannot test query filter logic; `mongomock-motor` validates that `{"user_id": x, "status": "active"}` filters correctly. Both needed for different test layers. |
| Frontend unit tests | Jest + RTL (CRA built-in) | Vitest + RTL | Vitest requires ejecting from CRA or moving to Vite. ThookAI uses CRA + CRACO — ejecting now is high risk for a testing sprint. Jest is already configured and working. |
| E2E framework | Playwright | Cypress | Playwright is superior for SSE testing (required for the notification system), native multi-tab, and is now the more actively developed option in 2026. Cypress has architectural limitations with streaming responses. |
| Load testing | Locust | k6 | k6 requires a separate Go binary and JavaScript test scripts; Locust is pure Python, integrates with existing test environment, no new toolchain. |
| Test data | `Faker` | `factory_boy` | `factory_boy` is designed for ORM model instances (SQLAlchemy, Django). ThookAI uses raw MongoDB dicts — `factory_boy` provides no benefit and adds ORM mapping boilerplate. |
| Stripe testing | `stripe-mock` Docker | `vcrpy` (cassette recording) | VCR cassettes become stale as Stripe's API evolves; `stripe-mock` always reflects the current Stripe API contract. |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| Ejecting CRA (`npm run eject`) | Irreversible. Breaks CRACO. Makes all future upgrades manual. The testing sprint does not require it. | Keep CRA + CRACO; Jest works fine without ejecting |
| `jest-environment-jsdom` explicitly | CRA already configures jsdom as the test environment. Adding it explicitly causes duplicate config warnings. | Nothing — CRA handles it |
| `Vitest` | Requires moving to Vite build. CRA is the build system. Migrating build systems during a testing sprint is out of scope and high risk. | Jest (CRA built-in) for unit/integration; Playwright for E2E |
| `Selenium` / `WebDriver` | Legacy technology. Fragile, slow, no SSE support. | Playwright |
| `responses` library (Python) | Mocks `requests` library only. ThookAI uses `httpx` for all async HTTP. Incompatible. | `respx` for async httpx mocking |
| `pytest-django` / `pytest-sqlalchemy` | ThookAI uses MongoDB/Motor, not Django or SQLAlchemy. These fixtures are irrelevant. | `mongomock-motor` for MongoDB mocking |
| Pinning `coverage` separately | `pytest-cov` pulls the correct `coverage` version. Manual pinning causes resolution conflicts. | Let `pytest-cov` manage `coverage` as its dependency |
| `nox` or `tox` | Over-engineering for a single-environment codebase. `pytest` directly is sufficient. | Plain `pytest` with `--cov` flags |
| `locust` in the `tests/` directory as `test_locust.py` | pytest will attempt to collect and run `locust` scenarios as regular pytest tests. | Name it `locustfile.py` and keep it in `tests/` but excluded from `pytest.ini`'s `testpaths` or via `collect_ignore` in `conftest.py` |

---

## Configuration Files to Create

### `backend/.coveragerc`

Already specified in the coverage section above. Key settings:
- `branch = true` — required for 85% threshold to be meaningful
- `concurrency = greenlet,thread` — prevents async FastAPI line undercounting
- `fail_under = 85` — gates CI
- `omit = tests/*, conftest.py` — excludes test files from coverage calculation (they're not product code)

### `backend/pytest.ini` (update existing)

```ini
[pytest]
asyncio_mode = auto
asyncio_default_fixture_loop_scope = function
testpaths = tests
```

### `frontend/src/setupTests.js` (update existing — add one line)

```javascript
import '@testing-library/jest-dom';
```

### `playwright.config.js` (create at repo root)

Already provided in the Playwright section above.

### `.github/workflows/ci.yml` (additions to existing)

Add to the `backend-test` job:
1. `stripe-mock` Docker service (for Stripe integration tests)
2. Change test command to include `--cov` flags
3. Add a `playwright-e2e` job after `frontend-build`
4. Add an `upload-coverage` job that uploads `coverage.xml` to Codecov (optional but recommended)

**Updated `backend-test` run command:**

```yaml
- name: Run tests with coverage
  run: |
    cd backend
    python -m pytest \
      --cov=. \
      --cov-branch \
      --cov-report=term-missing \
      --cov-report=xml \
      --cov-fail-under=85 \
      -v --tb=short
```

**New `playwright-e2e` job:**

```yaml
playwright-e2e:
  name: Playwright E2E
  runs-on: ubuntu-latest
  needs: [backend-test, frontend-build]
  steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-node@v4
      with:
        node-version: "18"
    - name: Install Playwright
      run: npm ci && npx playwright install chromium --with-deps
    - name: Install backend deps
      run: pip install -r backend/requirements.txt
    - name: Run E2E tests
      env:
        MONGO_URL: mongodb://localhost:27017
        # ... other env vars
      run: npx playwright test
    - name: Upload Playwright report
      if: always()
      uses: actions/upload-artifact@v4
      with:
        name: playwright-report
        path: playwright-report/
```

---

## Version Compatibility Matrix

| Package | Version | Python/Node | Compatible With ThookAI |
|---------|---------|-------------|-------------------------|
| `pytest-cov` | `>=7.1.0` | Python 3.9+ | Python 3.11.11 — YES |
| `pytest-asyncio` | `>=1.3.0` | Python 3.10+ | Python 3.11.11 — YES |
| `pytest-mock` | `>=3.15.1` | Python 3.9+ | Python 3.11.11 — YES |
| `respx` | `>=0.22.0` | Python 3.8+ | Python 3.11.11 — YES |
| `mongomock-motor` | `>=0.0.36` | Python 3.8-3.13 | Python 3.11.11 — YES |
| `Faker` | `>=40.12.0` | Python 3.10+ | Python 3.11.11 — YES |
| `locust` | `>=2.43.4` | Python 3.9+ | Python 3.11.11 — YES |
| `@testing-library/user-event` | `>=14.x` | Node 18+ | Node 18 — YES |
| `@testing-library/jest-dom` | `>=6.x` | Node 18+ | Node 18 — YES |
| `msw` | `>=2.7.x` | Node 18+ | Node 18 — YES |
| `@playwright/test` | `>=1.50.x` | Node 20+ recommended | Node 18 — YES (Node 18 still supported) |

**Note on Playwright Node version:** The Playwright docs now recommend Node 20+. Node 18 is still supported but is in maintenance mode. The CI workflow already uses Node 18 — it works, but consider upgrading the CI Node version to 20 for the Playwright job only (add `node-version: "20"` to the playwright CI job specifically).

---

## Sources

- [pytest-cov 7.1.0 on PyPI](https://pypi.org/project/pytest-cov/) — Version, options, `--cov-fail-under` behavior (HIGH confidence)
- [pytest-cov configuration docs](https://pytest-cov.readthedocs.io/en/latest/config.html) — pyproject.toml and .coveragerc format (HIGH confidence)
- [coverage.py configuration reference](https://coverage.readthedocs.io/en/latest/config.html) — `concurrency = greenlet,thread` for async FastAPI (HIGH confidence)
- [coveragepy issue #1240](https://github.com/nedbat/coveragepy/issues/1240) — Async line undercounting confirmed, greenlet workaround (MEDIUM confidence)
- [pytest-asyncio 1.3.0 on PyPI](https://pypi.org/project/pytest-asyncio/) — Version, `asyncio_default_fixture_loop_scope` requirement (HIGH confidence)
- [pytest-mock 3.15.1 on PyPI](https://pypi.org/project/pytest-mock/) — Version, automatic cleanup benefit (HIGH confidence)
- [Faker 40.12.0 on PyPI](https://pypi.org/project/faker/) — Version, pytest fixture integration (HIGH confidence)
- [mongomock-motor 0.0.36 on PyPI](https://pypi.org/project/mongomock-motor/) — Version, limitations (HIGH confidence)
- [respx 0.22.0 on PyPI](https://pypi.org/project/respx/) — Version, async httpx mocking pattern (HIGH confidence)
- [Locust 2.43.4 on PyPI](https://pypi.org/project/locust/) — Version, headless mode flags (HIGH confidence)
- [Playwright installation docs](https://playwright.dev/docs/intro) — npm install, browser installation (HIGH confidence)
- [Playwright webServer docs](https://playwright.dev/docs/test-webserver) — `webServer` config for CRA (HIGH confidence)
- [Playwright CI docs](https://playwright.dev/docs/ci) — `workers: 1` in CI, no browser caching (HIGH confidence)
- [CRA running tests docs](https://create-react-app.dev/docs/running-tests/) — Jest built-in, setupTests.js, no eject needed (HIGH confidence)
- [React Testing Library docs](https://testing-library.com/docs/react-testing-library/intro/) — `@testing-library/react` bundled in CRA (HIGH confidence)
- [stripe/stripe-mock GitHub](https://github.com/stripe/stripe-mock) — Docker image, `api_base` override pattern (HIGH confidence)

---

*Stack research for: ThookAI v2.1 — Production Hardening (50x Testing Sprint)*
*Researched: 2026-04-01*
