"""
Shared pytest fixtures and configuration for ThookAI backend tests.

Integration/E2E scripts (named *_test.py) are excluded from pytest collection
via collect_ignore — they require a running server and must be run directly.

Integration tests that hit a live server URL (test_auth, test_content_sprint3,
test_onboarding_persona) are automatically skipped when REACT_APP_BACKEND_URL
is not set, so `pytest` can always exit 0 in a local dev environment.
"""

import os
import pytest
from unittest.mock import AsyncMock, patch
from faker import Faker
from mongomock_motor import AsyncMongoMockClient
import respx as _respx

# ---------------------------------------------------------------------------
# Exclude live E2E integration scripts from pytest collection.
# These files hit live URLs or require a running server — they are NOT
# unit tests and will fail to collect cleanly when run via pytest.
# ---------------------------------------------------------------------------
collect_ignore = [
    "debug_series_test.py",
    "focused_series_test.py",
    "backend_test_sprint7.py",
    "backend_test_focused.py",
    "targeted_test.py",
    "auth_isolation_test.py",
    "backend_test.py",
    "production_deployment_test.py",
    "debug_public_persona.py",
]


# ---------------------------------------------------------------------------
# Auto-skip server-dependent integration tests when no server is configured.
# ---------------------------------------------------------------------------

_SERVER_URL = os.environ.get("REACT_APP_BACKEND_URL", "").strip()
_requires_server = pytest.mark.skipif(
    not _SERVER_URL,
    reason="Skipped: REACT_APP_BACKEND_URL not set — integration tests require a running server",
)


def pytest_collection_modifyitems(items):
    """Auto-apply the requires_server skip mark to test files that hit a live URL."""
    # Modules that use requests against a live BASE_URL — skip when no URL configured.
    server_dependent_modules = {
        "tests/test_auth.py",
        "tests/test_content_sprint3.py",
        "tests/test_onboarding_persona.py",
        "tests/test_fresh_public_persona.py",
    }
    for item in items:
        # Normalise path separator for cross-platform comparison.
        rel_path = "/".join(item.nodeid.split("::")[0].split("/")[-2:])
        if rel_path in server_dependent_modules:
            item.add_marker(_requires_server)


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_db():
    """Mock MongoDB database for unit tests."""
    with patch("database.db") as mock:
        yield mock


@pytest.fixture
def mock_settings():
    """Mock settings for unit tests."""
    with patch("config.settings") as mock:
        yield mock


# ---------------------------------------------------------------------------
# Standardized test infrastructure fixtures (Phase 17)
# ---------------------------------------------------------------------------

fake = Faker()


@pytest.fixture
def make_user():
    """Factory fixture for user documents. Call with kwargs to override defaults."""
    def _make(**kwargs) -> dict:
        defaults = {
            "user_id": f"user_{fake.uuid4()[:8]}",
            "email": fake.email(),
            "subscription_tier": "starter",
            "credits": 200,
            "credit_allowance": 0,
            "onboarding_completed": True,
        }
        defaults.update(kwargs)
        return defaults
    return _make


@pytest.fixture
def mongomock_db():
    """In-memory Motor DB with real query semantics. Function-scoped for isolation."""
    client = AsyncMongoMockClient()
    db = client["thookai_test"]
    yield db


@pytest.fixture
def mock_db_atomic(mongomock_db):
    """Patch database.db with mongomock for tests needing real $inc/$set semantics."""
    with patch("database.db", mongomock_db):
        yield mongomock_db


@pytest.fixture
def respx_mock():
    """respx transport-level mock for outbound httpx calls. Function-scoped."""
    with _respx.mock() as mock:
        yield mock


@pytest.fixture
def mock_current_user(make_user):
    """Pre-built mock user for auth dependency override."""
    return make_user(user_id="test_user_001", email="test@thookai.com")
