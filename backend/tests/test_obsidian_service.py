"""Unit tests for backend/services/obsidian_service.py.

Covers:
- ObsidianConfig.is_configured() — OBS-03/04
- _validate_vault_path() — OBS-05 path traversal prevention
- search_vault() graceful fallback — OBS-04
- get_recent_notes() graceful fallback — OBS-04
- _resolve_config() per-user vs global fallback
- _decrypt_obsidian_api_key() Fernet decryption
- _get_user_obsidian_config() DB lookup
"""

import base64
import hashlib
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from cryptography.fernet import Fernet


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_fernet_key() -> str:
    """Generate a valid Fernet key for testing."""
    return Fernet.generate_key().decode()


def _encrypt_with_raw_key(plaintext: str, raw_key: str) -> str:
    """Encrypt using the same approach as _get_cipher() in platforms.py."""
    key = raw_key.encode() if isinstance(raw_key, str) else raw_key
    if len(key) != 44:
        key = base64.urlsafe_b64encode(hashlib.sha256(key).digest())
    cipher = Fernet(key)
    return cipher.encrypt(plaintext.encode()).decode()


# ---------------------------------------------------------------------------
# ObsidianConfig tests
# ---------------------------------------------------------------------------

class TestObsidianConfig:
    """Tests for ObsidianConfig dataclass in config.py."""

    def test_is_configured_returns_false_when_base_url_empty(self):
        """OBS-04: is_configured() is False when OBSIDIAN_BASE_URL is empty."""
        from config import ObsidianConfig
        cfg = ObsidianConfig(base_url='', api_key='some_key')
        assert cfg.is_configured() is False

    def test_is_configured_returns_false_when_base_url_is_default(self):
        """OBS-04: is_configured() is False when base_url is not set."""
        from config import ObsidianConfig
        cfg = ObsidianConfig(base_url='', api_key=None)
        assert cfg.is_configured() is False

    def test_is_configured_returns_true_when_base_url_set(self):
        """OBS-03: is_configured() is True when OBSIDIAN_BASE_URL is a valid URL."""
        from config import ObsidianConfig
        cfg = ObsidianConfig(base_url='https://my-vault.example.com', api_key='tok_123')
        assert cfg.is_configured() is True

    def test_is_configured_requires_http_prefix(self):
        """OBS-03: bare hostname without http prefix is not a valid configured URL."""
        from config import ObsidianConfig
        cfg = ObsidianConfig(base_url='localhost:27124', api_key='tok_123')
        assert cfg.is_configured() is False

    def test_settings_has_obsidian_field(self):
        """OBS-03: Settings container exposes settings.obsidian."""
        from config import settings
        assert hasattr(settings, 'obsidian')
        from config import ObsidianConfig
        assert isinstance(settings.obsidian, ObsidianConfig)


# ---------------------------------------------------------------------------
# _validate_vault_path tests (OBS-05)
# ---------------------------------------------------------------------------

class TestValidateVaultPath:
    """Tests for _validate_vault_path() — path traversal prevention (OBS-05)."""

    def test_clean_relative_path_passes(self):
        """A simple relative path like 'research/notes' should pass."""
        from services.obsidian_service import _validate_vault_path
        result = _validate_vault_path("research/notes")
        assert result == "research/notes"

    def test_dotdot_traversal_raises(self):
        """../../etc/passwd must raise ValueError with 'path traversal' in message."""
        from services.obsidian_service import _validate_vault_path
        with pytest.raises(ValueError, match="path traversal"):
            _validate_vault_path("../../etc/passwd")

    def test_absolute_unix_path_raises(self):
        """Absolute path starting with / must raise ValueError."""
        from services.obsidian_service import _validate_vault_path
        with pytest.raises(ValueError, match="path traversal|absolute"):
            _validate_vault_path("/etc/passwd")

    def test_embedded_dotdot_raises(self):
        """Embedded traversal like notes/../../../secrets must be blocked."""
        from services.obsidian_service import _validate_vault_path
        with pytest.raises(ValueError, match="path traversal"):
            _validate_vault_path("notes/../../../secrets")

    def test_empty_path_raises(self):
        """Empty path string must raise ValueError."""
        from services.obsidian_service import _validate_vault_path
        with pytest.raises(ValueError):
            _validate_vault_path("")

    def test_nested_clean_path_passes(self):
        """Nested clean path like 'Research/AI/notes.md' should pass."""
        from services.obsidian_service import _validate_vault_path
        result = _validate_vault_path("Research/AI/notes.md")
        assert result == "Research/AI/notes.md"

    def test_windows_backslash_or_drive_raises(self):
        """Path with colon (Windows drive letter) must be blocked."""
        from services.obsidian_service import _validate_vault_path
        with pytest.raises(ValueError, match="path traversal|absolute"):
            _validate_vault_path("C:\\Windows\\system32")


