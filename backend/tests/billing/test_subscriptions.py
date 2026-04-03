"""Subscription lifecycle state machine tests (BILL-02).

Covers the full state machine from subscription creation through
cancel/reactivate via Stripe webhook handlers:
- handle_checkout_completed (credit purchase and custom plan paths)
- handle_subscription_created
- handle_subscription_updated (upgrade, downgrade, past_due)
- handle_subscription_deleted
- handle_payment_succeeded
- handle_payment_failed
- cancel_stripe_subscription (at period end and immediately)
- modify_subscription (upgrade/downgrade credits)
- Route-level: POST /api/billing/subscription/cancel, POST /api/billing/plan/modify,
  GET /api/billing/subscription, POST /api/billing/webhook/stripe

All tests use mongomock-motor for DB and mock Stripe objects.
"""

import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _uid() -> str:
    return f"user_{uuid.uuid4().hex[:8]}"


def _make_subscription(
    sub_id: str,
    status: str = "active",
    user_id: str = None,
    monthly_credits: int = 500,
) -> dict:
    """Build a minimal fake Stripe subscription dict."""
    return {
        "id": sub_id,
        "status": status,
        "customer": f"cus_{sub_id[-6:]}",
        "current_period_end": 1775187374,
        "cancel_at_period_end": False,
        "metadata": {
            "user_id": user_id or _uid(),
            "type": "custom_plan",
            "monthly_credits": str(monthly_credits),
        },
        "items": {
            "data": [
                {
                    "id": f"si_{sub_id}",
                    "price": {
                        "id": f"price_{sub_id}",
                        "product": f"prod_{sub_id}",
                        "unit_amount": 3000,
                    },
                }
            ]
        },
    }


def _make_invoice(
    invoice_id: str,
    subscription_id: str,
    amount_paid: int = 3000,
) -> dict:
    return {
        "id": invoice_id,
        "subscription": subscription_id,
        "amount_paid": amount_paid,
        "currency": "usd",
    }


# ---------------------------------------------------------------------------
# handle_checkout_completed
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestHandleCheckoutCompleted:

    async def test_credit_purchase_adds_credits(self, mongomock_db):
        """Credit purchase checkout → credits added to user."""
        user_id = _uid()
        await mongomock_db.users.insert_one({
            "user_id": user_id,
            "email": "a@test.com",
            "credits": 50,
            "subscription_tier": "starter",
        })

        session = {
            "id": "cs_credit_001",
            "metadata": {"user_id": user_id, "type": "credit_purchase", "credits": "100"},
            "amount_total": 600,
            "currency": "usd",
            "invoice": None,
        }

        with patch("services.stripe_service.db", mongomock_db), \
             patch("database.db", mongomock_db):
            from services.stripe_service import handle_checkout_completed
            await handle_checkout_completed(session)

        user = await mongomock_db.users.find_one({"user_id": user_id})
        assert user["credits"] == 150

    async def test_credit_purchase_records_payment(self, mongomock_db):
        """Credit purchase checkout → payment record written to db.payments."""
        user_id = _uid()
        await mongomock_db.users.insert_one({
            "user_id": user_id,
            "email": "b@test.com",
            "credits": 0,
        })

        session = {
            "id": "cs_payment_001",
            "metadata": {"user_id": user_id, "type": "credit_purchase", "credits": "500"},
            "amount_total": 2500,
            "currency": "usd",
            "invoice": None,
        }

        with patch("services.stripe_service.db", mongomock_db), \
             patch("database.db", mongomock_db):
            from services.stripe_service import handle_checkout_completed
            await handle_checkout_completed(session)

        payment = await mongomock_db.payments.find_one({"user_id": user_id})
        assert payment is not None
        assert payment["credits_granted"] == 500
        assert payment["status"] == "succeeded"

    async def test_custom_plan_activates_from_pending_config(self, mongomock_db):
        """Custom plan checkout → activates subscription from pending_plan_config."""
        user_id = _uid()
        pending_config = {"monthly_credits": 300, "features": {}}
        await mongomock_db.users.insert_one({
            "user_id": user_id,
            "email": "c@test.com",
            "credits": 0,
            "pending_plan_config": pending_config,
        })

        session = {
            "id": "cs_plan_001",
            "metadata": {
                "user_id": user_id,
                "type": "custom_plan",
                "monthly_credits": "300",
                "monthly_price_cents": "1800",
            },
            "amount_total": 1800,
            "currency": "usd",
            "invoice": None,
        }

        with patch("services.stripe_service.db", mongomock_db), \
             patch("database.db", mongomock_db):
            from services.stripe_service import handle_checkout_completed
            await handle_checkout_completed(session)

        user = await mongomock_db.users.find_one({"user_id": user_id})
        assert user["subscription_tier"] == "custom"
        assert user["credits"] == 300
        # pending_plan_config should be cleared
        assert user.get("pending_plan_config") is None

    async def test_missing_user_id_does_not_crash(self, mongomock_db):
        """Checkout without user_id in metadata logs error but does not raise."""
        session = {
            "id": "cs_no_user_001",
            "metadata": {},  # No user_id
            "amount_total": 600,
        }

        with patch("services.stripe_service.db", mongomock_db), \
             patch("database.db", mongomock_db):
            from services.stripe_service import handle_checkout_completed
            # Should not raise
            await handle_checkout_completed(session)

    async def test_missing_type_handled_gracefully(self, mongomock_db):
        """Checkout without type in metadata is logged but does not crash."""
        user_id = _uid()
        await mongomock_db.users.insert_one({"user_id": user_id, "credits": 0})

        session = {
            "id": "cs_no_type_001",
            "metadata": {"user_id": user_id},  # No type
            "amount_total": 0,
        }

        with patch("services.stripe_service.db", mongomock_db), \
             patch("database.db", mongomock_db):
            from services.stripe_service import handle_checkout_completed
            # Should not raise
            await handle_checkout_completed(session)


