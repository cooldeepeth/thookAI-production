"""TDD: Expose LightRAG lambda injection cross-user data leak (CORE-09).

BUG: lightrag_service.py line 138 uses:
  f"lambda meta: meta.get('user_id') == '{user_id}'"

A malicious user_id like "x' or True or '" would produce:
  lambda meta: meta.get('user_id') == 'x' or True or ''
which matches ALL documents — cross-user data leak.

RED phase tests: These tests are designed to FAIL against the buggy implementation,
proving the vulnerability exists. After the fix, all 4 tests pass.

Fix strategy:
  Option A (preferred): Structured dict filter — no string interpolation at all.
    "doc_filter_func": {"field": "user_id", "operator": "==", "value": user_id}

  Option B (fallback): Sanitized lambda with strict alphanumeric-only user_id validation.
    safe_uid = re.sub(r"[^a-zA-Z0-9_-]", "", user_id)
    "doc_filter_func": f"lambda meta: meta.get('user_id') == '{safe_uid}'"
    plus: raise/return if user_id != safe_uid (reject injection attempt)
"""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _FakeLightRAGConfig:
    """Fake LightRAGConfig for tests — avoids MagicMock assert_* collision."""

    def __init__(self, is_configured_val=True, url="http://test-lightrag:9621", api_key=None):
        self._is_configured = is_configured_val
        self.url = url
        self.api_key = api_key
        self.embedding_model = "text-embedding-3-small"
        self.embedding_dim = 1536

    def is_configured(self) -> bool:
        return self._is_configured

    def assert_embedding_config(self) -> None:
        pass


def _make_cfg(is_configured=True) -> _FakeLightRAGConfig:
    return _FakeLightRAGConfig(is_configured_val=is_configured)


def _make_mock_client(response_json=None):
    """Return a mock AsyncClient that captures POST calls."""
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = response_json or {"response": "mocked context"}

    mock_client = AsyncMock()
    mock_client.post.return_value = mock_response
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    return mock_client


def _get_doc_filter_func(mock_client):
    """Extract doc_filter_func from the captured POST request body."""
    call_kwargs = mock_client.post.call_args
    json_body = call_kwargs[1]["json"]
    return json_body["param"]["doc_filter_func"]


# ---------------------------------------------------------------------------
# TestLambdaInjectionBlocked
# ---------------------------------------------------------------------------