# ---------------------------------------------------------------------------
# is_configured() — module-level function
# ---------------------------------------------------------------------------

class TestIsConfigured:
    """Tests for the module-level is_configured() function."""

    def test_returns_false_when_no_global_config(self):
        """With no env vars set and no user_id, is_configured() returns False."""
        from services import obsidian_service
        with patch.object(obsidian_service, '_resolve_config', return_value=('', '', '')):
            result = obsidian_service.is_configured()
            assert result is False

    def test_returns_true_when_global_config_set(self):
        """With base_url configured, is_configured() returns True."""
        from services import obsidian_service
        with patch.object(
            obsidian_service, '_resolve_config',
            return_value=('https://vault.example.com', 'tok_123', 'Research')
        ):
            result = obsidian_service.is_configured()
            assert result is True


# ---------------------------------------------------------------------------
# _decrypt_obsidian_api_key() tests
# ---------------------------------------------------------------------------

class TestDecryptObsidianApiKey:
    """Tests for Fernet decryption of stored API keys."""

    def test_decrypts_correctly(self):
        """A Fernet-encrypted key is correctly decrypted."""
        raw_fernet_key = _make_fernet_key()
        plaintext = "secret-vault-api-key"
        encrypted = _encrypt_with_raw_key(plaintext, raw_fernet_key)

        from services import obsidian_service
        with patch('services.obsidian_service.settings') as mock_settings:
            mock_settings.security.fernet_key = raw_fernet_key
            result = obsidian_service._decrypt_obsidian_api_key(encrypted)
        assert result == plaintext

    def test_returns_empty_string_on_bad_key(self):
        """Decryption failure returns empty string (non-fatal)."""
        from services import obsidian_service
        with patch('services.obsidian_service.settings') as mock_settings:
            mock_settings.security.fernet_key = _make_fernet_key()
            result = obsidian_service._decrypt_obsidian_api_key("not_valid_ciphertext")
        assert result == ""

    def test_returns_empty_string_when_no_fernet_key(self):
        """If FERNET_KEY is not set, return empty string (non-fatal)."""
        from services import obsidian_service
        with patch('services.obsidian_service.settings') as mock_settings:
            mock_settings.security.fernet_key = None
            result = obsidian_service._decrypt_obsidian_api_key("anything")
        assert result == ""


# ---------------------------------------------------------------------------
# _get_user_obsidian_config() tests
# ---------------------------------------------------------------------------

class TestGetUserObsidianConfig:
    """Tests for per-user Obsidian config retrieval from MongoDB."""

    @pytest.mark.asyncio
    async def test_returns_none_when_user_has_no_obsidian_config(self):
        """User document without obsidian_config returns None."""
        from services import obsidian_service
        with patch('services.obsidian_service.db') as mock_db:
            mock_db.users.find_one = AsyncMock(
                return_value={"user_id": "user_1"}  # no obsidian_config
            )
            result = await obsidian_service._get_user_obsidian_config("user_1")
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_config_when_present_and_enabled(self):
        """User document with enabled obsidian_config returns the config dict."""
        from services import obsidian_service
        obsidian_cfg = {
            "base_url": "https://my-vault.ngrok.io",
            "api_key_encrypted": "enc_tok",
            "vault_path": "Research",
            "enabled": True,
        }
        with patch('services.obsidian_service.db') as mock_db:
            mock_db.users.find_one = AsyncMock(
                return_value={"user_id": "user_1", "obsidian_config": obsidian_cfg}
            )
            result = await obsidian_service._get_user_obsidian_config("user_1")
        assert result == obsidian_cfg

    @pytest.mark.asyncio
    async def test_returns_none_when_user_not_found(self):
        """Non-existent user returns None."""
        from services import obsidian_service
        with patch('services.obsidian_service.db') as mock_db:
            mock_db.users.find_one = AsyncMock(return_value=None)
            result = await obsidian_service._get_user_obsidian_config("nonexistent")
        assert result is None


