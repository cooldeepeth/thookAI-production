"""Volume pricing, credit balance, and tier boundary tests (BILL-05).

Covers:
- calculate_plan_credits: per-operation calculation
- calculate_plan_price: volume tier boundaries, rounding
- get_features_for_price: feature unlocks at price thresholds
- build_plan_preview: full plan preview dict
- get_operation_cost: operation name lookup
- get_all_tiers: tier list completeness
- get_credit_balance: balance, tier, allowance, low-balance detection
- deduct_credits: happy path, insufficient credits, starter cap enforcement
- add_credits: atomicity (covered separately in test_p0_add_credits_atomic.py)
- get_usage_history: days filter, limit, summary aggregation
- check_feature_access: starter vs custom features
- Boundary values: exactly 0, exactly operation cost, one below

All pure-function tests need no DB. DB-backed tests use mongomock-motor.
"""

import math
import uuid
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _uid() -> str:
    return f"user_{uuid.uuid4().hex[:8]}"


def _make_user(user_id: str, **kwargs) -> dict:
    defaults = {
        "user_id": user_id,
        "email": f"{user_id}@test.com",
        "subscription_tier": "starter",
        "credits": 200,
        "credit_allowance": 0,
        "onboarding_completed": True,
    }
    defaults.update(kwargs)
    return defaults


# ---------------------------------------------------------------------------
# calculate_plan_credits — pure function
# ---------------------------------------------------------------------------


class TestCalculatePlanCredits:
    """calculate_plan_credits multiplies qty × credit cost per operation."""

    def test_zero_returns_zero(self):
        from services.credits import calculate_plan_credits
        assert calculate_plan_credits() == 0

    def test_text_posts_only(self):
        from services.credits import calculate_plan_credits, CreditOperation
        result = calculate_plan_credits(text_posts=10)
        assert result == 10 * CreditOperation.CONTENT_CREATE.value  # 100

    def test_images_only(self):
        from services.credits import calculate_plan_credits, CreditOperation
        result = calculate_plan_credits(images=5)
        assert result == 5 * CreditOperation.IMAGE_GENERATE.value  # 40

    def test_videos_only(self):
        from services.credits import calculate_plan_credits, CreditOperation
        result = calculate_plan_credits(videos=2)
        assert result == 2 * CreditOperation.VIDEO_GENERATE.value  # 100

    def test_mixed_usage(self):
        from services.credits import calculate_plan_credits, CreditOperation
        result = calculate_plan_credits(text_posts=10, images=5, videos=2, carousels=3)
        expected = (
            10 * CreditOperation.CONTENT_CREATE.value
            + 5 * CreditOperation.IMAGE_GENERATE.value
            + 2 * CreditOperation.VIDEO_GENERATE.value
            + 3 * CreditOperation.CAROUSEL_GENERATE.value
        )
        assert result == expected  # 285

    def test_repurposes_and_voice(self):
        from services.credits import calculate_plan_credits, CreditOperation
        result = calculate_plan_credits(repurposes=10, voice_narrations=3)
        expected = (
            10 * CreditOperation.REPURPOSE.value
            + 3 * CreditOperation.VOICE_NARRATION.value
        )
        assert result == expected


# ---------------------------------------------------------------------------
# calculate_plan_price — pure function, volume tier boundaries
# ---------------------------------------------------------------------------


