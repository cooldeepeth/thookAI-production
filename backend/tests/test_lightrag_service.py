"""Tests for backend/services/lightrag_service.py

Verifies all 4 service functions handle success, failure, and
unconfigured states correctly. All external HTTP calls are mocked.

LRAG-02: Per-user isolation verified via test_query_scoped_to_user
and test_query_cross_user_isolation — storage-level filter, not just NL.
"""
import pytest
import httpx
from unittest.mock import patch, AsyncMock, MagicMock


# ---------------------------------------------------------------------------
# Helper: build a mock LightRAGConfig object
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
        self.assert_embedding_config_call_count = 0

    def is_configured(self) -> bool:
        return self._is_configured

    def assert_embedding_config(self) -> None:
        self.assert_embedding_config_call_count += 1
        assert self.embedding_model == "text-embedding-3-small", (
            f"LIGHTRAG_EMBEDDING_MODEL must be 'text-embedding-3-small', got: {self.embedding_model}"
        )
        assert self.embedding_dim == 1536, (
            f"LIGHTRAG_EMBEDDING_DIM must be 1536 for text-embedding-3-small, got: {self.embedding_dim}"
        )


def _make_lightrag_config(
    is_configured=True,
    url="http://test-lightrag:9621",
    api_key=None,
    embedding_model="text-embedding-3-small",
    embedding_dim=1536,
) -> _FakeLightRAGConfig:
    """Return a fake LightRAGConfig for tests."""
    return _FakeLightRAGConfig(
        is_configured_val=is_configured,
        url=url,
        api_key=api_key,
        embedding_model=embedding_model,
        embedding_dim=embedding_dim,
    )


# ---------------------------------------------------------------------------
# health_check tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_health_check_success():
    """Mock httpx GET to /health returning 200 -> returns True."""
    mock_response = MagicMock()
    mock_response.status_code = 200

    mock_client = AsyncMock()
    mock_client.get.return_value = mock_response
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    cfg = _make_lightrag_config(is_configured=True)

    with patch("services.lightrag_service.settings") as mock_settings, \
         patch("services.lightrag_service.LIGHTRAG_URL", "http://test-lightrag:9621"), \
         patch("httpx.AsyncClient", return_value=mock_client):
        mock_settings.lightrag = cfg
        from services.lightrag_service import health_check
        result = await health_check()

    assert result is True
    mock_client.get.assert_called_once_with("http://test-lightrag:9621/health")


@pytest.mark.asyncio
async def test_health_check_failure():
    """Mock httpx GET raising ConnectionError -> returns False."""
    mock_client = AsyncMock()
    mock_client.get.side_effect = Exception("Connection refused")
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    cfg = _make_lightrag_config(is_configured=True)

    with patch("services.lightrag_service.settings") as mock_settings, \
         patch("services.lightrag_service.LIGHTRAG_URL", "http://test-lightrag:9621"), \
         patch("httpx.AsyncClient", return_value=mock_client):
        mock_settings.lightrag = cfg
        from services.lightrag_service import health_check
        result = await health_check()

    assert result is False


@pytest.mark.asyncio
async def test_health_check_not_configured():
    """settings.lightrag.is_configured() returns False -> returns False without HTTP call."""
    cfg = _make_lightrag_config(is_configured=False)

    with patch("services.lightrag_service.settings") as mock_settings, \
         patch("httpx.AsyncClient") as mock_client_cls:
        mock_settings.lightrag = cfg
        from services.lightrag_service import health_check
        result = await health_check()

    assert result is False
    mock_client_cls.assert_not_called()