# ---------------------------------------------------------------------------
# handle_subscription_created
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestHandleSubscriptionCreated:

    async def test_creates_subscription_record_in_db(self, mongomock_db):
        """New subscription → writes stripe_subscription_id and status to user record."""
        user_id = _uid()
        await mongomock_db.users.insert_one({
            "user_id": user_id,
            "email": "a@test.com",
            "subscription_tier": "starter",
            "credits": 0,
        })

        sub = _make_subscription("sub_new_001", user_id=user_id, monthly_credits=500)

        with patch("services.stripe_service.db", mongomock_db), \
             patch("database.db", mongomock_db):
            from services.stripe_service import handle_subscription_created
            await handle_subscription_created(sub)

        user = await mongomock_db.users.find_one({"user_id": user_id})
        assert user.get("stripe_subscription_id") == "sub_new_001"
        assert user.get("subscription_status") == "active"

    async def test_custom_plan_type_sets_tier_and_credits(self, mongomock_db):
        """Custom plan subscription → subscription_tier=custom, credits updated."""
        user_id = _uid()
        await mongomock_db.users.insert_one({
            "user_id": user_id,
            "credits": 0,
            "subscription_tier": "starter",
        })

        sub = _make_subscription("sub_custom_001", user_id=user_id, monthly_credits=1000)

        with patch("services.stripe_service.db", mongomock_db), \
             patch("database.db", mongomock_db):
            from services.stripe_service import handle_subscription_created
            await handle_subscription_created(sub)

        user = await mongomock_db.users.find_one({"user_id": user_id})
        assert user["subscription_tier"] == "custom"
        assert user["credits"] == 1000
        assert user["credit_allowance"] == 1000

    async def test_looks_up_user_by_customer_id_when_no_metadata(self, mongomock_db):
        """When user_id is absent from metadata, lookup by stripe_customer_id."""
        user_id = _uid()
        await mongomock_db.users.insert_one({
            "user_id": user_id,
            "stripe_customer_id": "cus_lookup_001",
            "credits": 0,
        })

        sub = _make_subscription("sub_lookup_001", monthly_credits=500)
        sub["customer"] = "cus_lookup_001"
        sub["metadata"] = {}  # Remove user_id from metadata

        with patch("services.stripe_service.db", mongomock_db), \
             patch("database.db", mongomock_db):
            from services.stripe_service import handle_subscription_created
            await handle_subscription_created(sub)

        user = await mongomock_db.users.find_one({"user_id": user_id})
        assert user.get("stripe_subscription_id") == "sub_lookup_001"

    async def test_unknown_user_logs_error_no_crash(self, mongomock_db):
        """Subscription for unknown customer/user_id logs error, does not raise."""
        sub = _make_subscription("sub_unknown_001", monthly_credits=500)
        sub["customer"] = "cus_nobody"
        sub["metadata"] = {}

        with patch("services.stripe_service.db", mongomock_db), \
             patch("database.db", mongomock_db):
            from services.stripe_service import handle_subscription_created
            # Should not raise
            await handle_subscription_created(sub)


