import { test, expect } from '@playwright/test';

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

test.describe('Register and onboard', () => {
  test('new user can register, onboard with 10 posts, and land on Content Studio', async ({ page, request }) => {
    // 1. Register via API
    const registerRes = await request.post('/api/auth/register', {
      data: { email: TEST_EMAIL, password: TEST_PASSWORD }
    });
    expect(registerRes.status(), 'registration should return 200').toBe(200);
    const { token } = await registerRes.json();
    expect(token, 'registration should return a JWT').toBeTruthy();

    // 2. Submit onboarding posts via API
    const onboardRes = await request.post('/api/onboarding/posts', {
      headers: { Authorization: `Bearer ${token}` },
      data: { posts: SAMPLE_POSTS }
    });
    expect(onboardRes.status(), 'onboarding post submission should return 200').toBe(200);

    // 3. Poll persona extraction (max 60 seconds)
    let voiceProfile = null;
    const deadline = Date.now() + 60_000;
    while (Date.now() < deadline) {
      const personaRes = await request.get('/api/persona/me', {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (personaRes.ok()) {
        const body = await personaRes.json();
        if (body?.voice_profile) { voiceProfile = body.voice_profile; break; }
      }
      await page.waitForTimeout(3000);
    }
    expect(voiceProfile, 'persona voice_profile should be non-null within 60s').toBeTruthy();

    // 4. UI: log in and verify redirect to content studio
    await page.goto('/auth');
    await page.getByLabel(/email/i).fill(TEST_EMAIL);
    await page.getByLabel(/password/i).fill(TEST_PASSWORD);
    await page.getByRole('button', { name: /sign in|log in|continue/i }).click();
    await page.waitForURL('**/dashboard/content-studio', { timeout: 15_000 });
    await expect(page).toHaveURL(/dashboard\/content-studio/);
  });
});
