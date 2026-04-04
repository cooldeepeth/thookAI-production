/**
 * Unit tests for useStrategyFeed (frontend/src/hooks/useStrategyFeed.js)
 *
 * Covers: initial empty state, active cards loaded, approveCard POST,
 * approve returns generate_payload, approve refreshes active cards,
 * dismissCard POST, dismiss refreshes both lists, error does not crash.
 *
 * All network calls intercepted by MSW.
 */
import { renderHook, act, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { server } from '@/mocks/server';
import useStrategyFeed from '@/hooks/useStrategyFeed';

// Suppress toast mock (apiFetch uses it internally for 5xx handling)
jest.mock('@/hooks/use-toast', () => ({
  toast: jest.fn(),
}));

describe('useStrategyFeed', () => {
  // ── Initial empty state ───────────────────────────────────────────────────

  test('initial_empty: on mount with empty API response, activeCards=[] and loading transitions to false', async () => {
    // Default handler returns { cards: [] } — no override needed
    const { result } = renderHook(() => useStrategyFeed());

    // Should start loading
    expect(result.current.loading).toBe(true);

    // After fetch completes, loading should be false and activeCards empty
    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.activeCards).toEqual([]);
  });

  // ── Active cards loaded ───────────────────────────────────────────────────

  test('active_cards_loaded: when API returns 2 cards, activeCards.length === 2', async () => {
    server.use(
      http.get('*/api/strategy', ({ request }) => {
        const url = new URL(request.url);
        const status = url.searchParams.get('status');
        if (status === 'pending_approval') {
          return HttpResponse.json({
            cards: [
              {
                recommendation_id: 'r1',
                platform: 'linkedin',
                status: 'pending_approval',
                created_at: '2026-01-01T00:00:00Z',
              },
              {
                recommendation_id: 'r2',
                platform: 'x',
                status: 'pending_approval',
                created_at: '2026-01-01T01:00:00Z',
              },
            ],
          });
        }
        // History endpoints return empty
        return HttpResponse.json({ cards: [] });
      })
    );

    const { result } = renderHook(() => useStrategyFeed());

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.activeCards).toHaveLength(2);
    expect(result.current.activeCards[0].recommendation_id).toBe('r1');
    expect(result.current.activeCards[1].recommendation_id).toBe('r2');
  });

  // ── approveCard ───────────────────────────────────────────────────────────

  test('approve_posts: approveCard("rec-1") makes POST /api/strategy/rec-1/approve', async () => {
    let approvedId = null;

    server.use(
      http.post('*/api/strategy/:id/approve', ({ params }) => {
        approvedId = params.id;
        return HttpResponse.json({ generate_payload: { platform: 'linkedin' } });
      })
    );

    const { result } = renderHook(() => useStrategyFeed());

    await waitFor(() => expect(result.current.loading).toBe(false));

    await act(async () => {
      await result.current.approveCard('rec-1');
    });

    expect(approvedId).toBe('rec-1');
  });

  test('approve_returns_payload: approveCard returns the generate_payload from response', async () => {
    const expectedPayload = { platform: 'linkedin', content_type: 'post', topic: 'AI' };

    server.use(
      http.post('*/api/strategy/:id/approve', () =>
        HttpResponse.json({ generate_payload: expectedPayload })
      )
    );

    const { result } = renderHook(() => useStrategyFeed());

    await waitFor(() => expect(result.current.loading).toBe(false));

    let returnedPayload;
    await act(async () => {
      returnedPayload = await result.current.approveCard('rec-2');
    });

    expect(returnedPayload).toEqual(expectedPayload);
  });

  test('approve_refreshes_active: after approveCard, fetchActiveCards is called (activeCards re-fetched)', async () => {
    let fetchCount = 0;

    server.use(
      http.get('*/api/strategy', ({ request }) => {
        const url = new URL(request.url);
        const status = url.searchParams.get('status');
        if (status === 'pending_approval') {
          fetchCount += 1;
          // First call: return 1 card. After approve: return 0 cards.
          if (fetchCount === 1) {
            return HttpResponse.json({
              cards: [{ recommendation_id: 'r1', platform: 'linkedin', status: 'pending_approval', created_at: '2026-01-01T00:00:00Z' }],
            });
          }
          return HttpResponse.json({ cards: [] });
        }
        return HttpResponse.json({ cards: [] });
      }),
      http.post('*/api/strategy/:id/approve', () =>
        HttpResponse.json({ generate_payload: {} })
      )
    );

    const { result } = renderHook(() => useStrategyFeed());

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
      expect(result.current.activeCards).toHaveLength(1);
    });

    const initialFetchCount = fetchCount;

    await act(async () => {
      await result.current.approveCard('r1');
    });

    // fetchActiveCards should have been called again after approve
    expect(fetchCount).toBeGreaterThan(initialFetchCount);
    // After refresh, the empty response should update activeCards
    await waitFor(() => {
      expect(result.current.activeCards).toHaveLength(0);
    });
  });

  // ── dismissCard ───────────────────────────────────────────────────────────

  test('dismiss_posts: dismissCard("rec-1", "not_relevant") makes POST /api/strategy/rec-1/dismiss with body', async () => {
    let dismissedId = null;
    let dismissBody = null;

    server.use(
      http.post('*/api/strategy/:id/dismiss', async ({ params, request }) => {
        dismissedId = params.id;
        dismissBody = await request.json().catch(() => null);
        return HttpResponse.json({ needs_calibration_prompt: false });
      })
    );

    const { result } = renderHook(() => useStrategyFeed());

    await waitFor(() => expect(result.current.loading).toBe(false));

    await act(async () => {
      await result.current.dismissCard('rec-1', 'not_relevant');
    });

    expect(dismissedId).toBe('rec-1');
    expect(dismissBody).toEqual({ reason: 'not_relevant' });
  });

  test('dismiss_refreshes_both: after dismissCard, both active and history lists are re-fetched', async () => {
    let activeFetchCount = 0;
    let historyFetchCount = 0;

    server.use(
      http.get('*/api/strategy', ({ request }) => {
        const url = new URL(request.url);
        const status = url.searchParams.get('status');
        if (status === 'pending_approval') {
          activeFetchCount += 1;
          return HttpResponse.json({ cards: [] });
        }
        if (status === 'dismissed' || status === 'approved') {
          historyFetchCount += 1;
          return HttpResponse.json({ cards: [] });
        }
        return HttpResponse.json({ cards: [] });
      }),
      http.post('*/api/strategy/:id/dismiss', () =>
        HttpResponse.json({ needs_calibration_prompt: false })
      )
    );

    const { result } = renderHook(() => useStrategyFeed());

    await waitFor(() => expect(result.current.loading).toBe(false));

    const activeCountBefore = activeFetchCount;
    const historyCountBefore = historyFetchCount;

    await act(async () => {
      await result.current.dismissCard('rec-1', 'irrelevant');
    });

    // Both active and history should have been re-fetched
    expect(activeFetchCount).toBeGreaterThan(activeCountBefore);
    expect(historyFetchCount).toBeGreaterThan(historyCountBefore);
  });

  // ── Error handling ────────────────────────────────────────────────────────

  test('error_does_not_crash: when API returns 500, hook returns empty arrays without throwing', async () => {
    server.use(
      http.get('*/api/strategy', () =>
        new HttpResponse(null, { status: 500 })
      )
    );

    const { result } = renderHook(() => useStrategyFeed());

    // apiFetch retries once on 5xx with 1s backoff, so 3 strategy calls take ~3s.
    // Increase waitFor timeout to accommodate the retry delay.
    await waitFor(
      () => {
        expect(result.current.loading).toBe(false);
      },
      { timeout: 6000 }
    );

    // Should not throw and should return empty arrays
    expect(result.current.activeCards).toEqual([]);
    expect(result.current.historyCards).toEqual([]);
  }, 8000);
});