class TestCalculatePlanPrice:
    """Volume tiers: ≤500 @$0.06, ≤1500 @$0.05, ≤5000 @$0.035, >5000 @$0.03."""

    def test_zero_credits_returns_zero(self):
        from services.credits import calculate_plan_price
        assert calculate_plan_price(0) == 0.0

    def test_100_credits_tier1(self):
        from services.credits import calculate_plan_price
        assert calculate_plan_price(100) == math.ceil(100 * 0.06)  # 6

    def test_500_credits_tier1_boundary(self):
        from services.credits import calculate_plan_price
        # 500 is AT tier1 boundary (up_to=500)
        assert calculate_plan_price(500) == math.ceil(500 * 0.06)  # 30

    def test_501_credits_tier2(self):
        from services.credits import calculate_plan_price
        # 501 crosses into tier2 (up_to=1500 @$0.05)
        assert calculate_plan_price(501) == math.ceil(501 * 0.05)  # 26

    def test_1000_credits_tier2(self):
        from services.credits import calculate_plan_price
        assert calculate_plan_price(1000) == math.ceil(1000 * 0.05)  # 50

    def test_1500_credits_tier2_boundary(self):
        from services.credits import calculate_plan_price
        assert calculate_plan_price(1500) == math.ceil(1500 * 0.05)  # 75

    def test_1501_credits_tier3(self):
        from services.credits import calculate_plan_price
        assert calculate_plan_price(1501) == math.ceil(1501 * 0.035)  # 53

    def test_3000_credits_tier3(self):
        from services.credits import calculate_plan_price
        assert calculate_plan_price(3000) == math.ceil(3000 * 0.035)  # 105

    def test_5000_credits_tier3_boundary(self):
        from services.credits import calculate_plan_price
        assert calculate_plan_price(5000) == math.ceil(5000 * 0.035)  # 175

    def test_5001_credits_tier4(self):
        from services.credits import calculate_plan_price
        assert calculate_plan_price(5001) == math.ceil(5001 * 0.03)  # 151

    def test_6000_credits_tier4(self):
        from services.credits import calculate_plan_price
        assert calculate_plan_price(6000) == math.ceil(6000 * 0.03)  # 180

    def test_price_always_rounded_up(self):
        """Price should be rounded UP to the nearest dollar (math.ceil)."""
        from services.credits import calculate_plan_price
        # 100 credits * $0.06 = $6.00 (exact)
        assert calculate_plan_price(100) == 6
        # 101 credits * $0.06 = $6.06 → ceil = 7
        assert calculate_plan_price(101) == math.ceil(101 * 0.06)


# ---------------------------------------------------------------------------
# get_features_for_price — pure function
# ---------------------------------------------------------------------------


class TestGetFeaturesForPrice:

    def test_zero_spend_returns_base_features(self):
        """$0/month → base feature set (paid entry)."""
        from services.credits import get_features_for_price, FEATURE_THRESHOLDS
        features = get_features_for_price(0)
        assert isinstance(features, dict)
        assert "platforms" in features

    def test_29_99_returns_at_least_base_features(self):
        """$29.99/month → at least base features unlocked."""
        from services.credits import get_features_for_price
        features = get_features_for_price(29.99)
        assert "platforms" in features
        assert features.get("series_enabled") is True

    def test_79_unlocks_growth_features(self):
        """$79/month → growth tier features (voice_enabled=True)."""
        from services.credits import get_features_for_price, FEATURE_THRESHOLDS
        features = get_features_for_price(79)
        growth = FEATURE_THRESHOLDS["growth"]
        assert features.get("voice_enabled") == growth.get("voice_enabled")

    def test_149_unlocks_scale_features(self):
        """$149/month → scale tier features (api_access=True)."""
        from services.credits import get_features_for_price, FEATURE_THRESHOLDS
        features = get_features_for_price(149)
        scale = FEATURE_THRESHOLDS["scale"]
        assert features.get("api_access") == scale.get("api_access")

    def test_returns_dict_not_none(self):
        from services.credits import get_features_for_price
        result = get_features_for_price(50)
        assert result is not None
        assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# build_plan_preview — pure function
# ---------------------------------------------------------------------------


