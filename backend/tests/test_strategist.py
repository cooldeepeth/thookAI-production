"""Tests for backend/agents/strategist.py

Covers all 7 STRAT requirements:
  TestStrategistAgent            — STRAT-01: agent entry points and LLM synthesis
  TestRecommendationCardSchema   — STRAT-02: pending_approval status + required fields
  TestWhyNowRationale            — STRAT-03: why_now non-empty rationale
  TestCadenceControls            — STRAT-04: max 3 cards/user/day atomic cap
  TestDismissalTracking          — STRAT-05: 14-day topic suppression
  TestConsecutiveDismissalThreshold — STRAT-06: 5 dismissals -> halved rate
  TestGeneratePayloadSchema      — STRAT-07: generate_payload matches ContentCreateRequest

All external dependencies are mocked — no real DB, LLM, or LightRAG calls.
asyncio_mode=auto in pytest.ini means no @pytest.mark.asyncio decorator needed.
"""
import ast
import json
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch, call

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_llm_response(cards):
    """Return JSON string matching strategist prompt output format."""
    return json.dumps(cards)


SAMPLE_CARD = {
    "topic": "ai in content creation",
    "hook_options": ["Hook A", "Hook B"],
    "platform": "linkedin",
    "why_now": "Why now: Your last 3 posts on AI got 2x engagement",
    "signal_source": "analytics",
    "generate_payload": {
        "platform": "linkedin",
        "content_type": "post",
        "raw_input": "Write about AI in content creation",
        "topic": "ai in content creation",
        "hook_strategy": "contrarian",
    },
}

SAMPLE_CARD_2 = {
    "topic": "founder storytelling",
    "hook_options": ["Hook X", "Hook Y"],
    "platform": "linkedin",
    "why_now": "Why now: Founder stories get 3x more saves than tactical posts",
    "signal_source": "performance",
    "generate_payload": {
        "content_type": "carousel",
        "raw_input": "Write about founder storytelling",
    },
}

# Minimal required keys for a card to pass _synthesize_recommendations validation
MINIMAL_CARD = {
    "topic": "startups",
    "hook_options": ["Hook 1"],
    "platform": "x",
    "why_now": "Why now: trending topic",
    "signal_source": "trending",
    "generate_payload": {"content_type": "thread", "raw_input": "Write about startups"},
}


def _make_mock_db():
    """Build a mock `db` object with all required collection mocks."""
    mock_db = MagicMock()

    # strategy_recommendations collection
    mock_db.strategy_recommendations = MagicMock()
    mock_db.strategy_recommendations.insert_one = AsyncMock(return_value=None)
    mock_db.strategy_recommendations.find_one = AsyncMock(return_value=None)
    mock_db.strategy_recommendations.find_one_and_update = AsyncMock(return_value=None)
    mock_db.strategy_recommendations.count_documents = AsyncMock(return_value=0)

    # strategist_state collection
    mock_db.strategist_state = MagicMock()
    mock_db.strategist_state.find_one = AsyncMock(return_value=None)
    mock_db.strategist_state.find_one_and_update = AsyncMock(return_value=None)
    mock_db.strategist_state.update_one = AsyncMock(return_value=None)

    # users collection (async for iteration)
    mock_db.users = MagicMock()
    users_cursor = AsyncMock()
    users_cursor.__aiter__ = MagicMock(return_value=iter([]))
    mock_db.users.find = MagicMock(return_value=users_cursor)

    # persona_engines collection
    mock_db.persona_engines = MagicMock()
    mock_db.persona_engines.find_one = AsyncMock(return_value=None)

    # content_jobs collection — supports .find().sort().to_list()
    jobs_sort_mock = MagicMock()
    jobs_sort_mock.to_list = AsyncMock(return_value=[])
    jobs_cursor_mock = MagicMock()
    jobs_cursor_mock.sort = MagicMock(return_value=jobs_sort_mock)
    mock_db.content_jobs = MagicMock()
    mock_db.content_jobs.find = MagicMock(return_value=jobs_cursor_mock)

    return mock_db


class _AsyncIterator:
    """Proper async iterator for mocking Motor cursor async-for loops."""

    def __init__(self, docs):
        self._docs = iter(docs)

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            return next(self._docs)
        except StopIteration:
            raise StopAsyncIteration


