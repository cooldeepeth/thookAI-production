"""
Stripe Payment Integration for ThookAI

Handles:
- Custom plan subscriptions (plan builder)
- One-time credit purchases
- Webhooks for payment events
- Customer management
"""

import logging
import uuid
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from database import db
from config import settings

logger = logging.getLogger(__name__)

# Stripe API keys from config
STRIPE_SECRET_KEY = settings.stripe.secret_key or ''
STRIPE_WEBHOOK_SECRET = settings.stripe.webhook_secret or ''
STRIPE_PUBLISHABLE_KEY = settings.stripe.publishable_key or ''


def is_stripe_configured() -> bool:
    """Check if Stripe is properly configured."""
    return bool(STRIPE_SECRET_KEY and not STRIPE_SECRET_KEY.startswith('placeholder'))


def validate_stripe_config():
    """Log warnings for missing Stripe configuration in production."""
    if not is_stripe_configured():
        logger.warning("STRIPE: Secret key not configured. Payment features will use simulated mode.")
        return

    missing_prices = []
    credit_prices = [
        ("STRIPE_PRICE_CREDITS_100", settings.stripe.price_credits_100),
        ("STRIPE_PRICE_CREDITS_500", settings.stripe.price_credits_500),
        ("STRIPE_PRICE_CREDITS_1000", settings.stripe.price_credits_1000),
    ]
    for name, value in credit_prices:
        if not value or value.startswith("placeholder"):
            missing_prices.append(name)

    if missing_prices:
        logger.warning(
            "STRIPE: Credit package Price IDs not configured: %s. "
            "Credit package checkout will use dynamic pricing.",
            ", ".join(missing_prices),
        )

    if not STRIPE_WEBHOOK_SECRET:
        logger.error(
            "STRIPE: STRIPE_WEBHOOK_SECRET not configured. "
            "Webhook signature verification will fail in production."
        )


# Initialize Stripe if available
stripe = None
if is_stripe_configured():
    try:
        import stripe as stripe_lib
        stripe_lib.api_key = STRIPE_SECRET_KEY
        stripe = stripe_lib
        logger.info("Stripe initialized successfully")
    except ImportError:
        logger.warning("Stripe library not installed. Run: pip install stripe")
else:
    logger.warning("Stripe not configured. Payment features will be simulated.")

# Run validation on module import
validate_stripe_config()


# ============ CREDIT PACKAGES (one-time purchases) ============

CREDIT_PACKAGES = {
    "small": {"credits": 100, "price": 600, "stripe_price": settings.stripe.price_credits_100 or ''},
    "medium": {"credits": 500, "price": 2500, "stripe_price": settings.stripe.price_credits_500 or ''},
    "large": {"credits": 1000, "price": 4000, "stripe_price": settings.stripe.price_credits_1000 or ''},
}


# ============ CUSTOMER MANAGEMENT ============

async def get_or_create_stripe_customer(user_id: str, email: str, name: str = None) -> Dict[str, Any]:
    """Get existing Stripe customer or create new one."""

    user = await db.users.find_one({"user_id": user_id}, {"stripe_customer_id": 1})

    if user and user.get("stripe_customer_id"):
        if stripe:
            try:
                customer = stripe.Customer.retrieve(user["stripe_customer_id"])
                return {"success": True, "customer_id": customer.id, "customer": customer}
            except Exception as e:
                logger.error(f"Failed to retrieve Stripe customer: {e}")
        return {"success": True, "customer_id": user["stripe_customer_id"], "simulated": True}

    # Create new customer
    if stripe:
        try:
            customer = stripe.Customer.create(
                email=email,
                name=name,
                metadata={"user_id": user_id}
            )

            await db.users.update_one(
                {"user_id": user_id},
                {"$set": {"stripe_customer_id": customer.id}}
            )

            return {"success": True, "customer_id": customer.id, "customer": customer}
        except Exception as e:
            logger.error(f"Failed to create Stripe customer: {e}")
            return {"success": False, "error": str(e)}

    # Simulated mode
    simulated_id = f"cus_simulated_{user_id[:8]}"
    await db.users.update_one(
        {"user_id": user_id},
        {"$set": {"stripe_customer_id": simulated_id}}
    )
    return {"success": True, "customer_id": simulated_id, "simulated": True}


