/**
 * E2E auth helpers for ThookAI tests.
 *
 * Provides signUp, logIn, and getAuthToken utilities.
 * All wait with semantic waitForURL / waitForSelector — never waitForTimeout.
 */

import { Page } from "@playwright/test";

export interface AuthCredentials {
  email: string;
  password: string;
  name?: string;
}

/**
 * Navigate to /auth, switch to Sign Up mode, fill the form, and submit.
 * Waits for redirect to /dashboard (or /onboarding for new accounts).
 */
export async function signUp(
  page: Page,
  { email, password, name = "Test User" }: AuthCredentials
): Promise<void> {
  await page.goto("/auth");

  // Switch to sign-up tab/mode if needed
  const signUpTab = page.locator('[data-testid="signup-tab"], button:has-text("Sign up"), a:has-text("Sign up"), [role="tab"]:has-text("Sign up")');
  if (await signUpTab.count() > 0) {
    await signUpTab.first().click();
  }

  // Fill the name field if visible
  const nameField = page.locator('input[name="name"], input[placeholder*="Name"], input[placeholder*="name"]');
  if (await nameField.count() > 0) {
    await nameField.first().fill(name);
  }

  await page.locator('input[name="email"], input[type="email"]').first().fill(email);
  await page.locator('input[name="password"], input[type="password"]').first().fill(password);

  // Submit the form
  await page.locator('button[type="submit"], button:has-text("Sign up"), button:has-text("Create account")').first().click();

  // Wait for post-signup redirect (dashboard or onboarding)
  await page.waitForURL(/\/(dashboard|onboarding)/, { timeout: 30000 });
}

/**
 * Navigate to /auth, fill the login form, and submit.
 * Waits for redirect to /dashboard.
 */
export async function logIn(
  page: Page,
  { email, password }: AuthCredentials
): Promise<void> {
  await page.goto("/auth");

  // Switch to sign-in tab/mode if needed
  const signInTab = page.locator('[data-testid="signin-tab"], button:has-text("Sign in"), a:has-text("Sign in"), a:has-text("Log in"), [role="tab"]:has-text("Sign in")');
  if (await signInTab.count() > 0) {
    await signInTab.first().click();
  }

  await page.locator('input[name="email"], input[type="email"]').first().fill(email);
  await page.locator('input[name="password"], input[type="password"]').first().fill(password);

  await page.locator('button[type="submit"], button:has-text("Sign in"), button:has-text("Log in")').first().click();

  await page.waitForURL("**/dashboard**", { timeout: 30000 });
}

/**
 * Return the JWT token stored in localStorage by the React app.
 * Returns null if not authenticated.
 */
export async function getAuthToken(page: Page): Promise<string | null> {
  return page.evaluate(() => {
    return (
      localStorage.getItem("token") ||
      localStorage.getItem("access_token") ||
      localStorage.getItem("authToken") ||
      null
    );
  });
}

/**
 * Generate a unique test email using a timestamp to avoid collisions.
 */
export function uniqueEmail(prefix = "e2e"): string {
  return `${prefix}-${Date.now()}-${Math.floor(Math.random() * 9999)}@thookai-test.invalid`;
}
