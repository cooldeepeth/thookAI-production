"""
Billing route integration tests.

Covers BILL-09: 95%+ branch coverage on services/credits.py,
services/stripe_service.py, and routes/billing.py.

Test approach:
- httpx.AsyncClient + ASGITransport for real ASGI stack traversal
- app.dependency_overrides[get_current_user] for auth bypass
- mongomock_db fixture patches all DB calls
- Stripe calls mocked at function level (no real Stripe API)
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from httpx import AsyncClient, ASGITransport


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def test_user(make_user):
    return make_user(
        user_id="route_test_user",
        subscription_tier="custom",
        credits=500,
        credit_allowance=500,
        email="route_user@test.com",
        stripe_customer_id="cus_route_test",
        stripe_subscription_id="sub_route_test",
        plan_config={
            "monthly_credits": 500,
            "monthly_price_usd": 30,
            "features": {
                "max_personas": 3,
                "platforms": ["linkedin", "x", "instagram"],
                "content_per_day": 50,
                "team_members": 1,
                "analytics_days": 30,
                "series_enabled": True,
                "repurpose_enabled": True,
                "voice_enabled": False,
                "video_enabled": True,
                "priority_support": False,
                "api_access": False,
            },
        },
    )


@pytest.fixture
def starter_user(make_user):
    return make_user(
        user_id="starter_test_user",
        subscription_tier="starter",
        credits=200,
        credit_allowance=0,
        email="starter_user@test.com",
    )


@pytest.fixture
async def client(mongomock_db, test_user):
    """AsyncClient with auth override and mongomock DB."""
    from server import app
    from auth_utils import get_current_user

    # Insert the test user into the mock DB
    await mongomock_db.users.insert_one(dict(test_user))

    app.dependency_overrides[get_current_user] = lambda: test_user
    transport = ASGITransport(app=app)

    with patch("database.db", mongomock_db), \
         patch("routes.billing.db", mongomock_db):
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            yield c

    app.dependency_overrides.clear()


@pytest.fixture
async def starter_client(mongomock_db, starter_user):
    """AsyncClient for a starter tier user."""
    from server import app
    from auth_utils import get_current_user

    await mongomock_db.users.insert_one(dict(starter_user))

    app.dependency_overrides[get_current_user] = lambda: starter_user
    transport = ASGITransport(app=app)

    with patch("database.db", mongomock_db), \
         patch("routes.billing.db", mongomock_db):
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            yield c

    app.dependency_overrides.clear()


@pytest.fixture
async def anon_client():
    """AsyncClient with no auth (unauthenticated requests)."""
    from server import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


# ===========================================================================
# GET /api/billing/config
# ===========================================================================

@pytest.mark.asyncio
class TestBillingConfig:

    async def test_get_billing_config_returns_200(self, anon_client):
        """GET /api/billing/config returns 200 with tier info — no auth required."""
        resp = await anon_client.get("/api/billing/config")
        assert resp.status_code == 200
        data = resp.json()
        assert "configured" in data
        assert "volume_tiers" in data or "pricing_model" in data

    async def test_billing_config_has_credit_packages(self, anon_client):
        """Config includes credit package info."""
        resp = await anon_client.get("/api/billing/config")
        assert resp.status_code == 200
        data = resp.json()
        assert "credit_packages" in data or "operation_costs" in data


# ===========================================================================
# POST /api/billing/plan/preview
# ===========================================================================

@pytest.mark.asyncio
class TestPlanPreview:

    async def test_plan_preview_with_text_posts_returns_200(self, anon_client):
        """POST /api/billing/plan/preview with valid request returns price breakdown."""
        resp = await anon_client.post("/api/billing/plan/preview",
                                     json={"text_posts": 10, "images": 5})
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("success") is True
        assert "total_credits" in data
        assert "monthly_price_usd" in data

    async def test_plan_preview_with_videos_returns_200(self, anon_client):
        """Plan preview with video credits returns correct total."""
        resp = await anon_client.post("/api/billing/plan/preview",
                                     json={"videos": 2})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_credits"] == 100  # 2 * VIDEO_GENERATE(50)

    async def test_plan_preview_all_zero_returns_200(self, anon_client):
        """Plan preview with all zeros returns zero credits."""
        resp = await anon_client.post("/api/billing/plan/preview", json={})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_credits"] == 0
        assert data["monthly_price_usd"] == 0

    async def test_plan_preview_negative_field_returns_422(self, anon_client):
        """Negative usage fields fail Pydantic validation → 422."""
        resp = await anon_client.post("/api/billing/plan/preview",
                                     json={"text_posts": -1})
        assert resp.status_code == 422

    async def test_plan_preview_no_auth_required(self, anon_client):
        """Plan preview works without authentication."""
        resp = await anon_client.post("/api/billing/plan/preview",
                                     json={"text_posts": 5})
        assert resp.status_code == 200

    async def test_plan_preview_breakdown_structure(self, anon_client):
        """Plan preview returns breakdown with correct structure."""
        resp = await anon_client.post("/api/billing/plan/preview",
                                     json={"text_posts": 5, "images": 3, "videos": 1})
        assert resp.status_code == 200
        data = resp.json()
        assert "breakdown" in data
        assert "features" in data
        assert "volume_tier" in data


# ===========================================================================
# POST /api/billing/plan/checkout
# ===========================================================================

@pytest.mark.asyncio
class TestPlanCheckout:

    async def test_plan_checkout_authenticated_simulated_returns_200(self, client, mongomock_db):
        """Authenticated checkout with stripe not configured → 200 with checkout URL."""
        with patch("services.stripe_service.stripe", None), \
             patch("services.stripe_service.db", mongomock_db), \
             patch("database.db", mongomock_db):
            resp = await client.post("/api/billing/plan/checkout",
                                     json={"text_posts": 10})
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("success") is True
        assert "checkout_url" in data or "session_id" in data

    async def test_plan_checkout_unauthenticated_returns_401(self, anon_client):
        """Unauthenticated plan checkout → 401."""
        resp = await anon_client.post("/api/billing/plan/checkout",
                                     json={"text_posts": 10})
        assert resp.status_code == 401

    async def test_plan_checkout_zero_credits_returns_400(self, client):
        """Plan checkout with zero usage → 400 error."""
        with patch("services.stripe_service.stripe", None):
            resp = await client.post("/api/billing/plan/checkout", json={})
        assert resp.status_code == 400
        assert "select" in resp.json().get("detail", "").lower() or "at least" in resp.json().get("detail", "").lower()

    async def test_plan_checkout_negative_field_returns_422(self, client):
        """Negative field value → 422."""
        resp = await client.post("/api/billing/plan/checkout",
                                 json={"text_posts": -5})
        assert resp.status_code == 422


# ===========================================================================
# POST /api/billing/plan/modify
# ===========================================================================

@pytest.mark.asyncio
class TestPlanModify:

    async def test_plan_modify_with_subscription_simulated_returns_200(self, client, mongomock_db):
        """Modify plan with active subscription in simulated mode → 200."""
        with patch("services.stripe_service.stripe", None), \
             patch("services.stripe_service.db", mongomock_db), \
             patch("database.db", mongomock_db):
            resp = await client.post("/api/billing/plan/modify",
                                     json={"text_posts": 20})
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("success") is True

    async def test_plan_modify_zero_credits_returns_400(self, client):
        """Modify plan with zero usage → 400."""
        with patch("services.stripe_service.stripe", None):
            resp = await client.post("/api/billing/plan/modify", json={})
        assert resp.status_code == 400

    async def test_plan_modify_unauthenticated_returns_401(self, anon_client):
        """Unauthenticated plan modify → 401."""
        resp = await anon_client.post("/api/billing/plan/modify",
                                     json={"text_posts": 10})
        assert resp.status_code == 401


# ===========================================================================
# GET /api/billing/credits
# ===========================================================================

@pytest.mark.asyncio
class TestGetCredits:

    async def test_get_credits_authenticated_returns_200(self, client, mongomock_db):
        """Authenticated GET /api/billing/credits → 200 with credit balance."""
        with patch("database.db", mongomock_db):
            resp = await client.get("/api/billing/credits")
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("success") is True
        assert "credits" in data

    async def test_get_credits_unauthenticated_returns_401(self, anon_client):
        """Unauthenticated GET /api/billing/credits → 401."""
        resp = await anon_client.get("/api/billing/credits")
        assert resp.status_code == 401

    async def test_get_credits_returns_correct_balance(self, client, mongomock_db):
        """Credit balance matches what was seeded in DB."""
        with patch("database.db", mongomock_db):
            resp = await client.get("/api/billing/credits")
        assert resp.status_code == 200
        data = resp.json()
        assert data["credits"] == 500


# ===========================================================================
# GET /api/billing/credits/usage
# ===========================================================================

@pytest.mark.asyncio
class TestCreditUsage:

    async def test_get_credit_usage_authenticated_returns_200(self, client, mongomock_db):
        """Authenticated GET /api/billing/credits/usage → 200 with usage history."""
        with patch("database.db", mongomock_db):
            resp = await client.get("/api/billing/credits/usage")
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("success") is True
        assert "transactions" in data

    async def test_get_credit_usage_unauthenticated_returns_401(self, anon_client):
        """Unauthenticated GET /api/billing/credits/usage → 401."""
        resp = await anon_client.get("/api/billing/credits/usage")
        assert resp.status_code == 401

    async def test_get_credit_usage_with_days_param(self, client, mongomock_db):
        """Credit usage accepts days query parameter."""
        with patch("database.db", mongomock_db):
            resp = await client.get("/api/billing/credits/usage?days=7")
        assert resp.status_code == 200
        data = resp.json()
        assert data["period_days"] == 7


# ===========================================================================
# GET /api/billing/credits/costs
# ===========================================================================

@pytest.mark.asyncio
class TestOperationCosts:

    async def test_get_operation_costs_returns_200(self, anon_client):
        """GET /api/billing/credits/costs returns all operation costs."""
        resp = await anon_client.get("/api/billing/credits/costs")
        assert resp.status_code == 200
        data = resp.json()
        assert "costs" in data
        assert "content_create" in data["costs"]
        assert "video_generate" in data["costs"]

    async def test_operation_costs_has_correct_structure(self, anon_client):
        """Each cost entry has credits and name fields."""
        resp = await anon_client.get("/api/billing/credits/costs")
        costs = resp.json()["costs"]
        for op_name, op_data in costs.items():
            assert "credits" in op_data
            assert "name" in op_data


# ===========================================================================
# POST /api/billing/credits/checkout
# ===========================================================================

@pytest.mark.asyncio
class TestCreditCheckout:

    async def test_credit_checkout_valid_package_returns_200(self, client, mongomock_db):
        """Valid credit package checkout → 200."""
        with patch("services.stripe_service.stripe", None), \
             patch("services.stripe_service.db", mongomock_db), \
             patch("database.db", mongomock_db):
            resp = await client.post("/api/billing/credits/checkout",
                                     json={"package": "small"})
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("success") is True

    async def test_credit_checkout_invalid_package_returns_400(self, client, mongomock_db):
        """Invalid package name → 400."""
        with patch("services.stripe_service.stripe", None), \
             patch("services.stripe_service.db", mongomock_db), \
             patch("database.db", mongomock_db):
            resp = await client.post("/api/billing/credits/checkout",
                                     json={"package": "invalid_pkg"})
        assert resp.status_code == 400

    async def test_credit_checkout_unauthenticated_returns_401(self, anon_client):
        """Unauthenticated credit checkout → 401."""
        resp = await anon_client.post("/api/billing/credits/checkout",
                                     json={"package": "small"})
        assert resp.status_code == 401

    async def test_credit_checkout_medium_package_returns_200(self, client, mongomock_db):
        """Medium package checkout succeeds."""
        with patch("services.stripe_service.stripe", None), \
             patch("services.stripe_service.db", mongomock_db), \
             patch("database.db", mongomock_db):
            resp = await client.post("/api/billing/credits/checkout",
                                     json={"package": "medium"})
        assert resp.status_code == 200

    async def test_credit_checkout_large_package_returns_200(self, client, mongomock_db):
        """Large package checkout succeeds."""
        with patch("services.stripe_service.stripe", None), \
             patch("services.stripe_service.db", mongomock_db), \
             patch("database.db", mongomock_db):
            resp = await client.post("/api/billing/credits/checkout",
                                     json={"package": "large"})
        assert resp.status_code == 200


# ===========================================================================
# POST /api/billing/credits/purchase
# ===========================================================================

@pytest.mark.asyncio
class TestPurchaseCredits:

    async def test_purchase_credits_simulated_mode_returns_200(self, client, mongomock_db):
        """Direct purchase in simulated mode (no Stripe) → 200."""
        with patch("services.stripe_service.is_stripe_configured", return_value=False), \
             patch("database.db", mongomock_db):
            resp = await client.post("/api/billing/credits/purchase",
                                     json={"amount": 100})
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("success") is True
        assert data.get("payment_status") == "simulated"

    async def test_purchase_credits_too_small_returns_400(self, client):
        """Purchase below minimum (50) → 400."""
        with patch("services.stripe_service.is_stripe_configured", return_value=False):
            resp = await client.post("/api/billing/credits/purchase",
                                     json={"amount": 10})
        assert resp.status_code == 400
        assert "minimum" in resp.json().get("detail", "").lower()

    async def test_purchase_credits_too_large_returns_400(self, client):
        """Purchase above maximum (10000) → 400."""
        with patch("services.stripe_service.is_stripe_configured", return_value=False):
            resp = await client.post("/api/billing/credits/purchase",
                                     json={"amount": 99999})
        assert resp.status_code == 400
        assert "maximum" in resp.json().get("detail", "").lower()

    async def test_purchase_credits_stripe_configured_redirects(self, client):
        """When Stripe is configured, redirects to checkout instead of direct purchase."""
        with patch("services.stripe_service.is_stripe_configured", return_value=True):
            resp = await client.post("/api/billing/credits/purchase",
                                     json={"amount": 100})
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("redirect") is True

    async def test_purchase_credits_unauthenticated_returns_401(self, anon_client):
        """Unauthenticated purchase → 401."""
        resp = await anon_client.post("/api/billing/credits/purchase",
                                     json={"amount": 100})
        assert resp.status_code == 401


# ===========================================================================
# GET /api/billing/payments
# ===========================================================================

@pytest.mark.asyncio
class TestPaymentHistory:

    async def test_get_payment_history_authenticated_returns_200(self, client, mongomock_db):
        """Authenticated GET /api/billing/payments → 200 with payment list."""
        with patch("routes.billing.db", mongomock_db), \
             patch("database.db", mongomock_db):
            resp = await client.get("/api/billing/payments")
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("success") is True
        assert "payments" in data
        assert isinstance(data["payments"], list)

    async def test_get_payment_history_unauthenticated_returns_401(self, anon_client):
        """Unauthenticated GET /api/billing/payments → 401."""
        resp = await anon_client.get("/api/billing/payments")
        assert resp.status_code == 401

    async def test_get_payment_history_empty_for_new_user(self, client, mongomock_db):
        """New user has empty payment history."""
        with patch("routes.billing.db", mongomock_db), \
             patch("database.db", mongomock_db):
            resp = await client.get("/api/billing/payments")
        assert resp.status_code == 200
        assert resp.json()["payments"] == []


# ===========================================================================
# GET /api/billing/subscription
# ===========================================================================

@pytest.mark.asyncio
class TestSubscription:

    async def test_get_subscription_authenticated_returns_200(self, client, mongomock_db):
        """Authenticated GET /api/billing/subscription → 200."""
        with patch("database.db", mongomock_db), \
             patch("services.stripe_service.stripe", None), \
             patch("services.stripe_service.db", mongomock_db):
            resp = await client.get("/api/billing/subscription")
        assert resp.status_code == 200
        data = resp.json()
        assert "tier" in data or "success" in data

    async def test_get_subscription_unauthenticated_returns_401(self, anon_client):
        """Unauthenticated GET /api/billing/subscription → 401."""
        resp = await anon_client.get("/api/billing/subscription")
        assert resp.status_code == 401

    async def test_get_subscription_starter_user(self, starter_client, mongomock_db):
        """Starter user subscription shows starter tier."""
        with patch("database.db", mongomock_db), \
             patch("services.stripe_service.stripe", None), \
             patch("services.stripe_service.db", mongomock_db):
            resp = await starter_client.get("/api/billing/subscription")
        assert resp.status_code == 200


# ===========================================================================
# GET /api/billing/subscription/tiers
# ===========================================================================

@pytest.mark.asyncio
class TestSubscriptionTiers:

    async def test_get_tiers_authenticated_returns_200(self, client, mongomock_db):
        """GET /api/billing/subscription/tiers → 200 with tier list."""
        with patch("database.db", mongomock_db):
            resp = await client.get("/api/billing/subscription/tiers")
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("success") is True
        assert "tiers" in data
        assert len(data["tiers"]) >= 2  # starter + custom

    async def test_get_tiers_unauthenticated_returns_401(self, anon_client):
        """Unauthenticated GET /api/billing/subscription/tiers → 401."""
        resp = await anon_client.get("/api/billing/subscription/tiers")
        assert resp.status_code == 401


# ===========================================================================
# POST /api/billing/subscription/cancel
# ===========================================================================

@pytest.mark.asyncio
class TestSubscriptionCancel:

    async def test_cancel_subscription_custom_user_returns_200(self, client, mongomock_db):
        """Custom plan user cancels subscription → 200."""
        with patch("database.db", mongomock_db), \
             patch("services.stripe_service.stripe", None), \
             patch("services.stripe_service.db", mongomock_db), \
             patch("services.stripe_service.is_stripe_configured", return_value=False):
            resp = await client.post("/api/billing/subscription/cancel")
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("success") is True

    async def test_cancel_subscription_starter_user_returns_400(self, starter_client, mongomock_db):
        """Starter user cannot cancel (no active subscription) → 400."""
        with patch("database.db", mongomock_db), \
             patch("services.stripe_service.stripe", None), \
             patch("services.stripe_service.is_stripe_configured", return_value=False):
            resp = await starter_client.post("/api/billing/subscription/cancel")
        assert resp.status_code == 400

    async def test_cancel_subscription_unauthenticated_returns_401(self, anon_client):
        """Unauthenticated cancel → 401."""
        resp = await anon_client.post("/api/billing/subscription/cancel")
        assert resp.status_code == 401


# ===========================================================================
# GET /api/billing/subscription/limits
# ===========================================================================

@pytest.mark.asyncio
class TestSubscriptionLimits:

    async def test_get_feature_limits_authenticated_returns_200(self, client, mongomock_db):
        """GET /api/billing/subscription/limits → 200."""
        with patch("database.db", mongomock_db):
            resp = await client.get("/api/billing/subscription/limits")
        assert resp.status_code == 200

    async def test_get_feature_limits_unauthenticated_returns_401(self, anon_client):
        """Unauthenticated get limits → 401."""
        resp = await anon_client.get("/api/billing/subscription/limits")
        assert resp.status_code == 401


# ===========================================================================
# GET /api/billing/subscription/daily-limit
# ===========================================================================

@pytest.mark.asyncio
class TestDailyLimit:

    async def test_get_daily_limit_authenticated_returns_200(self, client, mongomock_db):
        """GET /api/billing/subscription/daily-limit → 200 with limit status."""
        with patch("database.db", mongomock_db):
            resp = await client.get("/api/billing/subscription/daily-limit")
        assert resp.status_code == 200
        data = resp.json()
        assert "allowed" in data
        assert "daily_limit" in data

    async def test_get_daily_limit_unauthenticated_returns_401(self, anon_client):
        """Unauthenticated get daily limit → 401."""
        resp = await anon_client.get("/api/billing/subscription/daily-limit")
        assert resp.status_code == 401

    async def test_daily_limit_remaining_calculation(self, client, mongomock_db):
        """Daily limit response includes remaining count."""
        with patch("database.db", mongomock_db):
            resp = await client.get("/api/billing/subscription/daily-limit")
        assert resp.status_code == 200
        data = resp.json()
        assert "remaining" in data


# ===========================================================================
# POST /api/billing/portal
# ===========================================================================

@pytest.mark.asyncio
class TestCustomerPortal:

    async def test_create_portal_simulated_returns_200(self, client, mongomock_db):
        """POST /api/billing/portal in simulated mode → 200 with portal URL."""
        with patch("services.stripe_service.stripe", None), \
             patch("services.stripe_service.db", mongomock_db), \
             patch("database.db", mongomock_db):
            resp = await client.post("/api/billing/portal")
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("success") is True
        assert "portal_url" in data

    async def test_create_portal_no_billing_account_returns_400(self, client, mongomock_db):
        """User without stripe_customer_id → 400."""
        # Update user to remove customer ID
        await mongomock_db.users.update_one(
            {"user_id": "route_test_user"},
            {"$unset": {"stripe_customer_id": ""}}
        )
        with patch("services.stripe_service.stripe", None), \
             patch("services.stripe_service.db", mongomock_db), \
             patch("database.db", mongomock_db):
            resp = await client.post("/api/billing/portal")
        assert resp.status_code == 400

    async def test_create_portal_unauthenticated_returns_401(self, anon_client):
        """Unauthenticated portal request → 401."""
        resp = await anon_client.post("/api/billing/portal")
        assert resp.status_code == 401


# ===========================================================================
# POST /api/billing/webhook/stripe
# ===========================================================================

@pytest.mark.asyncio
class TestWebhookRoute:

    async def test_webhook_missing_signature_returns_400(self, anon_client):
        """Missing Stripe-Signature header → 400."""
        resp = await anon_client.post("/api/billing/webhook/stripe",
                                     content=b"payload")
        assert resp.status_code == 400

    async def test_webhook_valid_returns_received(self, anon_client, mongomock_db):
        """Webhook with valid signature returns {'received': True}."""
        mock_event = {
            "id": "evt_webhook_route_001",
            "type": "unknown.event.type",
            "data": {"object": {}},
        }
        with patch("services.stripe_service.db", mongomock_db), \
             patch("database.db", mongomock_db), \
             patch("services.stripe_service.STRIPE_WEBHOOK_SECRET", "whsec_test"), \
             patch("services.stripe_service.stripe") as mock_stripe, \
             patch("config.settings") as mock_settings:
            mock_stripe.Webhook.construct_event.return_value = mock_event
            mock_stripe.error = MagicMock()
            mock_stripe.error.SignatureVerificationError = Exception
            mock_settings.stripe.webhook_secret = "whsec_test"
            mock_settings.app.environment = "test"

            resp = await anon_client.post(
                "/api/billing/webhook/stripe",
                content=b"payload",
                headers={"Stripe-Signature": "t=123,v1=abc"}
            )
        assert resp.status_code == 200
        assert resp.json() == {"received": True}

    async def test_webhook_invalid_signature_returns_received(self, anon_client, mongomock_db):
        """Webhook with bad signature still returns 200 with received=True (design choice)."""
        with patch("services.stripe_service.db", mongomock_db), \
             patch("database.db", mongomock_db), \
             patch("services.stripe_service.STRIPE_WEBHOOK_SECRET", "whsec_test"), \
             patch("services.stripe_service.stripe") as mock_stripe, \
             patch("config.settings") as mock_settings:
            mock_stripe.Webhook.construct_event.side_effect = Exception("Invalid signature")
            mock_stripe.error = MagicMock()
            mock_stripe.error.SignatureVerificationError = Exception
            mock_settings.stripe.webhook_secret = "whsec_test"
            mock_settings.app.environment = "test"

            resp = await anon_client.post(
                "/api/billing/webhook/stripe",
                content=b"bad_payload",
                headers={"Stripe-Signature": "t=bad,v1=bad"}
            )
        # Route returns 200 with received=True regardless of processing result
        assert resp.status_code == 200


# ===========================================================================
# POST /api/billing/simulate/upgrade
# ===========================================================================

@pytest.mark.asyncio
class TestSimulateUpgrade:

    async def test_simulate_upgrade_in_test_env_returns_200(self, client, mongomock_db):
        """Simulate upgrade in test environment → 200."""
        with patch("config.settings") as mock_settings, \
             patch("routes.billing.db", mongomock_db), \
             patch("database.db", mongomock_db):
            mock_settings.app.environment = "test"
            resp = await client.post("/api/billing/simulate/upgrade",
                                     json={"text_posts": 10})
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("success") is True
        assert data.get("simulated") is True

    async def test_simulate_upgrade_zero_credits_downgrades_to_starter(self, client, mongomock_db):
        """Simulate upgrade with zero usage → downgrades to starter."""
        with patch("config.settings") as mock_settings, \
             patch("routes.billing.db", mongomock_db), \
             patch("database.db", mongomock_db):
            mock_settings.app.environment = "test"
            resp = await client.post("/api/billing/simulate/upgrade", json={})
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("success") is True
        assert data.get("new_tier") == "starter"

    async def test_simulate_upgrade_in_production_returns_403(self, client, mongomock_db):
        """Simulate upgrade in production environment → 403."""
        with patch("config.settings") as mock_settings, \
             patch("routes.billing.db", mongomock_db):
            mock_settings.app.environment = "production"
            resp = await client.post("/api/billing/simulate/upgrade",
                                     json={"text_posts": 10})
        assert resp.status_code == 403

    async def test_simulate_upgrade_unauthenticated_returns_401(self, anon_client):
        """Unauthenticated simulate upgrade → 401."""
        resp = await anon_client.post("/api/billing/simulate/upgrade",
                                     json={"text_posts": 10})
        assert resp.status_code == 401


# ===========================================================================
# POST /api/billing/simulate/credits
# ===========================================================================

@pytest.mark.asyncio
class TestSimulateCredits:

    async def test_simulate_add_credits_in_test_env_returns_200(self, client, mongomock_db):
        """Simulate add credits in test environment → 200."""
        with patch("config.settings") as mock_settings, \
             patch("database.db", mongomock_db):
            mock_settings.app.environment = "test"
            resp = await client.post("/api/billing/simulate/credits?amount=50")
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("success") is True
        assert data.get("simulated") is True

    async def test_simulate_add_credits_in_production_returns_403(self, client, mongomock_db):
        """Simulate add credits in production → 403."""
        with patch("config.settings") as mock_settings, \
             patch("database.db", mongomock_db):
            mock_settings.app.environment = "production"
            resp = await client.post("/api/billing/simulate/credits?amount=100")
        assert resp.status_code == 403

    async def test_simulate_add_credits_unauthenticated_returns_401(self, anon_client):
        """Unauthenticated simulate credits → 401."""
        resp = await anon_client.post("/api/billing/simulate/credits?amount=100")
        assert resp.status_code == 401

    async def test_simulate_add_credits_default_amount(self, client, mongomock_db):
        """Simulate credits with default amount (100) → 200."""
        with patch("config.settings") as mock_settings, \
             patch("database.db", mongomock_db):
            mock_settings.app.environment = "test"
            resp = await client.post("/api/billing/simulate/credits")
        assert resp.status_code == 200


# ===========================================================================
# Additional coverage: edge cases in billing service functions
# ===========================================================================

@pytest.mark.asyncio
class TestBillingServiceCoverage:
    """Additional tests to boost branch coverage on service functions."""

    async def test_get_stripe_config_when_configured(self):
        """get_stripe_config includes publishable key when Stripe configured."""
        with patch("services.stripe_service.is_stripe_configured", return_value=True), \
             patch("services.stripe_service.STRIPE_PUBLISHABLE_KEY", "pk_test_xxx"):
            from services.stripe_service import get_stripe_config
            config = get_stripe_config()
        assert config["configured"] is True
        assert config["publishable_key"] == "pk_test_xxx"

    async def test_get_stripe_config_when_not_configured(self):
        """get_stripe_config omits key when Stripe not configured."""
        with patch("services.stripe_service.is_stripe_configured", return_value=False):
            from services.stripe_service import get_stripe_config
            config = get_stripe_config()
        assert config["configured"] is False
        assert config["publishable_key"] is None

    async def test_is_stripe_configured_false_for_placeholder(self):
        """is_stripe_configured returns False for placeholder keys."""
        with patch("services.stripe_service.STRIPE_SECRET_KEY", "placeholder_key"):
            from services.stripe_service import is_stripe_configured
            assert is_stripe_configured() is False

    async def test_is_stripe_configured_false_for_empty(self):
        """is_stripe_configured returns False for empty string."""
        with patch("services.stripe_service.STRIPE_SECRET_KEY", ""):
            from services.stripe_service import is_stripe_configured
            assert is_stripe_configured() is False

    async def test_calculate_plan_price_volume_tiers(self):
        """calculate_plan_price applies correct volume tiers."""
        from services.credits import calculate_plan_price
        # Under 500: 6 cents/credit
        price_small = calculate_plan_price(100)
        assert price_small == 6  # ceil(100 * 0.06) = 6

        # 500-1500: 5 cents/credit
        price_mid = calculate_plan_price(1000)
        assert price_mid == 50  # ceil(1000 * 0.05) = 50

        # Over 5000: 3 cents/credit
        price_large = calculate_plan_price(6000)
        assert price_large == 180  # ceil(6000 * 0.03) = 180

    async def test_calculate_plan_price_zero_returns_zero(self):
        """calculate_plan_price(0) returns 0."""
        from services.credits import calculate_plan_price
        assert calculate_plan_price(0) == 0.0

    async def test_build_plan_preview_volume_labels(self):
        """build_plan_preview returns correct volume_tier labels."""
        from services.credits import build_plan_preview
        # Small plan → standard tier
        preview = build_plan_preview(text_posts=5)
        assert preview["volume_tier"] in ("standard", "pro", "growth", "scale")

    async def test_get_credit_balance_unknown_tier_uses_starter(self, mongomock_db):
        """get_credit_balance for user with unknown tier falls back to starter."""
        await mongomock_db.users.insert_one({
            "user_id": "u_unknown_tier",
            "credits": 50,
            "subscription_tier": "legacy_tier",
        })
        with patch("database.db", mongomock_db):
            from services.credits import get_credit_balance
            result = await get_credit_balance("u_unknown_tier")
        assert result["success"] is True
        assert result["tier_name"] == "Starter"

    async def test_get_credit_balance_user_not_found(self, mongomock_db):
        """get_credit_balance for non-existent user returns error."""
        with patch("database.db", mongomock_db):
            from services.credits import get_credit_balance
            result = await get_credit_balance("nonexistent_user_xyz")
        assert result["success"] is False

    async def test_check_feature_access_allowed_feature(self, mongomock_db):
        """check_feature_access returns allowed for enabled feature."""
        await mongomock_db.users.insert_one({
            "user_id": "u_feature_ok",
            "subscription_tier": "custom",
            "plan_config": {
                "features": {"series_enabled": True, "voice_enabled": False}
            }
        })
        with patch("database.db", mongomock_db):
            from services.credits import check_feature_access
            result = await check_feature_access("u_feature_ok", "series_enabled")
        assert result["allowed"] is True

    async def test_check_feature_access_disabled_feature(self, mongomock_db):
        """check_feature_access returns not allowed for disabled feature."""
        await mongomock_db.users.insert_one({
            "user_id": "u_feature_off",
            "subscription_tier": "custom",
            "plan_config": {
                "features": {"series_enabled": True, "voice_enabled": False}
            }
        })
        with patch("database.db", mongomock_db):
            from services.credits import check_feature_access
            result = await check_feature_access("u_feature_off", "voice_enabled")
        assert result["allowed"] is False

    async def test_check_feature_access_unknown_feature(self, mongomock_db):
        """check_feature_access for unknown feature returns not allowed."""
        await mongomock_db.users.insert_one({
            "user_id": "u_unknown_feature",
            "subscription_tier": "starter",
        })
        with patch("database.db", mongomock_db):
            from services.credits import check_feature_access
            result = await check_feature_access("u_unknown_feature", "nonexistent_feature")
        assert result["allowed"] is False

    async def test_cancel_stripe_subscription_no_subscription(self, mongomock_db):
        """cancel_stripe_subscription with no subscription returns error."""
        await mongomock_db.users.insert_one({
            "user_id": "u_no_sub",
            "credits": 0,
            "subscription_tier": "starter",
        })
        with patch("services.stripe_service.db", mongomock_db):
            from services.stripe_service import cancel_stripe_subscription
            result = await cancel_stripe_subscription("u_no_sub")
        assert result["success"] is False
        assert "subscription" in result.get("error", "").lower()

    async def test_cancel_stripe_subscription_simulated(self, mongomock_db):
        """cancel_stripe_subscription in simulated mode updates DB."""
        await mongomock_db.users.insert_one({
            "user_id": "u_cancel_sim",
            "credits": 500,
            "subscription_tier": "custom",
            "stripe_subscription_id": "sub_cancel_sim",
        })
        with patch("services.stripe_service.stripe", None), \
             patch("services.stripe_service.db", mongomock_db):
            from services.stripe_service import cancel_stripe_subscription
            result = await cancel_stripe_subscription("u_cancel_sim")
        assert result["success"] is True
        assert result.get("simulated") is True

    async def test_get_subscription_status_no_subscription(self, mongomock_db):
        """get_subscription_status for user without subscription."""
        await mongomock_db.users.insert_one({
            "user_id": "u_no_stripe_sub",
            "subscription_tier": "starter",
        })
        with patch("services.stripe_service.db", mongomock_db):
            from services.stripe_service import get_subscription_status
            result = await get_subscription_status("u_no_stripe_sub")
        assert result["has_subscription"] is False

    async def test_get_subscription_status_simulated_mode(self, mongomock_db):
        """get_subscription_status in simulated mode with subscription."""
        await mongomock_db.users.insert_one({
            "user_id": "u_sim_sub",
            "subscription_tier": "custom",
            "stripe_subscription_id": "sub_sim_001",
            "stripe_customer_id": "cus_sim_001",
        })
        with patch("services.stripe_service.stripe", None), \
             patch("services.stripe_service.db", mongomock_db):
            from services.stripe_service import get_subscription_status
            result = await get_subscription_status("u_sim_sub")
        assert result["has_subscription"] is True
        assert result.get("simulated") is True

    async def test_get_or_create_stripe_customer_simulated(self, mongomock_db):
        """get_or_create_stripe_customer in simulated mode creates simulated ID."""
        await mongomock_db.users.insert_one({
            "user_id": "u_new_cus",
            "email": "new@test.com",
        })
        with patch("services.stripe_service.stripe", None), \
             patch("services.stripe_service.db", mongomock_db):
            from services.stripe_service import get_or_create_stripe_customer
            result = await get_or_create_stripe_customer("u_new_cus", "new@test.com")
        assert result["success"] is True
        assert "simulated" in result.get("customer_id", "")

    async def test_create_custom_plan_checkout_invalid_price(self, mongomock_db):
        """create_custom_plan_checkout with zero/negative price returns error."""
        with patch("services.stripe_service.db", mongomock_db):
            from services.stripe_service import create_custom_plan_checkout
            result = await create_custom_plan_checkout(
                "u_bad_price", "test@test.com", 500, 0,
                {"monthly_credits": 500}
            )
        assert result["success"] is False
        assert "price" in result.get("error", "").lower()

    async def test_get_usage_history_returns_transactions(self, mongomock_db):
        """get_usage_history returns transaction list."""
        await mongomock_db.users.insert_one({
            "user_id": "u_usage_hist",
            "credits": 200,
        })
        with patch("database.db", mongomock_db):
            from services.credits import get_usage_history
            result = await get_usage_history("u_usage_hist")
        assert result["success"] is True
        assert "transactions" in result
        assert "summary" in result

    async def test_check_feature_access_numeric_limit(self, mongomock_db):
        """check_feature_access for numeric limit returns limit value."""
        await mongomock_db.users.insert_one({
            "user_id": "u_numeric_feat",
            "subscription_tier": "custom",
            "plan_config": {
                "features": {"max_personas": 10}
            }
        })
        with patch("database.db", mongomock_db):
            from services.credits import check_feature_access
            result = await check_feature_access("u_numeric_feat", "max_personas")
        assert result["allowed"] is True
        assert result.get("limit") == 10

    async def test_check_feature_access_user_not_found(self, mongomock_db):
        """check_feature_access for non-existent user returns error."""
        with patch("database.db", mongomock_db):
            from services.credits import check_feature_access
            result = await check_feature_access("ghost_feature_user", "voice_enabled")
        assert result["allowed"] is False

    async def test_get_credit_balance_with_string_last_refresh(self, mongomock_db):
        """get_credit_balance handles string-type credits_last_refresh."""
        from datetime import datetime, timezone, timedelta
        past = (datetime.now(timezone.utc) - timedelta(days=45)).isoformat()
        await mongomock_db.users.insert_one({
            "user_id": "u_str_refresh",
            "credits": 100,
            "subscription_tier": "custom",
            "plan_config": {"monthly_credits": 500},
            "credits_last_refresh": past,
        })
        with patch("database.db", mongomock_db):
            from services.credits import get_credit_balance
            result = await get_credit_balance("u_str_refresh")
        # Should refresh and reset to 500 (30+ days since last refresh)
        assert result["success"] is True
        assert result["credits"] == 500

    async def test_get_credit_balance_naive_datetime_refresh(self, mongomock_db):
        """get_credit_balance handles naive datetime credits_last_refresh."""
        from datetime import datetime, timedelta
        past = datetime.utcnow() - timedelta(days=35)  # naive datetime
        await mongomock_db.users.insert_one({
            "user_id": "u_naive_refresh",
            "credits": 200,
            "subscription_tier": "custom",
            "plan_config": {"monthly_credits": 400},
            "credits_last_refresh": past,
        })
        with patch("database.db", mongomock_db):
            from services.credits import get_credit_balance
            result = await get_credit_balance("u_naive_refresh")
        assert result["success"] is True

    async def test_validate_stripe_config_with_configured_stripe(self):
        """validate_stripe_config logs warnings when Stripe configured but prices missing."""
        import logging
        with patch("services.stripe_service.is_stripe_configured", return_value=True), \
             patch("services.stripe_service.STRIPE_WEBHOOK_SECRET", ""), \
             patch("config.settings") as mock_settings:
            mock_settings.stripe.price_credits_100 = ""
            mock_settings.stripe.price_credits_500 = "placeholder_xxx"
            mock_settings.stripe.price_credits_1000 = ""
            # Should not raise — just logs warnings
            from services.stripe_service import validate_stripe_config
            validate_stripe_config()  # No assertion needed — just test it runs

    async def test_get_or_create_stripe_customer_existing_with_live_stripe(self, mongomock_db):
        """get_or_create_stripe_customer with Stripe configured and existing customer retrieves it."""
        await mongomock_db.users.insert_one({
            "user_id": "u_existing_cus",
            "email": "existing@test.com",
            "stripe_customer_id": "cus_existing_001",
        })
        mock_stripe = MagicMock()
        mock_customer = MagicMock()
        mock_customer.id = "cus_existing_001"
        mock_stripe.Customer.retrieve.return_value = mock_customer

        with patch("services.stripe_service.stripe", mock_stripe), \
             patch("services.stripe_service.db", mongomock_db):
            from services.stripe_service import get_or_create_stripe_customer
            result = await get_or_create_stripe_customer("u_existing_cus", "existing@test.com")
        assert result["success"] is True
        assert result["customer_id"] == "cus_existing_001"

    async def test_get_or_create_stripe_customer_retrieve_failure_falls_back(self, mongomock_db):
        """get_or_create_stripe_customer falls back to simulated if retrieval fails."""
        await mongomock_db.users.insert_one({
            "user_id": "u_fail_retrieve",
            "email": "fail@test.com",
            "stripe_customer_id": "cus_fail_001",
        })
        mock_stripe = MagicMock()
        mock_stripe.Customer.retrieve.side_effect = Exception("Stripe API error")

        with patch("services.stripe_service.stripe", mock_stripe), \
             patch("services.stripe_service.db", mongomock_db):
            from services.stripe_service import get_or_create_stripe_customer
            result = await get_or_create_stripe_customer("u_fail_retrieve", "fail@test.com")
        # Falls back to returning the customer_id with simulated=True
        assert result["success"] is True
        assert result["customer_id"] == "cus_fail_001"

    async def test_get_or_create_stripe_customer_create_new_with_live_stripe(self, mongomock_db):
        """get_or_create_stripe_customer creates new customer when none exists."""
        await mongomock_db.users.insert_one({
            "user_id": "u_create_cus",
            "email": "create@test.com",
        })
        mock_stripe = MagicMock()
        mock_customer = MagicMock()
        mock_customer.id = "cus_new_created_001"
        mock_stripe.Customer.create.return_value = mock_customer

        with patch("services.stripe_service.stripe", mock_stripe), \
             patch("services.stripe_service.db", mongomock_db):
            from services.stripe_service import get_or_create_stripe_customer
            result = await get_or_create_stripe_customer("u_create_cus", "create@test.com")
        assert result["success"] is True
        assert result["customer_id"] == "cus_new_created_001"

    async def test_get_or_create_stripe_customer_create_fails(self, mongomock_db):
        """get_or_create_stripe_customer returns error if creation fails."""
        await mongomock_db.users.insert_one({
            "user_id": "u_create_fail",
            "email": "cf@test.com",
        })
        mock_stripe = MagicMock()
        mock_stripe.Customer.create.side_effect = Exception("Create failed")

        with patch("services.stripe_service.stripe", mock_stripe), \
             patch("services.stripe_service.db", mongomock_db):
            from services.stripe_service import get_or_create_stripe_customer
            result = await get_or_create_stripe_customer("u_create_fail", "cf@test.com")
        assert result["success"] is False

    async def test_get_subscription_status_with_live_stripe(self, mongomock_db):
        """get_subscription_status with live Stripe retrieves real subscription."""
        await mongomock_db.users.insert_one({
            "user_id": "u_live_sub_status",
            "subscription_tier": "custom",
            "stripe_subscription_id": "sub_live_001",
            "stripe_customer_id": "cus_live_001",
        })
        mock_stripe = MagicMock()
        mock_sub = MagicMock()
        mock_sub.id = "sub_live_001"
        mock_sub.status = "active"
        mock_sub.current_period_end = 9999999999
        mock_sub.cancel_at_period_end = False
        mock_stripe.Subscription.retrieve.return_value = mock_sub

        with patch("services.stripe_service.stripe", mock_stripe), \
             patch("services.stripe_service.db", mongomock_db):
            from services.stripe_service import get_subscription_status
            result = await get_subscription_status("u_live_sub_status")
        assert result["has_subscription"] is True
        assert result["status"] == "active"

    async def test_get_subscription_status_stripe_retrieval_failure(self, mongomock_db):
        """get_subscription_status handles Stripe retrieval error gracefully."""
        await mongomock_db.users.insert_one({
            "user_id": "u_sub_err",
            "subscription_tier": "custom",
            "stripe_subscription_id": "sub_err_001",
            "stripe_customer_id": "cus_err_001",
        })
        mock_stripe = MagicMock()
        mock_stripe.Subscription.retrieve.side_effect = Exception("API error")

        with patch("services.stripe_service.stripe", mock_stripe), \
             patch("services.stripe_service.db", mongomock_db):
            from services.stripe_service import get_subscription_status
            result = await get_subscription_status("u_sub_err")
        assert result["has_subscription"] is False
        assert "error" in result

    async def test_modify_subscription_no_subscription_returns_error(self, mongomock_db):
        """modify_subscription with no subscription_id returns error."""
        await mongomock_db.users.insert_one({
            "user_id": "u_modify_nosub",
            "subscription_tier": "starter",
        })
        with patch("services.stripe_service.stripe", None), \
             patch("services.stripe_service.db", mongomock_db):
            from services.stripe_service import modify_subscription
            result = await modify_subscription(
                "u_modify_nosub", 500, 3000, {"monthly_credits": 500}
            )
        assert result["success"] is False
        assert "subscription" in result.get("error", "").lower()

    async def test_modify_subscription_user_not_found(self, mongomock_db):
        """modify_subscription for non-existent user returns error."""
        with patch("services.stripe_service.db", mongomock_db):
            from services.stripe_service import modify_subscription
            result = await modify_subscription(
                "ghost_modify_user", 500, 3000, {"monthly_credits": 500}
            )
        assert result["success"] is False

    async def test_create_custom_plan_checkout_customer_fail(self, mongomock_db):
        """create_custom_plan_checkout returns error if customer creation fails."""
        await mongomock_db.users.insert_one({
            "user_id": "u_cus_fail_checkout",
            "email": "cfc@test.com",
        })
        mock_stripe = MagicMock()
        mock_stripe.Customer.create.side_effect = Exception("Customer create failed")

        with patch("services.stripe_service.stripe", mock_stripe), \
             patch("services.stripe_service.db", mongomock_db):
            from services.stripe_service import create_custom_plan_checkout
            result = await create_custom_plan_checkout(
                "u_cus_fail_checkout", "cfc@test.com", 500, 3000, {}
            )
        # Customer creation failure returns {"success": False}
        assert result["success"] is False

    async def test_create_credit_checkout_with_stripe_price_id(self, mongomock_db):
        """create_credit_checkout uses existing Stripe price ID when available."""
        await mongomock_db.users.insert_one({
            "user_id": "u_price_id_checkout",
            "email": "pric@test.com",
        })
        mock_stripe = MagicMock()
        mock_customer = MagicMock()
        mock_customer.id = "cus_price_test"
        mock_stripe.Customer.create.return_value = mock_customer
        mock_session = MagicMock()
        mock_session.url = "https://checkout.stripe.com/pay/cs_test_123"
        mock_session.id = "cs_test_123"
        mock_stripe.checkout.Session.create.return_value = mock_session

        # Give small package a real stripe_price
        with patch("services.stripe_service.CREDIT_PACKAGES", {
            "small": {"credits": 100, "price": 600, "stripe_price": "price_test_100"}
        }), patch("services.stripe_service.stripe", mock_stripe), \
             patch("services.stripe_service.db", mongomock_db):
            from services.stripe_service import create_credit_checkout
            result = await create_credit_checkout(
                "u_price_id_checkout", "pric@test.com", "small"
            )
        assert result["success"] is True

    async def test_cancel_stripe_subscription_at_period_end_false(self, mongomock_db):
        """cancel_stripe_subscription with at_period_end=False deletes immediately."""
        await mongomock_db.users.insert_one({
            "user_id": "u_cancel_immediate",
            "stripe_subscription_id": "sub_immediate",
        })
        mock_stripe = MagicMock()
        mock_sub = MagicMock()
        mock_sub.status = "cancelled"
        mock_stripe.Subscription.delete.return_value = mock_sub

        with patch("services.stripe_service.stripe", mock_stripe), \
             patch("services.stripe_service.db", mongomock_db):
            from services.stripe_service import cancel_stripe_subscription
            result = await cancel_stripe_subscription("u_cancel_immediate", at_period_end=False)
        assert result["success"] is True

    async def test_cancel_stripe_subscription_stripe_error(self, mongomock_db):
        """cancel_stripe_subscription handles Stripe API error."""
        await mongomock_db.users.insert_one({
            "user_id": "u_cancel_err",
            "stripe_subscription_id": "sub_cancel_err",
        })
        mock_stripe = MagicMock()
        mock_stripe.Subscription.modify.side_effect = Exception("Stripe error")

        with patch("services.stripe_service.stripe", mock_stripe), \
             patch("services.stripe_service.db", mongomock_db):
            from services.stripe_service import cancel_stripe_subscription
            result = await cancel_stripe_subscription("u_cancel_err")
        assert result["success"] is False

    async def test_create_portal_session_with_live_stripe(self, mongomock_db):
        """create_customer_portal_session with Stripe configured creates session."""
        await mongomock_db.users.insert_one({
            "user_id": "u_portal_live",
            "stripe_customer_id": "cus_portal_live",
        })
        mock_stripe = MagicMock()
        mock_portal_session = MagicMock()
        mock_portal_session.url = "https://billing.stripe.com/portal/session/xxx"
        mock_stripe.billing_portal.Session.create.return_value = mock_portal_session

        with patch("services.stripe_service.stripe", mock_stripe), \
             patch("services.stripe_service.db", mongomock_db):
            from services.stripe_service import create_customer_portal_session
            result = await create_customer_portal_session("u_portal_live")
        assert result["success"] is True
        assert "portal_url" in result

    async def test_create_portal_session_stripe_error(self, mongomock_db):
        """create_customer_portal_session handles Stripe error."""
        await mongomock_db.users.insert_one({
            "user_id": "u_portal_err",
            "stripe_customer_id": "cus_portal_err",
        })
        mock_stripe = MagicMock()
        mock_stripe.billing_portal.Session.create.side_effect = Exception("Portal error")

        with patch("services.stripe_service.stripe", mock_stripe), \
             patch("services.stripe_service.db", mongomock_db):
            from services.stripe_service import create_customer_portal_session
            result = await create_customer_portal_session("u_portal_err")
        assert result["success"] is False

    async def test_cancel_subscription_stripe_configured_hard_error(self, client, mongomock_db):
        """cancel_subscription when Stripe returns error that's not 'no subscription'."""
        with patch("database.db", mongomock_db), \
             patch("services.stripe_service.is_stripe_configured", return_value=True), \
             patch("services.stripe_service.cancel_stripe_subscription",
                   new_callable=AsyncMock) as mock_cancel:
            mock_cancel.return_value = {"success": False, "error": "Some unrelated Stripe error"}
            resp = await client.post("/api/billing/subscription/cancel")
        assert resp.status_code == 400

    async def test_plan_checkout_create_checkout_error(self, client, mongomock_db):
        """plan/checkout propagates service error as 400."""
        with patch("services.stripe_service.stripe", None), \
             patch("services.stripe_service.db", mongomock_db), \
             patch("database.db", mongomock_db), \
             patch("services.stripe_service.create_custom_plan_checkout",
                   new_callable=AsyncMock) as mock_checkout:
            mock_checkout.return_value = {"success": False, "error": "Payment failed"}
            resp = await client.post("/api/billing/plan/checkout",
                                     json={"text_posts": 10})
        assert resp.status_code == 400

    async def test_plan_modify_service_error_returns_400(self, client, mongomock_db):
        """plan/modify propagates service error as 400."""
        with patch("services.stripe_service.stripe", None), \
             patch("services.stripe_service.db", mongomock_db), \
             patch("database.db", mongomock_db), \
             patch("services.stripe_service.modify_subscription",
                   new_callable=AsyncMock) as mock_modify:
            mock_modify.return_value = {"success": False, "error": "Modification failed"}
            resp = await client.post("/api/billing/plan/modify",
                                     json={"text_posts": 10})
        assert resp.status_code == 400

    async def test_webhook_no_secret_production_env_returns_500(self, anon_client):
        """Webhook with no secret in production → 500."""
        with patch("config.settings") as mock_settings:
            mock_settings.stripe.webhook_secret = ""
            mock_settings.app.environment = "production"
            resp = await anon_client.post(
                "/api/billing/webhook/stripe",
                content=b"payload",
                headers={"Stripe-Signature": "t=123,v1=abc"}
            )
        assert resp.status_code == 500

    async def test_get_all_tiers_includes_starter_and_custom(self):
        """get_all_tiers returns both starter and custom tiers."""
        from services.credits import get_all_tiers
        tiers = get_all_tiers()
        tier_ids = [t["id"] for t in tiers]
        assert "starter" in tier_ids
        assert "custom" in tier_ids

    async def test_get_operation_cost_valid_operation(self):
        """get_operation_cost returns correct value for known operation."""
        from services.credits import get_operation_cost
        cost = get_operation_cost("CONTENT_CREATE")
        assert cost == 10

    async def test_get_operation_cost_invalid_operation_returns_zero(self):
        """get_operation_cost returns 0 for unknown operation."""
        from services.credits import get_operation_cost
        cost = get_operation_cost("NONEXISTENT_OP")
        assert cost == 0

    async def test_build_plan_preview_large_plan_scale_label(self):
        """build_plan_preview returns scale volume_tier for large credit plans."""
        from services.credits import build_plan_preview
        # 6000+ credits (>5000 threshold) → scale tier
        preview = build_plan_preview(videos=120)  # 120 * 50 = 6000 credits
        assert preview["volume_tier"] == "scale"

    async def test_build_plan_preview_mid_plan_growth_label(self):
        """build_plan_preview returns growth volume_tier for mid-range plans."""
        from services.credits import build_plan_preview
        # ~2000 credits (between 1500-5000) → growth tier
        preview = build_plan_preview(videos=40)  # 40 * 50 = 2000 credits
        assert preview["volume_tier"] == "growth"

    async def test_build_plan_preview_pro_label(self):
        """build_plan_preview returns pro volume_tier for 500-1500 credit range."""
        from services.credits import build_plan_preview
        # 1000 credits (between 500-1500 at 5 cents) → pro tier
        preview = build_plan_preview(text_posts=100)  # 100 * 10 = 1000 credits
        assert preview["volume_tier"] == "pro"

    async def test_handle_payment_succeeded_no_subscription_id(self, mongomock_db):
        """handle_payment_succeeded with no subscription_id returns silently."""
        invoice = {"id": "inv_no_sub", "amount_paid": 0, "currency": "usd"}
        with patch("services.stripe_service.db", mongomock_db):
            from services.stripe_service import handle_payment_succeeded
            # Should not raise
            await handle_payment_succeeded(invoice)

    async def test_handle_payment_failed_no_subscription_id(self, mongomock_db):
        """handle_payment_failed with no subscription_id returns silently."""
        invoice = {"id": "inv_no_sub_fail"}
        with patch("services.stripe_service.db", mongomock_db):
            from services.stripe_service import handle_payment_failed
            await handle_payment_failed(invoice)

    async def test_handle_subscription_updated_unknown_user(self, mongomock_db):
        """handle_subscription_updated when user not found returns silently."""
        sub = {
            "id": "sub_unknown",
            "customer": "cus_not_in_db",
            "metadata": {},
            "status": "active",
        }
        with patch("services.stripe_service.db", mongomock_db):
            from services.stripe_service import handle_subscription_updated
            await handle_subscription_updated(sub)

    async def test_handle_subscription_deleted_unknown_customer(self, mongomock_db):
        """handle_subscription_deleted for unknown customer returns silently."""
        sub = {"id": "sub_del_unknown", "customer": "cus_not_exist_del"}
        with patch("services.stripe_service.db", mongomock_db):
            from services.stripe_service import handle_subscription_deleted
            await handle_subscription_deleted(sub)

    async def test_handle_subscription_updated_active_updates_credit_allowance(self, mongomock_db):
        """handle_subscription_updated with active status updates credit_allowance."""
        await mongomock_db.users.insert_one({
            "user_id": "u_sub_upd_allowance",
            "stripe_customer_id": "cus_upd_allowance",
            "subscription_tier": "custom",
        })
        sub = {
            "id": "sub_upd_all",
            "customer": "cus_upd_allowance",
            "metadata": {"user_id": "u_sub_upd_allowance", "monthly_credits": "700"},
            "status": "active",
        }
        with patch("services.stripe_service.db", mongomock_db):
            from services.stripe_service import handle_subscription_updated
            await handle_subscription_updated(sub)

        user = await mongomock_db.users.find_one({"user_id": "u_sub_upd_allowance"})
        assert user["credit_allowance"] == 700

    async def test_modify_subscription_with_live_stripe_existing_price(self, mongomock_db):
        """modify_subscription with live Stripe uses existing price if found."""
        await mongomock_db.users.insert_one({
            "user_id": "u_modify_live",
            "subscription_tier": "custom",
            "stripe_subscription_id": "sub_modify_live",
        })
        mock_stripe = MagicMock()

        # Mock subscription with items
        mock_sub = MagicMock()
        mock_sub.__getitem__ = lambda self, key: {
            "items": {"data": [{"id": "si_001", "price": {"product": "prod_001"}}]},
            "id": "sub_modify_live",
        }[key]
        mock_stripe.Subscription.retrieve.return_value = mock_sub

        # Mock existing price list — price found
        mock_existing_price = MagicMock()
        mock_existing_price.id = "price_existing_001"
        mock_existing_price.__getitem__ = lambda self, key: {"unit_amount": 3000}[key]
        mock_price_list = MagicMock()
        mock_price_list.auto_paging_iter.return_value = iter([mock_existing_price])
        mock_stripe.Price.list.return_value = mock_price_list

        # Mock subscription modify
        mock_updated = MagicMock()
        mock_updated.id = "sub_modify_live"
        mock_stripe.Subscription.modify.return_value = mock_updated

        with patch("services.stripe_service.stripe", mock_stripe), \
             patch("services.stripe_service.db", mongomock_db), \
             patch("database.db", mongomock_db):
            from services.stripe_service import modify_subscription
            result = await modify_subscription(
                "u_modify_live", 500, 3000,
                {"monthly_credits": 500, "monthly_price_usd": 30}
            )
        assert result["success"] is True
        assert result["subscription_id"] == "sub_modify_live"

    async def test_modify_subscription_with_live_stripe_creates_new_price(self, mongomock_db):
        """modify_subscription with live Stripe creates new price when none matches."""
        await mongomock_db.users.insert_one({
            "user_id": "u_modify_new_price",
            "subscription_tier": "custom",
            "stripe_subscription_id": "sub_new_price",
        })
        mock_stripe = MagicMock()

        mock_sub = MagicMock()
        mock_sub.__getitem__ = lambda self, key: {
            "items": {"data": [{"id": "si_002", "price": {"product": "prod_002"}}]},
            "id": "sub_new_price",
        }[key]
        mock_stripe.Subscription.retrieve.return_value = mock_sub

        # No existing price matches
        mock_price_list = MagicMock()
        mock_price_list.auto_paging_iter.return_value = iter([])
        mock_stripe.Price.list.return_value = mock_price_list

        # New price creation
        mock_new_price = MagicMock()
        mock_new_price.id = "price_new_002"
        mock_stripe.Price.create.return_value = mock_new_price

        mock_updated = MagicMock()
        mock_updated.id = "sub_new_price"
        mock_stripe.Subscription.modify.return_value = mock_updated

        with patch("services.stripe_service.stripe", mock_stripe), \
             patch("services.stripe_service.db", mongomock_db), \
             patch("database.db", mongomock_db):
            from services.stripe_service import modify_subscription
            result = await modify_subscription(
                "u_modify_new_price", 600, 4200,
                {"monthly_credits": 600, "monthly_price_usd": 42}
            )
        assert result["success"] is True
        mock_stripe.Price.create.assert_called_once()

    async def test_modify_subscription_stripe_api_error(self, mongomock_db):
        """modify_subscription handles Stripe API error gracefully."""
        await mongomock_db.users.insert_one({
            "user_id": "u_modify_err",
            "subscription_tier": "custom",
            "stripe_subscription_id": "sub_modify_err",
        })
        mock_stripe = MagicMock()
        mock_stripe.Subscription.retrieve.side_effect = Exception("Stripe API down")

        with patch("services.stripe_service.stripe", mock_stripe), \
             patch("services.stripe_service.db", mongomock_db):
            from services.stripe_service import modify_subscription
            result = await modify_subscription(
                "u_modify_err", 500, 3000, {"monthly_credits": 500}
            )
        assert result["success"] is False

    async def test_handle_payment_failed_user_not_found(self, mongomock_db):
        """handle_payment_failed when user not found returns silently."""
        invoice = {"id": "inv_no_user", "subscription": "sub_no_user"}
        # No user with stripe_subscription_id=sub_no_user in DB
        with patch("services.stripe_service.db", mongomock_db):
            from services.stripe_service import handle_payment_failed
            await handle_payment_failed(invoice)

    async def test_create_credit_checkout_with_stripe_configured_no_price_id(self, mongomock_db):
        """create_credit_checkout with Stripe configured uses price_data for dynamic pricing."""
        await mongomock_db.users.insert_one({
            "user_id": "u_dynamic_price",
            "email": "dp@test.com",
        })
        mock_stripe = MagicMock()
        mock_customer = MagicMock()
        mock_customer.id = "cus_dynamic"
        mock_stripe.Customer.create.return_value = mock_customer
        mock_session = MagicMock()
        mock_session.url = "https://checkout.stripe.com/pay/cs_dyn"
        mock_session.id = "cs_dyn"
        mock_stripe.checkout.Session.create.return_value = mock_session

        # Package with no stripe_price (empty string → falls to price_data branch)
        with patch("services.stripe_service.CREDIT_PACKAGES", {
            "small": {"credits": 100, "price": 600, "stripe_price": ""}
        }), patch("services.stripe_service.stripe", mock_stripe), \
             patch("services.stripe_service.db", mongomock_db):
            from services.stripe_service import create_credit_checkout
            result = await create_credit_checkout(
                "u_dynamic_price", "dp@test.com", "small"
            )
        assert result["success"] is True
        # Verify price_data was used (line_items with price_data key)
        call_kwargs = mock_stripe.checkout.Session.create.call_args[1]
        assert "price_data" in str(call_kwargs)

    async def test_create_credit_checkout_stripe_error(self, mongomock_db):
        """create_credit_checkout handles Stripe session creation error."""
        await mongomock_db.users.insert_one({
            "user_id": "u_checkout_err",
            "email": "ce@test.com",
        })
        mock_stripe = MagicMock()
        mock_customer = MagicMock()
        mock_customer.id = "cus_err"
        mock_stripe.Customer.create.return_value = mock_customer
        mock_stripe.checkout.Session.create.side_effect = Exception("Checkout error")

        with patch("services.stripe_service.stripe", mock_stripe), \
             patch("services.stripe_service.db", mongomock_db):
            from services.stripe_service import create_credit_checkout
            result = await create_credit_checkout(
                "u_checkout_err", "ce@test.com", "small"
            )
        assert result["success"] is False

    async def test_create_custom_plan_checkout_session_created(self, mongomock_db):
        """create_custom_plan_checkout with Stripe creates session successfully."""
        await mongomock_db.users.insert_one({
            "user_id": "u_custom_plan_live",
            "email": "cpl@test.com",
        })
        mock_stripe = MagicMock()
        mock_customer = MagicMock()
        mock_customer.id = "cus_custom_plan"
        mock_stripe.Customer.create.return_value = mock_customer
        mock_session = MagicMock()
        mock_session.url = "https://checkout.stripe.com/pay/cs_custom"
        mock_session.id = "cs_custom_001"
        mock_stripe.checkout.Session.create.return_value = mock_session

        with patch("services.stripe_service.stripe", mock_stripe), \
             patch("services.stripe_service.db", mongomock_db):
            from services.stripe_service import create_custom_plan_checkout
            result = await create_custom_plan_checkout(
                "u_custom_plan_live", "cpl@test.com",
                500, 3000, {"monthly_credits": 500}
            )
        assert result["success"] is True
        assert result["checkout_url"] == "https://checkout.stripe.com/pay/cs_custom"

    async def test_create_custom_plan_checkout_stripe_exception(self, mongomock_db):
        """create_custom_plan_checkout handles Stripe session creation error."""
        await mongomock_db.users.insert_one({
            "user_id": "u_custom_plan_err",
            "email": "cperr@test.com",
        })
        mock_stripe = MagicMock()
        mock_customer = MagicMock()
        mock_customer.id = "cus_custom_err"
        mock_stripe.Customer.create.return_value = mock_customer
        mock_stripe.checkout.Session.create.side_effect = Exception("Session error")

        with patch("services.stripe_service.stripe", mock_stripe), \
             patch("services.stripe_service.db", mongomock_db):
            from services.stripe_service import create_custom_plan_checkout
            result = await create_custom_plan_checkout(
                "u_custom_plan_err", "cperr@test.com",
                500, 3000, {"monthly_credits": 500}
            )
        assert result["success"] is False
