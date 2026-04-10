import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { Cookie, X } from "lucide-react";

const CONSENT_KEY = "thookai_cookie_consent";

export default function CookieConsent() {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const consent = localStorage.getItem(CONSENT_KEY);
    if (!consent) {
      // Show banner after a short delay so it doesn't flash on load
      const timer = setTimeout(() => setVisible(true), 1500);
      return () => clearTimeout(timer);
    }
  }, []);

  const accept = () => {
    localStorage.setItem(CONSENT_KEY, "accepted");
    setVisible(false);
    // Re-enable PostHog if previously opted out
    if (window.posthog && window.posthog.has_opted_out_capturing?.()) {
      window.posthog.opt_in_capturing();
    }
  };

  const decline = () => {
    localStorage.setItem(CONSENT_KEY, "declined");
    setVisible(false);
    if (window.posthog) {
      window.posthog.opt_out_capturing();
    }
  };

  return (
    <AnimatePresence>
      {visible && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: 20 }}
          className="fixed bottom-4 left-4 right-4 md:left-auto md:right-6 md:max-w-md z-50"
        >
          <div className="bg-[#18181B] border border-white/10 rounded-2xl p-4 shadow-2xl">
            <div className="flex items-start gap-3">
              <div className="w-8 h-8 rounded-lg bg-lime/10 flex items-center justify-center flex-shrink-0 mt-0.5">
                <Cookie size={16} className="text-lime" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm text-white font-medium mb-1">Cookie preferences</p>
                <p className="text-xs text-zinc-400 leading-relaxed">
                  We use essential cookies for authentication and optional analytics cookies (PostHog) to improve the product.{" "}
                  <Link to="/privacy" className="text-lime hover:underline">Privacy Policy</Link>
                </p>
                <div className="flex gap-2 mt-3">
                  <button
                    onClick={accept}
                    className="flex-1 bg-lime text-black text-xs font-semibold rounded-lg py-2 px-3 hover:bg-lime/90 transition-colors"
                  >
                    Accept all
                  </button>
                  <button
                    onClick={decline}
                    className="flex-1 bg-white/5 text-zinc-400 text-xs font-semibold rounded-lg py-2 px-3 hover:bg-white/10 transition-colors"
                  >
                    Essential only
                  </button>
                </div>
              </div>
              <button onClick={decline} aria-label="Dismiss cookie banner" className="text-zinc-600 hover:text-zinc-400 transition-colors">
                <X size={14} />
              </button>
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