# ---------------------------------------------------------------------------
# _resolve_config() tests
# ---------------------------------------------------------------------------

class TestResolveConfig:
    """Tests for _resolve_config() — per-user config takes precedence over global."""

    @pytest.mark.asyncio
    async def test_uses_per_user_config_when_enabled(self):
        """If user has an enabled obsidian_config, it takes precedence over global env."""
        from services import obsidian_service
        user_cfg = {
            "base_url": "https://user-vault.ngrok.io",
            "api_key_encrypted": "enc_tok",
            "vault_path": "Research",
            "enabled": True,
        }
        with patch.object(
            obsidian_service, '_get_user_obsidian_config', new_callable=AsyncMock,
            return_value=user_cfg
        ), patch.object(
            obsidian_service, '_decrypt_obsidian_api_key', return_value="decrypted_key"
        ):
            base_url, api_key, vault_path = await obsidian_service._resolve_config("user_1")
        assert base_url == "https://user-vault.ngrok.io"
        assert api_key == "decrypted_key"
        assert vault_path == "Research"

    @pytest.mark.asyncio
    async def test_falls_back_to_global_when_no_user_config(self):
        """When user has no obsidian_config, global settings are used."""
        from services import obsidian_service
        with patch.object(
            obsidian_service, '_get_user_obsidian_config', new_callable=AsyncMock,
            return_value=None
        ), patch('services.obsidian_service.settings') as mock_settings:
            mock_settings.obsidian.base_url = "https://global-vault.example.com"
            mock_settings.obsidian.api_key = "global_key"
            base_url, api_key, vault_path = await obsidian_service._resolve_config("user_1")
        assert base_url == "https://global-vault.example.com"
        assert api_key == "global_key"

    @pytest.mark.asyncio
    async def test_falls_back_to_global_when_user_config_disabled(self):
        """Disabled per-user config falls back to global."""
        from services import obsidian_service
        user_cfg = {
            "base_url": "https://user-vault.ngrok.io",
            "api_key_encrypted": "enc",
            "vault_path": "Notes",
            "enabled": False,  # disabled
        }
        with patch.object(
            obsidian_service, '_get_user_obsidian_config', new_callable=AsyncMock,
            return_value=user_cfg
        ), patch('services.obsidian_service.settings') as mock_settings:
            mock_settings.obsidian.base_url = "https://global.example.com"
            mock_settings.obsidian.api_key = "global_key"
            base_url, api_key, vault_path = await obsidian_service._resolve_config("user_1")
        assert base_url == "https://global.example.com"


# ---------------------------------------------------------------------------
# search_vault() tests (OBS-01 / OBS-04)
# ---------------------------------------------------------------------------

