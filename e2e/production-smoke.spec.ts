/**
 * Production Smoke Test — PERF-06 / PERF-08
 *
 * Hits the REAL production URL. Zero network interception — no mocks.
 *
 * Required env vars:
 *   PROD_URL             — live frontend URL (e.g. https://thook.ai or a Vercel preview)
 *   SMOKE_USER_EMAIL     — dedicated smoke-test account email
 *   SMOKE_USER_PASSWORD  — that account's password
 *
 * Optional:
 *   PROD_API_URL         — live API base (e.g. https://api.thook.ai). Derived from
 *                          PROD_URL by swapping thook.ai → api.thook.ai if not set.
 *
 * Run (single browser):
 *   PROD_URL=https://thook.ai \
 *   SMOKE_USER_EMAIL=... SMOKE_USER_PASSWORD=... \
 *   npx playwright test e2e/production-smoke.spec.ts --project=chromium
 *
 * Run (all 5 browsers — 20 tests total):
 *   PROD_URL=https://thook.ai \
 *   SMOKE_USER_EMAIL=... SMOKE_USER_PASSWORD=... \
 *   npx playwright test e2e/production-smoke.spec.ts
 *
 * Security (T-35-05-01): credentials are read from env vars only. Never hardcode.
 * Safety (T-35-05-02): use a dedicated smoke-test account with no admin role.
 */

import { test, expect } from "@playwright/test";

const BASE_URL = process.env.PROD_URL || "http://localhost:3000";
const SMOKE_EMAIL = process.env.SMOKE_USER_EMAIL || "";
const SMOKE_PASSWORD = process.env.SMOKE_USER_PASSWORD || "";

test.use({ baseURL: BASE_URL });

// Disable the main playwright.config.ts webServer block for this file —
// production smoke runs against a remote URL, not a local dev stack.
test.describe.configure({ mode: "serial" });

test.beforeAll(async () => {
  if (!process.env.PROD_URL) {
    console.warn(
      "[production-smoke] PROD_URL not set — running against localhost:3000",
    );
  }
  if (!SMOKE_EMAIL || !SMOKE_PASSWORD) {
    throw new Error(
      "SMOKE_USER_EMAIL and SMOKE_USER_PASSWORD must be set for production smoke test",
    );
  }
});

test("smoke-01: landing page loads with key elements", async ({ page }) => {
  await page.goto("/");
  await expect(page).toHaveTitle(/ThookAI|Thook/i);

  // Hero section or Get Started CTA must be visible on initial viewport
  const cta = page
    .getByRole("link", { name: /get started|sign up|try free|start/i })
    .first();
  await expect(cta).toBeVisible({ timeout: 10000 });
});

test("smoke-02: auth page renders and accepts credentials", async ({
  page,
}) => {
  await page.goto("/auth");

  const emailInput = page.locator('input[type="email"]').first();
  await expect(emailInput).toBeVisible({ timeout: 8000 });
  await emailInput.fill(SMOKE_EMAIL);

  const passInput = page.locator('input[type="password"]').first();
  await passInput.fill(SMOKE_PASSWORD);

  const submitBtn = page.locator('button[type="submit"]').first();
  await submitBtn.click();

  // After login, must navigate away from /auth (to /dashboard or /onboarding)
  await expect(page).not.toHaveURL(/\/auth/, { timeout: 15000 });
  console.log(`[smoke-02] Redirected to: ${page.url()}`);
});

test("smoke-03: dashboard or onboarding loads after auth", async ({ page }) => {
  await page.goto("/auth");
  const emailInput = page.locator('input[type="email"]').first();
  await expect(emailInput).toBeVisible({ timeout: 8000 });
  await emailInput.fill(SMOKE_EMAIL);
  await page.locator('input[type="password"]').first().fill(SMOKE_PASSWORD);
  await page.locator('button[type="submit"]').first().click();

  await page.waitForURL(/(dashboard|onboarding)/, { timeout: 20000 });
  console.log(`[smoke-03] Post-login URL: ${page.url()}`);

  // Dashboard nav, onboarding wizard, or any <nav> element must be present
  const dashElement = page
    .getByTestId("sidebar-nav")
    .or(page.getByTestId("onboarding-wizard"))
    .or(page.getByRole("navigation"))
    .or(page.getByTestId("dashboard-layout"));

  await expect(dashElement.first()).toBeVisible({ timeout: 10000 });
});

test("smoke-04: health endpoint is healthy", async ({ request }) => {
  const prodUrl = process.env.PROD_URL || "http://localhost:3000";
  const derivedApi = prodUrl.includes("thook.ai")
    ? prodUrl
        .replace("https://thook.ai", "https://api.thook.ai")
        .replace("https://www.thook.ai", "https://api.thook.ai")
    : "http://localhost:8001";

  const apiBase = process.env.PROD_API_URL || derivedApi;
  console.log(`[smoke-04] API base: ${apiBase}`);

  const response = await request.get(`${apiBase}/health`);
  expect(response.status()).toBe(200);

  const body = await response.json();
  expect(body.status).toBe("ok");
});