def _make_async_cursor(docs):
    """Return an async-iterable mock for Motor cursors (supports async-for)."""
    return _AsyncIterator(docs)


# ---------------------------------------------------------------------------
# STRAT-01: TestStrategistAgent
# ---------------------------------------------------------------------------


class TestStrategistAgent:
    """STRAT-01: run_strategist_for_user / run_strategist_for_all_users exported."""

    async def test_run_strategist_for_user_writes_cards(self):
        """Mock eligible user with persona + LLM returning 2 cards.

        Asserts insert_one called exactly 2 times, return dict has cards_written=2.
        """
        mock_db = _make_mock_db()

        # _get_cadence_state returns no halved_rate
        mock_db.strategist_state.find_one.return_value = {"halved_rate": False}

        # suppressed topics cursor (empty)
        mock_db.strategy_recommendations.find = MagicMock(
            return_value=_make_async_cursor([])
        )

        # persona_engines
        mock_db.persona_engines.find_one.return_value = {
            "user_id": "user_1",
            "card": {"archetype": "Thought Leader", "primary_platform": "linkedin"},
            "voice_fingerprint": {"traits": ["direct", "insightful"]},
            "content_identity": {"content_pillars": ["AI", "Startups"]},
            "learning_signals": {"approved_count": 5},
        }

        # content_jobs
        jobs_sort = MagicMock()
        jobs_sort.to_list = AsyncMock(return_value=[])
        jobs_cursor = MagicMock()
        jobs_cursor.sort = MagicMock(return_value=jobs_sort)
        mock_db.content_jobs.find = MagicMock(return_value=jobs_cursor)

        # _atomic_claim_card_slot — must return True twice (for 2 cards)
        mock_db.strategist_state.find_one_and_update.return_value = {
            "cards_today_count": 1
        }

        with (
            patch("agents.strategist.db", mock_db),
            patch("agents.strategist.anthropic_available", return_value=True),
            patch("agents.strategist._query_content_gaps", AsyncMock(return_value="")),
            patch("agents.strategist._synthesize_recommendations", AsyncMock(
                return_value=[SAMPLE_CARD, SAMPLE_CARD_2]
            )),
        ):
            from agents.strategist import run_strategist_for_user
            result = await run_strategist_for_user("user_1")

        assert result["cards_written"] == 2
        assert mock_db.strategy_recommendations.insert_one.call_count == 2

    async def test_run_strategist_for_all_users_processes_eligible(self):
        """Mock _get_eligible_users returning 2 IDs. Assert both processed.

        Return dict has total_users=2.
        """
        with (
            patch(
                "agents.strategist._get_eligible_users",
                AsyncMock(return_value=["user_A", "user_B"]),
            ),
            patch(
                "agents.strategist.run_strategist_for_user",
                AsyncMock(return_value={"user_id": "user_A", "cards_written": 1, "skipped_suppressed": 0}),
            ),
        ):
            from agents.strategist import run_strategist_for_all_users
            result = await run_strategist_for_all_users()

        assert result["total_users"] == 2
        assert result["processed"] == 2

    async def test_strategist_skips_users_with_insufficient_content(self):
        """User with approved_count=1 (below threshold=3) not in eligible list."""
        mock_db = _make_mock_db()

        # users.find async iterable returns one user
        user_doc = {"user_id": "low_content_user"}
        mock_db.users.find = MagicMock(
            return_value=_make_async_cursor([user_doc])
        )

        # persona_engines shows approved_count below threshold
        mock_db.persona_engines.find_one.return_value = {
            "learning_signals": {"approved_count": 1}
        }

        with patch("agents.strategist.db", mock_db):
            from agents.strategist import _get_eligible_users
            result = await _get_eligible_users()

        assert "low_content_user" not in result

    async def test_strategist_degrades_gracefully_without_lightrag(self):
        """LightRAG query_knowledge_graph raises Exception — _query_content_gaps catches it
        and returns '' — strategist still produces cards without crashing.
        """
        mock_db = _make_mock_db()
        mock_db.strategist_state.find_one.return_value = {"halved_rate": False}
        mock_db.strategy_recommendations.find = MagicMock(
            return_value=_make_async_cursor([])
        )
        mock_db.persona_engines.find_one.return_value = {
            "user_id": "user_1",
            "card": {"primary_platform": "linkedin"},
            "voice_fingerprint": {"traits": []},
            "content_identity": {"content_pillars": []},
        }
        jobs_sort = MagicMock()
        jobs_sort.to_list = AsyncMock(return_value=[])
        jobs_cursor = MagicMock()
        jobs_cursor.sort = MagicMock(return_value=jobs_sort)
        mock_db.content_jobs.find = MagicMock(return_value=jobs_cursor)
        mock_db.strategist_state.find_one_and_update.return_value = {"cards_today_count": 1}

        async def query_kg_raises(*args, **kwargs):
            raise Exception("LightRAG unavailable")

        mock_lightrag = MagicMock()
        mock_lightrag.query_knowledge_graph = query_kg_raises

        with (
            patch("agents.strategist.db", mock_db),
            patch.dict("sys.modules", {"services.lightrag_service": mock_lightrag}),
            patch("agents.strategist._synthesize_recommendations", AsyncMock(
                return_value=[SAMPLE_CARD]
            )),
        ):
            from agents.strategist import run_strategist_for_user
            # _query_content_gaps catches any Exception from lightrag and returns "" (non-fatal)
            # Must not raise — strategist degrades gracefully
            result = await run_strategist_for_user("user_1")

        assert "cards_written" in result

    async def test_strategist_degrades_gracefully_without_anthropic(self):
        """anthropic_available returns False — _synthesize_recommendations returns []."""
        mock_db = _make_mock_db()

        with (
            patch("agents.strategist.db", mock_db),
            patch("agents.strategist.anthropic_available", return_value=False),
        ):
            from agents.strategist import _synthesize_recommendations
            result = await _synthesize_recommendations("user_1", {}, [])

        assert result == []


