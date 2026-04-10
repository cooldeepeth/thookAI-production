# Backend API Audit — Phase 1

**Date:** 2026-04-11
**Tested against:** https://gallant-intuition-production-698a.up.railway.app
**Total endpoints tested:** 70
**Pass:** 67 | **Fail:** 3 (all fixed)

## Endpoint Registry

### Auth (auth.py, auth_google.py, auth_social.py, password_reset.py)
| Method | Path | Status | Auth | Notes |
|--------|------|--------|------|-------|
| POST | /api/auth/register | 200 | Public | Password policy enforced |
| POST | /api/auth/login | 200 | Public | Account lockout after 5 attempts |
| GET | /api/auth/me | 200 | JWT | Returns user profile |
| POST | /api/auth/logout | 200 | Cookie | Clears session |
| GET | /api/auth/csrf-token | 200 | JWT | Fresh CSRF token |
| POST | /api/auth/forgot-password | 200 | Public | Generic response (security) |
| POST | /api/auth/reset-password | 400 | Public | Validates token + password policy |
| GET | /api/auth/google | 302 | Public | Redirects to Google OAuth |
| GET | /api/auth/google/callback | 302 | Public | OAuth callback |
| GET | /api/auth/linkedin | 302 | Public | LinkedIn OAuth init |
| GET | /api/auth/x | 302 | Public | X/Twitter OAuth init |
| GET | /api/auth/social/providers | 200 | Public | Google: true, LinkedIn/X: false |
| GET | /api/auth/export | 200 | JWT | GDPR data export |
| POST | /api/auth/delete-account | 200 | JWT | GDPR account deletion |

### Onboarding (onboarding.py)
| Method | Path | Status | Auth | Notes |
|--------|------|--------|------|-------|
| GET | /api/onboarding/questions | 200 | Public | 7 questions |
| POST | /api/onboarding/analyze-posts | 200 | JWT | Post analysis |
| POST | /api/onboarding/generate-persona | 200 | JWT | Persona generation |
| POST | /api/onboarding/import-history | 200 | JWT | Bulk post import |

### Persona (persona.py)
| Method | Path | Status | Auth | Notes |
|--------|------|--------|------|-------|
| GET | /api/persona/me | 200 | JWT | Full persona |
| PUT | /api/persona/me | 200 | JWT | Update persona (HTML stripped) |
| DELETE | /api/persona/me | 200 | JWT | Reset persona |
| POST | /api/persona/share | 200 | JWT | Generate share link |
| GET | /api/persona/share/status | 200 | JWT | Share status |
| DELETE | /api/persona/share | 200 | JWT | Revoke share |
| GET | /api/persona/public/{token} | 200 | Public | Public persona card |
| GET | /api/persona/regional-english/options | 200 | Public | **FIXED: was returning empty body** |
| PUT | /api/persona/regional-english | 200 | JWT | Update regional preference |
| GET | /api/persona/avatar | 200 | JWT | Avatar status |
| GET | /api/persona/voice-clone | 200 | JWT | Voice clone status |

### Content (content.py)
| Method | Path | Status | Auth | Notes |
|--------|------|--------|------|-------|
| POST | /api/content/create | 200 | JWT | Creates pipeline job (10 credits) |
| GET | /api/content/job/{id} | 200 | JWT | Job status + all agent outputs |
| PATCH | /api/content/job/{id}/status | 200 | JWT | Approve/reject |
| GET | /api/content/jobs | 200 | JWT | List user's jobs |
| GET | /api/content/platform-types | 200 | Public | LinkedIn/X/Instagram types |
| GET | /api/content/image-styles | 200 | Public | Available styles |
| GET | /api/content/providers | 200 | Public | All media providers |
| GET | /api/content/voices | 200 | JWT | Available voices |
| GET | /api/content/job/{id}/export | 200 | JWT | Export as text/json |

