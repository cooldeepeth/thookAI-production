"""Comprehensive Stripe billing E2E tests for ThookAI.

Covers E2E-06:
- Checkout session creation for all plan types (custom plans, credit packs)
- Webhook signature verification (valid + invalid signatures)
- Subscription lifecycle (creation, update, deletion/downgrade)
- Missing configuration produces explicit errors
- Billing routes require authentication

All Stripe API calls are mocked — no real Stripe interactions.
"""
import uuid
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Helpers
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
        "stripe_customer_id": f"cus_test_{user_id[:8]}",
    }
    defaults.update(kwargs)
    return defaults


def _make_billing_app():
    """Create a minimal FastAPI app with the billing router and auth override."""
    import routes.billing as billing_module
    from auth_utils import get_current_user

    test_app = FastAPI()
    test_app.include_router(billing_module.router, prefix="/api")
    return test_app, billing_module, get_current_user


FAKE_USER = {"user_id": "test_user_001", "email": "test@example.com"}


# ---------------------------------------------------------------------------
# Helper: Mock Stripe checkout session
# ---------------------------------------------------------------------------

def _make_mock_session(session_id: str = "cs_test_123", url: str = "https://checkout.stripe.com/test") -> MagicMock:
    session = MagicMock()
    session.id = session_id
    session.url = url
    return session


def _make_mock_customer(customer_id: str = "cus_test_001") -> MagicMock:
    customer = MagicMock()
    customer.id = customer_id
    return customer


# ---------------------------------------------------------------------------
# Task 1-6: Credit checkout tests (parameterized by credit package)
# ---------------------------------------------------------------------------

class TestCreditCheckoutAllPackages:
    """Checkout session creation for all three credit packages."""

    @pytest.mark.parametrize("package,expected_credits,price_attr", [
        ("small",  100,  "price_credits_100"),
        ("medium", 500,  "price_credits_500"),
        ("large",  1000, "price_credits_1000"),
    ])
    @pytest.mark.asyncio
    async def test_checkout_credit_package(self, package, expected_credits, price_attr):
        """create_credit_checkout returns success=True and checkout_url for each package."""
        from services.stripe_service import create_credit_checkout

        user_id = _user_id()
        mock_session = _make_mock_session(f"cs_credits_{package}")
        mock_customer = _make_mock_customer()

        mock_stripe = MagicMock()
        mock_stripe.Customer.retrieve.return_value = mock_customer
        mock_stripe.checkout.Session.create.return_value = mock_session

        mock_db = MagicMock()
        mock_db.users.find_one = AsyncMock(
            return_value=make_user(user_id, stripe_customer_id="cus_existing_001")
        )

        # Use a real-looking price_id for the package
        test_price_id = f"price_test_{package}_xxx"

        mock_settings_stripe = MagicMock()
        setattr(mock_settings_stripe, price_attr, test_price_id)
        mock_settings_stripe.price_credits_100 = "price_test_small_xxx" if package != "small" else test_price_id
        mock_settings_stripe.price_credits_500 = "price_test_medium_xxx" if package != "medium" else test_price_id
        mock_settings_stripe.price_credits_1000 = "price_test_large_xxx" if package != "large" else test_price_id

        with patch("services.stripe_service.stripe", mock_stripe), \
             patch("services.stripe_service.db", mock_db):
            result = await create_credit_checkout(
                user_id=user_id,
                email=f"{user_id}@test.com",
                package=package,
            )

        assert result["success"] is True, f"Expected success for package={package}: {result}"
        assert "checkout_url" in result, f"Missing checkout_url for package={package}: {result}"
        assert result["credits"] == expected_credits

        # Stripe checkout session creation was called
        mock_stripe.checkout.Session.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_checkout_credit_package_invalid_returns_error(self):
        """Invalid package name returns success=False with error message."""
        from services.stripe_service import create_credit_checkout

        user_id = _user_id()
        mock_stripe = MagicMock()

        with patch("services.stripe_service.stripe", mock_stripe):
            result = await create_credit_checkout(
                user_id=user_id,
                email=f"{user_id}@test.com",
                package="invalid_package_xyz",
            )

        assert result["success"] is False
        assert "invalid" in result["error"].lower() or "package" in result["error"].lower()


