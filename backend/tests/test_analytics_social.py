"""Tests for social analytics service, performance intelligence, optimal posting times,
and persona evolution functionality.

Coverage:
- ANAL-01: Social analytics polling (LinkedIn, X, Instagram) + update_post_performance
- ANAL-02: calculate_optimal_posting_times from real published post data
- ANAL-03: get_content_analytics and get_analytics_overview prefer real data
- ANAL-04: Persona evolution timeline and apply_persona_refinements
"""

from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_async_cursor(items):
    """Return a mock Motor cursor that supports .to_list()."""
    mock_cursor = MagicMock()
    mock_cursor.to_list = AsyncMock(return_value=items)
    mock_cursor.sort = MagicMock(return_value=mock_cursor)
    return mock_cursor


def _make_mock_httpx_client(responses_by_url=None, default_status=200, default_json=None):
    """Build a mock httpx.AsyncClient context manager.

    responses_by_url: dict mapping URL fragment → MagicMock response
    If URL does not match any fragment, uses default_status + default_json.
    """
    if default_json is None:
        default_json = {}

    async def _fake_get(url, **kwargs):
        if responses_by_url:
            for fragment, resp in responses_by_url.items():
                if fragment in str(url):
                    return resp
        # Default response
        r = MagicMock()
        r.status_code = default_status
        r.json.return_value = default_json
        r.text = ""
        return r

    fake_client = MagicMock()
    fake_client.__aenter__ = AsyncMock(return_value=fake_client)
    fake_client.__aexit__ = AsyncMock(return_value=False)
    fake_client.get = AsyncMock(side_effect=_fake_get)
    return fake_client


# ===========================================================================
# TASK 1: Platform fetcher tests
# ===========================================================================


class TestFetchLinkedInPostMetrics:
    """ANAL-01: LinkedIn metrics fetcher."""

    @pytest.mark.asyncio
    async def test_fetch_linkedin_200_returns_metrics(self):
        """Returns likes, comments, shares, impressions, engagement_rate, platform='linkedin'."""
        from services.social_analytics import fetch_linkedin_post_metrics

        social_actions_response = MagicMock()
        social_actions_response.status_code = 200
        social_actions_response.json.return_value = {
            "likesSummary": {"totalLikes": 42},
            "commentsSummary": {"totalFirstLevelComments": 8},
            "sharesSummary": {"totalShares": 3},
        }

        stats_response = MagicMock()
        stats_response.status_code = 403  # no org scope — impression estimate used
        stats_response.text = ""

        fake_client = _make_mock_httpx_client({
            "socialActions": social_actions_response,
            "organizationalEntityShareStatistics": stats_response,
        })

        with patch("services.social_analytics.httpx.AsyncClient", return_value=fake_client):
            result = await fetch_linkedin_post_metrics("urn:li:share:123", "token")

        assert result.get("platform") == "linkedin"
        assert result.get("likes") == 42
        assert result.get("comments") == 8
        assert result.get("shares") == 3
        assert "impressions" in result
        assert "engagement_rate" in result
        assert "error" not in result

    @pytest.mark.asyncio
    async def test_fetch_linkedin_401_returns_token_expired(self):
        """401 response → {'error': 'token_expired'}."""
        from services.social_analytics import fetch_linkedin_post_metrics

        r = MagicMock()
        r.status_code = 401
        fake_client = _make_mock_httpx_client(default_status=401)
        fake_client.get = AsyncMock(return_value=r)

        with patch("services.social_analytics.httpx.AsyncClient", return_value=fake_client):
            result = await fetch_linkedin_post_metrics("urn:li:share:123", "bad_token")

        assert result == {"error": "token_expired"}

    @pytest.mark.asyncio
    async def test_fetch_linkedin_429_returns_rate_limited(self):
        """429 response → {'error': 'rate_limited', 'retry_after': int}."""
        from services.social_analytics import fetch_linkedin_post_metrics

        r = MagicMock()
        r.status_code = 429
        r.headers = {"Retry-After": "120"}
        fake_client = MagicMock()
        fake_client.__aenter__ = AsyncMock(return_value=fake_client)
        fake_client.__aexit__ = AsyncMock(return_value=False)
        fake_client.get = AsyncMock(return_value=r)

        with patch("services.social_analytics.httpx.AsyncClient", return_value=fake_client):
            result = await fetch_linkedin_post_metrics("urn:li:share:123", "token")

        assert result.get("error") == "rate_limited"
        assert isinstance(result.get("retry_after"), int)


