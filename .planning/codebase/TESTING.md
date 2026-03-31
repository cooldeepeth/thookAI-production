# Testing Patterns

**Analysis Date:** 2026-03-31

## Test Framework

**Runner:**
- pytest (Python backend) version 8.0.0+
- Config: `backend/pytest.ini` with `asyncio_mode = auto`
- Frontend: No test runner configured (no test files found)

**Assertion Library:**
- pytest built-in assertions (`assert condition`)
- requests library for HTTP assertions in integration tests

**Run Commands:**
```bash
cd backend && pytest                 # Run all tests
cd backend && pytest -v              # Verbose output
cd backend && pytest -s               # Show print statements
cd backend && pytest backend/tests/   # Run specific directory
cd backend && pytest -k test_auth     # Run tests matching pattern
```

**No test coverage tool configured** — coverage.py not in requirements.txt

## Test File Organization

**Location:**
- Backend: Co-located in `backend/tests/` directory (separate from source)
- Frontend: No test files found

**Naming:**
- Backend: `test_*.py` or `*_test.py` pattern (both used)
  - Examples: `test_auth.py`, `test_onboarding_persona.py`, `auth_isolation_test.py`
- Frontend: No tests found

**Structure:**
```
backend/
  tests/
    test_auth.py                    # Auth endpoint tests
    test_onboarding_persona.py      # Onboarding & persona tests
    test_health_endpoint.py
    test_critical_fixes.py
    backend_test.py
    production_deployment_test.py
    # ... more test files
```

## Test Structure

**Suite Organization:**
```python
# backend/tests/test_auth.py
class TestHealthCheck:
    """Health and root endpoint tests"""
    
    def test_root_api(self):
        r = requests.get(f"{BASE_URL}/api/")
        assert r.status_code == 200
        data = r.json()
        assert data.get("status") == "running"

class TestRegister:
    """Registration endpoint tests"""
    
    def test_register_new_user(self):
        r = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD,
            "name": TEST_NAME
        })
        assert r.status_code == 200
        data = r.json()
        assert "token" in data
```

**Patterns:**
- Tests organized into classes by functionality (TestHealthCheck, TestRegister, TestLogin)
- Class methods follow naming: `test_xxx()` pattern
- Setup: Using pytest fixtures with `@pytest.fixture` decorator
- Teardown: Not explicitly used; tests assume stateless or rollback-safe operations
- Assertion: Plain `assert` statements with status codes and JSON assertions

## Mocking

**Framework:** No mocking framework explicitly configured (unittest.mock available via standard library)

**Patterns:**
- Backend tests use live HTTP requests via requests library (integration tests)
- No mocked database calls detected — tests hit real MongoDB
- No mocked LLM API calls detected — tests may hit real APIs or use placeholder responses

**What to Mock (current practice):**
- External APIs (Stripe, Anthropic, OpenAI, etc.) — currently not mocked in test files
- Database calls — currently not mocked; tests use real `db` connection

**What NOT to Mock (current practice):**
- HTTP layer — tests make real requests to live backend
- Authentication — tests use real JWT tokens from auth endpoints

## Fixtures and Factories

**Test Data:**
```python
# backend/tests/test_onboarding_persona.py
TEST_CREDENTIALS = {"email": "test@thook.ai", "password": "TestPass123!"}
FRESH_CREDENTIALS = {"email": "fresh@thook.ai", "password": "FreshPass123!"}

SAMPLE_ANSWERS = [
    {"question_id": 0, "answer": "I am a SaaS founder sharing lessons on product-market fit"},
    {"question_id": 1, "answer": "LinkedIn"},
    # ... more answers
]

@pytest.fixture(scope="module")
def test_token():
    r = requests.post(f"{BASE_URL}/api/auth/login", json=TEST_CREDENTIALS)
    assert r.status_code == 200
    return r.json()["token"]

def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}
```

**Location:**
- Fixtures defined at top of test files using `@pytest.fixture` decorator
- Scope: `module` (shared across all tests in file) or function-level (default)
- Constants defined at module level (all-caps names like TEST_EMAIL, SAMPLE_ANSWERS)

## Coverage

**Requirements:** None enforced — no coverage configuration found

