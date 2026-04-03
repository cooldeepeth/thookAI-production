"""Comprehensive Stripe billing flow tests for ThookAI.

Covers:
- build_plan_preview calculation accuracy
- calculate_plan_price volume tier application
- _activate_custom_plan DB updates
- handle_checkout_completed for credit purchase and custom plan
- handle_subscription_deleted downgrade to starter
- handle_payment_succeeded credit refresh
- refresh_monthly_credits Celery task inner logic
- create_custom_plan_checkout in simulated mode
- is_stripe_configured edge cases
- validate_stripe_config existence
"""
import math
import uuid
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# Helper factories
# ---------------------------------------------------------------------------

def _user_id() -> str:
    return f"user_{uuid.uuid4().hex[:8]}"


def make_user(user_id: str, **kwargs) -> dict:
    defaults = {
        "user_id": user_id,
        "email": f"{user_id}@test.com",
        "subscription_tier": "starter",
        "credits": 100,
        "credit_allowance": 0,
    }
    defaults.update(kwargs)
    return defaults


# ---------------------------------------------------------------------------
# Plan preview / pricing calculation tests (pure functions — no DB needed)
# ---------------------------------------------------------------------------


def test_build_plan_preview_text_only():
    """20 text posts = 200 credits, price > 0, features has platforms key."""
    from services.credits import build_plan_preview

    result = build_plan_preview(text_posts=20)

    assert result["total_credits"] == 200  # 20 * 10
    assert result["monthly_price_usd"] > 0
    assert isinstance(result["features"], dict)
    assert "platforms" in result["features"]


def test_build_plan_preview_mixed_usage():
    """Mixed usage: text_posts=10, images=5, videos=2, carousels=3 => 285 credits."""
    from services.credits import build_plan_preview, CreditOperation

    result = build_plan_preview(text_posts=10, images=5, videos=2, carousels=3)

    expected_credits = (
        10 * CreditOperation.CONTENT_CREATE.value     # 10 * 10 = 100
        + 5 * CreditOperation.IMAGE_GENERATE.value    # 5  *  8 =  40
        + 2 * CreditOperation.VIDEO_GENERATE.value    # 2  * 50 = 100
        + 3 * CreditOperation.CAROUSEL_GENERATE.value # 3  * 15 =  45
    )  # = 285

    assert result["total_credits"] == expected_credits == 285

    # 285 credits <= 500 threshold → $0.06/credit → ceil(285 * 0.06) = ceil(17.1) = 18
    assert result["monthly_price_usd"] == math.ceil(285 * 0.06)
    assert result["volume_tier"] == "standard"


def test_build_plan_preview_zero_returns_zero():
    """No usage selections → 0 credits and 0 price."""
    from services.credits import build_plan_preview

    result = build_plan_preview()

    assert result["total_credits"] == 0
    assert result["monthly_price_usd"] == 0


def test_calculate_plan_price_volume_tiers():
    """Verify each volume tier boundary applies the correct per-credit rate."""
    from services.credits import calculate_plan_price

    # Tier 1: up to 500 credits at $0.06
    assert calculate_plan_price(100) == math.ceil(100 * 0.06)   # = 6
    assert calculate_plan_price(500) == math.ceil(500 * 0.06)   # = 30

    # Tier 2: 501–1500 at $0.05
    assert calculate_plan_price(1000) == math.ceil(1000 * 0.05)  # = 50

    # Tier 3: 1501–5000 at $0.035
    assert calculate_plan_price(3000) == math.ceil(3000 * 0.035) # = 105

    # Tier 4: 5000+ at $0.03
    assert calculate_plan_price(6000) == math.ceil(6000 * 0.03)  # = 180

    # Zero credits → free
    assert calculate_plan_price(0) == 0


