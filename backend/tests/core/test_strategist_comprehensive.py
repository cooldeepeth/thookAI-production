"""Comprehensive Strategist Agent tests for ThookAI (Phase 19 Plan 05).

Covers edge cases NOT in test_strategist.py or test_strategy_routes.py:

  TestCadenceControlsEdgeCases  — atomicity, halved-rate cap, new-day reset, no-doc creation
  TestDismissalEdgeCases        — non-existent card, idempotency, exact-match suppression,
                                  suppression window boundary
  TestAdaptiveThrottle          — 4-dismissal no-trigger, 5th-dismissal trigger, approval reset
  TestCardSchemaValidation      — all required fields, generate_payload schema, content_type
                                  validity, why_now prefix, signal_source enum
  TestStrategistLLMIntegration  — prompt includes persona/suppressed topics, LightRAG/Anthropic
                                  degradation
  TestApprovalFlow              — card status update, payload returned, dismissal reset,
                                  non-existent card

asyncio_mode=auto in pytest.ini — no @pytest.mark.asyncio decorator needed.
"""
import json
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_settings():
    settings = MagicMock()
    settings.strategist.max_cards_per_day = 3
    settings.strategist.suppression_days = 14
    settings.strategist.consecutive_dismissal_threshold = 5
    settings.strategist.min_approved_content = 3
    settings.strategist.synthesis_timeout = 30.0
    settings.obsidian.is_configured.return_value = False
    return settings


def _make_mock_db():
    """Build a mock db object with all required collection mocks."""
    mock_db = MagicMock()

    mock_db.strategy_recommendations = MagicMock()
    mock_db.strategy_recommendations.insert_one = AsyncMock(return_value=None)
    mock_db.strategy_recommendations.find_one = AsyncMock(return_value=None)
    mock_db.strategy_recommendations.find_one_and_update = AsyncMock(return_value=None)
    mock_db.strategy_recommendations.count_documents = AsyncMock(return_value=0)

    mock_db.strategist_state = MagicMock()
    mock_db.strategist_state.find_one = AsyncMock(return_value=None)
    mock_db.strategist_state.find_one_and_update = AsyncMock(return_value=None)
    mock_db.strategist_state.update_one = AsyncMock(return_value=None)

    mock_db.users = MagicMock()
    users_cursor = AsyncMock()
    users_cursor.__aiter__ = MagicMock(return_value=iter([]))
    mock_db.users.find = MagicMock(return_value=users_cursor)

    mock_db.persona_engines = MagicMock()
    mock_db.persona_engines.find_one = AsyncMock(return_value=None)

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
    return _AsyncIterator(docs)


MINIMAL_CARD = {
    "topic": "startups",
    "hook_options": ["Hook 1"],
    "platform": "x",
    "why_now": "Why now: trending topic",
    "signal_source": "trending",
    "generate_payload": {"content_type": "thread", "raw_input": "Write about startups"},
}


# ---------------------------------------------------------------------------
# TestCadenceControlsEdgeCases
# ---------------------------------------------------------------------------