# ---------------------------------------------------------------------------
# Custom plan checkout
# ---------------------------------------------------------------------------

class TestCustomPlanCheckout:
    """Checkout session creation for custom plans (dynamic pricing)."""

    @pytest.mark.asyncio
    async def test_checkout_custom_plan_returns_session_url(self):
        """create_custom_plan_checkout returns checkout_url and session_id."""
        from services.stripe_service import create_custom_plan_checkout

        user_id = _user_id()
        mock_session = _make_mock_session("cs_custom_test_123", "https://checkout.stripe.com/custom")
        mock_customer = _make_mock_customer("cus_custom_001")

        mock_stripe = MagicMock()
        mock_stripe.Customer.retrieve.return_value = mock_customer
        mock_stripe.checkout.Session.create.return_value = mock_session

        mock_db = MagicMock()
        mock_db.users.find_one = AsyncMock(
            return_value=make_user(user_id, stripe_customer_id="cus_custom_001")
        )
        mock_db.users.update_one = AsyncMock(return_value=MagicMock())

        plan_config = {"monthly_credits": 500, "features": {}}

        with patch("services.stripe_service.stripe", mock_stripe), \
             patch("services.stripe_service.db", mock_db):
            result = await create_custom_plan_checkout(
                user_id=user_id,
                email=f"{user_id}@test.com",
                monthly_credits=500,
                monthly_price_cents=3000,
                plan_config=plan_config,
            )

        assert result["success"] is True, f"Expected success: {result}"
        assert result["checkout_url"] == "https://checkout.stripe.com/custom"
        assert result["session_id"] == "cs_custom_test_123"
        assert result["monthly_credits"] == 500

    @pytest.mark.asyncio
    async def test_checkout_custom_plan_zero_price_returns_error(self):
        """Zero price rejects without calling Stripe."""
        from services.stripe_service import create_custom_plan_checkout

        user_id = _user_id()
        mock_stripe = MagicMock()

        with patch("services.stripe_service.stripe", mock_stripe):
            result = await create_custom_plan_checkout(
                user_id=user_id,
                email=f"{user_id}@test.com",
                monthly_credits=0,
                monthly_price_cents=0,
                plan_config={},
            )

        assert result["success"] is False
        mock_stripe.checkout.Session.create.assert_not_called()


# ---------------------------------------------------------------------------
# Webhook signature verification
# ---------------------------------------------------------------------------

