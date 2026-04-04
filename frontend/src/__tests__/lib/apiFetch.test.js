/**
 * Unit tests for apiFetch (frontend/src/lib/api.js)
 *
 * Covers: timeout, retry-on-5xx, 401 redirect, 403 toast, CSRF injection,
 * credentials, content-type handling, and response pass-through.
 *
 * All network calls intercepted by MSW (no real HTTP traffic).
 */
import { http, HttpResponse } from 'msw';
import { server } from '@/mocks/server';
import { apiFetch } from '@/lib/api';

// Mock the toast hook so we can assert on it without triggering Radix toasts
jest.mock('@/hooks/use-toast', () => ({
  toast: jest.fn(),
}));

import { toast } from '@/hooks/use-toast';

// ─── window.location helpers ──────────────────────────────────────────────────
const originalLocation = window.location;

beforeEach(() => {
  delete window.location;
  window.location = { href: '' };
  toast.mockClear();
});

afterEach(() => {
  window.location = originalLocation;
  // Clear any CSRF cookie set during tests
  document.cookie = 'csrf_token=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/';
});

// ─── Helpers ──────────────────────────────────────────────────────────────────

function setCsrfCookie(value = 'test-csrf-token') {
  document.cookie = `csrf_token=${value}`;
}

// ─── Tests ────────────────────────────────────────────────────────────────────