class TestLambdaInjectionBlocked:
    """Verify that injection characters in user_id cannot expand the filter scope.

    All 4 tests assert that the doc_filter_func sent to the LightRAG API is SAFE —
    meaning it cannot be exploited to match documents belonging to other users.

    Against the BUGGY implementation, these tests FAIL (RED phase).
    After the fix, all tests PASS (GREEN phase).
    """

    @pytest.mark.asyncio
    async def test_injection_with_single_quote_does_not_expand_match(self):
        """user_id with single quote injection does NOT produce a universally-matching filter.

        Buggy code produces:
          lambda meta: meta.get('user_id') == 'x' or True or ''
        which always evaluates to True — matching ALL documents.

        Fixed code either:
          (a) uses a structured dict filter (no string interpolation), OR
          (b) strips the quote so the filter only targets the sanitized user_id.
        """
        malicious_user_id = "x' or True or '"
        mock_client = _make_mock_client()
        cfg = _make_cfg()

        with (
            patch("services.lightrag_service.settings") as mock_settings,
            patch("services.lightrag_service.LIGHTRAG_URL", "http://test-lightrag:9621"),
            patch("services.lightrag_service.LIGHTRAG_API_KEY", None),
            patch("httpx.AsyncClient", return_value=mock_client),
        ):
            mock_settings.lightrag = cfg
            # Re-import to pick up patched settings
            import importlib
            import services.lightrag_service as svc
            importlib.reload(svc)
            result = await svc.query_knowledge_graph(user_id=malicious_user_id, topic="test")

        # If the call was not made (rejected early), that's also a valid fix
        if not mock_client.post.called:
            # Graceful rejection — empty return is acceptable
            assert result == "", (
                f"When injection user_id is rejected, should return ''. Got: {result!r}"
            )
            return

        doc_filter = _get_doc_filter_func(mock_client)

        # CASE A: structured dict — no string interpolation possible
        if isinstance(doc_filter, dict):
            filter_value = doc_filter.get("value", "")
            # The value must be the exact (possibly sanitized) user_id — NOT expanded
            assert "or True" not in str(filter_value), (
                f"Structured filter value contains 'or True' injection: {filter_value!r}"
            )
            return

        # CASE B: lambda string — must be sanitized (no unescaped quote that breaks the string)
        assert isinstance(doc_filter, str), (
            f"doc_filter_func must be a string lambda or dict, got: {type(doc_filter)}"
        )
        # The dangerous "or True or" pattern must NOT appear in the filter
        assert "or True or" not in doc_filter, (
            f"INJECTION VULNERABILITY: doc_filter_func contains 'or True or' expansion. "
            f"Filter: {doc_filter!r}\n"
            f"This means user_id injection expanded the filter to match ALL documents."
        )
        # The filter must not contain unescaped single quotes that terminate the string literal
        # A safe lambda with sanitized user_id would look like: "lambda meta: meta.get('user_id') == 'xorTrueor'"
        # where dangerous chars were stripped. Count unescaped quotes — odd count means broken string.
        # Simple check: the filter string must be parseable Python (no syntax from injection)
        assert "' or " not in doc_filter, (
            f"INJECTION: filter contains \"' or \" pattern indicating injection worked: {doc_filter!r}"
        )

    @pytest.mark.asyncio
    async def test_injection_with_or_true_does_not_match_all_documents(self):
        """user_id='or True or' injection does NOT produce a universally-true filter.

        Buggy code with user_id = "' or True or '" produces:
          lambda meta: meta.get('user_id') == '' or True or ''
        which always returns True — ALL documents match.

        Fixed code must NOT allow this expansion.
        """
        malicious_user_id = "' or True or '"
        mock_client = _make_mock_client()
        cfg = _make_cfg()

        with (
            patch("services.lightrag_service.settings") as mock_settings,
            patch("services.lightrag_service.LIGHTRAG_URL", "http://test-lightrag:9621"),
            patch("services.lightrag_service.LIGHTRAG_API_KEY", None),
            patch("httpx.AsyncClient", return_value=mock_client),
        ):
            mock_settings.lightrag = cfg
            import importlib
            import services.lightrag_service as svc
            importlib.reload(svc)
            result = await svc.query_knowledge_graph(user_id=malicious_user_id, topic="exploit")

        # Graceful rejection is acceptable
        if not mock_client.post.called:
            assert result == "", (
                f"Rejected injection user_id must return empty string. Got: {result!r}"
            )
            return

        doc_filter = _get_doc_filter_func(mock_client)

        if isinstance(doc_filter, dict):
            # Structured dict — safe by design
            value = str(doc_filter.get("value", ""))
            assert "or True" not in value, (
                f"Structured filter value unexpectedly contains 'or True': {value!r}"
            )
            return

        # String lambda — must not contain the injection expansion
        assert "or True" not in doc_filter, (
            f"INJECTION VULNERABILITY: 'or True' found in doc_filter_func: {doc_filter!r}\n"
            f"The lambda is universally true — all documents would match!"
        )

    @pytest.mark.asyncio
    async def test_injection_with_semicolon_does_not_execute_code(self):
        """user_id with semicolons/imports does NOT enable code execution path.

        Buggy code with user_id = "'; import os; os.system('rm -rf /'); '" would produce:
          lambda meta: meta.get('user_id') == ''; import os; os.system('rm -rf /'); ''
        This is a code injection attempt. The filter must sanitize or reject this.
        """
        malicious_user_id = "'; import os; os.system('id'); '"
        mock_client = _make_mock_client()
        cfg = _make_cfg()

        with (
            patch("services.lightrag_service.settings") as mock_settings,
            patch("services.lightrag_service.LIGHTRAG_URL", "http://test-lightrag:9621"),
            patch("services.lightrag_service.LIGHTRAG_API_KEY", None),
            patch("httpx.AsyncClient", return_value=mock_client),
        ):
            mock_settings.lightrag = cfg
            import importlib
            import services.lightrag_service as svc
            importlib.reload(svc)
            result = await svc.query_knowledge_graph(user_id=malicious_user_id, topic="rce")

        # Graceful rejection is acceptable (best approach)
        if not mock_client.post.called:
            assert result == "", (
                f"Rejected injection user_id must return empty string. Got: {result!r}"
            )
            return

        doc_filter = _get_doc_filter_func(mock_client)

        if isinstance(doc_filter, dict):
            # Structured dict — no string interpolation, safe by design
            value = str(doc_filter.get("value", ""))
            assert "import os" not in value, (
                f"Structured dict value contains code injection: {value!r}"
            )
            return

        # String lambda — must not contain the semicolons or import statement
        assert "import os" not in doc_filter, (
            f"CODE INJECTION: 'import os' found in doc_filter_func: {doc_filter!r}"
        )
        assert "os.system" not in doc_filter, (
            f"CODE INJECTION: 'os.system' found in doc_filter_func: {doc_filter!r}"
        )
        # Semicolons in a lambda string indicate statement injection
        assert doc_filter.count(";") == 0, (
            f"CODE INJECTION: semicolons found in doc_filter_func: {doc_filter!r}"
        )

    @pytest.mark.asyncio
    async def test_normal_user_id_produces_correct_filter(self):
        """A benign user_id like 'user_abc123' still produces a correct filter targeting only that user.

        This verifies the fix doesn't break the happy path — valid user_ids still work.
        """
        safe_user_id = "user_abc123"
        mock_client = _make_mock_client()
        cfg = _make_cfg()

        with (
            patch("services.lightrag_service.settings") as mock_settings,
            patch("services.lightrag_service.LIGHTRAG_URL", "http://test-lightrag:9621"),
            patch("services.lightrag_service.LIGHTRAG_API_KEY", None),
            patch("httpx.AsyncClient", return_value=mock_client),
        ):
            mock_settings.lightrag = cfg
            import importlib
            import services.lightrag_service as svc
            importlib.reload(svc)
            result = await svc.query_knowledge_graph(user_id=safe_user_id, topic="AI strategy")

        assert mock_client.post.called, "Normal user_id should proceed to make HTTP call"

        doc_filter = _get_doc_filter_func(mock_client)

        # user_id must appear in the filter (either as dict value or in string)
        if isinstance(doc_filter, dict):
            assert doc_filter.get("value") == safe_user_id, (
                f"Structured filter value must be '{safe_user_id}', got: {doc_filter.get('value')!r}"
            )
        else:
            assert safe_user_id in doc_filter, (
                f"user_id '{safe_user_id}' must appear in doc_filter_func. Got: {doc_filter!r}"
            )

    @pytest.mark.asyncio
    async def test_query_payload_does_not_use_raw_lambda_string_with_unescaped_user_id(self):
        """The doc_filter_func field in the query payload uses a safe format.

        It must NOT be a raw f-string lambda with the user_id directly interpolated
        without sanitization. This test inspects the structure of the filter.

        After the fix, ONE of the following must be true:
          (a) doc_filter_func is a dict (structured filter — no eval/exec risk), OR
          (b) doc_filter_func is a string BUT the user_id was sanitized BEFORE interpolation
              (dangerous characters stripped, evidenced by safe_uid usage in code), OR
          (c) user_ids with special characters cause early return (rejection approach).
        """
        test_user_id = "user_test_safe"
        mock_client = _make_mock_client()
        cfg = _make_cfg()

        with (
            patch("services.lightrag_service.settings") as mock_settings,
            patch("services.lightrag_service.LIGHTRAG_URL", "http://test-lightrag:9621"),
            patch("services.lightrag_service.LIGHTRAG_API_KEY", None),
            patch("httpx.AsyncClient", return_value=mock_client),
        ):
            mock_settings.lightrag = cfg
            import importlib
            import services.lightrag_service as svc
            importlib.reload(svc)
            await svc.query_knowledge_graph(user_id=test_user_id, topic="test topic")

        assert mock_client.post.called, "Safe user_id must proceed to make HTTP call"

        call_kwargs = mock_client.post.call_args
        json_body = call_kwargs[1]["json"]
        doc_filter = json_body["param"]["doc_filter_func"]

        # The filter must be either a dict OR a string that was built safely
        is_safe_dict = isinstance(doc_filter, dict)
        is_safe_string = isinstance(doc_filter, str) and test_user_id in doc_filter

        assert is_safe_dict or is_safe_string, (
            f"doc_filter_func must be a dict or a string containing the user_id. "
            f"Got type={type(doc_filter).__name__}, value={doc_filter!r}"
        )

        # If it's a string, it should NOT be the raw f-string pattern with unquoted variables
        # The raw buggy pattern is: f"lambda meta: meta.get('user_id') == '{user_id}'"
        # which is detectable because the user_id is interpolated without sanitization
        # We test this with an injection-like ID to verify sanitization happened
        malicious_id = "test'; DROP TABLE users; --"
        mock_client2 = _make_mock_client()

        with (
            patch("services.lightrag_service.settings") as mock_settings2,
            patch("services.lightrag_service.LIGHTRAG_URL", "http://test-lightrag:9621"),
            patch("services.lightrag_service.LIGHTRAG_API_KEY", None),
            patch("httpx.AsyncClient", return_value=mock_client2),
        ):
            mock_settings2.lightrag = cfg
            import importlib
            import services.lightrag_service as svc2
            importlib.reload(svc2)
            await svc2.query_knowledge_graph(user_id=malicious_id, topic="test")

        if mock_client2.post.called:
            doc_filter2 = _get_doc_filter_func(mock_client2)
            if isinstance(doc_filter2, str):
                # Must not contain SQL-injection-like content
                assert "DROP TABLE" not in doc_filter2, (
                    f"Injection content leaked into filter: {doc_filter2!r}"
                )
                assert "--" not in doc_filter2, (
                    f"SQL comment marker leaked into filter: {doc_filter2!r}"
                )
