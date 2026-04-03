/**
 * E2E API route mocking helpers for ThookAI.
 *
 * Uses Playwright's page.route() for request interception.
 * These mocks produce deterministic, fast responses that avoid hitting
 * real LLM or Stripe APIs during E2E tests.
 *
 * All mock helpers are composable — call multiple on the same page.
 */

import { Page } from "@playwright/test";

/** Represents the mock content generation response */
export interface MockContentResponse {
  job_id: string;
  status: string;
  draft: string;
  platform: string;
  content_type: string;
}

/**
 * Intercept POST /api/content/generate and return a deterministic mock.
 * The mock draft is injected to verify the response is displayed in the UI.
 */
export async function mockLLMResponse(
  page: Page,
  overrides: Partial<MockContentResponse> = {}
): Promise<void> {
  const mockResponse: MockContentResponse = {
    job_id: `mock-job-${Date.now()}`,
    status: "reviewing",
    draft: "This is a mock AI-generated LinkedIn post about building in public. #BuildInPublic #SaaS",
    platform: "linkedin",
    content_type: "post",
    ...overrides,
  };

  await page.route("**/api/content/generate", (route) => {
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(mockResponse),
    });
  });

  // Also intercept the polling endpoint for job status
  await page.route("**/api/content/jobs/**", (route) => {
    const jobId = overrides.job_id ?? mockResponse.job_id;
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        job_id: jobId,
        status: "reviewing",
        draft: mockResponse.draft,
        platform: mockResponse.platform,
        content_type: mockResponse.content_type,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      }),
    });
  });
}

/**
 * Intercept POST /api/billing/checkout and return a mock Stripe session.
 * Prevents real Stripe API calls during E2E tests.
 */
export async function mockStripeCheckout(
  page: Page,
  sessionUrl = "https://checkout.stripe.com/pay/cs_test_mock"
): Promise<void> {
  await page.route("**/api/billing/checkout", (route) => {
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        checkout_url: sessionUrl,
        session_id: "cs_test_mock_session_id",
      }),
    });
  });

  // Also intercept /api/billing/create-checkout-session (alternative path)
  await page.route("**/api/billing/create-checkout-session", (route) => {
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        checkout_url: sessionUrl,
        session_id: "cs_test_mock_session_id",
      }),
    });
  });
}

/**
 * Intercept POST /api/onboarding/generate-persona and return a mock persona.
 * Prevents calling the real Claude API during onboarding E2E tests.
 */
export async function mockOnboardingLLM(page: Page): Promise<void> {
  const mockPersona = {
    user_id: "mock-user-id",
    card: {
      name: "E2E Test User",
      archetype: "The Thought Leader",
      voice: "Authoritative yet approachable",
      core_topics: ["SaaS", "Entrepreneurship", "AI"],
      target_audience: "Founders and product builders",
      content_pillars: ["Insights", "Behind the scenes", "How-to guides"],
    },
    voice_fingerprint: {
      tone: "professional",
      style: "narrative",
      vocabulary_level: "intermediate",
      emoji_usage: "minimal",
      avg_post_length: 280,
    },
    content_identity: {
      primary_platform: "linkedin",
      posting_frequency: "3x per week",
      content_mix: {
        thought_leadership: 40,
        personal_stories: 30,
        educational: 30,
      },
    },
    performance_intelligence: {},
    learning_signals: {},
    uom: {
      success_metric: "engagement_rate",
      target_value: 5,
    },
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  };

  await page.route("**/api/onboarding/generate-persona", (route) => {
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(mockPersona),
    });
  });

  // Also intercept the full onboarding submit endpoint
  await page.route("**/api/onboarding/complete", (route) => {
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        success: true,
        persona_engine: mockPersona,
        message: "Persona created successfully",
      }),
    });
  });
}

/**
 * Intercept dashboard stats endpoint to return predictable counts.
 * Prevents flaky tests from real DB state variance.
 */
export async function mockDashboardStats(page: Page): Promise<void> {
  await page.route("**/api/dashboard/**", (route) => {
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        total_posts: 12,
        scheduled_posts: 3,
        credits_remaining: 80,
        subscription_tier: "pro",
        recent_content: [],
        recommendations: [],
      }),
    });
  });
}