class TestBuildPlanPreview:

    def test_zero_usage_returns_zero_price(self):
        from services.credits import build_plan_preview
        result = build_plan_preview()
        assert result["total_credits"] == 0
        assert result["monthly_price_usd"] == 0

    def test_text_posts_only_preview(self):
        from services.credits import build_plan_preview, CreditOperation
        result = build_plan_preview(text_posts=20)
        expected_credits = 20 * CreditOperation.CONTENT_CREATE.value
        assert result["total_credits"] == expected_credits
        assert result["monthly_price_usd"] > 0
        assert "features" in result
        assert "breakdown" in result

    def test_preview_includes_all_keys(self):
        """build_plan_preview must return all required keys."""
        from services.credits import build_plan_preview
        result = build_plan_preview(text_posts=10, images=5)
        required_keys = ["total_credits", "monthly_price_usd", "features", "breakdown",
                         "volume_tier", "price_per_credit"]
        for key in required_keys:
            assert key in result, f"Missing key: {key}"

    def test_high_usage_unlocks_growth_tier(self):
        """Enough usage to hit growth spend → growth features unlocked."""
        from services.credits import build_plan_preview, FEATURE_THRESHOLDS
        # Need $79 for growth. Using tier1: ceil(credits * 0.06) >= 79 → credits >= 1317.
        # 1580+ credits → at $0.05/credit (tier2) → ceil(1580 * 0.05) = ceil(79) = 79 ✓
        # Actually tier2 (501-1500): 1500 credits → 75; tier3 (1501-5000): 1501 credits → ceil(52.5) = 53
        # So we need $79+ at tier2 rates: 79/0.05 = 1580 → but that's tier3 range.
        # At tier3 ($0.035): need ceil(N * 0.035) >= 79 → N >= 2257 credits
        # 50 videos * 50 = 2500 credits → ceil(2500 * 0.035) = ceil(87.5) = 88 ≥ 79 ✓
        result = build_plan_preview(videos=50)
        assert result["monthly_price_usd"] >= FEATURE_THRESHOLDS["growth"]["min_monthly_usd"]
        assert result["features"].get("voice_enabled") is True

    def test_breakdown_subtotals_sum_to_total(self):
        """Sum of all subtotals in breakdown equals total_credits."""
        from services.credits import build_plan_preview
        result = build_plan_preview(text_posts=10, images=3, videos=1, repurposes=5)
        total_from_breakdown = sum(v["subtotal"] for v in result["breakdown"].values())
        assert total_from_breakdown == result["total_credits"]

    def test_volume_tier_label_standard_for_low_credits(self):
        """Low credit count → volume_tier = 'standard'."""
        from services.credits import build_plan_preview
        result = build_plan_preview(text_posts=5)  # 50 credits, well below 500
        assert result["volume_tier"] == "standard"


# ---------------------------------------------------------------------------
# get_operation_cost — pure function
# ---------------------------------------------------------------------------


class TestGetOperationCost:

    def test_content_create_cost(self):
        from services.credits import get_operation_cost, CreditOperation
        assert get_operation_cost("CONTENT_CREATE") == CreditOperation.CONTENT_CREATE.value

    def test_video_generate_cost(self):
        from services.credits import get_operation_cost, CreditOperation
        assert get_operation_cost("VIDEO_GENERATE") == CreditOperation.VIDEO_GENERATE.value

    def test_case_insensitive(self):
        from services.credits import get_operation_cost
        assert get_operation_cost("content_create") == get_operation_cost("CONTENT_CREATE")

    def test_invalid_operation_returns_default(self):
        from services.credits import get_operation_cost
        result = get_operation_cost("NONEXISTENT_OP")
        # Returns 0 (default) for unknown operations
        assert result == 0

    def test_repurpose_cost(self):
        from services.credits import get_operation_cost, CreditOperation
        assert get_operation_cost("REPURPOSE") == CreditOperation.REPURPOSE.value


# ---------------------------------------------------------------------------
# get_all_tiers — pure function
# ---------------------------------------------------------------------------


class TestGetAllTiers:

    def test_returns_list(self):
        from services.credits import get_all_tiers
        result = get_all_tiers()
        assert isinstance(result, list)
        assert len(result) >= 2

    def test_includes_starter_tier(self):
        from services.credits import get_all_tiers
        tiers = get_all_tiers()
        ids = [t["id"] for t in tiers]
        assert "starter" in ids

    def test_includes_custom_tier(self):
        from services.credits import get_all_tiers
        tiers = get_all_tiers()
        ids = [t["id"] for t in tiers]
        assert "custom" in ids

    def test_starter_tier_has_no_monthly_cost(self):
        from services.credits import get_all_tiers
        tiers = get_all_tiers()
        starter = next(t for t in tiers if t["id"] == "starter")
        assert starter["price_monthly"] == 0

    def test_custom_tier_has_volume_tiers(self):
        from services.credits import get_all_tiers
        tiers = get_all_tiers()
        custom = next(t for t in tiers if t["id"] == "custom")
        assert "volume_tiers" in custom
        assert len(custom["volume_tiers"]) > 0


