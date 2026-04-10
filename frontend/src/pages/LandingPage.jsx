import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { Zap, ArrowRight, Check, ChevronRight, Sparkles } from "lucide-react";

// ─── Navbar ──────────────────────────────────────────────
function Navbar() {
  const navigate = useNavigate();
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 20);
    window.addEventListener("scroll", onScroll);
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <nav
      className={`fixed top-0 left-0 right-0 z-50 flex items-center justify-between px-6 md:px-12 h-16 transition-all ${scrolled ? "bg-[#050505]/90 backdrop-blur-md border-b border-white/5" : ""}`}
      data-testid="landing-navbar"
    >
      <div className="flex items-center gap-2">
        <div className="w-8 h-8 bg-lime rounded-lg flex items-center justify-center">
          <Zap size={16} className="text-black" fill="black" />
        </div>
        <span className="font-display font-bold text-lg text-white">Thook</span>
        <span className="text-[10px] font-mono text-lime bg-lime/10 px-1.5 py-0.5 rounded-md">
          AI
        </span>
      </div>

      <div className="hidden md:flex items-center gap-8 text-sm text-zinc-400">
        <a href="#features" className="hover:text-white transition-colors">
          Product
        </a>
        <a href="#agents" className="hover:text-white transition-colors">
          Agents
        </a>
        <a href="#pricing" className="hover:text-white transition-colors">
          Pricing
        </a>
        <button
          onClick={() => navigate("/discover")}
          className="text-lime hover:text-[#B8E600] transition-colors flex items-center gap-1.5 font-medium"
        >
          <Sparkles size={14} />
          Discover Your Voice
        </button>
      </div>

      <div className="flex items-center gap-3">
        <button
          onClick={() => navigate("/auth")}
          data-testid="nav-signin-btn"
          className="text-sm text-zinc-400 hover:text-white transition-colors hidden md:block"
        >
          Sign in
        </button>
        <button
          onClick={() => navigate("/auth")}
          data-testid="nav-cta-btn"
          className="btn-primary text-sm py-2 px-5"
        >
          Get started
        </button>
      </div>
    </nav>
  );
}

// ─── Hero ─────────────────────────────────────────────────
function Hero() {
  const navigate = useNavigate();
  return (
    <section
      className="relative min-h-screen flex items-center justify-center px-6 pt-16 overflow-hidden"
      data-testid="hero-section"
    >
      {/* Background */}
      <div className="absolute inset-0 hero-glow" />
      <div className="absolute top-1/3 left-1/2 -translate-x-1/2 w-[600px] h-[600px] bg-violet/8 rounded-full blur-[120px]" />
      <div className="absolute top-1/2 left-1/4 w-64 h-64 bg-lime/4 rounded-full blur-[80px]" />

      <div className="relative z-10 text-center max-w-4xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          <div className="inline-flex items-center gap-2 bg-lime/10 border border-lime/20 rounded-full px-4 py-1.5 mb-8 text-sm">
            <span className="w-2 h-2 bg-lime rounded-full animate-pulse" />
            <span className="text-lime font-medium">
              Early Bird Launch — Save up to 38% for a limited time
            </span>
            <ChevronRight size={14} className="text-lime/60" />
          </div>
        </motion.div>

        <motion.h1
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.1 }}
          className="font-display font-bold text-5xl md:text-6xl lg:text-7xl text-white leading-[1.05] mb-6"
        >
          Your Voice. <span className="text-lime">Infinite</span> Content.
        </motion.h1>

        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.2 }}
          className="text-lg md:text-xl text-zinc-400 max-w-2xl mx-auto mb-10 leading-relaxed"
        >
          15+ specialized AI agents that learn your exact voice and style — then
          craft platform-native content for LinkedIn, X, and Instagram.{" "}
          <strong className="text-white">Without burning you out.</strong>
        </motion.p>

        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.3 }}
          className="flex flex-col sm:flex-row items-center justify-center gap-4"
        >
          <button
            onClick={() => navigate("/auth")}
            data-testid="hero-cta-primary"
            className="btn-primary text-base px-8 py-3.5 flex items-center gap-2"
          >
            Get Started
            <ArrowRight size={16} />
          </button>
          <a
            href="#features"
            data-testid="hero-cta-secondary"
            className="btn-ghost text-base flex items-center gap-2"
          >
            <ChevronRight size={16} className="text-lime" />
            <span>See how it works</span>
          </a>
        </motion.div>

        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.5 }}
          className="text-zinc-600 text-sm mt-6"
        >
          50 free credits on signup · No credit card for Free tier
        </motion.p>
      </div>

      {/* Platform logos */}
      <div className="absolute bottom-12 left-1/2 -translate-x-1/2 flex items-center gap-6 opacity-40">
        <span className="text-xs text-zinc-600 uppercase tracking-wider">
          Publishes to
        </span>
        <img
          src="https://upload.wikimedia.org/wikipedia/commons/c/ca/LinkedIn_logo_initials.png"
          alt="LinkedIn"
          className="h-5 w-5 object-contain"
        />
        <img
          src="https://upload.wikimedia.org/wikipedia/commons/thumb/c/ce/X_logo_2023.svg/450px-X_logo_2023.svg.png"
          alt="X"
          className="h-5 w-5 object-contain invert"
        />
        <img
          src="https://upload.wikimedia.org/wikipedia/commons/thumb/e/e7/Instagram_logo_2016.svg/2048px-Instagram_logo_2016.svg.png"
          alt="Instagram"
          className="h-5 w-5 object-contain"
        />
      </div>
    </section>
  );
}

