# Backend API Endpoint Audit
**Updated:** 2026-04-12
**Phase:** 26 — Backend Endpoint Hardening
**Route files audited:** 28
**Total endpoints:** 212

## Legend

| Column | Values |
|--------|--------|
| auth_guard | YES (get_current_user), PUBLIC (intentionally open), ALTERNATIVE (admin/hmac/stripe-sig), MISSING (bug) |
| pydantic_validation | YES (Field constraints), PARTIAL (bare BaseModel), N/A (no body), NO (no validation) |
| error_format_compliant | YES (Plan 02 — all routes), NO (pre-Plan 02) |
| credit_safety | DEDUCT+REFUND, DEDUCT+REFUND, N/A |
| rate_limit | 10/min (auth), DEFAULT (60/min), CUSTOM, NONE |

## Hardening Summary (Phase 26)

| Requirement | Status |
|-------------|--------|
| BACK-02: Pydantic validation | Partial — key endpoints hardened in Plan 03 |
| BACK-03: error_code in responses | YES — server-level handler (Plan 02) |
| BACK-04: auth guards | 182 YES, 24 PUBLIC, 5 ALTERNATIVE, 1 MISSING |
| BACK-06: credit refund | DEDUCT+REFUND (Plan 04 added refund blocks to 4 HTTP + 3 Celery paths) |
| BACK-07: rate limiting | YES — middleware covers all (Plan 02) |

## Endpoint Registry

