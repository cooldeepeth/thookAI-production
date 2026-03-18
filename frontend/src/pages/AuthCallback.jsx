import { useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

export default function AuthCallback() {
  const navigate = useNavigate();
  const { login } = useAuth();
  const hasProcessed = useRef(false);

  useEffect(() => {
    // Prevent double-processing under React StrictMode
    if (hasProcessed.current) return;
    hasProcessed.current = true;

    const hash = window.location.hash;
    const params = new URLSearchParams(hash.replace('#', '?'));
    const sessionId = params.get('session_id');

    if (!sessionId) {
      navigate('/auth', { replace: true });
      return;
    }

    (async () => {
      try {
        const res = await fetch(`${BACKEND_URL}/api/auth/google/session`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "include",
          body: JSON.stringify({ session_id: sessionId }),
        });
        if (!res.ok) throw new Error("Session exchange failed");
        const user = await res.json();
        login(user);
        navigate('/dashboard', { replace: true, state: { user } });
      } catch (err) {
        console.error("Auth callback error:", err);
        navigate('/auth?error=auth_failed', { replace: true });
      }
    })();
  }, [navigate, login]);

  return (
    <div className="min-h-screen bg-[#050505] flex items-center justify-center">
      <div className="flex flex-col items-center gap-4">
        <div className="w-10 h-10 border-2 border-lime border-t-transparent rounded-full animate-spin" />
        <p className="text-zinc-400 text-sm">Signing you in...</p>
      </div>
    </div>
  );
}
