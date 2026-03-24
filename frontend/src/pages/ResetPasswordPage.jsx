import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { motion } from "framer-motion";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

export default function ResetPasswordPage() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token") || "";
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    if (password.length < 8) {
      setError("Password must be at least 8 characters");
      return;
    }
    if (password !== confirm) {
      setError("Passwords do not match");
      return;
    }
    if (!token) {
      setError("Missing reset token. Open the link from your email.");
      return;
    }
    setLoading(true);
    try {
      const res = await fetch(`${BACKEND_URL}/api/auth/reset-password`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token, new_password: password }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        const d = data.detail;
        const msg = typeof d === "string" ? d : d?.message || "Reset failed";
        throw new Error(msg);
      }
      setSuccess(true);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#050505] flex items-center justify-center p-4 relative overflow-hidden">
      <div className="absolute inset-0 hero-glow pointer-events-none" />
      <motion.div
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="w-full max-w-md"
      >
        <div className="text-center mb-8">
          <a href="/" className="inline-flex items-center gap-2">
            <div className="w-9 h-9 bg-lime rounded-lg flex items-center justify-center">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z" fill="#000" stroke="#000" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </div>
            <span className="font-display font-bold text-xl text-white">Thook</span>
          </a>
        </div>

        <div className="card-thook p-6">
          {success ? (
            <div className="text-center space-y-4">
              <p className="text-white text-sm">Password reset! Sign in now.</p>
              <Link to="/auth" className="inline-block btn-primary py-2.5 px-6 text-sm">
                Go to sign in
              </Link>
            </div>
          ) : (
            <>
              <h1 className="text-white font-display font-semibold text-lg mb-1">Set new password</h1>
              <p className="text-zinc-500 text-xs mb-4">Choose a password with at least 8 characters.</p>
              <form onSubmit={handleSubmit} className="space-y-3">
                <input
                  type="password"
                  placeholder="New password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  minLength={8}
                  className="w-full bg-[#18181B] border border-white/10 focus:border-lime/50 focus:ring-1 focus:ring-lime/30 text-white rounded-xl h-12 px-4 text-sm placeholder:text-zinc-600 outline-none transition-colors"
                />
                <input
                  type="password"
                  placeholder="Confirm password"
                  value={confirm}
                  onChange={(e) => setConfirm(e.target.value)}
                  required
                  minLength={8}
                  className="w-full bg-[#18181B] border border-white/10 focus:border-lime/50 focus:ring-1 focus:ring-lime/30 text-white rounded-xl h-12 px-4 text-sm placeholder:text-zinc-600 outline-none transition-colors"
                />
                {error && <p className="text-red-400 text-sm text-center">{error}</p>}
                <button
                  type="submit"
                  disabled={loading}
                  className="w-full btn-primary py-3 text-sm disabled:opacity-60"
                >
                  {loading ? "Updating…" : "Reset password"}
                </button>
              </form>
              <p className="text-center mt-4">
                <Link to="/auth" className="text-xs text-zinc-500 hover:text-lime transition-colors">
                  Back to sign in
                </Link>
              </p>
            </>
          )}
        </div>
      </motion.div>
    </div>
  );
}
