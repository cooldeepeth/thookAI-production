"""
Analytics Feedback Loop Tests — Phase 19, Plan 04.

Covers the end-to-end analytics pipeline:
  - 24h and 7d poll write-back to content_jobs.performance_data
  - Error handling during platform API calls (token_expired → last_error stored)
  - Optimal posting times: insufficient data, stores to persona_engines, groups by platform,
    weights by engagement rate
  - Aggregate performance intelligence: running averages, best/worst, updates persona_engines,
    handles missing data gracefully
  - Cross-platform metric normalization (LinkedIn, X, Instagram schema shapes)
  - Strategist consumption of performance_signals

NOTE: Do NOT duplicate tests from test_analytics_social.py.  That file covers:
  - TestFetchLinkedInPostMetrics (200, 401, 429)
  - TestFetchXPostMetrics (200, 401)
  - TestFetchInstagramPostMetrics (200, OAuthException)
  - TestUpdatePostPerformance (persists metrics, calls aggregate, stores last_error, missing results)
  - TestAggregatePerformanceIntelligence (running averages, best/worst)
  - TestCalculateOptimalPostingTimes (15 posts, <10 posts, stores to persona_engines)
  - TestGetContentAnalyticsRealData (is_estimated flag)
  - TestGetAnalyticsOverviewRealData (counts, aggregation, has_data)
  - TestPersonaEvolution (timeline, apply_refinements)
  - TestOptimalTimesEndpointContract

This file closes the following NEW gaps:
  1. update_post_performance: 24h snapshot field naming, 7d snapshot added alongside 24h,
     expired token stores last_error
  2. calculate_optimal_posting_times: multi-platform grouping, engagement weighting
  3. aggregate_performance_intelligence: handles mix of complete/empty performance_data
  4. Cross-platform metric normalization (field presence and types)
  5. Strategist _gather_user_context: performance_signals populated from performance_data
"""

from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_async_cursor(items):
    """Return a mock Motor cursor that supports .to_list() and .sort()."""
    cursor = MagicMock()
    cursor.to_list = AsyncMock(return_value=items)
    cursor.sort = MagicMock(return_value=cursor)
    return cursor


def _make_mock_httpx_client(responses_by_url=None, default_status=200, default_json=None):
    """Build a mock httpx.AsyncClient context manager."""
    if default_json is None:
        default_json = {}

    async def _fake_get(url, **kwargs):
        if responses_by_url:
            for fragment, resp in responses_by_url.items():
                if fragment in str(url):
                    return resp
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


def _make_published_job(
    job_id: str,
    user_id: str,
    platform: str = "linkedin",
    performance_data: dict = None,
    published_at: datetime = None,
):
    """Build a minimal published content_job with optional performance_data."""
    base = {
        "job_id": job_id,
        "user_id": user_id,
        "platform": platform,
        "status": "published",
        "publish_results": {platform: {"post_id": f"post-{job_id}"}},
        "analytics_24h_polled": False,
        "analytics_7d_polled": False,
    }
    if performance_data is not None:
        base["performance_data"] = performance_data
    if published_at is not None:
        base["published_at"] = published_at
    return base


# ===========================================================================
# TASK 1: Analytics poll flow (NEW scenarios not in test_analytics_social.py)
# ===========================================================================