class TestSearchVault:
    """Tests for async search_vault() function."""

    @pytest.mark.asyncio
    async def test_returns_empty_when_not_configured(self):
        """OBS-04: search_vault returns empty result when Obsidian not configured."""
        from services import obsidian_service
        with patch.object(
            obsidian_service, '_resolve_config', new_callable=AsyncMock,
            return_value=('', '', '')
        ):
            result = await obsidian_service.search_vault("AI trends", user_id="user_1")
        assert result["sources_found"] == 0
        assert result["findings"] == ""
        assert result["vault_sources"] == []

    @pytest.mark.asyncio
    async def test_returns_findings_on_successful_response(self):
        """search_vault returns formatted findings from Obsidian REST API."""
        from services import obsidian_service

        mock_response_data = [
            {
                "filename": "Research/AI-trends.md",
                "matches": [{"match": {"content": "LLMs are transforming how..."}}]
            },
            {
                "filename": "Research/customer-stories.md",
                "matches": [{"match": {"content": "Customer discovered that..."}}]
            }
        ]

        mock_http_response = MagicMock()
        mock_http_response.status_code = 200
        mock_http_response.json.return_value = mock_response_data

        with patch.object(
            obsidian_service, '_resolve_config', new_callable=AsyncMock,
            return_value=('https://vault.example.com', 'tok_123', 'Research')
        ), patch('httpx.AsyncClient') as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.get = AsyncMock(return_value=mock_http_response)
            mock_client_cls.return_value = mock_client

            result = await obsidian_service.search_vault("AI trends", user_id="user_1")

        assert result["sources_found"] == 2
        assert "AI-trends.md" in result["findings"]
        assert len(result["vault_sources"]) == 2

    @pytest.mark.asyncio
    async def test_returns_empty_on_http_error(self):
        """OBS-04: search_vault returns empty result on any HTTP failure (non-fatal)."""
        import httpx as httpx_module
        from services import obsidian_service

        with patch.object(
            obsidian_service, '_resolve_config', new_callable=AsyncMock,
            return_value=('https://vault.example.com', 'tok_123', 'Research')
        ), patch('httpx.AsyncClient') as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.get = AsyncMock(
                side_effect=httpx_module.ConnectError("Connection refused")
            )
            mock_client_cls.return_value = mock_client

            result = await obsidian_service.search_vault("AI trends", user_id="user_1")

        assert result["sources_found"] == 0
        assert result["findings"] == ""

    @pytest.mark.asyncio
    async def test_filters_results_by_vault_path(self):
        """OBS-05: Results outside vault_path are filtered out."""
        from services import obsidian_service

        mock_response_data = [
            {
                "filename": "Research/notes.md",
                "matches": [{"match": {"content": "Good research note"}}]
            },
            {
                "filename": "Private/diary.md",  # Outside Research/
                "matches": [{"match": {"content": "Private diary entry"}}]
            }
        ]

        mock_http_response = MagicMock()
        mock_http_response.status_code = 200
        mock_http_response.json.return_value = mock_response_data

        with patch.object(
            obsidian_service, '_resolve_config', new_callable=AsyncMock,
            return_value=('https://vault.example.com', 'tok_123', 'Research')
        ), patch('httpx.AsyncClient') as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.get = AsyncMock(return_value=mock_http_response)
            mock_client_cls.return_value = mock_client

            result = await obsidian_service.search_vault("research notes", user_id="user_1")

        # Only Research/ file should appear
        assert result["sources_found"] == 1
        assert "Research/notes.md" in result["findings"]
        assert "Private/diary.md" not in result["findings"]


# ---------------------------------------------------------------------------
# get_recent_notes() tests (OBS-02 / OBS-04)
# ---------------------------------------------------------------------------

class TestGetRecentNotes:
    """Tests for async get_recent_notes() function."""

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_not_configured(self):
        """OBS-04: get_recent_notes returns [] when Obsidian not configured."""
        from services import obsidian_service
        with patch.object(
            obsidian_service, '_resolve_config', new_callable=AsyncMock,
            return_value=('', '', '')
        ):
            result = await obsidian_service.get_recent_notes(user_id="user_1")
        assert result == []

    @pytest.mark.asyncio
    async def test_returns_list_of_note_dicts_on_success(self):
        """get_recent_notes returns list of {title, path, modified} dicts."""
        from services import obsidian_service

        mock_vault_list = {
            "files": [
                "Research/AI-trends.md",
                "Research/customer-stories.md",
            ]
        }
        mock_list_response = MagicMock()
        mock_list_response.status_code = 200
        mock_list_response.json.return_value = mock_vault_list

        with patch.object(
            obsidian_service, '_resolve_config', new_callable=AsyncMock,
            return_value=('https://vault.example.com', 'tok_123', 'Research')
        ), patch('httpx.AsyncClient') as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.get = AsyncMock(return_value=mock_list_response)
            mock_client_cls.return_value = mock_client

            result = await obsidian_service.get_recent_notes(user_id="user_1")

        assert isinstance(result, list)
        # Each item should have title and path at minimum
        for item in result:
            assert "title" in item
            assert "path" in item

    @pytest.mark.asyncio
    async def test_returns_empty_list_on_http_error(self):
        """OBS-04: get_recent_notes returns [] on any HTTP failure (non-fatal)."""
        import httpx as httpx_module
        from services import obsidian_service

        with patch.object(
            obsidian_service, '_resolve_config', new_callable=AsyncMock,
            return_value=('https://vault.example.com', 'tok_123', 'Research')
        ), patch('httpx.AsyncClient') as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.get = AsyncMock(
                side_effect=httpx_module.ConnectError("Connection refused")
            )
            mock_client_cls.return_value = mock_client

            result = await obsidian_service.get_recent_notes(user_id="user_1")

        assert result == []