# ---------------------------------------------------------------------------
# STRAT-02: TestRecommendationCardSchema
# ---------------------------------------------------------------------------


class TestRecommendationCardSchema:
    """STRAT-02: cards always have status=pending_approval + required fields."""

    async def test_card_always_has_pending_approval_status(self):
        """LLM returns 1 card — inserted document has status='pending_approval'."""
        mock_db = _make_mock_db()
        mock_db.strategist_state.find_one.return_value = {"halved_rate": False}
        mock_db.strategy_recommendations.find = MagicMock(
            return_value=_make_async_cursor([])
        )
        mock_db.persona_engines.find_one.return_value = {
            "card": {}, "voice_fingerprint": {}, "content_identity": {}
        }
        jobs_sort = MagicMock()
        jobs_sort.to_list = AsyncMock(return_value=[])
        jobs_cursor = MagicMock()
        jobs_cursor.sort = MagicMock(return_value=jobs_sort)
        mock_db.content_jobs.find = MagicMock(return_value=jobs_cursor)
        mock_db.strategist_state.find_one_and_update.return_value = {"cards_today_count": 1}

        with (
            patch("agents.strategist.db", mock_db),
            patch("agents.strategist._synthesize_recommendations", AsyncMock(
                return_value=[SAMPLE_CARD]
            )),
        ):
            from agents.strategist import run_strategist_for_user
            await run_strategist_for_user("user_1")

        mock_db.strategy_recommendations.insert_one.assert_called_once()
        doc = mock_db.strategy_recommendations.insert_one.call_args[0][0]
        assert doc["status"] == "pending_approval"

    async def test_card_has_required_fields(self):
        """Inserted document contains all required keys."""
        mock_db = _make_mock_db()
        mock_db.strategist_state.find_one.return_value = {"halved_rate": False}
        mock_db.strategy_recommendations.find = MagicMock(
            return_value=_make_async_cursor([])
        )
        mock_db.persona_engines.find_one.return_value = {
            "card": {}, "voice_fingerprint": {}, "content_identity": {}
        }
        jobs_sort = MagicMock()
        jobs_sort.to_list = AsyncMock(return_value=[])
        jobs_cursor = MagicMock()
        jobs_cursor.sort = MagicMock(return_value=jobs_sort)
        mock_db.content_jobs.find = MagicMock(return_value=jobs_cursor)
        mock_db.strategist_state.find_one_and_update.return_value = {"cards_today_count": 1}

        with (
            patch("agents.strategist.db", mock_db),
            patch("agents.strategist._synthesize_recommendations", AsyncMock(
                return_value=[SAMPLE_CARD]
            )),
        ):
            from agents.strategist import run_strategist_for_user
            await run_strategist_for_user("user_1")

        doc = mock_db.strategy_recommendations.insert_one.call_args[0][0]
        required_keys = {
            "recommendation_id", "user_id", "status", "topic",
            "hook_options", "platform", "why_now", "signal_source",
            "generate_payload", "created_at",
        }
        missing = required_keys - set(doc.keys())
        assert not missing, f"Missing required keys: {missing}"

    def test_strategist_never_imports_pipeline(self):
        """AST check: strategist.py must not import pipeline or content generation functions."""
        import os
        strategist_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "agents", "strategist.py"
        )
        with open(strategist_path) as f:
            source = f.read()
        tree = ast.parse(source)

        forbidden_names = {"pipeline", "create_content", "run_pipeline", "generate_content"}

        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                if isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                    if any(name in module for name in forbidden_names):
                        pytest.fail(
                            f"strategist.py must not import '{module}' — "
                            "agent is write-only for recommendations, not content generation"
                        )
                    for alias in node.names:
                        if alias.name in forbidden_names:
                            pytest.fail(
                                f"strategist.py must not import '{alias.name}'"
                            )