// ─── Features Bento ──────────────────────────────────────
function Features() {
  const voicePoints = [
    "Sentence rhythm & length",
    "Vocabulary complexity",
    "Emoji frequency & style",
    "Hook patterns (question/stat/bold)",
    "CTA fingerprint",
  ];
  return (
    <section id="features" className="px-6 md:px-12 py-24 max-w-7xl mx-auto">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        className="text-center mb-16"
      >
        <p className="text-lime text-sm font-semibold uppercase tracking-wider mb-3">
          Core Features
        </p>
        <h2 className="font-display font-bold text-4xl md:text-5xl text-white">
          Anti-generic AI.
        </h2>
        <p className="text-zinc-500 mt-3 max-w-xl mx-auto">
          Built around your unique voice, not a generic template.
        </p>
      </motion.div>

      <div className="grid grid-cols-1 md:grid-cols-4 auto-rows-[minmax(180px,auto)] gap-4">
        {/* Persona Engine - Large card */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ delay: 0.1 }}
          className="md:col-span-2 md:row-span-2 card-thook p-6 relative overflow-hidden group"
          data-testid="feature-persona"
        >
          <div className="absolute inset-0 bg-gradient-to-br from-violet/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
          <div className="relative z-10">
            <div className="inline-flex items-center gap-2 bg-violet/15 text-violet rounded-full px-3 py-1 text-xs font-semibold mb-4">
              <Zap size={12} />
              Core Differentiator
            </div>
            <h3 className="font-display font-bold text-2xl text-white mb-2">
              The Persona Engine
            </h3>
            <p className="text-zinc-400 text-sm mb-6 leading-relaxed">
              Your AI voice clone. Learns from every post, edit, and approval to
              create content that sounds exactly like you — not like AI.
            </p>
            {/* Voice fingerprint visualization */}
            <div className="bg-[#0A0A0B] rounded-xl p-4 border border-white/5">
              <p className="text-xs text-zinc-600 mb-3 font-mono">
                VOICE FINGERPRINT
              </p>
              <div className="space-y-2">
                {voicePoints.map((pt, i) => (
                  <div key={pt} className="flex items-center gap-3">
                    <div className="flex gap-0.5">
                      {Array.from({ length: 8 }).map((_, j) => (
                        <div
                          key={j}
                          className="w-1 rounded-sm transition-all"
                          style={{
                            height: `${8 + Math.sin((i * 3 + j) * 0.8) * 6}px`,
                            backgroundColor: j < 5 + i ? "#D4FF00" : "#27272A",
                            opacity: j < 5 + i ? 0.7 + j * 0.04 : 1,
                          }}
                        />
                      ))}
                    </div>
                    <span className="text-xs text-zinc-500">{pt}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </motion.div>

        {/* Content Pipeline */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ delay: 0.2 }}
          className="md:col-span-2 card-thook p-5 relative overflow-hidden"
          data-testid="feature-pipeline"
        >
          <h3 className="font-display font-semibold text-lg text-white mb-1">
            Raw in, ready out
          </h3>
          <p className="text-zinc-500 text-xs mb-4">
            Drop a rough idea. Get platform-ready content.
          </p>
          <div className="flex items-center gap-1.5 flex-wrap">
            {["Scout", "Thinker", "Writer", "QC", "Publish"].map((step, i) => (
              <div key={step} className="flex items-center gap-1.5">
                <div className="bg-surface-2 text-xs text-zinc-300 rounded-lg px-3 py-1.5 border border-white/5">
                  {step}
                </div>
                {i < 4 && <ChevronRight size={12} className="text-zinc-700" />}
              </div>
            ))}
          </div>
        </motion.div>

        {/* Platform Native */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ delay: 0.3 }}
          className="md:col-span-2 card-thook p-5"
          data-testid="feature-platforms"
        >
          <h3 className="font-display font-semibold text-lg text-white mb-1">
            Platform-native UX
          </h3>
          <p className="text-zinc-500 text-xs mb-4">
            Editors that mimic LinkedIn, X, and Instagram — zero learning curve.
          </p>
          <div className="flex gap-2">
            {[
              { name: "LinkedIn", color: "#0A66C2", tag: "Post / Carousel" },
              { name: "X", color: "#1D9BF0", tag: "Thread" },
              { name: "Instagram", color: "#E1306C", tag: "Caption" },
            ].map((p) => (
              <div
                key={p.name}
                className="flex-1 bg-surface-2 rounded-lg p-2.5 border border-white/5 text-center"
              >
                <div
                  className="w-1.5 h-1.5 rounded-full mx-auto mb-1.5"
                  style={{ backgroundColor: p.color }}
                />
                <p className="text-xs font-medium text-white">{p.name}</p>
                <p className="text-[10px] text-zinc-600 mt-0.5">{p.tag}</p>
              </div>
            ))}
          </div>
        </motion.div>

        {/* Zero Burnout */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ delay: 0.35 }}
          className="md:col-span-1 card-thook p-5 bg-lime/5 border-lime/10"
          data-testid="feature-burnout"
        >
          <p className="text-4xl font-display font-bold text-lime mb-1">0</p>
          <p className="text-white font-semibold text-sm">Burnout</p>
          <p className="text-zinc-500 text-xs mt-1">
            Adaptive AI adjusts to your energy level automatically
          </p>
        </motion.div>

        {/* 15+ agents */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ delay: 0.4 }}
          className="md:col-span-1 card-thook p-5"
          data-testid="feature-agents-count"
        >
          <p className="text-4xl font-display font-bold text-white mb-1">
            15<span className="text-lime">+</span>
          </p>
          <p className="text-white font-semibold text-sm">AI Agents</p>
          <p className="text-zinc-500 text-xs mt-1">
            Each specialized for one task. All working as one team.
          </p>
        </motion.div>
      </div>
    </section>
  );
}

