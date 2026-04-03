import { http, HttpResponse } from 'msw';

export const handlers = [
  // Auth
  http.get('*/api/auth/me', () =>
    HttpResponse.json({ user_id: 'u1', email: 'test@example.com', subscription_tier: 'pro', credits: 100 })
  ),
  http.post('*/api/auth/logout', () =>
    HttpResponse.json({ ok: true })
  ),
  // Billing
  http.get('*/api/billing/credits', () =>
    HttpResponse.json({ credits: 80, monthly_allowance: 100, tier: 'pro', is_low_balance: false })
  ),
  // Notifications
  http.get('*/api/notifications', () =>
    HttpResponse.json({ notifications: [] })
  ),
  http.get('*/api/notifications/count', () =>
    HttpResponse.json({ unread_count: 0 })
  ),
  http.post('*/api/notifications/:id/read', () =>
    HttpResponse.json({ ok: true })
  ),
  http.post('*/api/notifications/read-all', () =>
    HttpResponse.json({ ok: true })
  ),
  // Strategy
  http.get('*/api/strategy', () =>
    HttpResponse.json({ cards: [] })
  ),
  http.post('*/api/strategy/:id/approve', () =>
    HttpResponse.json({ generate_payload: {} })
  ),
  http.post('*/api/strategy/:id/dismiss', () =>
    HttpResponse.json({ needs_calibration_prompt: false })
  ),
  // Content
  http.post('*/api/content/generate', () =>
    HttpResponse.json({ job_id: 'job-123', status: 'processing' })
  ),
  http.get('*/api/content/job/:id', () =>
    HttpResponse.json({ job_id: 'job-123', status: 'reviewing', draft: 'Test content' })
  ),
];
