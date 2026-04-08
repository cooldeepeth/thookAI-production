---
phase: 07-platform-features-admin-frontend-quality
plan: "02"
subsystem: tests
tags: [tests, persona-sharing, viral-card, notifications, webhooks, sse, tdd]
dependency_graph:
  requires: []
  provides:
    - tests for FEAT-06 persona sharing
    - tests for FEAT-07 viral card generation
    - tests for FEAT-08 SSE notifications
    - tests for FEAT-09 outbound webhooks
  affects:
    - backend/tests/test_sharing_notifications_webhooks.py
tech_stack:
  added: []
  patterns:
    - pytest-asyncio with httpx AsyncClient + ASGITransport for async route testing
    - patch route-level imports (routes.x.fn) not service-level (services.x.fn)
    - mock _sse_event_generator to prevent infinite stream hang in tests
    - dependency_overrides with try/finally for clean test isolation
key_files:
  created:
    - backend/tests/test_sharing_notifications_webhooks.py
  modified: []
decisions:
  - "Patch route-level imported names (routes.notifications.get_notifications not services.notification_service.get_notifications) because Python binds the name at import time"
  - "Mock _sse_event_generator with a single-yield async generator to prevent the 10s polling loop from hanging the test"
  - "Patch routes.viral_card.db (not database.db) because viral_card.py binds db at import via 'from database import db'"
metrics:
  duration: "17 minutes"
  completed_date: "2026-03-31"
  tasks_completed: 2
  files_modified: 1
---

# Phase 07 Plan 02: Persona Sharing, Viral Card, SSE Notifications, Outbound Webhooks Tests Summary

Automated tests for FEAT-06 through FEAT-09 — persona sharing tokens, viral card analysis, SSE notification streaming, and outbound webhook CRUD.

## What Was Built

**backend/tests/test_sharing_notifications_webhooks.py** (589 lines, 20 tests across 4 classes)

### TestPersonaSharing (5 tests) — FEAT-06

- `test_create_share_returns_token_and_url` — POST /api/persona/share returns `share_token` and `share_url` containing `/creator/`
- `test_create_share_no_persona_returns_404` — 404 when user has no persona engine
- `test_create_share_existing_returns_same_token` — returns existing active share token without creating a duplicate
- `test_get_public_persona_returns_card` — GET /api/persona/public/{token} returns persona card without auth
- `test_get_public_persona_invalid_token_returns_404` — 404 for invalid or missing share token

### TestViralCard (5 tests) — FEAT-07

- `test_analyze_returns_card_with_id_and_share_url` — POST /api/viral-card/analyze returns `card_id` starting with `vc_` and `share_url` containing `/discover/`
- `test_analyze_short_text_returns_400` — 400 when posts_text is fewer than 100 characters
- `test_analyze_invalid_platform_returns_400` — 400 for unsupported platform (e.g. "tiktok")
- `test_get_viral_card_returns_saved_card` — GET /api/viral-card/{card_id} retrieves stored card
- `test_get_viral_card_nonexistent_returns_404` — 404 for non-existent card_id

### TestSSENotifications (5 tests) — FEAT-08

- `test_list_notifications_returns_list_and_count` — GET /api/notifications returns `notifications` list and `count`
- `test_mark_notification_read` — POST /api/notifications/{id}/read returns success message
- `test_mark_all_notifications_read` — POST /api/notifications/read-all returns `updated` count
- `test_get_unread_count` — GET /api/notifications/count returns `unread_count` integer
- `test_sse_stream_returns_text_event_stream` — GET /api/notifications/stream returns `Content-Type: text/event-stream`

### TestOutboundWebhooks (5 tests) — FEAT-09

- `test_create_webhook_returns_id_and_secret` — POST /api/webhooks returns `webhook_id` and `secret` (status 201)
- `test_list_webhooks_returns_webhooks_list` — GET /api/webhooks returns `webhooks` list
- `test_delete_webhook_returns_deleted_true` — DELETE /api/webhooks/{id} returns `deleted: true`
- `test_test_webhook_returns_success` — POST /api/webhooks/{id}/test returns `success: true`
- `test_get_supported_events_includes_job_completed` — GET /api/webhooks/events returns events list including `job.completed`

## Test Results

```
20 passed, 3 warnings in 0.91s
```

All 20 tests pass with 0 failures.

## Decisions Made

1. **Patch route-level imports** — `routes.notifications.get_notifications` not `services.notification_service.get_notifications`. Python binds the function name at import time inside the routes module; patching the service module has no effect on already-imported names.

2. **SSE generator mock** — The real `_sse_event_generator` polls MongoDB every 10 seconds indefinitely. The test mocks it with a single-yield async generator so the stream test completes in milliseconds without hanging.

3. **Viral card db patch** — `routes.viral_card.db` is the correct patch target (not `database.db`) because `viral_card.py` uses `from database import db` which binds the name at import time.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Wrong patch targets caused test failures**
- **Found during:** Task 1 (viral card GET endpoint), Task 2 (notifications, webhooks)
- **Issue:** Plan specified patches like `services.notification_service.get_notifications`. Python's import binding means route handlers use the locally-bound name from `from services.notification_service import get_notifications`, so patching the original module has no effect.
- **Fix:** Changed all patch targets to the route module namespace: `routes.notifications.*`, `routes.webhooks.*`, `routes.viral_card.db`
- **Files modified:** backend/tests/test_sharing_notifications_webhooks.py
- **Commit:** bf04d1f

**2. [Rule 1 - Bug] SSE stream test hung indefinitely**
- **Found during:** Task 2 (SSE notifications)
- **Issue:** The SSE generator polls every 10 seconds in an infinite loop. `client.stream()` hangs waiting for the generator to complete.
- **Fix:** Mocked `routes.notifications._sse_event_generator` with a finite async generator that yields one heartbeat then stops.
- **Files modified:** backend/tests/test_sharing_notifications_webhooks.py
- **Commit:** bf04d1f

## Commits

| Hash | Message |
|------|---------|
| `198702e` | test(07-02): add persona sharing and viral card tests |
| `bf04d1f` | test(07-02): add SSE notifications and outbound webhook tests |

## Self-Check: PASSED