# ---------------------------------------------------------------------------
# get_credit_balance — DB-backed
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestGetCreditBalance:

    async def test_returns_balance_for_existing_user(self, mongomock_db):
        """Basic balance fetch returns success with credits and tier."""
        user_id = _uid()
        await mongomock_db.users.insert_one(_make_user(user_id, credits=150, subscription_tier="starter"))

        with patch("database.db", mongomock_db):
            from services.credits import get_credit_balance
            result = await get_credit_balance(user_id)

        assert result["success"] is True
        assert result["credits"] == 150
        assert result["tier"] == "starter"

    async def test_returns_error_for_nonexistent_user(self, mongomock_db):
        """Nonexistent user → error response."""
        with patch("database.db", mongomock_db):
            from services.credits import get_credit_balance
            result = await get_credit_balance("nobody")

        assert result["success"] is False
        assert "not found" in result.get("error", "").lower()

    async def test_includes_tier_name(self, mongomock_db):
        """Response includes tier_name field."""
        user_id = _uid()
        await mongomock_db.users.insert_one(_make_user(user_id))

        with patch("database.db", mongomock_db):
            from services.credits import get_credit_balance
            result = await get_credit_balance(user_id)

        assert "tier_name" in result

    async def test_low_balance_flag_for_nearly_depleted(self, mongomock_db):
        """User with credits below 20% threshold → is_low_balance=True."""
        user_id = _uid()
        await mongomock_db.users.insert_one(
            _make_user(user_id, credits=10, subscription_tier="starter")
        )

        with patch("database.db", mongomock_db):
            from services.credits import get_credit_balance
            result = await get_credit_balance(user_id)

        # 10 credits out of 200 signup credits = 5% → below 20% threshold
        assert result["is_low_balance"] is True

    async def test_sufficient_balance_not_low(self, mongomock_db):
        """User with plenty of credits → is_low_balance=False."""
        user_id = _uid()
        await mongomock_db.users.insert_one(
            _make_user(user_id, credits=180)  # 90% of 200 signup credits
        )

        with patch("database.db", mongomock_db):
            from services.credits import get_credit_balance
            result = await get_credit_balance(user_id)

        assert result["is_low_balance"] is False

    async def test_custom_plan_user_shows_plan_config(self, mongomock_db):
        """Custom plan user includes plan_config in response."""
        user_id = _uid()
        plan_config = {"monthly_credits": 500, "monthly_price_usd": 30}
        await mongomock_db.users.insert_one(
            _make_user(user_id, subscription_tier="custom", plan_config=plan_config)
        )

        with patch("database.db", mongomock_db):
            from services.credits import get_credit_balance
            result = await get_credit_balance(user_id)

        assert result["success"] is True
        assert result["plan_config"] is not None


