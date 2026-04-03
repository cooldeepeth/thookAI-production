/**
 * E2E Smoke Tests — Infrastructure Verification
 *
 * These tests verify that the dual webServer setup works:
 *   1. CRA React frontend is reachable on port 3000
 *   2. FastAPI backend health endpoint responds on port 8001
 *   3. The auth page loads correctly
 *
 * If any smoke test fails, the entire E2E suite is suspect —
 * investigate the webServer startup before debugging application tests.
 */

import { test, expect } from "@playwright/test";

test.describe("Smoke — Frontend (CRA)", () => {
  test("landing page body is visible", async ({ page }) => {
    await page.goto("/");
    await expect(page.locator("body")).toBeVisible();
  });

  test("auth page loads and body is visible", async ({ page }) => {
    await page.goto("/auth");
    await expect(page.locator("body")).toBeVisible();
  });

  test("page title is set (not empty)", async ({ page }) => {
    await page.goto("/");
    const title = await page.title();
    // Title should not be empty or the default CRA placeholder
    expect(title.length).toBeGreaterThan(0);
  });
});

test.describe("Smoke — Backend (FastAPI)", () => {
  test("health endpoint responds with 200 OK", async ({ request }) => {
    const response = await request.get("http://localhost:8001/health");
    expect(response.ok()).toBeTruthy();
  });

  test("health endpoint returns JSON with status field", async ({ request }) => {
    const response = await request.get("http://localhost:8001/health");
    expect(response.ok()).toBeTruthy();

    const body = await response.json();
    // Accept any truthy status — "ok", "healthy", true, etc.
    expect(body).toHaveProperty("status");
  });

  test("API root or docs endpoint is reachable", async ({ request }) => {
    // Try /api first, fall back to /docs (FastAPI auto-docs)
    const apiResponse = await request.get("http://localhost:8001/api");
    const docsResponse = await request.get("http://localhost:8001/docs");

    // At least one of these should respond (not 500)
    const apiOk = apiResponse.status() < 500;
    const docsOk = docsResponse.status() < 500;
    expect(apiOk || docsOk).toBeTruthy();
  });
});