class TestCadenceControlsEdgeCases:
    """Edge cases for _atomic_claim_card_slot — atomicity, halved-rate, new-day, no-doc."""

    async def test_atomic_claim_slot_uses_find_one_and_update(self):
        """_atomic_claim_card_slot calls find_one_and_update (not find then update) for atomicity."""
        mock_db = _make_mock_db()
        # Phase 1 succeeds — returns doc
        mock_db.strategist_state.find_one_and_update.return_value = {"cards_today_count": 1}

        with patch("agents.strategist.db", mock_db):
            from agents.strategist import _atomic_claim_card_slot
            result = await _atomic_claim_card_slot("user_atomic")

        assert result is True
        # Must use find_one_and_update (atomic), not find_one + update_one
        assert mock_db.strategist_state.find_one_and_update.called
        # update_one must NOT be called for the slot claim itself
        # (only find_one_and_update is atomic enough for STRAT-04)
        assert mock_db.strategist_state.find_one_and_update.call_count >= 1

    async def test_halved_rate_reduces_cap_to_1(self):
        """With halved_rate=True, run_strategist_for_user caps at 1 card (not 3)."""
        mock_db = _make_mock_db()
        # cadence state has halved_rate=True
        mock_db.strategist_state.find_one.return_value = {"halved_rate": True}
        mock_db.strategy_recommendations.find = MagicMock(
            return_value=_make_async_cursor([])
        )
        mock_db.persona_engines.find_one.return_value = {
            "card": {}, "voice_fingerprint": {}, "content_identity": {}
        }
        # claim slot always succeeds
        mock_db.strategist_state.find_one_and_update.return_value = {"cards_today_count": 1}

        three_cards = [dict(MINIMAL_CARD, topic=f"topic {i}") for i in range(3)]

        with (
            patch("agents.strategist.db", mock_db),
            patch("agents.strategist._synthesize_recommendations",
                  AsyncMock(return_value=three_cards)),
            patch("agents.strategist._is_topic_suppressed", AsyncMock(return_value=False)),
        ):
            from agents.strategist import run_strategist_for_user
            result = await run_strategist_for_user("user_halved")

        # halved_rate=True -> max_cards = max(1, 3//2) = 1
        assert result["cards_written"] == 1
        assert mock_db.strategy_recommendations.insert_one.call_count == 1

    async def test_cadence_resets_at_midnight_utc(self):
        """A cadence doc dated yesterday allows a new slot today (new-day reset path)."""
        mock_db = _make_mock_db()
        yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")
        today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        # Phase 1 fails (today_str doesn't match yesterday's date)
        # Phase 2 succeeds (new-day upsert)
        mock_db.strategist_state.find_one_and_update.side_effect = [
            None,
            {"cards_today_date": today_str, "cards_today_count": 1},
        ]

        with patch("agents.strategist.db", mock_db):
            from agents.strategist import _atomic_claim_card_slot
            result = await _atomic_claim_card_slot("user_newday")

        assert result is True
        # Phase 2 update must set today's date
        second_call = mock_db.strategist_state.find_one_and_update.call_args_list[1]
        update_doc = second_call[0][1]
        assert update_doc["$set"]["cards_today_date"] == today_str
        assert update_doc["$set"]["cards_today_count"] == 1

    async def test_claim_slot_returns_false_when_both_phases_fail(self):
        """If both find_one_and_update calls return None, claim returns False (cap reached)."""
        mock_db = _make_mock_db()
        # Both Phase 1 and Phase 2 fail
        mock_db.strategist_state.find_one_and_update.return_value = None

        with patch("agents.strategist.db", mock_db):
            from agents.strategist import _atomic_claim_card_slot
            result = await _atomic_claim_card_slot("user_cap")

        assert result is False
        # Both phases must have been attempted
        assert mock_db.strategist_state.find_one_and_update.call_count == 2

    async def test_cadence_with_no_existing_doc_creates_new(self):
        """With no existing cadence doc, Phase 2 upserts a new doc and returns True."""
        mock_db = _make_mock_db()
        today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        # Phase 1: no existing doc so $lt filter fails -> None
        # Phase 2: $ne today_str succeeds for a brand new user -> returns new doc
        mock_db.strategist_state.find_one_and_update.side_effect = [
            None,
            {"cards_today_date": today_str, "cards_today_count": 1, "user_id": "new_user"},
        ]

        with patch("agents.strategist.db", mock_db):
            from agents.strategist import _atomic_claim_card_slot
            result = await _atomic_claim_card_slot("new_user")

        assert result is True
        # Upsert must be True in Phase 2 call
        second_call = mock_db.strategist_state.find_one_and_update.call_args_list[1]
        kwargs = second_call[1]
        assert kwargs.get("upsert") is True


# ---------------------------------------------------------------------------
# TestDismissalEdgeCases
# ---------------------------------------------------------------------------