# ---------------------------------------------------------------------------
# STRAT-03: TestWhyNowRationale
# ---------------------------------------------------------------------------


class TestWhyNowRationale:
    """STRAT-03: every card includes a non-empty why_now rationale."""

    async def test_card_has_nonempty_why_now(self):
        """LLM returns card with why_now — inserted doc has non-empty why_now."""
        mock_db = _make_mock_db()
        mock_db.strategist_state.find_one.return_value = {"halved_rate": False}
        mock_db.strategy_recommendations.find = MagicMock(
            return_value=_make_async_cursor([])
        )
        mock_db.persona_engines.find_one.return_value = {
            "card": {}, "voice_fingerprint": {}, "content_identity": {}
        }
        jobs_sort = MagicMock()
        jobs_sort.to_list = AsyncMock(return_value=[])
        jobs_cursor = MagicMock()
        jobs_cursor.sort = MagicMock(return_value=jobs_sort)
        mock_db.content_jobs.find = MagicMock(return_value=jobs_cursor)
        mock_db.strategist_state.find_one_and_update.return_value = {"cards_today_count": 1}

        card_with_why_now = {**SAMPLE_CARD, "why_now": "Why now: trending topic"}

        with (
            patch("agents.strategist.db", mock_db),
            patch("agents.strategist._synthesize_recommendations", AsyncMock(
                return_value=[card_with_why_now]
            )),
        ):
            from agents.strategist import run_strategist_for_user
            await run_strategist_for_user("user_1")

        doc = mock_db.strategy_recommendations.insert_one.call_args[0][0]
        assert doc["why_now"]  # non-empty
        assert isinstance(doc["why_now"], str)

    async def test_card_with_empty_why_now_still_written(self):
        """LLM returns card with empty why_now — card is still written (agent fills in fallback)."""
        mock_db = _make_mock_db()
        mock_db.strategist_state.find_one.return_value = {"halved_rate": False}
        mock_db.strategy_recommendations.find = MagicMock(
            return_value=_make_async_cursor([])
        )
        mock_db.persona_engines.find_one.return_value = {
            "card": {}, "voice_fingerprint": {}, "content_identity": {}
        }
        jobs_sort = MagicMock()
        jobs_sort.to_list = AsyncMock(return_value=[])
        jobs_cursor = MagicMock()
        jobs_cursor.sort = MagicMock(return_value=jobs_sort)
        mock_db.content_jobs.find = MagicMock(return_value=jobs_cursor)
        mock_db.strategist_state.find_one_and_update.return_value = {"cards_today_count": 1}

        card_empty_why_now = {**SAMPLE_CARD, "why_now": ""}

        with (
            patch("agents.strategist.db", mock_db),
            patch("agents.strategist._synthesize_recommendations", AsyncMock(
                return_value=[card_empty_why_now]
            )),
        ):
            from agents.strategist import run_strategist_for_user
            result = await run_strategist_for_user("user_1")

        # Card IS still written — empty why_now triggers fallback, not rejection
        assert result["cards_written"] == 1
        mock_db.strategy_recommendations.insert_one.assert_called_once()
        doc = mock_db.strategy_recommendations.insert_one.call_args[0][0]
        # Fallback must still produce a non-empty why_now
        assert doc["why_now"]


