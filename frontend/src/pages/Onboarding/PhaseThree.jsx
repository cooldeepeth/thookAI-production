import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { Zap, ArrowRight, RefreshCw, Edit2 } from "lucide-react";

const ARCHETYPE_COLORS = {
  Educator: { bg: "bg-cyan-400/10", text: "text-cyan-400", border: "border-cyan-400/20" },
  Storyteller: { bg: "bg-violet/10", text: "text-violet", border: "border-violet/20" },
  Provocateur: { bg: "bg-pink-500/10", text: "text-pink-400", border: "border-pink-400/20" },
  Builder: { bg: "bg-lime/10", text: "text-lime", border: "border-lime/20" },
};

const AGENT_SEQUENCE = ["Scout", "Thinker", "Persona", "Writer", "QC"];

function LoadingState() {
  return (
    <div className="flex-1 flex flex-col items-center justify-center p-8">
      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="text-center">
        <div className="w-16 h-16 bg-violet/10 rounded-2xl flex items-center justify-center mx-auto mb-6">
          <Zap size={28} className="text-violet animate-pulse" />
        </div>
        <h2 className="font-display font-bold text-2xl text-white mb-2">Building your Persona Engine</h2>
        <p className="text-zinc-500 text-sm mb-8 max-w-sm mx-auto">Your agent team is analyzing your answers and calibrating your AI voice clone.</p>

        <div className="flex items-center justify-center gap-3 flex-wrap">
          {AGENT_SEQUENCE.map((agent, i) => (
            <motion.div
              key={agent}
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: i * 0.3 }}
              className="flex items-center gap-2 bg-white/5 rounded-full px-4 py-2 border border-white/8"
            >
              <div className="w-1.5 h-1.5 rounded-full bg-lime animate-pulse" style={{ animationDelay: `${i * 0.2}s` }} />
              <span className="text-xs text-zinc-400">{agent}</span>
            </motion.div>
          ))}
        </div>
      </motion.div>
    </div>
  );
}

