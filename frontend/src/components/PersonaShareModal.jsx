import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Share2,
  Copy,
  Check,
  ExternalLink,
  Trash2,
  Link2,
  Clock,
  Eye,
  ShieldAlert,
  X,
} from "lucide-react";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const EXPIRY_OPTIONS = [
  { value: "7", label: "7 days" },
  { value: "30", label: "30 days" },
  { value: "-1", label: "Never (Pro+)" },
];

export default function PersonaShareModal({ isOpen, onClose, shareStatus, onShareStatusChange }) {
  const [expiryDays, setExpiryDays] = useState("30");
  const [generating, setGenerating] = useState(false);
  const [revoking, setRevoking] = useState(false);
  const [copiedLink, setCopiedLink] = useState(false);
  const [error, setError] = useState(null);

  // Reset state when modal opens
  useEffect(() => {
    if (isOpen) {
      setCopiedLink(false);
      setError(null);
    }
  }, [isOpen]);

  const handleGenerateLink = async () => {
    setGenerating(true);
    setError(null);
    try {
      const res = await fetch(`${BACKEND_URL}/api/persona/share`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ expiry_days: parseInt(expiryDays, 10) }),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Failed to create share link");
      }
      const data = await res.json();
      onShareStatusChange({
        is_shared: true,
        share_token: data.share_token,
        share_url: data.share_url,
        expires_at: data.expires_at,
        is_permanent: data.is_permanent,
        view_count: 0,
        created_at: data.created_at,
      });
    } catch (err) {
      setError(err.message);
    } finally {
      setGenerating(false);
    }
  };

  const handleRevoke = async () => {
    if (!window.confirm("Revoke your share link? Anyone with the link will no longer be able to view your persona card.")) {
      return;
    }
    setRevoking(true);
    setError(null);
    try {
      const res = await fetch(`${BACKEND_URL}/api/persona/share`, {
        method: "DELETE",
        credentials: "include",
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Failed to revoke share link");
      }
      onShareStatusChange({ is_shared: false });
    } catch (err) {
      setError(err.message);
    } finally {
      setRevoking(false);
    }
  };

  const copyShareLink = async () => {
    // Prefer backend-provided share_url; normalize relative paths to absolute URLs, fallback to constructed URL
    const shareUrl = shareStatus?.share_url;
    const fullUrl =
      shareUrl != null
        ? (shareUrl.startsWith("/") ? `${window.location.origin}${shareUrl}` : shareUrl)
        : `${window.location.origin}/creator/${shareStatus?.share_token}`;
    try {
      await navigator.clipboard.writeText(fullUrl);
      setCopiedLink(true);
      setTimeout(() => setCopiedLink(false), 2000);
    } catch (err) {
      // Fallback: create temporary textarea for copying
      const textarea = document.createElement("textarea");
      textarea.value = fullUrl;
      textarea.style.position = "fixed";
      textarea.style.opacity = "0";
      document.body.appendChild(textarea);
      textarea.select();
      try {
        document.execCommand("copy");
        setCopiedLink(true);
        setTimeout(() => setCopiedLink(false), 2000);
      } catch (fallbackErr) {
        console.error("Fallback copy failed:", fallbackErr);
      }
      document.body.removeChild(textarea);
    }
  };

  const hasActiveShare = shareStatus?.is_shared;

  // FIXED: removed early return so AnimatePresence exit animations can fire
  return (
    <AnimatePresence>
      {isOpen && (
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 bg-black/70 z-50 flex items-center justify-center p-4"
        onClick={onClose}
      >
        <motion.div
          initial={{ scale: 0.95, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          exit={{ scale: 0.95, opacity: 0 }}
          className="bg-[#0F0F0F] border border-white/10 rounded-2xl p-6 max-w-md w-full"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="flex items-center justify-between mb-5">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-lime/10 rounded-xl flex items-center justify-center">
                <Share2 size={20} className="text-lime" />
              </div>
              <div>
                <h3 className="font-display font-bold text-white">Share Persona Card</h3>
                <p className="text-zinc-500 text-xs">Generate a public link to your persona</p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="w-8 h-8 flex items-center justify-center rounded-lg hover:bg-white/5 transition-colors"
            >
              <X size={16} className="text-zinc-500" />
            </button>
          </div>

          {/* Error message */}
          {error && (
            <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-3 mb-4">
              <p className="text-red-400 text-sm">{error}</p>
            </div>
          )}

          {hasActiveShare ? (
            /* Active share link display */
            <div className="space-y-4">
              {/* Share URL */}
              <div>
                <label className="text-xs text-zinc-500 uppercase tracking-wider mb-2 block">
                  Share Link
                </label>
                <div className="bg-white/5 rounded-lg p-3 flex items-center gap-2">
                  <Link2 size={14} className="text-zinc-500 flex-shrink-0" />
                  <input
                    type="text"
                    readOnly
                    value={shareStatus?.share_url ?? `${window.location.origin}/creator/${shareStatus?.share_token}`}
                    className="flex-1 bg-transparent text-white text-sm outline-none truncate"
                  />
                  <button
                    onClick={copyShareLink}
                    className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-all flex items-center gap-1.5 flex-shrink-0 ${
                      copiedLink
                        ? "bg-lime text-black"
                        : "bg-white/10 text-white hover:bg-white/20"
                    }`}
                  >
                    {copiedLink ? (
                      <>
                        <Check size={13} /> Copied
                      </>
                    ) : (
                      <>
                        <Copy size={13} /> Copy
                      </>
                    )}
                  </button>
                </div>
              </div>

              {/* Share details */}
              <div className="grid grid-cols-2 gap-3">
                <div className="bg-white/5 rounded-lg p-3">
                  <div className="flex items-center gap-1.5 mb-1">
                    <Clock size={12} className="text-zinc-500" />
                    <span className="text-xs text-zinc-500">Expires</span>
                  </div>
                  <p className="text-sm text-white">
                    {shareStatus?.is_permanent
                      ? "Never"
                      : shareStatus?.expires_at
                      ? new Date(shareStatus.expires_at).toLocaleDateString()
                      : "Unknown"}
                  </p>
                </div>
                <div className="bg-white/5 rounded-lg p-3">
                  <div className="flex items-center gap-1.5 mb-1">
                    <Eye size={12} className="text-zinc-500" />
                    <span className="text-xs text-zinc-500">Views</span>
                  </div>
                  <p className="text-sm text-white">
                    {(shareStatus?.view_count || 0).toLocaleString()}
                  </p>
                </div>
              </div>

              {/* Actions */}
              <div className="flex gap-2 pt-2">
                <button
                  onClick={() =>
                    window.open(`/creator/${shareStatus?.share_token}`, "_blank")
                  }
                  className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-white/5 hover:bg-white/10 rounded-lg text-sm text-white transition-colors"
                >
                  <ExternalLink size={14} /> Preview
                </button>
                <button
                  onClick={handleRevoke}
                  disabled={revoking}
                  className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-red-500/10 hover:bg-red-500/20 rounded-lg text-sm text-red-400 transition-colors disabled:opacity-50"
                >
                  {revoking ? (
                    <div className="w-4 h-4 border-2 border-red-400 border-t-transparent rounded-full animate-spin" />
                  ) : (
                    <Trash2 size={14} />
                  )}
                  Revoke Link
                </button>
              </div>

              {/* Security note */}
              <div className="flex items-start gap-2 pt-2 border-t border-white/5">
                <ShieldAlert size={14} className="text-zinc-600 mt-0.5 flex-shrink-0" />
                <p className="text-xs text-zinc-600">
                  Anyone with this link can view your persona card. Revoke at any time to disable access.
                </p>
              </div>
            </div>
          ) : (
            /* Generate new share link */
            <div className="space-y-4">
              {/* Expiry selection */}
              <div>
                <label className="text-xs text-zinc-500 uppercase tracking-wider mb-2 block">
                  Link Expiry
                </label>
                <div className="grid grid-cols-3 gap-2">
                  {EXPIRY_OPTIONS.map((option) => (
                    <button
                      key={option.value}
                      onClick={() => setExpiryDays(option.value)}
                      className={`px-3 py-2.5 rounded-lg text-sm font-medium transition-all border ${
                        expiryDays === option.value
                          ? "bg-lime/10 text-lime border-lime/30"
                          : "bg-white/5 text-zinc-400 border-white/5 hover:border-white/10"
                      }`}
                    >
                      {option.label}
                    </button>
                  ))}
                </div>
                {expiryDays === "-1" && (
                  <p className="text-xs text-zinc-600 mt-2">
                    Permanent links are available for Pro, Studio, and Agency plans. Free tier links are capped at 30 days.
                  </p>
                )}
              </div>

              {/* Generate button */}
              <button
                onClick={handleGenerateLink}
                disabled={generating}
                className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-lime text-black rounded-lg text-sm font-semibold hover:bg-lime/90 transition-colors disabled:opacity-50"
              >
                {generating ? (
                  <div className="w-4 h-4 border-2 border-black border-t-transparent rounded-full animate-spin" />
                ) : (
                  <Link2 size={16} />
                )}
                {generating ? "Generating..." : "Generate Share Link"}
              </button>

              <p className="text-xs text-zinc-600 text-center">
                Your persona card will be visible to anyone with the link. You can revoke access at any time.
              </p>
            </div>
          )}
        </motion.div>
      </motion.div>
      )}
    </AnimatePresence>
  );
}