# ---------------------------------------------------------------------------
# STRAT-04: TestCadenceControls
# ---------------------------------------------------------------------------


class TestCadenceControls:
    """STRAT-04: atomic cap guard — max 3 cards per user per day."""

    async def test_max_three_cards_per_user_per_day(self):
        """LLM returns 5 cards; _atomic_claim_card_slot returns True for 3, False for 4th.

        insert_one must be called exactly 3 times (cap hit after 3).
        """
        mock_db = _make_mock_db()
        mock_db.strategist_state.find_one.return_value = {"halved_rate": False}
        mock_db.strategy_recommendations.find = MagicMock(
            return_value=_make_async_cursor([])
        )
        mock_db.persona_engines.find_one.return_value = {
            "card": {}, "voice_fingerprint": {}, "content_identity": {}
        }
        jobs_sort = MagicMock()
        jobs_sort.to_list = AsyncMock(return_value=[])
        jobs_cursor = MagicMock()
        jobs_cursor.sort = MagicMock(return_value=jobs_sort)
        mock_db.content_jobs.find = MagicMock(return_value=jobs_cursor)

        five_cards = [dict(MINIMAL_CARD, topic=f"topic {i}") for i in range(5)]

        # _atomic_claim_card_slot: True for first 3, False for 4th onwards
        slot_results = [
            {"cards_today_count": 1},
            {"cards_today_count": 2},
            {"cards_today_count": 3},
            None,  # cap reached
            None,
        ]
        mock_db.strategist_state.find_one_and_update.side_effect = slot_results

        with (
            patch("agents.strategist.db", mock_db),
            patch("agents.strategist._synthesize_recommendations", AsyncMock(
                return_value=five_cards
            )),
            patch("agents.strategist._is_topic_suppressed", AsyncMock(return_value=False)),
        ):
            from agents.strategist import run_strategist_for_user
            result = await run_strategist_for_user("user_1")

        assert mock_db.strategy_recommendations.insert_one.call_count == 3
        assert result["cards_written"] == 3

    async def test_atomic_claim_slot_returns_false_at_cap(self):
        """find_one_and_update returning None means cap reached — _atomic_claim_card_slot returns False."""
        mock_db = _make_mock_db()
        today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        # Phase 1 fails (cap reached — returns None)
        # Phase 2 also fails (same date — $ne condition false — returns None)
        mock_db.strategist_state.find_one_and_update.return_value = None

        with patch("agents.strategist.db", mock_db):
            from agents.strategist import _atomic_claim_card_slot
            result = await _atomic_claim_card_slot("user_1")

        assert result is False

    async def test_cadence_resets_on_new_day(self):
        """strategist_state with cards_today_date = yesterday — new-day upsert happens."""
        mock_db = _make_mock_db()
        yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")
        today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        # Phase 1 returns None (date doesn't match today)
        # Phase 2 succeeds (upsert for new day)
        call_results = [None, {"cards_today_date": today_str, "cards_today_count": 1}]
        mock_db.strategist_state.find_one_and_update.side_effect = call_results

        with patch("agents.strategist.db", mock_db):
            from agents.strategist import _atomic_claim_card_slot
            result = await _atomic_claim_card_slot("user_1")

        assert result is True
        # Phase 2 call must set cards_today_date to today
        second_call = mock_db.strategist_state.find_one_and_update.call_args_list[1]
        update_doc = second_call[0][1]
        assert update_doc["$set"]["cards_today_date"] == today_str
        assert update_doc["$set"]["cards_today_count"] == 1