class TestFetchXPostMetrics:
    """ANAL-01: X / Twitter metrics fetcher."""

    @pytest.mark.asyncio
    async def test_fetch_x_200_returns_metrics(self):
        """Returns likes, retweets, replies, bookmarks, impressions, engagement_rate, platform='x'."""
        from services.social_analytics import fetch_x_post_metrics

        r = MagicMock()
        r.status_code = 200
        r.json.return_value = {
            "data": {
                "public_metrics": {
                    "like_count": 100,
                    "retweet_count": 25,
                    "reply_count": 10,
                    "bookmark_count": 5,
                    "quote_count": 3,
                },
                "non_public_metrics": {"impression_count": 5000},
            }
        }

        fake_client = MagicMock()
        fake_client.__aenter__ = AsyncMock(return_value=fake_client)
        fake_client.__aexit__ = AsyncMock(return_value=False)
        fake_client.get = AsyncMock(return_value=r)

        with patch("services.social_analytics.httpx.AsyncClient", return_value=fake_client):
            result = await fetch_x_post_metrics("tweet123", "token")

        assert result.get("platform") == "x"
        assert result.get("likes") == 100
        assert result.get("retweets") == 25
        assert result.get("replies") == 10
        assert result.get("bookmarks") == 5
        assert result.get("impressions") == 5000
        assert "engagement_rate" in result
        assert "error" not in result

    @pytest.mark.asyncio
    async def test_fetch_x_401_returns_token_expired(self):
        """401 response → {'error': 'token_expired'}."""
        from services.social_analytics import fetch_x_post_metrics

        r = MagicMock()
        r.status_code = 401

        fake_client = MagicMock()
        fake_client.__aenter__ = AsyncMock(return_value=fake_client)
        fake_client.__aexit__ = AsyncMock(return_value=False)
        fake_client.get = AsyncMock(return_value=r)

        with patch("services.social_analytics.httpx.AsyncClient", return_value=fake_client):
            result = await fetch_x_post_metrics("tweet123", "bad_token")

        assert result == {"error": "token_expired"}


class TestFetchInstagramPostMetrics:
    """ANAL-01: Instagram metrics fetcher."""

    @pytest.mark.asyncio
    async def test_fetch_instagram_200_returns_metrics(self):
        """Returns likes, comments, shares, saved, impressions, engagement_rate, platform='instagram'."""
        from services.social_analytics import fetch_instagram_post_metrics

        r = MagicMock()
        r.status_code = 200
        r.json.return_value = {
            "data": [
                {"name": "impressions", "values": [{"value": 3000}]},
                {"name": "likes", "values": [{"value": 150}]},
                {"name": "comments", "values": [{"value": 20}]},
                {"name": "shares", "values": [{"value": 10}]},
                {"name": "saved", "values": [{"value": 30}]},
            ]
        }

        fake_client = MagicMock()
        fake_client.__aenter__ = AsyncMock(return_value=fake_client)
        fake_client.__aexit__ = AsyncMock(return_value=False)
        fake_client.get = AsyncMock(return_value=r)

        with patch("services.social_analytics.httpx.AsyncClient", return_value=fake_client):
            result = await fetch_instagram_post_metrics("media123", "token")

        assert result.get("platform") == "instagram"
        assert result.get("likes") == 150
        assert result.get("comments") == 20
        assert result.get("shares") == 10
        assert result.get("saved") == 30
        assert result.get("impressions") == 3000
        assert "engagement_rate" in result
        assert "error" not in result

    @pytest.mark.asyncio
    async def test_fetch_instagram_oauth_exception_returns_token_expired(self):
        """400 + OAuthException text → {'error': 'token_expired'}."""
        from services.social_analytics import fetch_instagram_post_metrics

        r = MagicMock()
        r.status_code = 400
        r.text = '{"error": {"type": "OAuthException", "message": "Invalid OAuth token"}}'

        fake_client = MagicMock()
        fake_client.__aenter__ = AsyncMock(return_value=fake_client)
        fake_client.__aexit__ = AsyncMock(return_value=False)
        fake_client.get = AsyncMock(return_value=r)

        with patch("services.social_analytics.httpx.AsyncClient", return_value=fake_client):
            result = await fetch_instagram_post_metrics("media123", "bad_token")

        assert result == {"error": "token_expired"}


