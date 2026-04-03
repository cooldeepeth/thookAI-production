"""Comprehensive LightRAG isolation and service tests (CORE-05).

Covers coverage gaps not addressed by the existing test files:
  - test_lightrag_service.py   (18 tests — basic CRUD + config)
  - test_lightrag_isolation.py (5 tests  — per-user insert/query contracts)
  - test_lightrag_integration.py (10 tests — routing contracts, entity types)

New coverage in this file:
  - TestHealthCheck: timeout + 500 status
  - TestInsertContent: payload construction, API key header, timeout/network errors
  - TestQueryKnowledgeGraph: custom modes, structured response, timeout/network errors
  - TestPerUserIsolation: sequential queries, user_id sanitization
  - TestEmbeddingConfig: combined model+dim validation, not-configured path
  - TestGracefulDegradation: all functions with unconfigured service, arbitrary exceptions

All tests are fully mocked — no real HTTP calls or LightRAG sidecar needed.
"""

import pytest
import httpx
from unittest.mock import patch, AsyncMock, MagicMock
import importlib


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _FakeLightRAGConfig:
    """Fake LightRAGConfig for tests — avoids MagicMock assert_* collision."""

    def __init__(
        self,
        is_configured_val=True,
        url="http://test-lightrag:9621",
        api_key=None,
        embedding_model="text-embedding-3-small",
        embedding_dim=1536,
    ):
        self._is_configured = is_configured_val
        self.url = url
        self.api_key = api_key
        self.embedding_model = embedding_model
        self.embedding_dim = embedding_dim

    def is_configured(self) -> bool:
        return self._is_configured

    def assert_embedding_config(self) -> None:
        assert self.embedding_model == "text-embedding-3-small", (
            f"LIGHTRAG_EMBEDDING_MODEL must be 'text-embedding-3-small', got: {self.embedding_model}"
        )
        assert self.embedding_dim == 1536, (
            f"LIGHTRAG_EMBEDDING_DIM must be 1536 for text-embedding-3-small, got: {self.embedding_dim}"
        )


def _make_cfg(
    is_configured=True,
    url="http://test-lightrag:9621",
    api_key=None,
    embedding_model="text-embedding-3-small",
    embedding_dim=1536,
) -> _FakeLightRAGConfig:
    return _FakeLightRAGConfig(
        is_configured_val=is_configured,
        url=url,
        api_key=api_key,
        embedding_model=embedding_model,
        embedding_dim=embedding_dim,
    )


def _make_mock_client(status_code=200, response_json=None, side_effect=None):
    """Build a reusable mock AsyncClient."""
    mock_response = MagicMock()
    mock_response.status_code = status_code
    mock_response.raise_for_status = MagicMock()
    if status_code >= 400:
        mock_response.raise_for_status.side_effect = Exception(f"HTTP {status_code}")
    mock_response.json.return_value = response_json or {}

    mock_client = AsyncMock()
    if side_effect is not None:
        mock_client.get.side_effect = side_effect
        mock_client.post.side_effect = side_effect
    else:
        mock_client.get.return_value = mock_response
        mock_client.post.return_value = mock_response
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    return mock_client


def _patch_svc(cfg, mock_client, api_key=None, url="http://test-lightrag:9621"):
    """Return the combined context manager patches for lightrag_service."""
    return [
        patch("services.lightrag_service.settings", new=MagicMock(lightrag=cfg)),
        patch("services.lightrag_service.LIGHTRAG_URL", url),
        patch("services.lightrag_service.LIGHTRAG_API_KEY", api_key),
        patch("httpx.AsyncClient", return_value=mock_client),
    ]


# ---------------------------------------------------------------------------
# TestHealthCheck
# ---------------------------------------------------------------------------


