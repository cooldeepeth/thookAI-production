import { test, expect } from '@playwright/test';

// Use storageState for auth — assumes 01 test created a user and saved session,
// or use a seeded test account. Check if playwright.config.ts has storageState setup.
// If not, register fresh here and proceed.
const TEST_EMAIL = `wedge-gen-${Date.now()}@thookai-test.com`;
const TEST_PASSWORD = 'TestWedge2026!';

test.describe('Generate and edit post', () => {
  let token: string;

  test.beforeAll(async ({ request }) => {
    const reg = await request.post('/api/auth/register', {
      data: { email: TEST_EMAIL, password: TEST_PASSWORD }
    });
    const body = await reg.json();
    token = body.token;
    // Submit minimal onboarding so content studio is accessible
    await request.post('/api/onboarding/posts', {
      headers: { Authorization: `Bearer ${token}` },
      data: { posts: Array(10).fill('Building in public every day. Sharing what I learn.') }
    });
  });

  test('user can generate a post, edit it, and see credit deduction', async ({ page, request }) => {
    // 1. Get starting credit balance
    const balanceBefore = await request.get('/api/billing/credits', {
      headers: { Authorization: `Bearer ${token}` }
    });
    const { credits: creditsBefore } = await balanceBefore.json();

    // 2. Create content via API
    const createRes = await request.post('/api/content/create', {
      headers: { Authorization: `Bearer ${token}` },
      data: { topic: 'I just got my first paying customer', platform: 'linkedin' }
    });
    expect(createRes.status(), 'content create should return 200').toBe(200);
    const { job_id } = await createRes.json();
    expect(job_id, 'content create should return a job_id').toBeTruthy();

    // 3. Poll for completion (max 30 seconds)
    let postContent = null;
    const deadline = Date.now() + 30_000;
    while (Date.now() < deadline) {
      const statusRes = await request.get(`/api/content/status/${job_id}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      const body = await statusRes.json();
      if (body?.status === 'done' && body?.content) { postContent = body.content; break; }
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
    await page.goto('/auth');
    await page.getByLabel(/email/i).fill(TEST_EMAIL);
    await page.getByLabel(/password/i).fill(TEST_PASSWORD);
    await page.getByRole('button', { name: /sign in|log in|continue/i }).click();
    await page.waitForURL('**/dashboard/**', { timeout: 15_000 });
    await page.goto('/dashboard/content-studio');

    // Verify an editable text area / post editor is present
    const editor = page.locator('[contenteditable], textarea').first();
    await expect(editor, 'post editor should be present').toBeVisible({ timeout: 10_000 });
  });
});