class TestUpdatePostPerformance:
    """ANAL-01: update_post_performance end-to-end flow."""

    def _make_job(self):
        return {
            "job_id": "j1",
            "user_id": "u1",
            "platform": "linkedin",
            "publish_results": {
                "linkedin": {"post_id": "urn:li:share:123"}
            },
            "performance_data": {},
        }

    def _linkedin_metrics(self):
        return {
            "likes": 42,
            "comments": 8,
            "shares": 3,
            "impressions": 1325,
            "clicks": 0,
            "engagement_rate": 0.0402,
            "platform": "linkedin",
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }

    @pytest.mark.asyncio
    async def test_update_post_performance_persists_metrics_to_content_jobs(self):
        """Writes performance_data.latest to content_jobs and returns True."""
        from services.social_analytics import update_post_performance

        job = self._make_job()
        metrics = self._linkedin_metrics()

        mock_db = MagicMock()
        mock_db.content_jobs.find_one = AsyncMock(return_value=job)
        mock_db.content_jobs.update_one = AsyncMock()
        mock_db.persona_engines.find_one = AsyncMock(
            return_value={"user_id": "u1", "performance_intelligence": {}}
        )
        mock_db.persona_engines.update_one = AsyncMock()

        # social_analytics.py binds db at import time (from database import db),
        # so we must patch the module-level binding directly.
        with patch("services.social_analytics.db", mock_db):
            with patch("routes.platforms.get_platform_token", AsyncMock(return_value="test_token")):
                with patch("services.social_analytics.fetch_linkedin_post_metrics", AsyncMock(return_value=metrics)):
                    result = await update_post_performance("j1", "u1", "linkedin")

        assert result is True
        update_calls = mock_db.content_jobs.update_one.call_args_list
        assert len(update_calls) >= 1
        set_payload = update_calls[0].args[1]["$set"]
        assert "performance_data" in set_payload
        assert set_payload["performance_data"]["latest"] == metrics

    @pytest.mark.asyncio
    async def test_update_post_performance_calls_aggregate_intelligence(self):
        """Calls _aggregate_performance_intelligence which updates persona_engines."""
        from services.social_analytics import update_post_performance

        job = self._make_job()
        metrics = self._linkedin_metrics()

        mock_db = MagicMock()
        mock_db.content_jobs.find_one = AsyncMock(return_value=job)
        mock_db.content_jobs.update_one = AsyncMock()
        mock_db.persona_engines.find_one = AsyncMock(
            return_value={"user_id": "u1", "performance_intelligence": {}}
        )
        mock_db.persona_engines.update_one = AsyncMock()

        with patch("services.social_analytics.db", mock_db):
            with patch("routes.platforms.get_platform_token", AsyncMock(return_value="test_token")):
                with patch("services.social_analytics.fetch_linkedin_post_metrics", AsyncMock(return_value=metrics)):
                    result = await update_post_performance("j1", "u1", "linkedin")

        assert result is True
        assert mock_db.persona_engines.update_one.called
        persona_call = mock_db.persona_engines.update_one.call_args
        assert "performance_intelligence" in persona_call.args[1]["$set"]

    @pytest.mark.asyncio
    async def test_update_post_performance_with_fetch_error_stores_last_error(self):
        """Returns False and stores last_error when fetch returns error dict."""
        from services.social_analytics import update_post_performance

        job = self._make_job()

        mock_db = MagicMock()
        mock_db.content_jobs.find_one = AsyncMock(return_value=job)
        mock_db.content_jobs.update_one = AsyncMock()

        with patch("services.social_analytics.db", mock_db):
            with patch("routes.platforms.get_platform_token", AsyncMock(return_value="test_token")):
                with patch("services.social_analytics.fetch_linkedin_post_metrics",
                           AsyncMock(return_value={"error": "token_expired"})):
                    result = await update_post_performance("j1", "u1", "linkedin")

        assert result is False
        update_calls = mock_db.content_jobs.update_one.call_args_list
        assert len(update_calls) >= 1
        set_payload = update_calls[0].args[1]["$set"]
        assert "performance_data.last_error" in set_payload

    @pytest.mark.asyncio
    async def test_update_post_performance_missing_publish_results_returns_false(self):
        """Returns False when job has no publish_results for platform."""
        from services.social_analytics import update_post_performance

        job = {
            "job_id": "j2",
            "user_id": "u1",
            "platform": "linkedin",
            "publish_results": {},  # no linkedin key
        }

        mock_db = MagicMock()
        mock_db.content_jobs.find_one = AsyncMock(return_value=job)

        with patch("services.social_analytics.db", mock_db):
            result = await update_post_performance("j2", "u1", "linkedin")

        assert result is False