class TestHealthCheck:
    """Health check returns True on 200, False on 5xx, False on timeout."""

    @pytest.mark.asyncio
    async def test_health_check_returns_true_on_200(self):
        """Mock GET /health returning 200 -> returns True."""
        mock_client = _make_mock_client(status_code=200)
        cfg = _make_cfg()

        with (
            patch("services.lightrag_service.settings") as mock_settings,
            patch("services.lightrag_service.LIGHTRAG_URL", "http://test-lightrag:9621"),
            patch("httpx.AsyncClient", return_value=mock_client),
        ):
            mock_settings.lightrag = cfg
            import services.lightrag_service as svc
            result = await svc.health_check()

        assert result is True, f"Expected True for 200 response, got {result}"
        # The URL used is whatever LIGHTRAG_URL is patched to in the module
        assert mock_client.get.called, "health_check must call GET on the health endpoint"

    @pytest.mark.asyncio
    async def test_health_check_returns_false_on_500(self):
        """Mock GET /health returning 500 -> returns False (non-200 status)."""
        mock_response = MagicMock()
        mock_response.status_code = 500

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        cfg = _make_cfg()

        with (
            patch("services.lightrag_service.settings") as mock_settings,
            patch("services.lightrag_service.LIGHTRAG_URL", "http://test-lightrag:9621"),
            patch("httpx.AsyncClient", return_value=mock_client),
        ):
            mock_settings.lightrag = cfg
            import services.lightrag_service as svc
            importlib.reload(svc)
            result = await svc.health_check()

        assert result is False, f"Expected False for 500 response, got {result}"

    @pytest.mark.asyncio
    async def test_health_check_returns_false_on_timeout(self):
        """Mock GET /health raising httpx.TimeoutException -> returns False (graceful degradation)."""
        mock_client = _make_mock_client(side_effect=httpx.TimeoutException("Timeout"))
        cfg = _make_cfg()

        with (
            patch("services.lightrag_service.settings") as mock_settings,
            patch("services.lightrag_service.LIGHTRAG_URL", "http://test-lightrag:9621"),
            patch("httpx.AsyncClient", return_value=mock_client),
        ):
            mock_settings.lightrag = cfg
            import services.lightrag_service as svc
            importlib.reload(svc)
            result = await svc.health_check()

        assert result is False, f"Expected False on timeout, got {result}"


# ---------------------------------------------------------------------------
# TestInsertContent
# ---------------------------------------------------------------------------


