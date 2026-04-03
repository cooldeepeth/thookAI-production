"""Checkout flow tests — custom plan builder + credit packages (BILL-01).

Covers:
- create_custom_plan_checkout: happy paths, edge cases, simulated mode
- create_credit_checkout: all 3 package sizes, invalid package
- get_or_create_stripe_customer: new user, existing user, Stripe error
- Route-level: POST /api/billing/plan/checkout, POST /api/billing/credits/checkout,
  GET /api/billing/config, auth guards, validation

All tests use mongomock-motor for DB (no real MongoDB) and mock Stripe objects
so zero real Stripe API calls are made.
"""

import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _uid() -> str:
    return f"user_{uuid.uuid4().hex[:8]}"


def _make_stripe_session(session_id: str, url: str = None) -> MagicMock:
    """Build a minimal fake stripe.checkout.Session object."""
    s = MagicMock()
    s.id = session_id
    s.url = url or f"https://checkout.stripe.com/pay/{session_id}"
    return s


def _make_stripe_customer(customer_id: str) -> MagicMock:
    c = MagicMock()
    c.id = customer_id
    return c


# ---------------------------------------------------------------------------
# create_custom_plan_checkout — simulated mode (stripe=None)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestCustomPlanCheckoutSimulated:
    """Tests for create_custom_plan_checkout when Stripe is NOT configured."""

    async def test_happy_path_returns_simulated_url(self, mongomock_db):
        """Valid request returns simulated checkout URL and activates plan in DB."""
        user_id = _uid()
        await mongomock_db.users.insert_one({"user_id": user_id, "email": "a@test.com", "credits": 0})

        plan_config = {"monthly_credits": 500, "monthly_price_usd": 30}

        with patch("services.stripe_service.db", mongomock_db), \
             patch("database.db", mongomock_db), \
             patch("services.stripe_service.stripe", None):
            from services.stripe_service import create_custom_plan_checkout
            result = await create_custom_plan_checkout(
                user_id=user_id,
                email="a@test.com",
                monthly_credits=500,
                monthly_price_cents=3000,
                plan_config=plan_config,
            )

        assert result["success"] is True
        assert result["simulated"] is True
        assert "checkout_url" in result
        assert result["monthly_credits"] == 500
        assert result["monthly_price"] == 30.0

        user = await mongomock_db.users.find_one({"user_id": user_id})
        assert user["subscription_tier"] == "custom"
        assert user["credits"] == 500

    async def test_100_credits_simulated_activates(self, mongomock_db):
        """100 monthly credits — simulated mode still activates plan."""
        user_id = _uid()
        await mongomock_db.users.insert_one({"user_id": user_id, "email": "b@test.com", "credits": 0})
        plan_config = {"monthly_credits": 100}

        with patch("services.stripe_service.db", mongomock_db), \
             patch("database.db", mongomock_db), \
             patch("services.stripe_service.stripe", None):
            from services.stripe_service import create_custom_plan_checkout
            result = await create_custom_plan_checkout(
                user_id=user_id,
                email="b@test.com",
                monthly_credits=100,
                monthly_price_cents=600,
                plan_config=plan_config,
            )

        assert result["success"] is True
        user = await mongomock_db.users.find_one({"user_id": user_id})
        assert user["credits"] == 100

    async def test_250_credits_simulated(self, mongomock_db):
        """250 credits — verifies arbitrary credit amount works."""
        user_id = _uid()
        await mongomock_db.users.insert_one({"user_id": user_id, "email": "c@test.com", "credits": 0})

        with patch("services.stripe_service.db", mongomock_db), \
             patch("database.db", mongomock_db), \
             patch("services.stripe_service.stripe", None):
            from services.stripe_service import create_custom_plan_checkout
            result = await create_custom_plan_checkout(
                user_id=user_id,
                email="c@test.com",
                monthly_credits=250,
                monthly_price_cents=1500,
                plan_config={"monthly_credits": 250},
            )

        assert result["success"] is True
        assert result["monthly_credits"] == 250

    async def test_1000_credits_simulated(self, mongomock_db):
        """1000 credits — tier boundary test."""
        user_id = _uid()
        await mongomock_db.users.insert_one({"user_id": user_id, "email": "d@test.com", "credits": 0})

        with patch("services.stripe_service.db", mongomock_db), \
             patch("database.db", mongomock_db), \
             patch("services.stripe_service.stripe", None):
            from services.stripe_service import create_custom_plan_checkout
            result = await create_custom_plan_checkout(
                user_id=user_id,
                email="d@test.com",
                monthly_credits=1000,
                monthly_price_cents=5000,
                plan_config={"monthly_credits": 1000},
            )

        assert result["success"] is True
        assert result["monthly_credits"] == 1000

    async def test_2500_credits_simulated(self, mongomock_db):
        """2500 credits — volume discount tier."""
        user_id = _uid()
        await mongomock_db.users.insert_one({"user_id": user_id, "email": "e@test.com", "credits": 0})

        with patch("services.stripe_service.db", mongomock_db), \
             patch("database.db", mongomock_db), \
             patch("services.stripe_service.stripe", None):
            from services.stripe_service import create_custom_plan_checkout
            result = await create_custom_plan_checkout(
                user_id=user_id,
                email="e@test.com",
                monthly_credits=2500,
                monthly_price_cents=8800,
                plan_config={"monthly_credits": 2500},
            )

        assert result["success"] is True
        assert result["monthly_credits"] == 2500

    async def test_5000_credits_simulated(self, mongomock_db):
        """5000 credits — maximum discount tier."""
        user_id = _uid()
        await mongomock_db.users.insert_one({"user_id": user_id, "email": "f@test.com", "credits": 0})

        with patch("services.stripe_service.db", mongomock_db), \
             patch("database.db", mongomock_db), \
             patch("services.stripe_service.stripe", None):
            from services.stripe_service import create_custom_plan_checkout
            result = await create_custom_plan_checkout(
                user_id=user_id,
                email="f@test.com",
                monthly_credits=5000,
                monthly_price_cents=17500,
                plan_config={"monthly_credits": 5000},
            )

        assert result["success"] is True
        assert result["monthly_credits"] == 5000

    async def test_zero_price_returns_error(self, mongomock_db):
        """monthly_price_cents=0 → returns error immediately, no activation."""
        user_id = _uid()
        await mongomock_db.users.insert_one({"user_id": user_id, "email": "g@test.com", "credits": 0})

        with patch("services.stripe_service.db", mongomock_db), \
             patch("database.db", mongomock_db), \
             patch("services.stripe_service.stripe", None):
            from services.stripe_service import create_custom_plan_checkout
            result = await create_custom_plan_checkout(
                user_id=user_id,
                email="g@test.com",
                monthly_credits=500,
                monthly_price_cents=0,
                plan_config={"monthly_credits": 500},
            )

        assert result["success"] is False
        assert "price" in result.get("error", "").lower() or "invalid" in result.get("error", "").lower()

    async def test_negative_price_returns_error(self, mongomock_db):
        """monthly_price_cents < 0 → returns error."""
        user_id = _uid()

        with patch("services.stripe_service.db", mongomock_db), \
             patch("database.db", mongomock_db), \
             patch("services.stripe_service.stripe", None):
            from services.stripe_service import create_custom_plan_checkout
            result = await create_custom_plan_checkout(
                user_id=user_id,
                email="h@test.com",
                monthly_credits=500,
                monthly_price_cents=-100,
                plan_config={"monthly_credits": 500},
            )

        assert result["success"] is False


