/**
 * E2E: Content Export Actions (SHIP-01 — Phase 24 download/redirect coverage)
 *
 * Verifies ExportActionsBar behavior:
 *   1. Export bar visible — container renders when final_content exists
 *   2. Download .txt — triggers browser download with correct filename
 *   3. Open in LinkedIn — opens popup with LinkedIn shareArticle URL
 *   4. Open in X — opens popup with twitter intent/tweet URL
 *   5. Instagram info — shows tooltip (no popup, copy-paste flow)
 *
 * All API calls mocked via page.route(). No real network calls.
 * Uses page.waitForEvent('download') and context.waitForEvent('page') — no waitForTimeout.
 *
 * NOTE: The ExportActionsBar renders within ContentStudio after a content job is
 * returned from polling. Tests set up the full generate→poll flow via mocks and
 * wait for ExportActionsBar to become visible before asserting button behaviour.
 *
 * LinkedIn and X buttons are conditionally rendered by platform — separate tests
 * mock different platform values to exercise each branch.
 *
 * Instagram button is a tooltip-only flow (no window.open) — tested with a
 * context.waitForEvent('page', { timeout: 500 }) negative assertion.
 */

import { test, expect, Page } from "@playwright/test";

// ─── Constants ─────────────────────────────────────────────────────────────────

const JOB_ID = "export-test-job-001";
const FINAL_CONTENT =
  "This is a test LinkedIn post about AI content creation. It has enough text to be meaningful and demonstrates the export feature working correctly.";

// ─── Helpers ───────────────────────────────────────────────────────────────────

/**
 * Set up auth state (localStorage token + /api/auth/me mock).
 * All test pages start at /auth to allow localStorage writes before
 * navigating to the actual page.
 */
async function setupAuth(page: Page): Promise<void> {
  await page.goto("/auth");
  await page.evaluate(() => {
    localStorage.setItem("thook_token", "e2e-export-mock-jwt");
  });

  await page.route("**/api/auth/me", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        user_id: "export-user-001",
        email: "export@thookai.test",
        name: "Export Tester",
        subscription_tier: "pro",
        credits: 100,
        onboarding_completed: true,
      }),
    })
  );
}

/**
 * Mock the content creation + polling flow so ContentStudio immediately
 * renders ContentOutput (and therefore ExportActionsBar) after Generate is clicked.
 *
 * @param page     - Playwright page
 * @param platform - Content platform: "linkedin" | "x" | "instagram"
 */
async function mockContentFlow(page: Page, platform: string): Promise<void> {
  // POST /api/content/create → returns job_id immediately
  await page.route("**/api/content/create", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ job_id: JOB_ID }),
    })
  );

  // GET /api/content/job/:id → returns approved job with final_content
  await page.route(`**/api/content/job/${JOB_ID}`, (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        job_id: JOB_ID,
        platform,
        status: "approved",
        draft: FINAL_CONTENT,
        final_content: FINAL_CONTENT,
        edited_content: null,
        was_edited: false,
        media_assets: [],
        carousel: null,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      }),
    })
  );

  // GET /api/billing/credits — needed by ContentStudio to fetch user tier
  await page.route("**/api/billing/credits", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ credits: 100, tier: "pro", credit_allowance: 500 }),
    })
  );

  // GET /api/dashboard/** — catch-all for dashboard stats
  await page.route("**/api/dashboard/**", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        total_posts: 5,
        scheduled_posts: 1,
        credits_remaining: 100,
        subscription_tier: "pro",
        recent_content: [],
        recommendations: [],
      }),
    })
  );
}

/**
 * Navigate to /dashboard/studio with the given platform pre-selected,
 * trigger content generation (mocked), and wait for ExportActionsBar
 * to become visible.
 *
 * Returns after the export bar is confirmed visible.
 */
async function generateContentAndWaitForExportBar(
  page: Page,
  platform: string
): Promise<void> {
  await page.goto(`/dashboard/studio?platform=${platform}`);
  await page.waitForSelector('[data-testid="input-panel"]', { timeout: 10000 });

  // Fill in a topic
  await page.locator('[data-testid="content-input-textarea"]').fill(
    "E2E export test content"
  );

  // Race: set up waitForResponse BEFORE clicking to avoid missing a fast mock response
  const [createResponse] = await Promise.all([
    page.waitForResponse(
      (resp) => resp.url().includes("/api/content/create"),
      { timeout: 10000 }
    ),
    page.locator('[data-testid="generate-content-btn"]').click(),
  ]);

  // Verify content creation succeeded
  if (createResponse.status() >= 400) {
    throw new Error(`Content create returned ${createResponse.status()}`);
  }

  // Wait for ExportActionsBar container to be visible (polls job → returns approved)
  await page.locator('[data-testid="export-actions-bar"]').waitFor({
    state: "visible",
    timeout: 15000,
  });
}

