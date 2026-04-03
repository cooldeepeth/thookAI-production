"""Tests verifying per-user LightRAG graph namespace isolation.

E2E-03: Each user's knowledge graph is isolated — insert tags user_id,
query filters by user_id, no cross-user data leakage possible.

These tests use mocked httpx.AsyncClient to capture the exact HTTP request
body sent to the LightRAG service and assert that user_id isolation is
enforced at the storage filter level (not just via NL query text).
"""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock


# ---------------------------------------------------------------------------
# Helper: build a fake LightRAGConfig (avoids MagicMock assert_* collision)
# ---------------------------------------------------------------------------


class _FakeLightRAGConfig:
    """Fake LightRAGConfig for tests — avoids MagicMock assert_* collision."""

    def __init__(
        self,
        is_configured_val: bool = True,
        url: str = "http://fake-lightrag:9621",
        api_key: str = None,
        embedding_model: str = "text-embedding-3-small",
        embedding_dim: int = 1536,
    ):
        self._is_configured = is_configured_val
        self.url = url
        self.api_key = api_key
        self.embedding_model = embedding_model
        self.embedding_dim = embedding_dim

    def is_configured(self) -> bool:
        return self._is_configured

    def assert_embedding_config(self) -> None:
        pass


def _make_cfg(is_configured: bool = True) -> _FakeLightRAGConfig:
    return _FakeLightRAGConfig(is_configured_val=is_configured)


def _make_mock_client(response_json: dict = None):
    """Return a mock AsyncClient that captures POST calls."""
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = response_json or {"response": "mocked context"}

    mock_client = AsyncMock()
    mock_client.post.return_value = mock_response
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    return mock_client


# ---------------------------------------------------------------------------
# TestLightRAGPerUserIsolation
# ---------------------------------------------------------------------------