# ---------------------------------------------------------------------------
# STRAT-05: TestDismissalTracking
# ---------------------------------------------------------------------------


class TestDismissalTracking:
    """STRAT-05: dismissed topics are suppressed for 14 days."""

    async def test_handle_dismissal_marks_card_dismissed(self):
        """handle_dismissal sets status='dismissed' and dismissed_at on the card."""
        mock_db = _make_mock_db()
        dismissed_card = {
            "recommendation_id": "strat_abc123",
            "user_id": "user_1",
            "status": "dismissed",
            "topic": "ai content",
            "dismissed_at": datetime.now(timezone.utc),
        }
        mock_db.strategy_recommendations.find_one_and_update.return_value = dismissed_card
        mock_db.strategist_state.find_one_and_update.return_value = {
            "consecutive_dismissals": 0,
            "halved_rate": False,
        }

        with patch("agents.strategist.db", mock_db):
            from agents.strategist import handle_dismissal
            result = await handle_dismissal("user_1", "strat_abc123")

        # Verify the update was called with status=dismissed
        update_call = mock_db.strategy_recommendations.find_one_and_update.call_args
        update_doc = update_call[0][1]
        assert update_doc["$set"]["status"] == "dismissed"
        assert "dismissed_at" in update_doc["$set"]
        assert result.get("dismissed") is True

    async def test_handle_dismissal_increments_consecutive_count(self):
        """handle_dismissal calls find_one_and_update with $inc on consecutive_dismissals."""
        mock_db = _make_mock_db()
        mock_db.strategy_recommendations.find_one_and_update.return_value = {
            "topic": "ai content",
            "user_id": "user_1",
        }
        mock_db.strategist_state.find_one_and_update.return_value = {
            "consecutive_dismissals": 1,
            "halved_rate": False,
        }

        with patch("agents.strategist.db", mock_db):
            from agents.strategist import handle_dismissal
            await handle_dismissal("user_1", "strat_abc123")

        state_call = mock_db.strategist_state.find_one_and_update.call_args
        update_doc = state_call[0][1]
        assert update_doc["$inc"]["consecutive_dismissals"] == 1

    async def test_handle_dismissal_returns_suppression_window(self):
        """Return dict has topic_suppressed_until approximately 14 days from now."""
        mock_db = _make_mock_db()
        mock_db.strategy_recommendations.find_one_and_update.return_value = {
            "topic": "ai content",
            "user_id": "user_1",
        }
        mock_db.strategist_state.find_one_and_update.return_value = {
            "consecutive_dismissals": 0,
            "halved_rate": False,
        }

        with patch("agents.strategist.db", mock_db):
            from agents.strategist import handle_dismissal
            result = await handle_dismissal("user_1", "strat_abc123")

        assert "topic_suppressed_until" in result
        suppressed_until = datetime.fromisoformat(result["topic_suppressed_until"])
        expected = datetime.now(timezone.utc) + timedelta(days=14)
        # Within 5 seconds tolerance
        diff = abs((suppressed_until - expected).total_seconds())
        assert diff < 5, f"suppressed_until is off by {diff}s"

    async def test_handle_dismissal_not_found(self):
        """find_one_and_update returns None -> return {'error': 'not_found'}."""
        mock_db = _make_mock_db()
        mock_db.strategy_recommendations.find_one_and_update.return_value = None

        with patch("agents.strategist.db", mock_db):
            from agents.strategist import handle_dismissal
            result = await handle_dismissal("user_1", "nonexistent_rec")

        assert result == {"error": "not_found"}

    async def test_topic_suppression_blocks_recommendation(self):
        """Dismissed card 5 days ago for 'ai content' -> _is_topic_suppressed returns True."""
        mock_db = _make_mock_db()
        five_days_ago = datetime.now(timezone.utc) - timedelta(days=5)
        mock_db.strategy_recommendations.find_one.return_value = {
            "topic": "ai content",
            "status": "dismissed",
            "dismissed_at": five_days_ago,
        }

        with patch("agents.strategist.db", mock_db):
            from agents.strategist import _is_topic_suppressed
            result = await _is_topic_suppressed("user_1", "ai content")

        assert result is True

    async def test_topic_suppression_expires_after_14_days(self):
        """Dismissed card 15 days ago -> _is_topic_suppressed returns False."""
        mock_db = _make_mock_db()
        # find_one returns None when the cutoff excludes the old dismissal
        mock_db.strategy_recommendations.find_one.return_value = None

        with patch("agents.strategist.db", mock_db):
            from agents.strategist import _is_topic_suppressed
            result = await _is_topic_suppressed("user_1", "ai content")

        assert result is False