function VoiceFingerprint({ card }) {
  const bars = [
    { label: "Sentence rhythm", value: 0.72 },
    { label: "Vocabulary depth", value: 0.68 },
    { label: "Emoji usage", value: 0.12 },
    { label: "Hook strength", value: 0.85 },
    { label: "CTA clarity", value: 0.78 },
  ];

  return (
    <div className="bg-[#0A0A0B] rounded-xl p-4 border border-white/5">
      <p className="text-[10px] text-zinc-600 uppercase tracking-wider mb-3 font-mono">Voice Fingerprint</p>
      <div className="space-y-2">
        {bars.map((b) => (
          <div key={b.label} className="flex items-center gap-3">
            <span className="text-xs text-zinc-600 w-28 flex-shrink-0">{b.label}</span>
            <div className="flex-1 h-1.5 bg-white/5 rounded-full overflow-hidden">
              <motion.div
                initial={{ width: 0 }}
                animate={{ width: `${b.value * 100}%` }}
                transition={{ delay: 0.5, duration: 0.8 }}
                className="h-full bg-lime rounded-full"
              />
            </div>
            <span className="text-xs font-mono text-lime w-8 text-right">{Math.round(b.value * 100)}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function PersonaCardUI({ card, user }) {
  const archetype = card.personality_archetype || "Educator";
  const colors = ARCHETYPE_COLORS[archetype] || ARCHETYPE_COLORS.Educator;

  return (
    <motion.div
      initial={{ opacity: 0, y: 30, scale: 0.96 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ duration: 0.5, ease: "easeOut" }}
      className="relative overflow-hidden rounded-2xl border border-white/10 bg-gradient-to-br from-[#0F0F10] to-[#080808] p-6"
      data-testid="persona-card"
    >
      {/* Background accent */}
      <div className="absolute top-0 right-0 w-48 h-48 bg-violet/6 rounded-full blur-[80px]" />
      <div className="absolute bottom-0 left-0 w-32 h-32 bg-lime/4 rounded-full blur-[60px]" />

      <div className="relative z-10">
        {/* Header */}
        <div className="flex items-start justify-between mb-5">
          <div className="flex items-center gap-3">
            <div className="w-11 h-11 rounded-xl bg-violet/20 flex items-center justify-center overflow-hidden">
              {user?.picture ? (
                <img src={user.picture} alt="" className="w-full h-full object-cover" />
              ) : (
                <span className="font-bold text-violet text-lg">{user?.name?.[0]?.toUpperCase() || "C"}</span>
              )}
            </div>
            <div>
              <p className="text-sm font-semibold text-white">{user?.name || "Creator"}</p>
              <span className={`text-xs font-semibold px-2 py-0.5 rounded-full border ${colors.bg} ${colors.text} ${colors.border}`}>
                {archetype}
              </span>
            </div>
          </div>
          <div className="text-right">
            <p className="text-[10px] text-zinc-600 font-mono">PERSONA ENGINE</p>
            <p className="text-[10px] text-lime font-mono">ACTIVE</p>
          </div>
        </div>

        {/* Voice Descriptor */}
        <h3 className="font-display font-bold text-xl text-white mb-1">{card.writing_voice_descriptor}</h3>
        <p className="text-lime text-sm font-medium mb-5">{card.content_niche_signature}</p>

        {/* Three info cols */}
        <div className="grid grid-cols-3 gap-3 mb-5">
          {[
            { label: "Audience", value: card.inferred_audience_profile },
            { label: "Format", value: card.top_content_format },
            { label: "Tone", value: card.tone },
          ].map(item => (
            <div key={item.label} className="bg-white/3 rounded-lg p-2.5">
              <p className="text-[10px] text-zinc-600 mb-1">{item.label}</p>
              <p className="text-xs text-zinc-300 leading-tight">{item.value}</p>
            </div>
          ))}
        </div>

        {/* Platforms */}
        <div className="flex flex-wrap gap-1.5 mb-4">
          {(card.focus_platforms || []).map(p => (
            <span key={p} className="text-xs bg-white/8 text-zinc-300 rounded-full px-2.5 py-1 border border-white/8">{p}</span>
          ))}
        </div>

        {/* Content Pillars */}
        <div className="flex flex-wrap gap-1.5 mb-5">
          {(card.content_pillars || []).map(p => (
            <span key={p} className="text-xs bg-lime/8 text-lime/70 rounded-full px-2.5 py-1">{p}</span>
          ))}
        </div>

        {/* Voice Fingerprint */}
        <VoiceFingerprint card={card} />

        {/* Style notes */}
        {card.writing_style_notes && (
          <div className="mt-4 space-y-1">
            {card.writing_style_notes.map((note, i) => (
              <div key={i} className="flex items-start gap-2">
                <span className="text-lime text-xs mt-0.5 flex-shrink-0">▸</span>
                <p className="text-xs text-zinc-500 leading-relaxed">{note}</p>
              </div>
            ))}
          </div>
        )}
      </div>
    </motion.div>
  );
}

export default function PhaseThree({ personaCard, generating, error, user, onRetry }) {
  const navigate = useNavigate();

  if (generating) return <LoadingState />;

  if (error) {
    return (
      <div className="flex-1 flex items-center justify-center p-8">
        <div className="text-center max-w-md">
          <p className="text-red-400 text-sm mb-4">{error}</p>
          <button onClick={onRetry} className="btn-ghost flex items-center gap-2 mx-auto">
            <RefreshCw size={14} /> Try again
          </button>
        </div>
      </div>
    );
  }

  if (!personaCard) return <LoadingState />;

  return (
    <div className="flex-1 overflow-y-auto p-6 md:p-10">
      <div className="max-w-2xl mx-auto">
        {/* Success banner */}
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="flex items-center gap-3 bg-lime/10 border border-lime/20 rounded-xl p-4 mb-6"
          data-testid="activation-banner"
        >
          <div className="w-8 h-8 bg-lime rounded-lg flex items-center justify-center flex-shrink-0">
            <Zap size={16} className="text-black" fill="black" />
          </div>
          <div>
            <p className="text-sm font-semibold text-white">Your agent team is now activated</p>
            <p className="text-xs text-zinc-400">15 specialized agents have been calibrated to your voice. Ready to create.</p>
          </div>
        </motion.div>

        <div className="mb-4">
          <p className="text-xs text-zinc-600 uppercase tracking-wider mb-1 font-mono">Phase 3 of 3</p>
          <h2 className="font-display font-bold text-3xl text-white">Your Persona Card</h2>
          <p className="text-zinc-500 text-sm mt-1">This is your AI voice clone. Review and edit any field that doesn't feel right.</p>
        </div>

        <PersonaCardUI card={personaCard} user={user} />

        <div className="flex gap-3 mt-6">
          <button
            onClick={() => navigate("/dashboard/persona")}
            data-testid="go-to-dashboard-btn"
            className="flex-1 btn-primary flex items-center justify-center gap-2"
          >
            Go to Persona Engine <ArrowRight size={15} />
          </button>
          <button
            onClick={() => navigate("/dashboard")}
            className="btn-ghost text-sm px-5"
            data-testid="go-to-home-btn"
          >
            Dashboard
          </button>
        </div>
      </div>
    </div>
  );
}