# ---------------------------------------------------------------------------
# create_custom_plan_checkout — real Stripe path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestCustomPlanCheckoutStripe:
    """Tests for create_custom_plan_checkout when Stripe IS configured."""

    async def test_happy_path_returns_checkout_url(self, mongomock_db):
        """Valid request creates Stripe session and returns checkout URL."""
        user_id = _uid()
        await mongomock_db.users.insert_one({
            "user_id": user_id,
            "email": "stripe@test.com",
            "stripe_customer_id": "cus_existing",
            "credits": 0,
        })

        mock_stripe = MagicMock()
        fake_customer = _make_stripe_customer("cus_existing")
        mock_stripe.Customer.retrieve.return_value = fake_customer

        fake_session = _make_stripe_session("cs_test_stripe_001")
        mock_stripe.checkout.Session.create.return_value = fake_session

        with patch("services.stripe_service.db", mongomock_db), \
             patch("database.db", mongomock_db), \
             patch("services.stripe_service.stripe", mock_stripe):
            from services.stripe_service import create_custom_plan_checkout
            result = await create_custom_plan_checkout(
                user_id=user_id,
                email="stripe@test.com",
                monthly_credits=500,
                monthly_price_cents=3000,
                plan_config={"monthly_credits": 500},
                success_url="https://app.com/success",
                cancel_url="https://app.com/cancel",
            )

        assert result["success"] is True
        assert result["checkout_url"] == fake_session.url
        assert result["session_id"] == "cs_test_stripe_001"
        assert result["monthly_credits"] == 500

    async def test_metadata_includes_user_id_and_credits(self, mongomock_db):
        """Checkout session metadata must include user_id and monthly_credits."""
        user_id = _uid()
        await mongomock_db.users.insert_one({
            "user_id": user_id,
            "email": "meta@test.com",
            "stripe_customer_id": "cus_meta",
        })

        captured_kwargs = {}

        mock_stripe = MagicMock()
        mock_stripe.Customer.retrieve.return_value = _make_stripe_customer("cus_meta")

        def fake_session_create(**kwargs):
            captured_kwargs.update(kwargs)
            return _make_stripe_session("cs_meta_001")

        mock_stripe.checkout.Session.create.side_effect = fake_session_create

        with patch("services.stripe_service.db", mongomock_db), \
             patch("database.db", mongomock_db), \
             patch("services.stripe_service.stripe", mock_stripe):
            from services.stripe_service import create_custom_plan_checkout
            await create_custom_plan_checkout(
                user_id=user_id,
                email="meta@test.com",
                monthly_credits=300,
                monthly_price_cents=1800,
                plan_config={"monthly_credits": 300},
            )

        metadata = captured_kwargs.get("metadata", {})
        assert metadata.get("user_id") == user_id
        assert metadata.get("monthly_credits") == "300"

    async def test_success_cancel_urls_passed_through(self, mongomock_db):
        """Custom success_url and cancel_url are forwarded to Stripe."""
        user_id = _uid()
        await mongomock_db.users.insert_one({
            "user_id": user_id,
            "email": "urls@test.com",
            "stripe_customer_id": "cus_urls",
        })

        captured = {}
        mock_stripe = MagicMock()
        mock_stripe.Customer.retrieve.return_value = _make_stripe_customer("cus_urls")

        def capture_create(**kwargs):
            captured.update(kwargs)
            return _make_stripe_session("cs_urls_001")

        mock_stripe.checkout.Session.create.side_effect = capture_create

        with patch("services.stripe_service.db", mongomock_db), \
             patch("database.db", mongomock_db), \
             patch("services.stripe_service.stripe", mock_stripe):
            from services.stripe_service import create_custom_plan_checkout
            await create_custom_plan_checkout(
                user_id=user_id,
                email="urls@test.com",
                monthly_credits=200,
                monthly_price_cents=1200,
                plan_config={"monthly_credits": 200},
                success_url="https://custom.com/success",
                cancel_url="https://custom.com/cancel",
            )

        assert captured.get("success_url") == "https://custom.com/success"
        assert captured.get("cancel_url") == "https://custom.com/cancel"

    async def test_pending_plan_config_stored_in_db(self, mongomock_db):
        """Before Stripe checkout completes, pending_plan_config is written to user record."""
        user_id = _uid()
        await mongomock_db.users.insert_one({
            "user_id": user_id,
            "email": "pending@test.com",
            "stripe_customer_id": "cus_pending",
        })

        mock_stripe = MagicMock()
        mock_stripe.Customer.retrieve.return_value = _make_stripe_customer("cus_pending")
        mock_stripe.checkout.Session.create.return_value = _make_stripe_session("cs_pending_001")

        plan_config = {"monthly_credits": 400, "test_key": "test_val"}

        with patch("services.stripe_service.db", mongomock_db), \
             patch("database.db", mongomock_db), \
             patch("services.stripe_service.stripe", mock_stripe):
            from services.stripe_service import create_custom_plan_checkout
            await create_custom_plan_checkout(
                user_id=user_id,
                email="pending@test.com",
                monthly_credits=400,
                monthly_price_cents=2400,
                plan_config=plan_config,
            )

        user = await mongomock_db.users.find_one({"user_id": user_id})
        assert user.get("pending_plan_config") is not None
        assert user["pending_plan_config"]["monthly_credits"] == 400

    async def test_stripe_exception_returns_error(self, mongomock_db):
        """Stripe API exception → success=False with error message."""
        user_id = _uid()
        await mongomock_db.users.insert_one({
            "user_id": user_id,
            "email": "err@test.com",
            "stripe_customer_id": "cus_err",
        })

        mock_stripe = MagicMock()
        mock_stripe.Customer.retrieve.return_value = _make_stripe_customer("cus_err")
        mock_stripe.checkout.Session.create.side_effect = Exception("Stripe API error")

        with patch("services.stripe_service.db", mongomock_db), \
             patch("database.db", mongomock_db), \
             patch("services.stripe_service.stripe", mock_stripe):
            from services.stripe_service import create_custom_plan_checkout
            result = await create_custom_plan_checkout(
                user_id=user_id,
                email="err@test.com",
                monthly_credits=500,
                monthly_price_cents=3000,
                plan_config={"monthly_credits": 500},
            )

        assert result["success"] is False
        assert "error" in result


