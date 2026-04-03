"""Tests for media pipeline credit ledger functions.

Verifies:
- _ledger_stage: inserts pending entry before any provider call
- _ledger_update: transitions status (pending→consumed, pending→failed)
- _ledger_check_cap: aggregate sum check against cost cap
- _ledger_skip_remaining: marks all pending entries for job as 'skipped'
"""
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch, call


# ============================================================
# Helper fixtures
# ============================================================

@pytest.fixture
def mock_db():
    """Mock database with media_pipeline_ledger collection."""
    db_mock = MagicMock()
    db_mock.media_pipeline_ledger = MagicMock()
    db_mock.media_pipeline_ledger.insert_one = AsyncMock()
    db_mock.media_pipeline_ledger.update_one = AsyncMock()
    db_mock.media_pipeline_ledger.update_many = AsyncMock()

    # aggregate returns an async cursor — use an async generator helper
    async def _agg_cursor(docs):
        for doc in docs:
            yield doc

    db_mock.media_pipeline_ledger.aggregate = MagicMock(return_value=_agg_cursor([]))
    return db_mock


# ============================================================
# _ledger_stage tests
# ============================================================

class TestLedgerStage:
    """Test 1 — _ledger_stage inserts correct pending document shape."""

    @pytest.mark.asyncio
    async def test_ledger_stage_inserts_pending_document(self):
        """_ledger_stage inserts doc with correct fields and status='pending'."""
        captured_doc = {}

        async def capture_insert(doc):
            captured_doc.update(doc)

        with patch("services.media_orchestrator.db") as mock_db:
            mock_db.media_pipeline_ledger.insert_one = AsyncMock(side_effect=capture_insert)

            from services.media_orchestrator import _ledger_stage

            ledger_id = await _ledger_stage(
                job_id="job_abc",
                user_id="user_123",
                stage="image_generation",
                provider="openai",
                credits=8,
            )

        assert ledger_id is not None
        assert len(ledger_id) > 0

        assert captured_doc["ledger_id"] == ledger_id
        assert captured_doc["job_id"] == "job_abc"
        assert captured_doc["user_id"] == "user_123"
        assert captured_doc["stage"] == "image_generation"
        assert captured_doc["provider"] == "openai"
        assert captured_doc["credits_consumed"] == 8
        assert captured_doc["status"] == "pending"
        assert captured_doc["failure_reason"] is None
        assert isinstance(captured_doc["created_at"], datetime)
        assert captured_doc["completed_at"] is None

    @pytest.mark.asyncio
    async def test_ledger_stage_returns_unique_ids(self):
        """_ledger_stage returns a different ID each call."""
        with patch("services.media_orchestrator.db") as mock_db:
            mock_db.media_pipeline_ledger.insert_one = AsyncMock()

            from services.media_orchestrator import _ledger_stage

            id1 = await _ledger_stage("job1", "user1", "image_generation", "openai", 8)
            id2 = await _ledger_stage("job1", "user1", "voice_generation", "elevenlabs", 12)

        assert id1 != id2

    @pytest.mark.asyncio
    async def test_ledger_stage_called_before_provider(self):
        """Verifies the write-before-call guarantee: insert_one is called before any other action."""
        call_order = []

        async def mock_insert(doc):
            call_order.append("ledger_insert")

        with patch("services.media_orchestrator.db") as mock_db:
            mock_db.media_pipeline_ledger.insert_one = AsyncMock(side_effect=mock_insert)

            from services.media_orchestrator import _ledger_stage

            ledger_id = await _ledger_stage("job_abc", "user_123", "remotion_render", "remotion", 5)
            call_order.append("after_stage")

        assert call_order[0] == "ledger_insert", "Ledger must be written first"
        assert call_order[1] == "after_stage"


# ============================================================
# _ledger_update tests
# ============================================================

class TestLedgerUpdate:
    """Test 2 — _ledger_update transitions status correctly."""

    @pytest.mark.asyncio
    async def test_ledger_update_consumed(self):
        """_ledger_update sets status=consumed and completed_at."""
        filter_used = {}
        update_used = {}

        async def capture_update(filt, upd):
            filter_used.update(filt)
            update_used.update(upd)

        with patch("services.media_orchestrator.db") as mock_db:
            mock_db.media_pipeline_ledger.update_one = AsyncMock(side_effect=capture_update)

            from services.media_orchestrator import _ledger_update

            await _ledger_update("ledger_xyz", "consumed")

        assert filter_used == {"ledger_id": "ledger_xyz"}
        assert update_used["$set"]["status"] == "consumed"
        assert isinstance(update_used["$set"]["completed_at"], datetime)

    @pytest.mark.asyncio
    async def test_ledger_update_failed_with_reason(self):
        """_ledger_update sets status=failed and includes failure_reason."""
        update_used = {}

        async def capture_update(filt, upd):
            update_used.update(upd)

        with patch("services.media_orchestrator.db") as mock_db:
            mock_db.media_pipeline_ledger.update_one = AsyncMock(side_effect=capture_update)

            from services.media_orchestrator import _ledger_update

            await _ledger_update("ledger_xyz", "failed", reason="Provider timeout")

        assert update_used["$set"]["status"] == "failed"
        assert update_used["$set"]["failure_reason"] == "Provider timeout"

    @pytest.mark.asyncio
    async def test_ledger_update_skipped(self):
        """_ledger_update sets status=skipped without requiring a reason."""
        update_used = {}

        async def capture_update(filt, upd):
            update_used.update(upd)

        with patch("services.media_orchestrator.db") as mock_db:
            mock_db.media_pipeline_ledger.update_one = AsyncMock(side_effect=capture_update)

            from services.media_orchestrator import _ledger_update

            await _ledger_update("ledger_xyz", "skipped")

        assert update_used["$set"]["status"] == "skipped"


