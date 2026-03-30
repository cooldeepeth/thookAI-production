import { useState, useEffect, useRef } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import {
  Zap,
  Sparkles,
  Copy,
  Check,
  ChevronRight,
  ArrowRight,
  Twitter,
  Linkedin,
  Target,
  Users,
  Mic2,
  BarChart3,
  Brain,
  Flame,
  Share2,
  ExternalLink,
} from "lucide-react";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

// ─── Archetype styling maps ──────────────────────────────
const ARCHETYPE_CONFIG = {
  Educator: {
    gradient: "from-cyan-500/20 via-cyan-400/10 to-transparent",
    text: "text-cyan-400",
    bg: "bg-cyan-400/10",
    border: "border-cyan-400/30",
    glow: "shadow-[0_0_40px_rgba(34,211,238,0.15)]",
    ring: "ring-cyan-400/20",
    bar: "bg-cyan-400",
  },
  Storyteller: {
    gradient: "from-violet-500/20 via-violet-400/10 to-transparent",
    text: "text-violet-400",
    bg: "bg-violet-400/10",
    border: "border-violet-400/30",
    glow: "shadow-[0_0_40px_rgba(167,139,250,0.15)]",
    ring: "ring-violet-400/20",
    bar: "bg-violet-400",
  },
  Provocateur: {
    gradient: "from-pink-500/20 via-pink-400/10 to-transparent",
    text: "text-pink-400",
    bg: "bg-pink-400/10",
    border: "border-pink-400/30",
    glow: "shadow-[0_0_40px_rgba(244,114,182,0.15)]",
    ring: "ring-pink-400/20",
    bar: "bg-pink-400",
  },
  Builder: {
    gradient: "from-lime-500/20 via-lime-400/10 to-transparent",
    text: "text-lime",
    bg: "bg-lime/10",
    border: "border-lime/30",
    glow: "shadow-[0_0_40px_rgba(212,255,0,0.15)]",
    ring: "ring-lime/20",
    bar: "bg-lime",
  },
  Entertainer: {
    gradient: "from-amber-500/20 via-amber-400/10 to-transparent",
    text: "text-amber-400",
    bg: "bg-amber-400/10",
    border: "border-amber-400/30",
    glow: "shadow-[0_0_40px_rgba(251,191,36,0.15)]",
    ring: "ring-amber-400/20",
    bar: "bg-amber-400",
  },
};

const PLATFORM_OPTIONS = [
  { value: "linkedin", label: "LinkedIn", icon: Linkedin },
  { value: "x", label: "X (Twitter)", icon: Twitter },
  { value: "general", label: "General", icon: Sparkles },
];