class TestLightRAGPerUserIsolation:
    """Verify per-user LightRAG graph namespace isolation at service level."""

    @pytest.mark.asyncio
    async def test_insert_content_tags_creator_user_id(self):
        """insert_content sends [CREATOR:{user_id}] header in text body.

        Verifies:
        - text field starts with '[CREATOR:user_alpha]'
        - metadata.user_id == 'user_alpha'
        - doc_id is prefixed with user_id
        """
        mock_client = _make_mock_client()
        cfg = _make_cfg()

        with (
            patch("services.lightrag_service.settings") as mock_settings,
            patch("services.lightrag_service.LIGHTRAG_URL", "http://fake-lightrag:9621"),
            patch("services.lightrag_service.LIGHTRAG_API_KEY", None),
            patch("httpx.AsyncClient", return_value=mock_client),
        ):
            mock_settings.lightrag = cfg
            from services.lightrag_service import insert_content

            await insert_content(
                user_id="user_alpha",
                content="Test content about AI",
                metadata={"job_id": "j1", "platform": "linkedin"},
            )

        call_kwargs = mock_client.post.call_args
        json_body = call_kwargs[1]["json"]

        # Text starts with CREATOR tag
        assert json_body["text"].startswith("[CREATOR:user_alpha]"), (
            f"Expected text to start with '[CREATOR:user_alpha]', got: {json_body['text'][:80]}"
        )
        # Metadata carries user_id
        assert json_body["metadata"]["user_id"] == "user_alpha", (
            f"metadata.user_id must be 'user_alpha', got: {json_body['metadata'].get('user_id')}"
        )
        # doc_id is prefixed with user_id
        assert json_body["doc_id"].startswith("user_alpha"), (
            f"doc_id must start with 'user_alpha', got: {json_body['doc_id']}"
        )

    @pytest.mark.asyncio
    async def test_query_filters_by_exact_user_id(self):
        """query_knowledge_graph sends doc_filter_func containing exact user_id.

        Verifies that the lambda string in param.doc_filter_func contains
        the exact user_id string and uses equality comparison — not a prefix
        wildcard or unscoped query.
        """
        mock_client = _make_mock_client()
        cfg = _make_cfg()

        with (
            patch("services.lightrag_service.settings") as mock_settings,
            patch("services.lightrag_service.LIGHTRAG_URL", "http://fake-lightrag:9621"),
            patch("services.lightrag_service.LIGHTRAG_API_KEY", None),
            patch("httpx.AsyncClient", return_value=mock_client),
        ):
            mock_settings.lightrag = cfg
            from services.lightrag_service import query_knowledge_graph

            await query_knowledge_graph(user_id="user_alpha", topic="AI trends")

        call_kwargs = mock_client.post.call_args
        json_body = call_kwargs[1]["json"]
        doc_filter_func = json_body["param"]["doc_filter_func"]

        # The doc_filter_func lambda contains the user_id
        assert "user_alpha" in doc_filter_func, (
            f"doc_filter_func must contain 'user_alpha', got: {doc_filter_func!r}"
        )
        # The filter uses equality comparison (not just contains)
        assert "==" in doc_filter_func, (
            f"doc_filter_func must use == equality comparison, got: {doc_filter_func!r}"
        )
        # Standard LightRAG meta.get pattern present
        assert "meta.get('user_id')" in doc_filter_func or "user_id" in doc_filter_func, (
            f"doc_filter_func must reference user_id field: {doc_filter_func!r}"
        )

    @pytest.mark.asyncio
    async def test_different_users_get_different_filters(self):
        """Cross-user isolation: User A filter does not contain User B's ID and vice versa.

        This is the core security property: a query scoped to 'user_alpha'
        must NOT accidentally include 'user_beta' in its filter string.
        """
        cfg = _make_cfg()
        mock_client_alpha = _make_mock_client()
        mock_client_beta = _make_mock_client()

        # Query for user_alpha
        with (
            patch("services.lightrag_service.settings") as mock_settings,
            patch("services.lightrag_service.LIGHTRAG_URL", "http://fake-lightrag:9621"),
            patch("services.lightrag_service.LIGHTRAG_API_KEY", None),
            patch("httpx.AsyncClient", return_value=mock_client_alpha),
        ):
            mock_settings.lightrag = cfg
            from services.lightrag_service import query_knowledge_graph

            await query_knowledge_graph(user_id="user_alpha", topic="growth hacking")

        alpha_body = mock_client_alpha.post.call_args[1]["json"]
        alpha_filter = alpha_body["param"]["doc_filter_func"]

        # Query for user_beta
        with (
            patch("services.lightrag_service.settings") as mock_settings,
            patch("services.lightrag_service.LIGHTRAG_URL", "http://fake-lightrag:9621"),
            patch("services.lightrag_service.LIGHTRAG_API_KEY", None),
            patch("httpx.AsyncClient", return_value=mock_client_beta),
        ):
            mock_settings.lightrag = cfg
            from services.lightrag_service import query_knowledge_graph

            await query_knowledge_graph(user_id="user_beta", topic="growth hacking")

        beta_body = mock_client_beta.post.call_args[1]["json"]
        beta_filter = beta_body["param"]["doc_filter_func"]

        # user_alpha filter must not mention user_beta
        assert "user_beta" not in alpha_filter, (
            f"Cross-user contamination: 'user_beta' found in user_alpha filter: {alpha_filter!r}"
        )
        # user_beta filter must not mention user_alpha
        assert "user_alpha" not in beta_filter, (
            f"Cross-user contamination: 'user_alpha' found in user_beta filter: {beta_filter!r}"
        )
        # Each filter contains its own user_id
        assert "user_alpha" in alpha_filter, (
            f"'user_alpha' missing from alpha filter: {alpha_filter!r}"
        )
        assert "user_beta" in beta_filter, (
            f"'user_beta' missing from beta filter: {beta_filter!r}"
        )

    @pytest.mark.asyncio
    async def test_insert_doc_ids_prefixed_per_user(self):
        """Different users inserting same job_id get different doc_ids.

        doc_id format is '{user_id}_{job_id}' — prevents namespace collision
        between users who happen to share a job_id value.
        """
        cfg = _make_cfg()
        mock_client_alpha = _make_mock_client()
        mock_client_beta = _make_mock_client()

        with (
            patch("services.lightrag_service.settings") as mock_settings,
            patch("services.lightrag_service.LIGHTRAG_URL", "http://fake-lightrag:9621"),
            patch("services.lightrag_service.LIGHTRAG_API_KEY", None),
            patch("httpx.AsyncClient", return_value=mock_client_alpha),
        ):
            mock_settings.lightrag = cfg
            from services.lightrag_service import insert_content

            await insert_content(
                user_id="user_alpha",
                content="Content from user_alpha",
                metadata={"job_id": "j1", "platform": "linkedin"},
            )

        alpha_doc_id = mock_client_alpha.post.call_args[1]["json"]["doc_id"]

        with (
            patch("services.lightrag_service.settings") as mock_settings,
            patch("services.lightrag_service.LIGHTRAG_URL", "http://fake-lightrag:9621"),
            patch("services.lightrag_service.LIGHTRAG_API_KEY", None),
            patch("httpx.AsyncClient", return_value=mock_client_beta),
        ):
            mock_settings.lightrag = cfg
            from services.lightrag_service import insert_content

            await insert_content(
                user_id="user_beta",
                content="Content from user_beta",
                metadata={"job_id": "j1", "platform": "linkedin"},
            )

        beta_doc_id = mock_client_beta.post.call_args[1]["json"]["doc_id"]

        # Same job_id but different users -> different doc_ids
        assert alpha_doc_id != beta_doc_id, (
            f"Different users must produce different doc_ids for same job_id. "
            f"Got alpha={alpha_doc_id!r} beta={beta_doc_id!r}"
        )
        assert alpha_doc_id == "user_alpha_j1", (
            f"Expected doc_id 'user_alpha_j1', got: {alpha_doc_id!r}"
        )
        assert beta_doc_id == "user_beta_j1", (
            f"Expected doc_id 'user_beta_j1', got: {beta_doc_id!r}"
        )

    @pytest.mark.asyncio
    async def test_query_natural_language_includes_creator(self):
        """query_knowledge_graph includes 'For creator {user_id}:' in the NL query text.

        The natural language query is a secondary isolation signal — the primary
        isolation is via doc_filter_func. Both must reference user_id to ensure
        LightRAG entity extraction context and storage-level filtering are aligned.
        """
        mock_client = _make_mock_client()
        cfg = _make_cfg()

        with (
            patch("services.lightrag_service.settings") as mock_settings,
            patch("services.lightrag_service.LIGHTRAG_URL", "http://fake-lightrag:9621"),
            patch("services.lightrag_service.LIGHTRAG_API_KEY", None),
            patch("httpx.AsyncClient", return_value=mock_client),
        ):
            mock_settings.lightrag = cfg
            from services.lightrag_service import query_knowledge_graph

            await query_knowledge_graph(user_id="user_gamma", topic="startup fundraising")

        call_kwargs = mock_client.post.call_args
        json_body = call_kwargs[1]["json"]
        query_text = json_body["query"]

        assert query_text.startswith("For creator user_gamma:"), (
            f"Query text must start with 'For creator user_gamma:', got: {query_text[:80]!r}"
        )