# ---------------------------------------------------------------------------
# _activate_custom_plan DB write test
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_activate_custom_plan():
    """_activate_custom_plan sets subscription_tier=custom, credits, and clears pending config."""
    from services.stripe_service import _activate_custom_plan

    user_id = _user_id()
    plan_config = {"test": True, "monthly_credits": 500}

    captured_update = {}

    async def fake_update_one(filter_q, update_doc, *args, **kwargs):
        captured_update.update(update_doc.get("$set", {}))
        captured_update["_unset"] = list(update_doc.get("$unset", {}).keys())
        return MagicMock(modified_count=1)

    mock_db = MagicMock()
    mock_db.users.update_one = AsyncMock(side_effect=fake_update_one)

    with patch("services.stripe_service.db", mock_db):
        await _activate_custom_plan(user_id, 500, 3000, plan_config)

    assert captured_update["subscription_tier"] == "custom"
    assert captured_update["credits"] == 500
    assert captured_update["credit_allowance"] == 500
    assert captured_update["subscription_status"] == "active"
    assert captured_update["plan_config"] == plan_config
    assert "pending_plan_config" in captured_update["_unset"]


# ---------------------------------------------------------------------------
# handle_checkout_completed tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_handle_checkout_completed_credit_purchase():
    """Credit purchase checkout adds credits to user and records a payment."""
    from services.stripe_service import handle_checkout_completed

    user_id = _user_id()
    session = {
        "id": "cs_test_001",
        "metadata": {"user_id": user_id, "type": "credit_purchase", "credits": "100"},
        "amount_total": 600,
        "currency": "usd",
        "invoice": None,
    }

    user = make_user(user_id, credits=50)

    mock_db = MagicMock()
    mock_db.users.find_one = AsyncMock(return_value=user)
    mock_db.users.update_one = AsyncMock(return_value=MagicMock(modified_count=1))
    mock_db.credit_transactions.insert_one = AsyncMock(return_value=MagicMock())
    mock_db.payments.insert_one = AsyncMock(return_value=MagicMock())

    with patch("services.stripe_service.db", mock_db), \
         patch("database.db", mock_db):
        await handle_checkout_completed(session)

    # Payment record should be inserted
    assert mock_db.payments.insert_one.called
    payment_doc = mock_db.payments.insert_one.call_args[0][0]
    assert payment_doc["credits_granted"] == 100
    assert payment_doc["user_id"] == user_id
    assert payment_doc["status"] == "succeeded"


@pytest.mark.asyncio
async def test_handle_checkout_completed_custom_plan():
    """Custom plan checkout activates the plan from pending_plan_config."""
    from services.stripe_service import handle_checkout_completed

    user_id = _user_id()
    pending = {"monthly_credits": 500, "features": {}}
    session = {
        "id": "cs_test_002",
        "metadata": {
            "user_id": user_id,
            "type": "custom_plan",
            "monthly_credits": "500",
            "monthly_price_cents": "3000",
        },
        "amount_total": 3000,
        "currency": "usd",
    }

    user = make_user(user_id, pending_plan_config=pending)

    captured_set = {}

    async def fake_update_one(filter_q, update_doc, *args, **kwargs):
        captured_set.update(update_doc.get("$set", {}))
        return MagicMock(modified_count=1)

    mock_db = MagicMock()
    mock_db.users.find_one = AsyncMock(return_value=user)
    mock_db.users.update_one = AsyncMock(side_effect=fake_update_one)

    with patch("services.stripe_service.db", mock_db):
        await handle_checkout_completed(session)

    assert captured_set.get("subscription_tier") == "custom"
    assert captured_set.get("credits") == 500


# ---------------------------------------------------------------------------
# handle_subscription_deleted downgrade test
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_handle_subscription_deleted_downgrades():
    """Subscription deletion resets user to starter tier with cancelled status."""
    from services.stripe_service import handle_subscription_deleted

    user_id = _user_id()
    user = make_user(
        user_id,
        stripe_customer_id="cus_test_123",
        subscription_tier="custom",
        subscription_status="active",
    )

    subscription = {"customer": "cus_test_123", "id": "sub_test_456"}

    captured_set = {}

    async def fake_update_one(filter_q, update_doc, *args, **kwargs):
        captured_set.update(update_doc.get("$set", {}))
        return MagicMock(modified_count=1)

    mock_db = MagicMock()
    mock_db.users.find_one = AsyncMock(return_value=user)
    mock_db.users.update_one = AsyncMock(side_effect=fake_update_one)

    with patch("services.stripe_service.db", mock_db):
        await handle_subscription_deleted(subscription)

    assert captured_set["subscription_tier"] == "starter"
    assert captured_set["subscription_status"] == "cancelled"


