import { test, expect } from '@playwright/test';

// Project baseURL points at the API origin so `request.*` relative paths resolve
// to the backend. UI navigation (page.goto) needs the frontend origin instead.
const FRONTEND_URL = process.env.WEDGE_FRONTEND_URL || 'http://localhost:3000';

const TEST_EMAIL = `wedge-test-${Date.now()}@thookai-test.com`;
const TEST_PASSWORD = 'TestWedge2026!';
const SAMPLE_POSTS = [
  "Shipped our MVP today. 6 months of nights and weekends. Zero external validation until now. Terrifying and exciting.",
  "Failed my first sales call badly. Talked about features for 20 min. Never asked what problem they had. Starting over.",
  "We hit $1k MRR. It's small. But it's real money from real people. Everything changes when it's real.",
  "Hot take: most SaaS pricing pages are designed to confuse, not convert. Transparency wins.",
  "Hired our first contractor. Realised I had no idea how to delegate. Week 1 was chaos. Week 3 is better.",
  "Our biggest churn reason: users didn't understand the value fast enough. Onboarding rewrite starts Monday.",
  "Three things I wish someone told me before I started building: 1. Talk to users first. 2. Ship ugly. 3. Charge early.",
  "Turned down a VC intro today. Not the right time. Maybe not the right path. Still processing that.",
  "Our NPS went from 12 to 41 in 60 days. The only thing we changed was response time on support.",
  "Building in public is uncomfortable. You celebrate wins that feel small. You admit failures publicly. Worth it.",
];

// Minimal interview answers — satisfies the generate-persona schema
// (answers: List[Dict] with question_id + answer). Question IDs match
// backend/routes/onboarding.py:INTERVIEW_QUESTIONS.
const ONBOARDING_ANSWERS = [
  { question_id: 0, answer: "I'm a solo founder building ThookAI — helping creators post in their authentic voice." },
  { question_id: 1, answer: "LinkedIn" },
  { question_id: 2, answer: "Bold, Clear, Strategic" },
  { question_id: 3, answer: "Paul Graham for clarity. Lenny Rachitsky for depth." },
  { question_id: 4, answer: "Hustle culture, crypto speculation, vague motivation." },
  { question_id: 5, answer: "Build personal brand" },
  { question_id: 6, answer: "1–3 hours" },
];

test.describe('Register and onboard', () => {
  test('new user can register, onboard with 10 posts, and land on Content Studio', async ({ page, request }) => {
    // 1. Register via API (backend requires name — see auth.py RegisterRequest).
    //    Register sets session_token + csrf_token cookies and returns csrf_token
    //    in the body. Since Playwright's APIRequestContext replays cookies, every
    //    subsequent mutating request must also send X-CSRF-Token (double-submit
    //    cookie pattern enforced by middleware/csrf.py).
    const registerRes = await request.post('/api/auth/register', {
      data: { email: TEST_EMAIL, password: TEST_PASSWORD, name: 'Wedge Test User' }
    });
    expect(registerRes.status(), 'registration should return 200').toBe(200);
    const { token, csrf_token: csrfToken } = await registerRes.json();
    expect(token, 'registration should return a JWT').toBeTruthy();
    expect(csrfToken, 'registration should return a csrf_token').toBeTruthy();

    const authHeaders = {
      Authorization: `Bearer ${token}`,
      'X-CSRF-Token': csrfToken,
    };

    // 2a. Analyze writing samples — prerequisite that seeds posts_analysis for step 2b
    const analyzeRes = await request.post('/api/onboarding/analyze-posts', {
      headers: authHeaders,
      data: { posts_text: SAMPLE_POSTS.join('\n\n'), platform: 'linkedin' }
    });
    expect(analyzeRes.status(), 'analyze-posts should return 200').toBe(200);
    const { analysis } = await analyzeRes.json();

    // 2b. Generate persona — this is the call that creates the persona_engines document
    const personaGenRes = await request.post('/api/onboarding/generate-persona', {
      headers: authHeaders,
      data: {
        answers: ONBOARDING_ANSWERS,
        posts_analysis: analysis,
        writing_samples: SAMPLE_POSTS,
      }
    });
    expect(personaGenRes.status(), 'generate-persona should return 200').toBe(200);

    // 3. Poll persona document — the stored doc has `voice_fingerprint`
    //    (not `voice_profile`; see onboarding.py persona_doc shape).
    let voiceFingerprint = null;
    const deadline = Date.now() + 60_000;
    while (Date.now() < deadline) {
      const personaRes = await request.get('/api/persona/me', {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (personaRes.ok()) {
        const body = await personaRes.json();
        if (body?.voice_fingerprint) { voiceFingerprint = body.voice_fingerprint; break; }
      }
      await page.waitForTimeout(3000);
    }
    expect(voiceFingerprint, 'persona voice_fingerprint should be non-null within 60s').toBeTruthy();

    // 4. UI: log in and verify the user lands in the dashboard, then
    //    navigate to Content Studio (login redirects to /dashboard, not
    //    /dashboard/studio, by design — the studio is a sub-route).
    await page.goto(`${FRONTEND_URL}/auth`);
    await page.getByLabel(/email/i).fill(TEST_EMAIL);
    await page.getByLabel(/password/i).fill(TEST_PASSWORD);
    // Use data-testid to avoid strict-mode matches against the "Sign In" tab
    // and Google OAuth button which share the visible label.
    await page.getByTestId('auth-submit-btn').click();
    await page.waitForURL('**/dashboard', { timeout: 15_000 });
    await page.goto(`${FRONTEND_URL}/dashboard/studio`);
    await expect(page).toHaveURL(/dashboard\/studio/);
  });
});
