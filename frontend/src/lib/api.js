/**
 * Centralized API fetch wrapper with cookie auth and CSRF token header.
 *
 * Auth: session_token cookie (httpOnly) is sent automatically via credentials: 'include'.
 * CSRF: X-CSRF-Token header is read from the csrf_token cookie (JS-readable) and injected
 *       on all state-changing requests (POST, PUT, PATCH, DELETE).
 *
 * New code should use apiFetch() instead of raw fetch().
 * Existing pages will be migrated progressively (Phase 22).
 */
const API_BASE = process.env.REACT_APP_BACKEND_URL || '';

/**
 * Read the CSRF token from the JS-readable csrf_token cookie set by the backend.
 * @returns {string|null}
 */
function getCsrfToken() {
  const match = document.cookie.match(/(?:^|; )csrf_token=([^;]*)/);
  return match ? decodeURIComponent(match[1]) : null;
}

export async function apiFetch(path, options = {}) {
  const headers = {
    ...options.headers,
  };

  if (!(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json';
  }

  // Inject CSRF token header for state-changing requests
  const method = (options.method || 'GET').toUpperCase();
  if (method !== 'GET' && method !== 'HEAD') {
    const csrfToken = getCsrfToken();
    if (csrfToken) {
      headers['X-CSRF-Token'] = csrfToken;
    }
  }

  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
    credentials: 'include',
  });

  if (res.status === 401) {
    // Session expired — redirect to sign in
    window.location.href = '/auth?expired=1';
    throw new Error('Session expired');
  }

  return res;
}