# ---------------------------------------------------------------------------
# handle_subscription_updated
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestHandleSubscriptionUpdated:

    async def test_status_updated_in_db(self, mongomock_db):
        """Subscription update → subscription_status field updated."""
        user_id = _uid()
        await mongomock_db.users.insert_one({
            "user_id": user_id,
            "stripe_subscription_id": "sub_upd_001",
            "subscription_status": "active",
            "credits": 500,
        })

        sub = _make_subscription("sub_upd_001", status="past_due", user_id=user_id)

        with patch("services.stripe_service.db", mongomock_db), \
             patch("database.db", mongomock_db):
            from services.stripe_service import handle_subscription_updated
            await handle_subscription_updated(sub)

        user = await mongomock_db.users.find_one({"user_id": user_id})
        assert user["subscription_status"] == "past_due"

    async def test_active_status_updates_credit_allowance(self, mongomock_db):
        """Active subscription update → credit_allowance updated from metadata."""
        user_id = _uid()
        await mongomock_db.users.insert_one({
            "user_id": user_id,
            "stripe_subscription_id": "sub_active_upd_001",
            "subscription_status": "active",
            "credit_allowance": 500,
        })

        sub = _make_subscription("sub_active_upd_001", status="active", user_id=user_id, monthly_credits=800)

        with patch("services.stripe_service.db", mongomock_db), \
             patch("database.db", mongomock_db):
            from services.stripe_service import handle_subscription_updated
            await handle_subscription_updated(sub)

        user = await mongomock_db.users.find_one({"user_id": user_id})
        assert user["credit_allowance"] == 800

    async def test_past_due_does_not_change_credit_allowance(self, mongomock_db):
        """past_due status update does not reset credit_allowance."""
        user_id = _uid()
        await mongomock_db.users.insert_one({
            "user_id": user_id,
            "stripe_subscription_id": "sub_past_due_001",
            "subscription_status": "active",
            "credit_allowance": 500,
        })

        sub = _make_subscription("sub_past_due_001", status="past_due", user_id=user_id)

        with patch("services.stripe_service.db", mongomock_db), \
             patch("database.db", mongomock_db):
            from services.stripe_service import handle_subscription_updated
            await handle_subscription_updated(sub)

        user = await mongomock_db.users.find_one({"user_id": user_id})
        # Status should be updated but credit_allowance should stay at 500
        assert user["subscription_status"] == "past_due"
        assert user["credit_allowance"] == 500

    async def test_lookup_by_customer_when_no_user_id(self, mongomock_db):
        """subscription_updated without metadata user_id → lookup by stripe_customer_id."""
        user_id = _uid()
        await mongomock_db.users.insert_one({
            "user_id": user_id,
            "stripe_customer_id": "cus_upd_lookup_001",
            "subscription_status": "active",
        })

        sub = _make_subscription("sub_upd_lookup_001", status="past_due")
        sub["customer"] = "cus_upd_lookup_001"
        sub["metadata"] = {}

        with patch("services.stripe_service.db", mongomock_db), \
             patch("database.db", mongomock_db):
            from services.stripe_service import handle_subscription_updated
            await handle_subscription_updated(sub)

        user = await mongomock_db.users.find_one({"user_id": user_id})
        assert user["subscription_status"] == "past_due"


