/**
 * Unit tests for AuthProvider / useAuth (frontend/src/context/AuthContext.jsx)
 *
 * Covers: initial loading state, authenticated user from /api/auth/me,
 * unauthenticated on error, login, logout, Google OAuth token path,
 * and useAuth guard.
 *
 * Auth is cookie-based: no localStorage is read or written.
 * All network calls intercepted by MSW.
 */
import React from 'react';
import { render, screen, waitFor, act } from '@testing-library/react';
import { renderHook } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { server } from '@/mocks/server';
import { AuthProvider, useAuth } from '@/context/AuthContext';

// Silence the toast mock used by apiFetch in some tests
jest.mock('@/hooks/use-toast', () => ({
  toast: jest.fn(),
}));

// ─── window.location helpers ──────────────────────────────────────────────────
const originalLocation = window.location;

beforeEach(() => {
  delete window.location;
  window.location = { href: '', search: '' };
});

afterEach(() => {
  window.location = originalLocation;
});

// ─── Helpers ──────────────────────────────────────────────────────────────────

/**
 * Render any UI wrapped in AuthProvider.
 */
function renderWithAuth(ui) {
  return render(<AuthProvider>{ui}</AuthProvider>);
}

/**
 * A test component that exposes auth state via accessible text.
 */
function AuthStateDisplay() {
  const { user, loading } = useAuth();
  return (
    <div>
      <span data-testid="loading">{String(loading)}</span>
      <span data-testid="user">{user ? user.user_id : 'null'}</span>
    </div>
  );
}

// ─── Tests ────────────────────────────────────────────────────────────────────