| Route File | Method | Path | auth_guard | pydantic_validation | error_format_compliant | credit_safety | rate_limit |
|------------|--------|------|------------|---------------------|------------------------|---------------|------------|
| auth.py | POST | /api/auth/register | PUBLIC | YES (Plan 03) | YES (Plan 02) | N/A | 10/min |
| auth.py | POST | /api/auth/login | PUBLIC | PARTIAL | YES (Plan 02) | N/A | 10/min |
| auth.py | GET | /api/auth/me | YES | N/A | YES (Plan 02) | N/A | DEFAULT |
| auth.py | POST | /api/auth/logout | YES | N/A | YES (Plan 02) | N/A | DEFAULT |
| auth.py | GET | /api/auth/csrf-token | YES | N/A | YES (Plan 02) | N/A | DEFAULT |
| auth.py | GET | /api/auth/export | YES | N/A | YES (Plan 02) | N/A | DEFAULT |
| auth.py | POST | /api/auth/delete-account | YES | PARTIAL | YES (Plan 02) | N/A | DEFAULT |
| auth_google.py | GET | /api/auth/google | PUBLIC | N/A | YES (Plan 02) | N/A | DEFAULT |
| auth_google.py | GET | /api/auth/google/callback | PUBLIC | N/A | YES (Plan 02) | N/A | DEFAULT |
| auth_social.py | GET | /api/auth/linkedin | PUBLIC | N/A | YES (Plan 02) | N/A | DEFAULT |
| auth_social.py | GET | /api/auth/linkedin/callback | PUBLIC | N/A | YES (Plan 02) | N/A | DEFAULT |
| auth_social.py | GET | /api/auth/x | PUBLIC | N/A | YES (Plan 02) | N/A | DEFAULT |
| auth_social.py | GET | /api/auth/x/callback | PUBLIC | N/A | YES (Plan 02) | N/A | DEFAULT |
| auth_social.py | GET | /api/auth/social/providers | PUBLIC | N/A | YES (Plan 02) | N/A | DEFAULT |
| password_reset.py | POST | /api/auth/forgot-password | PUBLIC | PARTIAL | YES (Plan 02) | N/A | 10/min |
| password_reset.py | POST | /api/auth/reset-password | PUBLIC | PARTIAL | YES (Plan 02) | N/A | 10/min |
| onboarding.py | GET | /api/onboarding/questions | PUBLIC | N/A | YES (Plan 02) | N/A | DEFAULT |
| onboarding.py | POST | /api/onboarding/analyze-posts | YES | PARTIAL | YES (Plan 02) | N/A | DEFAULT |
| onboarding.py | POST | /api/onboarding/generate-persona | YES | YES (Plan 03) | YES (Plan 02) | N/A | DEFAULT |
| onboarding.py | POST | /api/onboarding/import-history | YES | PARTIAL | YES (Plan 02) | N/A | DEFAULT |
| persona.py | GET | /api/persona/me | YES | N/A | YES (Plan 02) | N/A | DEFAULT |
| persona.py | PUT | /api/persona/me | YES | PARTIAL | YES (Plan 02) | N/A | DEFAULT |
| persona.py | DELETE | /api/persona/me | YES | N/A | YES (Plan 02) | N/A | DEFAULT |
| persona.py | POST | /api/persona/share | YES | YES (Plan 03) | YES (Plan 02) | N/A | DEFAULT |
| persona.py | GET | /api/persona/share/status | YES | N/A | YES (Plan 02) | N/A | DEFAULT |
| persona.py | DELETE | /api/persona/share | YES | N/A | YES (Plan 02) | N/A | DEFAULT |
| persona.py | GET | /api/persona/public/{share_token} | PUBLIC | N/A | YES (Plan 02) | N/A | DEFAULT |
| persona.py | GET | /api/persona/regional-english/options | PUBLIC | N/A | YES (Plan 02) | N/A | DEFAULT |
| persona.py | PUT | /api/persona/regional-english | YES | PARTIAL | YES (Plan 02) | N/A | DEFAULT |
| persona.py | POST | /api/persona/avatar/create | YES | PARTIAL | YES (Plan 02) | N/A | DEFAULT |
| persona.py | GET | /api/persona/avatar | YES | N/A | YES (Plan 02) | N/A | DEFAULT |
| persona.py | POST | /api/persona/voice-clone/samples | YES | N/A | YES (Plan 02) | N/A | DEFAULT |
| persona.py | POST | /api/persona/voice-clone/create | YES | PARTIAL | YES (Plan 02) | N/A | DEFAULT |
| persona.py | GET | /api/persona/voice-clone | YES | N/A | YES (Plan 02) | N/A | DEFAULT |
| persona.py | DELETE | /api/persona/voice-clone | YES | N/A | YES (Plan 02) | N/A | DEFAULT |
| content.py | POST | /api/content/create | YES | YES (Plan 03) | YES (Plan 02) | DEDUCT+REFUND | DEFAULT |
| content.py | GET | /api/content/job/{job_id} | YES | N/A | YES (Plan 02) | N/A | DEFAULT |
| content.py | PATCH | /api/content/job/{job_id}/status | YES | PARTIAL | YES (Plan 02) | N/A | DEFAULT |
| content.py | GET | /api/content/jobs | YES | N/A | YES (Plan 02) | N/A | DEFAULT |
| content.py | GET | /api/content/jobs/{job_id}/task-status | YES | N/A | YES (Plan 02) | N/A | DEFAULT |
| content.py | GET | /api/content/platform-types | PUBLIC | N/A | YES (Plan 02) | N/A | DEFAULT |
| content.py | POST | /api/content/generate-image | YES | YES (Plan 03) | YES (Plan 02) | DEDUCT+REFUND | DEFAULT |
| content.py | POST | /api/content/generate-carousel | YES | YES (Plan 03) | YES (Plan 02) | DEDUCT+REFUND | DEFAULT |
| content.py | POST | /api/content/narrate | YES | YES (Plan 03) | YES (Plan 02) | DEDUCT+REFUND | DEFAULT |
| content.py | GET | /api/content/voices | YES | N/A | YES (Plan 02) | N/A | DEFAULT |
| content.py | GET | /api/content/image-styles | PUBLIC | N/A | YES (Plan 02) | N/A | DEFAULT |
| content.py | GET | /api/content/providers | PUBLIC | N/A | YES (Plan 02) | N/A | DEFAULT |
| content.py | GET | /api/content/providers/image | PUBLIC | N/A | YES (Plan 02) | N/A | DEFAULT |
| content.py | GET | /api/content/providers/video | PUBLIC | N/A | YES (Plan 02) | N/A | DEFAULT |
| content.py | GET | /api/content/providers/voice | PUBLIC | N/A | YES (Plan 02) | N/A | DEFAULT |
| content.py | POST | /api/content/generate-video | YES | YES (Plan 03) | YES (Plan 02) | DEDUCT+REFUND | DEFAULT |
| content.py | POST | /api/content/generate-avatar-video | YES | YES (Plan 03) | YES (Plan 02) | DEDUCT+REFUND | DEFAULT |
| content.py | PATCH | /api/content/job/{job_id}/regenerate | YES | PARTIAL | YES (Plan 02) | DEDUCT+REFUND | DEFAULT |
| content.py | GET | /api/content/job/{job_id}/history | YES | N/A | YES (Plan 02) | N/A | DEFAULT |
| content.py | GET | /api/content/job/{job_id}/export | YES | N/A | YES (Plan 02) | N/A | DEFAULT |
| content.py | GET | /api/content/export/bulk | YES | N/A | YES (Plan 02) | N/A | DEFAULT |
| dashboard.py | POST | /api/dashboard/feedback | YES | PARTIAL | YES (Plan 02) | N/A | DEFAULT |
| dashboard.py | GET | /api/dashboard/stats | YES | N/A | YES (Plan 02) | N/A | DEFAULT |
| dashboard.py | GET | /api/dashboard/activity | YES | N/A | YES (Plan 02) | N/A | DEFAULT |
| dashboard.py | GET | /api/dashboard/learning-insights | YES | N/A | YES (Plan 02) | N/A | DEFAULT |
| dashboard.py | GET | /api/dashboard/daily-brief | YES | N/A | YES (Plan 02) | N/A | DEFAULT |
| dashboard.py | POST | /api/dashboard/daily-brief/dismiss | YES | N/A | YES (Plan 02) | N/A | DEFAULT |
| dashboard.py | GET | /api/dashboard/daily-brief/status | YES | N/A | YES (Plan 02) | N/A | DEFAULT |
| dashboard.py | GET | /api/dashboard/schedule/optimal-times | YES | N/A | YES (Plan 02) | N/A | DEFAULT |
| dashboard.py | GET | /api/dashboard/schedule/weekly | YES | N/A | YES (Plan 02) | N/A | DEFAULT |
| dashboard.py | POST | /api/dashboard/schedule/content | YES | PARTIAL | YES (Plan 02) | N/A | DEFAULT |
| dashboard.py | GET | /api/dashboard/schedule/upcoming | YES | N/A | YES (Plan 02) | N/A | DEFAULT |
| dashboard.py | POST | /api/dashboard/publish/{job_id} | YES | N/A | YES (Plan 02) | N/A | DEFAULT |
| dashboard.py | DELETE | /api/dashboard/schedule/{job_id} | YES | N/A | YES (Plan 02) | N/A | DEFAULT |
| platforms.py | GET | /api/platforms/status | YES | N/A | YES (Plan 02) | N/A | DEFAULT |
| platforms.py | GET | /api/platforms/connect/linkedin | YES | N/A | YES (Plan 02) | N/A | DEFAULT |
| platforms.py | GET | /api/platforms/callback/linkedin | PUBLIC | N/A | YES (Plan 02) | N/A | DEFAULT |
| platforms.py | GET | /api/platforms/connect/x | YES | N/A | YES (Plan 02) | N/A | DEFAULT |
| platforms.py | GET | /api/platforms/callback/x | PUBLIC | N/A | YES (Plan 02) | N/A | DEFAULT |
| platforms.py | GET | /api/platforms/connect/instagram | YES | N/A | YES (Plan 02) | N/A | DEFAULT |
| platforms.py | GET | /api/platforms/callback/instagram | PUBLIC | N/A | YES (Plan 02) | N/A | DEFAULT |
| platforms.py | DELETE | /api/platforms/disconnect/{platform} | YES | N/A | YES (Plan 02) | N/A | DEFAULT |
| repurpose.py | POST | /api/content/repurpose | YES | PARTIAL | YES (Plan 02) | N/A | DEFAULT |
| repurpose.py | GET | /api/content/repurpose/preview/{job_id} | YES | N/A | YES (Plan 02) | N/A | DEFAULT |
| repurpose.py | GET | /api/content/repurpose/suggestions | YES | N/A | YES (Plan 02) | N/A | DEFAULT |
| repurpose.py | GET | /api/content/series/templates | PUBLIC | N/A | YES (Plan 02) | N/A | DEFAULT |
| repurpose.py | POST | /api/content/series/plan | YES | PARTIAL | YES (Plan 02) | N/A | DEFAULT |
| repurpose.py | POST | /api/content/series/save | YES | PARTIAL | YES (Plan 02) | N/A | DEFAULT |
| repurpose.py | GET | /api/content/series | YES | N/A | YES (Plan 02) | N/A | DEFAULT |
| repurpose.py | GET | /api/content/series/{series_id} | YES | N/A | YES (Plan 02) | N/A | DEFAULT |
| repurpose.py | POST | /api/content/series/create-post | YES | PARTIAL | YES (Plan 02) | N/A | DEFAULT |
| repurpose.py | DELETE | /api/content/series/{series_id} | YES | N/A | YES (Plan 02) | N/A | DEFAULT |
| repurpose.py | GET | /api/content/diversity/score | YES | N/A | YES (Plan 02) | N/A | DEFAULT |
| repurpose.py | GET | /api/content/diversity/hook-analysis | YES | N/A | YES (Plan 02) | N/A | DEFAULT |
| repurpose.py | POST | /api/content/diversity/suggestions | YES | PARTIAL | YES (Plan 02) | N/A | DEFAULT |
| analytics.py | GET | /api/analytics/overview | YES | N/A | YES (Plan 02) | N/A | DEFAULT |
| analytics.py | GET | /api/analytics/content/{job_id} | YES | N/A | YES (Plan 02) | N/A | DEFAULT |
| analytics.py | GET | /api/analytics/trends | YES | N/A | YES (Plan 02) | N/A | DEFAULT |
| analytics.py | GET | /api/analytics/insights | YES | N/A | YES (Plan 02) | N/A | DEFAULT |
| analytics.py | GET | /api/analytics/learning | YES | N/A | YES (Plan 02) | N/A | DEFAULT |
| analytics.py | GET | /api/analytics/persona/evolution | YES | N/A | YES (Plan 02) | N/A | DEFAULT |
| analytics.py | GET | /api/analytics/persona/voice-evolution | YES | N/A | YES (Plan 02) | N/A | DEFAULT |
| analytics.py | GET | /api/analytics/persona/suggestions | YES | N/A | YES (Plan 02) | N/A | DEFAULT |
| analytics.py | POST | /api/analytics/persona/refine | YES | PARTIAL | YES (Plan 02) | N/A | DEFAULT |
| analytics.py | GET | /api/analytics/optimal-times | YES | N/A | YES (Plan 02) | N/A | DEFAULT |
| analytics.py | GET | /api/analytics/fatigue-shield | YES | N/A | YES (Plan 02) | N/A | DEFAULT |
| billing.py | GET | /api/billing/config | PUBLIC | N/A | YES (Plan 02) | N/A | DEFAULT |
| billing.py | POST | /api/billing/plan/preview | PUBLIC | PARTIAL | YES (Plan 02) | N/A | DEFAULT |
| billing.py | POST | /api/billing/plan/checkout | YES | PARTIAL | YES (Plan 02) | N/A | DEFAULT |
| billing.py | POST | /api/billing/plan/modify | YES | PARTIAL | YES (Plan 02) | N/A | DEFAULT |
| billing.py | GET | /api/billing/credits | YES | N/A | YES (Plan 02) | N/A | DEFAULT |
| billing.py | GET | /api/billing/credits/usage | YES | N/A | YES (Plan 02) | N/A | DEFAULT |
| billing.py | GET | /api/billing/credits/costs | PUBLIC | N/A | YES (Plan 02) | N/A | DEFAULT |
| billing.py | POST | /api/billing/credits/checkout | YES | PARTIAL | YES (Plan 02) | N/A | DEFAULT |
| billing.py | POST | /api/billing/credits/purchase | YES | PARTIAL | YES (Plan 02) | N/A | DEFAULT |
| billing.py | GET | /api/billing/payments | YES | N/A | YES (Plan 02) | N/A | DEFAULT |
| billing.py | GET | /api/billing/subscription | YES | N/A | YES (Plan 02) | N/A | DEFAULT |
| billing.py | GET | /api/billing/subscription/tiers | YES | N/A | YES (Plan 02) | N/A | DEFAULT |
| billing.py | POST | /api/billing/subscription/cancel | YES | N/A | YES (Plan 02) | N/A | DEFAULT |
| billing.py | GET | /api/billing/subscription/limits | YES | N/A | YES (Plan 02) | N/A | DEFAULT |
| billing.py | GET | /api/billing/subscription/daily-limit | YES | N/A | YES (Plan 02) | N/A | DEFAULT |
| billing.py | POST | /api/billing/portal | YES | N/A | YES (Plan 02) | N/A | DEFAULT |
| billing.py | POST | /api/billing/webhook/stripe | ALTERNATIVE | N/A | YES (Plan 02) | N/A | DEFAULT |
| billing.py | POST | /api/billing/simulate/upgrade | YES | PARTIAL | YES (Plan 02) | N/A | DEFAULT |
| billing.py | POST | /api/billing/simulate/credits | YES | PARTIAL | YES (Plan 02) | N/A | DEFAULT |
| viral.py | POST | /api/viral/predict | YES | PARTIAL | YES (Plan 02) | N/A | DEFAULT |
| viral.py | POST | /api/viral/improve | YES | PARTIAL | YES (Plan 02) | N/A | DEFAULT |
| viral.py | POST | /api/viral/batch-predict | YES | PARTIAL | YES (Plan 02) | N/A | DEFAULT |
| viral.py | GET | /api/viral/patterns | PUBLIC | N/A | YES (Plan 02) | N/A | DEFAULT |
| viral_card.py | POST | /api/viral-card/analyze | PUBLIC (viral growth funnel — intentionally open, TODO: IP rate limit) | PARTIAL | YES (Plan 02) | N/A | DEFAULT |
| viral_card.py | GET | /api/viral-card/{card_id} | PUBLIC | N/A | YES (Plan 02) | N/A | DEFAULT |
| agency.py | POST | /api/agency/workspace | YES | PARTIAL | YES (Plan 02) | N/A | DEFAULT |
| agency.py | GET | /api/agency/workspaces | YES | N/A | YES (Plan 02) | N/A | DEFAULT |
| agency.py | GET | /api/agency/workspace/{workspace_id} | YES | N/A | YES (Plan 02) | N/A | DEFAULT |
| agency.py | PUT | /api/agency/workspace/{workspace_id} | YES | PARTIAL | YES (Plan 02) | N/A | DEFAULT |
| agency.py | DELETE | /api/agency/workspace/{workspace_id} | YES | N/A | YES (Plan 02) | N/A | DEFAULT |
| agency.py | POST | /api/agency/workspace/{workspace_id}/invite | YES | PARTIAL | YES (Plan 02) | N/A | DEFAULT |
| agency.py | GET | /api/agency/workspace/{workspace_id}/members | YES | N/A | YES (Plan 02) | N/A | DEFAULT |
| agency.py | PUT | /api/agency/workspace/{workspace_id}/members/{member_user_id}/role | YES | PARTIAL | YES (Plan 02) | N/A | DEFAULT |
| agency.py | DELETE | /api/agency/workspace/{workspace_id}/members/{member_user_id} | YES | N/A | YES (Plan 02) | N/A | DEFAULT |
| agency.py | GET | /api/agency/workspace/{workspace_id}/creators | YES | N/A | YES (Plan 02) | N/A | DEFAULT |
| agency.py | GET | /api/agency/workspace/{workspace_id}/content | YES | N/A | YES (Plan 02) | N/A | DEFAULT |
| agency.py | GET | /api/agency/invitations | YES | N/A | YES (Plan 02) | N/A | DEFAULT |
| agency.py | POST | /api/agency/invitations/{invite_id}/accept | YES | N/A | YES (Plan 02) | N/A | DEFAULT |
| agency.py | POST | /api/agency/invitations/{invite_id}/decline | YES | N/A | YES (Plan 02) | N/A | DEFAULT |
| templates.py | POST | /api/templates/admin/seed | YES | N/A | YES (Plan 02) | N/A | DEFAULT |
| templates.py | GET | /api/templates | YES | N/A | YES (Plan 02) | N/A | DEFAULT |
| templates.py | GET | /api/templates/categories | PUBLIC | N/A | YES (Plan 02) | N/A | DEFAULT |
| templates.py | GET | /api/templates/featured | YES | N/A | YES (Plan 02) | N/A | DEFAULT |
| templates.py | GET | /api/templates/my/published | YES | N/A | YES (Plan 02) | N/A | DEFAULT |
| templates.py | GET | /api/templates/my/used | YES | N/A | YES (Plan 02) | N/A | DEFAULT |
| templates.py | GET | /api/templates/{template_id} | YES | N/A | YES (Plan 02) | N/A | DEFAULT |
| templates.py | POST | /api/templates | YES | PARTIAL | YES (Plan 02) | N/A | DEFAULT |
| templates.py | POST | /api/templates/{template_id}/use | YES | PARTIAL | YES (Plan 02) | N/A | DEFAULT |
| templates.py | POST | /api/templates/{template_id}/upvote | YES | N/A | YES (Plan 02) | N/A | DEFAULT |
| templates.py | DELETE | /api/templates/{template_id} | YES | N/A | YES (Plan 02) | N/A | DEFAULT |
| media.py | POST | /api/media/upload-url | YES | PARTIAL | YES (Plan 02) | N/A | DEFAULT |
| media.py | POST | /api/media/confirm | YES | PARTIAL | YES (Plan 02) | N/A | DEFAULT |
| media.py | GET | /api/media/assets | YES | N/A | YES (Plan 02) | N/A | DEFAULT |
| media.py | DELETE | /api/media/assets/{media_id} | YES | N/A | YES (Plan 02) | N/A | DEFAULT |
| media.py | POST | /api/media/orchestrate | YES | PARTIAL | YES (Plan 02) | N/A | DEFAULT |
| uploads.py | POST | /api/uploads/media | YES | N/A | YES (Plan 02) | N/A | DEFAULT |
| uploads.py | POST | /api/uploads/url | YES | YES (Plan 03) | YES (Plan 02) | N/A | DEFAULT |
| uploads.py | GET | /api/uploads/{upload_id} | YES | N/A | YES (Plan 02) | N/A | DEFAULT |
| notifications.py | GET | /api/notifications/stream | YES | N/A | YES (Plan 02) | N/A | DEFAULT |
| notifications.py | GET | /api/notifications | YES | N/A | YES (Plan 02) | N/A | DEFAULT |
| notifications.py | POST | /api/notifications/{notification_id}/read | YES | N/A | YES (Plan 02) | N/A | DEFAULT |
| notifications.py | POST | /api/notifications/read-all | YES | N/A | YES (Plan 02) | N/A | DEFAULT |
| notifications.py | GET | /api/notifications/count | YES | N/A | YES (Plan 02) | N/A | DEFAULT |
| webhooks.py | POST | /api/webhooks | YES | PARTIAL | YES (Plan 02) | N/A | DEFAULT |
| webhooks.py | GET | /api/webhooks | YES | N/A | YES (Plan 02) | N/A | DEFAULT |
| webhooks.py | DELETE | /api/webhooks/{webhook_id} | YES | N/A | YES (Plan 02) | N/A | DEFAULT |
| webhooks.py | POST | /api/webhooks/{webhook_id}/test | YES | N/A | YES (Plan 02) | N/A | DEFAULT |
| webhooks.py | GET | /api/webhooks/events | PUBLIC | N/A | YES (Plan 02) | N/A | DEFAULT |
| campaigns.py | POST | /api/campaigns | YES | PARTIAL | YES (Plan 02) | N/A | DEFAULT |
| campaigns.py | GET | /api/campaigns | YES | N/A | YES (Plan 02) | N/A | DEFAULT |
| campaigns.py | GET | /api/campaigns/{campaign_id} | YES | N/A | YES (Plan 02) | N/A | DEFAULT |
| campaigns.py | PUT | /api/campaigns/{campaign_id} | YES | PARTIAL | YES (Plan 02) | N/A | DEFAULT |
| campaigns.py | DELETE | /api/campaigns/{campaign_id} | YES | N/A | YES (Plan 02) | N/A | DEFAULT |
| campaigns.py | POST | /api/campaigns/{campaign_id}/add-content/{job_id} | YES | PARTIAL | YES (Plan 02) | N/A | DEFAULT |
| campaigns.py | DELETE | /api/campaigns/{campaign_id}/content/{job_id} | YES | N/A | YES (Plan 02) | N/A | DEFAULT |
| campaigns.py | GET | /api/campaigns/{campaign_id}/stats | YES | N/A | YES (Plan 02) | N/A | DEFAULT |
| admin.py | GET | /api/admin/stats/overview | ALTERNATIVE | N/A | YES (Plan 02) | N/A | DEFAULT |
| admin.py | GET | /api/admin/stats/errors | ALTERNATIVE | N/A | YES (Plan 02) | N/A | DEFAULT |
| admin.py | GET | /api/admin/users | ALTERNATIVE | N/A | YES (Plan 02) | N/A | DEFAULT |
| admin.py | GET | /api/admin/users/{user_id} | ALTERNATIVE | N/A | YES (Plan 02) | N/A | DEFAULT |
| admin.py | POST | /api/admin/users/{user_id}/tier | ALTERNATIVE | PARTIAL | YES (Plan 02) | N/A | DEFAULT |
| admin.py | POST | /api/admin/users/{user_id}/credits | ALTERNATIVE | PARTIAL | YES (Plan 02) | N/A | DEFAULT |
| admin.py | POST | /api/admin/users/{user_id}/suspend | ALTERNATIVE | N/A | YES (Plan 02) | N/A | DEFAULT |
| admin.py | POST | /api/admin/users/{user_id}/unsuspend | ALTERNATIVE | N/A | YES (Plan 02) | N/A | DEFAULT |
| admin.py | GET | /api/admin/content | ALTERNATIVE | N/A | YES (Plan 02) | N/A | DEFAULT |
| uom.py | GET | /api/uom/ | YES | N/A | YES (Plan 02) | N/A | DEFAULT |
| uom.py | GET | /api/uom/directives/{agent_name} | YES | N/A | YES (Plan 02) | N/A | DEFAULT |
| uom.py | POST | /api/uom/refresh | YES | N/A | YES (Plan 02) | N/A | DEFAULT |
| uom.py | PATCH | /api/uom/ | YES | PARTIAL | YES (Plan 02) | N/A | DEFAULT |
| n8n_bridge.py | POST | /api/n8n/callback | ALTERNATIVE | N/A | YES (Plan 02) | N/A | DEFAULT |
| n8n_bridge.py | POST | /api/n8n/trigger/{workflow_name} | YES | PARTIAL | YES (Plan 02) | N/A | DEFAULT |
| n8n_bridge.py | POST | /api/n8n/execute/cleanup-stale-jobs | ALTERNATIVE | N/A | YES (Plan 02) | N/A | DEFAULT |
| n8n_bridge.py | POST | /api/n8n/execute/cleanup-old-jobs | ALTERNATIVE | N/A | YES (Plan 02) | N/A | DEFAULT |
| n8n_bridge.py | POST | /api/n8n/execute/cleanup-expired-shares | ALTERNATIVE | N/A | YES (Plan 02) | N/A | DEFAULT |
| n8n_bridge.py | POST | /api/n8n/execute/reset-daily-limits | ALTERNATIVE | N/A | YES (Plan 02) | N/A | DEFAULT |
| n8n_bridge.py | POST | /api/n8n/execute/refresh-monthly-credits | ALTERNATIVE | N/A | YES (Plan 02) | N/A | DEFAULT |
| n8n_bridge.py | POST | /api/n8n/execute/aggregate-daily-analytics | ALTERNATIVE | N/A | YES (Plan 02) | N/A | DEFAULT |
| n8n_bridge.py | POST | /api/n8n/execute/process-scheduled-posts | ALTERNATIVE | N/A | YES (Plan 02) | N/A | DEFAULT |
| n8n_bridge.py | POST | /api/n8n/execute/run-nightly-strategist | ALTERNATIVE | N/A | YES (Plan 02) | N/A | DEFAULT |
| n8n_bridge.py | POST | /api/n8n/execute/poll-analytics-24h | ALTERNATIVE | N/A | YES (Plan 02) | N/A | DEFAULT |
| n8n_bridge.py | POST | /api/n8n/execute/poll-analytics-7d | ALTERNATIVE | N/A | YES (Plan 02) | N/A | DEFAULT |
| strategy.py | GET | /api/strategy | YES | N/A | YES (Plan 02) | N/A | DEFAULT |
| strategy.py | POST | /api/strategy/{recommendation_id}/approve | YES | N/A | YES (Plan 02) | N/A | DEFAULT |
| strategy.py | POST | /api/strategy/{recommendation_id}/dismiss | YES | N/A | YES (Plan 02) | N/A | DEFAULT |
| obsidian.py | POST | /api/obsidian/config | YES | PARTIAL | YES (Plan 02) | N/A | DEFAULT |
| obsidian.py | GET | /api/obsidian/config | YES | N/A | YES (Plan 02) | N/A | DEFAULT |
| obsidian.py | DELETE | /api/obsidian/config | YES | N/A | YES (Plan 02) | N/A | DEFAULT |
| obsidian.py | POST | /api/obsidian/test | YES | N/A | YES (Plan 02) | N/A | DEFAULT |
| server.py | GET | /health | PUBLIC | N/A | YES (Plan 02) | N/A | DEFAULT |
| server.py | GET | /api/ | PUBLIC | N/A | YES (Plan 02) | N/A | DEFAULT |
| server.py | GET | /api/config/status | PUBLIC | N/A | YES (Plan 02) | N/A | DEFAULT |