# ---------------------------------------------------------------------------
# handle_subscription_deleted
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestHandleSubscriptionDeleted:

    async def test_user_reverted_to_starter(self, mongomock_db):
        """Deleted subscription → user reverted to starter tier."""
        user_id = _uid()
        await mongomock_db.users.insert_one({
            "user_id": user_id,
            "stripe_customer_id": "cus_del_001",
            "subscription_tier": "custom",
            "stripe_subscription_id": "sub_del_001",
            "credits": 500,
            "credit_allowance": 500,
        })

        sub = {
            "id": "sub_del_001",
            "customer": "cus_del_001",
        }

        with patch("services.stripe_service.db", mongomock_db), \
             patch("database.db", mongomock_db):
            from services.stripe_service import handle_subscription_deleted
            await handle_subscription_deleted(sub)

        user = await mongomock_db.users.find_one({"user_id": user_id})
        assert user["subscription_tier"] == "starter"
        assert user["subscription_status"] == "cancelled"
        assert user["stripe_subscription_id"] is None

    async def test_credits_not_removed_on_cancellation(self, mongomock_db):
        """Credits are pre-paid so they are NOT cleared on subscription deletion."""
        user_id = _uid()
        await mongomock_db.users.insert_one({
            "user_id": user_id,
            "stripe_customer_id": "cus_credits_del_001",
            "subscription_tier": "custom",
            "credits": 300,  # Pre-paid credits
        })

        sub = {"id": "sub_credits_del_001", "customer": "cus_credits_del_001"}

        with patch("services.stripe_service.db", mongomock_db), \
             patch("database.db", mongomock_db):
            from services.stripe_service import handle_subscription_deleted
            await handle_subscription_deleted(sub)

        user = await mongomock_db.users.find_one({"user_id": user_id})
        # Credits should remain (pre-paid); allowance set to 0
        assert user["credits"] == 300
        assert user["credit_allowance"] == 0

    async def test_unknown_customer_no_crash(self, mongomock_db):
        """Deletion event for unknown customer logs nothing and does not raise."""
        sub = {"id": "sub_unknown_del_001", "customer": "cus_nobody_del"}

        with patch("services.stripe_service.db", mongomock_db), \
             patch("database.db", mongomock_db):
            from services.stripe_service import handle_subscription_deleted
            # Should not raise
            await handle_subscription_deleted(sub)


# ---------------------------------------------------------------------------
# handle_payment_succeeded
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestHandlePaymentSucceeded:

    async def test_monthly_credits_refreshed(self, mongomock_db):
        """Payment succeeded → user credits reset to credit_allowance."""
        user_id = _uid()
        await mongomock_db.users.insert_one({
            "user_id": user_id,
            "stripe_subscription_id": "sub_pay_001",
            "credits": 50,  # Almost depleted
            "credit_allowance": 500,
            "subscription_tier": "custom",
        })

        invoice = _make_invoice("inv_001", "sub_pay_001", amount_paid=3000)

        with patch("services.stripe_service.db", mongomock_db), \
             patch("database.db", mongomock_db):
            from services.stripe_service import handle_payment_succeeded
            await handle_payment_succeeded(invoice)

        user = await mongomock_db.users.find_one({"user_id": user_id})
        assert user["credits"] == 500  # Reset to allowance

    async def test_payment_record_written(self, mongomock_db):
        """Payment succeeded → payment record written to db.payments."""
        user_id = _uid()
        await mongomock_db.users.insert_one({
            "user_id": user_id,
            "stripe_subscription_id": "sub_pay_rec_001",
            "credits": 0,
            "credit_allowance": 300,
            "subscription_tier": "custom",
        })

        invoice = _make_invoice("inv_rec_001", "sub_pay_rec_001", amount_paid=1800)

        with patch("services.stripe_service.db", mongomock_db), \
             patch("database.db", mongomock_db):
            from services.stripe_service import handle_payment_succeeded
            await handle_payment_succeeded(invoice)

        payment = await mongomock_db.payments.find_one({"user_id": user_id})
        assert payment is not None
        assert payment["stripe_invoice_id"] == "inv_rec_001"
        assert payment["status"] == "succeeded"

    async def test_invoice_without_subscription_no_crash(self, mongomock_db):
        """Invoice without subscription_id is safely ignored."""
        invoice = {"id": "inv_no_sub_001", "subscription": None, "amount_paid": 600}

        with patch("services.stripe_service.db", mongomock_db), \
             patch("database.db", mongomock_db):
            from services.stripe_service import handle_payment_succeeded
            # Should not raise
            await handle_payment_succeeded(invoice)

    async def test_no_matching_user_no_crash(self, mongomock_db):
        """Invoice for unknown subscription is safely ignored."""
        invoice = _make_invoice("inv_no_user_001", "sub_nobody_001")

        with patch("services.stripe_service.db", mongomock_db), \
             patch("database.db", mongomock_db):
            from services.stripe_service import handle_payment_succeeded
            await handle_payment_succeeded(invoice)