// ─── Discover CTA Banner ─────────────────────────────────
function DiscoverBanner() {
  const navigate = useNavigate();
  return (
    <section className="px-6 md:px-12 py-16 max-w-7xl mx-auto">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        className="relative overflow-hidden rounded-2xl border border-lime/20 bg-gradient-to-br from-lime/[0.06] via-[#0A0A0B] to-violet/[0.04] p-8 md:p-12"
      >
        <div className="absolute top-0 right-0 w-64 h-64 bg-lime/[0.06] rounded-full blur-[80px] pointer-events-none" />
        <div className="absolute bottom-0 left-0 w-48 h-48 bg-violet/[0.08] rounded-full blur-[60px] pointer-events-none" />
        <div className="relative z-10 flex flex-col md:flex-row items-center gap-8">
          <div className="flex-1 text-center md:text-left">
            <div className="inline-flex items-center gap-2 bg-lime/10 border border-lime/20 rounded-full px-3 py-1 text-xs font-semibold mb-4">
              <Sparkles size={12} className="text-lime" />
              <span className="text-lime">Free Tool</span>
            </div>
            <h3 className="font-display font-bold text-2xl md:text-3xl text-white mb-3">
              Discover Your Creator DNA
            </h3>
            <p className="text-zinc-400 text-sm md:text-base leading-relaxed max-w-lg">
              Paste your posts and get an AI-powered persona card that reveals
              your writing voice, content archetype, and strengths. No signup
              needed.
            </p>
          </div>
          <div className="flex-shrink-0">
            <button
              onClick={() => navigate("/discover")}
              className="btn-primary text-base px-8 py-3.5 flex items-center gap-2 whitespace-nowrap"
            >
              <Sparkles size={16} />
              Try It Free
              <ArrowRight size={16} />
            </button>
          </div>
        </div>
      </motion.div>
    </section>
  );
}