// ─── Tests ────────────────────────────────────────────────────────────────────

test.describe("Export Actions Bar", () => {

  // ---------------------------------------------------------------------------
  // Test 1: Export bar visible when final_content exists
  // ---------------------------------------------------------------------------
  test("export-actions-bar container is visible when final_content exists", async ({ page }) => {
    await setupAuth(page);
    await mockContentFlow(page, "linkedin");
    await generateContentAndWaitForExportBar(page, "linkedin");

    await expect(page.locator('[data-testid="export-actions-bar"]')).toBeVisible();
  });

  // ---------------------------------------------------------------------------
  // Test 2: Download .txt triggers a file download
  // ---------------------------------------------------------------------------
  test("clicking Download .txt triggers a file download", async ({ page }) => {
    await setupAuth(page);
    await mockContentFlow(page, "linkedin");
    await generateContentAndWaitForExportBar(page, "linkedin");

    // Listen for download event and click the Download .txt button simultaneously
    const [download] = await Promise.all([
      page.waitForEvent("download"),
      page.getByRole("button", { name: /download \.txt/i }).click(),
    ]);

    // Filename should match: linkedin-YYYY-MM-DD.txt
    const filename = download.suggestedFilename();
    expect(filename).toMatch(/^linkedin-\d{4}-\d{2}-\d{2}\.txt$/);
  });

  // ---------------------------------------------------------------------------
  // Test 3: Open in LinkedIn opens a new tab with LinkedIn shareArticle URL
  // ---------------------------------------------------------------------------
  test("clicking Open in LinkedIn opens a new tab with LinkedIn shareArticle URL", async ({ page, context }) => {
    await setupAuth(page);
    await mockContentFlow(page, "linkedin");
    await generateContentAndWaitForExportBar(page, "linkedin");

    // Wait for the Open in LinkedIn button and the popup simultaneously
    const [popup] = await Promise.all([
      context.waitForEvent("page"),
      page.getByRole("button", { name: /open in linkedin/i }).click(),
    ]);

    await popup.waitForLoadState("domcontentloaded");
    // LinkedIn redirects unauthenticated users to /uas/login?session_redirect=...shareArticle...
    // Either the direct shareArticle URL or the login redirect (both confirm correct target URL)
    const popupUrl = popup.url();
    expect(popupUrl).toMatch(/linkedin\.com/);
    expect(decodeURIComponent(popupUrl)).toMatch(/shareArticle/);
  });

  // ---------------------------------------------------------------------------
  // Test 4: Open in X opens a new tab with twitter intent URL
  // ---------------------------------------------------------------------------
  test("clicking Open in X opens a new tab with twitter intent URL", async ({ page, context }) => {
    await setupAuth(page);
    await mockContentFlow(page, "x");
    await generateContentAndWaitForExportBar(page, "x");

    // Wait for the Open in X button and the popup simultaneously
    const [popup] = await Promise.all([
      context.waitForEvent("page"),
      page.getByRole("button", { name: /open in x/i }).click(),
    ]);

    await popup.waitForLoadState("domcontentloaded");
    // twitter.com/intent/tweet redirects to x.com/intent/tweet (Twitter → X rebrand)
    // Accept either domain since browsers follow the redirect
    expect(popup.url()).toMatch(/(twitter|x)\.com\/intent\/tweet/);
  });

  // ---------------------------------------------------------------------------
  // Test 5: Instagram info shows tooltip (no popup)
  // ---------------------------------------------------------------------------
  test("clicking Post to Instagram shows tooltip without opening a popup", async ({ page, context }) => {
    await setupAuth(page);
    await mockContentFlow(page, "instagram");
    await generateContentAndWaitForExportBar(page, "instagram");

    // Click the Instagram info button
    await page.getByRole("button", { name: /post to instagram/i }).click();

    // Verify no popup opens — context.waitForEvent('page') throws on timeout, catch it
    let popupOpened = false;
    await context
      .waitForEvent("page", { timeout: 500 })
      .then(() => { popupOpened = true; })
      .catch(() => { /* timeout — no popup opened, as expected */ });

    expect(popupOpened).toBe(false);

    // Tooltip text should be visible after clicking
    await expect(page.getByText("Instagram has no web compose URL")).toBeVisible({
      timeout: 3000,
    });
  });

});