# ---------------------------------------------------------------------------
# handle_payment_failed
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestHandlePaymentFailed:

    async def test_user_marked_past_due(self, mongomock_db):
        """Failed payment → subscription_status set to past_due."""
        user_id = _uid()
        await mongomock_db.users.insert_one({
            "user_id": user_id,
            "stripe_subscription_id": "sub_fail_001",
            "subscription_status": "active",
        })

        invoice = {"id": "inv_fail_001", "subscription": "sub_fail_001"}

        with patch("services.stripe_service.db", mongomock_db), \
             patch("database.db", mongomock_db):
            from services.stripe_service import handle_payment_failed
            await handle_payment_failed(invoice)

        user = await mongomock_db.users.find_one({"user_id": user_id})
        assert user["subscription_status"] == "past_due"
        assert user.get("payment_failed_at") is not None

    async def test_invoice_without_subscription_no_crash(self, mongomock_db):
        """Invoice without subscription_id is safely ignored."""
        invoice = {"id": "inv_fail_no_sub_001", "subscription": None}

        with patch("services.stripe_service.db", mongomock_db), \
             patch("database.db", mongomock_db):
            from services.stripe_service import handle_payment_failed
            await handle_payment_failed(invoice)


# ---------------------------------------------------------------------------
# cancel_stripe_subscription
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestCancelStripeSubscription:

    async def test_cancel_at_period_end_simulated(self, mongomock_db):
        """Cancel at period end (simulated mode) → success=True."""
        user_id = _uid()
        await mongomock_db.users.insert_one({
            "user_id": user_id,
            "stripe_subscription_id": "sub_cancel_sim_001",
        })

        with patch("services.stripe_service.db", mongomock_db), \
             patch("database.db", mongomock_db), \
             patch("services.stripe_service.stripe", None):
            from services.stripe_service import cancel_stripe_subscription
            result = await cancel_stripe_subscription(user_id, at_period_end=True)

        assert result["success"] is True
        assert result.get("simulated") is True

    async def test_cancel_sets_db_flag_simulated(self, mongomock_db):
        """Cancel (simulated) → subscription_cancelled flag written to user record."""
        user_id = _uid()
        await mongomock_db.users.insert_one({
            "user_id": user_id,
            "stripe_subscription_id": "sub_cancel_flag_001",
        })

        with patch("services.stripe_service.db", mongomock_db), \
             patch("database.db", mongomock_db), \
             patch("services.stripe_service.stripe", None):
            from services.stripe_service import cancel_stripe_subscription
            await cancel_stripe_subscription(user_id, at_period_end=True)

        user = await mongomock_db.users.find_one({"user_id": user_id})
        assert user.get("subscription_cancelled") is True

    async def test_cancel_at_period_end_stripe(self, mongomock_db):
        """Cancel at period end (real Stripe) → calls modify with cancel_at_period_end=True."""
        user_id = _uid()
        await mongomock_db.users.insert_one({
            "user_id": user_id,
            "stripe_subscription_id": "sub_cancel_001",
        })

        mock_stripe = MagicMock()
        mock_sub = MagicMock()
        mock_sub.status = "active"
        mock_sub.current_period_end = 1775187374
        mock_stripe.Subscription.modify.return_value = mock_sub

        with patch("services.stripe_service.db", mongomock_db), \
             patch("database.db", mongomock_db), \
             patch("services.stripe_service.stripe", mock_stripe):
            from services.stripe_service import cancel_stripe_subscription
            result = await cancel_stripe_subscription(user_id, at_period_end=True)

        assert result["success"] is True
        mock_stripe.Subscription.modify.assert_called_once()

    async def test_cancel_immediately_stripe(self, mongomock_db):
        """Cancel immediately (real Stripe) → calls delete."""
        user_id = _uid()
        await mongomock_db.users.insert_one({
            "user_id": user_id,
            "stripe_subscription_id": "sub_delete_001",
        })

        mock_stripe = MagicMock()
        mock_sub = MagicMock()
        mock_sub.status = "cancelled"
        mock_stripe.Subscription.delete.return_value = mock_sub

        with patch("services.stripe_service.db", mongomock_db), \
             patch("database.db", mongomock_db), \
             patch("services.stripe_service.stripe", mock_stripe):
            from services.stripe_service import cancel_stripe_subscription
            result = await cancel_stripe_subscription(user_id, at_period_end=False)

        assert result["success"] is True
        mock_stripe.Subscription.delete.assert_called_once_with("sub_delete_001")

    async def test_no_subscription_returns_error(self, mongomock_db):
        """User with no subscription → returns error."""
        user_id = _uid()
        await mongomock_db.users.insert_one({
            "user_id": user_id,
            # No stripe_subscription_id
        })

        with patch("services.stripe_service.db", mongomock_db), \
             patch("database.db", mongomock_db), \
             patch("services.stripe_service.stripe", None):
            from services.stripe_service import cancel_stripe_subscription
            result = await cancel_stripe_subscription(user_id)

        assert result["success"] is False
        assert "subscription" in result.get("error", "").lower()

    async def test_stripe_api_error_returns_error(self, mongomock_db):
        """Stripe API exception during cancel → returns error."""
        user_id = _uid()
        await mongomock_db.users.insert_one({
            "user_id": user_id,
            "stripe_subscription_id": "sub_cancel_err_001",
        })

        mock_stripe = MagicMock()
        mock_stripe.Subscription.modify.side_effect = Exception("Stripe API down")

        with patch("services.stripe_service.db", mongomock_db), \
             patch("database.db", mongomock_db), \
             patch("services.stripe_service.stripe", mock_stripe):
            from services.stripe_service import cancel_stripe_subscription
            result = await cancel_stripe_subscription(user_id, at_period_end=True)

        assert result["success"] is False