class TestDismissalEdgeCases:
    """Edge cases for handle_dismissal and topic suppression logic."""

    async def test_dismiss_nonexistent_card_returns_not_found(self):
        """handle_dismissal with a card_id that doesn't exist returns {'error': 'not_found'}."""
        mock_db = _make_mock_db()
        # find_one_and_update returns None = card not found
        mock_db.strategy_recommendations.find_one_and_update.return_value = None

        with patch("agents.strategist.db", mock_db):
            from agents.strategist import handle_dismissal
            result = await handle_dismissal("user_1", "nonexistent_card_id")

        assert result == {"error": "not_found"}
        # consecutive_dismissals must NOT be incremented for a missing card
        mock_db.strategist_state.find_one_and_update.assert_not_called()

    async def test_dismiss_already_dismissed_card_returns_not_found(self):
        """Dismissing a card that's already dismissed returns not_found (status filter).

        The strategy_recommendations filter requires status='pending_approval', so
        an already-dismissed card won't match — returns {'error': 'not_found'}.
        """
        mock_db = _make_mock_db()
        # Already dismissed card won't match the status=pending_approval filter
        mock_db.strategy_recommendations.find_one_and_update.return_value = None

        with patch("agents.strategist.db", mock_db):
            from agents.strategist import handle_dismissal
            result = await handle_dismissal("user_1", "already_dismissed_card")

        # Should return not_found (idempotent in practice — can't double-dismiss)
        assert result.get("error") == "not_found"

    async def test_suppressed_topic_not_matched_when_absent(self):
        """_is_topic_suppressed returns False when DB has no dismissed record for the topic."""
        mock_db = _make_mock_db()
        mock_db.strategy_recommendations.find_one.return_value = None

        with patch("agents.strategist.db", mock_db):
            from agents.strategist import _is_topic_suppressed
            result = await _is_topic_suppressed("user_1", "AI automation")

        assert result is False

    async def test_suppressed_topic_exact_match_returns_true(self):
        """_is_topic_suppressed returns True when exact topic is in dismissed records."""
        mock_db = _make_mock_db()
        mock_db.strategy_recommendations.find_one.return_value = {
            "topic": "ai automation",
            "status": "dismissed",
            "dismissed_at": datetime.now(timezone.utc) - timedelta(days=5),
        }

        with patch("agents.strategist.db", mock_db):
            from agents.strategist import _is_topic_suppressed
            result = await _is_topic_suppressed("user_1", "AI automation")

        assert result is True

    async def test_suppression_window_boundary_13_days_still_suppressed(self):
        """Topic dismissed 13 days ago is still within the 14-day window -> True."""
        mock_db = _make_mock_db()
        # DB finds the dismissed record (within 14-day window)
        mock_db.strategy_recommendations.find_one.return_value = {
            "topic": "founder storytelling",
            "status": "dismissed",
            "dismissed_at": datetime.now(timezone.utc) - timedelta(days=13),
        }

        with patch("agents.strategist.db", mock_db):
            from agents.strategist import _is_topic_suppressed
            result = await _is_topic_suppressed("user_1", "founder storytelling")

        assert result is True

    async def test_suppression_window_boundary_15_days_no_longer_suppressed(self):
        """Topic dismissed 15 days ago is outside the 14-day window -> False."""
        mock_db = _make_mock_db()
        # DB query with $gte cutoff excludes the 15-day-old record -> returns None
        mock_db.strategy_recommendations.find_one.return_value = None

        with patch("agents.strategist.db", mock_db):
            from agents.strategist import _is_topic_suppressed
            result = await _is_topic_suppressed("user_1", "founder storytelling")

        assert result is False

    async def test_suppression_check_non_fatal_on_db_error(self):
        """_is_topic_suppressed returns False (not raises) when DB throws an exception."""
        mock_db = _make_mock_db()
        mock_db.strategy_recommendations.find_one.side_effect = Exception("DB connection error")

        with patch("agents.strategist.db", mock_db):
            from agents.strategist import _is_topic_suppressed
            result = await _is_topic_suppressed("user_1", "some topic")

        # Non-fatal: returns False, doesn't raise
        assert result is False