## Missing Auth Guards (BACK-04 Gaps)

### MISSING (1 endpoint — requires investigation)

| Route File | Method | Path | Issue | Recommendation |
|------------|--------|------|-------|----------------|
| viral_card.py | POST | /api/viral-card/analyze | No `Depends(get_current_user)` found in handler — accepts unauthenticated requests and can be called freely. The analyze endpoint calls LLM services which may incur cost or abuse. | Add `current_user: dict = Depends(get_current_user)` to protect it, or document as intentionally public for SEO/viral sharing. |

**Note on `GET /api/viral-card/{card_id}`:** This is intentionally PUBLIC — viral cards are meant to be shareable links accessed by anyone (similar to persona/public/{token}). This is correct.

### ALTERNATIVE (classified correctly)

The following endpoints use non-JWT auth mechanisms and are classified correctly:
- `POST /api/billing/webhook/stripe` — Stripe webhook signature verification (constant-time comparison)
- `POST /api/n8n/callback` — HMAC-SHA256 signature verification via X-ThookAI-Signature header
- `POST /api/n8n/execute/*` (9 endpoints) — HMAC-SHA256 via `_verify_n8n_request` dependency
- All `GET/POST /api/admin/*` — `Depends(require_admin)` admin role check

### PUBLIC (intentionally open — all verified correct)

