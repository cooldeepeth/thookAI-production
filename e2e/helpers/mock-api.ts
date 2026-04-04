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

// ===== BILLING MOCK TYPES =====

export interface MockSubscription {
  subscription_tier: string;
  credits: number;
  status: string;
  plan_config?: Record<string, unknown> | null;
  stripe_status?: string | null;
  cancel_at_period_end?: boolean;
}

export interface MockCredits {
  credits: number;
  tier: string;
  credit_allowance?: number;
}

// ===== AGENCY MOCK TYPES =====

export interface MockWorkspace {
  workspace_id: string;
  name: string;
  owner_id: string;
  role: string;
  member_count: number;
  content_count: number;
  description?: string;
  created_at: string;
  updated_at: string;
  settings: Record<string, unknown>;
}

export interface MockWorkspaceMember {
  user_id: string;
  email: string;
  name: string;
  role: string;
  status: string;
  joined_at: string;
  invite_id?: string;
}

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

// ===== BILLING MOCKS =====

/**
 * Intercept all billing-related API endpoints with sensible defaults.
 *
 * Covers:
 *   GET  /api/billing/subscription  — free tier user
 *   POST /api/billing/plan/checkout — returns mock Stripe checkout URL
 *   GET  /api/billing/credits       — 100 credits remaining
 *   POST /api/billing/portal        — returns mock Stripe portal URL
 *   GET  /api/billing/config        — minimal config
 *   GET  /api/billing/subscription/tiers — available plan tiers
 *   GET  /api/billing/subscription/limits — feature limits
 *   GET  /api/billing/credits/costs  — credit costs per operation
 */
export async function mockBillingEndpoints(page: Page): Promise<void> {
  // GET subscription status
  await page.route("**/api/billing/subscription", (route) => {
    if (route.request().method() === "GET") {
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          subscription_tier: "free",
          credits: 100,
          status: "active",
          credit_allowance: 100,
          plan_config: null,
          stripe_status: null,
          cancel_at_period_end: false,
        }),
      });
    } else {
      route.continue();
    }
  });

  // POST plan checkout — returns a mock Stripe checkout URL
  await page.route("**/api/billing/plan/checkout", (route) => {
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        success: true,
        checkout_url: "https://checkout.stripe.com/pay/cs_test_mock_session_123",
        session_id: "cs_test_mock_session_123",
      }),
    });
  });

  // Also intercept legacy /api/billing/checkout path
  await page.route("**/api/billing/checkout", (route) => {
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        success: true,
        checkout_url: "https://checkout.stripe.com/pay/cs_test_mock_session_123",
        session_id: "cs_test_mock_session_123",
      }),
    });
  });

  // GET credits balance
  await page.route("**/api/billing/credits", (route) => {
    if (route.request().method() === "GET") {
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          credits: 100,
          tier: "free",
          credit_allowance: 100,
        }),
      });
    } else {
      route.continue();
    }
  });

  // POST customer portal
  await page.route("**/api/billing/portal", (route) => {
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        success: true,
        portal_url: "https://billing.stripe.com/test_portal_session",
      }),
    });
  });

  // GET billing config
  await page.route("**/api/billing/config", (route) => {
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        publishable_key: "pk_test_mock",
        is_configured: true,
      }),
    });
  });

  // GET subscription tiers
  await page.route("**/api/billing/subscription/tiers", (route) => {
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        current_tier: "free",
        available_tiers: [
          { tier: "free", name: "Free", credits: 30, price: 0 },
          { tier: "pro", name: "Pro", credits: 500, price: 29 },
          { tier: "studio", name: "Studio", credits: 1500, price: 79 },
          { tier: "agency", name: "Agency", credits: 5000, price: 199 },
        ],
      }),
    });
  });

  // GET feature limits
  await page.route("**/api/billing/subscription/limits", (route) => {
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        tier: "free",
        limits: {
          daily_posts: 1,
          monthly_credits: 30,
          workspaces: 0,
          team_members: 1,
        },
      }),
    });
  });

  // GET credit costs
  await page.route("**/api/billing/credits/costs", (route) => {
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        costs: {
          content_create: { credits: 10, name: "Content Creation" },
          image_generate: { credits: 8, name: "Image Generation" },
          repurpose: { credits: 3, name: "Repurpose" },
        },
      }),
    });
  });

  // GET plan preview
  await page.route("**/api/billing/plan/preview", (route) => {
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        success: true,
        total_credits: 100,
        monthly_price_usd: 14.99,
        volume_tier: "starter",
        price_per_credit: 0.15,
        features: { team_members: 1 },
      }),
    });
  });

  // Block any accidental navigation to real Stripe
  await page.route("**/checkout.stripe.com/**", (route) => {
    route.fulfill({
      status: 200,
      contentType: "text/html",
      body: "<html><body>Mock Stripe Checkout Page</body></html>",
    });
  });

  await page.route("**/billing.stripe.com/**", (route) => {
    route.fulfill({
      status: 200,
      contentType: "text/html",
      body: "<html><body>Mock Stripe Portal Page</body></html>",
    });
  });
}