# ---------------------------------------------------------------------------
# deduct_credits — DB-backed
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestDeductCredits:

    async def test_happy_path_reduces_balance(self, mongomock_db):
        """Successful deduction reduces credits by operation cost."""
        user_id = _uid()
        from services.credits import CreditOperation
        cost = CreditOperation.CONTENT_CREATE.value  # 10
        await mongomock_db.users.insert_one(
            _make_user(user_id, credits=100, subscription_tier="custom")
        )

        with patch("database.db", mongomock_db):
            from services.credits import deduct_credits
            result = await deduct_credits(user_id, CreditOperation.CONTENT_CREATE)

        assert result["success"] is True
        assert result["credits_used"] == cost
        assert result["new_balance"] == 100 - cost

        user = await mongomock_db.users.find_one({"user_id": user_id})
        assert user["credits"] == 100 - cost

    async def test_records_transaction(self, mongomock_db):
        """Successful deduction writes a credit_transactions record."""
        user_id = _uid()
        from services.credits import CreditOperation
        await mongomock_db.users.insert_one(
            _make_user(user_id, credits=100, subscription_tier="custom")
        )

        with patch("database.db", mongomock_db):
            from services.credits import deduct_credits
            await deduct_credits(user_id, CreditOperation.CONTENT_CREATE)

        txn = await mongomock_db.credit_transactions.find_one({"user_id": user_id})
        assert txn is not None
        assert txn["type"] == "deduction"
        assert txn["operation"] == "CONTENT_CREATE"

    async def test_insufficient_credits_returns_error(self, mongomock_db):
        """Insufficient credits → error, balance unchanged."""
        user_id = _uid()
        from services.credits import CreditOperation
        low_credits = CreditOperation.CONTENT_CREATE.value - 1  # 9 credits, need 10
        await mongomock_db.users.insert_one(
            _make_user(user_id, credits=low_credits, subscription_tier="custom")
        )

        with patch("database.db", mongomock_db):
            from services.credits import deduct_credits
            result = await deduct_credits(user_id, CreditOperation.CONTENT_CREATE)

        assert result["success"] is False
        assert "credits" in result.get("error", "").lower()

        # Balance must be unchanged
        user = await mongomock_db.users.find_one({"user_id": user_id})
        assert user["credits"] == low_credits

    async def test_zero_credits_deduction_fails(self, mongomock_db):
        """Exactly 0 credits → deduction fails."""
        user_id = _uid()
        from services.credits import CreditOperation
        await mongomock_db.users.insert_one(
            _make_user(user_id, credits=0, subscription_tier="custom")
        )

        with patch("database.db", mongomock_db):
            from services.credits import deduct_credits
            result = await deduct_credits(user_id, CreditOperation.VIRAL_PREDICT)  # cost=1

        assert result["success"] is False

    async def test_exact_operation_cost_succeeds_zero_balance(self, mongomock_db):
        """Credits == operation cost → deduction succeeds, balance = 0."""
        user_id = _uid()
        from services.credits import CreditOperation
        exact = CreditOperation.CONTENT_CREATE.value  # 10
        await mongomock_db.users.insert_one(
            _make_user(user_id, credits=exact, subscription_tier="custom")
        )

        with patch("database.db", mongomock_db):
            from services.credits import deduct_credits
            result = await deduct_credits(user_id, CreditOperation.CONTENT_CREATE)

        assert result["success"] is True
        assert result["new_balance"] == 0

    async def test_starter_video_cap_enforced(self, mongomock_db):
        """Starter user hitting video hard cap → returns cap error."""
        user_id = _uid()
        from services.credits import CreditOperation, STARTER_CONFIG
        cap = STARTER_CONFIG["features"]["video_max"]

        await mongomock_db.users.insert_one(
            _make_user(user_id, credits=1000, subscription_tier="starter")
        )

        # Insert fake transactions to simulate hitting the cap
        for _ in range(cap):
            await mongomock_db.credit_transactions.insert_one({
                "user_id": user_id,
                "type": "deduction",
                "operation": "VIDEO_GENERATE",
                "amount": CreditOperation.VIDEO_GENERATE.value,
            })

        with patch("database.db", mongomock_db):
            from services.credits import deduct_credits
            result = await deduct_credits(user_id, CreditOperation.VIDEO_GENERATE)

        assert result["success"] is False
        assert result.get("upgrade_required") is True
        assert "video" in result.get("error", "").lower()

    async def test_starter_carousel_cap_enforced(self, mongomock_db):
        """Starter user hitting carousel hard cap → returns cap error."""
        user_id = _uid()
        from services.credits import CreditOperation, STARTER_CONFIG
        cap = STARTER_CONFIG["features"]["carousel_max"]

        await mongomock_db.users.insert_one(
            _make_user(user_id, credits=1000, subscription_tier="starter")
        )

        for _ in range(cap):
            await mongomock_db.credit_transactions.insert_one({
                "user_id": user_id,
                "type": "deduction",
                "operation": "CAROUSEL_GENERATE",
                "amount": CreditOperation.CAROUSEL_GENERATE.value,
            })

        with patch("database.db", mongomock_db):
            from services.credits import deduct_credits
            result = await deduct_credits(user_id, CreditOperation.CAROUSEL_GENERATE)

        assert result["success"] is False
        assert result.get("upgrade_required") is True


