"""
Test scaffold for Phase 31 — Smart Scheduling (SCHD-01 through SCHD-04).

All tests are written against TARGET behavior before implementation.
Tests 1, 4, 5, 6, 7, 8 must FAIL (RED) until Plans 02–04 are implemented.
Tests 2 and 3 MAY PASS (regression guards for already-working heuristics).

SCHD-01: get_optimal_posting_times reads stored optimal_posting_times from persona
SCHD-02: schedule_content inserts per-platform doc into db.scheduled_posts
SCHD-03: GET /schedule/calendar endpoint exists and returns calendar data
SCHD-04: PATCH /schedule/{id}/reschedule endpoint exists and creates new record
"""

import os
import sys
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch, call

import pytest

# ---------------------------------------------------------------------------
# sys.path — identical pattern from test_celery_cutover.py
# ---------------------------------------------------------------------------
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)


# ---------------------------------------------------------------------------
# Helper: build a mock db object with async-capable collections
# ---------------------------------------------------------------------------

def make_mock_db():
    """Return a MagicMock mimicking Motor's async db object."""
    mock_db = MagicMock()

    # persona_engines
    mock_db.persona_engines.find_one = AsyncMock(return_value=None)

    # content_jobs
    mock_db.content_jobs.find_one = AsyncMock(return_value=None)
    mock_db.content_jobs.update_one = AsyncMock(
        return_value=MagicMock(modified_count=1)
    )

    # scheduled_posts
    mock_cursor = MagicMock()
    mock_cursor.to_list = AsyncMock(return_value=[])
    mock_db.scheduled_posts.find = MagicMock(return_value=mock_cursor)
    mock_db.scheduled_posts.find_one = AsyncMock(return_value=None)
    mock_db.scheduled_posts.insert_many = AsyncMock(
        return_value=MagicMock(inserted_ids=["id1"])
    )
    mock_db.scheduled_posts.insert_one = AsyncMock(
        return_value=MagicMock(inserted_id="id1")
    )
    mock_db.scheduled_posts.update_one = AsyncMock(
        return_value=MagicMock(modified_count=1)
    )

    return mock_db


# ===========================================================================
# SCHD-01 — Optimal times wiring to stored persona data
# ===========================================================================