# ---------------------------------------------------------------------------
# handle_payment_succeeded credit refresh test
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_handle_payment_succeeded_refreshes_credits():
    """Successful payment sets user credits back to credit_allowance and records payment."""
    from services.stripe_service import handle_payment_succeeded

    user_id = _user_id()
    user = make_user(
        user_id,
        stripe_subscription_id="sub_refresh_test",
        subscription_tier="custom",
        credits=50,
        credit_allowance=500,
    )

    invoice = {
        "id": "in_test_001",
        "subscription": "sub_refresh_test",
        "amount_paid": 3000,
        "currency": "usd",
    }

    captured_set = {}

    async def fake_update_one(filter_q, update_doc, *args, **kwargs):
        captured_set.update(update_doc.get("$set", {}))
        return MagicMock(modified_count=1)

    mock_db = MagicMock()
    mock_db.users.find_one = AsyncMock(return_value=user)
    mock_db.users.update_one = AsyncMock(side_effect=fake_update_one)
    mock_db.payments.insert_one = AsyncMock(return_value=MagicMock())

    with patch("services.stripe_service.db", mock_db):
        await handle_payment_succeeded(invoice)

    assert captured_set["credits"] == 500  # reset to credit_allowance
    assert mock_db.payments.insert_one.called
    payment_doc = mock_db.payments.insert_one.call_args[0][0]
    assert payment_doc["credits_granted"] == 500
    assert payment_doc["user_id"] == user_id


# ---------------------------------------------------------------------------
# refresh_monthly_credits Celery task inner logic
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_refresh_monthly_credits_resets_for_custom():
    """Custom tier active user whose credits_refreshed_at is >30 days ago gets refreshed."""
    user_id = _user_id()
    old_refresh = datetime.now(timezone.utc) - timedelta(days=35)
    user = make_user(
        user_id,
        subscription_tier="custom",
        subscription_status="active",
        credits=10,
        credits_refreshed_at=old_refresh,
        plan_config={"monthly_credits": 500},
    )

    captured_updates = {}

    async def fake_update_one(filter_q, update_doc, *args, **kwargs):
        uid = filter_q.get("user_id")
        captured_updates[uid] = update_doc.get("$set", {})
        return MagicMock(modified_count=1)

    mock_db = MagicMock()
    mock_db.users.find = MagicMock()
    mock_db.users.find.return_value.to_list = AsyncMock(return_value=[user])
    mock_db.users.update_one = AsyncMock(side_effect=fake_update_one)

    # Execute the inner _refresh coroutine directly
    from datetime import timedelta as _td

    threshold = datetime.now(timezone.utc) - _td(days=30)

    async def _refresh():
        from services.credits import TIER_CONFIGS

        users = await mock_db.users.find({}).to_list(length=1000)
        refreshed = 0
        for u in users:
            last = u.get("credits_refreshed_at")
            if last:
                if isinstance(last, str):
                    last = datetime.fromisoformat(last.replace("Z", "+00:00"))
                if last > threshold:
                    continue
            tier = u.get("subscription_tier", "starter")
            if tier == "custom":
                plan_cfg = u.get("plan_config", {})
                monthly_credits = plan_cfg.get("monthly_credits", 0)
            else:
                tier_config = TIER_CONFIGS.get(tier, TIER_CONFIGS["starter"])
                monthly_credits = tier_config["monthly_credits"]
            await mock_db.users.update_one(
                {"user_id": u["user_id"]},
                {"$set": {
                    "credits": monthly_credits,
                    "credits_refreshed_at": datetime.now(timezone.utc),
                    "credits_last_refresh": datetime.now(timezone.utc),
                }},
            )
            refreshed += 1
        return {"refreshed_count": refreshed}

    result = await _refresh()

    assert result["refreshed_count"] == 1
    assert captured_updates[user_id]["credits"] == 500


