import { test, expect } from '@playwright/test';

const TEST_EMAIL = `wedge-pub-${Date.now()}@thookai-test.com`;
const TEST_PASSWORD = 'TestWedge2026!';

// Minimal interview answers to satisfy generate-persona schema.
const ONBOARDING_ANSWERS = [
  { question_id: 0, answer: "Testing schedule + publish for the wedge suite." },
  { question_id: 1, answer: "LinkedIn" },
  { question_id: 2, answer: "Bold, Clear, Strategic" },
  { question_id: 5, answer: "Build personal brand" },
  { question_id: 6, answer: "1–3 hours" },
];

test.describe('Schedule and publish', () => {
  let token: string;
  let csrfToken: string;
  let postId: string;

  test.beforeAll(async ({ request }) => {
    // Register (name required per RegisterRequest schema in auth.py).
    // Capture csrf_token so subsequent mutating requests satisfy the
    // double-submit check in middleware/csrf.py.
    const reg = await request.post('/api/auth/register', {
      data: { email: TEST_EMAIL, password: TEST_PASSWORD, name: 'Wedge Pub Test User' }
    });
    const regBody = await reg.json();
    token = regBody.token;
    csrfToken = regBody.csrf_token;

    const mutatingHeaders = {
      Authorization: `Bearer ${token}`,
      'X-CSRF-Token': csrfToken,
    };

    // Create persona_engines doc so pipeline/scheduling paths are reachable
    await request.post('/api/onboarding/generate-persona', {
      headers: mutatingHeaders,
      data: {
        answers: ONBOARDING_ANSWERS,
        writing_samples: Array(10).fill('Building in public every day. Sharing what I learn.'),
      }
    });

    // Create a draft post directly (skip generation polling)
    // NOTE: /api/content/draft does NOT exist in backend — this call will 404
    //       and postId will be undefined. Tracked as a Day 3 failure — not fixed
    //       here per "do NOT touch the app" rule.
    const draft = await request.post('/api/content/draft', {
      headers: mutatingHeaders,
      data: { content: 'Test post from wedge Playwright suite.', platform: 'linkedin' }
    });
    postId = (await draft.json()).post_id ?? (await draft.json()).id;
  });

  test('post can be scheduled and appears in queue', async ({ request }) => {
    const futureTime = new Date(Date.now() + 3600_000).toISOString(); // 1h from now

    // Real path is /api/dashboard/schedule/content; real payload is
    // { job_id, scheduled_at, platforms } (ScheduleContentRequest in dashboard.py).
    // The user's spec said `content_id` but the backend field is `job_id`.
    const scheduleRes = await request.post('/api/dashboard/schedule/content', {
      headers: {
        Authorization: `Bearer ${token}`,
        'X-CSRF-Token': csrfToken,
      },
      data: { job_id: postId, scheduled_at: futureTime, platforms: ['linkedin'] }
    });
    expect(scheduleRes.status(), 'schedule should return 200').toBe(200);

    const queueRes = await request.get('/api/dashboard/schedule/upcoming', {
      headers: { Authorization: `Bearer ${token}` }
    });
    expect(queueRes.ok()).toBeTruthy();
    // Response shape: { scheduled: [{ job_id, platform, ... }], total: N }
    const queue = await queueRes.json();
    const items: any[] = Array.isArray(queue) ? queue : (queue?.scheduled ?? queue?.posts ?? []);
    const found = items.some((p: any) => p.job_id === postId || p.id === postId || p.post_id === postId);
    expect(found, 'scheduled post should appear in the queue').toBeTruthy();
  });

  test('publish-now triggers LinkedIn API (mocked) and post appears in history', async ({ request }) => {
    // In test env, the LinkedIn publish call must be mocked — do not hit real LinkedIn.
    // NOTE: /api/content/publish-now does NOT exist in backend. Tracked as a Day 3
    //       failure — user's spec did not provide a replacement path.
    const publishRes = await request.post('/api/content/publish-now', {
      headers: {
        Authorization: `Bearer ${token}`,
        'X-CSRF-Token': csrfToken,
      },
      data: { post_id: postId }
    });
    expect(publishRes.status(), 'publish-now should return 200').toBe(200);
    const publishBody = await publishRes.json();
    expect(publishBody?.published_url ?? publishBody?.url, 'publish should return a URL').toBeTruthy();

    // Real history endpoint is /api/content/jobs which returns { jobs: [...] }.
    const historyRes = await request.get('/api/content/jobs', {
      headers: { Authorization: `Bearer ${token}` }
    });
    expect(historyRes.ok()).toBeTruthy();
    const history = await historyRes.json();
    const items: any[] = Array.isArray(history) ? history : (history?.jobs ?? history?.posts ?? []);
    const published = items.find((p: any) => p.job_id === postId || p.id === postId || p.post_id === postId);
    expect(published, 'post should appear in history').toBeTruthy();
    expect(published?.status, 'post status should be published').toBe('published');
  });
});