# ---------------------------------------------------------------------------
# get_usage_history — DB-backed
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestGetUsageHistory:

    async def test_returns_transactions_for_user(self, mongomock_db):
        """Usage history for user with transactions returns success with transaction list."""
        user_id = _uid()
        now = datetime.now(timezone.utc)

        for i in range(5):
            await mongomock_db.credit_transactions.insert_one({
                "user_id": user_id,
                "type": "deduction",
                "operation": "CONTENT_CREATE",
                "amount": 10,
                "balance_after": 190 - (i * 10),
                "created_at": now - timedelta(days=i),
            })

        with patch("database.db", mongomock_db):
            from services.credits import get_usage_history
            result = await get_usage_history(user_id)

        assert result["success"] is True
        assert len(result["transactions"]) == 5

    async def test_days_filter_excludes_old_transactions(self, mongomock_db):
        """Transactions older than 'days' parameter are excluded."""
        user_id = _uid()
        now = datetime.now(timezone.utc)

        # Recent transaction (5 days ago)
        await mongomock_db.credit_transactions.insert_one({
            "user_id": user_id,
            "type": "deduction",
            "operation": "CONTENT_CREATE",
            "amount": 10,
            "balance_after": 90,
            "created_at": now - timedelta(days=5),
        })
        # Old transaction (45 days ago)
        await mongomock_db.credit_transactions.insert_one({
            "user_id": user_id,
            "type": "deduction",
            "operation": "IMAGE_GENERATE",
            "amount": 8,
            "balance_after": 82,
            "created_at": now - timedelta(days=45),
        })

        with patch("database.db", mongomock_db):
            from services.credits import get_usage_history
            result = await get_usage_history(user_id, days=30)

        assert result["success"] is True
        assert len(result["transactions"]) == 1  # Only recent one

    async def test_limit_respected(self, mongomock_db):
        """limit parameter caps the number of returned transactions."""
        user_id = _uid()
        now = datetime.now(timezone.utc)

        for i in range(20):
            await mongomock_db.credit_transactions.insert_one({
                "user_id": user_id,
                "type": "deduction",
                "operation": "CONTENT_CREATE",
                "amount": 10,
                "balance_after": 200 - (i * 10),
                "created_at": now - timedelta(hours=i),
            })

        with patch("database.db", mongomock_db):
            from services.credits import get_usage_history
            result = await get_usage_history(user_id, limit=5)

        assert len(result["transactions"]) == 5

    async def test_summary_aggregates_totals(self, mongomock_db):
        """Summary section correctly totals deductions and additions."""
        user_id = _uid()
        now = datetime.now(timezone.utc)

        await mongomock_db.credit_transactions.insert_one({
            "user_id": user_id,
            "type": "deduction",
            "operation": "CONTENT_CREATE",
            "amount": 10,
            "balance_after": 90,
            "created_at": now,
        })
        await mongomock_db.credit_transactions.insert_one({
            "user_id": user_id,
            "type": "addition",
            "source": "purchase",
            "amount": 100,
            "balance_after": 190,
            "created_at": now,
        })

        with patch("database.db", mongomock_db):
            from services.credits import get_usage_history
            result = await get_usage_history(user_id)

        assert result["summary"]["total_deducted"] == 10
        assert result["summary"]["total_added"] == 100
        assert result["summary"]["net_change"] == 90

    async def test_empty_history_returns_empty_list(self, mongomock_db):
        """User with no transactions → empty list, not an error."""
        user_id = _uid()

        with patch("database.db", mongomock_db):
            from services.credits import get_usage_history
            result = await get_usage_history(user_id)

        assert result["success"] is True
        assert result["transactions"] == []