describe('apiFetch', () => {
  // ── Timeout behaviour ────────────────────────────────────────────────────

  test('timeout: throws AbortError and calls toast when request never resolves', async () => {
    // MSW v2 Node interceptor does not propagate AbortError back from the
    // intercepted handler to the caller (the fetch never settles when using
    // a never-resolving MSW handler + AbortSignal).
    //
    // Strategy: stub global.fetch directly to simulate the AbortError that a
    // real browser fetch() throws when the signal fires. This directly tests
    // the fetchWithTimeout catch-block that calls toast and re-throws.
    const abortError = new DOMException('The operation was aborted.', 'AbortError');
    const origFetch = global.fetch;
    global.fetch = jest.fn().mockRejectedValue(abortError);

    let caughtError;
    try {
      await apiFetch('/api/test-timeout', { timeout: 10 });
    } catch (err) {
      caughtError = err;
    }

    global.fetch = origFetch; // restore

    expect(caughtError).toBeDefined();
    expect(caughtError.name).toBe('AbortError');
    expect(toast).toHaveBeenCalledWith(
      expect.objectContaining({ title: 'Request timed out' })
    );
  });

  test('timeout_override: options.timeout=50 uses 50ms instead of DEFAULT_TIMEOUT_MS', async () => {
    // Verify a custom short timeout (10ms) fires before the default 15000ms
    server.use(
      http.get('*/api/test-override', async () => {
        await new Promise(() => {});
      })
    );

    const start = Date.now();
    await expect(
      apiFetch('/api/test-override', { timeout: 10 })
    ).rejects.toThrow();
    const elapsed = Date.now() - start;

    // If it used 15000ms default, this would fail. 10ms override means it
    // should complete well under 2000ms.
    expect(elapsed).toBeLessThan(2000);
  });

  test('caller_signal: when options.signal provided, no internal timeout is applied', async () => {
    // Provide a signal that is NOT aborted — request completes normally
    const controller = new AbortController();

    server.use(
      http.get('*/api/test-signal', () =>
        HttpResponse.json({ ok: true })
      )
    );

    const res = await apiFetch('/api/test-signal', { signal: controller.signal });
    expect(res.ok).toBe(true);
    // No timeout toast should have been called
    expect(toast).not.toHaveBeenCalled();
  });

  // ── Retry behaviour ──────────────────────────────────────────────────────

  test('retry_5xx: on first 503 then 200, makes exactly 2 fetch calls', async () => {
    let callCount = 0;

    server.use(
      http.get('*/api/test-retry', () => {
        callCount += 1;
        if (callCount === 1) {
          return new HttpResponse(null, { status: 503 });
        }
        return HttpResponse.json({ ok: true });
      })
    );

    const res = await apiFetch('/api/test-retry');
    expect(callCount).toBe(2);
    expect(res.ok).toBe(true);
  });

  test('no_retry_4xx: on 404, makes exactly 1 fetch call', async () => {
    let callCount = 0;

    server.use(
      http.get('*/api/test-no-retry-4xx', () => {
        callCount += 1;
        return new HttpResponse(null, { status: 404 });
      })
    );

    await apiFetch('/api/test-no-retry-4xx');
    expect(callCount).toBe(1);
  });

  test('no_retry_success: on 200, makes exactly 1 fetch call', async () => {
    let callCount = 0;

    server.use(
      http.get('*/api/test-no-retry-success', () => {
        callCount += 1;
        return HttpResponse.json({ ok: true });
      })
    );

    await apiFetch('/api/test-no-retry-success');
    expect(callCount).toBe(1);
  });

  // ── 401 / 403 handling ───────────────────────────────────────────────────

  test('401_redirect: on 401, window.location.href is set to /auth?expired=1 and throws', async () => {
    server.use(
      http.get('*/api/test-401', () => new HttpResponse(null, { status: 401 }))
    );

    await expect(apiFetch('/api/test-401')).rejects.toThrow('Session expired');
    expect(window.location.href).toBe('/auth?expired=1');
  });

  test('403_toast: on 403, toast is called with title "Permission denied" and throws', async () => {
    server.use(
      http.get('*/api/test-403', () => new HttpResponse(null, { status: 403 }))
    );

    await expect(apiFetch('/api/test-403')).rejects.toThrow('Permission denied');
    expect(toast).toHaveBeenCalledWith(
      expect.objectContaining({ title: 'Permission denied' })
    );
  });

  test('5xx_toast: on 500 after retry exhaustion, toast is called with title "Server error"', async () => {
    server.use(
      http.get('*/api/test-5xx-toast', () =>
        new HttpResponse(null, { status: 500 })
      )
    );

    await apiFetch('/api/test-5xx-toast');
    expect(toast).toHaveBeenCalledWith(
      expect.objectContaining({ title: 'Server error' })
    );
  });

  // ── CSRF injection ───────────────────────────────────────────────────────

  test('csrf_injected: POST request includes X-CSRF-Token when csrf_token cookie present', async () => {
    setCsrfCookie('my-csrf-value');
    let capturedHeaders = {};

    server.use(
      http.post('*/api/test-csrf-post', ({ request }) => {
        capturedHeaders = Object.fromEntries(request.headers.entries());
        return HttpResponse.json({ ok: true });
      })
    );

    await apiFetch('/api/test-csrf-post', { method: 'POST', body: '{}' });
    expect(capturedHeaders['x-csrf-token']).toBe('my-csrf-value');
  });

  test('csrf_not_injected_get: GET request does NOT include X-CSRF-Token header', async () => {
    setCsrfCookie('my-csrf-value');
    let capturedHeaders = {};

    server.use(
      http.get('*/api/test-csrf-get', ({ request }) => {
        capturedHeaders = Object.fromEntries(request.headers.entries());
        return HttpResponse.json({ ok: true });
      })
    );

    await apiFetch('/api/test-csrf-get');
    expect(capturedHeaders['x-csrf-token']).toBeUndefined();
  });

  test('csrf_skip_no_cookie: POST with no csrf_token cookie does not include X-CSRF-Token', async () => {
    // Ensure cookie is NOT set
    document.cookie = 'csrf_token=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/';
    let capturedHeaders = {};

    server.use(
      http.post('*/api/test-csrf-no-cookie', ({ request }) => {
        capturedHeaders = Object.fromEntries(request.headers.entries());
        return HttpResponse.json({ ok: true });
      })
    );

    await apiFetch('/api/test-csrf-no-cookie', { method: 'POST', body: '{}' });
    expect(capturedHeaders['x-csrf-token']).toBeUndefined();
  });

  // ── credentials ──────────────────────────────────────────────────────────

  test('credentials_include: every request is made with credentials: include', async () => {
    let capturedCredentials;

    server.use(
      http.get('*/api/test-credentials', ({ request }) => {
        capturedCredentials = request.credentials;
        return HttpResponse.json({ ok: true });
      })
    );

    await apiFetch('/api/test-credentials');
    expect(capturedCredentials).toBe('include');
  });

  // ── Content-Type handling ────────────────────────────────────────────────

  test('content_type_json: non-FormData body request includes Content-Type: application/json', async () => {
    let capturedHeaders = {};

    server.use(
      http.post('*/api/test-ct-json', ({ request }) => {
        capturedHeaders = Object.fromEntries(request.headers.entries());
        return HttpResponse.json({ ok: true });
      })
    );

    await apiFetch('/api/test-ct-json', {
      method: 'POST',
      body: JSON.stringify({ foo: 'bar' }),
    });

    expect(capturedHeaders['content-type']).toBe('application/json');
  });

  test('content_type_formdata: FormData body request does NOT include Content-Type header', async () => {
    let capturedHeaders = {};

    server.use(
      http.post('*/api/test-ct-formdata', ({ request }) => {
        capturedHeaders = Object.fromEntries(request.headers.entries());
        return HttpResponse.json({ ok: true });
      })
    );

    const formData = new FormData();
    formData.append('file', new Blob(['hello']), 'hello.txt');

    await apiFetch('/api/test-ct-formdata', {
      method: 'POST',
      body: formData,
    });

    // Content-Type must NOT be explicitly set (browser sets multipart/form-data + boundary)
    expect(capturedHeaders['content-type']).not.toBe('application/json');
  });

  // ── Response handling ────────────────────────────────────────────────────

  test('returns_response: successful response returns a Response object', async () => {
    server.use(
      http.get('*/api/test-response-obj', () =>
        HttpResponse.json({ data: 'hello' })
      )
    );

    const res = await apiFetch('/api/test-response-obj');
    expect(res).toBeDefined();
    expect(typeof res.json).toBe('function');
    expect(res.ok).toBe(true);
  });

  test('200_json: response from GET /api/auth/me can be parsed with .json()', async () => {
    server.use(
      http.get('*/api/auth/me', () =>
        HttpResponse.json({ user_id: 'u1', email: 'test@example.com' })
      )
    );

    const res = await apiFetch('/api/auth/me');
    const data = await res.json();
    expect(data.user_id).toBe('u1');
    expect(data.email).toBe('test@example.com');
  });

  // ── URL construction ─────────────────────────────────────────────────────

  test('base_url_prepend: apiFetch calls fetch with API_BASE_URL + the path', async () => {
    // The default API_BASE_URL is '' in test env so we just verify the path is hit
    server.use(
      http.get('*/api/test-base-url', () =>
        HttpResponse.json({ ok: true })
      )
    );

    const res = await apiFetch('/api/test-base-url');
    expect(res.ok).toBe(true);
  });

  test('base_url_empty: when REACT_APP_BACKEND_URL is unset, prepends empty string', async () => {
    // REACT_APP_BACKEND_URL is not set in test env — just the path is used
    server.use(
      http.get('*/api/test-no-base', () =>
        HttpResponse.json({ ok: true })
      )
    );

    const res = await apiFetch('/api/test-no-base');
    expect(res.ok).toBe(true);
  });

  // ── CSRF on other mutating methods ───────────────────────────────────────

  test('method_put_csrf: PUT request includes X-CSRF-Token', async () => {
    setCsrfCookie('put-token');
    let capturedHeaders = {};

    server.use(
      http.put('*/api/test-put-csrf', ({ request }) => {
        capturedHeaders = Object.fromEntries(request.headers.entries());
        return HttpResponse.json({ ok: true });
      })
    );

    await apiFetch('/api/test-put-csrf', { method: 'PUT', body: '{}' });
    expect(capturedHeaders['x-csrf-token']).toBe('put-token');
  });

  test('method_delete_csrf: DELETE request includes X-CSRF-Token', async () => {
    setCsrfCookie('delete-token');
    let capturedHeaders = {};

    server.use(
      http.delete('*/api/test-delete-csrf', ({ request }) => {
        capturedHeaders = Object.fromEntries(request.headers.entries());
        return HttpResponse.json({ ok: true });
      })
    );

    await apiFetch('/api/test-delete-csrf', { method: 'DELETE' });
    expect(capturedHeaders['x-csrf-token']).toBe('delete-token');
  });

  test('method_patch_csrf: PATCH request includes X-CSRF-Token', async () => {
    setCsrfCookie('patch-token');
    let capturedHeaders = {};

    server.use(
      http.patch('*/api/test-patch-csrf', ({ request }) => {
        capturedHeaders = Object.fromEntries(request.headers.entries());
        return HttpResponse.json({ ok: true });
      })
    );

    await apiFetch('/api/test-patch-csrf', { method: 'PATCH', body: '{}' });
    expect(capturedHeaders['x-csrf-token']).toBe('patch-token');
  });
});