# ---------------------------------------------------------------------------
# modify_subscription
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestModifySubscription:

    async def test_upgrade_credits_simulated(self, mongomock_db):
        """Upgrade credits (simulated) → plan activated with new credits."""
        user_id = _uid()
        await mongomock_db.users.insert_one({
            "user_id": user_id,
            "stripe_subscription_id": "sub_mod_sim_001",
            "credits": 300,
            "credit_allowance": 300,
        })

        plan_config = {"monthly_credits": 800, "monthly_price_usd": 28}

        with patch("services.stripe_service.db", mongomock_db), \
             patch("database.db", mongomock_db), \
             patch("services.stripe_service.stripe", None):
            from services.stripe_service import modify_subscription
            result = await modify_subscription(
                user_id=user_id,
                monthly_credits=800,
                monthly_price_cents=2800,
                plan_config=plan_config,
            )

        assert result["success"] is True
        assert result.get("simulated") is True
        assert result["monthly_credits"] == 800

        user = await mongomock_db.users.find_one({"user_id": user_id})
        assert user["credits"] == 800

    async def test_downgrade_credits_simulated(self, mongomock_db):
        """Downgrade credits (simulated) → plan activated with lower credits."""
        user_id = _uid()
        await mongomock_db.users.insert_one({
            "user_id": user_id,
            "stripe_subscription_id": "sub_mod_down_001",
            "credits": 1000,
            "credit_allowance": 1000,
        })

        plan_config = {"monthly_credits": 200, "monthly_price_usd": 12}

        with patch("services.stripe_service.db", mongomock_db), \
             patch("database.db", mongomock_db), \
             patch("services.stripe_service.stripe", None):
            from services.stripe_service import modify_subscription
            result = await modify_subscription(
                user_id=user_id,
                monthly_credits=200,
                monthly_price_cents=1200,
                plan_config=plan_config,
            )

        assert result["success"] is True
        user = await mongomock_db.users.find_one({"user_id": user_id})
        assert user["credits"] == 200

    async def test_no_subscription_returns_error(self, mongomock_db):
        """Modify for user without subscription → returns error."""
        user_id = _uid()
        await mongomock_db.users.insert_one({
            "user_id": user_id,
            # No stripe_subscription_id
        })

        with patch("services.stripe_service.db", mongomock_db), \
             patch("database.db", mongomock_db), \
             patch("services.stripe_service.stripe", None):
            from services.stripe_service import modify_subscription
            result = await modify_subscription(
                user_id=user_id,
                monthly_credits=500,
                monthly_price_cents=3000,
                plan_config={"monthly_credits": 500},
            )

        assert result["success"] is False
        assert "subscription" in result.get("error", "").lower()

    async def test_unknown_user_returns_error(self, mongomock_db):
        """Modify for nonexistent user → returns error."""
        with patch("services.stripe_service.db", mongomock_db), \
             patch("database.db", mongomock_db), \
             patch("services.stripe_service.stripe", None):
            from services.stripe_service import modify_subscription
            result = await modify_subscription(
                user_id="nobody",
                monthly_credits=500,
                monthly_price_cents=3000,
                plan_config={},
            )

        assert result["success"] is False


