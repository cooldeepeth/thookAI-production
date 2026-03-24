import { createContext, useContext, useState, useEffect, useCallback } from "react";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const checkAuth = useCallback(async () => {
    try {
      const token = localStorage.getItem("thook_token");
      const headers = {};
      if (token) {
        headers.Authorization = `Bearer ${token}`;
      }
      const res = await fetch(`${BACKEND_URL}/api/auth/me`, {
        credentials: "include",
        headers,
      });
      if (!res.ok) {
        setUser(null);
        return;
      }
      const data = await res.json();
      setUser(data);
    } catch {
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const token = params.get("token");
    if (token) {
      localStorage.setItem("thook_token", token);
      (async () => {
        try {
          const res = await fetch(`${BACKEND_URL}/api/auth/me`, {
            headers: { Authorization: `Bearer ${token}` },
            credentials: "include",
          });
          if (!res.ok) throw new Error("Invalid token");
          const userData = await res.json();
          setUser({ ...userData, token });
          window.history.replaceState({}, "", "/dashboard");
        } catch {
          localStorage.removeItem("thook_token");
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
    await fetch(`${BACKEND_URL}/api/auth/logout`, { method: "POST", credentials: "include" });
    localStorage.removeItem("thook_token");
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
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