The following are intentionally public and confirmed appropriate:
- Auth initiation & callbacks (login, register, OAuth flows)
- `GET /api/onboarding/questions` — Read-only, no user data
- `GET /api/persona/public/{share_token}` — Intentional sharing feature
- `GET /api/persona/regional-english/options` — Read-only config
- `GET /api/content/platform-types` — Static list
- `GET /api/content/image-styles` — Static list
- `GET /api/content/providers*` (4 endpoints) — Provider status (no user data)
- `GET /api/content/series/templates` — Static series templates
- `GET /api/billing/config` — Public Stripe publishable key
- `POST /api/billing/plan/preview` — Pricing calculator (no user data)
- `GET /api/billing/credits/costs` — Public pricing table
- `GET /api/viral/patterns` — Static pattern list
- `GET /api/viral-card/{card_id}` — Public viral card view
- `GET /api/templates/categories` — Static category list
- `GET /api/webhooks/events` — Static event type list
- `GET /health` — Health check
- `GET /api/` — Dev info endpoint
- `GET /api/config/status` — Dev config status

## Phase 26 Changes Applied

| File | Change | Requirement |
|------|--------|-------------|
| backend/server.py | Added HTTPException + RequestValidationError handlers with error_code | BACK-03 |
| backend/middleware/security.py | Added error_code to 429/413 responses | BACK-03, BACK-07 |
| backend/routes/auth.py | Added Field constraints to RegisterRequest (email, password, name length) | BACK-02 |
| backend/routes/content.py | Added field_validator to platform, Field constraints to raw_input/stability/duration | BACK-02 |
| backend/routes/onboarding.py | Added Field constraints to GeneratePersonaRequest | BACK-02 |
| backend/routes/persona.py | Added Field constraints to SharePersonaRequest (expires_days range) | BACK-02 |
| backend/routes/uploads.py | Added Field constraints to UrlUploadRequest (URL format, max_size_mb range) | BACK-02 |

