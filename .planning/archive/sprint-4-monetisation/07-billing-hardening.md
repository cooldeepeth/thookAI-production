# Agent: Billing Hardening — Stripe Guards + Simulation Lockdown
Sprint: 4 | Branch: fix/billing-hardening | PR target: dev
Depends on: Sprint 3 fully merged
⚠️  FLAG THIS PR FOR OWNER REVIEW — do not merge without owner approval

## Context
Stripe checkout will fail in production because all STRIPE_PRICE_* env vars are blank.
The webhook handler silently accepts unverified webhooks if STRIPE_WEBHOOK_SECRET is missing.
The /simulate/upgrade endpoint can be called by anyone if is_production flag is False.

## Files You Will Touch
- backend/services/stripe_service.py    (MODIFY)
- backend/routes/billing.py            (MODIFY)
- backend/server.py                    (MODIFY — startup Stripe config check)
- backend/config.py                    (MODIFY — add Stripe config dataclass)

## Files You Must Read First (do not modify)
- backend/routes/billing.py            (read fully)
- backend/services/stripe_service.py   (read fully)
- backend/.env.example                 (all STRIPE_PRICE_* vars listed)

## Step 1: Add StripeConfig dataclass to config.py
```python
@dataclass
class StripeConfig:
    secret_key: Optional[str] = field(default_factory=lambda: os.environ.get('STRIPE_SECRET_KEY'))
    publishable_key: Optional[str] = field(default_factory=lambda: os.environ.get('STRIPE_PUBLISHABLE_KEY'))
    webhook_secret: Optional[str] = field(default_factory=lambda: os.environ.get('STRIPE_WEBHOOK_SECRET'))
    price_pro_monthly: Optional[str] = field(default_factory=lambda: os.environ.get('STRIPE_PRICE_PRO_MONTHLY'))
    price_pro_annual: Optional[str] = field(default_factory=lambda: os.environ.get('STRIPE_PRICE_PRO_ANNUAL'))
    price_studio_monthly: Optional[str] = field(default_factory=lambda: os.environ.get('STRIPE_PRICE_STUDIO_MONTHLY'))
    price_studio_annual: Optional[str] = field(default_factory=lambda: os.environ.get('STRIPE_PRICE_STUDIO_ANNUAL'))
    price_agency_monthly: Optional[str] = field(default_factory=lambda: os.environ.get('STRIPE_PRICE_AGENCY_MONTHLY'))
    price_agency_annual: Optional[str] = field(default_factory=lambda: os.environ.get('STRIPE_PRICE_AGENCY_ANNUAL'))
    price_credits_100: Optional[str] = field(default_factory=lambda: os.environ.get('STRIPE_PRICE_CREDITS_100'))
    price_credits_500: Optional[str] = field(default_factory=lambda: os.environ.get('STRIPE_PRICE_CREDITS_500'))
    price_credits_1000: Optional[str] = field(default_factory=lambda: os.environ.get('STRIPE_PRICE_CREDITS_1000'))
    
    def all_price_ids_configured(self) -> bool:
        return all([
            self.price_pro_monthly, self.price_pro_annual,
            self.price_studio_monthly, self.price_studio_annual,
            self.price_agency_monthly, self.price_agency_annual
        ])
    
    def is_fully_configured(self) -> bool:
        return bool(self.secret_key and self.webhook_secret and self.all_price_ids_configured())
```
Add `stripe: StripeConfig = field(default_factory=StripeConfig)` to Settings.

## Step 2: Add Stripe startup check in server.py
In the lifespan startup section:
```python
if settings.app.is_production:
    if not settings.stripe.is_fully_configured():
        logger.error(
            "CRITICAL: Stripe is not fully configured for production! "
            "Billing features will fail. Check STRIPE_SECRET_KEY, "
            "STRIPE_WEBHOOK_SECRET, and all STRIPE_PRICE_* env vars."
        )
    else:
        logger.info("✓ Stripe billing configured")
```

## Step 3: Guard simulate endpoints strictly
In billing.py, find the /simulate/upgrade and /simulate/credits endpoints.
Change the guard from `if settings.app.is_production` to:
```python
if settings.app.environment not in ("development", "test"):
    raise HTTPException(status_code=403, detail="Simulation endpoints disabled outside development")
```
Also add rate limiting comment: `# DO NOT expose in staging or production`

## Step 4: Harden webhook signature verification
In the webhook handler in billing.py, find where Stripe signature is verified.
If `settings.stripe.webhook_secret` is None:
- In production: raise HTTP 500 with "Webhook secret not configured"
- In development: log a WARNING and skip verification (allow for local testing)

## Step 5: Add Stripe config to health endpoint
```python
health_status["checks"]["billing"] = "configured" if settings.stripe.is_fully_configured() else "not_configured"
```

## Definition of Done
- Production startup logs ERROR if any STRIPE_PRICE_* vars are missing
- Simulate endpoints return 403 in any non-development environment
- Webhook handler explicitly rejects calls if webhook_secret is None in production
- PR created to dev with title: "fix: harden Stripe billing config guards and webhook verification"
- ⚠️ PR marked as draft — owner must review before merging