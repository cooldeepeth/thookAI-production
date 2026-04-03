/**
 * Shared Playwright fixtures for ThookAI E2E tests.
 *
 * Exports a custom `test` that extends @playwright/test base with:
 *   - authenticatedPage  — page with a freshly registered user session
 *   - mockPage          — page with all LLM/Stripe mocks pre-applied
 *
 * Usage:
 *   import { test, expect } from '../fixtures';
 *   test('my test', async ({ authenticatedPage }) => { ... });
 */

import { test as base, Page } from "@playwright/test";
import { signUp, getAuthToken, uniqueEmail } from "./helpers/auth";
import { mockLLMResponse, mockStripeCheckout, mockOnboardingLLM } from "./helpers/mock-api";

/** Shape of the fixtures added by this module */
export type ThookAIFixtures = {
  /** A page that has completed sign-up — has a valid auth token in localStorage */
  authenticatedPage: Page;
  /** A page with all LLM, Stripe, and onboarding mocks pre-applied */
  mockPage: Page;
};

export const test = base.extend<ThookAIFixtures>({
  /**
   * authenticatedPage fixture.
   *
   * Registers a brand-new user on each test run (unique email prevents conflicts).
   * After signUp() the page is already redirected to /dashboard or /onboarding.
   */
  authenticatedPage: async ({ page }, use) => {
    const email = uniqueEmail("auth-fixture");
    const password = "TestPassword123!";

    await signUp(page, { email, password, name: "E2E Test User" });

    // Verify we actually got a token — fail fast if auth broke
    const token = await getAuthToken(page);
    if (!token) {
      throw new Error(
        `authenticatedPage fixture: no auth token found after signUp for ${email}. ` +
          "Check that the auth flow stores the JWT in localStorage."
      );
    }

    // Provide the page to the test
    await use(page);
  },

  /**
   * mockPage fixture.
   *
   * Creates a fresh page with all deterministic API mocks pre-applied:
   *   - LLM content generation → returns mock draft
   *   - Stripe checkout → returns mock session URL
   *   - Onboarding persona generation → returns mock persona
   *
   * Does NOT auto-authenticate — tests that need auth should combine with
   * signUp() themselves, or use authenticatedPage instead.
   */
  mockPage: async ({ page }, use) => {
    // Apply all mocks before any navigation
    await mockLLMResponse(page);
    await mockStripeCheckout(page);
    await mockOnboardingLLM(page);

    await use(page);
  },
});

// Re-export expect so tests only need to import from this file
export { expect } from "@playwright/test";