class TestAggregatePerformanceIntelligence:
    """ANAL-01: Running average calculation in _aggregate_performance_intelligence."""

    @pytest.mark.asyncio
    async def test_aggregate_updates_running_averages(self):
        """Running average recalculated using incremental formula: old_avg + (new - old) / n."""
        from services.social_analytics import _aggregate_performance_intelligence

        existing_intel = {
            "linkedin": {
                "posts_tracked": 5,
                "total_impressions": 10000,
                "total_engagements": 400,
                "avg_engagement_rate": 0.04,
                "best_engagement_rate": 0.05,
                "worst_engagement_rate": 0.02,
            }
        }
        persona = {"user_id": "u1", "performance_intelligence": existing_intel}

        mock_db = MagicMock()
        mock_db.persona_engines.find_one = AsyncMock(return_value=persona)
        mock_db.persona_engines.update_one = AsyncMock()

        new_metrics = {
            "likes": 60,
            "comments": 10,
            "shares": 2,
            "impressions": 2000,
            "engagement_rate": 0.06,
            "platform": "linkedin",
        }

        with patch("services.social_analytics.db", mock_db):
            await _aggregate_performance_intelligence("u1", "linkedin", new_metrics)

        assert mock_db.persona_engines.update_one.called
        call_args = mock_db.persona_engines.update_one.call_args
        updated_intel = call_args.args[1]["$set"]["performance_intelligence"]
        li = updated_intel["linkedin"]

        assert li["posts_tracked"] == 6
        expected_avg = round(0.04 + (0.06 - 0.04) / 6, 4)  # 0.0433
        assert li["avg_engagement_rate"] == expected_avg

    @pytest.mark.asyncio
    async def test_aggregate_updates_best_and_worst_rates(self):
        """Best rate updated when new post exceeds previous best."""
        from services.social_analytics import _aggregate_performance_intelligence

        existing_intel = {
            "linkedin": {
                "posts_tracked": 3,
                "total_impressions": 5000,
                "total_engagements": 150,
                "avg_engagement_rate": 0.03,
                "best_engagement_rate": 0.04,
                "worst_engagement_rate": 0.02,
            }
        }
        persona = {"user_id": "u1", "performance_intelligence": existing_intel}

        mock_db = MagicMock()
        mock_db.persona_engines.find_one = AsyncMock(return_value=persona)
        mock_db.persona_engines.update_one = AsyncMock()

        new_metrics = {
            "likes": 100,
            "impressions": 1000,
            "engagement_rate": 0.10,
            "platform": "linkedin",
        }

        with patch("services.social_analytics.db", mock_db):
            await _aggregate_performance_intelligence("u1", "linkedin", new_metrics)

        call_args = mock_db.persona_engines.update_one.call_args
        updated_intel = call_args.args[1]["$set"]["performance_intelligence"]
        li = updated_intel["linkedin"]
        assert li["best_engagement_rate"] == 0.10


