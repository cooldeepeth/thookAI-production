import { useState, useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { motion, AnimatePresence } from "framer-motion";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

export default function AuthPage() {
  const [tab, setTab] = useState("login");
  const [form, setForm] = useState({ email: "", password: "", name: "" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [showForgot, setShowForgot] = useState(false);
  const [forgotEmail, setForgotEmail] = useState("");
  const [forgotSent, setForgotSent] = useState(false);
  const [forgotLoading, setForgotLoading] = useState(false);
  const navigate = useNavigate();
  const { user, login } = useAuth();
  const [searchParams] = useSearchParams();

  useEffect(() => {
    if (user) navigate("/dashboard", { replace: true });
    if (searchParams.get("error")) setError("Authentication failed. Please try again.");
    if (searchParams.get("expired") === "1") setError("Your session has expired. Please sign in again.");
  }, [user, navigate, searchParams]);

  const handleGoogleAuth = () => {
    window.location.href = `${BACKEND_URL}/api/auth/google`;
  };

  const handleForgotSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setForgotLoading(true);
    try {
      const res = await fetch(`${BACKEND_URL}/api/auth/forgot-password`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ email: forgotEmail }),
      });
      await res.json().catch(() => ({}));
      setForgotSent(true);
    } catch {
      setForgotSent(true);
    } finally {
      setForgotLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const endpoint = tab === "register" ? "/api/auth/register" : "/api/auth/login";
      const body = tab === "register"
        ? { email: form.email, password: form.password, name: form.name }
        : { email: form.email, password: form.password };

      const res = await fetch(`${BACKEND_URL}${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify(body),
      });

      let data = {};
      
      // Try to read response body, but handle cases where it's already consumed
      try {
        const text = await res.text();
        if (text) {
          try {
            data = JSON.parse(text);
          } catch {
            // Not valid JSON, will use status-based errors
          }
        }
      } catch (bodyError) {
        // Body already consumed by browser/proxy - use status-based error messages
        if (!res.ok) {
          const statusErrors = {
            400: tab === "register" ? "Email already registered" : "Invalid request",
            401: "Invalid email or password",
            409: "Email already registered",
            500: "Server error. Please try again later."
          };
          throw new Error(statusErrors[res.status] || "Something went wrong");
        }
      }

      // Check response status
      if (!res.ok) {
        // If we have parsed data with detail/message, use it; otherwise use status-based error
        if (data.detail || data.message) {
          throw new Error(data.detail || data.message);
        } else {
          const statusErrors = {
            400: tab === "register" ? "Email already registered" : "Invalid request",
            401: "Invalid email or password",
            409: "Email already registered",
            500: "Server error. Please try again later."
          };
          throw new Error(statusErrors[res.status] || "Something went wrong");
        }
      }

      // Success - log user in (persist JWT for endpoints that use Bearer)
      if (data.token) {
        localStorage.setItem("thook_token", data.token);
      }
      login(data);
      navigate("/dashboard", { replace: true });
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#050505] flex items-center justify-center p-4 relative overflow-hidden">
      {/* Background glow */}
      <div className="absolute inset-0 hero-glow pointer-events-none" />
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-96 h-96 bg-violet/5 rounded-full blur-[120px] pointer-events-none" />

      <motion.div
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="w-full max-w-md"
      >
        {/* Logo */}
        <div className="text-center mb-8">
          <a href="/" className="inline-flex items-center gap-2 group">
            <div className="w-9 h-9 bg-lime rounded-lg flex items-center justify-center">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z" fill="#000" stroke="#000" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </div>
            <span className="font-display font-bold text-xl text-white">Thook</span>
          </a>
          <p className="text-zinc-500 text-sm mt-2">Your AI Creative Agency</p>
        </div>

        <div className="card-thook p-6">
          {showForgot ? (
            <div data-testid="forgot-password-form">
              <h2 className="text-white font-medium text-sm mb-1">Forgot password</h2>
              <p className="text-zinc-500 text-xs mb-4">Enter your email and we&apos;ll send a reset link if an account exists.</p>
              {forgotSent ? (
                <div className="space-y-4">
                  <p className="text-zinc-300 text-sm text-center">Check your email for a reset link.</p>
                  <button
                    type="button"
                    onClick={() => { setShowForgot(false); setForgotSent(false); setForgotEmail(""); }}
                    className="w-full text-center text-xs text-zinc-500 hover:text-lime transition-colors"
                  >
                    Back to sign in
                  </button>
                </div>
              ) : (
                <form onSubmit={handleForgotSubmit} className="space-y-3">
                  <input
                    type="email"
                    placeholder="Email address"
                    value={forgotEmail}
                    onChange={(e) => setForgotEmail(e.target.value)}
                    required
                    className="w-full bg-[#18181B] border border-white/10 focus:border-lime/50 focus:ring-1 focus:ring-lime/30 text-white rounded-xl h-12 px-4 text-sm placeholder:text-zinc-600 outline-none transition-colors"
                  />
                  <button
                    type="submit"
                    disabled={forgotLoading}
                    className="w-full btn-primary py-3 text-sm disabled:opacity-60"
                  >
                    {forgotLoading ? "Sending…" : "Send reset link"}
                  </button>
                  <button
                    type="button"
                    onClick={() => { setShowForgot(false); setForgotEmail(""); setError(""); }}
                    className="w-full text-center text-xs text-zinc-500 hover:text-lime transition-colors"
                  >
                    Back to sign in
                  </button>
                </form>
              )}
            </div>
          ) : (
            <>
              {/* Tabs */}
              <div className="flex gap-1 bg-[#18181B] rounded-lg p-1 mb-6" data-testid="auth-tabs">
                {["login", "register"].map((t) => (
                  <button
                    key={t}
                    onClick={() => { setTab(t); setError(""); setShowForgot(false); }}
                    data-testid={`tab-${t}`}
                    className={`flex-1 py-2 px-4 rounded-md text-sm font-medium transition-colors ${
                      tab === t ? "bg-[#27272A] text-white" : "text-zinc-500 hover:text-zinc-300"
                    }`}
                  >
                    {t === "login" ? "Sign In" : "Create Account"}
                  </button>
                ))}
              </div>

              {/* Google OAuth */}
              <button
                onClick={handleGoogleAuth}
                data-testid="google-auth-btn"
                className="w-full flex items-center justify-center gap-3 py-3 px-4 bg-white text-black rounded-xl font-medium text-sm hover:bg-zinc-100 transition-colors mb-4"
              >
                <svg width="18" height="18" viewBox="0 0 24 24">
                  <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
                  <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
                  <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
                  <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
                </svg>
                Continue with Google
              </button>

              <div className="flex items-center gap-3 mb-4">
                <div className="flex-1 h-px bg-white/10" />
                <span className="text-zinc-600 text-xs">or</span>
                <div className="flex-1 h-px bg-white/10" />
              </div>

              {/* Email/Password Form */}
              <form onSubmit={handleSubmit} data-testid="auth-form" className="space-y-3">
                <AnimatePresence>
                  {tab === "register" && (
                    <motion.div
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: "auto" }}
                      exit={{ opacity: 0, height: 0 }}
                      transition={{ duration: 0.2 }}
                    >
                      <input
                        type="text"
                        placeholder="Full name"
                        value={form.name}
                        onChange={(e) => setForm({ ...form, name: e.target.value })}
                        data-testid="input-name"
                        required={tab === "register"}
                        className="w-full bg-[#18181B] border border-white/10 focus:border-lime/50 focus:ring-1 focus:ring-lime/30 text-white rounded-xl h-12 px-4 text-sm placeholder:text-zinc-600 outline-none transition-colors"
                      />
                    </motion.div>
                  )}
                </AnimatePresence>

                <input
                  type="email"
                  placeholder="Email address"
                  value={form.email}
                  onChange={(e) => setForm({ ...form, email: e.target.value })}
                  data-testid="input-email"
                  required
                  className="w-full bg-[#18181B] border border-white/10 focus:border-lime/50 focus:ring-1 focus:ring-lime/30 text-white rounded-xl h-12 px-4 text-sm placeholder:text-zinc-600 outline-none transition-colors"
                />
                <input
                  type="password"
                  placeholder="Password"
                  value={form.password}
                  onChange={(e) => setForm({ ...form, password: e.target.value })}
                  data-testid="input-password"
                  required
                  className="w-full bg-[#18181B] border border-white/10 focus:border-lime/50 focus:ring-1 focus:ring-lime/30 text-white rounded-xl h-12 px-4 text-sm placeholder:text-zinc-600 outline-none transition-colors"
                />

                {tab === "login" && (
                  <div className="text-right">
                    <button
                      type="button"
                      onClick={() => setShowForgot(true)}
                      className="text-xs text-zinc-500 hover:text-lime transition-colors"
                    >
                      Forgot password?
                    </button>
                  </div>
                )}

                {error && (
                  <p data-testid="auth-error" className="text-red-400 text-sm text-center">{error}</p>
                )}

                <button
                  type="submit"
                  disabled={loading}
                  data-testid="auth-submit-btn"
                  className="w-full btn-primary py-3 text-sm disabled:opacity-60 disabled:cursor-not-allowed"
                >
                  {loading ? (
                    <span className="flex items-center justify-center gap-2">
                      <span className="w-4 h-4 border-2 border-black/30 border-t-black rounded-full animate-spin" />
                      {tab === "register" ? "Creating account..." : "Signing in..."}
                    </span>
                  ) : (
                    tab === "register" ? "Create Account" : "Sign In"
                  )}
                </button>
              </form>
            </>
          )}
        </div>

        <p className="text-center text-zinc-600 text-xs mt-4">
          By continuing, you agree to ThookAI's Terms & Privacy Policy
        </p>
      </motion.div>
    </div>
  );
}