# ============================================================
# _ledger_check_cap tests
# ============================================================

class TestLedgerCheckCap:
    """Test 3 — _ledger_check_cap aggregates consumed credits correctly."""

    @pytest.mark.asyncio
    async def test_ledger_check_cap_under_limit_returns_true(self):
        """Returns True when consumed credits are below the cap."""
        async def fake_agg(pipeline):
            yield {"_id": None, "total": 20}

        with patch("services.media_orchestrator.db") as mock_db:
            mock_db.media_pipeline_ledger.aggregate = MagicMock(side_effect=lambda p: fake_agg(p))

            from services.media_orchestrator import _ledger_check_cap

            result = await _ledger_check_cap("job_abc", cost_cap=40)

        assert result is True

    @pytest.mark.asyncio
    async def test_ledger_check_cap_at_limit_returns_false(self):
        """Returns False when consumed credits exactly equal the cap."""
        async def fake_agg(pipeline):
            yield {"_id": None, "total": 40}

        with patch("services.media_orchestrator.db") as mock_db:
            mock_db.media_pipeline_ledger.aggregate = MagicMock(side_effect=lambda p: fake_agg(p))

            from services.media_orchestrator import _ledger_check_cap

            result = await _ledger_check_cap("job_abc", cost_cap=40)

        assert result is False

    @pytest.mark.asyncio
    async def test_ledger_check_cap_over_limit_returns_false(self):
        """Returns False when consumed credits exceed the cap."""
        async def fake_agg(pipeline):
            yield {"_id": None, "total": 85}

        with patch("services.media_orchestrator.db") as mock_db:
            mock_db.media_pipeline_ledger.aggregate = MagicMock(side_effect=lambda p: fake_agg(p))

            from services.media_orchestrator import _ledger_check_cap

            result = await _ledger_check_cap("job_abc", cost_cap=80)

        assert result is False

    @pytest.mark.asyncio
    async def test_ledger_check_cap_no_consumed_entries_returns_true(self):
        """Returns True when aggregate returns no results (zero consumed credits)."""
        async def fake_agg(pipeline):
            # Yield nothing — no consumed entries
            return
            yield  # make it a generator

        with patch("services.media_orchestrator.db") as mock_db:
            mock_db.media_pipeline_ledger.aggregate = MagicMock(side_effect=lambda p: fake_agg(p))

            from services.media_orchestrator import _ledger_check_cap

            result = await _ledger_check_cap("job_empty", cost_cap=40)

        assert result is True


# ============================================================
# _ledger_skip_remaining tests
# ============================================================

class TestLedgerSkipRemaining:
    """Test 4 — _ledger_skip_remaining marks all pending entries as skipped."""

    @pytest.mark.asyncio
    async def test_ledger_skip_remaining_marks_all_pending(self):
        """update_many called with correct filter and 'skipped' status."""
        filter_used = {}
        update_used = {}

        async def capture_update(filt, upd):
            filter_used.update(filt)
            update_used.update(upd)

        with patch("services.media_orchestrator.db") as mock_db:
            mock_db.media_pipeline_ledger.update_many = AsyncMock(side_effect=capture_update)

            from services.media_orchestrator import _ledger_skip_remaining

            await _ledger_skip_remaining("job_abc", reason="Provider failed at image_generation")

        # Filter must target pending entries for this job only
        assert filter_used["job_id"] == "job_abc"
        assert filter_used["status"] == "pending"

        # Update must set status=skipped and record reason
        assert update_used["$set"]["status"] == "skipped"
        assert update_used["$set"]["failure_reason"] == "Provider failed at image_generation"
        assert isinstance(update_used["$set"]["completed_at"], datetime)

    @pytest.mark.asyncio
    async def test_ledger_skip_remaining_does_not_affect_consumed(self):
        """update_many filter includes status=pending — consumed entries are not touched."""
        filter_used = {}

        async def capture_update(filt, upd):
            filter_used.update(filt)

        with patch("services.media_orchestrator.db") as mock_db:
            mock_db.media_pipeline_ledger.update_many = AsyncMock(side_effect=capture_update)

            from services.media_orchestrator import _ledger_skip_remaining

            await _ledger_skip_remaining("job_abc", reason="Failed")

        # status=pending in filter ensures consumed entries are not overwritten
        assert filter_used.get("status") == "pending"
