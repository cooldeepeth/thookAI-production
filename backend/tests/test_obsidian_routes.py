"""Route-level tests for backend/routes/obsidian.py (Phase 15, Plan 03).

Covers OBS-05 path sandboxing and OBS-06 per-user config CRUD:
  TestSaveConfig    — POST /api/obsidian/config stores encrypted API key
  TestGetConfig     — GET /api/obsidian/config returns masked key
  TestDeleteConfig  — DELETE /api/obsidian/config removes config doc
  TestTestEndpoint  — POST /api/obsidian/test calls search_vault
  TestAuthRequired  — All endpoints enforce authentication (401 without token)

asyncio_mode=auto (pytest.ini) — no @pytest.mark.asyncio decorator needed.
"""

import base64
import hashlib
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from cryptography.fernet import Fernet
from httpx import AsyncClient, ASGITransport

from server import app
from auth_utils import get_current_user


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_TEST_USER = {"user_id": "obs_test_user", "email": "obs@example.com"}

# Generate a deterministic test Fernet key
_RAW_KEY = "test-fernet-key-for-obsidian-routes"
_KEY_BYTES = _RAW_KEY.encode()
if len(_KEY_BYTES) != 44:
    _KEY_BYTES = base64.urlsafe_b64encode(hashlib.sha256(_KEY_BYTES).digest())
_TEST_FERNET_KEY = _KEY_BYTES.decode()
_CIPHER = Fernet(_KEY_BYTES)


def _encrypt(plaintext: str) -> str:
    """Encrypt a plaintext string with the test key."""
    return _CIPHER.encrypt(plaintext.encode()).decode()


def _decrypt(ciphertext: str) -> str:
    """Decrypt a ciphertext string with the test key."""
    return _CIPHER.decrypt(ciphertext.encode()).decode()


# ---------------------------------------------------------------------------
# TestSaveConfig — POST /api/obsidian/config
# ---------------------------------------------------------------------------