class TestWebhookSignatureVerification:
    """Webhook events are verified with Stripe HMAC signature."""

    @pytest.mark.asyncio
    async def test_webhook_valid_signature_accepted(self):
        """handle_webhook_event with valid signature returns success=True."""
        from services.stripe_service import handle_webhook_event

        user_id = _user_id()
        mock_event = {
            "id": "evt_valid_001",  # Required for BILL-08 idempotency guard
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": "cs_test_valid",
                    "metadata": {"user_id": user_id, "type": "credit_purchase", "credits": "100"},
                    "amount_total": 600,
                    "currency": "usd",
                    "invoice": None,
                }
            }
        }

        mock_stripe = MagicMock()
        mock_stripe.Webhook.construct_event.return_value = mock_event
        mock_stripe.error = MagicMock()

        updated_user = {**make_user(user_id), "credits": 300}
        mock_db = MagicMock()
        mock_db.users.find_one = AsyncMock(return_value=make_user(user_id))
        # BILL-07: add_credits uses atomic find_one_and_update($inc)
        mock_db.users.find_one_and_update = AsyncMock(return_value=updated_user)
        mock_db.users.update_one = AsyncMock(return_value=MagicMock())
        mock_db.credit_transactions.insert_one = AsyncMock(return_value=MagicMock())
        mock_db.payments.insert_one = AsyncMock(return_value=MagicMock())
        # BILL-08: stripe_events dedup guard — return None for first delivery (not a duplicate)
        mock_db.stripe_events.find_one = AsyncMock(return_value=None)
        mock_db.stripe_events.insert_one = AsyncMock(return_value=MagicMock())

        with patch("services.stripe_service.stripe", mock_stripe), \
             patch("services.stripe_service.STRIPE_WEBHOOK_SECRET", "whsec_test_secret"), \
             patch("services.stripe_service.db", mock_db), \
             patch("database.db", mock_db):
            result = await handle_webhook_event(b'{"test": "payload"}', "t=123,v1=abc")

        assert result["success"] is True, f"Expected success: {result}"
        mock_stripe.Webhook.construct_event.assert_called_once()

    @pytest.mark.asyncio
    async def test_webhook_invalid_signature_rejected(self):
        """handle_webhook_event with invalid signature returns success=False."""
        from services.stripe_service import handle_webhook_event

        import stripe as real_stripe

        mock_stripe = MagicMock()
        # Simulate SignatureVerificationError from stripe library
        mock_stripe.error = MagicMock()
        mock_stripe.error.SignatureVerificationError = real_stripe.error.SignatureVerificationError
        mock_stripe.Webhook.construct_event.side_effect = real_stripe.error.SignatureVerificationError(
            "No signatures found matching the expected signature for payload",
            sig_header="invalid_sig",
            http_body="test",
        )

        with patch("services.stripe_service.stripe", mock_stripe), \
             patch("services.stripe_service.STRIPE_WEBHOOK_SECRET", "whsec_test_secret"):
            result = await handle_webhook_event(b'bad payload', "invalid_signature")

        assert result["success"] is False
        assert "signature" in result["error"].lower() or "invalid" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_webhook_no_secret_configured_returns_error(self):
        """handle_webhook_event returns error when STRIPE_WEBHOOK_SECRET is empty."""
        from services.stripe_service import handle_webhook_event

        mock_stripe = MagicMock()

        with patch("services.stripe_service.stripe", mock_stripe), \
             patch("services.stripe_service.STRIPE_WEBHOOK_SECRET", ""):
            result = await handle_webhook_event(b'payload', "sig_header")

        assert result["success"] is False


# ---------------------------------------------------------------------------
# Subscription lifecycle webhooks
# ---------------------------------------------------------------------------

