"""TDD: Missing webhook deduplication — BILL-08.

BUG: handle_webhook_event has no idempotency guard. Retried or duplicate
Stripe events re-execute handlers, causing double credit additions.
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timezone


def _make_stripe_event(event_id: str, event_type: str, data: dict) -> dict:
    return {
        "id": event_id,
        "type": event_type,
        "data": {"object": data},
    }


@pytest.mark.asyncio
class TestWebhookDeduplication:

    @pytest.fixture(autouse=True)
    async def _ensure_unique_index(self, mongomock_db):
        """Create the unique index on stripe_events.event_id for dedup tests."""
        await mongomock_db.stripe_events.create_index("event_id", unique=True)

    async def test_first_event_processes_successfully(self, mongomock_db):
        """First delivery of a Stripe event processes and returns success."""
        event = _make_stripe_event("evt_first_001", "checkout.session.completed", {
            "metadata": {"user_id": "user_dedup_1", "type": "credit_purchase", "credits": "100"},
            "amount_total": 600, "currency": "usd", "invoice": None, "id": "cs_test_1",
        })
        await mongomock_db.users.insert_one({
            "user_id": "user_dedup_1", "credits": 50, "email": "dedup@test.com",
            "subscription_tier": "starter",
        })

        with patch("services.stripe_service.db", mongomock_db), \
             patch("database.db", mongomock_db), \
             patch("services.stripe_service.stripe") as mock_stripe, \
             patch("services.stripe_service.STRIPE_WEBHOOK_SECRET", "whsec_test"):
            mock_stripe.Webhook.construct_event.return_value = event
            mock_stripe.error = MagicMock()
            mock_stripe.error.SignatureVerificationError = Exception

            from services.stripe_service import handle_webhook_event
            result = await handle_webhook_event(b"payload", "sig_header")

        assert result["success"] is True
        assert result.get("duplicate") is not True

    async def test_duplicate_event_skipped(self, mongomock_db):
        """Same event_id delivered twice: second call returns duplicate=True, no re-processing."""
        event = _make_stripe_event("evt_dup_001", "checkout.session.completed", {
            "metadata": {"user_id": "user_dedup_2", "type": "credit_purchase", "credits": "100"},
            "amount_total": 600, "currency": "usd", "invoice": None, "id": "cs_test_2",
        })
        await mongomock_db.users.insert_one({
            "user_id": "user_dedup_2", "credits": 50, "email": "dedup2@test.com",
            "subscription_tier": "starter",
        })

        with patch("services.stripe_service.db", mongomock_db), \
             patch("database.db", mongomock_db), \
             patch("services.stripe_service.stripe") as mock_stripe, \
             patch("services.stripe_service.STRIPE_WEBHOOK_SECRET", "whsec_test"):
            mock_stripe.Webhook.construct_event.return_value = event
            mock_stripe.error = MagicMock()
            mock_stripe.error.SignatureVerificationError = Exception

            from services.stripe_service import handle_webhook_event
            result1 = await handle_webhook_event(b"payload", "sig")
            result2 = await handle_webhook_event(b"payload", "sig")

        assert result1["success"] is True
        assert result2["success"] is True
        assert result2.get("duplicate") is True

        # Credits must have been added only ONCE
        user = await mongomock_db.users.find_one({"user_id": "user_dedup_2"})
        # Without fix: 250 (double-added); With fix: 150 (added once)
        assert user["credits"] == 150, f"Credits double-added: {user['credits']}"

    async def test_different_event_ids_both_process(self, mongomock_db):
        """Two different event IDs for the same type both process (no false positive)."""
        await mongomock_db.users.insert_one({
            "user_id": "user_dedup_3", "credits": 0, "email": "d3@test.com",
            "subscription_tier": "starter",
        })

        with patch("services.stripe_service.db", mongomock_db), \
             patch("database.db", mongomock_db), \
             patch("services.stripe_service.stripe") as mock_stripe, \
             patch("services.stripe_service.STRIPE_WEBHOOK_SECRET", "whsec_test"):
            mock_stripe.error = MagicMock()
            mock_stripe.error.SignatureVerificationError = Exception

            from services.stripe_service import handle_webhook_event

            for evt_id, credits in [("evt_a", "100"), ("evt_b", "100")]:
                event = _make_stripe_event(evt_id, "checkout.session.completed", {
                    "metadata": {"user_id": "user_dedup_3", "type": "credit_purchase", "credits": credits},
                    "amount_total": 600, "currency": "usd", "invoice": None, "id": f"cs_{evt_id}",
                })
                mock_stripe.Webhook.construct_event.return_value = event
                await handle_webhook_event(b"payload", "sig")

        user = await mongomock_db.users.find_one({"user_id": "user_dedup_3"})
        assert user["credits"] == 200  # Both distinct events processed

    async def test_event_recorded_in_stripe_events_collection(self, mongomock_db):
        """After processing, the event_id is stored in stripe_events collection."""
        event = _make_stripe_event("evt_record_001", "invoice.payment_succeeded", {
            "subscription": "sub_test", "lines": {"data": [{"metadata": {}}]},
        })

        with patch("services.stripe_service.db", mongomock_db), \
             patch("database.db", mongomock_db), \
             patch("services.stripe_service.stripe") as mock_stripe, \
             patch("services.stripe_service.STRIPE_WEBHOOK_SECRET", "whsec_test"):
            mock_stripe.Webhook.construct_event.return_value = event
            mock_stripe.error = MagicMock()
            mock_stripe.error.SignatureVerificationError = Exception

            from services.stripe_service import handle_webhook_event
            await handle_webhook_event(b"payload", "sig")

        stored = await mongomock_db.stripe_events.find_one({"event_id": "evt_record_001"})
        assert stored is not None
        assert stored["event_type"] == "invoice.payment_succeeded"