# ---------------------------------------------------------------------------
# STRAT-06: TestConsecutiveDismissalThreshold
# ---------------------------------------------------------------------------


class TestConsecutiveDismissalThreshold:
    """STRAT-06: 5 consecutive dismissals triggers halved_rate and calibration prompt."""

    async def test_five_dismissals_triggers_halved_rate(self):
        """State has consecutive_dismissals=4, halved_rate=False.

        After handle_dismissal (makes it 5), halved_rate must be set to True.
        """
        mock_db = _make_mock_db()
        mock_db.strategy_recommendations.find_one_and_update.return_value = {
            "topic": "some topic",
            "user_id": "user_1",
        }
        # Return value has consecutive_dismissals=4 (pre-increment value in return_document=True)
        mock_db.strategist_state.find_one_and_update.return_value = {
            "consecutive_dismissals": 4,
            "halved_rate": False,
        }

        with patch("agents.strategist.db", mock_db):
            from agents.strategist import handle_dismissal
            result = await handle_dismissal("user_1", "strat_abc123")

        # update_one should be called to set halved_rate=True
        mock_db.strategist_state.update_one.assert_called_once()
        update_call = mock_db.strategist_state.update_one.call_args
        set_doc = update_call[0][1]["$set"]
        assert set_doc["halved_rate"] is True

    async def test_five_dismissals_sets_needs_calibration_prompt(self):
        """After 5th dismissal, needs_calibration_prompt is set to True."""
        mock_db = _make_mock_db()
        mock_db.strategy_recommendations.find_one_and_update.return_value = {
            "topic": "some topic",
            "user_id": "user_1",
        }
        mock_db.strategist_state.find_one_and_update.return_value = {
            "consecutive_dismissals": 4,
            "halved_rate": False,
        }

        with patch("agents.strategist.db", mock_db):
            from agents.strategist import handle_dismissal
            result = await handle_dismissal("user_1", "strat_abc123")

        update_call = mock_db.strategist_state.update_one.call_args
        set_doc = update_call[0][1]["$set"]
        assert set_doc["needs_calibration_prompt"] is True
        assert result["needs_calibration_prompt"] is True

    async def test_halved_rate_reduces_max_cards(self):
        """strategist_state halved_rate=True -> max_cards becomes 1 (3//2=1).

        LLM returns 3 cards but only 1 is written.
        """
        mock_db = _make_mock_db()
        # cadence state has halved_rate=True
        mock_db.strategist_state.find_one.return_value = {"halved_rate": True}
        mock_db.strategy_recommendations.find = MagicMock(
            return_value=_make_async_cursor([])
        )
        mock_db.persona_engines.find_one.return_value = {
            "card": {}, "voice_fingerprint": {}, "content_identity": {}
        }
        jobs_sort = MagicMock()
        jobs_sort.to_list = AsyncMock(return_value=[])
        jobs_cursor = MagicMock()
        jobs_cursor.sort = MagicMock(return_value=jobs_sort)
        mock_db.content_jobs.find = MagicMock(return_value=jobs_cursor)

        three_cards = [dict(MINIMAL_CARD, topic=f"topic {i}") for i in range(3)]

        # _atomic_claim_card_slot always succeeds
        mock_db.strategist_state.find_one_and_update.return_value = {"cards_today_count": 1}

        with (
            patch("agents.strategist.db", mock_db),
            patch("agents.strategist._synthesize_recommendations", AsyncMock(
                return_value=three_cards
            )),
            patch("agents.strategist._is_topic_suppressed", AsyncMock(return_value=False)),
        ):
            from agents.strategist import run_strategist_for_user
            result = await run_strategist_for_user("user_1")

        # halved_rate: max(1, 3//2) = 1 — only 1 card written
        assert result["cards_written"] == 1
        assert mock_db.strategy_recommendations.insert_one.call_count == 1

    async def test_approval_resets_consecutive_dismissals(self):
        """handle_approval calls update_one resetting consecutive_dismissals, halved_rate, calibration."""
        mock_db = _make_mock_db()
        mock_db.strategy_recommendations.find_one_and_update.return_value = {
            "recommendation_id": "strat_xyz",
            "user_id": "user_1",
            "generate_payload": {"platform": "linkedin", "content_type": "post", "raw_input": "test"},
        }

        with patch("agents.strategist.db", mock_db):
            from agents.strategist import handle_approval
            result = await handle_approval("user_1", "strat_xyz")

        mock_db.strategist_state.update_one.assert_called_once()
        update_call = mock_db.strategist_state.update_one.call_args
        set_doc = update_call[0][1]["$set"]
        assert set_doc["consecutive_dismissals"] == 0
        assert set_doc["halved_rate"] is False
        assert set_doc["needs_calibration_prompt"] is False

    async def test_approval_not_found(self):
        """find_one_and_update returns None -> return {'error': 'not_found'}."""
        mock_db = _make_mock_db()
        mock_db.strategy_recommendations.find_one_and_update.return_value = None

        with patch("agents.strategist.db", mock_db):
            from agents.strategist import handle_approval
            result = await handle_approval("user_1", "nonexistent_rec")

        assert result == {"error": "not_found"}