class TestOptimalTimesWiring:
    """Tests for get_optimal_posting_times reading stored optimal_posting_times.

    BUG (current): function reads persona.uom but NOT persona.optimal_posting_times.
    Tests 1 FAILS until the fix in Plan 02 is applied.
    Tests 2 and 3 may already PASS (regression guards).
    """

    @pytest.mark.asyncio
    async def test_optimal_times_uses_stored_data(self):
        """
        SCHD-01: When a persona has optimal_posting_times stored,
        get_optimal_posting_times must use that data and return a reason
        that references engagement data or 'based on your data'.

        Currently FAILS — function ignores optimal_posting_times entirely.
        """
        persona_with_stored_times = {
            "user_id": "u1",
            "uom": {"burnout_risk": "low"},
            "optimal_posting_times": {
                "linkedin": [
                    {
                        "day_of_week": 2,  # Wednesday
                        "hour": 9,
                        "avg_engagement_rate": 0.08,
                        "post_count": 5,
                    }
                ]
            },
        }

        mock_db = make_mock_db()
        mock_db.persona_engines.find_one = AsyncMock(
            return_value=persona_with_stored_times
        )

        with patch("database.db", mock_db):
            from agents.planner import get_optimal_posting_times

            result = await get_optimal_posting_times(
                user_id="u1",
                platform="linkedin",
                num_suggestions=3,
            )

        # After the fix, at least one suggestion must reflect the stored data:
        # either the reason mentions engagement/data, OR a dedicated flag is set.
        assert "best_times" in result, "result must have 'best_times' key"
        assert len(result["best_times"]) >= 1, "must return at least one suggestion"

        reasons = [t.get("reason", "") for t in result["best_times"]]
        sources = [t.get("source", "") for t in result["best_times"]]

        # After the fix, stored data must be evidenced by:
        # - reason explicitly mentioning "your data" / "historical" / "based on your"
        #   (NOT the generic "peak engagement time for professionals" from heuristics)
        # OR a source field set to "stored" / "historical"
        # OR a dedicated flag (e.g., data_driven=True) on the suggestion or result
        has_data_reason = any(
            "based on your data" in r.lower()
            or "your data" in r.lower()
            or "historical" in r.lower()
            or "your posting history" in r.lower()
            for r in reasons
        )
        has_data_source = any("stored" in s or "historical" in s for s in sources)
        has_data_flag = result.get("data_driven") is True or any(
            t.get("data_driven") is True or t.get("source") in ("stored", "historical")
            for t in result["best_times"]
        )

        assert has_data_reason or has_data_source or has_data_flag, (
            f"Expected stored engagement data to drive at least one suggestion. "
            f"Reasons: {reasons}. Sources: {sources}. result keys: {list(result.keys())}. "
            "The generic 'peak engagement time for professionals' heuristic reason does NOT count. "
            "Fix: planner.get_optimal_posting_times must read optimal_posting_times from persona "
            "and produce a reason/flag distinct from the PLATFORM_PEAKS heuristic path."
        )

    @pytest.mark.asyncio
    async def test_optimal_times_falls_back_to_heuristics_when_no_stored_data(self):
        """
        SCHD-01 regression guard: When no optimal_posting_times stored,
        function must fall back to PLATFORM_PEAKS heuristics and return >= 1 suggestion.

        This SHOULD already PASS (heuristics already work).
        """
        persona_no_stored = {
            "user_id": "u1",
            "uom": {"burnout_risk": "low"},
            # no optimal_posting_times key
        }

        mock_db = make_mock_db()
        mock_db.persona_engines.find_one = AsyncMock(return_value=persona_no_stored)

        with patch("database.db", mock_db):
            from agents.planner import get_optimal_posting_times

            result = await get_optimal_posting_times(
                user_id="u1",
                platform="linkedin",
                num_suggestions=3,
            )

        assert len(result["best_times"]) >= 1, (
            "Heuristic fallback must return at least 1 suggestion when no stored data."
        )
        assert result["platform"] == "linkedin", (
            "Result must echo back the requested platform."
        )

    @pytest.mark.asyncio
    async def test_optimal_times_returns_correct_count(self):
        """
        SCHD-01 regression guard: num_suggestions=3 must return exactly 3 slots
        (cold-start persona, low burnout).

        This SHOULD already PASS.
        """
        persona_no_stored = {
            "user_id": "u1",
            "uom": {"burnout_risk": "low"},
        }

        mock_db = make_mock_db()
        mock_db.persona_engines.find_one = AsyncMock(return_value=persona_no_stored)

        with patch("database.db", mock_db):
            from agents.planner import get_optimal_posting_times

            result = await get_optimal_posting_times(
                user_id="u1",
                platform="x",
                num_suggestions=3,
            )

        assert len(result["best_times"]) == 3, (
            f"Expected exactly 3 suggestions, got {len(result['best_times'])}. "
            "num_suggestions param must be respected for cold-start users."
        )


# ===========================================================================
# SCHD-02 / SCHD-04 — schedule_content inserts into scheduled_posts
# ===========================================================================