# ============ CUSTOM PLAN CHECKOUT ============

async def create_custom_plan_checkout(
    user_id: str,
    email: str,
    monthly_credits: int,
    monthly_price_cents: int,
    plan_config: Dict[str, Any],
    success_url: str = None,
    cancel_url: str = None
) -> Dict[str, Any]:
    """Create a Stripe Checkout session for a custom plan subscription.

    Uses Stripe's dynamic pricing (price_data) to create a subscription
    at the user's calculated monthly price.
    """
    if monthly_price_cents <= 0:
        return {"success": False, "error": "Invalid plan price"}

    if not stripe:
        # Simulated mode
        simulated_session_id = f"cs_custom_sim_{user_id[:8]}"
        # In simulated mode, activate the plan directly
        await _activate_custom_plan(user_id, monthly_credits, monthly_price_cents, plan_config)
        return {
            "success": True,
            "simulated": True,
            "checkout_url": f"/dashboard?subscription=success",
            "session_id": simulated_session_id,
            "monthly_price": monthly_price_cents / 100,
            "monthly_credits": monthly_credits,
            "message": "Stripe not configured. Plan activated directly (simulated)."
        }

    try:
        customer_result = await get_or_create_stripe_customer(user_id, email)
        if not customer_result.get("success"):
            return customer_result

        session = stripe.checkout.Session.create(
            customer=customer_result["customer_id"],
            payment_method_types=["card"],
            line_items=[{
                "price_data": {
                    "currency": "usd",
                    "product_data": {
                        "name": f"ThookAI Custom Plan — {monthly_credits} credits/mo",
                        "description": f"{monthly_credits} credits per month with volume pricing"
                    },
                    "unit_amount": monthly_price_cents,
                    "recurring": {"interval": "month"}
                },
                "quantity": 1
            }],
            mode="subscription",
            success_url=success_url or f"{settings.app.frontend_url}/dashboard?subscription=success",
            cancel_url=cancel_url or f"{settings.app.frontend_url}/pricing?subscription=cancelled",
            metadata={
                "user_id": user_id,
                "type": "custom_plan",
                "monthly_credits": str(monthly_credits),
                "monthly_price_cents": str(monthly_price_cents),
            },
            subscription_data={
                "metadata": {
                    "user_id": user_id,
                    "type": "custom_plan",
                    "monthly_credits": str(monthly_credits),
                }
            }
        )

        # Store pending plan config (activated on webhook confirmation)
        await db.users.update_one(
            {"user_id": user_id},
            {"$set": {"pending_plan_config": plan_config}}
        )

        return {
            "success": True,
            "checkout_url": session.url,
            "session_id": session.id,
            "monthly_price": monthly_price_cents / 100,
            "monthly_credits": monthly_credits
        }
    except Exception as e:
        logger.error(f"Failed to create custom plan checkout: {e}")
        return {"success": False, "error": str(e)}


async def _activate_custom_plan(
    user_id: str,
    monthly_credits: int,
    monthly_price_cents: int,
    plan_config: Dict[str, Any]
):
    """Activate a custom plan for a user (called after successful payment)."""
    now = datetime.now(timezone.utc)
    await db.users.update_one(
        {"user_id": user_id},
        {"$set": {
            "subscription_tier": "custom",
            "plan_config": plan_config,
            "credits": monthly_credits,
            "credit_allowance": monthly_credits,
            "credits_last_refresh": now,
            "subscription_status": "active",
            "subscription_started": now,
            "subscription_updated_at": now,
        },
        "$unset": {"pending_plan_config": ""}}
    )
    logger.info(f"Custom plan activated for user {user_id}: {monthly_credits} credits at ${monthly_price_cents / 100}/mo")


# ============ CREDIT PURCHASE CHECKOUT ============