**View Coverage:**
- No coverage tool configured; would need to add pytest-cov to requirements.txt
- To add: `pytest --cov=backend --cov-report=html` (after pip install pytest-cov)

## Test Types

**Unit Tests:**
- Scope: Test individual functions/methods in isolation
- Approach: Not practiced in current codebase (no mocking framework configured)
- Examples not found in test files

**Integration Tests:**
- Scope: Test full API endpoints with real backend + database
- Approach: Make HTTP requests to running backend server
- Location: All tests in `backend/tests/` are integration tests
- Example:
  ```python
  def test_register_new_user(self):
      r = requests.post(f"{BASE_URL}/api/auth/register", json={
          "email": TEST_EMAIL,
          "password": TEST_PASSWORD,
          "name": TEST_NAME
      })
      assert r.status_code == 200
      data = r.json()
      assert "token" in data
  ```

**E2E Tests:**
- Framework: Not formally used; some tests labeled as "e2e" but structured as integration tests
- Examples: `test_e2e_ship.py`, `production_deployment_test.py`
- Approach: Test full user workflows (register → onboard → create content)

**Async Tests:**
- Async support: Built-in via `pytest-asyncio`
- Config: `pytest.ini` has `asyncio_mode = auto`
- Tests can be async: `async def test_xxx()` — pytest-asyncio runs them automatically
- Examples not found in current test files (tests use requests library, not async)

## Common Patterns

**HTTP Testing:**
```python
# backend/tests/test_auth.py
import requests

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# GET request
r = requests.get(f"{BASE_URL}/api/")
assert r.status_code == 200
data = r.json()
assert data.get("status") == "running"

# POST request with JSON body
r = requests.post(f"{BASE_URL}/api/auth/register", json={
    "email": TEST_EMAIL,
    "password": TEST_PASSWORD,
    "name": TEST_NAME
})
assert r.status_code == 200
```

**Authentication Testing:**
```python
# Fixture provides token
@pytest.fixture(scope="module")
def test_token():
    r = requests.post(f"{BASE_URL}/api/auth/login", json=TEST_CREDENTIALS)
    return r.json()["token"]

# Pass token in Authorization header
def test_something(test_token):
    r = requests.get(
        f"{BASE_URL}/api/persona",
        headers={"Authorization": f"Bearer {test_token}"}
    )
    assert r.status_code == 200
```

**Status Code Assertions:**
```python
assert r.status_code == 200      # Success
assert r.status_code == 400      # Bad request
assert r.status_code == 401      # Unauthorized
assert r.status_code == 403      # Forbidden
assert r.status_code == 404      # Not found
```

**JSON Response Assertions:**
```python
data = r.json()
assert "token" in data
assert data["email"] == TEST_EMAIL
assert "hashed_password" not in data  # Sensitive field hidden
assert "_id" not in data              # MongoDB _id excluded
```

## Test Execution

**Before Running Tests:**
1. Backend must be running: `cd backend && uvicorn server:app --reload`
2. MongoDB must be accessible (configured via MONGO_URL env var)
3. `REACT_APP_BACKEND_URL` env var set (e.g., `http://localhost:8000`)

**Running Tests:**
```bash
# From backend directory
cd backend

# All tests
pytest

# With verbose output
pytest -v

# Single test class
pytest tests/test_auth.py::TestRegister

# Single test
pytest tests/test_auth.py::TestRegister::test_register_new_user

# Show print statements
pytest -s

# Stop on first failure
pytest -x
```

## Test Cleanup

**Database State:**
- Tests write to real MongoDB (no isolation)
- Some tests reuse email addresses with timestamps: `TEST_EMAIL = f"TEST_user_{TIMESTAMP}@thook.ai"`
- No explicit cleanup between tests — relies on unique identifiers (timestamps, UUIDs)

**Teardown:**
- No teardown fixtures found
- Tests should ideally clean up created resources but don't currently

## Frontend Testing

**Status:** No test runner or test files configured

**Recommendation:** If adding frontend tests:
- Use Jest (already available via create-react-app)
- Use React Testing Library for component tests
- Create test files co-located: `Component.test.jsx` next to `Component.jsx`

---

*Testing analysis: 2026-03-31*
