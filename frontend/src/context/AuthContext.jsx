import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { apiFetch } from '@/lib/api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const checkAuth = useCallback(async () => {
    try {
      // session_token cookie is sent automatically via credentials: 'include' (apiFetch default)
      // No Authorization header — cookie is the source of truth
      const res = await apiFetch('/api/auth/me', { _skipAuthRedirect: true });
      if (!res.ok) {
        setUser(null);
        return;
      }
      const data = await res.json();
      setUser(data);
    } catch {
      // 401 is expected for unauthenticated visitors — _skipAuthRedirect prevents page redirect
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const token = params.get('token');
    if (token) {
      // Google OAuth callback: token param present.
      // The Google OAuth callback handler already set the session_token cookie
      // before redirecting to the frontend. We call /api/auth/me with the Bearer
      // header one-time for validation, but do NOT store the token in browser storage.
      // The cookie (set by the backend) is the session source of truth.
      (async () => {
        try {
          const res = await apiFetch('/api/auth/me', {
            headers: { Authorization: `Bearer ${token}` },
            _skipAuthRedirect: true,
          });
          if (!res.ok) throw new Error('Invalid token');
          const userData = await res.json();
          setUser(userData);
          window.history.replaceState({}, '', '/dashboard');
        } catch {
          setUser(null);
        } finally {
          setLoading(false);
        }
      })();
      return;
    }
    checkAuth();
  }, [checkAuth]);

  const login = (userData) => setUser(userData);

  const logout = async () => {
    // Backend clears session_token and csrf_token cookies
    await apiFetch('/api/auth/logout', { method: 'POST' });
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, logout, checkAuth }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
