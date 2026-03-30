"""
Stripe Payment Integration for ThookAI

Handles:
- Subscription creation and management
- One-time credit purchases
- Webhooks for payment events
- Customer management
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from database import db
from config import settings

logger = logging.getLogger(__name__)

# Stripe API keys from config
STRIPE_SECRET_KEY = settings.stripe.secret_key or ''
STRIPE_WEBHOOK_SECRET = settings.stripe.webhook_secret or ''
STRIPE_PUBLISHABLE_KEY = settings.stripe.publishable_key or ''

# Check if Stripe is configured


def is_stripe_configured() -> bool:
    """Check if Stripe is properly configured."""
    return bool(STRIPE_SECRET_KEY and not STRIPE_SECRET_KEY.startswith('placeholder'))


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


# ============ PRICE CONFIGURATION ============

# Stripe Price IDs - Create these in your Stripe Dashboard
# Format: price_xxxxxxxxxxxxxxxxxx
PRICE_IDS = {
    "pro_monthly": settings.stripe.price_pro_monthly or '',
    "pro_annual": settings.stripe.price_pro_annual or '',
    "studio_monthly": settings.stripe.price_studio_monthly or '',
    "studio_annual": settings.stripe.price_studio_annual or '',
    "agency_monthly": settings.stripe.price_agency_monthly or '',
    "agency_annual": settings.stripe.price_agency_annual or '',
}

# Credit package prices (one-time)
CREDIT_PACKAGES = {
    "small": {"credits": 100, "price": 1000, "stripe_price": settings.stripe.price_credits_100 or ''},
    "medium": {"credits": 500, "price": 4500, "stripe_price": settings.stripe.price_credits_500 or ''},
    "large": {"credits": 1000, "price": 8000, "stripe_price": settings.stripe.price_credits_1000 or ''},
}

# Tier pricing in cents
TIER_PRICING = {
    "free": {"monthly": 0, "annual": 0, "credits": 50},
    "pro": {"monthly": 1900, "annual": 19000, "credits": 500},  # Early bird: $19/mo
    "studio": {"monthly": 4900, "annual": 49000, "credits": 2000},  # Early bird: $49/mo
    "agency": {"monthly": 12900, "annual": 129000, "credits": 10000},  # Early bird: $129/mo
}


# ============ CUSTOMER MANAGEMENT ============

async def get_or_create_stripe_customer(user_id: str, email: str, name: str = None) -> Dict[str, Any]:
    """Get existing Stripe customer or create new one."""
    
    # Check if user already has a Stripe customer ID
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
            
            # Save customer ID to user
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


# ============ SUBSCRIPTION MANAGEMENT ============

async def create_checkout_session(
    user_id: str,
    email: str,
    tier: str,
    billing_period: str = "monthly",
    success_url: str = None,
    cancel_url: str = None
) -> Dict[str, Any]:
    """Create a Stripe Checkout session for subscription."""
    
    if tier == "free":
        return {"success": False, "error": "Cannot checkout for free tier"}
    
    price_key = f"{tier}_{billing_period}"
    price_id = PRICE_IDS.get(price_key)
    
    if not stripe:
        # Simulated mode - return mock session
        return {
            "success": True,
            "simulated": True,
            "checkout_url": f"/billing/simulate-success?tier={tier}&period={billing_period}",
            "session_id": f"cs_simulated_{user_id[:8]}_{tier}",
            "message": "Stripe not configured. Using simulated checkout."
        }
    
    if not price_id:
        return {
            "success": False, 
            "error": f"Price ID not configured for {price_key}. Set STRIPE_PRICE_{tier.upper()}_{billing_period.upper()} in .env"
        }
    
    try:
        # Get or create customer
        customer_result = await get_or_create_stripe_customer(user_id, email)
        if not customer_result.get("success"):
            return customer_result
        
        # Create checkout session
        session = stripe.checkout.Session.create(
            customer=customer_result["customer_id"],
            payment_method_types=["card"],
            line_items=[{"price": price_id, "quantity": 1}],
            mode="subscription",
            success_url=success_url or f"{settings.app.frontend_url}/dashboard?subscription=success",
            cancel_url=cancel_url or f"{settings.app.frontend_url}/settings?subscription=cancelled",
            metadata={
                "user_id": user_id,
                "tier": tier,
                "billing_period": billing_period
            },
            subscription_data={
                "metadata": {
                    "user_id": user_id,
                    "tier": tier
                }
            }
        )
        
        return {
            "success": True,
            "checkout_url": session.url,
            "session_id": session.id
        }
    except Exception as e:
        logger.error(f"Failed to create checkout session: {e}")
        return {"success": False, "error": str(e)}


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
        # Simulated mode
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
        
        # Create one-time payment session
        if pkg.get("stripe_price"):
            line_items = [{"price": pkg["stripe_price"], "quantity": 1}]
        else:
            # Dynamic pricing
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


async def get_subscription_status(user_id: str) -> Dict[str, Any]:
    """Get current subscription status from Stripe."""
    
    user = await db.users.find_one({"user_id": user_id}, {"stripe_customer_id": 1, "stripe_subscription_id": 1})
    
    if not user or not user.get("stripe_subscription_id"):
        return {
            "has_subscription": False,
            "tier": "free",
            "status": "none"
        }
    
    if not stripe:
        return {
            "has_subscription": True,
            "tier": user.get("subscription_tier", "free"),
            "status": "simulated",
            "simulated": True
        }
    
    try:
        subscription = stripe.Subscription.retrieve(user["stripe_subscription_id"])
        return {
            "has_subscription": True,
            "subscription_id": subscription.id,
            "status": subscription.status,
            "tier": subscription.metadata.get("tier", "pro"),
            "current_period_end": datetime.fromtimestamp(subscription.current_period_end, tz=timezone.utc).isoformat(),
            "cancel_at_period_end": subscription.cancel_at_period_end
        }
    except Exception as e:
        logger.error(f"Failed to get subscription status: {e}")
        return {"has_subscription": False, "error": str(e)}


async def cancel_stripe_subscription(user_id: str, at_period_end: bool = True) -> Dict[str, Any]:
    """Cancel a Stripe subscription."""
    
    user = await db.users.find_one({"user_id": user_id}, {"stripe_subscription_id": 1})
    
    if not user or not user.get("stripe_subscription_id"):
        return {"success": False, "error": "No active subscription found"}
    
    if not stripe:
        # Simulated cancellation
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
            message = f"Subscription will be cancelled at period end: {datetime.fromtimestamp(subscription.current_period_end).isoformat()}"
        else:
            subscription = stripe.Subscription.delete(user["stripe_subscription_id"])
            message = "Subscription cancelled immediately"
        
        return {"success": True, "message": message, "status": subscription.status}
    except Exception as e:
        logger.error(f"Failed to cancel subscription: {e}")
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
    
    # Handle specific events
    event_type = event["type"]
    event_data = event["data"]["object"]
    
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
    
    # Check if this is a credit purchase
    if session.get("metadata", {}).get("type") == "credit_purchase":
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
    else:
        # Subscription checkout - subscription.created event will handle tier update
        logger.info(f"Subscription checkout completed for user {user_id}")


async def handle_subscription_created(subscription: Dict[str, Any]):
    """Handle new subscription creation."""
    user_id = subscription.get("metadata", {}).get("user_id")
    tier = subscription.get("metadata", {}).get("tier", "pro")
    
    if not user_id:
        # Try to find user by customer ID
        customer_id = subscription.get("customer")
        user = await db.users.find_one({"stripe_customer_id": customer_id})
        if user:
            user_id = user["user_id"]
        else:
            logger.error(f"Could not find user for subscription {subscription['id']}")
            return
    
    # Update user subscription
    credits = TIER_PRICING.get(tier, {}).get("credits", 500)
    await db.users.update_one(
        {"user_id": user_id},
        {"$set": {
            "subscription_tier": tier,
            "stripe_subscription_id": subscription["id"],
            "subscription_status": subscription["status"],
            "credits": credits,
            "credit_allowance": credits,
            "subscription_updated_at": datetime.now(timezone.utc)
        }}
    )
    logger.info(f"User {user_id} subscribed to {tier} tier with {credits} credits")


async def handle_subscription_updated(subscription: Dict[str, Any]):
    """Handle subscription updates (upgrades, downgrades, renewals)."""
    user_id = subscription.get("metadata", {}).get("user_id")
    
    if not user_id:
        customer_id = subscription.get("customer")
        user = await db.users.find_one({"stripe_customer_id": customer_id})
        if user:
            user_id = user["user_id"]
        else:
            return
    
    tier = subscription.get("metadata", {}).get("tier", "pro")
    status = subscription.get("status")
    
    update_data = {
        "subscription_status": status,
        "subscription_updated_at": datetime.now(timezone.utc)
    }
    
    if status == "active":
        update_data["subscription_tier"] = tier
    
    await db.users.update_one({"user_id": user_id}, {"$set": update_data})
    logger.info(f"Subscription updated for user {user_id}: status={status}, tier={tier}")


async def handle_subscription_deleted(subscription: Dict[str, Any]):
    """Handle subscription cancellation."""
    customer_id = subscription.get("customer")
    user = await db.users.find_one({"stripe_customer_id": customer_id})
    
    if not user:
        return
    
    # Downgrade to free tier
    await db.users.update_one(
        {"user_id": user["user_id"]},
        {"$set": {
            "subscription_tier": "free",
            "subscription_status": "cancelled",
            "stripe_subscription_id": None,
            "credit_allowance": 50,  # Free tier credits
            "subscription_updated_at": datetime.now(timezone.utc)
        }}
    )
    logger.info(f"Subscription deleted for user {user['user_id']}, downgraded to free")


async def handle_payment_succeeded(invoice: Dict[str, Any]):
    """Handle successful recurring payment."""
    subscription_id = invoice.get("subscription")
    if not subscription_id:
        return
    
    user = await db.users.find_one({"stripe_subscription_id": subscription_id})
    if not user:
        return
    
    # Refresh credits on successful payment
    tier = user.get("subscription_tier", "free")
    credits = TIER_PRICING.get(tier, {}).get("credits", 50)
    
    await db.users.update_one(
        {"user_id": user["user_id"]},
        {"$set": {
            "credits": credits,
            "last_payment_at": datetime.now(timezone.utc)
        }}
    )
    logger.info(f"Payment succeeded for user {user['user_id']}, credits reset to {credits}")


async def handle_payment_failed(invoice: Dict[str, Any]):
    """Handle failed payment."""
    subscription_id = invoice.get("subscription")
    if not subscription_id:
        return
    
    user = await db.users.find_one({"stripe_subscription_id": subscription_id})
    if not user:
        return
    
    # Mark payment as failed - could trigger email notification
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
    return {
        "configured": is_stripe_configured(),
        "publishable_key": STRIPE_PUBLISHABLE_KEY if is_stripe_configured() else None,
        "prices": {
            "pro": TIER_PRICING["pro"],
            "studio": TIER_PRICING["studio"],
            "agency": TIER_PRICING["agency"]
        },
        "credit_packages": {
            name: {"credits": pkg["credits"], "price": pkg["price"] / 100}
            for name, pkg in CREDIT_PACKAGES.items()
        }
    }
