import { http, HttpResponse } from "msw";

export const handlers = [
  // Auth
  http.get("*/api/auth/me", () =>
    HttpResponse.json({
      user_id: "u1",
      email: "test@example.com",
      subscription_tier: "pro",
      credits: 100,
    }),
  ),
  http.post("*/api/auth/logout", () => HttpResponse.json({ ok: true })),
  // Platforms (Settings → Connections tab)
  http.get("*/api/platforms", () => HttpResponse.json({ platforms: [] })),
  // Billing
  http.get("*/api/billing/subscription", () =>
    HttpResponse.json({
      tier: "free",
      tier_name: "Free",
      credits: 100,
      is_active: true,
      price_monthly: 0,
      cancel_at_period_end: false,
      stripe_status: null,
    }),
  ),
  http.get("*/api/billing/credits", () =>
    HttpResponse.json({
      credits: 80,
      monthly_allowance: 100,
      tier: "pro",
      is_low_balance: false,
    }),
  ),
  // Billing — BillingTab mount in Settings calls these on first render.
  // Without handlers here MSW falls through to a real XHR which is intercepted
  // but never cleanly closed. On Jest worker shutdown libuv panics:
  //   "Assertion failed: (!uv__io_active(...)), function uv__stream_destroy"
  // which hangs CI (Frontend Tests) and makes exit=1. See PR #67 checkpoint.
  // Query-string cache-busters like `?v=2026-04-14` are matched by the `*`
  // prefix — MSW v2 ignores query string in path matching by default.
  http.get("*/api/billing/subscription/tiers", () =>
    HttpResponse.json({ tiers: [] }),
  ),
  http.get("*/api/billing/subscription/limits", () =>
    HttpResponse.json({ limits: {} }),
  ),
  http.get("*/api/billing/config", () =>
    HttpResponse.json({ publishable_key: "pk_test_mock", mode: "test" }),
  ),
  http.get("*/api/billing/credits/costs", () =>
    HttpResponse.json({ costs: {} }),
  ),
  http.post("*/api/billing/plan/preview", () =>
    HttpResponse.json({
      monthly_price: 0,
      credits_total: 0,
      breakdown: {},
    }),
  ),
  // Notifications
  http.get("*/api/notifications", () =>
    HttpResponse.json({ notifications: [] }),
  ),
  http.get("*/api/notifications/count", () =>
    HttpResponse.json({ unread_count: 0 }),
  ),
  http.post("*/api/notifications/:id/read", () =>
    HttpResponse.json({ ok: true }),
  ),
  http.post("*/api/notifications/read-all", () =>
    HttpResponse.json({ ok: true }),
  ),
  // Strategy
  http.get("*/api/strategy", () => HttpResponse.json({ cards: [] })),
  http.post("*/api/strategy/:id/approve", () =>
    HttpResponse.json({ generate_payload: {} }),
  ),
  http.post("*/api/strategy/:id/dismiss", () =>
    HttpResponse.json({ needs_calibration_prompt: false }),
  ),
  // Content
  http.post("*/api/content/generate", () =>
    HttpResponse.json({ job_id: "job-123", status: "processing" }),
  ),
  http.get("*/api/content/job/:id", () =>
    HttpResponse.json({
      job_id: "job-123",
      status: "reviewing",
      draft: "Test content",
    }),
  ),
];