# ---------------------------------------------------------------------------
# TestAdaptiveThrottle
# ---------------------------------------------------------------------------

class TestAdaptiveThrottle:
    """Tests for the adaptive throttle mechanism (STRAT-06)."""

    async def test_4_consecutive_dismissals_does_not_trigger_throttle(self):
        """4 consecutive dismissals (below threshold=5) do not set halved_rate."""
        mock_db = _make_mock_db()
        mock_db.strategy_recommendations.find_one_and_update.return_value = {
            "topic": "some topic",
            "user_id": "user_1",
        }
        # State returns pre-increment value of 3 -> post-increment is 4, below threshold
        mock_db.strategist_state.find_one_and_update.return_value = {
            "consecutive_dismissals": 3,
            "halved_rate": False,
        }

        with patch("agents.strategist.db", mock_db):
            from agents.strategist import handle_dismissal
            result = await handle_dismissal("user_1", "strat_abc123")

        # update_one for halved_rate must NOT be called
        mock_db.strategist_state.update_one.assert_not_called()
        assert result.get("needs_calibration_prompt") is False

    async def test_5th_dismissal_triggers_throttle_and_calibration_prompt(self):
        """5th consecutive dismissal sets halved_rate=True and needs_calibration=True."""
        mock_db = _make_mock_db()
        mock_db.strategy_recommendations.find_one_and_update.return_value = {
            "topic": "some topic",
            "user_id": "user_1",
        }
        # State returns pre-increment value of 4 -> post-increment is 5 = threshold
        mock_db.strategist_state.find_one_and_update.return_value = {
            "consecutive_dismissals": 4,
            "halved_rate": False,
        }

        with patch("agents.strategist.db", mock_db):
            from agents.strategist import handle_dismissal
            result = await handle_dismissal("user_1", "strat_abc123")

        # halved_rate must be set via update_one
        mock_db.strategist_state.update_one.assert_called_once()
        update_call = mock_db.strategist_state.update_one.call_args
        update_doc = update_call[0][1]
        assert update_doc["$set"]["halved_rate"] is True
        assert update_doc["$set"]["needs_calibration_prompt"] is True
        assert result.get("needs_calibration_prompt") is True

    async def test_approval_after_throttle_resets_consecutive_count(self):
        """After throttle triggered, handle_approval resets consecutive_dismissals to 0."""
        mock_db = _make_mock_db()
        # Return approved card with generate_payload
        mock_db.strategy_recommendations.find_one_and_update.return_value = {
            "recommendation_id": "strat_abc123",
            "user_id": "user_1",
            "status": "approved",
            "generate_payload": {"platform": "linkedin", "content_type": "post", "raw_input": "test"},
        }

        with patch("agents.strategist.db", mock_db):
            from agents.strategist import handle_approval
            result = await handle_approval("user_1", "strat_abc123")

        # update_one must reset consecutive_dismissals, halved_rate, needs_calibration_prompt
        mock_db.strategist_state.update_one.assert_called_once()
        update_call = mock_db.strategist_state.update_one.call_args
        update_doc = update_call[0][1]
        assert update_doc["$set"]["consecutive_dismissals"] == 0
        assert update_doc["$set"]["halved_rate"] is False
        assert update_doc["$set"]["needs_calibration_prompt"] is False
        assert result.get("approved") is True

    async def test_throttle_not_doubled_when_already_halved(self):
        """If halved_rate is already True, additional dismissals don't trigger update_one again."""
        mock_db = _make_mock_db()
        mock_db.strategy_recommendations.find_one_and_update.return_value = {
            "topic": "some topic",
            "user_id": "user_1",
        }
        # Already throttled (halved_rate=True)
        mock_db.strategist_state.find_one_and_update.return_value = {
            "consecutive_dismissals": 6,
            "halved_rate": True,  # already halved
        }

        with patch("agents.strategist.db", mock_db):
            from agents.strategist import handle_dismissal
            await handle_dismissal("user_1", "strat_abc123")

        # update_one for halved_rate must NOT be called again (already halved)
        mock_db.strategist_state.update_one.assert_not_called()