class TestSaveConfig:
    """POST /api/obsidian/config saves Fernet-encrypted API key in db.users."""

    def setup_method(self):
        app.dependency_overrides[get_current_user] = lambda: _TEST_USER

    def teardown_method(self):
        app.dependency_overrides.pop(get_current_user, None)

    async def test_saves_config_and_returns_vault_path_display(self):
        """Valid body stores encrypted config and returns vault_path_display."""
        mock_db = MagicMock()
        mock_db.users.update_one = AsyncMock(return_value=MagicMock(modified_count=1))

        mock_security = MagicMock()
        mock_security.fernet_key = _TEST_FERNET_KEY

        mock_settings = MagicMock()
        mock_settings.security = mock_security

        with patch("routes.obsidian.db", mock_db), \
             patch("routes.obsidian.settings", mock_settings):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post(
                    "/api/obsidian/config",
                    json={
                        "base_url": "https://my-vault.example.com",
                        "api_key": "super-secret-api-key",
                        "vault_path": "research/notes",
                    },
                )

        assert resp.status_code == 200
        body = resp.json()
        assert body["configured"] is True
        assert body["enabled"] is True
        assert body["base_url"] == "https://my-vault.example.com"
        assert body["vault_path"] == "research/notes"
        assert "ThookAI will read files from: research/notes" in body["vault_path_display"]
        # API key must be masked, not plaintext
        assert body.get("api_key_masked", "") != "super-secret-api-key"
        assert "****" in body.get("api_key_masked", "")

    async def test_encrypts_api_key_before_storage(self):
        """The stored api_key_encrypted value is Fernet-encrypted (not plaintext)."""
        stored_doc = {}

        async def capture_update(filter_q, update_q, **kwargs):
            stored_doc.update(update_q.get("$set", {}))
            return MagicMock(modified_count=1)

        mock_db = MagicMock()
        mock_db.users.update_one = capture_update

        mock_security = MagicMock()
        mock_security.fernet_key = _TEST_FERNET_KEY
        mock_settings = MagicMock()
        mock_settings.security = mock_security

        with patch("routes.obsidian.db", mock_db), \
             patch("routes.obsidian.settings", mock_settings):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post(
                    "/api/obsidian/config",
                    json={
                        "base_url": "https://vault.example.com",
                        "api_key": "my-plain-key-1234",
                        "vault_path": "notes",
                    },
                )

        assert resp.status_code == 200
        obsidian_cfg = stored_doc.get("obsidian_config", {})
        encrypted_val = obsidian_cfg.get("api_key_encrypted", "")
        # Must not be plaintext
        assert encrypted_val != "my-plain-key-1234"
        # Must be decryptable
        decrypted = _decrypt(encrypted_val)
        assert decrypted == "my-plain-key-1234"

    async def test_path_traversal_in_vault_path_returns_400(self):
        """vault_path with '..' traversal is rejected with 400."""
        mock_db = MagicMock()
        mock_db.users.update_one = AsyncMock(return_value=MagicMock(modified_count=0))

        mock_security = MagicMock()
        mock_security.fernet_key = _TEST_FERNET_KEY
        mock_settings = MagicMock()
        mock_settings.security = mock_security

        with patch("routes.obsidian.db", mock_db), \
             patch("routes.obsidian.settings", mock_settings):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post(
                    "/api/obsidian/config",
                    json={
                        "base_url": "https://vault.example.com",
                        "api_key": "key",
                        "vault_path": "../../etc/passwd",
                    },
                )

        assert resp.status_code == 400
        assert "traversal" in resp.json().get("detail", "").lower() or \
               "path" in resp.json().get("detail", "").lower()

    async def test_absolute_path_returns_400(self):
        """vault_path starting with '/' is rejected with 400."""
        mock_security = MagicMock()
        mock_security.fernet_key = _TEST_FERNET_KEY
        mock_settings = MagicMock()
        mock_settings.security = mock_security

        with patch("routes.obsidian.settings", mock_settings):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post(
                    "/api/obsidian/config",
                    json={
                        "base_url": "https://vault.example.com",
                        "api_key": "key",
                        "vault_path": "/etc/passwd",
                    },
                )

        assert resp.status_code == 400

    async def test_empty_base_url_returns_422(self):
        """Empty base_url fails Pydantic validation with 422."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/obsidian/config",
                json={"base_url": "", "api_key": "k", "vault_path": "notes"},
            )
        assert resp.status_code == 422

    async def test_vault_path_display_with_empty_path(self):
        """Empty vault_path shows 'entire vault' in display string."""
        mock_db = MagicMock()
        mock_db.users.update_one = AsyncMock(return_value=MagicMock(modified_count=1))

        mock_security = MagicMock()
        mock_security.fernet_key = _TEST_FERNET_KEY
        mock_settings = MagicMock()
        mock_settings.security = mock_security

        with patch("routes.obsidian.db", mock_db), \
             patch("routes.obsidian.settings", mock_settings):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post(
                    "/api/obsidian/config",
                    json={
                        "base_url": "https://vault.example.com",
                        "api_key": "key",
                        "vault_path": "",
                    },
                )

        assert resp.status_code == 200
        body = resp.json()
        assert "entire vault" in body.get("vault_path_display", "").lower()


# ---------------------------------------------------------------------------
# TestGetConfig — GET /api/obsidian/config
# ---------------------------------------------------------------------------

class TestGetConfig:
    """GET /api/obsidian/config returns config with masked API key."""

    def setup_method(self):
        app.dependency_overrides[get_current_user] = lambda: _TEST_USER

    def teardown_method(self):
        app.dependency_overrides.pop(get_current_user, None)

    async def test_returns_configured_false_when_no_config(self):
        """Returns {"configured": false} when user has no obsidian_config."""
        mock_db = MagicMock()
        mock_db.users.find_one = AsyncMock(return_value={"user_id": "obs_test_user"})

        with patch("routes.obsidian.db", mock_db):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.get("/api/obsidian/config")

        assert resp.status_code == 200
        body = resp.json()
        assert body["configured"] is False

    async def test_returns_masked_api_key_when_config_exists(self):
        """Returns masked API key (****last4) not plaintext."""
        encrypted_key = _encrypt("myapikey1234")
        mock_db = MagicMock()
        mock_db.users.find_one = AsyncMock(return_value={
            "user_id": "obs_test_user",
            "obsidian_config": {
                "base_url": "https://vault.example.com",
                "api_key_encrypted": encrypted_key,
                "vault_path": "research",
                "enabled": True,
                "configured_at": datetime(2026, 3, 1, tzinfo=timezone.utc).isoformat(),
            }
        })

        mock_security = MagicMock()
        mock_security.fernet_key = _TEST_FERNET_KEY
        mock_settings = MagicMock()
        mock_settings.security = mock_security

        with patch("routes.obsidian.db", mock_db), \
             patch("routes.obsidian.settings", mock_settings):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.get("/api/obsidian/config")

        assert resp.status_code == 200
        body = resp.json()
        assert body["configured"] is True
        assert body["base_url"] == "https://vault.example.com"
        assert body["vault_path"] == "research"
        # Key must be masked
        assert "****" in body["api_key_masked"]
        # Must end with last 4 chars of "myapikey1234"
        assert body["api_key_masked"].endswith("1234")

    async def test_returns_vault_path_display(self):
        """Response includes vault_path_display field."""
        encrypted_key = _encrypt("testkey")
        mock_db = MagicMock()
        mock_db.users.find_one = AsyncMock(return_value={
            "obsidian_config": {
                "base_url": "https://vault.example.com",
                "api_key_encrypted": encrypted_key,
                "vault_path": "my/notes",
                "enabled": True,
            }
        })

        mock_security = MagicMock()
        mock_security.fernet_key = _TEST_FERNET_KEY
        mock_settings = MagicMock()
        mock_settings.security = mock_security

        with patch("routes.obsidian.db", mock_db), \
             patch("routes.obsidian.settings", mock_settings):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.get("/api/obsidian/config")

        assert resp.status_code == 200
        body = resp.json()
        assert "vault_path_display" in body
        assert "my/notes" in body["vault_path_display"]


# ---------------------------------------------------------------------------
# TestDeleteConfig — DELETE /api/obsidian/config
# ---------------------------------------------------------------------------

class TestDeleteConfig:
    """DELETE /api/obsidian/config removes obsidian_config from db.users."""

    def setup_method(self):
        app.dependency_overrides[get_current_user] = lambda: _TEST_USER

    def teardown_method(self):
        app.dependency_overrides.pop(get_current_user, None)

    async def test_removes_obsidian_config_and_returns_removed_true(self):
        """DELETE unsets obsidian_config and returns {"removed": true}."""
        mock_db = MagicMock()
        mock_db.users.update_one = AsyncMock(return_value=MagicMock(modified_count=1))

        with patch("routes.obsidian.db", mock_db):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.delete("/api/obsidian/config")

        assert resp.status_code == 200
        body = resp.json()
        assert body["removed"] is True

        # Verify $unset was called with obsidian_config key
        call_args = mock_db.users.update_one.call_args
        update_arg = call_args[0][1]
        assert "obsidian_config" in update_arg.get("$unset", {})

    async def test_filter_targets_correct_user(self):
        """DELETE update_one filter uses user_id from auth token."""
        mock_db = MagicMock()
        mock_db.users.update_one = AsyncMock(return_value=MagicMock(modified_count=1))

        with patch("routes.obsidian.db", mock_db):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                await client.delete("/api/obsidian/config")

        call_args = mock_db.users.update_one.call_args
        filter_arg = call_args[0][0]
        assert filter_arg.get("user_id") == "obs_test_user"


# ---------------------------------------------------------------------------
# TestTestEndpoint — POST /api/obsidian/test
# ---------------------------------------------------------------------------

class TestTestEndpoint:
    """POST /api/obsidian/test calls search_vault and returns connection status."""

    def setup_method(self):
        app.dependency_overrides[get_current_user] = lambda: _TEST_USER

    def teardown_method(self):
        app.dependency_overrides.pop(get_current_user, None)

    async def test_returns_connected_true_on_vault_success(self):
        """Returns {"connected": true} when search_vault returns results."""
        mock_search = AsyncMock(return_value={
            "findings": "Some vault note content",
            "vault_sources": [{"title": "notes/test.md", "snippet": "content"}],
            "sources_found": 1,
        })

        with patch("routes.obsidian.search_vault", mock_search):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post("/api/obsidian/test")

        assert resp.status_code == 200
        body = resp.json()
        assert body["connected"] is True
        assert body["vault_accessible"] is True
        assert body["notes_found"] == 1
        assert "error" not in body or body.get("error") is None

    async def test_returns_connected_false_on_vault_exception(self):
        """Returns {"connected": false, "error": str} when search_vault raises."""
        mock_search = AsyncMock(
            side_effect=Exception("Connection refused: https://vault.example.com")
        )

        with patch("routes.obsidian.search_vault", mock_search):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post("/api/obsidian/test")

        assert resp.status_code == 200
        body = resp.json()
        assert body["connected"] is False
        assert "error" in body
        assert body["error"] is not None

    async def test_search_vault_called_with_user_id(self):
        """search_vault is called with user_id from auth token."""
        mock_search = AsyncMock(return_value={
            "findings": "",
            "vault_sources": [],
            "sources_found": 0,
        })

        with patch("routes.obsidian.search_vault", mock_search):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                await client.post("/api/obsidian/test")

        mock_search.assert_called_once()
        call_kwargs = mock_search.call_args
        # user_id should be passed
        assert "user_id" in (call_kwargs.kwargs or {}) or \
               "obs_test_user" in str(call_kwargs)


# ---------------------------------------------------------------------------
# TestAuthRequired — 401 without token
# ---------------------------------------------------------------------------

class TestAuthRequired:
    """All Obsidian endpoints return 401 when no auth token provided."""

    def setup_method(self):
        # Ensure no dependency override so real auth runs
        app.dependency_overrides.pop(get_current_user, None)

    def teardown_method(self):
        app.dependency_overrides.pop(get_current_user, None)

    async def test_post_config_requires_auth(self):
        """POST /api/obsidian/config returns 401 without token."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/obsidian/config",
                json={"base_url": "https://v.example.com", "api_key": "k"},
            )
        assert resp.status_code == 401

    async def test_get_config_requires_auth(self):
        """GET /api/obsidian/config returns 401 without token."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/obsidian/config")
        assert resp.status_code == 401

    async def test_delete_config_requires_auth(self):
        """DELETE /api/obsidian/config returns 401 without token."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.delete("/api/obsidian/config")
        assert resp.status_code == 401

    async def test_post_test_requires_auth(self):
        """POST /api/obsidian/test returns 401 without token."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post("/api/obsidian/test")
        assert resp.status_code == 401