class TestInsertContent:
    """Insert content builds correct payload and handles errors gracefully."""

    @pytest.mark.asyncio
    async def test_insert_builds_correct_payload(self):
        """Verify doc_id format, tagged_content structure, and metadata fields in POST body."""
        mock_client = _make_mock_client(status_code=200)
        cfg = _make_cfg()

        with (
            patch("services.lightrag_service.settings") as mock_settings,
            patch("services.lightrag_service.LIGHTRAG_URL", "http://test-lightrag:9621"),
            patch("services.lightrag_service.LIGHTRAG_API_KEY", None),
            patch("httpx.AsyncClient", return_value=mock_client),
        ):
            mock_settings.lightrag = cfg
            import services.lightrag_service as svc
            importlib.reload(svc)
            result = await svc.insert_content(
                user_id="user_build_test",
                content="Test content payload",
                metadata={
                    "job_id": "job_payload_001",
                    "platform": "linkedin",
                    "content_type": "post",
                    "was_edited": False,
                },
            )

        assert result is True
        call_kwargs = mock_client.post.call_args
        json_body = call_kwargs[1]["json"]

        # doc_id must follow {user_id}_{job_id} format
        assert json_body["doc_id"] == "user_build_test_job_payload_001", (
            f"doc_id must be 'user_build_test_job_payload_001', got: {json_body['doc_id']!r}"
        )
        # tagged_content must have all meta headers
        text = json_body["text"]
        assert "[CREATOR:user_build_test]" in text, f"Missing CREATOR tag in text: {text[:100]}"
        assert "[PLATFORM:linkedin]" in text, f"Missing PLATFORM tag in text: {text[:100]}"
        assert "[TYPE:post]" in text, f"Missing TYPE tag in text: {text[:100]}"
        assert "[EDITED:False]" in text, f"Missing EDITED tag in text: {text[:100]}"
        assert "Test content payload" in text, f"Missing actual content in text: {text[:100]}"

        # metadata dict must have all required fields
        meta = json_body["metadata"]
        assert meta["user_id"] == "user_build_test"
        assert meta["platform"] == "linkedin"
        assert meta["content_type"] == "post"
        assert meta["was_edited"] is False
        assert meta["job_id"] == "job_payload_001"

    @pytest.mark.asyncio
    async def test_insert_sends_api_key_header_when_configured(self):
        """When LIGHTRAG_API_KEY module variable is set, the X-API-Key header is present in the POST request."""
        mock_client = _make_mock_client(status_code=200)
        cfg = _make_cfg(api_key="test-api-key-abc")

        # Patch the module-level LIGHTRAG_API_KEY constant (not just settings.lightrag.api_key)
        # because insert_content uses: `if LIGHTRAG_API_KEY else {}`
        with (
            patch("services.lightrag_service.settings") as mock_settings,
            patch("services.lightrag_service.LIGHTRAG_URL", "http://test-lightrag:9621"),
            patch("services.lightrag_service.LIGHTRAG_API_KEY", "test-api-key-abc"),
            patch("httpx.AsyncClient", return_value=mock_client),
        ):
            mock_settings.lightrag = cfg
            import services.lightrag_service as svc
            await svc.insert_content(
                user_id="user_apikey",
                content="content",
                metadata={"job_id": "j1"},
            )

        call_kwargs = mock_client.post.call_args
        headers = call_kwargs[1].get("headers", {})
        assert "X-API-Key" in headers, (
            f"X-API-Key header must be present when api_key is configured. Headers: {headers}"
        )
        assert headers["X-API-Key"] == "test-api-key-abc"

    @pytest.mark.asyncio
    async def test_insert_omits_api_key_header_when_not_configured(self):
        """When api_key is None, the X-API-Key header must NOT be sent."""
        mock_client = _make_mock_client(status_code=200)
        cfg = _make_cfg(api_key=None)

        with (
            patch("services.lightrag_service.settings") as mock_settings,
            patch("services.lightrag_service.LIGHTRAG_URL", "http://test-lightrag:9621"),
            patch("services.lightrag_service.LIGHTRAG_API_KEY", None),
            patch("httpx.AsyncClient", return_value=mock_client),
        ):
            mock_settings.lightrag = cfg
            import services.lightrag_service as svc
            importlib.reload(svc)
            await svc.insert_content(
                user_id="user_no_key",
                content="content",
                metadata={"job_id": "j2"},
            )

        call_kwargs = mock_client.post.call_args
        headers = call_kwargs[1].get("headers", {})
        assert "X-API-Key" not in headers, (
            f"X-API-Key header must NOT be present when api_key is None. Headers: {headers}"
        )

    @pytest.mark.asyncio
    async def test_insert_returns_false_on_http_error(self):
        """When LightRAG returns 500, insert_content returns False (non-fatal)."""
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = Exception("HTTP 500")

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        cfg = _make_cfg()

        with (
            patch("services.lightrag_service.settings") as mock_settings,
            patch("services.lightrag_service.LIGHTRAG_URL", "http://test-lightrag:9621"),
            patch("services.lightrag_service.LIGHTRAG_API_KEY", None),
            patch("httpx.AsyncClient", return_value=mock_client),
        ):
            mock_settings.lightrag = cfg
            import services.lightrag_service as svc
            importlib.reload(svc)
            result = await svc.insert_content(
                user_id="user_500",
                content="content",
                metadata={"job_id": "j3"},
            )

        assert result is False, f"Expected False on HTTP error, got {result}"

    @pytest.mark.asyncio
    async def test_insert_returns_false_on_network_timeout(self):
        """When httpx raises TimeoutException, insert_content returns False (non-fatal)."""
        mock_client = _make_mock_client(side_effect=httpx.TimeoutException("Timeout"))
        cfg = _make_cfg()

        with (
            patch("services.lightrag_service.settings") as mock_settings,
            patch("services.lightrag_service.LIGHTRAG_URL", "http://test-lightrag:9621"),
            patch("services.lightrag_service.LIGHTRAG_API_KEY", None),
            patch("httpx.AsyncClient", return_value=mock_client),
        ):
            mock_settings.lightrag = cfg
            import services.lightrag_service as svc
            importlib.reload(svc)
            result = await svc.insert_content(
                user_id="user_timeout",
                content="content",
                metadata={"job_id": "j4"},
            )

        assert result is False, f"Expected False on timeout, got {result}"


