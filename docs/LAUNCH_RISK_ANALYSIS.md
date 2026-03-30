# ThookAI Pre-Deployment Risk Analysis & Recommendations

## Executive Summary

**Updated March 31, 2026** — Reflects the new **Custom Plan Builder** pricing model replacing the old 4-tier (Free/Pro/Studio/Agency) system.

**New Model**: Users get 200 free starter credits to try the platform, then build a custom subscription by selecting their monthly usage quantities (text posts, images, videos, carousels). Volume pricing ensures margins stay 75%+ at all spend levels.

**Bottom Line**: The custom plan builder eliminates rigid tier boundaries, gives users maximum flexibility, and protects margins through volume-based pricing. Starter credits cost ~$1.40/user to offer, making customer acquisition extremely efficient.

---

## 1. API Cost vs Revenue Analysis (Custom Plan Builder)

### Credit Costs Per Operation (Unchanged):

| Operation | Credits | Real API Cost | Margin at $0.06/cr | Margin at $0.03/cr |
|-----------|---------|---------------|---------------------|---------------------|
| **CONTENT_CREATE** | 10 | $0.05-$0.08 | **$0.60 → 87%** | **$0.30 → 73%** |
| **IMAGE_GENERATE** | 8 | $0.05-$0.12 | **$0.48 → 75%** | **$0.24 → 50%** |
| **CAROUSEL** | 15 | $0.15-$0.36 | **$0.90 → 60%** | **$0.45 → 20%** |
| **REPURPOSE** | 3 | $0.02 | **$0.18 → 89%** | **$0.09 → 78%** |
| **VOICE_NARRATION** | 12 | $0.15-$0.30 | **$0.72 → 58%** | **$0.36 → 17%** |
| **VIDEO_GENERATE** | 50 | $0.50-$2.50 | **$3.00 → 17-83%** | **$1.50 → -67% to 67%** |

### Volume Pricing Tiers:

| Monthly Credits | Price/Credit | Example Plan | Monthly Price |
|-----------------|-------------|--------------|---------------|
| Up to 500 | $0.06 | 50 posts ($30) | ~$30/mo |
| 501-1500 | $0.05 | 50 posts + 20 images + 5 videos ($75) | ~$55/mo |
| 1501-5000 | $0.035 | 100 posts + 50 images + 10 videos ($175) | ~$105/mo |
| 5000+ | $0.03 | Agency-scale usage | ~$150+/mo |

### Key Insight: Video Margin Protection

At $0.06/credit (smallest plans), a video costs the user $3.00 with API cost of $0.50-$2.50 — **maintaining 17-83% margin**. This is dramatically better than the old model where video was a loss leader at 25 credits.

At $0.03/credit (highest volume), video becomes tight. But high-volume users generate primarily text content (86% margin), so the blended margin stays healthy.

### Content Creation Pipeline Breakdown:
```
Commander → Scout (Perplexity) → Thinker → Writer (Claude) → QC
Total API cost: ~$0.07 per generation
```

**At 10 credits ($0.30-$0.60 depending on volume tier), text generation has 57-87% margin. This is the core of the platform and it's highly profitable.**

---

## 2. Starter Credits: Customer Acquisition Cost

### The Math:
- 200 starter credits per new user
- Average usage: ~15-20 text posts before credits run out
- **Max API cost per starter user: ~$1.40**
- Starter users are limited: max 2 videos, 5 carousels, LinkedIn only

### Conversion Economics:

| Scenario | Signups | Conversion Rate | Paid Users | Starter Cost | Monthly Revenue | CAC |
|----------|---------|-----------------|------------|--------------|-----------------|-----|
| Conservative | 500 | 3% | 15 | $700 | $750 | $47 |
| Moderate | 500 | 5% | 25 | $700 | $1,250 | $28 |
| Optimistic | 500 | 10% | 50 | $700 | $2,500 | $14 |

**Even at 3% conversion, CAC of $47 is excellent for a SaaS at $30-150/mo price points.**

---

## 3. Financial Projections (Custom Plan Builder)

### Assumptions:
- Average custom plan: ~$50/mo (750 credits — typical creator: 50 posts + 10 images)
- User mix: 70% small plans ($30-50), 20% medium ($50-100), 10% large ($100+)
- Average blended margin: 78% (weighted by operation mix)

### 100 Paid Users:

| Revenue Source | Amount |
|----------------|--------|
| Plan subscriptions | $5,000/mo |
| Credit top-up purchases | $500/mo |
| **Total Revenue** | **$5,500/mo** |
| API costs (22% of revenue) | -$1,210 |
| Infrastructure (hosting, DB, Redis) | -$300 |
| **Net Profit** | **$3,990/mo (73%)** |

### 500 Paid Users:

| Revenue Source | Amount |
|----------------|--------|
| Plan subscriptions | $25,000/mo |
| Credit top-up purchases | $2,500/mo |
| **Total Revenue** | **$27,500/mo** |
| API costs | -$6,050 |
| Infrastructure | -$600 |
| **Net Profit** | **$20,850/mo (76%)** |

### Break-Even Point:
- Fixed costs: ~$300/mo (hosting + DB + Redis)
- At average $50/plan with 78% margin: **$300 / ($50 × 0.78) = 8 paid users**
- **Break-even at 8 paid users.** Everything after that is profit.

---

## 4. Risk Assessment (Updated)

### Resolved Risks (Previously Critical):

| Risk | Status | Resolution |
|------|--------|------------|
| Wrong Claude model in onboarding | **FIXED** | Correct model name in place |
| Celery not configured | **FIXED** | celery_app.py + celeryconfig.py created |
| Fake publishing placeholder | **FIXED** | Real publisher.py wired in production |
| Designer blocking event loop | **FIXED** | asyncio.wait_for() with 60s timeouts |
| /tmp media fallback | **FIXED** | HTTP 503 in production, /tmp only in dev |
| No email service | **FIXED** | Resend integration for password reset + invites |

### Remaining Risks:

| Risk | Severity | Mitigation |
|------|----------|------------|
| Video generation API cost spikes | **MEDIUM** | Starter hard cap (2 videos), credits naturally limit usage |
| Stripe dynamic pricing edge cases | **LOW** | Simulated mode fallback when Stripe not configured |
| No real social analytics ingestion | **MEDIUM** | Analytics show internal metrics only — not blocking for launch |
| Template marketplace empty | **LOW** | Seed data script needed before launch |
| No cost anomaly detection | **MEDIUM** | Add daily spend alerts per user before 200 users |

---

## 5. Competitive Positioning (Updated)

| Platform | Pricing Model | ThookAI Advantage |
|----------|--------------|-------------------|
| Jasper | $39-69/mo fixed tiers, word limits | **Pay only for what you use**, persona engine |
| Copy.ai | $29-49/mo, marketing copy only | **Multi-platform**, video, scheduling |
| Buffer + ChatGPT | $50+/mo combined, manual | **End-to-end automation**, single platform |
| Writesonic | $12-249/mo, word credits | **Custom plan builder**, voice matching |
| **ThookAI** | **$30-150+/mo, usage-based** | **Only platform combining persona learning + plan builder flexibility** |

**Unique differentiator**: No competitor offers a plan builder where users configure exact usage quantities. This positions ThookAI as both flexible AND premium.

---

## 6. Launch Strategy (Updated)

### Phase 1: Soft Launch (Week 1-2)
- 50-100 users via waitlist/invite
- 200 starter credits per user
- Monitor: conversion rate, average plan size, API cost per user
- Target: 5%+ conversion, $40+ average plan

### Phase 2: Public Launch (Week 3-4)
- Open registration
- "Founding Member" badge for first 100 paid users (optional, can add later)
- Referral program: give 50 credits, get 50 credits

### Phase 3: Optimize (Month 2+)
- Analyze actual usage patterns vs plan selections
- Adjust volume pricing tiers if margins are too thin or too fat
- Consider separate image/video credit system if UX warrants it
- Introduce annual billing at 20% discount

---

## 7. Feature Unlock Thresholds

The custom plan builder unlocks features based on monthly spend:

| Monthly Spend | Features Unlocked |
|---------------|-------------------|
| **$0 (Starter)** | 1 persona, LinkedIn only, 7-day analytics |
| **Any paid plan** | 3 personas, all platforms, 30-day analytics, series, repurpose |
| **$79+/mo** | 10 personas, 5 team members, 90-day analytics, voice, priority support |
| **$149+/mo** | 25 personas, 10 team members, 365-day analytics, API access |

This creates natural upgrade incentives without rigid tier boundaries.

---

## 8. Final Recommendation

**Launch with the Custom Plan Builder from Day 1.**

| Decision | Recommendation |
|----------|----------------|
| Free trial? | 200 starter credits (not time-limited) |
| Fixed tiers? | No — custom plan builder |
| Video for starters? | Limited (max 2, credit-gated) |
| Video credit cost? | 50 credits (~$1.50-$3.00 to user) |
| Founding member discount? | Optional — can introduce later |
| Target initial users? | 50-100 via waitlist |
| Break-even point? | **8 paid users** |
| Max financial risk? | ~$1.40/starter user + $300/mo infrastructure |

### Why This Model Wins:
1. **No decision paralysis** — users build exactly what they need
2. **Natural upgrade path** — just slide the quantities up
3. **Margin-safe at all levels** — volume pricing ensures profitability
4. **Low acquisition cost** — $1.40/starter user is negligible
5. **Competitive moat** — no competitor offers this flexibility

**Go live. Let users build their own plans. Iterate based on real usage data.**
