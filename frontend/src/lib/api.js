/**
 * Centralized API fetch wrapper with auth token injection and 401 handling.
 * New code should use apiFetch() instead of raw fetch().
 * Existing pages will be migrated progressively.
 */
const API_BASE = process.env.REACT_APP_BACKEND_URL || '';

export async function apiFetch(path, options = {}) {
  const token = localStorage.getItem('thook_token');
  const headers = {
    ...options.headers,
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  if (!(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json';
  }

  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
    credentials: 'include',
  });

  if (res.status === 401) {
    // Token expired or invalid — clear and redirect
    localStorage.removeItem('thook_token');
    window.location.href = '/auth?expired=1';
    throw new Error('Session expired');
  }

  return res;
}