# ---------------------------------------------------------------------------
# TestQueryKnowledgeGraph
# ---------------------------------------------------------------------------


class TestQueryKnowledgeGraph:
    """Query builds correct payload and handles all failure modes."""

    @pytest.mark.asyncio
    async def test_query_builds_natural_language_query_with_user_id(self):
        """The query string in the POST body contains the user_id and topic."""
        mock_client = _make_mock_client(status_code=200, response_json={"response": "context"})
        cfg = _make_cfg()

        with (
            patch("services.lightrag_service.settings") as mock_settings,
            patch("services.lightrag_service.LIGHTRAG_URL", "http://test-lightrag:9621"),
            patch("services.lightrag_service.LIGHTRAG_API_KEY", None),
            patch("httpx.AsyncClient", return_value=mock_client),
        ):
            mock_settings.lightrag = cfg
            import services.lightrag_service as svc
            importlib.reload(svc)
            await svc.query_knowledge_graph(user_id="user_nl_test", topic="AI fundraising")

        call_kwargs = mock_client.post.call_args
        json_body = call_kwargs[1]["json"]

        assert "user_nl_test" in json_body["query"], (
            f"user_id 'user_nl_test' must appear in query text. Got: {json_body['query'][:100]}"
        )
        assert "AI fundraising" in json_body["query"], (
            f"topic 'AI fundraising' must appear in query text. Got: {json_body['query'][:100]}"
        )

    @pytest.mark.asyncio
    async def test_query_uses_hybrid_mode_by_default(self):
        """When mode is not specified, param.mode must be 'hybrid'."""
        mock_client = _make_mock_client(status_code=200, response_json={"response": "ctx"})
        cfg = _make_cfg()

        with (
            patch("services.lightrag_service.settings") as mock_settings,
            patch("services.lightrag_service.LIGHTRAG_URL", "http://test-lightrag:9621"),
            patch("services.lightrag_service.LIGHTRAG_API_KEY", None),
            patch("httpx.AsyncClient", return_value=mock_client),
        ):
            mock_settings.lightrag = cfg
            import services.lightrag_service as svc
            importlib.reload(svc)
            await svc.query_knowledge_graph(user_id="user_mode_default", topic="startups")

        call_kwargs = mock_client.post.call_args
        json_body = call_kwargs[1]["json"]
        assert json_body["param"]["mode"] == "hybrid", (
            f"Default mode must be 'hybrid', got: {json_body['param']['mode']!r}"
        )

    @pytest.mark.asyncio
    async def test_query_uses_custom_mode_when_specified(self):
        """When mode='local' is passed, param.mode must be 'local'."""
        mock_client = _make_mock_client(status_code=200, response_json={"response": "ctx"})
        cfg = _make_cfg()

        with (
            patch("services.lightrag_service.settings") as mock_settings,
            patch("services.lightrag_service.LIGHTRAG_URL", "http://test-lightrag:9621"),
            patch("services.lightrag_service.LIGHTRAG_API_KEY", None),
            patch("httpx.AsyncClient", return_value=mock_client),
        ):
            mock_settings.lightrag = cfg
            import services.lightrag_service as svc
            importlib.reload(svc)
            await svc.query_knowledge_graph(user_id="user_mode_local", topic="startups", mode="local")

        call_kwargs = mock_client.post.call_args
        json_body = call_kwargs[1]["json"]
        assert json_body["param"]["mode"] == "local", (
            f"Custom mode 'local' must be forwarded to param.mode. Got: {json_body['param']['mode']!r}"
        )

    @pytest.mark.asyncio
    async def test_query_returns_response_text_on_success(self):
        """When LightRAG returns {'response': 'graph context'}, the function returns 'graph context'."""
        mock_client = _make_mock_client(
            status_code=200,
            response_json={"response": "graph context about AI topics"},
        )
        cfg = _make_cfg()

        with (
            patch("services.lightrag_service.settings") as mock_settings,
            patch("services.lightrag_service.LIGHTRAG_URL", "http://test-lightrag:9621"),
            patch("services.lightrag_service.LIGHTRAG_API_KEY", None),
            patch("httpx.AsyncClient", return_value=mock_client),
        ):
            mock_settings.lightrag = cfg
            import services.lightrag_service as svc
            importlib.reload(svc)
            result = await svc.query_knowledge_graph(user_id="user_response", topic="AI")

        assert result == "graph context about AI topics", (
            f"Expected 'graph context about AI topics', got: {result!r}"
        )

    @pytest.mark.asyncio
    async def test_query_returns_empty_string_on_failure(self):
        """When LightRAG returns 500, query_knowledge_graph returns '' (non-fatal)."""
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = Exception("HTTP 500")

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        cfg = _make_cfg()

        with (
            patch("services.lightrag_service.settings") as mock_settings,
            patch("services.lightrag_service.LIGHTRAG_URL", "http://test-lightrag:9621"),
            patch("services.lightrag_service.LIGHTRAG_API_KEY", None),
            patch("httpx.AsyncClient", return_value=mock_client),
        ):
            mock_settings.lightrag = cfg
            import services.lightrag_service as svc
            importlib.reload(svc)
            result = await svc.query_knowledge_graph(user_id="user_500_q", topic="topic")

        assert result == "", f"Expected empty string on HTTP error, got: {result!r}"

    @pytest.mark.asyncio
    async def test_query_returns_empty_string_on_timeout(self):
        """When httpx raises TimeoutException, query_knowledge_graph returns '' (non-fatal)."""
        mock_client = _make_mock_client(side_effect=httpx.TimeoutException("Timeout"))
        cfg = _make_cfg()

        with (
            patch("services.lightrag_service.settings") as mock_settings,
            patch("services.lightrag_service.LIGHTRAG_URL", "http://test-lightrag:9621"),
            patch("services.lightrag_service.LIGHTRAG_API_KEY", None),
            patch("httpx.AsyncClient", return_value=mock_client),
        ):
            mock_settings.lightrag = cfg
            import services.lightrag_service as svc
            importlib.reload(svc)
            result = await svc.query_knowledge_graph(user_id="user_timeout_q", topic="topic")

        assert result == "", f"Expected empty string on timeout, got: {result!r}"


