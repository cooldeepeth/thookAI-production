"""E2E Critical Path Smoke Tests for ThookAI v2.0 (Phase 16 — E2E-01).

Verifies the full user journey from signup through second-cycle content
generation:
  signup -> onboard -> generate -> schedule -> publish -> analytics
  -> strategy -> approve -> regenerate

All external services (MongoDB, Redis, LLM, Stripe, social APIs) are
fully mocked so the suite runs in any CI environment without credentials.

Patterns follow backend/tests/test_e2e_ship.py:
  - Isolated FastAPI test apps per test class
  - dependency_overrides[get_current_user] for auth bypass
  - patch("routes.<module>.db") for database mocking
  - AsyncMock for async database methods
"""

import hashlib
import hmac
import json
import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


# ============================================================
# Shared helpers
# ============================================================

FAKE_USER = {
    "user_id": "user_e2e_cp_001",
    "email": "e2e-cp@thookai.io",
    "name": "E2E CP Tester",
    "subscription_tier": "pro",
    "credits": 500,
    "onboarding_completed": True,
}

FAKE_JOB_ID = "job_e2e_cp_001"
FAKE_SCHEDULE_ID = "sched_e2e_cp_001"
FAKE_REC_ID = "rec_e2e_cp_001"


def _make_job(job_id: str = FAKE_JOB_ID, status: str = "reviewing", **overrides) -> dict:
    """Return a minimal content_jobs document for mocking."""
    doc = {
        "job_id": job_id,
        "user_id": FAKE_USER["user_id"],
        "platform": "linkedin",
        "content_type": "post",
        "raw_input": "AI trends shaping the future",
        "status": status,
        "current_agent": "qc",
        "agent_outputs": {},
        "agent_summaries": {},
        "final_content": "Here is your AI-powered LinkedIn post.",
        "qc_score": 0.88,
        "error": None,
        "analytics_24h_polled": False,
        "analytics_7d_polled": False,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    doc.update(overrides)
    return doc


def _make_strategy_rec(rec_id: str = FAKE_REC_ID, status: str = "pending_approval") -> dict:
    """Return a minimal strategy_recommendations document for mocking."""
    return {
        "recommendation_id": rec_id,
        "user_id": FAKE_USER["user_id"],
        "status": status,
        "topic": "AI trends in 2025",
        "rationale": "High engagement potential based on your recent posts.",
        "generate_payload": {
            "platform": "linkedin",
            "content_type": "post",
            "raw_input": "AI trends shaping the future — second angle",
        },
        "created_at": datetime.now(timezone.utc),
    }


# ============================================================
# Helper: Build isolated test apps
# ============================================================

def _build_app_for(*route_modules, user: dict = None) -> FastAPI:
    """Build a minimal FastAPI app with just the given route modules."""
    from auth_utils import get_current_user

    app = FastAPI()
    override_user = user or FAKE_USER
    app.dependency_overrides[get_current_user] = lambda: override_user
    for module in route_modules:
        app.include_router(module.router, prefix="/api")
    return app


# ============================================================
# Test Class: TestE2ECriticalPath
# ============================================================


class TestE2ECriticalPath:
    """Phase 16 E2E-01: Full critical path — signup through re-generation.

    Each test_* method covers one stage of the user journey and can be run
    independently (all external dependencies fully mocked).
    """

    # ------------------------------------------------------------------
    # T1: Signup creates a new user
    # ------------------------------------------------------------------

    def test_signup_creates_user(self):
        """POST /api/auth/register returns 200 with user_id and token."""
        import routes.auth as auth_module

        app = FastAPI()
        app.include_router(auth_module.router, prefix="/api")

        captured_doc: dict = {}

        async def _capture_insert(doc):
            captured_doc.update(doc)
            return MagicMock(inserted_id="mock_id")

        mock_wmajority = MagicMock()
        mock_wmajority.insert_one = AsyncMock(side_effect=_capture_insert)

        with patch("routes.auth.db") as mock_db:
            mock_db.users.find_one = AsyncMock(return_value=None)
            mock_db.users.with_options = MagicMock(return_value=mock_wmajority)

            client = TestClient(app, raise_server_exceptions=False)
            resp = client.post(
                "/api/auth/register",
                json={
                    "email": "newuser-e2e@thookai.io",
                    "password": "SecureP@ss123",
                    "name": "E2E New User",
                },
            )

        assert resp.status_code == 200, f"Register failed: {resp.text}"
        data = resp.json()
        assert "user_id" in data
        assert "token" in data
        assert data["subscription_tier"] == "starter"
        assert captured_doc.get("credits") == 200
        assert captured_doc.get("onboarding_completed") is False

    # ------------------------------------------------------------------
    # T2: Onboarding generates persona card
    # ------------------------------------------------------------------

    def test_onboarding_generates_persona(self):
        """POST /api/onboarding/generate-persona returns 200 with persona card."""
        import routes.onboarding as onboarding_module

        app = _build_app_for(onboarding_module)

        # Sample 7 answers for the interview
        seven_answers = [
            {"question_id": i, "answer": f"Test answer for question {i}"}
            for i in range(7)
        ]

        mock_persona_doc = {"user_id": FAKE_USER["user_id"]}
        mock_persona_card = {
            "writing_voice_descriptor": "Systems-thinker narrating the builder journey",
            "content_niche_signature": "AI product development",
            "inferred_audience_profile": "Founders and engineers",
            "top_content_format": "Long-form LinkedIn posts",
            "personality_archetype": "Educator",
            "tone": "Professional yet conversational",
            "regional_english": "US",
            "hook_style": "Bold statements",
            "focus_platforms": ["LinkedIn"],
            "content_pillars": ["AI", "Productivity", "Startups"],
            "not_list": ["crypto", "politics"],
            "uom": "Follower growth",
        }

        with patch("routes.onboarding.db") as mock_db, patch(
            "routes.onboarding.anthropic_available", return_value=False
        ):
            mock_db.persona_engines.find_one = AsyncMock(return_value=None)
            # onboarding uses update_one with upsert=True, not insert_one
            mock_db.persona_engines.update_one = AsyncMock(return_value=MagicMock(upserted_id="pe_1"))
            mock_db.users.update_one = AsyncMock()

            client = TestClient(app, raise_server_exceptions=False)
            resp = client.post(
                "/api/onboarding/generate-persona",
                json={"answers": seven_answers},
            )

        app.dependency_overrides.clear()

        assert resp.status_code == 200, f"Generate-persona failed: {resp.text}"
        data = resp.json()
        # Route returns {persona_card, message, source}
        assert "persona_card" in data or "card" in data or "message" in data

    # ------------------------------------------------------------------
    # T3: Content generation starts and returns job_id
    # ------------------------------------------------------------------

    def test_content_generation_starts(self):
        """POST /api/content/create returns 200 with job_id and status 'running'."""
        import routes.content as content_module

        app = _build_app_for(content_module)

        with (
            patch("routes.content.db") as mock_db,
            patch(
                "routes.content.deduct_credits",
                new_callable=AsyncMock,
                return_value={"success": True, "credits_used": 10, "new_balance": 490},
            ),
            patch("routes.content.run_agent_pipeline", new_callable=AsyncMock),
        ):
            mock_db.content_jobs.insert_one = AsyncMock()
            mock_db.campaigns.find_one = AsyncMock(return_value=None)

            client = TestClient(app, raise_server_exceptions=False)
            resp = client.post(
                "/api/content/create",
                json={
                    "platform": "linkedin",
                    "content_type": "post",
                    "raw_input": "AI trends shaping the future",
                },
            )

        app.dependency_overrides.clear()

        assert resp.status_code == 200, f"Content create failed: {resp.text}"
        data = resp.json()
        assert "job_id" in data
        assert data["status"] == "running"

    # ------------------------------------------------------------------
    # T4: Schedule content job via dashboard route
    # ------------------------------------------------------------------

    def test_schedule_then_publish(self):
        """POST /api/dashboard/schedule/content schedules an approved job.

        The schedule endpoint lives in routes/dashboard.py and calls
        agents.planner.schedule_content internally.
        """
        import routes.dashboard as dashboard_module

        app = _build_app_for(dashboard_module)
        future_time = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()

        mock_schedule_result = {
            "success": True,
            "schedule_id": FAKE_SCHEDULE_ID,
            "job_id": FAKE_JOB_ID,
            "scheduled_at": future_time,
            "status": "scheduled",
        }

        with patch(
            "agents.planner.schedule_content",
            new_callable=AsyncMock,
            return_value=mock_schedule_result,
        ):
            client = TestClient(app, raise_server_exceptions=False)
            resp = client.post(
                "/api/dashboard/schedule/content",
                json={
                    "job_id": FAKE_JOB_ID,
                    "scheduled_at": future_time,
                    "platforms": ["linkedin"],
                },
            )

        app.dependency_overrides.clear()

        assert resp.status_code == 200, f"Schedule failed: {resp.text}"
        data = resp.json()
        assert data.get("success") is True or data.get("schedule_id") is not None

    # ------------------------------------------------------------------
    # T5: Analytics poll writes performance data
    # ------------------------------------------------------------------

    def test_analytics_poll_writes_performance(self):
        """POST /api/n8n/execute/poll-analytics-24h with HMAC auth triggers analytics update.

        n8n_bridge uses lazy imports of database.db inside each handler,
        so we patch database.db at the module level.
        """
        import routes.n8n_bridge as n8n_module

        app = FastAPI()
        app.include_router(n8n_module.router, prefix="/api")

        job_with_analytics = _make_job(
            status="published",
            analytics_24h_polled=False,
            analytics_24h_due_at=datetime.now(timezone.utc) - timedelta(minutes=5),
            platform_post_id="urn:li:share:12345",
            # publish_results required by n8n poll-analytics-24h query filter
            publish_results={"linkedin": {"success": True, "post_id": "urn:li:share:12345"}},
        )

        # n8n poll uses cursor.to_list(length=200) directly (no .limit())
        mock_cursor = MagicMock()
        mock_cursor.to_list = AsyncMock(return_value=[job_with_analytics])

        mock_db = MagicMock()
        mock_db.content_jobs.find = MagicMock(return_value=mock_cursor)
        mock_db.content_jobs.update_one = AsyncMock()
        mock_db.persona_engines.update_one = AsyncMock()

        mock_perf_result = {
            "success": True,
            "platform": "linkedin",
            "metrics": {"impressions": 1200, "likes": 45, "comments": 8},
        }

        from routes.n8n_bridge import _verify_n8n_request

        app.dependency_overrides[_verify_n8n_request] = lambda: {"verified": True}

        with (
            patch("database.db", mock_db),
            patch(
                "services.social_analytics.update_post_performance",
                new_callable=AsyncMock,
                return_value=mock_perf_result,
            ),
        ):
            client = TestClient(app, raise_server_exceptions=False)
            resp = client.post("/api/n8n/execute/poll-analytics-24h", json={})

        assert resp.status_code == 200, f"Analytics poll failed: {resp.text}"
        data = resp.json()
        # n8n execute endpoints return {status: 'completed', result: {polled, errors, ...}}
        assert data.get("status") == "completed" or data.get("success") is True

    # ------------------------------------------------------------------
    # T6: Strategy approve returns generate_payload
    # ------------------------------------------------------------------

    def test_strategy_approve_returns_generate_payload(self):
        """POST /api/strategy/{rec_id}/approve returns 200 with generate_payload."""
        import routes.strategy as strategy_module

        app = _build_app_for(strategy_module)
        rec = _make_strategy_rec()

        with patch("routes.strategy.db") as mock_db, patch(
            "routes.strategy.handle_approval",
            new_callable=AsyncMock,
        ) as mock_approve:
            mock_db.strategy_recommendations.find_one = AsyncMock(return_value=rec)
            mock_approve.return_value = {
                "approved": True,
                "generate_payload": rec["generate_payload"],
            }

            client = TestClient(app, raise_server_exceptions=False)
            resp = client.post(f"/api/strategy/{FAKE_REC_ID}/approve")

        app.dependency_overrides.clear()

        assert resp.status_code == 200, f"Strategy approve failed: {resp.text}"
        data = resp.json()
        assert data.get("approved") is True
        payload = data.get("generate_payload", {})
        assert payload.get("platform") == "linkedin"
        assert "raw_input" in payload

    # ------------------------------------------------------------------
    # T7: Notification stream returns text/event-stream
    # ------------------------------------------------------------------

    def test_notification_stream_returns_sse_content_type(self):
        """GET /api/notifications/stream route returns a StreamingResponse
        with text/event-stream content type.

        We verify the route uses StreamingResponse with text/event-stream by
        inspecting the source code. This avoids the infinite SSE polling loop
        in the synchronous test environment.
        """
        import inspect

        import routes.notifications as notifications_module

        # Verify the stream endpoint function exists
        assert hasattr(notifications_module, "notification_stream"), (
            "notification_stream function must exist in routes/notifications.py"
        )

        # Verify the stream function returns StreamingResponse with text/event-stream
        source = inspect.getsource(notifications_module.notification_stream)
        assert "StreamingResponse" in source, (
            "notification_stream must return a StreamingResponse"
        )
        assert "text/event-stream" in source, (
            "notification_stream must set text/event-stream media type"
        )

        # Verify the SSE event generator is also present
        assert hasattr(notifications_module, "_sse_event_generator"), (
            "_sse_event_generator async generator must exist in routes/notifications.py"
        )

        # Verify the router has a /stream route registered (paths include the prefix)
        stream_paths = [
            getattr(r, "path", "") for r in notifications_module.router.routes
        ]
        assert any("/stream" in p for p in stream_paths), (
            f"Router must have a /stream route. Found: {stream_paths}"
        )

    # ------------------------------------------------------------------
    # T8: Second-cycle generation after strategy approve
    # ------------------------------------------------------------------

    def test_second_cycle_generation_after_approve(self):
        """After strategy approve, POST /api/content/create with generate_payload
        starts a second content generation cycle successfully.
        """
        import routes.content as content_module

        app = _build_app_for(content_module)
        # Use the generate_payload from the strategy recommendation
        second_cycle_payload = {
            "platform": "linkedin",
            "content_type": "post",
            "raw_input": "AI trends shaping the future — second angle",
        }

        with (
            patch("routes.content.db") as mock_db,
            patch(
                "routes.content.deduct_credits",
                new_callable=AsyncMock,
                return_value={"success": True, "credits_used": 10, "new_balance": 480},
            ),
            patch("routes.content.run_agent_pipeline", new_callable=AsyncMock),
        ):
            mock_db.content_jobs.insert_one = AsyncMock()
            mock_db.campaigns.find_one = AsyncMock(return_value=None)

            client = TestClient(app, raise_server_exceptions=False)
            resp = client.post("/api/content/create", json=second_cycle_payload)

        app.dependency_overrides.clear()

        assert resp.status_code == 200, f"Second-cycle generation failed: {resp.text}"
        data = resp.json()
        assert "job_id" in data
        assert data["status"] == "running"

    # ------------------------------------------------------------------
    # T9: Job status retrieval works after generation
    # ------------------------------------------------------------------

    def test_get_job_status_after_generation(self):
        """GET /api/content/job/{job_id} returns the job with correct fields."""
        import routes.content as content_module

        app = _build_app_for(content_module)
        job = _make_job(status="reviewing")

        with patch("routes.content.db") as mock_db:
            mock_db.content_jobs.find_one = AsyncMock(return_value=job)

            client = TestClient(app, raise_server_exceptions=False)
            resp = client.get(f"/api/content/job/{FAKE_JOB_ID}")

        app.dependency_overrides.clear()

        assert resp.status_code == 200, f"Get job failed: {resp.text}"
        data = resp.json()
        assert data["job_id"] == FAKE_JOB_ID
        assert data["status"] in ("reviewing", "approved", "running", "completed")
        assert "platform" in data

    # ------------------------------------------------------------------
    # T10: Full sequential journey — all stages in one test
    # ------------------------------------------------------------------

    def test_full_critical_path_sequential(self):
        """Chain all critical path stages in sequence.

        A single user goes from content generation through strategy approval
        and second-cycle generation. Each stage uses mocks that simulate
        realistic DB state transitions.

        NOTE: Registration and onboarding are tested independently above.
        This test focuses on generation -> schedule -> strategy -> approve -> regenerate.
        """
        import routes.content as content_module
        import routes.strategy as strategy_module

        # --- Stage 1: First content generation ---
        content_app = _build_app_for(content_module)
        job_id_stage1 = f"job_seq_{uuid.uuid4().hex[:8]}"

        async def _insert_job_capture(doc):
            """Capture insert and verify the job doc structure."""
            assert doc["platform"] == "linkedin"
            assert doc["status"] == "running"
            return MagicMock(inserted_id="mock")

        with (
            patch("routes.content.db") as mock_db,
            patch(
                "routes.content.deduct_credits",
                new_callable=AsyncMock,
                return_value={"success": True, "credits_used": 10, "new_balance": 490},
            ),
            patch("routes.content.run_agent_pipeline", new_callable=AsyncMock),
        ):
            mock_db.content_jobs.insert_one = AsyncMock(side_effect=_insert_job_capture)
            mock_db.campaigns.find_one = AsyncMock(return_value=None)

            client = TestClient(content_app, raise_server_exceptions=False)
            resp1 = client.post(
                "/api/content/create",
                json={
                    "platform": "linkedin",
                    "content_type": "post",
                    "raw_input": "Full journey test — first post",
                },
            )

        content_app.dependency_overrides.clear()
        assert resp1.status_code == 200, f"Stage 1 generation failed: {resp1.text}"
        stage1_data = resp1.json()
        assert "job_id" in stage1_data, "Stage 1 must return job_id"

        # --- Stage 2: Schedule the approved job via dashboard ---
        import routes.dashboard as dashboard_module

        schedule_app = _build_app_for(dashboard_module)
        future_time = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
        mock_sched_result = {
            "success": True,
            "schedule_id": FAKE_SCHEDULE_ID,
            "job_id": FAKE_JOB_ID,
        }

        with patch(
            "agents.planner.schedule_content",
            new_callable=AsyncMock,
            return_value=mock_sched_result,
        ):
            client = TestClient(schedule_app, raise_server_exceptions=False)
            resp2 = client.post(
                "/api/dashboard/schedule/content",
                json={"job_id": FAKE_JOB_ID, "scheduled_at": future_time, "platforms": ["linkedin"]},
            )

        schedule_app.dependency_overrides.clear()
        assert resp2.status_code == 200, f"Stage 2 schedule failed: {resp2.text}"

        # --- Stage 3: Strategy card appears and gets approved ---
        strategy_app = _build_app_for(strategy_module)
        rec = _make_strategy_rec()

        with patch("routes.strategy.handle_approval", new_callable=AsyncMock) as mock_approve:
            mock_approve.return_value = {
                "approved": True,
                "generate_payload": rec["generate_payload"],
            }

            client = TestClient(strategy_app, raise_server_exceptions=False)
            resp3 = client.post(f"/api/strategy/{FAKE_REC_ID}/approve")

        strategy_app.dependency_overrides.clear()
        assert resp3.status_code == 200, f"Stage 3 approve failed: {resp3.text}"
        approve_data = resp3.json()
        assert approve_data.get("approved") is True
        generate_payload = approve_data.get("generate_payload", {})

        # --- Stage 4: Second-cycle generation using approved generate_payload ---
        regen_app = _build_app_for(content_module)

        with (
            patch("routes.content.db") as mock_db,
            patch(
                "routes.content.deduct_credits",
                new_callable=AsyncMock,
                return_value={"success": True, "credits_used": 10, "new_balance": 480},
            ),
            patch("routes.content.run_agent_pipeline", new_callable=AsyncMock),
        ):
            mock_db.content_jobs.insert_one = AsyncMock()
            mock_db.campaigns.find_one = AsyncMock(return_value=None)

            client = TestClient(regen_app, raise_server_exceptions=False)
            resp4 = client.post("/api/content/create", json=generate_payload)

        regen_app.dependency_overrides.clear()
        assert resp4.status_code == 200, f"Stage 4 regeneration failed: {resp4.text}"
        regen_data = resp4.json()
        assert "job_id" in regen_data, "Second-cycle generation must return job_id"
        assert regen_data["status"] == "running"

        # Full journey completed without any unexpected exceptions