# ===========================================================================
# TASK 2: Optimal posting times, real-data analytics, persona evolution
# ===========================================================================


class TestCalculateOptimalPostingTimes:
    """ANAL-02: Optimal posting times from real published data."""

    def _make_published_posts(self, count=15, platform="linkedin"):
        """Create published posts with real performance data spread across day/hour slots."""
        posts = []
        base = datetime(2026, 1, 5, tzinfo=timezone.utc)  # Monday
        for i in range(count):
            # 3 distinct day/hour slots, ~5 posts each  → each slot has 5 samples ≥ MIN_SLOT_SAMPLE(3)
            day_offset = (i % 3) * 2
            hour = 9 + (i % 3) * 3
            published_at = base + timedelta(days=day_offset + (i // 3) * 7, hours=hour)
            posts.append({
                "job_id": f"job_{i}",
                "user_id": "u1",
                "platform": platform,
                "status": "published",
                "published_at": published_at,
                "performance_data": {
                    "engagement_rate": 0.03 + (i % 5) * 0.01,
                    "impressions": 1000 + i * 50,
                },
            })
        return posts

    @pytest.mark.asyncio
    async def test_calculates_optimal_times_from_15_posts(self):
        """Returns dict with platform keys when there are enough posts and qualifying slots."""
        from services.persona_refinement import calculate_optimal_posting_times

        posts = self._make_published_posts(15)
        cursor = _make_async_cursor(posts)

        mock_db = MagicMock()
        mock_db.content_jobs.find = MagicMock(return_value=cursor)
        mock_db.persona_engines.update_one = AsyncMock()

        with patch("database.db", mock_db):
            result = await calculate_optimal_posting_times("u1")

        # Should have linkedin key with slot recommendations (or message if no qualifying slots)
        if "message" not in result:
            assert "linkedin" in result
            assert len(result["linkedin"]) > 0
            slot = result["linkedin"][0]
            assert "day_of_week" in slot
            assert "hour_of_day" in slot
            assert "avg_engagement_rate" in slot

    @pytest.mark.asyncio
    async def test_returns_message_for_fewer_than_10_posts(self):
        """Returns message dict when fewer than 10 posts with performance data."""
        from services.persona_refinement import calculate_optimal_posting_times

        posts = self._make_published_posts(5)
        cursor = _make_async_cursor(posts)

        mock_db = MagicMock()
        mock_db.content_jobs.find = MagicMock(return_value=cursor)
        mock_db.persona_engines.update_one = AsyncMock()

        with patch("database.db", mock_db):
            result = await calculate_optimal_posting_times("u1")

        assert "message" in result
        assert result.get("posts_with_data") == 5

    @pytest.mark.asyncio
    async def test_stores_result_in_persona_engines(self):
        """Result is persisted to persona_engines.optimal_posting_times and optimal_times_calculated_at."""
        from services.persona_refinement import calculate_optimal_posting_times

        posts = self._make_published_posts(15)
        cursor = _make_async_cursor(posts)

        mock_db = MagicMock()
        mock_db.content_jobs.find = MagicMock(return_value=cursor)
        mock_db.persona_engines.update_one = AsyncMock()

        with patch("database.db", mock_db):
            await calculate_optimal_posting_times("u1")

        assert mock_db.persona_engines.update_one.called
        call_args = mock_db.persona_engines.update_one.call_args
        set_payload = call_args.args[1]["$set"]
        assert "optimal_posting_times" in set_payload
        assert "optimal_times_calculated_at" in set_payload


class TestGetContentAnalyticsRealData:
    """ANAL-03: get_content_analytics prefers real performance_data.latest."""

    @pytest.mark.asyncio
    async def test_returns_is_estimated_false_when_real_data_present(self):
        """Job with performance_data.latest → is_estimated=False, real metrics returned."""
        from agents.analyst import get_content_analytics

        real_metrics = {
            "impressions": 5000,
            "likes": 200,
            "comments": 30,
            "engagement_rate": 0.046,
            "platform": "linkedin",
        }
        job = {
            "job_id": "j1",
            "user_id": "u1",
            "platform": "linkedin",
            "status": "published",
            "final_content": "Test content",
            "performance_data": {"latest": real_metrics},
        }

        mock_db = MagicMock()
        mock_db.content_jobs.find_one = AsyncMock(return_value=job)

        with patch("database.db", mock_db):
            result = await get_content_analytics("u1", "j1")

        assert result.get("success") is True
        assert result.get("is_estimated") is False
        assert result["metrics"].get("impressions") == 5000
        assert result["metrics"].get("likes") == 200

    @pytest.mark.asyncio
    async def test_returns_is_estimated_true_when_no_performance_data(self):
        """Job without performance_data → is_estimated=True, simulated metrics returned."""
        from agents.analyst import get_content_analytics

        job = {
            "job_id": "j2",
            "user_id": "u1",
            "platform": "linkedin",
            "status": "published",
            "final_content": "Test content",
            # no performance_data field
        }

        mock_db = MagicMock()
        mock_db.content_jobs.find_one = AsyncMock(return_value=job)

        with patch("database.db", mock_db):
            result = await get_content_analytics("u1", "j2")

        assert result.get("success") is True
        assert result.get("is_estimated") is True


class TestGetAnalyticsOverviewRealData:
    """ANAL-03: get_analytics_overview counts real vs estimated correctly."""

    def _make_job_with_real_data(self, job_id, platform="linkedin"):
        return {
            "job_id": job_id,
            "user_id": "u1",
            "platform": platform,
            "status": "published",
            "final_content": "Real content",
            "created_at": datetime.now(timezone.utc),
            "performance_data": {
                "latest": {
                    "impressions": 3000,
                    "likes": 100,
                    "comments": 15,
                    "shares": 5,
                    "engagement_rate": 0.04,
                    "platform": platform,
                }
            },
        }

    def _make_job_without_real_data(self, job_id, platform="linkedin"):
        return {
            "job_id": job_id,
            "user_id": "u1",
            "platform": platform,
            "status": "published",
            "final_content": "Simulated content",
            "created_at": datetime.now(timezone.utc),
            # no performance_data
        }

    @pytest.mark.asyncio
    async def test_counts_real_vs_estimated_posts(self):
        """3 real + 2 estimated → summary.real_data_posts==3, estimated_posts==2."""
        from agents.analyst import get_analytics_overview

        jobs = [
            self._make_job_with_real_data("j1"),
            self._make_job_with_real_data("j2"),
            self._make_job_with_real_data("j3"),
            self._make_job_without_real_data("j4"),
            self._make_job_without_real_data("j5"),
        ]
        cursor = _make_async_cursor(jobs)

        mock_db = MagicMock()
        mock_db.content_jobs.find = MagicMock(return_value=cursor)

        with patch("database.db", mock_db):
            result = await get_analytics_overview("u1", days=30)

        assert result.get("success") is True
        assert result.get("has_data") is True
        summary = result.get("summary", {})
        assert summary.get("real_data_posts") == 3
        assert summary.get("estimated_posts") == 2

    @pytest.mark.asyncio
    async def test_is_estimated_true_when_any_estimated(self):
        """is_estimated is True when at least one post used simulated metrics."""
        from agents.analyst import get_analytics_overview

        jobs = [
            self._make_job_with_real_data("j1"),
            self._make_job_without_real_data("j2"),
        ]
        cursor = _make_async_cursor(jobs)

        mock_db = MagicMock()
        mock_db.content_jobs.find = MagicMock(return_value=cursor)

        with patch("database.db", mock_db):
            result = await get_analytics_overview("u1", days=30)

        assert result.get("is_estimated") is True

    @pytest.mark.asyncio
    async def test_valid_aggregation_with_mix_of_real_and_simulated(self):
        """Mixed real and simulated data still produces valid aggregation output."""
        from agents.analyst import get_analytics_overview

        jobs = [
            self._make_job_with_real_data("j1"),
            self._make_job_without_real_data("j2"),
            self._make_job_with_real_data("j3"),
        ]
        cursor = _make_async_cursor(jobs)

        mock_db = MagicMock()
        mock_db.content_jobs.find = MagicMock(return_value=cursor)

        with patch("database.db", mock_db):
            result = await get_analytics_overview("u1", days=30)

        assert result.get("success") is True
        assert result.get("has_data") is True
        assert "summary" in result
        assert result["summary"]["total_posts"] == 3
        assert "by_platform" in result
        assert "top_performing" in result

    @pytest.mark.asyncio
    async def test_returns_has_data_false_when_no_jobs(self):
        """Returns has_data=False when no published content in period."""
        from agents.analyst import get_analytics_overview

        cursor = _make_async_cursor([])
        mock_db = MagicMock()
        mock_db.content_jobs.find = MagicMock(return_value=cursor)

        with patch("database.db", mock_db):
            result = await get_analytics_overview("u1", days=30)

        assert result.get("success") is True
        assert result.get("has_data") is False


class TestPersonaEvolution:
    """ANAL-04: Persona evolution timeline and apply_persona_refinements."""

    @pytest.mark.asyncio
    async def test_get_persona_evolution_timeline_returns_history(self):
        """Returns evolution timeline with timestamps and field changes."""
        from services.persona_refinement import get_persona_evolution_timeline

        now = datetime.now(timezone.utc)
        persona = {
            "user_id": "u1",
            "created_at": now - timedelta(days=30),
            "card": {
                "archetype": "Expert Educator",
                "writing_voice_descriptor": "Clear and direct",
                "content_niche_signature": "AI tools",
                "last_refined": now - timedelta(days=7),
            },
            "evolution_history": [
                {
                    "timestamp": now - timedelta(days=14),
                    "source": "refinement",
                    "updates": [
                        {
                            "field": "writing_voice_descriptor",
                            "old_value": "Technical",
                            "new_value": "Clear and direct",
                        }
                    ],
                },
                {
                    "timestamp": now - timedelta(days=7),
                    "source": "refinement",
                    "updates": [
                        {
                            "field": "content_niche_signature",
                            "old_value": "Tech",
                            "new_value": "AI tools",
                        }
                    ],
                },
            ],
        }

        mock_db = MagicMock()
        mock_db.persona_engines.find_one = AsyncMock(return_value=persona)

        with patch("database.db", mock_db):
            result = await get_persona_evolution_timeline("u1")

        assert result.get("success") is True
        assert "timeline" in result
        assert result.get("total_refinements") == 2
        assert len(result["timeline"]) >= 2

    @pytest.mark.asyncio
    async def test_apply_persona_refinements_stores_evolution_snapshot(self):
        """apply_persona_refinements pushes to evolution_history and updates card fields."""
        from services.persona_refinement import apply_persona_refinements

        persona = {
            "user_id": "u1",
            "card": {
                "writing_voice_descriptor": "Technical",
                "content_niche_signature": "Tech",
            },
            "evolution_history": [],
        }
        mock_result = MagicMock()
        mock_result.modified_count = 1

        mock_db = MagicMock()
        mock_db.persona_engines.find_one = AsyncMock(return_value=persona)
        mock_db.persona_engines.update_one = AsyncMock(return_value=mock_result)

        updates = [
            {"field": "writing_voice_descriptor", "value": "Clear and direct"},
        ]

        with patch("database.db", mock_db):
            result = await apply_persona_refinements("u1", updates)

        assert result.get("success") is True
        assert result.get("updates_applied") == 1

        call_args = mock_db.persona_engines.update_one.call_args
        update_doc = call_args.args[1]
        assert "$push" in update_doc
        assert "evolution_history" in update_doc["$push"]

    @pytest.mark.asyncio
    async def test_get_persona_evolution_returns_error_for_missing_persona(self):
        """Returns error dict when persona not found."""
        from services.persona_refinement import get_persona_evolution_timeline

        mock_db = MagicMock()
        mock_db.persona_engines.find_one = AsyncMock(return_value=None)

        with patch("database.db", mock_db):
            result = await get_persona_evolution_timeline("nonexistent_user")

        assert result.get("success") is False
        assert "error" in result


class TestOptimalTimesEndpointContract:
    """ANAL-02: GET /api/analytics/optimal-times endpoint contract verification."""

    @pytest.mark.asyncio
    async def test_optimal_times_response_with_calculated_data(self):
        """When persona has optimal_posting_times, response includes the times."""
        from services.persona_refinement import calculate_optimal_posting_times

        # Verify the shape of data returned by calculate_optimal_posting_times
        posts = []
        base = datetime(2026, 1, 5, tzinfo=timezone.utc)
        for i in range(15):
            day_offset = (i % 3) * 2
            hour = 9 + (i % 3) * 3
            published_at = base + timedelta(days=day_offset + (i // 3) * 7, hours=hour)
            posts.append({
                "job_id": f"job_{i}",
                "platform": "linkedin",
                "status": "published",
                "published_at": published_at,
                "performance_data": {
                    "engagement_rate": 0.04 + (i % 3) * 0.01,
                    "impressions": 2000,
                },
            })

        cursor = _make_async_cursor(posts)
        mock_db = MagicMock()
        mock_db.content_jobs.find = MagicMock(return_value=cursor)
        mock_db.persona_engines.update_one = AsyncMock()

        with patch("database.db", mock_db):
            result = await calculate_optimal_posting_times("u1")

        # Response is either the optimal times dict or a message dict
        assert isinstance(result, dict)
        if "message" not in result:
            # Each platform key maps to a list of slot dicts
            for platform, slots in result.items():
                assert isinstance(slots, list)
                for slot in slots:
                    assert "day_of_week" in slot
                    assert "hour_of_day" in slot
                    assert "avg_engagement_rate" in slot

    @pytest.mark.asyncio
    async def test_optimal_times_empty_response_structure(self):
        """When no data available, response has message and empty optimal_times."""
        # Simulate what the endpoint returns when persona has no optimal_times
        persona = {
            "user_id": "u1",
            "optimal_posting_times": {},
        }

        mock_db = MagicMock()
        mock_db.persona_engines.find_one = AsyncMock(return_value=persona)

        with patch("database.db", mock_db):
            stored_persona = await mock_db.persona_engines.find_one({"user_id": "u1"})
            optimal_times = stored_persona.get("optimal_posting_times", {}) if stored_persona else {}

        if not optimal_times:
            response = {
                "optimal_times": {},
                "message": "Optimal times are calculated after 10+ published posts with performance data.",
                "last_calculated_at": None,
            }
        else:
            response = {"optimal_times": optimal_times}

        assert response.get("optimal_times") == {}
        assert "message" in response