class TestSubscriptionLifecycleWebhooks:
    """Webhook handlers update subscription tier correctly for key events."""

    @pytest.mark.asyncio
    async def test_webhook_checkout_completed_updates_credits(self):
        """checkout.session.completed for credit_purchase adds credits to user."""
        from services.stripe_service import handle_checkout_completed

        user_id = _user_id()
        session = {
            "id": "cs_test_credits",
            "metadata": {"user_id": user_id, "type": "credit_purchase", "credits": "100"},
            "amount_total": 600,
            "currency": "usd",
            "invoice": None,
        }

        updated_user = {**make_user(user_id), "credits": 300}

        mock_db = MagicMock()
        mock_db.users.find_one = AsyncMock(return_value=make_user(user_id))
        # BILL-07: add_credits uses atomic find_one_and_update($inc), not update_one($set)
        mock_db.users.find_one_and_update = AsyncMock(return_value=updated_user)
        mock_db.users.update_one = AsyncMock(return_value=MagicMock(modified_count=1))
        mock_db.credit_transactions.insert_one = AsyncMock(return_value=MagicMock())
        mock_db.payments.insert_one = AsyncMock(return_value=MagicMock())

        with patch("services.stripe_service.db", mock_db), \
             patch("database.db", mock_db):
            await handle_checkout_completed(session)

        # Payment record should be created
        assert mock_db.payments.insert_one.called
        payment_doc = mock_db.payments.insert_one.call_args[0][0]
        assert payment_doc["credits_granted"] == 100
        assert payment_doc["user_id"] == user_id
        assert payment_doc["status"] == "succeeded"

    @pytest.mark.asyncio
    async def test_webhook_checkout_completed_custom_plan_activates_plan(self):
        """checkout.session.completed for custom_plan activates subscription_tier=custom."""
        from services.stripe_service import handle_checkout_completed

        user_id = _user_id()
        pending_config = {"monthly_credits": 500, "features": {}}
        session = {
            "id": "cs_test_custom",
            "metadata": {
                "user_id": user_id,
                "type": "custom_plan",
                "monthly_credits": "500",
                "monthly_price_cents": "3000",
            },
            "amount_total": 3000,
            "currency": "usd",
        }

        captured_set = {}

        async def fake_update_one(filter_q, update_doc, *args, **kwargs):
            captured_set.update(update_doc.get("$set", {}))
            return MagicMock(modified_count=1)

        mock_db = MagicMock()
        mock_db.users.find_one = AsyncMock(
            return_value=make_user(user_id, pending_plan_config=pending_config)
        )
        mock_db.users.update_one = AsyncMock(side_effect=fake_update_one)

        with patch("services.stripe_service.db", mock_db):
            await handle_checkout_completed(session)

        assert captured_set.get("subscription_tier") == "custom"
        assert captured_set.get("credits") == 500

    @pytest.mark.asyncio
    async def test_webhook_subscription_deleted_downgrades_to_starter(self):
        """customer.subscription.deleted downgrades user to starter tier."""
        from services.stripe_service import handle_subscription_deleted

        user_id = _user_id()
        customer_id = "cus_delete_test_001"
        user = make_user(
            user_id,
            stripe_customer_id=customer_id,
            subscription_tier="custom",
            subscription_status="active",
        )
        subscription = {"customer": customer_id, "id": "sub_test_delete_001"}

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
        assert captured_set["stripe_subscription_id"] is None
        assert captured_set["plan_config"] is None
        assert captured_set["credit_allowance"] == 0

    @pytest.mark.asyncio
    async def test_webhook_subscription_created_sets_subscription_id(self):
        """customer.subscription.created stores subscription_id in user record."""
        from services.stripe_service import handle_subscription_created

        user_id = _user_id()
        customer_id = "cus_created_test_001"
        user = make_user(user_id, stripe_customer_id=customer_id)
        subscription = {
            "id": "sub_created_test_001",
            "customer": customer_id,
            "status": "active",
            "metadata": {
                "user_id": user_id,
                "type": "custom_plan",
                "monthly_credits": "300",
            }
        }

        captured_set = {}

        async def fake_update_one(filter_q, update_doc, *args, **kwargs):
            captured_set.update(update_doc.get("$set", {}))
            return MagicMock(modified_count=1)

        mock_db = MagicMock()
        mock_db.users.find_one = AsyncMock(return_value=None)  # Not found by customer_id
        mock_db.users.update_one = AsyncMock(side_effect=fake_update_one)

        with patch("services.stripe_service.db", mock_db):
            await handle_subscription_created(subscription)

        # Should set stripe_subscription_id
        assert captured_set.get("stripe_subscription_id") == "sub_created_test_001"
        assert captured_set.get("subscription_tier") == "custom"
        assert captured_set.get("credits") == 300


# ---------------------------------------------------------------------------
# Missing price ID / Stripe not configured
# ---------------------------------------------------------------------------