# ---------------------------------------------------------------------------
# TestPerUserIsolation
# ---------------------------------------------------------------------------


class TestPerUserIsolation:
    """Per-user isolation: insert and query operations are scoped to exact user_id."""

    @pytest.mark.asyncio
    async def test_insert_for_user_a_tags_only_user_a(self):
        """insert_content for user_A must tag metadata.user_id='user_A' and doc_id starting with 'user_A_'."""
        mock_client = _make_mock_client(status_code=200)
        cfg = _make_cfg()

        with (
            patch("services.lightrag_service.settings") as mock_settings,
            patch("services.lightrag_service.LIGHTRAG_URL", "http://test-lightrag:9621"),
            patch("services.lightrag_service.LIGHTRAG_API_KEY", None),
            patch("httpx.AsyncClient", return_value=mock_client),
        ):
            mock_settings.lightrag = cfg
            import services.lightrag_service as svc
            importlib.reload(svc)
            await svc.insert_content(
                user_id="user_A",
                content="User A's content",
                metadata={"job_id": "job_A_1", "platform": "linkedin"},
            )

        call_kwargs = mock_client.post.call_args
        json_body = call_kwargs[1]["json"]

        assert json_body["metadata"]["user_id"] == "user_A", (
            f"metadata.user_id must be 'user_A', got: {json_body['metadata']['user_id']!r}"
        )
        assert json_body["doc_id"].startswith("user_A_"), (
            f"doc_id must start with 'user_A_', got: {json_body['doc_id']!r}"
        )

    @pytest.mark.asyncio
    async def test_query_for_user_a_filters_only_user_a(self):
        """query_knowledge_graph for user_A must include user_A in the doc_filter scope."""
        mock_client = _make_mock_client(status_code=200, response_json={"response": "ctx"})
        cfg = _make_cfg()

        with (
            patch("services.lightrag_service.settings") as mock_settings,
            patch("services.lightrag_service.LIGHTRAG_URL", "http://test-lightrag:9621"),
            patch("services.lightrag_service.LIGHTRAG_API_KEY", None),
            patch("httpx.AsyncClient", return_value=mock_client),
        ):
            mock_settings.lightrag = cfg
            import services.lightrag_service as svc
            importlib.reload(svc)
            await svc.query_knowledge_graph(user_id="user_A", topic="growth")

        call_kwargs = mock_client.post.call_args
        json_body = call_kwargs[1]["json"]
        param = json_body["param"]

        # user_A must appear in the filter
        doc_filter = param.get("doc_filter_func", "")
        filter_str = str(doc_filter)
        assert "user_A" in filter_str, (
            f"'user_A' must appear in doc_filter_func. Got: {doc_filter!r}"
        )

    @pytest.mark.asyncio
    async def test_query_for_user_b_does_not_match_user_a(self):
        """query_knowledge_graph for user_B must NOT contain 'user_A' in the filter."""
        mock_client = _make_mock_client(status_code=200, response_json={"response": "ctx"})
        cfg = _make_cfg()

        with (
            patch("services.lightrag_service.settings") as mock_settings,
            patch("services.lightrag_service.LIGHTRAG_URL", "http://test-lightrag:9621"),
            patch("services.lightrag_service.LIGHTRAG_API_KEY", None),
            patch("httpx.AsyncClient", return_value=mock_client),
        ):
            mock_settings.lightrag = cfg
            import services.lightrag_service as svc
            importlib.reload(svc)
            await svc.query_knowledge_graph(user_id="user_B", topic="growth")

        call_kwargs = mock_client.post.call_args
        json_body = call_kwargs[1]["json"]
        param = json_body["param"]
        doc_filter = str(param.get("doc_filter_func", ""))

        assert "user_A" not in doc_filter, (
            f"Cross-user contamination: 'user_A' found in user_B filter. Filter: {doc_filter!r}"
        )
        assert "user_B" in doc_filter, (
            f"'user_B' must appear in filter. Filter: {doc_filter!r}"
        )

    @pytest.mark.asyncio
    async def test_sequential_queries_for_different_users_are_isolated(self):
        """Sequential queries for user_alpha and user_beta use their own user filters."""
        cfg = _make_cfg()
        captured_bodies = []

        def make_capturing_client():
            mock_response = MagicMock()
            mock_response.raise_for_status = MagicMock()
            mock_response.json.return_value = {"response": "ctx"}
            client = AsyncMock()
            client.post.return_value = mock_response
            client.__aenter__ = AsyncMock(return_value=client)
            client.__aexit__ = AsyncMock(return_value=False)
            return client

        client_alpha = make_capturing_client()
        client_beta = make_capturing_client()
        clients = [client_alpha, client_beta]
        call_count = {"n": 0}

        def client_factory(*args, **kwargs):
            c = clients[call_count["n"] % 2]
            call_count["n"] += 1
            return c

        with (
            patch("services.lightrag_service.settings") as mock_settings,
            patch("services.lightrag_service.LIGHTRAG_URL", "http://test-lightrag:9621"),
            patch("services.lightrag_service.LIGHTRAG_API_KEY", None),
            patch("httpx.AsyncClient", side_effect=client_factory),
        ):
            mock_settings.lightrag = cfg
            import services.lightrag_service as svc
            importlib.reload(svc)
            await svc.query_knowledge_graph(user_id="user_alpha", topic="content")
            await svc.query_knowledge_graph(user_id="user_beta", topic="content")

        alpha_body = client_alpha.post.call_args[1]["json"]
        beta_body = client_beta.post.call_args[1]["json"]

        alpha_filter = str(alpha_body["param"].get("doc_filter_func", ""))
        beta_filter = str(beta_body["param"].get("doc_filter_func", ""))

        assert "user_alpha" in alpha_filter, f"'user_alpha' missing from alpha filter: {alpha_filter!r}"
        assert "user_beta" in beta_filter, f"'user_beta' missing from beta filter: {beta_filter!r}"
        assert "user_beta" not in alpha_filter, (
            f"Cross-user: 'user_beta' in alpha filter: {alpha_filter!r}"
        )
        assert "user_alpha" not in beta_filter, (
            f"Cross-user: 'user_alpha' in beta filter: {beta_filter!r}"
        )

    @pytest.mark.asyncio
    async def test_user_id_with_special_chars_is_sanitized_or_rejected(self):
        """user_id containing dots, spaces, or special characters is either sanitized or rejected.

        The fix in lightrag_service.py validates user_id against [a-zA-Z0-9_-].
        A user_id with special characters (e.g. 'user.name@domain.com') is rejected
        and query_knowledge_graph returns '' without making an HTTP call.
        """
        special_user_id = "user.name@domain.com"
        mock_client = _make_mock_client(status_code=200, response_json={"response": "ctx"})
        cfg = _make_cfg()

        with (
            patch("services.lightrag_service.settings") as mock_settings,
            patch("services.lightrag_service.LIGHTRAG_URL", "http://test-lightrag:9621"),
            patch("services.lightrag_service.LIGHTRAG_API_KEY", None),
            patch("httpx.AsyncClient", return_value=mock_client),
        ):
            mock_settings.lightrag = cfg
            import services.lightrag_service as svc
            importlib.reload(svc)
            result = await svc.query_knowledge_graph(user_id=special_user_id, topic="test")

        # Either rejected (no HTTP call, returns '') OR sanitized (HTTP call made, filter uses clean id)
        if not mock_client.post.called:
            # Rejection path — acceptable
            assert result == "", (
                f"Rejected user_id must return empty string. Got: {result!r}"
            )
        else:
            # Sanitization path — filter must not contain dots or @ symbols
            doc_filter = str(mock_client.post.call_args[1]["json"]["param"].get("doc_filter_func", ""))
            assert "@" not in doc_filter, f"@ symbol leaked into filter: {doc_filter!r}"
            assert ".com" not in doc_filter, f"Domain leaked into filter: {doc_filter!r}"