async def create_credit_checkout(
    user_id: str,
    email: str,
    package: str,
    success_url: str = None,
    cancel_url: str = None
) -> Dict[str, Any]:
    """Create checkout session for one-time credit purchase."""

    if package not in CREDIT_PACKAGES:
        return {"success": False, "error": f"Invalid package. Choose from: {list(CREDIT_PACKAGES.keys())}"}

    pkg = CREDIT_PACKAGES[package]

    if not stripe:
        return {
            "success": True,
            "simulated": True,
            "checkout_url": f"/billing/simulate-credits?package={package}",
            "session_id": f"cs_credits_simulated_{user_id[:8]}",
            "credits": pkg["credits"],
            "price": pkg["price"] / 100,
            "message": "Stripe not configured. Using simulated checkout."
        }

    try:
        customer_result = await get_or_create_stripe_customer(user_id, email)
        if not customer_result.get("success"):
            return customer_result

        if pkg.get("stripe_price"):
            line_items = [{"price": pkg["stripe_price"], "quantity": 1}]
        else:
            line_items = [{
                "price_data": {
                    "currency": "usd",
                    "product_data": {
                        "name": f"{pkg['credits']} ThookAI Credits",
                        "description": f"One-time purchase of {pkg['credits']} credits"
                    },
                    "unit_amount": pkg["price"]
                },
                "quantity": 1
            }]

        session = stripe.checkout.Session.create(
            customer=customer_result["customer_id"],
            payment_method_types=["card"],
            line_items=line_items,
            mode="payment",
            success_url=success_url or f"{settings.app.frontend_url}/settings?credits=success",
            cancel_url=cancel_url or f"{settings.app.frontend_url}/settings?credits=cancelled",
            metadata={
                "user_id": user_id,
                "type": "credit_purchase",
                "credits": str(pkg["credits"])
            }
        )

        return {
            "success": True,
            "checkout_url": session.url,
            "session_id": session.id,
            "credits": pkg["credits"],
            "price": pkg["price"] / 100
        }
    except Exception as e:
        logger.error(f"Failed to create credit checkout: {e}")
        return {"success": False, "error": str(e)}


# ============ SUBSCRIPTION STATUS ============

async def get_subscription_status(user_id: str) -> Dict[str, Any]:
    """Get current subscription status from Stripe."""

    user = await db.users.find_one({"user_id": user_id}, {
        "stripe_customer_id": 1, "stripe_subscription_id": 1,
        "subscription_tier": 1, "plan_config": 1
    })

    if not user or not user.get("stripe_subscription_id"):
        return {
            "has_subscription": False,
            "tier": user.get("subscription_tier", "starter") if user else "starter",
            "status": "none"
        }

    if not stripe:
        return {
            "has_subscription": True,
            "tier": user.get("subscription_tier", "starter"),
            "status": "simulated",
            "simulated": True,
            "plan_config": user.get("plan_config")
        }

    try:
        subscription = stripe.Subscription.retrieve(user["stripe_subscription_id"])
        return {
            "has_subscription": True,
            "subscription_id": subscription.id,
            "status": subscription.status,
            "tier": user.get("subscription_tier", "custom"),
            "current_period_end": datetime.fromtimestamp(subscription.current_period_end, tz=timezone.utc).isoformat(),
            "cancel_at_period_end": subscription.cancel_at_period_end,
            "plan_config": user.get("plan_config")
        }
    except Exception as e:
        logger.error(f"Failed to get subscription status: {e}")
        return {"has_subscription": False, "error": str(e)}


# ============ CANCEL SUBSCRIPTION ============

async def cancel_stripe_subscription(user_id: str, at_period_end: bool = True) -> Dict[str, Any]:
    """Cancel a Stripe subscription."""

    user = await db.users.find_one({"user_id": user_id}, {"stripe_subscription_id": 1})

    if not user or not user.get("stripe_subscription_id"):
        return {"success": False, "error": "No active subscription found"}

    if not stripe:
        await db.users.update_one(
            {"user_id": user_id},
            {"$set": {"subscription_cancelled": True, "subscription_ends_at": datetime.now(timezone.utc).isoformat()}}
        )
        return {"success": True, "simulated": True, "message": "Subscription marked for cancellation (simulated)"}

    try:
        if at_period_end:
            subscription = stripe.Subscription.modify(
                user["stripe_subscription_id"],
                cancel_at_period_end=True
            )
            message = f"Subscription will be cancelled at period end: {datetime.fromtimestamp(subscription.current_period_end, tz=timezone.utc).isoformat()}"
        else:
            subscription = stripe.Subscription.delete(user["stripe_subscription_id"])
            message = "Subscription cancelled immediately"

        return {"success": True, "message": message, "status": subscription.status}
    except Exception as e:
        logger.error(f"Failed to cancel subscription: {e}")
        return {"success": False, "error": str(e)}


