import { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { Zap, RefreshCw, Edit2, Check, X, Share2, Download, Copy, Globe, ExternalLink } from "lucide-react";
import { useAuth } from "@/context/AuthContext";


const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const ARCHETYPE_COLORS = {
  Educator: { bg: "bg-cyan-400/10", text: "text-cyan-400", border: "border-cyan-400/20" },
  Storyteller: { bg: "bg-violet/10", text: "text-violet", border: "border-violet/20" },
  Provocateur: { bg: "bg-pink-500/10", text: "text-pink-400", border: "border-pink-400/20" },
  Builder: { bg: "bg-lime/10", text: "text-lime", border: "border-lime/20" },
};

const UOM_LABELS = {
  burnout_risk: { label: "Burnout Risk", values: { low: "text-lime", medium: "text-yellow-400", high: "text-red-400" } },
  focus_preference: { label: "Focus Mode", values: { "single-platform": "text-cyan-400", "multi-platform": "text-violet" } },
  risk_tolerance: { label: "Risk Tolerance", values: { conservative: "text-blue-400", balanced: "text-zinc-300", bold: "text-orange-400" } },
};

const REGIONAL_ENGLISH_OPTIONS = [
  { code: "US", name: "American English", flag: "🇺🇸" },
  { code: "UK", name: "British English", flag: "🇬🇧" },
  { code: "AU", name: "Australian English", flag: "🇦🇺" },
  { code: "IN", name: "Indian English", flag: "🇮🇳" },
];

function VoiceFingerprintBars({ fingerprint = {} }) {
  const dist = fingerprint.sentence_length_distribution || {};
  const bars = [
    { label: "Sentence rhythm", value: (dist.medium ?? 0.50), desc: dist.medium ? `${Math.round((dist.medium||0.5)*100)}% medium-length sentences` : "Mixed short & medium sentences" },
    { label: "Vocabulary depth", value: (fingerprint.vocabulary_complexity ?? 0.65), desc: "Professional, accessible vocabulary" },
    { label: "Emoji usage", value: (fingerprint.emoji_frequency ?? 0.05), desc: fingerprint.emoji_frequency < 0.1 ? "Minimal, purposeful emoji use" : "Moderate emoji integration" },
    { label: "Hook strength", value: 0.85, desc: fingerprint.hook_style_preferences?.[0] || "Strong opening statements" },
    { label: "CTA clarity", value: 0.78, desc: fingerprint.cta_patterns?.[0] || "Clear, non-pushy calls-to-action" },
  ];
  return (
    <div className="space-y-3">
      {bars.map((b, i) => (
        <div key={b.label}>
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs text-zinc-400">{b.label}</span>
            <span className="text-xs font-mono text-lime">{Math.round(b.value * 100)}</span>
          </div>
          <div className="w-full h-1.5 bg-white/5 rounded-full overflow-hidden">
            <motion.div
              initial={{ width: 0 }}
              animate={{ width: `${b.value * 100}%` }}
              transition={{ delay: i * 0.1, duration: 0.7 }}
              className="h-full bg-lime rounded-full"
            />
          </div>
          <p className="text-[10px] text-zinc-600 mt-0.5">{b.desc}</p>
        </div>
      ))}
    </div>
  );
}

function EditableField({ label, value, onSave }) {
  const [editing, setEditing] = useState(false);
  const [val, setVal] = useState(value);

  const save = () => { onSave(val); setEditing(false); };
  const cancel = () => { setVal(value); setEditing(false); };

  return (
    <div>
      <p className="text-[10px] text-zinc-600 uppercase tracking-wider mb-1">{label}</p>
      {editing ? (
        <div className="flex items-center gap-2">
          <input
            value={val}
            onChange={e => setVal(e.target.value)}
            className="flex-1 bg-[#18181B] border border-lime/30 text-white rounded-lg px-3 py-1.5 text-sm outline-none"
            autoFocus
          />
          <button onClick={save} className="w-7 h-7 bg-lime rounded-lg flex items-center justify-center"><Check size={13} className="text-black" /></button>
          <button onClick={cancel} className="w-7 h-7 bg-white/5 rounded-lg flex items-center justify-center"><X size={13} className="text-zinc-400" /></button>
        </div>
      ) : (
        <div className="flex items-center gap-2 group cursor-pointer" onClick={() => setEditing(true)}>
          <p className="text-sm text-white">{value}</p>
          <Edit2 size={11} className="text-zinc-700 opacity-0 group-hover:opacity-100 transition-opacity" />
        </div>
      )}
    </div>
  );
}

export default function PersonaEngine() {
  const [persona, setPersona] = useState(null);
  const [loading, setLoading] = useState(true);
  const [shareStatus, setShareStatus] = useState(null);
  const [shareLoading, setShareLoading] = useState(false);
  const [showShareModal, setShowShareModal] = useState(false);
  const [copiedLink, setCopiedLink] = useState(false);
  const [downloadingImage, setDownloadingImage] = useState(false);
  const [selectedRegion, setSelectedRegion] = useState("US");
  const [showRegionDropdown, setShowRegionDropdown] = useState(false);
  const personaCardRef = useRef(null);
  const { user, checkAuth } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    (async () => {
      try {
        const res = await fetch(`${BACKEND_URL}/api/persona/me`, { credentials: "include" });
        if (res.ok) {
          const data = await res.json();
          setPersona(data);
          setSelectedRegion(data?.card?.regional_english || "US");
        }
        // Also fetch share status
        const shareRes = await fetch(`${BACKEND_URL}/api/persona/share/status`, { credentials: "include" });
        if (shareRes.ok) {
          setShareStatus(await shareRes.json());
        }
      } catch {}
      setLoading(false);
    })();
  }, []);

  const handleSaveField = async (field, value) => {
    const updatedCard = { ...persona.card, [field]: value };
    try {
      await fetch(`${BACKEND_URL}/api/persona/me`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ card: updatedCard }),
      });
      setPersona(p => ({ ...p, card: updatedCard }));
    } catch {}
  };

  const handleReset = async () => {
    if (!window.confirm("Reset your Persona Engine and redo the interview?")) return;
    await fetch(`${BACKEND_URL}/api/persona/me`, { method: "DELETE", credentials: "include" });
    await checkAuth(); // refresh user state so onboarding_completed=false
    navigate("/onboarding");
  };

  // Share functionality
  const handleShare = async () => {
    setShareLoading(true);
    try {
      const res = await fetch(`${BACKEND_URL}/api/persona/share`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ expiry_days: 30 }),
      });
      if (res.ok) {
        const data = await res.json();
        setShareStatus({
          is_shared: true,
          share_token: data.share_token,
          share_url: data.share_url,
          expires_at: data.expires_at,
          is_permanent: data.is_permanent,
          view_count: 0,
        });
        setShowShareModal(true);
      }
    } catch (err) {
      console.error("Failed to create share link:", err);
    } finally {
      setShareLoading(false);
    }
  };

  const handleRevokeShare = async () => {
    if (!window.confirm("Revoke your persona share link? Anyone with the link will no longer be able to view it.")) return;
    try {
      await fetch(`${BACKEND_URL}/api/persona/share`, {
        method: "DELETE",
        credentials: "include",
      });
      setShareStatus({ is_shared: false });
      setShowShareModal(false);
    } catch {}
  };

  const copyShareLink = async () => {
    const fullUrl = `${window.location.origin}/creator/${shareStatus?.share_token}`;
    try {
      await navigator.clipboard.writeText(fullUrl);
      setCopiedLink(true);
      setTimeout(() => setCopiedLink(false), 2000);
    } catch (err) {
      console.error('Failed to copy to clipboard:', err);
      // Fallback: create temporary textarea for copying
      const textarea = document.createElement('textarea');
      textarea.value = fullUrl;
      textarea.style.position = 'fixed';
      textarea.style.opacity = '0';
      document.body.appendChild(textarea);
      textarea.select();
      try {
        document.execCommand('copy');
        setCopiedLink(true);
        setTimeout(() => setCopiedLink(false), 2000);
      } catch (fallbackErr) {
        console.error('Fallback copy failed:', fallbackErr);
      }
      document.body.removeChild(textarea);
    }
  };

  // Download as image functionality
  const handleDownloadImage = async () => {
    if (!personaCardRef.current) return;
    setDownloadingImage(true);
    try {
      // Dynamically import html2canvas
      const html2canvas = (await import("html2canvas")).default;
      const canvas = await html2canvas(personaCardRef.current, {
        backgroundColor: "#0A0A0A",
        scale: 2,
        useCORS: true,
        logging: false,
      });
      const link = document.createElement("a");
      link.download = `${user?.name || "creator"}-persona-card.png`;
      link.href = canvas.toDataURL("image/png");
      link.click();
    } catch (err) {
      console.error("Failed to download image:", err);
    } finally {
      setDownloadingImage(false);
    }
  };

  // Regional English update
  const handleRegionalEnglishChange = async (code) => {
    setSelectedRegion(code);
    setShowRegionDropdown(false);
    try {
      await fetch(`${BACKEND_URL}/api/persona/regional-english`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ regional_english: code }),
      });
      setPersona(p => ({ ...p, card: { ...p.card, regional_english: code } }));
    } catch {}
  };

  if (loading) return (
    <main className="flex-1 flex items-center justify-center p-6">
      <div className="w-6 h-6 border-2 border-lime border-t-transparent rounded-full animate-spin" />
    </main>
  );

  if (!persona) return (
    <main className="flex-1 flex items-center justify-center p-6">
      <div className="text-center max-w-sm">
        <div className="w-16 h-16 bg-violet/10 rounded-2xl flex items-center justify-center mx-auto mb-5">
          <Zap size={28} className="text-violet" />
        </div>
        <h2 className="font-display font-bold text-2xl text-white mb-2">Persona Engine not set up</h2>
        <p className="text-zinc-500 text-sm mb-5">Complete the 15-minute onboarding to activate your AI voice clone.</p>
        <button onClick={() => navigate("/onboarding")} data-testid="setup-persona-btn" className="btn-primary flex items-center gap-2 mx-auto">
          <Zap size={14} /> Set up Persona Engine
        </button>
      </div>
    </main>
  );

  const card = persona.card || {};
  const archetype = card.personality_archetype || "Educator";
  const colors = ARCHETYPE_COLORS[archetype] || ARCHETYPE_COLORS.Educator;
  const uom = persona.uom || {};
  const currentRegion = REGIONAL_ENGLISH_OPTIONS.find(r => r.code === selectedRegion) || REGIONAL_ENGLISH_OPTIONS[0];

  return (
    <main className="p-6 space-y-6 max-w-5xl" data-testid="persona-engine-page">
      {/* Share Modal */}
      <AnimatePresence>
        {showShareModal && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/70 z-50 flex items-center justify-center p-4"
            onClick={() => setShowShareModal(false)}
          >
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              className="bg-[#0F0F0F] border border-white/10 rounded-2xl p-6 max-w-md w-full"
              onClick={e => e.stopPropagation()}
            >
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 bg-lime/10 rounded-xl flex items-center justify-center">
                  <Share2 size={20} className="text-lime" />
                </div>
                <div>
                  <h3 className="font-display font-bold text-white">Share Your Persona Card</h3>
                  <p className="text-zinc-500 text-xs">Anyone with this link can view your card</p>
                </div>
              </div>
              
              <div className="bg-white/5 rounded-lg p-3 flex items-center gap-2 mb-4">
                <input
                  type="text"
                  readOnly
                  value={`${window.location.origin}/creator/${shareStatus?.share_token}`}
                  className="flex-1 bg-transparent text-white text-sm outline-none truncate"
                />
                <button
                  onClick={copyShareLink}
                  className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${
                    copiedLink 
                      ? "bg-lime text-black" 
                      : "bg-white/10 text-white hover:bg-white/20"
                  }`}
                >
                  {copiedLink ? "Copied!" : "Copy"}
                </button>
              </div>

              <div className="flex items-center justify-between text-xs text-zinc-500 mb-4">
                <span>
                  {shareStatus?.is_permanent 
                    ? "Permanent link (Pro+)" 
                    : `Expires ${new Date(shareStatus?.expires_at).toLocaleDateString()}`
                  }
                </span>
                <span>{shareStatus?.view_count || 0} views</span>
              </div>

              <div className="flex gap-2">
                <button
                  onClick={() => window.open(`/creator/${shareStatus?.share_token}`, "_blank")}
                  className="flex-1 btn-ghost text-sm py-2 flex items-center justify-center gap-2"
                >
                  <ExternalLink size={14} /> Preview
                </button>
                <button
                  onClick={handleRevokeShare}
                  className="flex-1 btn-ghost text-sm py-2 text-red-400 hover:bg-red-400/10"
                >
                  Revoke Link
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="w-2 h-2 bg-lime rounded-full animate-pulse" />
            <span className="text-xs text-lime font-mono">ENGINE ACTIVE</span>
          </div>
          <h2 className="font-display font-bold text-2xl text-white">Your Persona Engine</h2>
          <p className="text-zinc-500 text-sm">Your AI voice clone. Edit any field to fine-tune your identity.</p>
        </div>
        <div className="flex items-center gap-2">
          {/* Share button */}
          <button
            onClick={shareStatus?.is_shared ? () => setShowShareModal(true) : handleShare}
            disabled={shareLoading}
            data-testid="share-persona-btn"
            className="flex items-center gap-2 btn-ghost text-xs px-4 py-2 text-lime border border-lime/30 hover:bg-lime/10"
          >
            {shareLoading ? (
              <div className="w-4 h-4 border-2 border-lime border-t-transparent rounded-full animate-spin" />
            ) : (
              <Share2 size={13} />
            )}
            {shareStatus?.is_shared ? "View Share Link" : "Share Card"}
          </button>
          {/* Download button */}
          <button
            onClick={handleDownloadImage}
            disabled={downloadingImage}
            data-testid="download-persona-btn"
            className="flex items-center gap-2 btn-ghost text-xs px-4 py-2 text-zinc-400 hover:text-white"
          >
            {downloadingImage ? (
              <div className="w-4 h-4 border-2 border-zinc-400 border-t-transparent rounded-full animate-spin" />
            ) : (
              <Download size={13} />
            )}
            Download
          </button>
          {/* Re-interview button */}
          <button
            onClick={handleReset}
            data-testid="reset-persona-btn"
            className="flex items-center gap-2 btn-ghost text-xs px-4 py-2 text-zinc-500"
          >
            <RefreshCw size={13} /> Re-interview
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Persona Card */}
        <div className="lg:col-span-2 space-y-4">
          <motion.div ref={personaCardRef} initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} className="card-thook p-6" data-testid="persona-card-full">
            {/* Avatar + archetype */}
            <div className="flex items-center gap-3 mb-5">
              <div className="w-11 h-11 rounded-xl bg-violet/20 flex items-center justify-center overflow-hidden flex-shrink-0">
                {user?.picture ? <img src={user.picture} alt="" className="w-full h-full object-cover" /> : (
                  <span className="font-bold text-violet text-lg">{user?.name?.[0]?.toUpperCase() || "C"}</span>
                )}
              </div>
              <div className="flex-1">
                <p className="text-sm font-semibold text-white">{user?.name}</p>
                <div className="flex items-center gap-2">
                  <span className={`text-xs font-semibold px-2 py-0.5 rounded-full border ${colors.bg} ${colors.text} ${colors.border}`}>{archetype}</span>
                </div>
              </div>
              {/* Regional English Selector */}
              <div className="relative">
                <button
                  onClick={() => setShowRegionDropdown(!showRegionDropdown)}
                  className="flex items-center gap-2 px-3 py-1.5 bg-white/5 rounded-lg border border-white/10 hover:border-white/20 transition-colors"
                >
                  <Globe size={14} className="text-zinc-400" />
                  <span className="text-sm">{currentRegion.flag}</span>
                  <span className="text-xs text-zinc-400">{currentRegion.code}</span>
                </button>
                <AnimatePresence>
                  {showRegionDropdown && (
                    <motion.div
                      initial={{ opacity: 0, y: -10 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -10 }}
                      className="absolute right-0 top-full mt-1 bg-[#18181B] border border-white/10 rounded-lg overflow-hidden z-10 min-w-[180px]"
                    >
                      {REGIONAL_ENGLISH_OPTIONS.map(option => (
                        <button
                          key={option.code}
                          onClick={() => handleRegionalEnglishChange(option.code)}
                          className={`w-full flex items-center gap-3 px-4 py-2.5 text-left hover:bg-white/5 transition-colors ${
                            selectedRegion === option.code ? "bg-lime/10" : ""
                          }`}
                        >
                          <span className="text-lg">{option.flag}</span>
                          <div>
                            <p className="text-sm text-white">{option.name}</p>
                            <p className="text-xs text-zinc-500">{option.code}</p>
                          </div>
                          {selectedRegion === option.code && (
                            <Check size={14} className="text-lime ml-auto" />
                          )}
                        </button>
                      ))}
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            </div>

            <div className="space-y-4">
              <EditableField label="Writing Voice Descriptor" value={card.writing_voice_descriptor || "—"} onSave={v => handleSaveField("writing_voice_descriptor", v)} />
              <EditableField label="Content Niche Signature" value={card.content_niche_signature || "—"} onSave={v => handleSaveField("content_niche_signature", v)} />
              <EditableField label="Inferred Audience Profile" value={card.inferred_audience_profile || "—"} onSave={v => handleSaveField("inferred_audience_profile", v)} />
              <EditableField label="Top Content Format" value={card.top_content_format || "—"} onSave={v => handleSaveField("top_content_format", v)} />
              <EditableField label="Hook Style" value={card.hook_style || "—"} onSave={v => handleSaveField("hook_style", v)} />
            </div>

            {/* Platforms + Pillars */}
            <div className="mt-5 space-y-3">
              <div>
                <p className="text-[10px] text-zinc-600 uppercase tracking-wider mb-2">Focus Platforms</p>
                <div className="flex flex-wrap gap-2">
                  {(card.focus_platforms || []).map(p => (
                    <span key={p} className="text-xs bg-white/8 text-zinc-300 rounded-full px-3 py-1 border border-white/8">{p}</span>
                  ))}
                </div>
              </div>
              <div>
                <p className="text-[10px] text-zinc-600 uppercase tracking-wider mb-2">Content Pillars</p>
                <div className="flex flex-wrap gap-2">
                  {(card.content_pillars || []).map(p => (
                    <span key={p} className="text-xs bg-lime/8 text-lime/70 rounded-full px-3 py-1">{p}</span>
                  ))}
                </div>
              </div>
            </div>
          </motion.div>

          {/* Voice Fingerprint */}
          <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }} className="card-thook p-5">
            <h3 className="font-display font-semibold text-white mb-1">Voice Fingerprint</h3>
            <p className="text-zinc-500 text-xs mb-4">Calibrated from your interview and content analysis. Updates as you create.</p>
            <VoiceFingerprintBars fingerprint={persona.voice_fingerprint || {}} />
          </motion.div>
        </div>

        {/* Right: UOM + Learning Signals */}
        <div className="space-y-4">
          {/* AI Strategy Profile (simplified UOM) */}
          <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 }} className="card-thook p-5" data-testid="uom-panel">
            <h3 className="font-display font-semibold text-white mb-1 text-sm">AI Strategy Profile</h3>
            <p className="text-zinc-600 text-xs mb-4">How Thook adapts its behavior for you. Updates automatically.</p>
            <div className="space-y-3">
              {Object.entries(UOM_LABELS).map(([key, config]) => {
                const val = uom[key] || "—";
                const colorClass = config.values[val] || "text-zinc-400";
                return (
                  <div key={key} className="flex items-center justify-between">
                    <span className="text-xs text-zinc-500">{config.label}</span>
                    <span className={`text-xs font-semibold capitalize ${colorClass}`}>{val.replace(/-/g, " ")}</span>
                  </div>
                );
              })}
              <div className="flex items-center justify-between">
                <span className="text-xs text-zinc-500">Strategy Maturity</span>
                <div className="flex gap-1">
                  {[1,2,3,4,5].map(n => (
                    <div key={n} className={`w-1.5 h-1.5 rounded-full ${n <= (uom.strategy_maturity || 2) ? "bg-lime" : "bg-white/10"}`} />
                  ))}
                </div>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-xs text-zinc-500">Trust in Thook</span>
                <div className="w-16 h-1.5 bg-white/5 rounded-full overflow-hidden">
                  <div className="h-full bg-violet rounded-full" style={{ width: `${(uom.trust_in_thook || 0.5) * 100}%` }} />
                </div>
              </div>
            </div>
          </motion.div>

          {/* Learning Signals */}
          <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }} className="card-thook p-5">
            <h3 className="font-display font-semibold text-white mb-1 text-sm">Learning Signals</h3>
            <p className="text-zinc-500 text-xs mb-4">Tracks how your Persona evolves as you create content.</p>
            <div className="text-center py-4">
              <p className="text-zinc-700 text-xs">No learning signals yet</p>
              <p className="text-zinc-800 text-xs mt-1">Create your first post to start the learning loop</p>
            </div>
            <div className="space-y-2">
              {[
                { label: "Edits logged", value: 0 },
                { label: "Posts approved", value: 0 },
                { label: "Patterns avoided", value: 0 },
              ].map(item => (
                <div key={item.label} className="flex items-center justify-between">
                  <span className="text-xs text-zinc-600">{item.label}</span>
                  <span className="text-xs font-mono text-zinc-600">{item.value}</span>
                </div>
              ))}
            </div>
          </motion.div>

          {/* Style Notes */}
          {card.writing_style_notes?.length > 0 && (
            <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.25 }} className="card-thook p-5">
              <h3 className="font-display font-semibold text-white mb-3 text-sm">Style Notes</h3>
              <div className="space-y-2">
                {card.writing_style_notes.map((note, i) => (
                  <div key={i} className="flex items-start gap-2">
                    <span className="text-lime text-xs mt-0.5">▸</span>
                    <p className="text-xs text-zinc-500 leading-relaxed">{note}</p>
                  </div>
                ))}
              </div>
            </motion.div>
          )}
        </div>
      </div>
    </main>
  );
}