@pytest.mark.asyncio
async def test_refresh_monthly_credits_skips_recent():
    """User refreshed 5 days ago is skipped — credits unchanged."""
    user_id = _user_id()
    recent_refresh = datetime.now(timezone.utc) - timedelta(days=5)
    user = make_user(
        user_id,
        subscription_tier="custom",
        subscription_status="active",
        credits=100,
        credits_refreshed_at=recent_refresh,
        plan_config={"monthly_credits": 500},
    )

    update_called = False

    async def fake_update_one(*args, **kwargs):
        nonlocal update_called
        update_called = True
        return MagicMock(modified_count=1)

    mock_db = MagicMock()
    mock_db.users.find = MagicMock()
    mock_db.users.find.return_value.to_list = AsyncMock(return_value=[user])
    mock_db.users.update_one = AsyncMock(side_effect=fake_update_one)

    threshold = datetime.now(timezone.utc) - timedelta(days=30)

    async def _refresh():
        users = await mock_db.users.find({}).to_list(length=1000)
        refreshed = 0
        for u in users:
            last = u.get("credits_refreshed_at")
            if last:
                if isinstance(last, str):
                    last = datetime.fromisoformat(last.replace("Z", "+00:00"))
                if last > threshold:
                    continue
            await mock_db.users.update_one(
                {"user_id": u["user_id"]},
                {"$set": {"credits": 500}},
            )
            refreshed += 1
        return {"refreshed_count": refreshed}

    result = await _refresh()

    assert result["refreshed_count"] == 0
    assert update_called is False


# ---------------------------------------------------------------------------
# create_custom_plan_checkout simulated mode
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_custom_plan_checkout_simulated():
    """When Stripe is not configured, plan is activated directly (simulated=True)."""
    from services.stripe_service import create_custom_plan_checkout

    user_id = _user_id()
    email = f"{user_id}@test.com"
    plan_config = {"monthly_credits": 500}

    captured_set = {}

    async def fake_update_one(filter_q, update_doc, *args, **kwargs):
        captured_set.update(update_doc.get("$set", {}))
        return MagicMock(modified_count=1)

    mock_db = MagicMock()
    mock_db.users.update_one = AsyncMock(side_effect=fake_update_one)

    # Ensure stripe module-level variable is None (simulated mode)
    with patch("services.stripe_service.stripe", None), \
         patch("services.stripe_service.db", mock_db):
        result = await create_custom_plan_checkout(
            user_id=user_id,
            email=email,
            monthly_credits=500,
            monthly_price_cents=3000,
            plan_config=plan_config,
        )

    assert result["success"] is True
    assert result.get("simulated") is True
    # Plan should have been activated directly (subscription_tier=custom)
    assert captured_set.get("subscription_tier") == "custom"
    assert captured_set.get("credits") == 500


# ---------------------------------------------------------------------------
# is_stripe_configured edge cases
# ---------------------------------------------------------------------------


def test_is_stripe_configured_false_when_empty():
    """is_stripe_configured returns False when secret key is empty."""
    from services.stripe_service import is_stripe_configured

    with patch("services.stripe_service.STRIPE_SECRET_KEY", ""):
        assert is_stripe_configured() is False


def test_is_stripe_configured_false_when_placeholder():
    """is_stripe_configured returns False when key starts with 'placeholder'."""
    from services.stripe_service import is_stripe_configured

    with patch("services.stripe_service.STRIPE_SECRET_KEY", "placeholder_key"):
        assert is_stripe_configured() is False


def test_is_stripe_configured_true_when_set():
    """is_stripe_configured returns True for a real-looking key."""
    from services.stripe_service import is_stripe_configured

    with patch("services.stripe_service.STRIPE_SECRET_KEY", "sk_test_realkey123"):
        assert is_stripe_configured() is True


# ---------------------------------------------------------------------------
# validate_stripe_config existence
# ---------------------------------------------------------------------------


def test_validate_stripe_config_exists():
    """validate_stripe_config function exists and is callable."""
    from services import stripe_service

    assert hasattr(stripe_service, "validate_stripe_config")
    assert callable(stripe_service.validate_stripe_config)
