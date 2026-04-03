/**
 * Deterministic test data for ThookAI E2E critical path tests.
 *
 * These fixtures are designed for plan 20-03 (E2E-02: Critical Path).
 * All objects are immutable — spread to create overrides if needed.
 *
 * IMPORTANT: TEST_USER.email is generated at import time using Date.now()
 * so each test run gets a unique address with no manual cleanup required.
 */

// ─── User ────────────────────────────────────────────────────────────────────

export interface TestUser {
  readonly email: string;
  readonly password: string;
  readonly name: string;
}

/**
 * Unique test user for the critical path run.
 * Email uses Date.now() so parallel runs never collide.
 */
export const TEST_USER: TestUser = Object.freeze({
  email: `e2e-critical-${Date.now()}@test.io`,
  password: "TestPass123!",
  name: "E2E Critical Path",
});

// ─── Persona ─────────────────────────────────────────────────────────────────

export interface MockPersona {
  readonly user_id: string;
  readonly card: {
    readonly name: string;
    readonly archetype: string;
    readonly voice: string;
    readonly core_topics: readonly string[];
    readonly target_audience: string;
    readonly content_pillars: readonly string[];
  };
  readonly voice_fingerprint: {
    readonly tone: string;
    readonly style: string;
    readonly vocabulary_level: string;
    readonly emoji_usage: string;
    readonly avg_post_length: number;
  };
  readonly content_identity: {
    readonly primary_platform: string;
    readonly posting_frequency: string;
    readonly content_mix: {
      readonly thought_leadership: number;
      readonly personal_stories: number;
      readonly educational: number;
    };
  };
  readonly performance_intelligence: Record<string, never>;
  readonly learning_signals: Record<string, never>;
  readonly uom: {
    readonly success_metric: string;
    readonly target_value: number;
  };
}

/**
 * Minimal valid persona engine matching the schema in CLAUDE.md Section 5.
 * Returned by mockOnboardingLLM when intercepting /api/onboarding/generate-persona.
 */
export const MOCK_PERSONA: MockPersona = Object.freeze({
  user_id: "e2e-test-user-id",
  card: Object.freeze({
    name: "E2E Test User",
    archetype: "The Thought Leader",
    voice: "Authoritative yet approachable",
    core_topics: Object.freeze(["SaaS", "Entrepreneurship", "AI"]),
    target_audience: "Founders and product builders",
    content_pillars: Object.freeze(["Insights", "Behind the scenes", "How-to guides"]),
  }),
  voice_fingerprint: Object.freeze({
    tone: "professional",
    style: "narrative",
    vocabulary_level: "intermediate",
    emoji_usage: "minimal",
    avg_post_length: 280,
  }),
  content_identity: Object.freeze({
    primary_platform: "linkedin",
    posting_frequency: "3x per week",
    content_mix: Object.freeze({
      thought_leadership: 40,
      personal_stories: 30,
      educational: 30,
    }),
  }),
  performance_intelligence: Object.freeze({}),
  learning_signals: Object.freeze({}),
  uom: Object.freeze({
    success_metric: "engagement_rate",
    target_value: 5,
  }),
});

// ─── Content Job ─────────────────────────────────────────────────────────────

export interface MockContentJob {
  readonly job_id: string;
  readonly status: string;
  readonly platform: string;
  readonly content_type: string;
  readonly draft: string;
  readonly final_content: string;
}

/**
 * Mock content job returned by the /api/content/create endpoint.
 * Used in content generation and one-click approve tests.
 */
export const MOCK_CONTENT_JOB: MockContentJob = Object.freeze({
  job_id: "e2e-job-001",
  status: "reviewing",
  platform: "linkedin",
  content_type: "post",
  draft: "AI is transforming content creation...",
  final_content:
    "AI is transforming content creation for creators and founders.",
});

// ─── Schedule Result ──────────────────────────────────────────────────────────

export interface MockScheduleResult {
  readonly schedule_id: string;
  readonly status: string;
  readonly scheduled_at: string;
}

/**
 * Mock scheduling confirmation — returned when a post is scheduled.
 * scheduled_at is tomorrow (24h from import time) in ISO format.
 */
export const MOCK_SCHEDULE_RESULT: MockScheduleResult = Object.freeze({
  schedule_id: "e2e-sched-001",
  status: "scheduled",
  scheduled_at: new Date(Date.now() + 86_400_000).toISOString(),
});

// ─── Strategy Card ────────────────────────────────────────────────────────────

export interface MockStrategyCard {
  readonly recommendation_id: string;
  readonly topic: string;
  readonly signal_source: string;
  readonly why_now: string;
  readonly platform: string;
  readonly status: string;
  readonly hook_options: readonly string[];
  readonly generate_payload: {
    readonly platform: string;
    readonly content_type: string;
    readonly raw_input: string;
  };
  readonly created_at: string;
}

/**
 * Mock strategy recommendation card.
 * Returned by the /api/strategy endpoint in strategy dashboard tests.
 * The why_now text is asserted in the test — do not change without updating assertions.
 */
export const MOCK_STRATEGY_CARD: MockStrategyCard = Object.freeze({
  recommendation_id: "e2e-rec-001",
  topic: "AI content trends",
  signal_source: "trending",
  why_now: "AI content creation is trending on LinkedIn this week",
  platform: "linkedin",
  status: "pending_approval",
  hook_options: Object.freeze([
    "How AI is changing content creation",
    "The future of AI-powered marketing",
  ]),
  generate_payload: Object.freeze({
    platform: "linkedin",
    content_type: "post",
    raw_input: "Write about AI content trends from a founder perspective",
  }),
  created_at: new Date().toISOString(),
});