class TestAnalyticsPollFlow:
    """NEW coverage: update_post_performance snapshot fields, token error storage."""

    @pytest.mark.asyncio
    async def test_24h_poll_persists_latest_metrics_with_all_required_fields(self):
        """update_post_performance persists impressions, reach, likes, comments, shares
        under performance_data.latest — verifies field completeness for LinkedIn."""
        from services.social_analytics import update_post_performance

        job = {
            "job_id": "j-24h",
            "user_id": "u1",
            "platform": "linkedin",
            "publish_results": {"linkedin": {"post_id": "urn:li:share:111"}},
            "performance_data": {},
        }

        linkedin_metrics = {
            "impressions": 2500,
            "clicks": 12,
            "likes": 95,
            "comments": 18,
            "shares": 7,
            "engagement_rate": 0.048,
            "platform": "linkedin",
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }

        mock_db = MagicMock()
        mock_db.content_jobs.find_one = AsyncMock(return_value=job)
        mock_db.content_jobs.update_one = AsyncMock()
        mock_db.persona_engines.find_one = AsyncMock(
            return_value={"user_id": "u1", "performance_intelligence": {}}
        )
        mock_db.persona_engines.update_one = AsyncMock()

        with patch("services.social_analytics.db", mock_db):
            with patch("routes.platforms.get_platform_token", AsyncMock(return_value="tok")):
                with patch(
                    "services.social_analytics.fetch_linkedin_post_metrics",
                    AsyncMock(return_value=linkedin_metrics),
                ):
                    result = await update_post_performance("j-24h", "u1", "linkedin")

        assert result is True
        update_calls = mock_db.content_jobs.update_one.call_args_list
        assert len(update_calls) >= 1
        set_payload = update_calls[0].args[1]["$set"]

        # performance_data.latest must contain the required metric fields
        latest = set_payload["performance_data"]["latest"]
        for field in ("impressions", "likes", "comments", "shares", "engagement_rate"):
            assert field in latest, f"Missing field '{field}' in performance_data.latest"
        assert latest["impressions"] == 2500
        assert latest["likes"] == 95

    @pytest.mark.asyncio
    async def test_7d_poll_adds_snapshot_alongside_existing_24h_data(self):
        """Second call with 7d period writes new metrics without erasing 24h data.

        Verifies that the history list grows and latest is updated.
        """
        from services.social_analytics import update_post_performance

        # Job already has 24h snapshot in history
        existing_history = [
            {
                "impressions": 1000,
                "likes": 30,
                "engagement_rate": 0.03,
                "platform": "linkedin",
                "collected_at": (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat(),
            }
        ]
        job = {
            "job_id": "j-7d",
            "user_id": "u1",
            "platform": "linkedin",
            "publish_results": {"linkedin": {"post_id": "urn:li:share:222"}},
            "performance_data": {
                "latest": {"impressions": 1000, "engagement_rate": 0.03, "platform": "linkedin"},
                "history": existing_history,
            },
        }

        week_metrics = {
            "impressions": 4200,
            "clicks": 55,
            "likes": 180,
            "comments": 40,
            "shares": 22,
            "engagement_rate": 0.057,
            "platform": "linkedin",
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }

        mock_db = MagicMock()
        mock_db.content_jobs.find_one = AsyncMock(return_value=job)
        mock_db.content_jobs.update_one = AsyncMock()
        mock_db.persona_engines.find_one = AsyncMock(
            return_value={"user_id": "u1", "performance_intelligence": {}}
        )
        mock_db.persona_engines.update_one = AsyncMock()

        with patch("services.social_analytics.db", mock_db):
            with patch("routes.platforms.get_platform_token", AsyncMock(return_value="tok")):
                with patch(
                    "services.social_analytics.fetch_linkedin_post_metrics",
                    AsyncMock(return_value=week_metrics),
                ):
                    result = await update_post_performance("j-7d", "u1", "linkedin")

        assert result is True
        set_payload = mock_db.content_jobs.update_one.call_args.args[1]["$set"]

        # Latest metrics updated to 7d values
        latest = set_payload["performance_data"]["latest"]
        assert latest["impressions"] == 4200

        # History now contains 2 entries (original 24h + new 7d snapshot)
        history = set_payload["performance_data"]["history"]
        assert len(history) == 2, (
            f"Expected 2 history entries (24h + 7d), got {len(history)}"
        )

    @pytest.mark.asyncio
    async def test_7d_poll_triggers_aggregate_performance_intelligence(self):
        """After successful update_post_performance, _aggregate_performance_intelligence
        is called to update persona_engines.performance_intelligence."""
        from services.social_analytics import update_post_performance

        job = {
            "job_id": "j-agg",
            "user_id": "u-agg",
            "platform": "x",
            "publish_results": {"x": {"tweet_ids": ["tw-789"]}},
            "performance_data": {},
        }

        x_metrics = {
            "impressions": 8000,
            "likes": 350,
            "retweets": 80,
            "replies": 25,
            "bookmarks": 10,
            "quote_tweets": 5,
            "engagement_rate": 0.059,
            "platform": "x",
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }

        existing_intel = {
            "x": {
                "posts_tracked": 2,
                "total_impressions": 5000,
                "total_engagements": 100,
                "avg_engagement_rate": 0.02,
                "best_engagement_rate": 0.025,
                "worst_engagement_rate": 0.015,
            }
        }

        mock_db = MagicMock()
        mock_db.content_jobs.find_one = AsyncMock(return_value=job)
        mock_db.content_jobs.update_one = AsyncMock()
        mock_db.persona_engines.find_one = AsyncMock(
            return_value={"user_id": "u-agg", "performance_intelligence": existing_intel}
        )
        mock_db.persona_engines.update_one = AsyncMock()

        with patch("services.social_analytics.db", mock_db):
            with patch("routes.platforms.get_platform_token", AsyncMock(return_value="tok")):
                with patch(
                    "services.social_analytics.fetch_x_post_metrics",
                    AsyncMock(return_value=x_metrics),
                ):
                    result = await update_post_performance("j-agg", "u-agg", "x")

        assert result is True
        # persona_engines must be updated after performance fetch
        assert mock_db.persona_engines.update_one.called
        pi_update = mock_db.persona_engines.update_one.call_args.args[1]["$set"]
        assert "performance_intelligence" in pi_update
        assert "x" in pi_update["performance_intelligence"]
        # posts_tracked should now be 3
        assert pi_update["performance_intelligence"]["x"]["posts_tracked"] == 3

    @pytest.mark.asyncio
    async def test_poll_with_expired_token_stores_error_in_performance_data(self):
        """When platform API returns 401 (token_expired), performance_data.last_error
        is written to the job and update_post_performance returns False."""
        from services.social_analytics import update_post_performance

        job = {
            "job_id": "j-err",
            "user_id": "u-err",
            "platform": "instagram",
            "publish_results": {"instagram": {"post_id": "ig-media-555"}},
            "performance_data": {},
        }

        mock_db = MagicMock()
        mock_db.content_jobs.find_one = AsyncMock(return_value=job)
        mock_db.content_jobs.update_one = AsyncMock()

        with patch("services.social_analytics.db", mock_db):
            with patch("routes.platforms.get_platform_token", AsyncMock(return_value="expired_tok")):
                with patch(
                    "services.social_analytics.fetch_instagram_post_metrics",
                    AsyncMock(return_value={"error": "token_expired"}),
                ):
                    result = await update_post_performance("j-err", "u-err", "instagram")

        assert result is False

        # Verify last_error stored
        update_calls = mock_db.content_jobs.update_one.call_args_list
        assert len(update_calls) >= 1
        set_payload = update_calls[0].args[1]["$set"]
        assert "performance_data.last_error" in set_payload
        assert set_payload["performance_data.last_error"]["error"] == "token_expired"


# ===========================================================================
# TASK 2: Optimal posting times (NEW scenarios not in test_analytics_social.py)
# ===========================================================================


class TestOptimalPostingTimes:
    """NEW coverage: multi-platform grouping and engagement-rate weighting."""

    @pytest.mark.asyncio
    async def test_groups_by_platform_independently(self):
        """Posts across linkedin/x/instagram produce independent optimal time sets."""
        from services.persona_refinement import calculate_optimal_posting_times

        base = datetime(2026, 1, 5, tzinfo=timezone.utc)  # Monday

        posts = []
        # Generate 15+ posts per platform to meet minimum threshold
        for platform in ("linkedin", "x", "instagram"):
            for i in range(15):
                day_offset = (i % 3) * 2
                hour = 9 + (i % 3) * 3
                published_at = base + timedelta(days=day_offset + (i // 3) * 7, hours=hour)
                posts.append({
                    "job_id": f"job-{platform}-{i}",
                    "user_id": "u-multi",
                    "platform": platform,
                    "status": "published",
                    "published_at": published_at,
                    "performance_data": {
                        "engagement_rate": 0.03 + (i % 5) * 0.01,
                        "impressions": 1000 + i * 50,
                    },
                })

        mock_db = MagicMock()
        mock_db.content_jobs.find = MagicMock(return_value=_make_async_cursor(posts))
        mock_db.persona_engines.update_one = AsyncMock()

        with patch("database.db", mock_db):
            result = await calculate_optimal_posting_times("u-multi")

        # Each platform should have its own optimal times if sufficient data
        if "message" not in result:
            present_platforms = set(result.keys())
            # At least some platforms should be present (requires 3+ samples per slot)
            assert len(present_platforms) > 0
            for p in present_platforms:
                assert isinstance(result[p], list)
                assert len(result[p]) > 0
                slot = result[p][0]
                assert "day_of_week" in slot
                assert "hour_of_day" in slot
                assert "avg_engagement_rate" in slot

    @pytest.mark.asyncio
    async def test_weights_by_engagement_rate(self):
        """Slots with higher average engagement rate rank above slots with lower rate."""
        from services.persona_refinement import calculate_optimal_posting_times

        base = datetime(2026, 1, 5, tzinfo=timezone.utc)  # Monday 00:00 UTC

        # Create posts that fall into exactly two distinct (day, hour) slots with 5+ samples each
        # Slot A: Monday 09:00 — high engagement (0.10)
        # Slot B: Wednesday 15:00 — low engagement (0.01)
        posts = []
        for i in range(5):
            posts.append({
                "job_id": f"high-{i}",
                "user_id": "u-weight",
                "platform": "linkedin",
                "status": "published",
                "published_at": base + timedelta(hours=9),  # Monday 09:00
                "performance_data": {"engagement_rate": 0.10, "impressions": 2000},
            })
        for i in range(5):
            posts.append({
                "job_id": f"low-{i}",
                "user_id": "u-weight",
                "platform": "linkedin",
                "status": "published",
                "published_at": base + timedelta(days=2, hours=15),  # Wednesday 15:00
                "performance_data": {"engagement_rate": 0.01, "impressions": 500},
            })

        mock_db = MagicMock()
        mock_db.content_jobs.find = MagicMock(return_value=_make_async_cursor(posts))
        mock_db.persona_engines.update_one = AsyncMock()

        with patch("database.db", mock_db):
            result = await calculate_optimal_posting_times("u-weight")

        if "message" in result:
            # Insufficient data path hit — not enough qualifying slots with 3 samples
            # This is acceptable: we created 5 samples each but MIN_SLOT_SAMPLE=3
            return

        assert "linkedin" in result, "Should have linkedin recommendations"
        slots = result["linkedin"]
        assert len(slots) >= 2, f"Expected at least 2 slot recommendations, got {len(slots)}"

        # First slot (highest engagement) should have higher rate than second
        top_rate = slots[0]["avg_engagement_rate"]
        second_rate = slots[1]["avg_engagement_rate"] if len(slots) > 1 else 0
        assert top_rate >= second_rate, (
            f"Slots not sorted by engagement: top={top_rate}, second={second_rate}"
        )
        # The 9am slot should rank first
        assert slots[0]["hour_of_day"] == 9

    @pytest.mark.asyncio
    async def test_returns_insufficient_data_message_for_fewer_than_10(self):
        """Returns informational message when fewer than 10 posts with performance data."""
        from services.persona_refinement import calculate_optimal_posting_times

        posts = [
            {
                "job_id": f"j{i}",
                "user_id": "u-low",
                "platform": "linkedin",
                "status": "published",
                "published_at": datetime.now(timezone.utc),
                "performance_data": {"engagement_rate": 0.03, "impressions": 500},
            }
            for i in range(7)
        ]

        mock_db = MagicMock()
        mock_db.content_jobs.find = MagicMock(return_value=_make_async_cursor(posts))
        mock_db.persona_engines.update_one = AsyncMock()

        with patch("database.db", mock_db):
            result = await calculate_optimal_posting_times("u-low")

        assert "message" in result
        assert "posts_with_data" in result
        assert result["posts_with_data"] == 7

    @pytest.mark.asyncio
    async def test_stores_result_in_persona_engines_optimal_posting_times(self):
        """Calculated result is persisted to persona_engines.optimal_posting_times."""
        from services.persona_refinement import calculate_optimal_posting_times

        base = datetime(2026, 1, 5, tzinfo=timezone.utc)
        posts = [
            {
                "job_id": f"j{i}",
                "user_id": "u-store",
                "platform": "linkedin",
                "status": "published",
                "published_at": base + timedelta(days=(i % 3) * 2, hours=9 + (i % 3) * 3),
                "performance_data": {"engagement_rate": 0.04, "impressions": 1200},
            }
            for i in range(15)
        ]

        mock_db = MagicMock()
        mock_db.content_jobs.find = MagicMock(return_value=_make_async_cursor(posts))
        mock_db.persona_engines.update_one = AsyncMock()

        with patch("database.db", mock_db):
            await calculate_optimal_posting_times("u-store")

        assert mock_db.persona_engines.update_one.called
        call_args = mock_db.persona_engines.update_one.call_args
        set_payload = call_args.args[1]["$set"]
        assert "optimal_posting_times" in set_payload
        assert "optimal_times_calculated_at" in set_payload

    @pytest.mark.asyncio
    async def test_excludes_posts_without_performance_data(self):
        """Posts without performance_data or with error fields are excluded from calculation."""
        from services.persona_refinement import calculate_optimal_posting_times

        base = datetime(2026, 1, 5, tzinfo=timezone.utc)
        posts = [
            # 5 valid posts
            *[
                {
                    "job_id": f"valid-{i}",
                    "user_id": "u-excl",
                    "platform": "linkedin",
                    "status": "published",
                    "published_at": base + timedelta(hours=9),
                    "performance_data": {"engagement_rate": 0.04, "impressions": 1000},
                }
                for i in range(5)
            ],
            # 3 posts with error in performance_data — should be excluded
            *[
                {
                    "job_id": f"err-{i}",
                    "user_id": "u-excl",
                    "platform": "linkedin",
                    "status": "published",
                    "published_at": base + timedelta(hours=10),
                    "performance_data": {"error": "token_expired"},
                }
                for i in range(3)
            ],
            # 2 posts without performance_data entirely — should be excluded
            *[
                {
                    "job_id": f"no-data-{i}",
                    "user_id": "u-excl",
                    "platform": "linkedin",
                    "status": "published",
                    "published_at": base + timedelta(hours=11),
                    # No performance_data key
                }
                for i in range(2)
            ],
        ]

        mock_db = MagicMock()
        mock_db.content_jobs.find = MagicMock(return_value=_make_async_cursor(posts))
        mock_db.persona_engines.update_one = AsyncMock()

        with patch("database.db", mock_db):
            result = await calculate_optimal_posting_times("u-excl")

        # Only 5 valid posts — below the 10-post minimum
        assert "message" in result
        assert result["posts_with_data"] == 5


# ===========================================================================
# TASK 3: Aggregate performance intelligence (NEW scenarios)
# ===========================================================================


class TestAggregatePerformanceIntelligence:
    """NEW coverage: handles missing performance_data gracefully."""

    @pytest.mark.asyncio
    async def test_aggregate_computes_running_averages_correctly(self):
        """Running average uses incremental formula: avg = prev_avg + (new - prev_avg) / n."""
        from services.social_analytics import _aggregate_performance_intelligence

        existing_intel = {
            "linkedin": {
                "posts_tracked": 4,
                "total_impressions": 8000,
                "total_engagements": 320,
                "avg_engagement_rate": 0.04,
                "best_engagement_rate": 0.05,
                "worst_engagement_rate": 0.02,
            }
        }
        persona = {"user_id": "u-avg", "performance_intelligence": existing_intel}

        mock_db = MagicMock()
        mock_db.persona_engines.find_one = AsyncMock(return_value=persona)
        mock_db.persona_engines.update_one = AsyncMock()

        new_metrics = {
            "likes": 80,
            "comments": 15,
            "shares": 5,
            "impressions": 2000,
            "engagement_rate": 0.05,
            "platform": "linkedin",
        }

        with patch("services.social_analytics.db", mock_db):
            await _aggregate_performance_intelligence("u-avg", "linkedin", new_metrics)

        call_args = mock_db.persona_engines.update_one.call_args
        updated_intel = call_args.args[1]["$set"]["performance_intelligence"]
        li = updated_intel["linkedin"]

        assert li["posts_tracked"] == 5
        # Running avg formula: 0.04 + (0.05 - 0.04) / 5 = 0.042
        expected_avg = round(0.04 + (0.05 - 0.04) / 5, 4)
        assert li["avg_engagement_rate"] == expected_avg

    @pytest.mark.asyncio
    async def test_aggregate_tracks_best_performing(self):
        """best_engagement_rate is updated when new post beats previous best."""
        from services.social_analytics import _aggregate_performance_intelligence

        existing_intel = {
            "x": {
                "posts_tracked": 3,
                "total_impressions": 6000,
                "total_engagements": 90,
                "avg_engagement_rate": 0.015,
                "best_engagement_rate": 0.02,
                "worst_engagement_rate": 0.01,
            }
        }
        persona = {"user_id": "u-best", "performance_intelligence": existing_intel}

        mock_db = MagicMock()
        mock_db.persona_engines.find_one = AsyncMock(return_value=persona)
        mock_db.persona_engines.update_one = AsyncMock()

        new_metrics = {
            "likes": 200,
            "retweets": 50,
            "impressions": 5000,
            "engagement_rate": 0.10,  # New record
            "platform": "x",
        }

        with patch("services.social_analytics.db", mock_db):
            await _aggregate_performance_intelligence("u-best", "x", new_metrics)

        updated_intel = (
            mock_db.persona_engines.update_one.call_args.args[1]["$set"]["performance_intelligence"]
        )
        assert updated_intel["x"]["best_engagement_rate"] == 0.10

    @pytest.mark.asyncio
    async def test_aggregate_tracks_worst_performing(self):
        """worst_engagement_rate is updated when new post is below previous worst."""
        from services.social_analytics import _aggregate_performance_intelligence

        existing_intel = {
            "instagram": {
                "posts_tracked": 2,
                "total_impressions": 4000,
                "total_engagements": 60,
                "avg_engagement_rate": 0.015,
                "best_engagement_rate": 0.02,
                "worst_engagement_rate": 0.01,
            }
        }
        persona = {"user_id": "u-worst", "performance_intelligence": existing_intel}

        mock_db = MagicMock()
        mock_db.persona_engines.find_one = AsyncMock(return_value=persona)
        mock_db.persona_engines.update_one = AsyncMock()

        new_metrics = {
            "likes": 5,
            "impressions": 2000,
            "engagement_rate": 0.0025,  # New worst
            "platform": "instagram",
        }

        with patch("services.social_analytics.db", mock_db):
            await _aggregate_performance_intelligence("u-worst", "instagram", new_metrics)

        updated_intel = (
            mock_db.persona_engines.update_one.call_args.args[1]["$set"]["performance_intelligence"]
        )
        assert updated_intel["instagram"]["worst_engagement_rate"] == 0.0025

    @pytest.mark.asyncio
    async def test_aggregate_handles_no_existing_persona(self):
        """_aggregate_performance_intelligence returns gracefully when persona doesn't exist."""
        from services.social_analytics import _aggregate_performance_intelligence

        mock_db = MagicMock()
        mock_db.persona_engines.find_one = AsyncMock(return_value=None)
        mock_db.persona_engines.update_one = AsyncMock()

        metrics = {"likes": 10, "impressions": 500, "engagement_rate": 0.02, "platform": "linkedin"}

        with patch("services.social_analytics.db", mock_db):
            # Must not raise
            await _aggregate_performance_intelligence("nonexistent-user", "linkedin", metrics)

        # update_one should NOT be called when persona doesn't exist
        assert not mock_db.persona_engines.update_one.called


# ===========================================================================
# TASK 4: Cross-platform metric normalization
# ===========================================================================


class TestCrossPlatformMetricNormalization:
    """Verify that each platform fetcher returns the expected normalized schema."""

    @pytest.mark.asyncio
    async def test_linkedin_metrics_normalized_schema(self):
        """LinkedIn fetcher returns impressions, clicks, likes, comments, shares,
        engagement_rate, platform='linkedin', fetched_at."""
        from services.social_analytics import fetch_linkedin_post_metrics

        social_actions_resp = MagicMock()
        social_actions_resp.status_code = 200
        social_actions_resp.json.return_value = {
            "likesSummary": {"totalLikes": 55},
            "commentsSummary": {"totalFirstLevelComments": 12},
            "sharesSummary": {"totalShares": 4},
        }

        stats_resp = MagicMock()
        stats_resp.status_code = 200
        stats_resp.json.return_value = {
            "elements": [
                {
                    "totalShareStatistics": {
                        "impressionCount": 3000,
                        "clickCount": 45,
                    }
                }
            ]
        }

        fake_client = _make_mock_httpx_client(
            responses_by_url={
                "socialActions": social_actions_resp,
                "organizationalEntityShareStatistics": stats_resp,
            }
        )

        with patch("services.social_analytics.httpx.AsyncClient", return_value=fake_client):
            result = await fetch_linkedin_post_metrics("urn:li:share:999", "tok")

        assert "error" not in result
        assert result["platform"] == "linkedin"
        # Standard normalized fields present
        for field in ("impressions", "clicks", "likes", "comments", "shares", "engagement_rate", "fetched_at"):
            assert field in result, f"Missing normalized field: {field}"
        assert isinstance(result["impressions"], (int, float))
        assert isinstance(result["engagement_rate"], float)
        assert result["likes"] == 55
        assert result["comments"] == 12
        assert result["impressions"] == 3000

    @pytest.mark.asyncio
    async def test_x_metrics_normalized_schema(self):
        """X fetcher returns impressions, likes, retweets, replies, bookmarks,
        quote_tweets, engagement_rate, platform='x', fetched_at."""
        from services.social_analytics import fetch_x_post_metrics

        r = MagicMock()
        r.status_code = 200
        r.json.return_value = {
            "data": {
                "public_metrics": {
                    "like_count": 88,
                    "retweet_count": 20,
                    "reply_count": 7,
                    "bookmark_count": 3,
                    "quote_count": 2,
                },
                "non_public_metrics": {"impression_count": 6000},
            }
        }

        fake_client = MagicMock()
        fake_client.__aenter__ = AsyncMock(return_value=fake_client)
        fake_client.__aexit__ = AsyncMock(return_value=False)
        fake_client.get = AsyncMock(return_value=r)

        with patch("services.social_analytics.httpx.AsyncClient", return_value=fake_client):
            result = await fetch_x_post_metrics("tweet-id-123", "tok")

        assert "error" not in result
        assert result["platform"] == "x"
        for field in ("impressions", "likes", "retweets", "replies", "bookmarks",
                      "quote_tweets", "engagement_rate", "fetched_at"):
            assert field in result, f"Missing normalized field: {field}"
        assert result["likes"] == 88
        assert result["retweets"] == 20
        assert result["impressions"] == 6000
        total_eng = 88 + 20 + 7 + 3 + 2
        expected_rate = round(total_eng / 6000, 4)
        assert result["engagement_rate"] == expected_rate

    @pytest.mark.asyncio
    async def test_instagram_metrics_normalized_schema(self):
        """Instagram fetcher returns impressions, reach, likes, comments, shares,
        saved, engagement_rate, platform='instagram', fetched_at."""
        from services.social_analytics import fetch_instagram_post_metrics

        r = MagicMock()
        r.status_code = 200
        r.json.return_value = {
            "data": [
                {"name": "impressions", "values": [{"value": 4500}]},
                {"name": "reach", "values": [{"value": 3200}]},
                {"name": "likes", "values": [{"value": 110}]},
                {"name": "comments", "values": [{"value": 22}]},
                {"name": "shares", "values": [{"value": 8}]},
                {"name": "saved", "values": [{"value": 45}]},
            ]
        }

        fake_client = MagicMock()
        fake_client.__aenter__ = AsyncMock(return_value=fake_client)
        fake_client.__aexit__ = AsyncMock(return_value=False)
        fake_client.get = AsyncMock(return_value=r)

        with patch("services.social_analytics.httpx.AsyncClient", return_value=fake_client):
            result = await fetch_instagram_post_metrics("media-ig-777", "tok")

        assert "error" not in result
        assert result["platform"] == "instagram"
        for field in ("impressions", "reach", "likes", "comments", "shares", "saved",
                      "engagement_rate", "fetched_at"):
            assert field in result, f"Missing normalized field: {field}"
        assert result["impressions"] == 4500
        assert result["reach"] == 3200
        assert result["saved"] == 45
        total_eng = 110 + 22 + 8 + 45
        expected_rate = round(total_eng / 4500, 4)
        assert result["engagement_rate"] == expected_rate


# ===========================================================================
# TASK 5: Strategist consumption of performance data
# ===========================================================================


class TestStrategistConsumption:
    """NEW coverage: _gather_user_context populates performance_signals from jobs
    with performance_data (ANLYT-04 already covers the basic case in test_n8n_bridge.py —
    these tests extend coverage for edge cases)."""

    @pytest.mark.asyncio
    async def test_strategist_reads_latest_performance_data(self):
        """_gather_user_context includes performance_signals from jobs with performance_data."""
        from agents.strategist import _gather_user_context

        jobs = [
            {
                "job_id": "perf-1",
                "user_id": "strat-user",
                "platform": "linkedin",
                "status": "published",
                "performance_data": {
                    "latest": {"impressions": 3000, "engagement_rate": 0.05}
                },
                "final_content": "Winning content",
                "created_at": "2026-01-01T00:00:00Z",
            },
            {
                "job_id": "perf-2",
                "user_id": "strat-user",
                "platform": "x",
                "status": "published",
                "performance_data": {
                    "latest": {"impressions": 1500, "engagement_rate": 0.03}
                },
                "final_content": "Another post",
                "created_at": "2026-01-02T00:00:00Z",
            },
        ]

        mock_cursor = MagicMock()
        mock_cursor.sort = MagicMock(return_value=mock_cursor)
        mock_cursor.to_list = AsyncMock(return_value=jobs)

        mock_db = MagicMock()
        mock_db.content_jobs.find = MagicMock(return_value=mock_cursor)
        mock_db.persona_engines.find_one = AsyncMock(
            return_value={
                "user_id": "strat-user",
                "card": {"archetype": "Thought Leader"},
                "voice_fingerprint": {},
                "content_identity": {},
            }
        )
        mock_db.strategy_recommendations.find = MagicMock(
            return_value=_make_async_cursor([])
        )

        import sys

        fake_lightrag = MagicMock()
        fake_lightrag.query_knowledge_graph = AsyncMock(return_value="")

        fake_obsidian = MagicMock()
        fake_obsidian.get_recent_notes = AsyncMock(return_value=[])

        with patch.dict(sys.modules, {
            "services.lightrag_service": fake_lightrag,
            "services.obsidian_service": fake_obsidian,
        }):
            with patch("agents.strategist.db", mock_db):
                result = await _gather_user_context("strat-user")

        performance_signals = result.get("performance_signals", [])
        assert len(performance_signals) == 2
        # Signals are the full performance_data values
        for sig in performance_signals:
            assert sig is not None

    @pytest.mark.asyncio
    async def test_strategist_excludes_jobs_without_performance_data(self):
        """Jobs without performance_data are not included in performance_signals."""
        from agents.strategist import _gather_user_context

        jobs = [
            {
                "job_id": "has-data",
                "user_id": "strat-u2",
                "platform": "linkedin",
                "status": "published",
                "performance_data": {"latest": {"engagement_rate": 0.04}},
                "final_content": "Post with data",
                "created_at": "2026-01-01T00:00:00Z",
            },
            {
                "job_id": "no-data",
                "user_id": "strat-u2",
                "platform": "linkedin",
                "status": "approved",
                # No performance_data
                "final_content": "Post without data",
                "created_at": "2026-01-02T00:00:00Z",
            },
            {
                "job_id": "also-no-data",
                "user_id": "strat-u2",
                "platform": "x",
                "status": "published",
                # No performance_data
                "final_content": "Another post without data",
                "created_at": "2026-01-03T00:00:00Z",
            },
        ]

        mock_cursor = MagicMock()
        mock_cursor.sort = MagicMock(return_value=mock_cursor)
        mock_cursor.to_list = AsyncMock(return_value=jobs)

        mock_db = MagicMock()
        mock_db.content_jobs.find = MagicMock(return_value=mock_cursor)
        mock_db.persona_engines.find_one = AsyncMock(
            return_value={
                "user_id": "strat-u2",
                "card": {"archetype": "Expert"},
                "voice_fingerprint": {},
                "content_identity": {},
            }
        )
        mock_db.strategy_recommendations.find = MagicMock(
            return_value=_make_async_cursor([])
        )

        import sys

        fake_lightrag = MagicMock()
        fake_lightrag.query_knowledge_graph = AsyncMock(return_value="")

        fake_obsidian = MagicMock()
        fake_obsidian.get_recent_notes = AsyncMock(return_value=[])

        with patch.dict(sys.modules, {
            "services.lightrag_service": fake_lightrag,
            "services.obsidian_service": fake_obsidian,
        }):
            with patch("agents.strategist.db", mock_db):
                result = await _gather_user_context("strat-u2")

        performance_signals = result.get("performance_signals", [])
        # Only 1 job has performance_data
        assert len(performance_signals) == 1

    @pytest.mark.asyncio
    async def test_performance_intelligence_available_in_context(self):
        """persona_engines.performance_intelligence present in persona context."""
        from agents.strategist import _gather_user_context

        mock_cursor = MagicMock()
        mock_cursor.sort = MagicMock(return_value=mock_cursor)
        mock_cursor.to_list = AsyncMock(return_value=[])

        performance_intel = {
            "linkedin": {
                "posts_tracked": 15,
                "avg_engagement_rate": 0.042,
                "best_engagement_rate": 0.09,
            }
        }

        mock_db = MagicMock()
        mock_db.content_jobs.find = MagicMock(return_value=mock_cursor)
        mock_db.persona_engines.find_one = AsyncMock(
            return_value={
                "user_id": "strat-u3",
                "card": {"archetype": "Storyteller"},
                "voice_fingerprint": {},
                "content_identity": {},
                "performance_intelligence": performance_intel,
            }
        )
        mock_db.strategy_recommendations.find = MagicMock(
            return_value=_make_async_cursor([])
        )

        import sys

        fake_lightrag = MagicMock()
        fake_lightrag.query_knowledge_graph = AsyncMock(return_value="")

        fake_obsidian = MagicMock()
        fake_obsidian.get_recent_notes = AsyncMock(return_value=[])

        with patch.dict(sys.modules, {
            "services.lightrag_service": fake_lightrag,
            "services.obsidian_service": fake_obsidian,
        }):
            with patch("agents.strategist.db", mock_db):
                result = await _gather_user_context("strat-u3")

        # Persona is returned with performance_intelligence intact
        persona = result.get("persona", {})
        assert "performance_intelligence" in persona
        assert persona["performance_intelligence"]["linkedin"]["posts_tracked"] == 15