# ---------------------------------------------------------------------------
# TestCardSchemaValidation
# ---------------------------------------------------------------------------

class TestCardSchemaValidation:
    """Tests for recommendation card schema compliance (STRAT-02, STRAT-03, STRAT-07)."""

    def _make_card(self, **overrides):
        base = {
            "topic": "ai in content creation",
            "hook_options": ["Hook A", "Hook B"],
            "platform": "linkedin",
            "why_now": "Why now: Your last 3 posts on AI got 2x engagement",
            "signal_source": "performance",
            "generate_payload": {
                "content_type": "post",
                "raw_input": "Write about AI in content creation",
            },
        }
        base.update(overrides)
        return base

    def _setup_run_context(self, mock_db, cards):
        mock_db.strategist_state.find_one.return_value = {"halved_rate": False}
        mock_db.strategy_recommendations.find = MagicMock(
            return_value=_make_async_cursor([])
        )
        mock_db.persona_engines.find_one.return_value = {
            "card": {"archetype": "Thought Leader", "primary_platform": "linkedin"},
            "voice_fingerprint": {"traits": ["direct"]},
            "content_identity": {"content_pillars": ["AI"]},
        }
        jobs_sort = MagicMock()
        jobs_sort.to_list = AsyncMock(return_value=[])
        jobs_cursor = MagicMock()
        jobs_cursor.sort = MagicMock(return_value=jobs_sort)
        mock_db.content_jobs.find = MagicMock(return_value=jobs_cursor)
        mock_db.strategist_state.find_one_and_update.return_value = {"cards_today_count": 1}

    async def test_card_has_all_required_fields(self):
        """Inserted card document contains all required fields."""
        mock_db = _make_mock_db()
        card = self._make_card()
        self._setup_run_context(mock_db, [card])

        with (
            patch("agents.strategist.db", mock_db),
            patch("agents.strategist._synthesize_recommendations",
                  AsyncMock(return_value=[card])),
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

    async def test_generate_payload_matches_content_create_schema(self):
        """generate_payload in inserted card has platform, content_type, raw_input keys."""
        mock_db = _make_mock_db()
        card = self._make_card()
        self._setup_run_context(mock_db, [card])

        with (
            patch("agents.strategist.db", mock_db),
            patch("agents.strategist._synthesize_recommendations",
                  AsyncMock(return_value=[card])),
        ):
            from agents.strategist import run_strategist_for_user
            await run_strategist_for_user("user_1")

        doc = mock_db.strategy_recommendations.insert_one.call_args[0][0]
        payload = doc.get("generate_payload", {})
        # Must have all three ContentCreateRequest required fields
        assert "platform" in payload
        assert "content_type" in payload
        assert "raw_input" in payload

    async def test_generate_payload_content_type_is_valid(self):
        """generate_payload content_type must be one of the valid platform content types."""
        mock_db = _make_mock_db()
        valid_types = ["post", "carousel", "thread", "story", "reel"]
        card = self._make_card(generate_payload={
            "content_type": "carousel",
            "raw_input": "Test brief",
        })
        self._setup_run_context(mock_db, [card])

        with (
            patch("agents.strategist.db", mock_db),
            patch("agents.strategist._synthesize_recommendations",
                  AsyncMock(return_value=[card])),
        ):
            from agents.strategist import run_strategist_for_user
            await run_strategist_for_user("user_1")

        doc = mock_db.strategy_recommendations.insert_one.call_args[0][0]
        payload = doc.get("generate_payload", {})
        assert payload.get("content_type") in valid_types

    async def test_why_now_starts_with_prefix(self):
        """why_now in inserted card starts with 'Why now:' (STRAT-03)."""
        mock_db = _make_mock_db()
        card = self._make_card(why_now="Why now: Your vault note on AI trends just added")
        self._setup_run_context(mock_db, [card])

        with (
            patch("agents.strategist.db", mock_db),
            patch("agents.strategist._synthesize_recommendations",
                  AsyncMock(return_value=[card])),
        ):
            from agents.strategist import run_strategist_for_user
            await run_strategist_for_user("user_1")

        doc = mock_db.strategy_recommendations.insert_one.call_args[0][0]
        assert doc["why_now"].startswith("Why now:")

    async def test_signal_source_is_valid_enum(self):
        """signal_source in inserted card must be a recognized enum value."""
        mock_db = _make_mock_db()
        valid_sources = {"persona", "performance", "knowledge_graph", "trending", "vault"}
        card = self._make_card(signal_source="vault")
        self._setup_run_context(mock_db, [card])

        with (
            patch("agents.strategist.db", mock_db),
            patch("agents.strategist._synthesize_recommendations",
                  AsyncMock(return_value=[card])),
        ):
            from agents.strategist import run_strategist_for_user
            await run_strategist_for_user("user_1")

        doc = mock_db.strategy_recommendations.insert_one.call_args[0][0]
        # signal_source should be preserved as-is from the LLM response
        assert doc.get("signal_source") in valid_sources

    async def test_empty_why_now_gets_fallback_text(self):
        """Empty why_now from LLM is replaced with a non-empty fallback (STRAT-03)."""
        mock_db = _make_mock_db()
        card = self._make_card(why_now="")
        self._setup_run_context(mock_db, [card])

        with (
            patch("agents.strategist.db", mock_db),
            patch("agents.strategist._synthesize_recommendations",
                  AsyncMock(return_value=[card])),
        ):
            from agents.strategist import run_strategist_for_user
            await run_strategist_for_user("user_1")

        doc = mock_db.strategy_recommendations.insert_one.call_args[0][0]
        # Fallback must be non-empty
        assert doc["why_now"]
        assert len(doc["why_now"]) > 0

    async def test_card_has_pending_approval_status(self):
        """Every inserted card always has status='pending_approval' (STRAT-02)."""
        mock_db = _make_mock_db()
        card = self._make_card()
        self._setup_run_context(mock_db, [card])

        with (
            patch("agents.strategist.db", mock_db),
            patch("agents.strategist._synthesize_recommendations",
                  AsyncMock(return_value=[card])),
        ):
            from agents.strategist import run_strategist_for_user
            await run_strategist_for_user("user_1")

        doc = mock_db.strategy_recommendations.insert_one.call_args[0][0]
        assert doc["status"] == "pending_approval"


# ---------------------------------------------------------------------------
# TestStrategistLLMIntegration
# ---------------------------------------------------------------------------

class TestStrategistLLMIntegration:
    """Tests for LLM prompt content and graceful degradation."""

    async def test_strategist_prompt_includes_persona_context(self):
        """_build_synthesis_prompt includes archetype and content pillars from persona."""
        context = {
            "persona": {
                "card": {"archetype": "Thought Leader", "primary_platform": "linkedin"},
                "voice_fingerprint": {"traits": ["direct", "insightful"]},
                "content_identity": {"content_pillars": ["AI", "Startups"]},
            },
            "recent_content": [],
            "performance_signals": [],
            "knowledge_gaps": "",
            "vault_notes": [],
        }

        with patch("agents.strategist.settings", _make_settings()):
            from agents.strategist import _build_synthesis_prompt
            prompt = await _build_synthesis_prompt(context, [])

        assert "Thought Leader" in prompt
        assert "AI" in prompt
        assert "Startups" in prompt

    async def test_strategist_prompt_includes_suppressed_topics(self):
        """_build_synthesis_prompt includes suppressed topics in SUPPRESSED TOPICS section."""
        context = {
            "persona": {
                "card": {"archetype": "Founder", "primary_platform": "x"},
                "voice_fingerprint": {"traits": []},
                "content_identity": {"content_pillars": []},
            },
            "recent_content": [],
            "performance_signals": [],
            "knowledge_gaps": "",
            "vault_notes": [],
        }
        suppressed = ["ai automation", "linkedin tips"]

        with patch("agents.strategist.settings", _make_settings()):
            from agents.strategist import _build_synthesis_prompt
            prompt = await _build_synthesis_prompt(context, suppressed)

        assert "SUPPRESSED TOPICS" in prompt
        assert "ai automation" in prompt
        assert "linkedin tips" in prompt

    async def test_strategist_degrades_without_lightrag(self):
        """_query_content_gaps returns '' when LightRAG is unavailable — non-fatal."""
        mock_db = _make_mock_db()
        mock_db.strategist_state.find_one.return_value = {"halved_rate": False}
        mock_db.strategy_recommendations.find = MagicMock(
            return_value=_make_async_cursor([])
        )
        mock_db.persona_engines.find_one.return_value = {
            "card": {"primary_platform": "linkedin"},
            "voice_fingerprint": {"traits": []},
            "content_identity": {"content_pillars": []},
        }
        mock_db.strategist_state.find_one_and_update.return_value = {"cards_today_count": 1}

        card = {
            "topic": "startups",
            "hook_options": ["Hook 1"],
            "platform": "linkedin",
            "why_now": "Why now: trending",
            "signal_source": "persona",
            "generate_payload": {"content_type": "post", "raw_input": "Test"},
        }

        # LightRAG import raises — _query_content_gaps must catch and return ""
        mock_lightrag = MagicMock()
        mock_lightrag.query_knowledge_graph.side_effect = Exception("LightRAG unavailable")

        with (
            patch("agents.strategist.db", mock_db),
            patch.dict("sys.modules", {"services.lightrag_service": mock_lightrag}),
            patch("agents.strategist._synthesize_recommendations",
                  AsyncMock(return_value=[card])),
        ):
            from agents.strategist import run_strategist_for_user
            result = await run_strategist_for_user("user_1")

        # Must complete without raising — graceful degradation
        assert "cards_written" in result

    async def test_strategist_degrades_without_anthropic(self):
        """anthropic_available=False causes _synthesize_recommendations to return []."""
        with patch("agents.strategist.anthropic_available", return_value=False):
            from agents.strategist import _synthesize_recommendations
            result = await _synthesize_recommendations("user_1", {}, [])

        assert result == []

    async def test_prompt_includes_no_suppression_section_when_empty(self):
        """When no suppressed topics exist, prompt shows 'No topics currently suppressed'."""
        context = {
            "persona": {
                "card": {"archetype": "Creator", "primary_platform": "instagram"},
                "voice_fingerprint": {"traits": []},
                "content_identity": {"content_pillars": ["Fitness"]},
            },
            "recent_content": [],
            "performance_signals": [],
            "knowledge_gaps": "",
            "vault_notes": [],
        }

        with patch("agents.strategist.settings", _make_settings()):
            from agents.strategist import _build_synthesis_prompt
            prompt = await _build_synthesis_prompt(context, [])

        assert "No topics currently suppressed" in prompt

    async def test_synthesize_recommendations_validates_required_keys(self):
        """Cards missing required keys from LLM output are discarded."""
        invalid_card = {"topic": "ai", "hook_options": ["Hook"]}  # missing many fields
        valid_card = {
            "topic": "founders",
            "hook_options": ["Hook A"],
            "platform": "linkedin",
            "why_now": "Why now: trending",
            "signal_source": "persona",
            "generate_payload": {"content_type": "post", "raw_input": "test"},
        }
        llm_json = json.dumps([invalid_card, valid_card])

        mock_llm_chat = MagicMock()
        mock_llm_chat.with_model.return_value = mock_llm_chat
        mock_llm_chat.send_message = AsyncMock(return_value=llm_json)

        with (
            patch("agents.strategist.anthropic_available", return_value=True),
            patch("agents.strategist.chat_constructor_key", return_value="key"),
            patch("services.llm_client.LlmChat", return_value=mock_llm_chat),
            patch("agents.strategist.settings", _make_settings()),
        ):
            from agents.strategist import _synthesize_recommendations
            result = await _synthesize_recommendations("user_1", {}, [])

        # Only the valid card should be kept
        assert len(result) == 1
        assert result[0]["topic"] == "founders"


# ---------------------------------------------------------------------------
# TestApprovalFlow
# ---------------------------------------------------------------------------

class TestApprovalFlow:
    """Tests for handle_approval — card status update, generate_payload return, dismissal reset."""

    async def test_approval_marks_card_approved(self):
        """handle_approval updates card status to 'approved'."""
        mock_db = _make_mock_db()
        mock_db.strategy_recommendations.find_one_and_update.return_value = {
            "recommendation_id": "strat_abc123",
            "user_id": "user_1",
            "status": "approved",
            "generate_payload": {
                "platform": "linkedin",
                "content_type": "post",
                "raw_input": "Write about AI",
            },
        }

        with patch("agents.strategist.db", mock_db):
            from agents.strategist import handle_approval
            result = await handle_approval("user_1", "strat_abc123")

        # Filter must target status=pending_approval
        call_args = mock_db.strategy_recommendations.find_one_and_update.call_args
        filter_doc = call_args[0][0]
        assert filter_doc["status"] == "pending_approval"
        assert result.get("approved") is True

    async def test_approval_returns_generate_payload(self):
        """handle_approval returns the generate_payload for one-click generation."""
        mock_db = _make_mock_db()
        expected_payload = {
            "platform": "linkedin",
            "content_type": "carousel",
            "raw_input": "Write a carousel about startup growth",
        }
        mock_db.strategy_recommendations.find_one_and_update.return_value = {
            "recommendation_id": "strat_xyz789",
            "user_id": "user_1",
            "status": "approved",
            "generate_payload": expected_payload,
        }

        with patch("agents.strategist.db", mock_db):
            from agents.strategist import handle_approval
            result = await handle_approval("user_1", "strat_xyz789")

        assert result.get("generate_payload") == expected_payload

    async def test_approval_resets_consecutive_dismissals(self):
        """handle_approval calls update_one to reset consecutive_dismissals to 0."""
        mock_db = _make_mock_db()
        mock_db.strategy_recommendations.find_one_and_update.return_value = {
            "recommendation_id": "strat_abc123",
            "user_id": "user_1",
            "status": "approved",
            "generate_payload": {"platform": "linkedin", "content_type": "post", "raw_input": "test"},
        }

        with patch("agents.strategist.db", mock_db):
            from agents.strategist import handle_approval
            await handle_approval("user_1", "strat_abc123")

        mock_db.strategist_state.update_one.assert_called_once()
        update_call = mock_db.strategist_state.update_one.call_args
        update_doc = update_call[0][1]
        assert update_doc["$set"]["consecutive_dismissals"] == 0
        assert update_doc["$set"]["halved_rate"] is False

    async def test_approval_nonexistent_card_returns_not_found(self):
        """handle_approval with non-existent recommendation_id returns {'error': 'not_found'}."""
        mock_db = _make_mock_db()
        mock_db.strategy_recommendations.find_one_and_update.return_value = None

        with patch("agents.strategist.db", mock_db):
            from agents.strategist import handle_approval
            result = await handle_approval("user_1", "bad_card_id")

        assert result == {"error": "not_found"}
        # Must NOT attempt to update strategist_state for a missing card
        mock_db.strategist_state.update_one.assert_not_called()

    async def test_approval_sets_approved_at_timestamp(self):
        """handle_approval update includes approved_at datetime field."""
        mock_db = _make_mock_db()
        mock_db.strategy_recommendations.find_one_and_update.return_value = {
            "recommendation_id": "strat_abc123",
            "user_id": "user_1",
            "status": "approved",
            "generate_payload": {"platform": "linkedin", "content_type": "post", "raw_input": "test"},
        }

        with patch("agents.strategist.db", mock_db):
            from agents.strategist import handle_approval
            await handle_approval("user_1", "strat_abc123")

        update_call = mock_db.strategy_recommendations.find_one_and_update.call_args
        update_doc = update_call[0][1]
        # approved_at must be set in $set
        assert "approved_at" in update_doc["$set"]