### Dashboard (dashboard.py)
| Method | Path | Status | Auth | Notes |
|--------|------|--------|------|-------|
| GET | /api/dashboard/stats | 200 | JWT | Dashboard stats |
| GET | /api/dashboard/activity | 200 | JWT | Recent activity |
| GET | /api/dashboard/learning-insights | 200 | JWT | Learning data |
| GET | /api/dashboard/daily-brief/status | 200 | JWT | Brief availability |
| POST | /api/dashboard/feedback | 200 | JWT | User feedback (Pydantic validated) |
| GET | /api/dashboard/schedule/upcoming | 200 | JWT | Upcoming posts |
| GET | /api/dashboard/schedule/weekly | 200 | JWT | **FIXED: added 12s timeout** |
| GET | /api/dashboard/schedule/optimal-times | 422 | JWT | Needs platform param |
| POST | /api/dashboard/publish/{id} | 200 | JWT | Publish content |

### Billing (billing.py)
| Method | Path | Status | Auth | Notes |
|--------|------|--------|------|-------|
| GET | /api/billing/config | 200 | Public | Stripe config |
| POST | /api/billing/plan/preview | 200 | Public | Plan pricing (capped at 500/operation) |
| POST | /api/billing/plan/checkout | 200 | JWT | Stripe checkout |
| GET | /api/billing/credits | 200 | JWT | Credit balance |
| GET | /api/billing/credits/usage | 200 | JWT | Usage history |
| GET | /api/billing/credits/costs | 200 | Public | Operation costs |
| GET | /api/billing/subscription | 200 | JWT | Subscription status |
| GET | /api/billing/subscription/limits | 200 | JWT | Feature limits |
| GET | /api/billing/subscription/daily-limit | 200 | JWT | Daily cap |
| GET | /api/billing/payments | 200 | JWT | Payment history |

### Analytics (analytics.py)
| Method | Path | Status | Auth | Notes |
|--------|------|--------|------|-------|
| GET | /api/analytics/overview | 200 | JWT | Analytics overview |
| GET | /api/analytics/trends | 200 | JWT | Content trends |
| GET | /api/analytics/insights | 200 | JWT | AI insights |
| GET | /api/analytics/learning | 200 | JWT | Learning data |
| GET | /api/analytics/optimal-times | 200 | JWT | Best posting times |
| GET | /api/analytics/fatigue-shield | 200 | JWT | Fatigue status |
| GET | /api/analytics/persona/evolution | 200 | JWT | Persona evolution |
| GET | /api/analytics/persona/voice-evolution | 200 | JWT | Voice changes |
| GET | /api/analytics/persona/suggestions | 200 | JWT | **FIXED: added 12s timeout** |

### Other Routes (all tested, all working)
- Platforms: /api/platforms/status — 200
- Repurpose: /api/content/repurpose/*, /api/content/series/*, /api/content/diversity/* — all 200
- Templates: /api/templates/* — all 200
- Strategy: /api/strategy — 200
- Notifications: /api/notifications, /api/notifications/count — 200
- Webhooks: /api/webhooks, /api/webhooks/events — 200
- UOM: /api/uom/, /api/uom/directives/{agent} — 200
- Campaigns: /api/campaigns — 200
- Agency: /api/agency/workspaces, /api/agency/invitations — 200
- Viral Card: /api/viral-card/analyze — 200
- Obsidian: /api/obsidian/config — 200
- Admin: /api/admin/* — 403 (correctly blocked for non-admin)
- Health: /health — 200 (all services connected)

## Issues Found & Fixed

| # | Endpoint | Issue | Fix |
|---|----------|-------|-----|
| 1 | /persona/regional-english/options | Returns empty body (Railway CDN compression) | Added JSONResponse + Cache-Control: no-transform |
| 2 | /dashboard/schedule/weekly | Timeout >15s (LLM-heavy planner agent) | Added 12s asyncio timeout wrapper |
| 3 | /analytics/persona/suggestions | Timeout >15s (chained LLM calls) | Added 12s asyncio timeout wrapper |