# ---------------------------------------------------------------------------
# create_credit_checkout
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestCreditCheckout:
    """Tests for create_credit_checkout — all 3 package sizes + error cases."""

    async def test_small_package_simulated(self, mongomock_db):
        """Small package (100 credits) returns simulated checkout."""
        user_id = _uid()
        await mongomock_db.users.insert_one({"user_id": user_id, "email": "a@test.com"})

        with patch("services.stripe_service.db", mongomock_db), \
             patch("database.db", mongomock_db), \
             patch("services.stripe_service.stripe", None):
            from services.stripe_service import create_credit_checkout
            result = await create_credit_checkout(
                user_id=user_id,
                email="a@test.com",
                package="small",
            )

        assert result["success"] is True
        assert result["credits"] == 100
        assert result["simulated"] is True

    async def test_medium_package_simulated(self, mongomock_db):
        """Medium package (500 credits) returns simulated checkout."""
        user_id = _uid()
        await mongomock_db.users.insert_one({"user_id": user_id, "email": "b@test.com"})

        with patch("services.stripe_service.db", mongomock_db), \
             patch("database.db", mongomock_db), \
             patch("services.stripe_service.stripe", None):
            from services.stripe_service import create_credit_checkout
            result = await create_credit_checkout(
                user_id=user_id,
                email="b@test.com",
                package="medium",
            )

        assert result["success"] is True
        assert result["credits"] == 500

    async def test_large_package_simulated(self, mongomock_db):
        """Large package (1000 credits) returns simulated checkout."""
        user_id = _uid()
        await mongomock_db.users.insert_one({"user_id": user_id, "email": "c@test.com"})

        with patch("services.stripe_service.db", mongomock_db), \
             patch("database.db", mongomock_db), \
             patch("services.stripe_service.stripe", None):
            from services.stripe_service import create_credit_checkout
            result = await create_credit_checkout(
                user_id=user_id,
                email="c@test.com",
                package="large",
            )

        assert result["success"] is True
        assert result["credits"] == 1000

    async def test_invalid_package_returns_error(self, mongomock_db):
        """Unknown package type → success=False with error listing valid choices."""
        user_id = _uid()

        with patch("services.stripe_service.db", mongomock_db), \
             patch("database.db", mongomock_db), \
             patch("services.stripe_service.stripe", None):
            from services.stripe_service import create_credit_checkout
            result = await create_credit_checkout(
                user_id=user_id,
                email="d@test.com",
                package="mega_pack",
            )

        assert result["success"] is False
        assert "invalid" in result.get("error", "").lower() or "choose" in result.get("error", "").lower()

    async def test_credit_checkout_stripe_mode(self, mongomock_db):
        """With Stripe configured, credit checkout creates a real session."""
        user_id = _uid()
        await mongomock_db.users.insert_one({
            "user_id": user_id,
            "email": "stripe_credit@test.com",
            "stripe_customer_id": "cus_credit_001",
        })

        mock_stripe = MagicMock()
        mock_stripe.Customer.retrieve.return_value = _make_stripe_customer("cus_credit_001")
        fake_session = _make_stripe_session("cs_credit_001")
        mock_stripe.checkout.Session.create.return_value = fake_session

        with patch("services.stripe_service.db", mongomock_db), \
             patch("database.db", mongomock_db), \
             patch("services.stripe_service.stripe", mock_stripe):
            from services.stripe_service import create_credit_checkout
            result = await create_credit_checkout(
                user_id=user_id,
                email="stripe_credit@test.com",
                package="medium",
            )

        assert result["success"] is True
        assert result["session_id"] == "cs_credit_001"
        assert result["credits"] == 500

    async def test_credit_checkout_metadata_includes_user_id(self, mongomock_db):
        """Credit checkout session metadata includes user_id and credits."""
        user_id = _uid()
        await mongomock_db.users.insert_one({
            "user_id": user_id,
            "email": "meta_credit@test.com",
            "stripe_customer_id": "cus_meta_credit",
        })

        captured = {}
        mock_stripe = MagicMock()
        mock_stripe.Customer.retrieve.return_value = _make_stripe_customer("cus_meta_credit")

        def capture(**kwargs):
            captured.update(kwargs)
            return _make_stripe_session("cs_meta_credit_001")

        mock_stripe.checkout.Session.create.side_effect = capture

        with patch("services.stripe_service.db", mongomock_db), \
             patch("database.db", mongomock_db), \
             patch("services.stripe_service.stripe", mock_stripe):
            from services.stripe_service import create_credit_checkout
            await create_credit_checkout(
                user_id=user_id,
                email="meta_credit@test.com",
                package="small",
            )

        metadata = captured.get("metadata", {})
        assert metadata.get("user_id") == user_id
        assert metadata.get("type") == "credit_purchase"
        assert metadata.get("credits") == "100"