# ---------------------------------------------------------------------------
# check_feature_access — DB-backed
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestCheckFeatureAccess:

    async def test_starter_series_disabled(self, mongomock_db):
        """Starter user: series_enabled=False → allowed=False."""
        user_id = _uid()
        await mongomock_db.users.insert_one(
            _make_user(user_id, subscription_tier="starter")
        )

        with patch("database.db", mongomock_db):
            from services.credits import check_feature_access
            result = await check_feature_access(user_id, "series_enabled")

        assert result["allowed"] is False

    async def test_starter_voice_disabled(self, mongomock_db):
        """Starter user: voice_enabled=False → allowed=False."""
        user_id = _uid()
        await mongomock_db.users.insert_one(
            _make_user(user_id, subscription_tier="starter")
        )

        with patch("database.db", mongomock_db):
            from services.credits import check_feature_access
            result = await check_feature_access(user_id, "voice_enabled")

        assert result["allowed"] is False

    async def test_custom_plan_with_features_allows_voice(self, mongomock_db):
        """Custom plan user with voice_enabled=True → allowed=True."""
        user_id = _uid()
        plan_config = {
            "monthly_credits": 500,
            "features": {"voice_enabled": True, "series_enabled": True},
        }
        await mongomock_db.users.insert_one(
            _make_user(user_id, subscription_tier="custom", plan_config=plan_config)
        )

        with patch("database.db", mongomock_db):
            from services.credits import check_feature_access
            result = await check_feature_access(user_id, "voice_enabled")

        assert result["allowed"] is True

    async def test_unknown_feature_returns_error(self, mongomock_db):
        """Unknown feature name → allowed=False with error."""
        user_id = _uid()
        await mongomock_db.users.insert_one(_make_user(user_id))

        with patch("database.db", mongomock_db):
            from services.credits import check_feature_access
            result = await check_feature_access(user_id, "nonexistent_feature")

        assert result["allowed"] is False

    async def test_nonexistent_user_returns_error(self, mongomock_db):
        """Nonexistent user → allowed=False with error."""
        with patch("database.db", mongomock_db):
            from services.credits import check_feature_access
            result = await check_feature_access("nobody", "voice_enabled")

        assert result["allowed"] is False
        assert "error" in result


# ---------------------------------------------------------------------------
# Boundary value tests — DB-backed (async)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestBoundaryValuesAsync:

    async def test_deduct_exactly_at_operation_cost_succeeds(self, mongomock_db):
        """Credits exactly equal to operation cost → deduction succeeds, balance=0."""
        user_id = _uid()
        from services.credits import CreditOperation
        cost = CreditOperation.AI_INSIGHTS.value  # 2
        await mongomock_db.users.insert_one(
            _make_user(user_id, credits=cost, subscription_tier="custom")
        )

        with patch("database.db", mongomock_db):
            from services.credits import deduct_credits
            result = await deduct_credits(user_id, CreditOperation.AI_INSIGHTS)

        assert result["success"] is True
        assert result["new_balance"] == 0

    async def test_deduct_one_below_operation_cost_fails(self, mongomock_db):
        """Credits one below operation cost → deduction fails."""
        user_id = _uid()
        from services.credits import CreditOperation
        cost = CreditOperation.AI_INSIGHTS.value  # 2
        await mongomock_db.users.insert_one(
            _make_user(user_id, credits=cost - 1, subscription_tier="custom")
        )

        with patch("database.db", mongomock_db):
            from services.credits import deduct_credits
            result = await deduct_credits(user_id, CreditOperation.AI_INSIGHTS)

        assert result["success"] is False


# ---------------------------------------------------------------------------
# Boundary value tests — pure functions (sync)
# ---------------------------------------------------------------------------


class TestBoundaryValuesPure:

    def test_calculate_plan_price_large_credit_count(self):
        """Very large credit count (50000) → handled without error."""
        from services.credits import calculate_plan_price
        result = calculate_plan_price(50000)
        assert result == math.ceil(50000 * 0.03)  # tier4: $0.03/credit

    def test_calculate_plan_credits_all_operations(self):
        """All operations combined produces correct sum."""
        from services.credits import calculate_plan_credits, CreditOperation
        result = calculate_plan_credits(
            text_posts=1,
            images=1,
            videos=1,
            carousels=1,
            repurposes=1,
            voice_narrations=1,
            series_plans=1,
        )
        expected = (
            CreditOperation.CONTENT_CREATE.value
            + CreditOperation.IMAGE_GENERATE.value
            + CreditOperation.VIDEO_GENERATE.value
            + CreditOperation.CAROUSEL_GENERATE.value
            + CreditOperation.REPURPOSE.value
            + CreditOperation.VOICE_NARRATION.value
            + CreditOperation.SERIES_PLAN.value
        )
        assert result == expected