# ============ MODIFY SUBSCRIPTION ============

async def modify_subscription(user_id: str, monthly_credits: int, monthly_price_cents: int, plan_config: Dict[str, Any]) -> Dict[str, Any]:
    """Modify existing subscription to a new custom plan configuration."""
    user = await db.users.find_one({"user_id": user_id})
    if not user:
        return {"success": False, "error": "User not found"}

    subscription_id = user.get("stripe_subscription_id")
    if not subscription_id:
        return {"success": False, "error": "No active subscription to modify"}

    if not stripe:
        # Simulated mode — apply directly
        await _activate_custom_plan(user_id, monthly_credits, monthly_price_cents, plan_config)
        return {"success": True, "simulated": True, "monthly_credits": monthly_credits}

    try:
        subscription = stripe.Subscription.retrieve(subscription_id)

        # Look up an existing active Price with the same amount before creating
        # a new one. Creating a fresh Price on every modification leads to
        # unbounded Price objects in Stripe that accumulate over time.
        # TODO: improve further with an in-process price cache (dict keyed by
        #   (product_id, unit_amount)) to avoid a Stripe API round-trip per call.
        product_id = subscription["items"]["data"][0]["price"]["product"]
        existing_prices = stripe.Price.list(
            product=product_id,
            active=True,
            currency="usd",
            recurring={"interval": "month"},
            limit=100,
        )
        new_price = next(
            (
                p for p in existing_prices.auto_paging_iter()
                if p["unit_amount"] == monthly_price_cents
            ),
            None,
        )
        if new_price is None:
            new_price = stripe.Price.create(
                currency="usd",
                product=product_id,
                unit_amount=monthly_price_cents,
                recurring={"interval": "month"},
                metadata={
                    "user_id": user_id,
                    "type": "custom_plan",
                    "monthly_credits": str(monthly_credits),
                },
            )

        updated = stripe.Subscription.modify(
            subscription_id,
            items=[{
                "id": subscription["items"]["data"][0]["id"],
                "price": new_price.id,
            }],
            proration_behavior="create_prorations",
            metadata={
                "user_id": user_id,
                "type": "custom_plan",
                "monthly_credits": str(monthly_credits),
            },
        )

        await _activate_custom_plan(user_id, monthly_credits, monthly_price_cents, plan_config)

        return {"success": True, "subscription_id": updated.id, "monthly_credits": monthly_credits}
    except Exception as e:
        logger.error(f"Failed to modify subscription for user {user_id}: {e}")
        return {"success": False, "error": str(e)}


# ============ WEBHOOK HANDLING ============

async def handle_webhook_event(payload: bytes, sig_header: str) -> Dict[str, Any]:
    """Process Stripe webhook events."""

    if not stripe:
        return {"success": False, "error": "Stripe not configured"}

    if not STRIPE_WEBHOOK_SECRET:
        logger.warning("Stripe webhook secret not configured")
        return {"success": False, "error": "Webhook secret not configured"}

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
    except ValueError:
        return {"success": False, "error": "Invalid payload"}
    except stripe.error.SignatureVerificationError:
        return {"success": False, "error": "Invalid signature"}

    event_type = event["type"]
    event_data = event["data"]["object"]

    # Webhook idempotency guard — BILL-08
    # Race-safe: attempt insert first, catch DuplicateKeyError.
    # The stripe_events collection has a unique index on event_id.
    from pymongo.errors import DuplicateKeyError
    event_id = event["id"]
    try:
        await db.stripe_events.insert_one({
            "event_id": event_id,
            "event_type": event_type,
            "processed_at": datetime.now(timezone.utc)
        })
    except DuplicateKeyError:
        logger.info(f"Duplicate Stripe event {event_id} — skipping (concurrent dedup)")
        return {"success": True, "event_type": event_type, "duplicate": True}

    logger.info(f"Processing Stripe webhook: {event_type}")

    try:
        if event_type == "checkout.session.completed":
            await handle_checkout_completed(event_data)
        elif event_type == "customer.subscription.created":
            await handle_subscription_created(event_data)
        elif event_type == "customer.subscription.updated":
            await handle_subscription_updated(event_data)
        elif event_type == "customer.subscription.deleted":
            await handle_subscription_deleted(event_data)
        elif event_type == "invoice.payment_succeeded":
            await handle_payment_succeeded(event_data)
        elif event_type == "invoice.payment_failed":
            await handle_payment_failed(event_data)
        else:
            logger.info(f"Unhandled webhook event type: {event_type}")

        return {"success": True, "event_type": event_type}
    except Exception as e:
        logger.error(f"Error handling webhook {event_type}: {e}")
        return {"success": False, "error": str(e)}