# ---------------------------------------------------------------------------
# TestEmbeddingConfig
# ---------------------------------------------------------------------------


class TestEmbeddingConfig:
    """Embedding config assertions: valid, wrong model, wrong dim, not configured."""

    @pytest.mark.asyncio
    async def test_assert_embedding_valid_config_passes(self):
        """Correct model (text-embedding-3-small) and dim (1536) -> no exception raised."""
        cfg = _make_cfg(
            embedding_model="text-embedding-3-small",
            embedding_dim=1536,
        )

        with patch("services.lightrag_service.settings") as mock_settings:
            mock_settings.lightrag = cfg
            from services import lightrag_service as svc
            # Should NOT raise
            await svc.assert_lightrag_embedding_config()

    @pytest.mark.asyncio
    async def test_assert_embedding_wrong_model_raises(self):
        """Wrong embedding model -> raises AssertionError with 'text-embedding-3-small' in message."""
        cfg = _make_cfg(
            embedding_model="text-embedding-ada-002",
            embedding_dim=1536,
        )

        with patch("services.lightrag_service.settings") as mock_settings:
            mock_settings.lightrag = cfg
            from services import lightrag_service as svc
            with pytest.raises(AssertionError, match="text-embedding-3-small"):
                await svc.assert_lightrag_embedding_config()

    @pytest.mark.asyncio
    async def test_assert_embedding_wrong_dim_raises(self):
        """Wrong embedding dimension (768) -> raises AssertionError with '1536' in message."""
        cfg = _make_cfg(
            embedding_model="text-embedding-3-small",
            embedding_dim=768,
        )

        with patch("services.lightrag_service.settings") as mock_settings:
            mock_settings.lightrag = cfg
            from services import lightrag_service as svc
            with pytest.raises(AssertionError, match="1536"):
                await svc.assert_lightrag_embedding_config()

    @pytest.mark.asyncio
    async def test_assert_embedding_not_configured_logs_warning_no_error(self):
        """When LightRAG is not configured, function returns without error or assertion check."""
        cfg = _make_cfg(is_configured=False)
        assertion_called = {"count": 0}
        original_assert = cfg.assert_embedding_config

        def track_assert():
            assertion_called["count"] += 1
            original_assert()

        cfg.assert_embedding_config = track_assert

        with patch("services.lightrag_service.settings") as mock_settings:
            mock_settings.lightrag = cfg
            from services import lightrag_service as svc
            # Should NOT raise even though embedding is not configured
            await svc.assert_lightrag_embedding_config()

        assert assertion_called["count"] == 0, (
            "assert_embedding_config must NOT be called when LightRAG is not configured"
        )