class TestScheduleContentCreatesScheduledPosts:
    """Tests that schedule_content writes to db.scheduled_posts.

    BUG (current): schedule_content only updates content_jobs, never inserts
    into scheduled_posts.  The _process_scheduled_posts task therefore finds
    nothing to publish.

    Tests 4 and 5 FAIL until Plan 03 fix is applied.
    """

    @pytest.mark.asyncio
    async def test_schedule_content_creates_scheduled_posts_doc(self):
        """
        SCHD-02: schedule_content must insert a document into db.scheduled_posts
        for each platform.  Single-platform case.

        Currently FAILS — schedule_content never calls insert_many.
        """
        mock_db = make_mock_db()
        mock_db.content_jobs.update_one = AsyncMock(
            return_value=MagicMock(modified_count=1)
        )

        inserted_docs = []

        async def capture_insert_many(docs):
            inserted_docs.extend(docs)
            return MagicMock(inserted_ids=[f"id_{i}" for i in range(len(docs))])

        mock_db.scheduled_posts.insert_many = capture_insert_many

        future_time = datetime.now(timezone.utc) + timedelta(hours=2)

        with patch("database.db", mock_db):
            from agents.planner import schedule_content

            result = await schedule_content(
                user_id="u1",
                job_id="j1",
                scheduled_at=future_time,
                platforms=["linkedin"],
            )

        assert result.get("scheduled") is True, (
            f"schedule_content should return scheduled=True. Got: {result}"
        )
        assert len(inserted_docs) == 1, (
            f"Expected 1 doc inserted into scheduled_posts, got {len(inserted_docs)}. "
            "Fix: schedule_content must call db.scheduled_posts.insert_many."
        )

        doc = inserted_docs[0]
        assert doc.get("schedule_id", "").startswith("sch_"), (
            f"schedule_id must start with 'sch_', got: {doc.get('schedule_id')}"
        )
        assert doc.get("user_id") == "u1", (
            f"user_id mismatch in scheduled_posts doc: {doc.get('user_id')}"
        )
        assert doc.get("job_id") == "j1", (
            f"job_id mismatch in scheduled_posts doc: {doc.get('job_id')}"
        )
        assert doc.get("status") == "scheduled", (
            f"status must be 'scheduled', got: {doc.get('status')}"
        )

    @pytest.mark.asyncio
    async def test_schedule_content_one_doc_per_platform(self):
        """
        SCHD-02: For multiple platforms, insert_many must receive one doc per platform.

        Currently FAILS.
        """
        mock_db = make_mock_db()
        mock_db.content_jobs.update_one = AsyncMock(
            return_value=MagicMock(modified_count=1)
        )

        inserted_docs = []

        async def capture_insert_many(docs):
            inserted_docs.extend(docs)
            return MagicMock(inserted_ids=[f"id_{i}" for i in range(len(docs))])

        mock_db.scheduled_posts.insert_many = capture_insert_many

        future_time = datetime.now(timezone.utc) + timedelta(hours=2)

        with patch("database.db", mock_db):
            from agents.planner import schedule_content

            result = await schedule_content(
                user_id="u1",
                job_id="j1",
                scheduled_at=future_time,
                platforms=["linkedin", "x"],
            )

        assert result.get("scheduled") is True, (
            f"schedule_content should return scheduled=True. Got: {result}"
        )
        assert len(inserted_docs) == 2, (
            f"Expected 2 docs (one per platform), got {len(inserted_docs)}. "
            "Fix: insert one scheduled_posts doc per platform."
        )

        platforms_in_docs = {doc.get("platform") for doc in inserted_docs}
        assert platforms_in_docs == {"linkedin", "x"}, (
            f"Expected platform values {{'linkedin', 'x'}}, got: {platforms_in_docs}"
        )


# ===========================================================================
# SCHD-03 — Calendar endpoint
# ===========================================================================


class TestCalendarEndpoint:
    """Tests for GET /api/dashboard/schedule/calendar.

    Endpoint does not exist yet — tests 6 and 7 FAIL until Plan 04.
    """

    def _make_test_client(self):
        """Build isolated FastAPI test app with dashboard router mounted."""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from routes.dashboard import router
        from auth_utils import get_current_user

        test_app = FastAPI()
        test_app.include_router(router, prefix="/api")
        test_app.dependency_overrides[get_current_user] = lambda: {"user_id": "u1"}
        return TestClient(test_app)

    def test_calendar_endpoint_exists(self):
        """
        SCHD-03: GET /api/dashboard/schedule/calendar?year=2026&month=4 must return 200
        with a 'posts' key in the response body.

        Currently FAILS — endpoint does not exist (returns 404 or 422).
        """
        mock_db = make_mock_db()

        with patch("database.db", mock_db):
            client = self._make_test_client()
            response = client.get(
                "/api/dashboard/schedule/calendar",
                params={"year": 2026, "month": 4},
            )

        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}. "
            "Fix: add GET /schedule/calendar endpoint to dashboard router."
        )
        body = response.json()
        assert "posts" in body, (
            f"Response must contain 'posts' key. Got keys: {list(body.keys())}"
        )

    def test_calendar_endpoint_month_filter(self):
        """
        SCHD-03: Calendar endpoint must filter by year/month and echo them back.

        Currently FAILS — endpoint does not exist.
        """
        mock_db = make_mock_db()
        # find() returns async cursor with empty list
        mock_cursor = MagicMock()
        mock_cursor.to_list = AsyncMock(return_value=[])
        mock_db.scheduled_posts.find = MagicMock(return_value=mock_cursor)

        with patch("database.db", mock_db):
            client = self._make_test_client()
            response = client.get(
                "/api/dashboard/schedule/calendar",
                params={"year": 2026, "month": 4},
            )

        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}. Endpoint may not exist yet."
        )

        body = response.json()
        assert body.get("year") == 2026, (
            f"Response must echo back year=2026. Got: {body.get('year')}"
        )
        assert body.get("month") == 4, (
            f"Response must echo back month=4. Got: {body.get('month')}"
        )