async def handle_checkout_completed(session: Dict[str, Any]):
    """Handle successful checkout session."""
    user_id = session.get("metadata", {}).get("user_id")
    if not user_id:
        logger.error("Checkout completed without user_id in metadata")
        return

    checkout_type = session.get("metadata", {}).get("type", "")

    if checkout_type == "credit_purchase":
        credits = int(session.get("metadata", {}).get("credits", 0))
        if credits > 0:
            from services.credits import add_credits
            await add_credits(
                user_id=user_id,
                amount=credits,
                source="purchase",
                description=f"Purchased {credits} credits via Stripe"
            )
            logger.info(f"Added {credits} credits to user {user_id}")

            await db.payments.insert_one({
                "payment_id": f"pay_{uuid.uuid4().hex[:12]}",
                "user_id": user_id,
                "stripe_invoice_id": session.get("invoice") or session.get("id"),
                "amount_cents": session.get("amount_total", 0),
                "currency": session.get("currency", "usd"),
                "tier": "credits",
                "credits_granted": credits,
                "status": "succeeded",
                "created_at": datetime.now(timezone.utc),
            })

    elif checkout_type == "custom_plan":
        # Custom plan subscription — activate from pending config
        user = await db.users.find_one({"user_id": user_id}, {"pending_plan_config": 1})
        if user and user.get("pending_plan_config"):
            monthly_credits = int(session.get("metadata", {}).get("monthly_credits", 500))
            monthly_price_cents = int(session.get("metadata", {}).get("monthly_price_cents", 0))
            await _activate_custom_plan(user_id, monthly_credits, monthly_price_cents, user["pending_plan_config"])
        logger.info(f"Custom plan checkout completed for user {user_id}")
    else:
        logger.info(f"Subscription checkout completed for user {user_id} — payment will be recorded via invoice.payment_succeeded")


async def handle_subscription_created(subscription: Dict[str, Any]):
    """Handle new subscription creation."""
    user_id = subscription.get("metadata", {}).get("user_id")

    if not user_id:
        customer_id = subscription.get("customer")
        user = await db.users.find_one({"stripe_customer_id": customer_id})
        if user:
            user_id = user["user_id"]
        else:
            logger.error(f"Could not find user for subscription {subscription['id']}")
            return

    sub_type = subscription.get("metadata", {}).get("type", "")
    monthly_credits = int(subscription.get("metadata", {}).get("monthly_credits", 500))

    now = datetime.now(timezone.utc)
    update = {
        "stripe_subscription_id": subscription["id"],
        "subscription_status": subscription["status"],
        "subscription_updated_at": now,
    }

    if sub_type == "custom_plan":
        update["subscription_tier"] = "custom"
        update["credits"] = monthly_credits
        update["credit_allowance"] = monthly_credits
    else:
        update["subscription_tier"] = "custom"
        update["credits"] = monthly_credits
        update["credit_allowance"] = monthly_credits

    await db.users.update_one({"user_id": user_id}, {"$set": update})
    logger.info(f"User {user_id} subscribed: {monthly_credits} credits/mo")


async def handle_subscription_updated(subscription: Dict[str, Any]):
    """Handle subscription updates (plan changes, renewals)."""
    user_id = subscription.get("metadata", {}).get("user_id")

    if not user_id:
        customer_id = subscription.get("customer")
        user = await db.users.find_one({"stripe_customer_id": customer_id})
        if user:
            user_id = user["user_id"]
        else:
            return

    status = subscription.get("status")

    update_data = {
        "subscription_status": status,
        "subscription_updated_at": datetime.now(timezone.utc)
    }

    if status == "active":
        monthly_credits = int(subscription.get("metadata", {}).get("monthly_credits", 500))
        update_data["credit_allowance"] = monthly_credits

    await db.users.update_one({"user_id": user_id}, {"$set": update_data})
    logger.info(f"Subscription updated for user {user_id}: status={status}")