# ---------------------------------------------------------------------------
# Route-level tests
# ---------------------------------------------------------------------------


@pytest.fixture
def billing_app_sub(mongomock_db):
    """Minimal FastAPI app with billing router, auth overridden."""
    from fastapi import FastAPI
    from routes.billing import router as billing_router
    from auth_utils import get_current_user

    test_user = {
        "user_id": "route_sub_user",
        "email": "route_sub@test.com",
        "subscription_tier": "custom",
        "credits": 500,
        "stripe_subscription_id": "sub_route_001",
    }

    app = FastAPI()
    app.include_router(billing_router, prefix="/api")
    app.dependency_overrides[get_current_user] = lambda: test_user
    return app, test_user, mongomock_db


@pytest.mark.asyncio
class TestSubscriptionRoutes:

    async def test_get_subscription_returns_200(self, billing_app_sub):
        """GET /api/billing/subscription returns 200 with subscription details."""
        import httpx
        from httpx import ASGITransport
        app, user, db = billing_app_sub

        await db.users.insert_one(user)

        with patch("services.stripe_service.db", db), \
             patch("database.db", db), \
             patch("services.stripe_service.stripe", None):
            async with httpx.AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get("/api/billing/subscription")

        assert response.status_code == 200

    async def test_cancel_subscription_returns_200(self, billing_app_sub):
        """POST /api/billing/subscription/cancel returns 200."""
        import httpx
        from httpx import ASGITransport
        app, user, db = billing_app_sub

        await db.users.insert_one(user)

        with patch("services.stripe_service.db", db), \
             patch("database.db", db), \
             patch("services.stripe_service.stripe", None):
            async with httpx.AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post("/api/billing/subscription/cancel")

        assert response.status_code == 200

    async def test_modify_plan_valid_request_returns_200(self, billing_app_sub):
        """POST /api/billing/plan/modify with valid request returns 200."""
        import httpx
        from httpx import ASGITransport
        app, user, db = billing_app_sub

        await db.users.insert_one(user)

        with patch("services.stripe_service.db", db), \
             patch("database.db", db), \
             patch("services.stripe_service.stripe", None):
            async with httpx.AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/api/billing/plan/modify",
                    json={"text_posts": 20},
                )

        assert response.status_code == 200

    async def test_webhook_missing_signature_returns_400(self, billing_app_sub):
        """POST /api/billing/webhook/stripe without Stripe-Signature → 400."""
        import httpx
        from httpx import ASGITransport
        app, user, db = billing_app_sub

        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/billing/webhook/stripe",
                content=b'{"type":"test"}',
                headers={"Content-Type": "application/json"},
                # No Stripe-Signature header
            )

        assert response.status_code == 400