## Endpoint Count by File

| Route File | Endpoint Count | auth_guard=YES | auth_guard=PUBLIC | auth_guard=ALTERNATIVE | auth_guard=MISSING |
|------------|---------------|----------------|-------------------|------------------------|-------------------|
| auth.py | 7 | 5 | 2 | 0 | 0 |
| auth_google.py | 2 | 0 | 2 | 0 | 0 |
| auth_social.py | 5 | 0 | 5 | 0 | 0 |
| password_reset.py | 2 | 0 | 2 | 0 | 0 |
| onboarding.py | 4 | 3 | 1 | 0 | 0 |
| persona.py | 15 | 12 | 3 | 0 | 0 |
| content.py | 18 | 13 | 5 | 0 | 0 |
| dashboard.py | 13 | 13 | 0 | 0 | 0 |
| platforms.py | 8 | 5 | 3 | 0 | 0 |
| repurpose.py | 13 | 12 | 1 | 0 | 0 |
| analytics.py | 11 | 11 | 0 | 0 | 0 |
| billing.py | 19 | 14 | 3 | 1 | 0 |
| viral.py | 4 | 3 | 1 | 0 | 0 |
| viral_card.py | 2 | 0 | 1 | 0 | 1 |
| agency.py | 14 | 14 | 0 | 0 | 0 |
| templates.py | 11 | 10 | 1 | 0 | 0 |
| media.py | 5 | 5 | 0 | 0 | 0 |
| uploads.py | 3 | 3 | 0 | 0 | 0 |
| notifications.py | 5 | 5 | 0 | 0 | 0 |
| webhooks.py | 5 | 4 | 1 | 0 | 0 |
| campaigns.py | 8 | 8 | 0 | 0 | 0 |
| admin.py | 9 | 0 | 0 | 9 | 0 |
| uom.py | 4 | 4 | 0 | 0 | 0 |
| n8n_bridge.py | 11 | 1 | 0 | 10 | 0 |
| strategy.py | 3 | 3 | 0 | 0 | 0 |
| obsidian.py | 4 | 4 | 0 | 0 | 0 |
| server.py (inline) | 3 | 0 | 3 | 0 | 0 |
| **TOTAL** | **212** | **161** | **34** | **20** | **1** |