async def handle_subscription_deleted(subscription: Dict[str, Any]):
    """Handle subscription cancellation — downgrade to starter."""
    customer_id = subscription.get("customer")
    user = await db.users.find_one({"stripe_customer_id": customer_id})

    if not user:
        return

    await db.users.update_one(
        {"user_id": user["user_id"]},
        {"$set": {
            "subscription_tier": "starter",
            "subscription_status": "cancelled",
            "stripe_subscription_id": None,
            "plan_config": None,
            "credit_allowance": 0,
            "subscription_updated_at": datetime.now(timezone.utc)
        }}
    )
    logger.info(f"Subscription deleted for user {user['user_id']}, downgraded to starter")


async def handle_payment_succeeded(invoice: Dict[str, Any]):
    """Handle successful recurring payment — refresh credits."""
    subscription_id = invoice.get("subscription")
    if not subscription_id:
        return

    user = await db.users.find_one({"stripe_subscription_id": subscription_id})
    if not user:
        return

    monthly_credits = user.get("credit_allowance", 500)

    await db.users.update_one(
        {"user_id": user["user_id"]},
        {"$set": {
            "credits": monthly_credits,
            "credits_last_refresh": datetime.now(timezone.utc),
            "last_payment_at": datetime.now(timezone.utc)
        }}
    )

    await db.payments.insert_one({
        "payment_id": f"pay_{uuid.uuid4().hex[:12]}",
        "user_id": user["user_id"],
        "stripe_invoice_id": invoice.get("id"),
        "amount_cents": invoice.get("amount_paid", 0),
        "currency": invoice.get("currency", "usd"),
        "tier": user.get("subscription_tier", "custom"),
        "credits_granted": monthly_credits,
        "status": "succeeded",
        "created_at": datetime.now(timezone.utc),
    })

    logger.info(f"Payment succeeded for user {user['user_id']}, credits reset to {monthly_credits}")


async def handle_payment_failed(invoice: Dict[str, Any]):
    """Handle failed payment."""
    subscription_id = invoice.get("subscription")
    if not subscription_id:
        return

    user = await db.users.find_one({"stripe_subscription_id": subscription_id})
    if not user:
        return

    await db.users.update_one(
        {"user_id": user["user_id"]},
        {"$set": {
            "payment_failed_at": datetime.now(timezone.utc),
            "subscription_status": "past_due"
        }}
    )
    logger.warning(f"Payment failed for user {user['user_id']}")


# ============ CUSTOMER PORTAL ============

async def create_customer_portal_session(user_id: str, return_url: str = None) -> Dict[str, Any]:
    """Create a Stripe Customer Portal session for self-service billing management."""

    user = await db.users.find_one({"user_id": user_id}, {"stripe_customer_id": 1})

    if not user or not user.get("stripe_customer_id"):
        return {"success": False, "error": "No billing account found"}

    if not stripe:
        return {
            "success": True,
            "simulated": True,
            "portal_url": "/settings",
            "message": "Stripe not configured. Customer portal simulated."
        }

    try:
        session = stripe.billing_portal.Session.create(
            customer=user["stripe_customer_id"],
            return_url=return_url or f"{settings.app.frontend_url}/settings"
        )
        return {"success": True, "portal_url": session.url}
    except Exception as e:
        logger.error(f"Failed to create portal session: {e}")
        return {"success": False, "error": str(e)}


# ============ UTILITY FUNCTIONS ============

def get_stripe_config() -> Dict[str, Any]:
    """Get Stripe configuration for frontend."""
    from services.credits import VOLUME_TIERS, FEATURE_THRESHOLDS, CreditOperation

    return {
        "configured": is_stripe_configured(),
        "publishable_key": STRIPE_PUBLISHABLE_KEY if is_stripe_configured() else None,
        "pricing_model": "custom_plan_builder",
        "volume_tiers": VOLUME_TIERS,
        "feature_thresholds": {
            k: {"min_monthly_usd": v["min_monthly_usd"]}
            for k, v in FEATURE_THRESHOLDS.items()
        },
        "operation_costs": {op.name.lower(): op.value for op in CreditOperation},
        "credit_packages": {
            name: {"credits": pkg["credits"], "price": pkg["price"] / 100}
            for name, pkg in CREDIT_PACKAGES.items()
        }
    }