# ---------------------------------------------------------------------------
# insert_content tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_insert_content_success():
    """Mock httpx POST to /documents/insert_text returning 200 -> returns True."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.post.return_value = mock_response
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    cfg = _make_lightrag_config(is_configured=True)

    with patch("services.lightrag_service.settings") as mock_settings, \
         patch("services.lightrag_service.LIGHTRAG_URL", "http://test-lightrag:9621"), \
         patch("services.lightrag_service.LIGHTRAG_API_KEY", None), \
         patch("httpx.AsyncClient", return_value=mock_client):
        mock_settings.lightrag = cfg
        from services.lightrag_service import insert_content
        result = await insert_content(
            user_id="user_123",
            content="Great content here",
            metadata={"platform": "linkedin", "content_type": "post", "was_edited": False, "job_id": "job_456"},
        )

    assert result is True
    # doc_id should be "user_123_job_456"
    call_kwargs = mock_client.post.call_args
    assert call_kwargs[1]["json"]["doc_id"] == "user_123_job_456"


@pytest.mark.asyncio
async def test_insert_content_failure():
    """Mock httpx POST raising HTTPStatusError -> returns False, logs warning."""
    mock_client = AsyncMock()
    mock_client.post.side_effect = Exception("Service unavailable")
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    cfg = _make_lightrag_config(is_configured=True)

    with patch("services.lightrag_service.settings") as mock_settings, \
         patch("services.lightrag_service.LIGHTRAG_URL", "http://test-lightrag:9621"), \
         patch("services.lightrag_service.LIGHTRAG_API_KEY", None), \
         patch("httpx.AsyncClient", return_value=mock_client):
        mock_settings.lightrag = cfg
        from services.lightrag_service import insert_content
        result = await insert_content(
            user_id="user_123",
            content="Some content",
            metadata={"job_id": "job_x"},
        )

    assert result is False


@pytest.mark.asyncio
async def test_insert_content_not_configured():
    """settings.lightrag.is_configured() returns False -> returns False without HTTP call."""
    cfg = _make_lightrag_config(is_configured=False)

    with patch("services.lightrag_service.settings") as mock_settings, \
         patch("httpx.AsyncClient") as mock_client_cls:
        mock_settings.lightrag = cfg
        from services.lightrag_service import insert_content
        result = await insert_content(
            user_id="user_123",
            content="Some content",
            metadata={},
        )

    assert result is False
    mock_client_cls.assert_not_called()


@pytest.mark.asyncio
async def test_insert_content_tags_user_id():
    """Verify content sent starts with '[CREATOR:{user_id}]'."""
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.post.return_value = mock_response
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    cfg = _make_lightrag_config(is_configured=True)
    user_id = "creator_abc"

    with patch("services.lightrag_service.settings") as mock_settings, \
         patch("services.lightrag_service.LIGHTRAG_URL", "http://test-lightrag:9621"), \
         patch("services.lightrag_service.LIGHTRAG_API_KEY", None), \
         patch("httpx.AsyncClient", return_value=mock_client):
        mock_settings.lightrag = cfg
        from services.lightrag_service import insert_content
        await insert_content(
            user_id=user_id,
            content="My amazing post",
            metadata={"platform": "linkedin", "content_type": "post", "was_edited": False, "job_id": "j1"},
        )

    call_kwargs = mock_client.post.call_args
    text_body = call_kwargs[1]["json"]["text"]
    assert text_body.startswith(f"[CREATOR:{user_id}]"), (
        f"Content must start with [CREATOR:{user_id}], got: {text_body[:60]}"
    )


@pytest.mark.asyncio
async def test_insert_content_forwards_metadata():
    """Verify the POST JSON body includes metadata dict with platform, content_type, was_edited, job_id fields."""
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.post.return_value = mock_response
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    cfg = _make_lightrag_config(is_configured=True)

    with patch("services.lightrag_service.settings") as mock_settings, \
         patch("services.lightrag_service.LIGHTRAG_URL", "http://test-lightrag:9621"), \
         patch("services.lightrag_service.LIGHTRAG_API_KEY", None), \
         patch("httpx.AsyncClient", return_value=mock_client):
        mock_settings.lightrag = cfg
        from services.lightrag_service import insert_content
        await insert_content(
            user_id="user_xyz",
            content="Some content",
            metadata={
                "platform": "x",
                "content_type": "thread",
                "was_edited": True,
                "job_id": "job_999",
            },
        )

    call_kwargs = mock_client.post.call_args
    json_body = call_kwargs[1]["json"]
    metadata = json_body["metadata"]

    assert metadata["platform"] == "x"
    assert metadata["content_type"] == "thread"
    assert metadata["was_edited"] is True
    assert metadata["job_id"] == "job_999"
    assert metadata["user_id"] == "user_xyz"


# ---------------------------------------------------------------------------
# query_knowledge_graph tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_query_knowledge_graph_success():
    """Mock httpx POST to /query returning {"response": "some context"} -> returns "some context"."""
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {"response": "some context about AI topics"}

    mock_client = AsyncMock()
    mock_client.post.return_value = mock_response
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    cfg = _make_lightrag_config(is_configured=True)

    with patch("services.lightrag_service.settings") as mock_settings, \
         patch("services.lightrag_service.LIGHTRAG_URL", "http://test-lightrag:9621"), \
         patch("services.lightrag_service.LIGHTRAG_API_KEY", None), \
         patch("httpx.AsyncClient", return_value=mock_client):
        mock_settings.lightrag = cfg
        from services.lightrag_service import query_knowledge_graph
        result = await query_knowledge_graph(user_id="user_A", topic="AI productivity")

    assert result == "some context about AI topics"


@pytest.mark.asyncio
async def test_query_knowledge_graph_failure():
    """Mock httpx POST raising TimeoutError -> returns ''."""
    mock_client = AsyncMock()
    mock_client.post.side_effect = Exception("Timeout")
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    cfg = _make_lightrag_config(is_configured=True)

    with patch("services.lightrag_service.settings") as mock_settings, \
         patch("services.lightrag_service.LIGHTRAG_URL", "http://test-lightrag:9621"), \
         patch("services.lightrag_service.LIGHTRAG_API_KEY", None), \
         patch("httpx.AsyncClient", return_value=mock_client):
        mock_settings.lightrag = cfg
        from services.lightrag_service import query_knowledge_graph
        result = await query_knowledge_graph(user_id="user_A", topic="AI")

    assert result == ""


@pytest.mark.asyncio
async def test_query_knowledge_graph_not_configured():
    """is_configured() False -> returns ''."""
    cfg = _make_lightrag_config(is_configured=False)

    with patch("services.lightrag_service.settings") as mock_settings, \
         patch("httpx.AsyncClient") as mock_client_cls:
        mock_settings.lightrag = cfg
        from services.lightrag_service import query_knowledge_graph
        result = await query_knowledge_graph(user_id="user_A", topic="AI")

    assert result == ""
    mock_client_cls.assert_not_called()


@pytest.mark.asyncio
async def test_query_uses_hybrid_mode():
    """Verify the POST body contains {'param': {'mode': 'hybrid'}}."""
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {"response": "context"}

    mock_client = AsyncMock()
    mock_client.post.return_value = mock_response
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    cfg = _make_lightrag_config(is_configured=True)

    with patch("services.lightrag_service.settings") as mock_settings, \
         patch("services.lightrag_service.LIGHTRAG_URL", "http://test-lightrag:9621"), \
         patch("services.lightrag_service.LIGHTRAG_API_KEY", None), \
         patch("httpx.AsyncClient", return_value=mock_client):
        mock_settings.lightrag = cfg
        from services.lightrag_service import query_knowledge_graph
        await query_knowledge_graph(user_id="user_A", topic="startups")

    call_kwargs = mock_client.post.call_args
    json_body = call_kwargs[1]["json"]
    assert json_body["param"]["mode"] == "hybrid"


@pytest.mark.asyncio
async def test_query_scoped_to_user():
    """Verify the POST body's 'param' dict contains a user_id scoping mechanism.

    This proves per-user isolation happens at the storage filter level,
    NOT just in the natural language query string.
    """
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {"response": "context"}

    mock_client = AsyncMock()
    mock_client.post.return_value = mock_response
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    cfg = _make_lightrag_config(is_configured=True)
    user_id = "user_isolated"

    with patch("services.lightrag_service.settings") as mock_settings, \
         patch("services.lightrag_service.LIGHTRAG_URL", "http://test-lightrag:9621"), \
         patch("services.lightrag_service.LIGHTRAG_API_KEY", None), \
         patch("httpx.AsyncClient", return_value=mock_client):
        mock_settings.lightrag = cfg
        from services.lightrag_service import query_knowledge_graph
        await query_knowledge_graph(user_id=user_id, topic="content strategy")

    call_kwargs = mock_client.post.call_args
    json_body = call_kwargs[1]["json"]
    param = json_body["param"]

    # The user_id must appear in a structured filter field within param
    # (doc_filter_func containing user_id string OR ids field with CREATOR:{user_id} prefix)
    param_str = str(param)
    assert user_id in param_str, (
        f"user_id '{user_id}' must appear in param dict for storage-level isolation, "
        f"but param was: {param}"
    )

    # Ensure it's in a filter field, not only in the natural language query
    doc_filter_func = param.get("doc_filter_func", "")
    ids_field = param.get("ids")
    filter_contains_user = (
        (isinstance(doc_filter_func, str) and user_id in doc_filter_func)
        or (isinstance(ids_field, (list, str)) and user_id in str(ids_field))
    )
    assert filter_contains_user, (
        f"user_id must appear in doc_filter_func or ids field for storage-level isolation. "
        f"doc_filter_func={doc_filter_func!r}, ids={ids_field!r}"
    )


@pytest.mark.asyncio
async def test_query_cross_user_isolation():
    """Call query_knowledge_graph with user_id='user_A' and verify param does NOT contain 'user_B'.

    Ensures query is scoped exclusively to the requesting user — no cross-user data leakage.
    """
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {"response": "user A content context"}

    mock_client = AsyncMock()
    mock_client.post.return_value = mock_response
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    cfg = _make_lightrag_config(is_configured=True)

    with patch("services.lightrag_service.settings") as mock_settings, \
         patch("services.lightrag_service.LIGHTRAG_URL", "http://test-lightrag:9621"), \
         patch("services.lightrag_service.LIGHTRAG_API_KEY", None), \
         patch("httpx.AsyncClient", return_value=mock_client):
        mock_settings.lightrag = cfg
        from services.lightrag_service import query_knowledge_graph
        await query_knowledge_graph(user_id="user_A", topic="startup growth")

    call_kwargs = mock_client.post.call_args
    json_body = call_kwargs[1]["json"]
    param = json_body["param"]

    # user_B must NOT appear anywhere in the param dict
    assert "user_B" not in str(param), (
        f"Cross-user contamination: 'user_B' found in param for user_A query. param={param}"
    )


# ---------------------------------------------------------------------------
# assert_lightrag_embedding_config tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_assert_embedding_config_valid():
    """Default config (text-embedding-3-small, 1536) -> no error raised."""
    cfg = _make_lightrag_config(
        is_configured=True,
        embedding_model="text-embedding-3-small",
        embedding_dim=1536,
    )

    with patch("services.lightrag_service.settings") as mock_settings:
        mock_settings.lightrag = cfg
        from services.lightrag_service import assert_lightrag_embedding_config
        # Should NOT raise
        await assert_lightrag_embedding_config()


@pytest.mark.asyncio
async def test_assert_embedding_config_wrong_model():
    """Set embedding_model to 'text-embedding-ada-002' -> raises AssertionError."""
    cfg = _make_lightrag_config(
        is_configured=True,
        embedding_model="text-embedding-ada-002",
        embedding_dim=1536,
    )

    with patch("services.lightrag_service.settings") as mock_settings:
        mock_settings.lightrag = cfg
        from services.lightrag_service import assert_lightrag_embedding_config
        with pytest.raises(AssertionError, match="text-embedding-3-small"):
            await assert_lightrag_embedding_config()


@pytest.mark.asyncio
async def test_assert_embedding_config_wrong_dim():
    """Set embedding_dim to 768 -> raises AssertionError."""
    cfg = _make_lightrag_config(
        is_configured=True,
        embedding_model="text-embedding-3-small",
        embedding_dim=768,
    )

    with patch("services.lightrag_service.settings") as mock_settings:
        mock_settings.lightrag = cfg
        from services.lightrag_service import assert_lightrag_embedding_config
        with pytest.raises(AssertionError, match="1536"):
            await assert_lightrag_embedding_config()


@pytest.mark.asyncio
async def test_assert_embedding_config_not_configured():
    """is_configured() False -> logs warning, no AssertionError raised."""
    cfg = _make_lightrag_config(is_configured=False)

    with patch("services.lightrag_service.settings") as mock_settings:
        mock_settings.lightrag = cfg
        from services.lightrag_service import assert_lightrag_embedding_config
        # Should NOT raise even though assert_embedding_config would raise — returns early
        await assert_lightrag_embedding_config()

    # assert_embedding_config should NOT have been called on the config object
    assert cfg.assert_embedding_config_call_count == 0, (
        "assert_embedding_config should not be called when LightRAG is not configured"
    )