# ---------------------------------------------------------------------------
# get_or_create_stripe_customer
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestStripeCustomerManagement:
    """Tests for get_or_create_stripe_customer."""

    async def test_new_user_creates_customer_and_stores_id(self, mongomock_db):
        """New user (no stripe_customer_id) → creates customer and persists ID."""
        user_id = _uid()
        await mongomock_db.users.insert_one({
            "user_id": user_id,
            "email": "new@test.com",
        })

        mock_stripe = MagicMock()
        new_customer = _make_stripe_customer("cus_new_001")
        mock_stripe.Customer.create.return_value = new_customer

        with patch("services.stripe_service.db", mongomock_db), \
             patch("database.db", mongomock_db), \
             patch("services.stripe_service.stripe", mock_stripe):
            from services.stripe_service import get_or_create_stripe_customer
            result = await get_or_create_stripe_customer(user_id, "new@test.com", "New User")

        assert result["success"] is True
        assert result["customer_id"] == "cus_new_001"

        user = await mongomock_db.users.find_one({"user_id": user_id})
        assert user.get("stripe_customer_id") == "cus_new_001"

    async def test_existing_user_retrieves_customer_no_creation(self, mongomock_db):
        """User with existing stripe_customer_id → retrieves, does NOT create new."""
        user_id = _uid()
        await mongomock_db.users.insert_one({
            "user_id": user_id,
            "email": "existing@test.com",
            "stripe_customer_id": "cus_existing_001",
        })

        mock_stripe = MagicMock()
        existing_customer = _make_stripe_customer("cus_existing_001")
        mock_stripe.Customer.retrieve.return_value = existing_customer

        with patch("services.stripe_service.db", mongomock_db), \
             patch("database.db", mongomock_db), \
             patch("services.stripe_service.stripe", mock_stripe):
            from services.stripe_service import get_or_create_stripe_customer
            result = await get_or_create_stripe_customer(user_id, "existing@test.com")

        assert result["success"] is True
        assert result["customer_id"] == "cus_existing_001"
        mock_stripe.Customer.create.assert_not_called()

    async def test_stripe_customer_creation_error_returns_error(self, mongomock_db):
        """Stripe API exception during customer creation → returns error."""
        user_id = _uid()
        await mongomock_db.users.insert_one({"user_id": user_id, "email": "err@test.com"})

        mock_stripe = MagicMock()
        mock_stripe.Customer.create.side_effect = Exception("Stripe unavailable")

        with patch("services.stripe_service.db", mongomock_db), \
             patch("database.db", mongomock_db), \
             patch("services.stripe_service.stripe", mock_stripe):
            from services.stripe_service import get_or_create_stripe_customer
            result = await get_or_create_stripe_customer(user_id, "err@test.com")

        assert result["success"] is False
        assert "error" in result

    async def test_no_stripe_creates_simulated_customer(self, mongomock_db):
        """Without Stripe, creates simulated customer ID."""
        user_id = _uid()
        await mongomock_db.users.insert_one({"user_id": user_id, "email": "sim@test.com"})

        with patch("services.stripe_service.db", mongomock_db), \
             patch("database.db", mongomock_db), \
             patch("services.stripe_service.stripe", None):
            from services.stripe_service import get_or_create_stripe_customer
            result = await get_or_create_stripe_customer(user_id, "sim@test.com")

        assert result["success"] is True
        assert result.get("simulated") is True
        assert result["customer_id"].startswith("cus_simulated_")