describe('AuthProvider', () => {
  // ── Initial state ────────────────────────────────────────────────────────

  test('initial_loading: loading=true initially, then false after /api/auth/me resolves', async () => {
    // Use the default handler (happy path from handlers.js) which resolves immediately.
    // We check that loading starts as true and ends as false after mount.
    // Note: in React 18 + React Testing Library, the initial render captures loading=true
    // synchronously before effects run.
    renderWithAuth(<AuthStateDisplay />);

    // At this point, the component has rendered but the useEffect hasn't fired yet.
    // In React 18, effects run asynchronously after the first commit.
    // The initial state before any effect: loading=true, user=null.
    expect(screen.getByTestId('loading').textContent).toBe('true');

    // After the /api/auth/me call completes, loading becomes false
    await waitFor(() => {
      expect(screen.getByTestId('loading').textContent).toBe('false');
    });
  });

  // ── Authenticated user ────────────────────────────────────────────────────

  test('authenticated_user: after successful /api/auth/me, user state equals response data', async () => {
    server.use(
      http.get('*/api/auth/me', () =>
        HttpResponse.json({ user_id: 'u1', email: 'test@example.com', subscription_tier: 'pro' })
      )
    );

    renderWithAuth(<AuthStateDisplay />);

    await waitFor(() => {
      expect(screen.getByTestId('user').textContent).toBe('u1');
    });
  });

  // ── Unauthenticated on 401 ────────────────────────────────────────────────

  test('unauthenticated_on_401: when /api/auth/me returns 401, user remains null', async () => {
    server.use(
      // Override only the status — don't let apiFetch redirect for 401 in tests.
      // We need checkAuth to set user=null, which it does when res.ok is false.
      // apiFetch redirects to /auth on 401, but checkAuth catches the thrown error.
      http.get('*/api/auth/me', () => new HttpResponse(null, { status: 401 }))
    );

    renderWithAuth(<AuthStateDisplay />);

    await waitFor(() => {
      expect(screen.getByTestId('loading').textContent).toBe('false');
      expect(screen.getByTestId('user').textContent).toBe('null');
    });
  });

  // ── Unauthenticated on network error ─────────────────────────────────────

  test('unauthenticated_on_error: when /api/auth/me throws network error, user is null', async () => {
    server.use(
      http.get('*/api/auth/me', () => HttpResponse.error())
    );

    renderWithAuth(<AuthStateDisplay />);

    await waitFor(() => {
      expect(screen.getByTestId('loading').textContent).toBe('false');
      expect(screen.getByTestId('user').textContent).toBe('null');
    });
  });

  // ── No localStorage ───────────────────────────────────────────────────────

  test('no_localStorage: user state is never read from or written to localStorage', async () => {
    const getSpy = jest.spyOn(Storage.prototype, 'getItem');
    const setSpy = jest.spyOn(Storage.prototype, 'setItem');

    server.use(
      http.get('*/api/auth/me', () =>
        HttpResponse.json({ user_id: 'u1', email: 'test@example.com' })
      )
    );

    renderWithAuth(<AuthStateDisplay />);

    await waitFor(() => {
      expect(screen.getByTestId('user').textContent).toBe('u1');
    });

    // Verify localStorage was never touched for user data
    const userRelatedGetCalls = getSpy.mock.calls.filter(
      ([key]) => key && (key.includes('user') || key.includes('token') || key.includes('auth'))
    );
    const userRelatedSetCalls = setSpy.mock.calls.filter(
      ([key]) => key && (key.includes('user') || key.includes('token') || key.includes('auth'))
    );

    expect(userRelatedGetCalls).toHaveLength(0);
    expect(userRelatedSetCalls).toHaveLength(0);

    getSpy.mockRestore();
    setSpy.mockRestore();
  });

  // ── login ─────────────────────────────────────────────────────────────────

  test('login_sets_user: calling login({ user_id: "u2" }) sets user to that object', async () => {
    server.use(
      // Return 401 so initial checkAuth leaves user=null
      http.get('*/api/auth/me', () => new HttpResponse(null, { status: 401 }))
    );

    // Consumer component that calls login
    function LoginTest() {
      const { user, login } = useAuth();
      return (
        <div>
          <span data-testid="user">{user ? user.user_id : 'null'}</span>
          <button onClick={() => login({ user_id: 'u2', email: 'new@example.com' })}>
            Login
          </button>
        </div>
      );
    }

    renderWithAuth(<LoginTest />);

    await waitFor(() => {
      expect(screen.getByTestId('user').textContent).toBe('null');
    });

    // Click the login button to call login(userData)
    await act(async () => {
      screen.getByRole('button').click();
    });

    expect(screen.getByTestId('user').textContent).toBe('u2');
  });

  // ── logout ────────────────────────────────────────────────────────────────

  test('logout_clears_user: calling logout() posts to /api/auth/logout then sets user to null', async () => {
    let logoutCalled = false;

    server.use(
      http.get('*/api/auth/me', () =>
        HttpResponse.json({ user_id: 'u1', email: 'test@example.com' })
      ),
      http.post('*/api/auth/logout', () => {
        logoutCalled = true;
        return HttpResponse.json({ ok: true });
      })
    );

    function LogoutTest() {
      const { user, logout } = useAuth();
      return (
        <div>
          <span data-testid="user">{user ? user.user_id : 'null'}</span>
          <button onClick={logout}>Logout</button>
        </div>
      );
    }

    renderWithAuth(<LogoutTest />);

    // Wait for user to be set
    await waitFor(() => {
      expect(screen.getByTestId('user').textContent).toBe('u1');
    });

    // Click logout
    await act(async () => {
      screen.getByRole('button').click();
    });

    expect(logoutCalled).toBe(true);

    await waitFor(() => {
      expect(screen.getByTestId('user').textContent).toBe('null');
    });
  });

  // ── Google OAuth token path ───────────────────────────────────────────────

  test('google_oauth_token: when ?token=abc in URL, /api/auth/me is called with Authorization: Bearer abc', async () => {
    window.location.search = '?token=test-token-123';

    let capturedAuthHeader = null;

    server.use(
      http.get('*/api/auth/me', ({ request }) => {
        capturedAuthHeader = request.headers.get('Authorization');
        return HttpResponse.json({ user_id: 'oauth-u1', email: 'oauth@example.com' });
      })
    );

    window.history = { replaceState: jest.fn() };

    renderWithAuth(<AuthStateDisplay />);

    await waitFor(() => {
      expect(screen.getByTestId('user').textContent).toBe('oauth-u1');
    });

    expect(capturedAuthHeader).toBe('Bearer test-token-123');
  });

  test('google_oauth_clears_param: after Google OAuth, window.history.replaceState called with /dashboard', async () => {
    window.location.search = '?token=clear-test';

    // Spy on the existing window.history.replaceState (jsdom provides this)
    const replaceStateSpy = jest.spyOn(window.history, 'replaceState');

    server.use(
      http.get('*/api/auth/me', () =>
        HttpResponse.json({ user_id: 'u3', email: 'clear@example.com' })
      )
    );

    renderWithAuth(<AuthStateDisplay />);

    await waitFor(() => {
      expect(screen.getByTestId('user').textContent).toBe('u3');
    });

    expect(replaceStateSpy).toHaveBeenCalledWith(
      expect.anything(),
      expect.anything(),
      '/dashboard'
    );

    replaceStateSpy.mockRestore();
  });

  // ── useAuth throws outside provider ──────────────────────────────────────

  test('useAuth_throws_outside_provider: calling useAuth() outside AuthProvider throws', () => {
    // Suppress the expected error output
    const consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => {});

    expect(() => {
      renderHook(() => useAuth());
    }).toThrow('useAuth must be used within AuthProvider');

    consoleSpy.mockRestore();
  });
});