# ===========================================================================
# SCHD-02 reschedule — PATCH /schedule/{id}/reschedule
# ===========================================================================


class TestRescheduleEndpoint:
    """Test for PATCH /api/dashboard/schedule/{schedule_id}/reschedule.

    Endpoint does not exist yet — test 8 FAILS until Plan 04.
    """

    def _make_test_client(self):
        """Build isolated FastAPI test app with dashboard router mounted."""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from routes.dashboard import router
        from auth_utils import get_current_user

        test_app = FastAPI()
        test_app.include_router(router, prefix="/api")
        test_app.dependency_overrides[get_current_user] = lambda: {"user_id": "u1"}
        return TestClient(test_app)

    def test_reschedule_creates_new_record(self):
        """
        SCHD-02: PATCH /schedule/sch_abc123/reschedule must:
        1. Cancel the old scheduled_posts doc (update status to 'cancelled')
        2. Insert a new scheduled_posts doc with a different schedule_id
        3. Return 200

        Currently FAILS — endpoint does not exist.
        """
        existing_doc = {
            "schedule_id": "sch_abc123",
            "user_id": "u1",
            "job_id": "j1",
            "platform": "linkedin",
            "status": "scheduled",
            "scheduled_at": datetime.now(timezone.utc) + timedelta(hours=1),
        }

        mock_db = make_mock_db()
        mock_db.scheduled_posts.find_one = AsyncMock(return_value=existing_doc)
        mock_db.scheduled_posts.update_one = AsyncMock(
            return_value=MagicMock(modified_count=1)
        )
        mock_db.scheduled_posts.insert_one = AsyncMock(
            return_value=MagicMock(inserted_id="new_id")
        )
        mock_db.content_jobs.update_one = AsyncMock(
            return_value=MagicMock(modified_count=1)
        )

        new_time = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()

        with patch("database.db", mock_db):
            client = self._make_test_client()
            response = client.patch(
                "/api/dashboard/schedule/sch_abc123/reschedule",
                json={"new_scheduled_at": new_time},
            )

        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}. "
            "Fix: add PATCH /schedule/{schedule_id}/reschedule endpoint."
        )

        # Verify old doc was cancelled
        cancel_calls = mock_db.scheduled_posts.update_one.call_args_list
        cancelled = any(
            call_args.args
            and len(call_args.args) >= 2
            and call_args.args[1].get("$set", {}).get("status") == "cancelled"
            for call_args in cancel_calls
        )
        assert cancelled, (
            "update_one must be called with status='cancelled' to cancel the old record. "
            f"Actual calls: {cancel_calls}"
        )

        # Verify new doc was inserted
        assert mock_db.scheduled_posts.insert_one.called, (
            "insert_one must be called to create a new scheduled_posts record."
        )
        new_doc_args = mock_db.scheduled_posts.insert_one.call_args
        if new_doc_args and new_doc_args.args:
            new_doc = new_doc_args.args[0]
            assert new_doc.get("schedule_id") != "sch_abc123", (
                f"New record must have a different schedule_id. Got: {new_doc.get('schedule_id')}"
            )
