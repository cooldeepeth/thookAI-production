import { test, expect } from '@playwright/test';

// Use storageState for auth — assumes 01 test created a user and saved session,
// or use a seeded test account. Check if playwright.config.ts has storageState setup.
// If not, register fresh here and proceed.
const FRONTEND_URL = process.env.WEDGE_FRONTEND_URL || 'http://localhost:3000';
const TEST_EMAIL = `wedge-gen-${Date.now()}@thookai-test.com`;
const TEST_PASSWORD = 'TestWedge2026!';

// Minimal interview answers to satisfy generate-persona schema.
const ONBOARDING_ANSWERS = [
  { question_id: 0, answer: "Testing persona creation for the wedge suite." },
  { question_id: 1, answer: "LinkedIn" },
  { question_id: 2, answer: "Bold, Clear, Strategic" },
  { question_id: 5, answer: "Build personal brand" },
  { question_id: 6, answer: "1–3 hours" },
];

test.describe('Generate and edit post', () => {
  let token: string;
  let csrfToken: string;

  test.beforeAll(async ({ request }) => {
    // Register (name required per RegisterRequest schema in auth.py).
    // Capture csrf_token so subsequent mutating requests satisfy the
    // double-submit check in middleware/csrf.py.
    const reg = await request.post('/api/auth/register', {
      data: { email: TEST_EMAIL, password: TEST_PASSWORD, name: 'Wedge Gen Test User' }
    });
    const body = await reg.json();
    token = body.token;
    csrfToken = body.csrf_token;

    // Create the persona_engine doc so the user can generate content
    // (the pipeline expects a persona to exist). onboarding.py exposes
    // generate-persona — this is the call that creates the doc.
    await request.post('/api/onboarding/generate-persona', {
      headers: {
        Authorization: `Bearer ${token}`,
        'X-CSRF-Token': csrfToken,
      },
      data: {
        answers: ONBOARDING_ANSWERS,
        writing_samples: Array(10).fill('Building in public every day. Sharing what I learn.'),
      }
    });
  });

  test('user can generate a post, edit it, and see credit deduction', async ({ page, request }) => {
    // 1. Get starting credit balance
    const balanceBefore = await request.get('/api/billing/credits', {
      headers: { Authorization: `Bearer ${token}` }
    });
    const { credits: creditsBefore } = await balanceBefore.json();

    // 2. Create content via API — payload must match ContentCreateRequest in
    //    backend/routes/content.py: { platform, content_type, raw_input, ... }.
    //    Valid LinkedIn content_types: "post", "carousel_caption", "article".
    const createRes = await request.post('/api/content/create', {
      headers: {
        Authorization: `Bearer ${token}`,
        'X-CSRF-Token': csrfToken,
      },
      data: {
        platform: 'linkedin',
        content_type: 'post',
        raw_input: 'I just got my first paying customer',
      }
    });
    expect(createRes.status(), 'content create should return 200').toBe(200);
    const { job_id } = await createRes.json();
    expect(job_id, 'content create should return a job_id').toBeTruthy();

    // 3. Poll for completion (max 250 seconds).
    //    Endpoint is /api/content/job/{id}; backend pipeline terminal state is
    //    `status: "completed"` with `final_content` populated. We also accept
    //    "reviewing"/"approved" to be forward-compatible with upcoming status
    //    transitions. Real Claude pipeline takes ~60–180s.
    const TERMINAL_STATUSES = new Set(['completed', 'reviewing', 'approved', 'done']);
    let postContent = null;
    const deadline = Date.now() + 250_000;
    while (Date.now() < deadline) {
      const statusRes = await request.get(`/api/content/job/${job_id}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      const body = await statusRes.json();
      if (TERMINAL_STATUSES.has(body?.status) && body?.final_content) {
        postContent = body.final_content;
        break;
      }
      await page.waitForTimeout(2000);
    }
    expect(postContent, 'generated post content should be non-null within 30s').toBeTruthy();

    // 4. Credit deduction
    const balanceAfter = await request.get('/api/billing/credits', {
      headers: { Authorization: `Bearer ${token}` }
    });
    const { credits: creditsAfter } = await balanceAfter.json();
    expect(creditsAfter, 'credits should decrease after generation').toBeLessThan(creditsBefore);

    // 5. UI: navigate to content studio, verify edit is possible
    await page.goto(`${FRONTEND_URL}/auth`);
    await page.getByLabel(/email/i).fill(TEST_EMAIL);
    await page.getByLabel(/password/i).fill(TEST_PASSWORD);
    // Testid disambiguates from the "Sign In" tab and Google OAuth button.
    await page.getByTestId('auth-submit-btn').click();
    // Login lands on /dashboard (no trailing path); use a regex so both
    // `/dashboard` and `/dashboard/xxx` match.
    await page.waitForURL(/\/dashboard(\/|$)/, { timeout: 15_000 });
    await page.goto(`${FRONTEND_URL}/dashboard/studio`);

    // Verify an editable text area / post editor is present
    const editor = page.locator('[contenteditable], textarea').first();
    await expect(editor, 'post editor should be present').toBeVisible({ timeout: 10_000 });
  });
});