# ---------------------------------------------------------------------------
# Route-level tests via FastAPI TestClient
# ---------------------------------------------------------------------------


@pytest.fixture
def billing_app(mongomock_db):
    """Minimal FastAPI app with the billing router, auth overridden."""
    from fastapi import FastAPI
    from routes.billing import router as billing_router
    from auth_utils import get_current_user

    test_user = {
        "user_id": "route_test_user",
        "email": "route@test.com",
        "subscription_tier": "starter",
        "credits": 200,
    }

    app = FastAPI()
    app.include_router(billing_router, prefix="/api")
    app.dependency_overrides[get_current_user] = lambda: test_user
    return app, test_user, mongomock_db


@pytest.mark.asyncio
class TestBillingRoutes:
    """Route-level integration tests using TestClient."""

    async def test_get_billing_config_returns_200(self, billing_app):
        """GET /api/billing/config returns 200 with pricing info (no auth required)."""
        import httpx
        from httpx import ASGITransport
        app, user, db = billing_app

        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/billing/config")

        assert response.status_code == 200
        data = response.json()
        assert "pricing_model" in data or "configured" in data

    async def test_plan_checkout_no_body_returns_422(self, billing_app):
        """POST /api/billing/plan/checkout with no body returns 422 (FastAPI validation)."""
        import httpx
        from httpx import ASGITransport
        app, user, db = billing_app

        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            # Send completely invalid body type
            response = await client.post(
                "/api/billing/plan/checkout",
                content=b"not json",
                headers={"Content-Type": "application/json"},
            )

        # FastAPI returns 422 for invalid body
        assert response.status_code == 422

    async def test_plan_checkout_all_zero_returns_400(self, billing_app, mongomock_db):
        """POST /api/billing/plan/checkout with all zeros = 0 credits → 400."""
        import httpx
        from httpx import ASGITransport
        app, user, db = billing_app

        await mongomock_db.users.insert_one(user)

        with patch("services.stripe_service.db", mongomock_db), \
             patch("database.db", mongomock_db), \
             patch("services.stripe_service.stripe", None):
            async with httpx.AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/api/billing/plan/checkout",
                    json={"text_posts": 0, "images": 0, "videos": 0},
                )

        assert response.status_code == 400

    async def test_plan_checkout_valid_request_simulated(self, billing_app, mongomock_db):
        """POST /api/billing/plan/checkout with valid request returns 200 (simulated)."""
        import httpx
        from httpx import ASGITransport
        app, user, db = billing_app

        await mongomock_db.users.insert_one(user)

        with patch("services.stripe_service.db", mongomock_db), \
             patch("database.db", mongomock_db), \
             patch("services.stripe_service.stripe", None):
            async with httpx.AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/api/billing/plan/checkout",
                    json={"text_posts": 10},
                )

        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is True

    async def test_credits_checkout_valid_package(self, billing_app, mongomock_db):
        """POST /api/billing/credits/checkout with valid package returns 200 (simulated)."""
        import httpx
        from httpx import ASGITransport
        app, user, db = billing_app

        await mongomock_db.users.insert_one(user)

        with patch("services.stripe_service.db", mongomock_db), \
             patch("database.db", mongomock_db), \
             patch("services.stripe_service.stripe", None):
            async with httpx.AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/api/billing/credits/checkout",
                    json={"package": "small"},
                )

        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is True

    async def test_credits_checkout_invalid_package_returns_400(self, billing_app, mongomock_db):
        """POST /api/billing/credits/checkout with invalid package → 400."""
        import httpx
        from httpx import ASGITransport
        app, user, db = billing_app

        await mongomock_db.users.insert_one(user)

        with patch("services.stripe_service.db", mongomock_db), \
             patch("database.db", mongomock_db), \
             patch("services.stripe_service.stripe", None):
            async with httpx.AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/api/billing/credits/checkout",
                    json={"package": "super_pack"},
                )

        assert response.status_code == 400

    async def test_plan_checkout_no_auth_returns_401(self):
        """POST /api/billing/plan/checkout without auth dependency override → 401."""
        import httpx
        from httpx import ASGITransport
        from fastapi import FastAPI
        from routes.billing import router as billing_router

        # App WITHOUT dependency override — auth will fail
        app_no_auth = FastAPI()
        app_no_auth.include_router(billing_router, prefix="/api")

        async with httpx.AsyncClient(
            transport=ASGITransport(app=app_no_auth), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/billing/plan/checkout",
                json={"text_posts": 10},
            )

        assert response.status_code == 401