// ─── Voice Metric Bar ────────────────────────────────────
function VoiceMetricBar({ label, value, delay = 0, barClass = "bg-lime" }) {
  const clamped = Math.max(0, Math.min(100, value));
  return (
    <div className="space-y-1.5">
      <div className="flex justify-between text-xs">
        <span className="text-zinc-500">{label}</span>
        <span className="text-zinc-300 font-mono">{Math.round(clamped)}</span>
      </div>
      <div className="h-2 bg-white/5 rounded-full overflow-hidden">
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${clamped}%` }}
          transition={{ duration: 1, delay, ease: "easeOut" }}
          className={`h-full rounded-full ${barClass}`}
        />
      </div>
    </div>
  );
}

// ─── Analysis Loading State ──────────────────────────────
const loadingSteps = [
  "Reading your writing patterns...",
  "Mapping sentence rhythm...",
  "Detecting your hook style...",
  "Identifying content pillars...",
  "Profiling your archetype...",
  "Building your persona card...",
];

function AnalysisLoader() {
  const [step, setStep] = useState(0);
  useEffect(() => {
    const interval = setInterval(() => {
      setStep((prev) => (prev < loadingSteps.length - 1 ? prev + 1 : prev));
    }, 2800);
    return () => clearInterval(interval);
  }, []);

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex flex-col items-center gap-6 py-16"
    >
      <div className="relative">
        <div className="w-16 h-16 border-2 border-lime/30 border-t-lime rounded-full animate-spin" />
        <div className="absolute inset-0 flex items-center justify-center">
          <Brain size={24} className="text-lime animate-pulse" />
        </div>
      </div>
      <div className="text-center space-y-2">
        <AnimatePresence mode="wait">
          <motion.p
            key={step}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            className="text-white font-medium"
          >
            {loadingSteps[step]}
          </motion.p>
        </AnimatePresence>
        <div className="flex items-center justify-center gap-1.5 mt-3">
          {loadingSteps.map((_, i) => (
            <div
              key={i}
              className={`h-1 rounded-full transition-all duration-500 ${
                i <= step
                  ? "w-6 bg-lime"
                  : "w-2 bg-white/10"
              }`}
            />
          ))}
        </div>
      </div>
    </motion.div>
  );
}

// ─── Persona Card Result ─────────────────────────────────
function PersonaCardResult({ card, name, cardId }) {
  const [copied, setCopied] = useState(false);
  const cardRef = useRef(null);
  const navigate = useNavigate();

  const archetype = card.personality_archetype || "Builder";
  const cfg = ARCHETYPE_CONFIG[archetype] || ARCHETYPE_CONFIG.Builder;
  const metrics = card.voice_metrics || {};
  const shareUrl = `${window.location.origin}/discover/${cardId}`;

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(shareUrl);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback
      const input = document.createElement("input");
      input.value = shareUrl;
      document.body.appendChild(input);
      input.select();
      document.execCommand("copy");
      document.body.removeChild(input);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const twitterShareUrl = `https://twitter.com/intent/tweet?text=${encodeURIComponent(
    `I just discovered my Creator DNA: "${card.writing_voice_descriptor}" ${card.personality_archetype}.\n\nFind yours for free:`
  )}&url=${encodeURIComponent(shareUrl)}`;

  const linkedinShareUrl = `https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(shareUrl)}`;

  return (
    <motion.div
      initial={{ opacity: 0, y: 30 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6 }}
      className="space-y-8"
    >
      {/* ─── The Card ─────────────────────────────────── */}
      <div
        ref={cardRef}
        className={`bg-[#0A0A0A] border border-white/10 rounded-3xl overflow-hidden ${cfg.glow}`}
      >
        {/* Header with gradient */}
        <div className={`p-8 pb-6 bg-gradient-to-br ${cfg.gradient} border-b border-white/5`}>
          <div className="flex items-center gap-4">
            <div
              className={`w-16 h-16 rounded-2xl ${cfg.bg} flex items-center justify-center ring-2 ${cfg.ring}`}
            >
              <span className={`font-display font-bold text-2xl ${cfg.text}`}>
                {(name || "C")[0].toUpperCase()}
              </span>
            </div>
            <div className="flex-1 min-w-0">
              <h2 className="font-display font-bold text-2xl text-white truncate">
                {name || "Creator"}
              </h2>
              <div className="flex items-center gap-2 mt-1">
                <span
                  className={`text-sm font-semibold px-3 py-1 rounded-full border ${cfg.bg} ${cfg.text} ${cfg.border}`}
                >
                  {archetype}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Body */}
        <div className="p-8 space-y-6">
          {/* Voice descriptor */}
          <div>
            <p className="text-[10px] text-zinc-600 uppercase tracking-widest font-mono mb-2">
              Voice
            </p>
            <p className="text-white text-lg font-medium leading-relaxed">
              &ldquo;{card.writing_voice_descriptor}&rdquo;
            </p>
          </div>

          {/* Niche + audience row */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {card.content_niche_signature && (
              <div className="bg-white/[0.03] rounded-xl p-4 border border-white/5">
                <div className="flex items-center gap-2 mb-1.5">
                  <Target size={13} className={cfg.text} />
                  <span className="text-[10px] text-zinc-600 uppercase tracking-wider">
                    Niche
                  </span>
                </div>
                <p className="text-white text-sm">{card.content_niche_signature}</p>
              </div>
            )}
            {card.audience_vibe && (
              <div className="bg-white/[0.03] rounded-xl p-4 border border-white/5">
                <div className="flex items-center gap-2 mb-1.5">
                  <Users size={13} className={cfg.text} />
                  <span className="text-[10px] text-zinc-600 uppercase tracking-wider">
                    Audience
                  </span>
                </div>
                <p className="text-white text-sm">{card.audience_vibe}</p>
              </div>
            )}
          </div>

          {/* Tone + hook style */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {card.tone && (
              <div className="bg-white/[0.03] rounded-xl p-4 border border-white/5">
                <div className="flex items-center gap-2 mb-1.5">
                  <Mic2 size={13} className={cfg.text} />
                  <span className="text-[10px] text-zinc-600 uppercase tracking-wider">
                    Tone
                  </span>
                </div>
                <p className="text-white text-sm">{card.tone}</p>
              </div>
            )}
            {card.hook_style && (
              <div className="bg-white/[0.03] rounded-xl p-4 border border-white/5">
                <div className="flex items-center gap-2 mb-1.5">
                  <Flame size={13} className={cfg.text} />
                  <span className="text-[10px] text-zinc-600 uppercase tracking-wider">
                    Hook Style
                  </span>
                </div>
                <p className="text-white text-sm">{card.hook_style}</p>
              </div>
            )}
          </div>

          {/* Voice Fingerprint metrics */}
          <div className="bg-white/[0.03] rounded-xl p-5 border border-white/5">
            <div className="flex items-center gap-2 mb-4">
              <BarChart3 size={14} className={cfg.text} />
              <span className="text-[10px] text-zinc-600 uppercase tracking-widest font-mono">
                Voice Fingerprint
              </span>
            </div>
            <div className="space-y-3">
              <VoiceMetricBar
                label="Sentence Rhythm"
                value={metrics.sentence_rhythm ?? 60}
                delay={0.1}
                barClass={cfg.bar}
              />
              <VoiceMetricBar
                label="Vocabulary Depth"
                value={metrics.vocabulary_depth ?? 55}
                delay={0.2}
                barClass={cfg.bar}
              />
              <VoiceMetricBar
                label="Hook Strength"
                value={metrics.hook_strength ?? 65}
                delay={0.3}
                barClass={cfg.bar}
              />
              <VoiceMetricBar
                label="CTA Clarity"
                value={metrics.cta_clarity ?? 50}
                delay={0.4}
                barClass={cfg.bar}
              />
              <VoiceMetricBar
                label="Emoji Usage"
                value={metrics.emoji_usage ?? 20}
                delay={0.5}
                barClass={cfg.bar}
              />
            </div>
          </div>

          {/* Content pillars */}
          {card.content_pillars?.length > 0 && (
            <div>
              <p className="text-[10px] text-zinc-600 uppercase tracking-widest font-mono mb-3">
                Content Pillars
              </p>
              <div className="flex flex-wrap gap-2">
                {card.content_pillars.map((pillar, i) => (
                  <motion.span
                    key={i}
                    initial={{ opacity: 0, scale: 0.9 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ delay: 0.6 + i * 0.1 }}
                    className={`text-sm px-3 py-1.5 rounded-full ${cfg.bg} ${cfg.text} border ${cfg.border}`}
                  >
                    {pillar}
                  </motion.span>
                ))}
              </div>
            </div>
          )}

          {/* Strengths */}
          {card.strengths?.length > 0 && (
            <div>
              <p className="text-[10px] text-zinc-600 uppercase tracking-widest font-mono mb-3">
                Strengths
              </p>
              <div className="flex flex-wrap gap-2">
                {card.strengths.map((strength, i) => (
                  <motion.span
                    key={i}
                    initial={{ opacity: 0, scale: 0.9 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ delay: 0.8 + i * 0.1 }}
                    className="text-sm px-3 py-1.5 rounded-full bg-white/5 text-zinc-300 border border-white/10"
                  >
                    {strength}
                  </motion.span>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Watermark footer */}
        <div className="px-8 py-3.5 bg-white/[0.02] border-t border-white/5 flex items-center justify-center">
          <div className="flex items-center gap-2 text-zinc-600 text-xs">
            <span>Powered by</span>
            <div className="flex items-center gap-1">
              <div className="w-4 h-4 rounded bg-lime flex items-center justify-center">
                <Zap size={10} className="text-black" />
              </div>
              <span className="font-display font-semibold text-zinc-400">
                ThookAI
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* ─── Share buttons ────────────────────────────── */}
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4 }}
        className="space-y-4"
      >
        <p className="text-center text-zinc-500 text-sm">Share your card</p>
        <div className="flex items-center justify-center gap-3 flex-wrap">
          <button
            onClick={handleCopy}
            className={`flex items-center gap-2 px-5 py-2.5 rounded-full text-sm font-medium transition-all ${
              copied
                ? "bg-lime/20 text-lime border border-lime/30"
                : "bg-white/8 text-white border border-white/10 hover:bg-white/14 hover:border-white/20"
            }`}
          >
            {copied ? <Check size={15} /> : <Copy size={15} />}
            {copied ? "Copied!" : "Copy Link"}
          </button>
          <a
            href={twitterShareUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-2 px-5 py-2.5 rounded-full text-sm font-medium bg-white/8 text-white border border-white/10 hover:bg-white/14 hover:border-white/20 transition-all"
          >
            <Twitter size={15} />
            Share on X
          </a>
          <a
            href={linkedinShareUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-2 px-5 py-2.5 rounded-full text-sm font-medium bg-white/8 text-white border border-white/10 hover:bg-white/14 hover:border-white/20 transition-all"
          >
            <Linkedin size={15} />
            Share on LinkedIn
          </a>
        </div>
      </motion.div>

      {/* ─── Signup CTA ───────────────────────────────── */}
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.6 }}
        className="text-center py-6"
      >
        <div className="card-thook p-8 border-lime/10 bg-lime/[0.03]">
          <Sparkles size={28} className="text-lime mx-auto mb-3" />
          <h3 className="font-display font-bold text-xl text-white mb-2">
            Want to create content in this voice?
          </h3>
          <p className="text-zinc-500 text-sm mb-5 max-w-md mx-auto">
            ThookAI uses 15+ AI agents that learn your exact style and generate
            platform-ready content for LinkedIn, X, and Instagram.
          </p>
          <button
            onClick={() => navigate("/auth")}
            className="btn-primary text-base px-8 py-3 inline-flex items-center gap-2"
          >
            Sign Up Free
            <ArrowRight size={16} />
          </button>
          <p className="text-zinc-600 text-xs mt-3">
            50 free credits. No credit card required.
          </p>
        </div>
      </motion.div>
    </motion.div>
  );
}

// ─── Main Page Component ─────────────────────────────────
export default function ViralCard() {
  const { cardId: routeCardId } = useParams();
  const navigate = useNavigate();

  // Form state
  const [postsText, setPostsText] = useState("");
  const [platform, setPlatform] = useState("general");
  const [name, setName] = useState("");
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState(null);

  // Result state
  const [result, setResult] = useState(null); // { card, card_id, name }

  // Loading state for fetching existing card
  const [loadingCard, setLoadingCard] = useState(!!routeCardId);

  // ── Fetch existing card if URL has cardId ──────────
  useEffect(() => {
    if (!routeCardId) return;
    (async () => {
      try {
        const res = await fetch(
          `${BACKEND_URL}/api/viral-card/${routeCardId}`
        );
        if (!res.ok) {
          setError("Card not found or expired");
          return;
        }
        const data = await res.json();
        setResult({
          card: data.card,
          card_id: data.card_id,
          name: data.name,
        });
      } catch {
        setError("Failed to load card");
      } finally {
        setLoadingCard(false);
      }
    })();
  }, [routeCardId]);

  // ── Submit analysis ────────────────────────────────
  const handleAnalyze = async () => {
    if (postsText.trim().length < 100) {
      setError("Please paste at least 100 characters of your content.");
      return;
    }
    setError(null);
    setAnalyzing(true);
    try {
      const res = await fetch(`${BACKEND_URL}/api/viral-card/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          posts_text: postsText,
          platform,
          name: name.trim() || null,
        }),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Analysis failed");
      }
      const data = await res.json();
      setResult({
        card: data.card,
        card_id: data.card_id,
        name: data.name,
      });
      // Update URL to shareable link without full reload, keeping React Router in sync
      navigate(`/discover/${data.card_id}`, { replace: true });
    } catch (err) {
      setError(err.message || "Something went wrong. Please try again.");
    } finally {
      setAnalyzing(false);
    }
  };

  // ── Character count helper ─────────────────────────
  const charCount = postsText.trim().length;
  const charCountColor =
    charCount === 0
      ? "text-zinc-600"
      : charCount < 100
      ? "text-red-400"
      : charCount < 500
      ? "text-amber-400"
      : "text-lime";

  // ── Loading existing card ──────────────────────────
  if (loadingCard) {
    return (
      <div className="min-h-screen bg-[#050505] flex items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <div className="w-10 h-10 border-2 border-lime border-t-transparent rounded-full animate-spin" />
          <span className="text-zinc-500 text-sm">Loading persona card...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#050505] text-white relative overflow-hidden">
      {/* Background effects */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[600px] bg-gradient-radial from-violet-500/8 via-transparent to-transparent blur-3xl pointer-events-none" />
      <div className="absolute top-1/3 right-0 w-[400px] h-[400px] bg-lime/[0.03] rounded-full blur-[120px] pointer-events-none" />

      {/* ─── Header ───────────────────────────────────── */}
      <header className="relative z-10 flex items-center justify-between px-6 md:px-12 h-16">
        <Link to="/" className="flex items-center gap-2">
          <div className="w-8 h-8 bg-lime rounded-lg flex items-center justify-center">
            <Zap size={16} className="text-black" fill="black" />
          </div>
          <span className="font-display font-bold text-lg text-white">
            Thook
          </span>
          <span className="text-[10px] font-mono text-lime bg-lime/10 px-1.5 py-0.5 rounded-md">
            AI
          </span>
        </Link>
        <div className="flex items-center gap-3">
          <Link
            to="/auth"
            className="text-sm text-zinc-400 hover:text-white transition-colors hidden md:block"
          >
            Sign in
          </Link>
          <Link
            to="/auth"
            className="btn-primary text-sm py-2 px-5"
          >
            Get started
          </Link>
        </div>
      </header>

      {/* ─── Main Content ─────────────────────────────── */}
      <main className="relative z-10 max-w-2xl mx-auto px-6 pt-8 pb-20">
        {result ? (
          /* ─── Card Result View ──────────────────────── */
          <>
            <PersonaCardResult
              card={result.card}
              name={result.name}
              cardId={result.card_id}
            />
            {/* Try again link */}
            <div className="text-center mt-6">
              <button
                onClick={() => {
                  setResult(null);
                  setPostsText("");
                  setError(null);
                  navigate("/discover", { replace: true });
                }}
                className="text-zinc-500 text-sm hover:text-white transition-colors inline-flex items-center gap-1"
              >
                <ArrowRight size={14} className="rotate-180" />
                Analyze different content
              </button>
            </div>
          </>
        ) : analyzing ? (
          /* ─── Loading ───────────────────────────────── */
          <AnalysisLoader />
        ) : (
          /* ─── Input Form ────────────────────────────── */
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="space-y-8"
          >
            {/* Hero text */}
            <div className="text-center space-y-4 pt-8">
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 }}
                className="inline-flex items-center gap-2 bg-lime/10 border border-lime/20 rounded-full px-4 py-1.5 text-sm"
              >
                <Sparkles size={14} className="text-lime" />
                <span className="text-lime font-medium">Free - No signup required</span>
              </motion.div>
              <motion.h1
                initial={{ opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.15 }}
                className="font-display font-bold text-4xl md:text-5xl text-white leading-tight"
              >
                Discover Your{" "}
                <span className="gradient-text">Creator DNA</span>
              </motion.h1>
              <motion.p
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.25 }}
                className="text-zinc-400 text-lg max-w-lg mx-auto leading-relaxed"
              >
                Paste your posts below. Our AI will analyze your writing
                patterns and build your unique persona card in seconds.
              </motion.p>
            </div>

            {/* Form card */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 }}
              className="card-thook p-6 md:p-8 space-y-5"
            >
              {/* Name field (optional) */}
              <div>
                <label className="text-xs text-zinc-500 uppercase tracking-wider block mb-2">
                  Your name{" "}
                  <span className="text-zinc-700 normal-case">(optional)</span>
                </label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="How should we address you?"
                  maxLength={50}
                  className="input-thook"
                />
              </div>

              {/* Platform selector */}
              <div>
                <label className="text-xs text-zinc-500 uppercase tracking-wider block mb-2">
                  Primary platform
                </label>
                <div className="flex gap-2">
                  {PLATFORM_OPTIONS.map((opt) => {
                    const Icon = opt.icon;
                    const isActive = platform === opt.value;
                    return (
                      <button
                        key={opt.value}
                        onClick={() => setPlatform(opt.value)}
                        className={`flex-1 flex items-center justify-center gap-2 py-2.5 rounded-xl text-sm font-medium transition-all border ${
                          isActive
                            ? "bg-lime/10 text-lime border-lime/30"
                            : "bg-white/5 text-zinc-400 border-white/5 hover:bg-white/8 hover:text-white"
                        }`}
                      >
                        <Icon size={15} />
                        <span className="hidden sm:inline">{opt.label}</span>
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Textarea */}
              <div>
                <label className="text-xs text-zinc-500 uppercase tracking-wider block mb-2">
                  Paste your posts
                </label>
                <textarea
                  value={postsText}
                  onChange={(e) => {
                    setPostsText(e.target.value);
                    if (error) setError(null);
                  }}
                  placeholder={
                    "Paste 3-5 of your best posts here, separated by blank lines.\n\nThe more content you share, the more accurate your persona card will be..."
                  }
                  rows={8}
                  maxLength={10000}
                  className="input-thook resize-none font-body text-sm leading-relaxed"
                />
                <div className="flex items-center justify-between mt-2">
                  <p className={`text-xs ${charCountColor} transition-colors`}>
                    {charCount > 0 ? `${charCount.toLocaleString()} characters` : "Min 100 characters"}
                    {charCount > 0 && charCount < 100 && (
                      <span className="text-zinc-600 ml-1">
                        ({100 - charCount} more needed)
                      </span>
                    )}
                  </p>
                  <p className="text-xs text-zinc-700">
                    {(10000 - charCount).toLocaleString()} remaining
                  </p>
                </div>
              </div>

              {/* Error */}
              {error && (
                <motion.p
                  initial={{ opacity: 0, y: -4 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="text-red-400 text-sm bg-red-400/10 border border-red-400/20 rounded-xl px-4 py-3"
                >
                  {error}
                </motion.p>
              )}

              {/* Submit button */}
              <button
                onClick={handleAnalyze}
                disabled={charCount < 100}
                className="w-full btn-primary text-base py-3.5 flex items-center justify-center gap-2 disabled:opacity-40 disabled:cursor-not-allowed disabled:transform-none disabled:shadow-none"
              >
                <Sparkles size={18} />
                Analyze My Voice
                <ArrowRight size={16} />
              </button>
            </motion.div>

            {/* Trust signals */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.5 }}
              className="flex items-center justify-center gap-6 text-zinc-600 text-xs"
            >
              <div className="flex items-center gap-1.5">
                <Zap size={12} />
                <span>AI-powered analysis</span>
              </div>
              <div className="w-1 h-1 rounded-full bg-zinc-800" />
              <div className="flex items-center gap-1.5">
                <Share2 size={12} />
                <span>Shareable card</span>
              </div>
              <div className="w-1 h-1 rounded-full bg-zinc-800" />
              <div className="flex items-center gap-1.5">
                <Check size={12} />
                <span>100% free</span>
              </div>
            </motion.div>
          </motion.div>
        )}
      </main>

      {/* ─── Footer ───────────────────────────────────── */}
      <footer className="relative z-10 border-t border-white/5 px-6 md:px-12 py-6">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <div className="w-5 h-5 bg-lime rounded-md flex items-center justify-center">
              <Zap size={10} className="text-black" fill="black" />
            </div>
            <span className="font-display font-bold text-xs text-white">
              Thook AI
            </span>
          </div>
          <p className="text-zinc-700 text-xs">
            Your AI Creative Agency.
          </p>
          <div className="flex gap-5 text-xs text-zinc-600">
            <Link to="/" className="hover:text-white transition-colors">
              Home
            </Link>
            <Link to="/auth" className="hover:text-white transition-colors">
              Sign up
            </Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