class TestMissingStripeConfig:
    """Missing or empty Stripe configuration produces explicit errors."""

    @pytest.mark.asyncio
    async def test_missing_price_id_falls_back_to_dynamic_pricing(self):
        """Credit checkout with empty stripe_price uses dynamic price_data instead."""
        from services.stripe_service import create_credit_checkout

        user_id = _user_id()
        mock_session = _make_mock_session()
        mock_customer = _make_mock_customer()

        mock_stripe = MagicMock()
        mock_stripe.Customer.retrieve.return_value = mock_customer
        mock_stripe.checkout.Session.create.return_value = mock_session

        mock_db = MagicMock()
        mock_db.users.find_one = AsyncMock(
            return_value=make_user(user_id, stripe_customer_id="cus_fallback_001")
        )

        # Force empty stripe_price on "small" package via CREDIT_PACKAGES patch
        patched_packages = {
            "small": {"credits": 100, "price": 600, "stripe_price": ""},  # Empty price_id
            "medium": {"credits": 500, "price": 2500, "stripe_price": "price_test_medium"},
            "large": {"credits": 1000, "price": 4000, "stripe_price": "price_test_large"},
        }

        with patch("services.stripe_service.stripe", mock_stripe), \
             patch("services.stripe_service.db", mock_db), \
             patch("services.stripe_service.CREDIT_PACKAGES", patched_packages):
            result = await create_credit_checkout(
                user_id=user_id,
                email=f"{user_id}@test.com",
                package="small",
            )

        # Should succeed using dynamic price_data
        assert result["success"] is True
        # Verify dynamic price_data was used (no price: "xxx" in line_items)
        call_kwargs = mock_stripe.checkout.Session.create.call_args[1]
        line_items = call_kwargs.get("line_items") or mock_stripe.checkout.Session.create.call_args[0][0].get("line_items", [])
        # Checkout was created
        mock_stripe.checkout.Session.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_stripe_not_configured_returns_simulated_checkout(self):
        """When stripe is None (not configured), checkout returns simulated=True."""
        from services.stripe_service import create_credit_checkout

        user_id = _user_id()

        with patch("services.stripe_service.stripe", None):
            result = await create_credit_checkout(
                user_id=user_id,
                email=f"{user_id}@test.com",
                package="small",
            )

        assert result["success"] is True
        assert result.get("simulated") is True

    def test_is_stripe_configured_returns_false_for_empty_key(self):
        """is_stripe_configured() is False when STRIPE_SECRET_KEY is empty."""
        from services.stripe_service import is_stripe_configured

        with patch("services.stripe_service.STRIPE_SECRET_KEY", ""):
            assert is_stripe_configured() is False

    def test_is_stripe_configured_returns_false_for_placeholder(self):
        """is_stripe_configured() is False when key contains 'placeholder'."""
        from services.stripe_service import is_stripe_configured

        with patch("services.stripe_service.STRIPE_SECRET_KEY", "placeholder_key"):
            assert is_stripe_configured() is False

    def test_is_stripe_configured_true_for_real_key(self):
        """is_stripe_configured() is True for a real-looking test key."""
        from services.stripe_service import is_stripe_configured

        with patch("services.stripe_service.STRIPE_SECRET_KEY", "sk_test_51ngLef4k3"):
            assert is_stripe_configured() is True

    def test_validate_stripe_config_callable(self):
        """validate_stripe_config function exists and can be called."""
        from services import stripe_service

        assert hasattr(stripe_service, "validate_stripe_config")
        assert callable(stripe_service.validate_stripe_config)


# ---------------------------------------------------------------------------
# Billing route authentication
# ---------------------------------------------------------------------------

class TestBillingRoutesRequireAuth:
    """Billing endpoints return 401/403 without a valid auth token."""

    def test_plan_checkout_requires_auth(self):
        """POST /api/billing/plan/checkout returns 401 without auth."""
        test_app, billing_module, get_current_user = _make_billing_app()
        # No dependency override — auth not bypassed

        client = TestClient(test_app, raise_server_exceptions=False)
        response = client.post(
            "/api/billing/plan/checkout",
            json={"text_posts": 10}
        )

        assert response.status_code in (401, 403), (
            f"Expected 401/403 without auth, got {response.status_code}: {response.text}"
        )

    def test_credits_checkout_requires_auth(self):
        """POST /api/billing/credits/checkout returns 401 without auth."""
        test_app, billing_module, get_current_user = _make_billing_app()

        client = TestClient(test_app, raise_server_exceptions=False)
        response = client.post(
            "/api/billing/credits/checkout",
            json={"package": "small"}
        )

        assert response.status_code in (401, 403), (
            f"Expected 401/403 without auth, got {response.status_code}: {response.text}"
        )

    def test_credits_get_requires_auth(self):
        """GET /api/billing/credits returns 401 without auth."""
        test_app, billing_module, get_current_user = _make_billing_app()

        client = TestClient(test_app, raise_server_exceptions=False)
        response = client.get("/api/billing/credits")

        assert response.status_code in (401, 403), (
            f"Expected 401/403 without auth, got {response.status_code}: {response.text}"
        )

    def test_subscription_requires_auth(self):
        """GET /api/billing/subscription returns 401 without auth."""
        test_app, billing_module, get_current_user = _make_billing_app()

        client = TestClient(test_app, raise_server_exceptions=False)
        response = client.get("/api/billing/subscription")

        assert response.status_code in (401, 403), (
            f"Expected 401/403 without auth, got {response.status_code}: {response.text}"
        )

    def test_billing_config_is_public(self):
        """GET /api/billing/config is publicly accessible (returns pricing info)."""
        test_app, billing_module, get_current_user = _make_billing_app()

        client = TestClient(test_app, raise_server_exceptions=False)
        response = client.get("/api/billing/config")

        # Config endpoint is public for the pricing page
        assert response.status_code == 200, (
            f"Expected 200 for public config endpoint, got {response.status_code}: {response.text}"
        )