# ---------------------------------------------------------------------------
# STRAT-07: TestGeneratePayloadSchema
# ---------------------------------------------------------------------------


class TestGeneratePayloadSchema:
    """STRAT-07: generate_payload matches ContentCreateRequest schema."""

    def test_build_generate_payload_has_required_fields(self):
        """_build_generate_payload result has exactly platform, content_type, raw_input."""
        from agents.strategist import _build_generate_payload

        result = _build_generate_payload(SAMPLE_CARD)
        assert "platform" in result
        assert "content_type" in result
        assert "raw_input" in result

    def test_build_generate_payload_maps_correctly(self):
        """Card with platform='x', content_type='thread', raw_input='Write about startups'."""
        from agents.strategist import _build_generate_payload

        card = {
            "topic": "startup growth",
            "platform": "x",
            "generate_payload": {
                "content_type": "thread",
                "raw_input": "Write about startups",
            },
        }
        result = _build_generate_payload(card)
        assert result["platform"] == "x"
        assert result["content_type"] == "thread"
        assert result["raw_input"] == "Write about startups"

    def test_build_generate_payload_defaults(self):
        """Card with only topic -> platform defaults to 'linkedin', content_type to 'post',
        raw_input falls back to topic value.
        """
        from agents.strategist import _build_generate_payload

        card = {"topic": "leadership lessons"}
        result = _build_generate_payload(card)
        assert result["platform"] == "linkedin"
        assert result["content_type"] == "post"
        assert result["raw_input"] == "leadership lessons"

    async def test_approval_returns_generate_payload(self):
        """handle_approval returns dict with generate_payload key containing the card's payload."""
        mock_db = _make_mock_db()
        stored_payload = {
            "platform": "linkedin",
            "content_type": "post",
            "raw_input": "Write about AI in content creation",
        }
        mock_db.strategy_recommendations.find_one_and_update.return_value = {
            "recommendation_id": "strat_xyz",
            "user_id": "user_1",
            "generate_payload": stored_payload,
        }

        with patch("agents.strategist.db", mock_db):
            from agents.strategist import handle_approval
            result = await handle_approval("user_1", "strat_xyz")

        assert result.get("approved") is True
        assert "generate_payload" in result
        assert result["generate_payload"] == stored_payload

    def test_generate_payload_matches_content_route(self):
        """_build_generate_payload keys are a subset of ContentCreateRequest required fields."""
        from agents.strategist import _build_generate_payload

        result = _build_generate_payload(SAMPLE_CARD)
        # ContentCreateRequest requires at minimum: platform, content_type, raw_input
        required_by_route = {"platform", "content_type", "raw_input"}
        assert required_by_route <= set(result.keys()), (
            f"generate_payload is missing fields required by /api/content/generate: "
            f"{required_by_route - set(result.keys())}"
        )
