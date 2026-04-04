/**
 * Unit tests for useNotifications (frontend/src/hooks/useNotifications.js)
 *
 * Covers: initial loading state, notifications fetched, unread count,
 * markRead POST, markAllRead POST, loading false after fetch,
 * empty on error, and SSE EventSource does not crash mount.
 *
 * EventSource is mocked globally to prevent jsdom errors on SSE connections.
 * All REST calls intercepted by MSW.
 */
import { renderHook, act, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { server } from '@/mocks/server';
import useNotifications from '@/hooks/useNotifications';

// Suppress toast mock (apiFetch uses it internally)
jest.mock('@/hooks/use-toast', () => ({
  toast: jest.fn(),
}));

// Note: resetMocks: true (CRA default) calls jest.resetAllMocks() before each
// test, clearing mock implementations. EventSource must be re-assigned in
// beforeEach so each test gets a fresh implementation.

describe('useNotifications', () => {
  beforeEach(() => {
    // Re-assign EventSource before each test.
    // resetMocks: true would clear any module-level jest.fn() implementation.
    global.EventSource = jest.fn(() => ({
      addEventListener: jest.fn(),
      removeEventListener: jest.fn(),
      close: jest.fn(),
      onmessage: null,
      onerror: null,
    }));
  });

  // ── Initial loading ───────────────────────────────────────────────────────

  test('initial_loading: loading=true on mount', () => {
    const { result } = renderHook(() => useNotifications());

    // Before the async fetch completes, loading should be true
    expect(result.current.loading).toBe(true);
  });

  // ── Notifications fetched ─────────────────────────────────────────────────

  test('notifications_fetched: after mount, notifications array is populated from API response', async () => {
    server.use(
      http.get('*/api/notifications', () =>
        HttpResponse.json({
          notifications: [
            { notification_id: 'n1', message: 'Hello', read: false },
            { notification_id: 'n2', message: 'World', read: true },
          ],
        })
      )
    );

    const { result } = renderHook(() => useNotifications());

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.notifications).toHaveLength(2);
    expect(result.current.notifications[0].notification_id).toBe('n1');
    expect(result.current.notifications[1].notification_id).toBe('n2');
  });

  // ── Unread count ──────────────────────────────────────────────────────────

  test('unread_count_fetched: unreadCount equals API response value', async () => {
    server.use(
      http.get('*/api/notifications/count', () =>
        HttpResponse.json({ unread_count: 3 })
      )
    );

    const { result } = renderHook(() => useNotifications());

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.unreadCount).toBe(3);
  });

  // ── markRead ──────────────────────────────────────────────────────────────

  test('mark_read_posts: markRead("notif-1") makes POST /api/notifications/notif-1/read', async () => {
    let markedId = null;

    server.use(
      http.get('*/api/notifications', () =>
        HttpResponse.json({
          notifications: [{ notification_id: 'notif-1', message: 'Test', read: false }],
        })
      ),
      http.get('*/api/notifications/count', () =>
        HttpResponse.json({ unread_count: 1 })
      ),
      http.post('*/api/notifications/:id/read', ({ params }) => {
        markedId = params.id;
        return HttpResponse.json({ ok: true });
      })
    );

    const { result } = renderHook(() => useNotifications());

    await waitFor(() => expect(result.current.loading).toBe(false));

    await act(async () => {
      await result.current.markRead('notif-1');
    });

    expect(markedId).toBe('notif-1');
  });

  // ── markAllRead ───────────────────────────────────────────────────────────

  test('mark_all_read_posts: markAllRead() makes POST /api/notifications/read-all', async () => {
    let readAllCalled = false;

    server.use(
      http.post('*/api/notifications/read-all', () => {
        readAllCalled = true;
        return HttpResponse.json({ ok: true });
      })
    );

    const { result } = renderHook(() => useNotifications());

    await waitFor(() => expect(result.current.loading).toBe(false));

    await act(async () => {
      await result.current.markAllRead();
    });

    expect(readAllCalled).toBe(true);
  });

  // ── Loading state ─────────────────────────────────────────────────────────

  test('loading_false_after_fetch: loading becomes false after initial fetch', async () => {
    const { result } = renderHook(() => useNotifications());

    // Starts as true
    expect(result.current.loading).toBe(true);

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });
  });

  // ── Error handling ────────────────────────────────────────────────────────

  test('empty_on_error: on API error, notifications stays []', async () => {
    server.use(
      http.get('*/api/notifications', () =>
        HttpResponse.error()
      ),
      http.get('*/api/notifications/count', () =>
        HttpResponse.error()
      )
    );

    const { result } = renderHook(() => useNotifications());

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.notifications).toEqual([]);
    expect(result.current.unreadCount).toBe(0);
  });

  // ── SSE EventSource ───────────────────────────────────────────────────────

  test('sse_not_blocking: component mounts without SSE EventSource crash', async () => {
    // EventSource is mocked globally — this test verifies that:
    // 1. The hook mounts without crashing
    // 2. EventSource constructor was called (proving the hook attempted SSE)
    const { result } = renderHook(() => useNotifications());

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    // EventSource should have been instantiated exactly once
    expect(global.EventSource).toHaveBeenCalledTimes(1);

    // The hook should still be functional (not crashed)
    expect(result.current.notifications).toBeDefined();
    expect(Array.isArray(result.current.notifications)).toBe(true);
  });
});