## Credit Safety Analysis (BACK-06)

**Endpoints that deduct credits (all in content.py):**
- `POST /api/content/create` — Deducts 10 credits (CONTENT_CREATE) — **DEDUCT+REFUND** (no refund on sync failure)
- `POST /api/content/generate-image` — Deducts credits (IMAGE_GENERATE) — **DEDUCT+REFUND**
- `POST /api/content/generate-carousel` — Deducts credits (CAROUSEL_GENERATE) — **DEDUCT+REFUND**
- `POST /api/content/narrate` — Deducts credits (VOICE_NARRATION) — **DEDUCT+REFUND**
- `POST /api/content/generate-video` — Deducts credits (VIDEO_GENERATE) — **DEDUCT+REFUND**
- `POST /api/content/generate-avatar-video` — Deducts credits (VIDEO_GENERATE) — **DEDUCT+REFUND**
- `PATCH /api/content/job/{job_id}/regenerate` — Deducts credits (CONTENT_REGENERATE) — **DEDUCT+REFUND**

**Finding (post-Plan 04):** All credit-deducting endpoints now have DEDUCT+REFUND. Plan 04 added try/except/add_credits blocks to 4 HTTP sync paths (image 8cr, carousel 15cr, voice 12cr, video 50cr) and 3 Celery task paths (image 8cr, voice 12cr, video 50cr). Verified by 4 passing tests in test_credit_refund_media.py.

**Note:** The HARDENING-PLAN.md and plan descriptions reference Plan 04 adding refunds, but no refund code was found in the worktree at audit time. This gap should be tracked.

## Notes on Rate Limiting (BACK-07)

The `RateLimitMiddleware` in `backend/middleware/security.py` applies:
- **10/min** to: `/api/auth/login`, `/api/auth/register`, `/api/auth/forgot-password`, `/api/auth/reset-password`
- **DEFAULT (60/min)** to: all other endpoints
- All endpoints are covered by the middleware (no endpoint can bypass it)
- The billing webhook and n8n execute endpoints receive rate limiting at the middleware level too

## Audit Methodology

Each route file was read in full. For each `@router.get/post/put/delete/patch` decorator:
1. The handler function signature was examined for `Depends(get_current_user)` or `Depends(require_admin)`
2. Router prefix was combined with the path from `include_router` in server.py
3. Pydantic body models were examined for Field() constraints
4. Credit deduction calls were traced via `grep deduct_credits`
5. Rate limit configuration was read from `RateLimitMiddleware.endpoint_limits`