/**
 * Override the subscription endpoint to simulate an active paid subscription.
 *
 * Call after mockBillingEndpoints() to override the subscription response.
 * Used to simulate post-checkout state where user has upgraded to `tier`.
 *
 * @param page - Playwright page
 * @param tier - Subscription tier ('pro' | 'studio' | 'agency' | 'custom')
 */
export async function mockSubscriptionActive(
  page: Page,
  tier: string
): Promise<void> {
  const creditsByTier: Record<string, number> = {
    pro: 500,
    studio: 1500,
    agency: 5000,
    custom: 300,
  };

  const credits = creditsByTier[tier] ?? 100;

  await page.route("**/api/billing/subscription", (route) => {
    if (route.request().method() === "GET") {
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          subscription_tier: tier,
          credits,
          status: "active",
          credit_allowance: credits,
          plan_config: null,
          stripe_status: "active",
          cancel_at_period_end: false,
        }),
      });
    } else {
      route.continue();
    }
  });

  // Also update the credits endpoint to reflect new tier
  await page.route("**/api/billing/credits", (route) => {
    if (route.request().method() === "GET") {
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          credits,
          tier,
          credit_allowance: credits,
        }),
      });
    } else {
      route.continue();
    }
  });
}

/**
 * Override the credits endpoint to simulate credit deduction.
 *
 * @param page - Playwright page
 * @param remaining - Credits remaining after deduction
 */
export async function mockCreditDeduction(
  page: Page,
  remaining: number
): Promise<void> {
  await page.route("**/api/billing/credits", (route) => {
    if (route.request().method() === "GET") {
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          credits: remaining,
          tier: "pro",
          credit_allowance: 500,
        }),
      });
    } else {
      route.continue();
    }
  });
}

// ===== AGENCY MOCKS =====

const E2E_WORKSPACE: MockWorkspace = {
  workspace_id: "ws-e2e-001",
  name: "E2E Agency",
  owner_id: "user-e2e-owner",
  role: "owner",
  member_count: 1,
  content_count: 0,
  description: "E2E test workspace",
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
  settings: {
    allow_member_publish: false,
    require_approval: true,
    default_platforms: ["linkedin"],
  },
};

const E2E_MEMBERS: MockWorkspaceMember[] = [
  {
    user_id: "user-e2e-owner",
    email: "owner-e2e@test.io",
    name: "E2E Owner",
    role: "owner",
    status: "active",
    joined_at: new Date().toISOString(),
  },
];

/**
 * Intercept all agency workspace API endpoints with deterministic mocks.
 *
 * Covers:
 *   POST /api/agency/workspace            — create workspace
 *   GET  /api/agency/workspaces           — list user workspaces
 *   POST /api/agency/workspace/:id/invite — invite member
 *   GET  /api/agency/workspace/:id/members — list members
 *   GET  /api/agency/workspace/:id/creators — list creators
 */
