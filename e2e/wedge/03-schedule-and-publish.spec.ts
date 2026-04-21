import { test, expect } from '@playwright/test';

const TEST_EMAIL = `wedge-pub-${Date.now()}@thookai-test.com`;
const TEST_PASSWORD = 'TestWedge2026!';

test.describe('Schedule and publish', () => {
  let token: string;
  let postId: string;

  test.beforeAll(async ({ request }) => {
    const reg = await request.post('/api/auth/register', {
      data: { email: TEST_EMAIL, password: TEST_PASSWORD }
    });
    token = (await reg.json()).token;
    await request.post('/api/onboarding/posts', {
      headers: { Authorization: `Bearer ${token}` },
      data: { posts: Array(10).fill('Building in public every day. Sharing what I learn.') }
    });
    // Create a draft post directly (skip generation polling)
    const draft = await request.post('/api/content/draft', {
      headers: { Authorization: `Bearer ${token}` },
      data: { content: 'Test post from wedge Playwright suite.', platform: 'linkedin' }
    });
    postId = (await draft.json()).post_id ?? (await draft.json()).id;
  });

  test('post can be scheduled and appears in queue', async ({ request }) => {
    const futureTime = new Date(Date.now() + 3600_000).toISOString(); // 1h from now
    const scheduleRes = await request.post('/api/content/schedule', {
      headers: { Authorization: `Bearer ${token}` },
      data: { post_id: postId, scheduled_at: futureTime }
    });
    expect(scheduleRes.status(), 'schedule should return 200').toBe(200);

    const queueRes = await request.get('/api/content/scheduled', {
      headers: { Authorization: `Bearer ${token}` }
    });
    expect(queueRes.ok()).toBeTruthy();
    const queue = await queueRes.json();
    const found = Array.isArray(queue)
      ? queue.some((p: any) => p.id === postId || p.post_id === postId)
      : queue?.posts?.some((p: any) => p.id === postId || p.post_id === postId);
    expect(found, 'scheduled post should appear in the queue').toBeTruthy();
  });

  test('publish-now triggers LinkedIn API (mocked) and post appears in history', async ({ request }) => {
    // In test env, the LinkedIn publish call must be mocked — do not hit real LinkedIn
    const publishRes = await request.post('/api/content/publish-now', {
      headers: { Authorization: `Bearer ${token}` },
      data: { post_id: postId }
    });
    expect(publishRes.status(), 'publish-now should return 200').toBe(200);
    const publishBody = await publishRes.json();
    expect(publishBody?.published_url ?? publishBody?.url, 'publish should return a URL').toBeTruthy();

    const historyRes = await request.get('/api/content/history', {
      headers: { Authorization: `Bearer ${token}` }
    });
    expect(historyRes.ok()).toBeTruthy();
    const history = await historyRes.json();
    const published = Array.isArray(history)
      ? history.find((p: any) => p.id === postId || p.post_id === postId)
      : history?.posts?.find((p: any) => p.id === postId || p.post_id === postId);
    expect(published, 'post should appear in history').toBeTruthy();
    expect(published?.status, 'post status should be published').toBe('published');
  });
});