// ─── Agent Council ────────────────────────────────────────
const agents = [
  { name: "Commander", model: "GPT-4o", role: "Orchestrates all flows" },
  { name: "Scout", model: "Perplexity", role: "Research & trends" },
  { name: "Thinker", model: "o1-mini", role: "Content strategy" },
  { name: "Writer", model: "Claude 3.5", role: "Voice-matched copy" },
  { name: "Persona", model: "GPT-4o", role: "Identity cloning" },
  { name: "Visual", model: "Gemini Vision", role: "Media analysis" },
  { name: "Designer", model: "DALL-E", role: "Carousels & graphics" },
  { name: "Director", model: "Kling/Runway", role: "Video generation" },
  { name: "Clone", model: "HeyGen", role: "AI avatar videos" },
  { name: "Voice", model: "ElevenLabs", role: "Voice cloning" },
  { name: "QC", model: "GPT-4o-mini", role: "Quality control" },
  { name: "Analyst", model: "GPT-4o", role: "Performance tracking" },
  { name: "Planner", model: "GPT-4o-mini", role: "Optimal scheduling" },
  { name: "Editor", model: "Vizard", role: "Video editing" },
  { name: "Sound", model: "Suno", role: "Audio branding" },
];

function AgentCouncil() {
  return (
    <section id="agents" className="px-6 md:px-12 py-24 bg-surface/50">
      <div className="max-w-7xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="text-center mb-12"
        >
          <p className="text-zinc-500 text-sm font-semibold uppercase tracking-wider mb-3">
            The Agent Council
          </p>
          <h2 className="font-display font-bold text-4xl md:text-5xl text-white">
            15 specialists. <span className="text-lime">One team.</span>
          </h2>
          <p className="text-zinc-500 mt-3 max-w-xl mx-auto text-sm">
            Each agent is purpose-built with the world's best model for its job.
            Orchestrated by Commander GPT-4o.
          </p>
        </motion.div>

        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
          {agents.map((agent, i) => (
            <motion.div
              key={agent.name}
              initial={{ opacity: 0, y: 16 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.04 }}
              className="card-thook p-4 hover:border-lime/20 transition-all group"
              data-testid={`agent-card-${agent.name.toLowerCase()}`}
            >
              <div className="w-8 h-8 bg-white/5 rounded-lg flex items-center justify-center mb-3 group-hover:bg-lime/10 transition-colors">
                <span className="text-xs font-bold text-zinc-400 group-hover:text-lime transition-colors">
                  {agent.name[0]}
                </span>
              </div>
              <p className="text-sm font-semibold text-white">{agent.name}</p>
              <p className="text-[10px] text-lime/70 font-mono mb-1">
                {agent.model}
              </p>
              <p className="text-xs text-zinc-600">{agent.role}</p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}

// ─── Pricing ──────────────────────────────────────────────
const plans = [
  {
    name: "Starter",
    price: "$0",
    period: "",
    desc: "Try ThookAI with 200 free credits",
    features: [
      "200 one-time credits",
      "LinkedIn platform",
      "Persona Engine",
      "Text posts",
      "Content library",
    ],
    cta: "Start free",
    highlight: false,
  },
  {
    name: "Creator",
    price: "$15",
    period: "/month",
    desc: "For consistent creators posting weekly",
    features: [
      "~300 credits/month",
      "All 3 platforms",
      "Full Persona Engine",
      "Images & carousels",
      "Content repurposing",
      "30-day analytics",
    ],
    cta: "Build your plan",
    highlight: false,
    example: "~20 posts + 5 images + 5 repurposes",
  },
  {
    name: "Growth",
    price: "$79",
    period: "/month",
    desc: "For serious creators scaling output",
    features: [
      "~1,800 credits/month",
      "Voice narration",
      "10 personas",
      "5 team members",
      "90-day analytics",
      "Priority support",
    ],
    cta: "Build your plan",
    highlight: true,
    badge: "Most Popular",
    example: "~100 posts + 30 images + 10 videos",
  },
  {
    name: "Scale",
    price: "$149+",
    period: "/month",
    desc: "For agencies and power users",
    features: [
      "5,000+ credits/month",
      "Video generation",
      "API access",
      "10+ team members",
      "365-day analytics",
      "Custom integrations",
    ],
    cta: "Build your plan",
    highlight: false,
    badge: "Best Value",
    example: "Unlimited content at $0.03/credit",
  },
];

function Pricing() {
  const navigate = useNavigate();
  return (
    <section id="pricing" className="px-6 md:px-12 py-24">
      <div className="max-w-6xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="text-center mb-12"
        >
          <div className="inline-flex items-center gap-2 bg-lime/10 border border-lime/20 rounded-full px-4 py-1.5 mb-4 text-sm">
            <span className="w-2 h-2 bg-lime rounded-full animate-pulse" />
            <span className="text-lime font-medium">
              Volume Discounts — The More You Use, The Less You Pay
            </span>
          </div>
          <p className="text-lime text-sm font-semibold uppercase tracking-wider mb-3">
            Pricing
          </p>
          <h2 className="font-display font-bold text-4xl md:text-5xl text-white">
            Build your own plan.
          </h2>
          <p className="text-zinc-500 mt-3 text-sm">
            Pick your usage, we calculate the price. Credits refresh monthly.
            Start free.
          </p>
        </motion.div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {plans.map((plan, i) => (
            <motion.div
              key={plan.name}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.1 }}
              className={`card-thook p-6 relative ${plan.highlight ? "border-lime/30 bg-lime/3 ring-2 ring-lime/20" : ""}`}
              data-testid={`pricing-${plan.name.toLowerCase()}`}
            >
              {plan.badge && (
                <div
                  className={`absolute -top-3 left-1/2 -translate-x-1/2 text-xs font-bold rounded-full px-3 py-1 ${
                    plan.highlight
                      ? "bg-lime text-black"
                      : "bg-violet text-white"
                  }`}
                >
                  {plan.badge}
                </div>
              )}
              <p className="text-sm font-semibold text-zinc-400 mb-1">
                {plan.name}
              </p>
              <div className="flex items-end gap-2 mb-1">
                <span className="font-display font-bold text-4xl text-white">
                  {plan.price}
                </span>
                {plan.originalPrice && (
                  <span className="text-zinc-500 text-lg line-through mb-1">
                    {plan.originalPrice}
                  </span>
                )}
                <span className="text-zinc-500 text-sm mb-1">
                  {plan.period}
                </span>
              </div>
              <p className="text-xs text-zinc-500 mb-5">{plan.desc}</p>
              <ul className="space-y-2.5 mb-6">
                {plan.features.map((f) => (
                  <li
                    key={f}
                    className="flex items-center gap-2 text-sm text-zinc-300"
                  >
                    <Check size={14} className="text-lime flex-shrink-0" />
                    {f}
                  </li>
                ))}
              </ul>
              <button
                onClick={() => navigate("/auth")}
                data-testid={`pricing-cta-${plan.name.toLowerCase()}`}
                className={`w-full py-2.5 rounded-xl text-sm font-semibold transition-colors ${
                  plan.highlight
                    ? "bg-lime text-black hover:bg-[#B8E600]"
                    : "bg-white/8 text-white hover:bg-white/14 border border-white/10"
                }`}
              >
                {plan.cta}
              </button>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}

// ─── Footer ───────────────────────────────────────────────
function Footer() {
  return (
    <footer className="border-t border-white/5 px-6 md:px-12 py-8">
      <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 bg-lime rounded-md flex items-center justify-center">
            <Zap size={12} className="text-black" fill="black" />
          </div>
          <span className="font-display font-bold text-sm text-white">
            Thook AI
          </span>
        </div>
        <p className="text-zinc-600 text-xs">
          © 2025 ThookAI. Your AI Creative Agency.
        </p>
        <div className="flex gap-5 text-xs text-zinc-600">
          <a href="/privacy" className="hover:text-white transition-colors">
            Privacy
          </a>
          <a href="/terms" className="hover:text-white transition-colors">
            Terms
          </a>
          <a
            href="mailto:support@thookai.com"
            className="hover:text-white transition-colors"
          >
            Contact
          </a>
        </div>
      </div>
    </footer>
  );
}

// ─── Main Page ────────────────────────────────────────────
export default function LandingPage() {
  return (
    <div
      className="min-h-screen bg-[#050505] text-white overflow-x-hidden"
      data-testid="landing-page"
    >
      <Navbar />
      <Hero />
      <Features />
      <DiscoverBanner />
      <AgentCouncil />
      <Pricing />
      <Footer />
    </div>
  );
}