export async function mockAgencyEndpoints(page: Page): Promise<void> {
  // POST create workspace
  await page.route("**/api/agency/workspace", (route) => {
    if (route.request().method() === "POST") {
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          workspace_id: E2E_WORKSPACE.workspace_id,
          name: E2E_WORKSPACE.name,
          message: "Workspace created successfully",
        }),
      });
    } else {
      route.continue();
    }
  });

  // GET list workspaces
  await page.route("**/api/agency/workspaces", (route) => {
    if (route.request().method() === "GET") {
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          owned: [E2E_WORKSPACE],
          member_of: [],
          total: 1,
        }),
      });
    } else {
      route.continue();
    }
  });

  // POST invite member to workspace
  await page.route("**/api/agency/workspace/*/invite", (route) => {
    if (route.request().method() === "POST") {
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          invite_id: "inv-e2e-001",
          email: "member-e2e@test.io",
          status: "pending",
          message: "Invitation sent to member-e2e@test.io",
        }),
      });
    } else {
      route.continue();
    }
  });

  // GET workspace members
  await page.route("**/api/agency/workspace/*/members", (route) => {
    if (route.request().method() === "GET") {
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          members: E2E_MEMBERS,
          total: E2E_MEMBERS.length,
        }),
      });
    } else {
      route.continue();
    }
  });

  // GET workspace creators
  await page.route("**/api/agency/workspace/*/creators", (route) => {
    if (route.request().method() === "GET") {
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          creators: [],
          total: 0,
        }),
      });
    } else {
      route.continue();
    }
  });

  // GET single workspace detail
  await page.route("**/api/agency/workspace/ws-e2e-001", (route) => {
    if (route.request().method() === "GET") {
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          workspace: { ...E2E_WORKSPACE, user_role: "owner" },
        }),
      });
    } else {
      route.continue();
    }
  });
}

/**
 * Mock workspace context — intercepts requests to include workspace scoping.
 *
 * In the ThookAI frontend, workspace context is passed via the Authorization
 * header (JWT already contains user_id). The mock simulates a user who is
 * already a member of the given workspace.
 *
 * @param page - Playwright page
 * @param workspaceId - Workspace ID to scope to
 */
export async function mockWorkspaceContext(
  page: Page,
  workspaceId: string
): Promise<void> {
  // Override workspaces list to include the given workspace as a member
  await page.route("**/api/agency/workspaces", (route) => {
    if (route.request().method() === "GET") {
      const workspace: MockWorkspace = {
        ...E2E_WORKSPACE,
        workspace_id: workspaceId,
        role: "creator",
      };
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          owned: [],
          member_of: [workspace],
          total: 1,
        }),
      });
    } else {
      route.continue();
    }
  });
}

/**
 * Mock all endpoints needed to render a ContentOutput page with
 * an approved content job that has final_content set — this makes
 * ExportActionsBar visible in the DOM.
 *
 * Mocks:
 *   GET /api/auth/me           → authenticated user
 *   GET /api/content/:job_id   → approved job with final_content
 *   GET /api/dashboard/stats   → minimal stats (so Dashboard loads)
 */
export async function mockExportContent(
  page: Page,
  options: { jobId?: string; platform?: string; finalContent?: string } = {}
): Promise<void> {
  const jobId = options.jobId ?? "export-test-job-001";
  const platform = options.platform ?? "linkedin";
  const finalContent =
    options.finalContent ??
    "This is a test LinkedIn post about AI content creation. It has enough text to be meaningful and demonstrates the export feature working correctly.";

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

  await page.route(`**/api/content/${jobId}`, (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        job_id: jobId,
        platform,
        status: "approved",
        draft: finalContent,
        final_content: finalContent,
        edited_content: null,
        was_edited: false,
        media_assets: [],
        carousel: null,
        created_at: new Date().toISOString(),
      }),
    })
  );

  await page.route("**/api/dashboard/stats", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        total_posts: 5,
        total_credits: 100,
        platforms_connected: 1,
      }),
    })
  );
}