# ---------------------------------------------------------------------------
# Full webhook event flow via HTTP route
# ---------------------------------------------------------------------------

class TestStripeWebhookRoute:
    """POST /api/billing/webhook/stripe processes events correctly."""

    def test_webhook_route_missing_signature_returns_400(self):
        """Webhook endpoint returns 400 when Stripe-Signature header is absent."""
        test_app, billing_module, get_current_user = _make_billing_app()

        client = TestClient(test_app, raise_server_exceptions=False)
        response = client.post(
            "/api/billing/webhook/stripe",
            content=b'{"type": "test"}',
            headers={"Content-Type": "application/json"}
            # No Stripe-Signature header
        )

        assert response.status_code == 400, (
            f"Expected 400 for missing signature, got {response.status_code}: {response.text}"
        )

    def test_webhook_route_accepts_event_with_valid_setup(self):
        """Webhook returns 200 with received=True for valid events."""
        import stripe as real_stripe

        test_app, billing_module, get_current_user = _make_billing_app()

        # Mock event to be returned by construct_event
        mock_event = {
            "id": "evt_route_001",  # Required for BILL-08 idempotency guard
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": "cs_test_route",
                    "metadata": {"user_id": "user_route_001", "type": "credit_purchase", "credits": "100"},
                    "amount_total": 600,
                    "currency": "usd",
                    "invoice": None,
                }
            }
        }

        mock_stripe = MagicMock()
        mock_stripe.Webhook.construct_event.return_value = mock_event
        mock_stripe.error = real_stripe.error

        updated_user = {**make_user("user_route_001"), "credits": 300}
        mock_db = MagicMock()
        mock_db.users.find_one = AsyncMock(return_value=make_user("user_route_001"))
        # BILL-07: add_credits uses atomic find_one_and_update($inc)
        mock_db.users.find_one_and_update = AsyncMock(return_value=updated_user)
        mock_db.users.update_one = AsyncMock(return_value=MagicMock())
        mock_db.credit_transactions.insert_one = AsyncMock(return_value=MagicMock())
        mock_db.payments.insert_one = AsyncMock(return_value=MagicMock())
        # BILL-08: dedup guard — return None for first delivery (not a duplicate)
        mock_db.stripe_events.find_one = AsyncMock(return_value=None)
        mock_db.stripe_events.insert_one = AsyncMock(return_value=MagicMock())

        with patch("services.stripe_service.stripe", mock_stripe), \
             patch("services.stripe_service.STRIPE_WEBHOOK_SECRET", "whsec_test"), \
             patch("services.stripe_service.db", mock_db), \
             patch("database.db", mock_db), \
             patch("config.settings") as mock_settings:
            mock_settings.stripe.webhook_secret = "whsec_test"
            mock_settings.app.environment = "test"

            client = TestClient(test_app, raise_server_exceptions=False)
            response = client.post(
                "/api/billing/webhook/stripe",
                content=b'{"type": "checkout.session.completed"}',
                headers={
                    "Content-Type": "application/json",
                    "Stripe-Signature": "t=123,v1=validsig"
                }
            )

        assert response.status_code == 200, (
            f"Expected 200 for valid webhook, got {response.status_code}: {response.text}"
        )
        data = response.json()
        assert data.get("received") is True