# ---------------------------------------------------------------------------
# TestGracefulDegradation
# ---------------------------------------------------------------------------


class TestGracefulDegradation:
    """All public functions return safe defaults when LightRAG is not configured or errors occur."""

    @pytest.mark.asyncio
    async def test_all_functions_return_default_when_not_configured(self):
        """When is_configured()=False, all functions return their default values without HTTP calls."""
        cfg = _make_cfg(is_configured=False)
        http_calls = {"count": 0}

        class TrackingClient:
            """Tracks whether AsyncClient was instantiated."""
            def __init__(self, *args, **kwargs):
                http_calls["count"] += 1

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

            async def get(self, *args, **kwargs):
                raise AssertionError("Should not be called when not configured")

            async def post(self, *args, **kwargs):
                raise AssertionError("Should not be called when not configured")

        with (
            patch("services.lightrag_service.settings") as mock_settings,
            patch("httpx.AsyncClient", TrackingClient),
        ):
            mock_settings.lightrag = cfg
            import services.lightrag_service as svc

            health_result = await svc.health_check()
            insert_result = await svc.insert_content(
                user_id="user_uncfg", content="content", metadata={}
            )
            query_result = await svc.query_knowledge_graph(
                user_id="user_uncfg", topic="topic"
            )

        assert health_result is False, f"health_check must return False when not configured, got {health_result}"
        assert insert_result is False, f"insert_content must return False when not configured, got {insert_result}"
        assert query_result == "", f"query_knowledge_graph must return '' when not configured, got {query_result!r}"

        # No HTTP clients should have been instantiated
        assert http_calls["count"] == 0, (
            f"httpx.AsyncClient must NOT be instantiated when LightRAG is not configured. "
            f"Got {http_calls['count']} instantiation(s)."
        )

    @pytest.mark.asyncio
    async def test_insert_does_not_raise_on_any_exception(self):
        """Even if httpx raises a completely unexpected exception, insert_content returns False (never raises)."""
        mock_client = _make_mock_client(side_effect=RuntimeError("Unexpected internal error"))
        cfg = _make_cfg()

        with (
            patch("services.lightrag_service.settings") as mock_settings,
            patch("services.lightrag_service.LIGHTRAG_URL", "http://test-lightrag:9621"),
            patch("services.lightrag_service.LIGHTRAG_API_KEY", None),
            patch("httpx.AsyncClient", return_value=mock_client),
        ):
            mock_settings.lightrag = cfg
            import services.lightrag_service as svc
            importlib.reload(svc)
            # Must NOT raise
            result = await svc.insert_content(
                user_id="user_exception",
                content="content",
                metadata={"job_id": "j_exc"},
            )

        assert result is False, f"insert_content must return False on any exception, got {result}"

    @pytest.mark.asyncio
    async def test_query_does_not_raise_on_any_exception(self):
        """Even if httpx raises a completely unexpected exception, query_knowledge_graph returns '' (never raises)."""
        mock_client = _make_mock_client(side_effect=RuntimeError("Unexpected internal error"))
        cfg = _make_cfg()

        with (
            patch("services.lightrag_service.settings") as mock_settings,
            patch("services.lightrag_service.LIGHTRAG_URL", "http://test-lightrag:9621"),
            patch("services.lightrag_service.LIGHTRAG_API_KEY", None),
            patch("httpx.AsyncClient", return_value=mock_client),
        ):
            mock_settings.lightrag = cfg
            import services.lightrag_service as svc
            importlib.reload(svc)
            # Must NOT raise
            result = await svc.query_knowledge_graph(
                user_id="user_exc_query",
                topic="topic",
            )

        assert result == "", f"query_knowledge_graph must return '' on any exception, got {result!r}"
