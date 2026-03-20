import { useState, useEffect, useRef } from "react";
import { useParams, Link } from "react-router-dom";
import { motion } from "framer-motion";
import { 
  Zap, Users, Target, Sparkles, Eye, Calendar, 
  Share2, Download, ExternalLink, ChevronRight 
} from "lucide-react";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const ARCHETYPE_GRADIENTS = {
  Educator: "from-cyan-500/20 via-cyan-400/10 to-transparent",
  Storyteller: "from-violet-500/20 via-violet-400/10 to-transparent",
  Provocateur: "from-pink-500/20 via-pink-400/10 to-transparent",
  Builder: "from-lime-500/20 via-lime-400/10 to-transparent",
};

const ARCHETYPE_COLORS = {
  Educator: { text: "text-cyan-400", bg: "bg-cyan-400/10", border: "border-cyan-400/30", glow: "shadow-cyan-400/20" },
  Storyteller: { text: "text-violet-400", bg: "bg-violet-400/10", border: "border-violet-400/30", glow: "shadow-violet-400/20" },
  Provocateur: { text: "text-pink-400", bg: "bg-pink-400/10", border: "border-pink-400/30", glow: "shadow-pink-400/20" },
  Builder: { text: "text-lime", bg: "bg-lime/10", border: "border-lime/30", glow: "shadow-lime/20" },
};

const REGIONAL_FLAGS = {
  US: "🇺🇸",
  UK: "🇬🇧",
  AU: "🇦🇺",
  IN: "🇮🇳",
};

function VoiceMetricBar({ label, value, color = "lime" }) {
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs">
        <span className="text-zinc-500">{label}</span>
        <span className={`text-${color} font-mono`}>{Math.round(value * 100)}</span>
      </div>
      <div className="h-1.5 bg-white/5 rounded-full overflow-hidden">
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${value * 100}%` }}
          transition={{ duration: 0.8, ease: "easeOut" }}
          className={`h-full bg-${color} rounded-full`}
        />
      </div>
    </div>
  );
}

export default function PersonaCardPublic() {
  const { shareToken } = useParams();
  const [persona, setPersona] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const cardRef = useRef(null);

  useEffect(() => {
    const fetchPublicPersona = async () => {
      try {
        const res = await fetch(`${BACKEND_URL}/api/persona/public/${shareToken}`);
        if (!res.ok) {
          const err = await res.json();
          throw new Error(err.detail || "Failed to load persona");
        }
        const data = await res.json();
        setPersona(data);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };
    
    if (shareToken) {
      fetchPublicPersona();
    }
  }, [shareToken]);

  if (loading) {
    return (
      <div className="min-h-screen bg-[#050505] flex items-center justify-center">
        <motion.div 
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="flex flex-col items-center gap-4"
        >
          <div className="w-10 h-10 border-2 border-lime border-t-transparent rounded-full animate-spin" />
          <span className="text-zinc-500 text-sm">Loading Persona Card...</span>
        </motion.div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-[#050505] flex items-center justify-center p-6">
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center max-w-md"
        >
          <div className="w-16 h-16 bg-red-500/10 rounded-2xl flex items-center justify-center mx-auto mb-5">
            <Zap size={28} className="text-red-400" />
          </div>
          <h2 className="font-display font-bold text-2xl text-white mb-2">
            {error === "Share link has expired" ? "Link Expired" : "Persona Not Found"}
          </h2>
          <p className="text-zinc-500 text-sm mb-6">
            {error === "Share link has expired" 
              ? "This persona card share link has expired. The creator may have revoked it or it's past its expiry date."
              : "This persona card doesn't exist or has been removed by its creator."
            }
          </p>
          <Link 
            to="/" 
            className="inline-flex items-center gap-2 btn-primary"
          >
            Create Your Own <ChevronRight size={16} />
          </Link>
        </motion.div>
      </div>
    );
  }

  const card = persona?.card || {};
  const creator = persona?.creator || {};
  const voiceMetrics = persona?.voice_metrics || {};
  const shareInfo = persona?.share_info || {};
  
  const archetype = card.personality_archetype || "Educator";
  const colors = ARCHETYPE_COLORS[archetype] || ARCHETYPE_COLORS.Educator;
  const gradient = ARCHETYPE_GRADIENTS[archetype] || ARCHETYPE_GRADIENTS.Educator;

  return (
    <div className="min-h-screen bg-[#050505] relative overflow-hidden">
      {/* Background gradient effect */}
      <div className={`absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[600px] bg-gradient-radial ${gradient} blur-3xl opacity-50 pointer-events-none`} />
      
      {/* Thook branding header */}
      <header className="relative z-10 p-6 flex items-center justify-between">
        <Link to="/" className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-lime flex items-center justify-center">
            <Zap size={18} className="text-black" />
          </div>
          <span className="font-display font-bold text-white text-lg">ThookAI</span>
        </Link>
        <div className="flex items-center gap-2 text-zinc-500 text-xs">
          <Eye size={14} />
          <span>{shareInfo.view_count?.toLocaleString() || 0} views</span>
        </div>
      </header>

      {/* Main content */}
      <main className="relative z-10 max-w-2xl mx-auto px-6 py-8">
        <motion.div
          ref={cardRef}
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className={`bg-[#0A0A0A] border border-white/10 rounded-3xl overflow-hidden shadow-2xl ${colors.glow}`}
          data-testid="public-persona-card"
        >
          {/* Card header with creator info */}
          <div className={`p-8 border-b border-white/5 bg-gradient-to-br ${gradient}`}>
            <div className="flex items-center gap-4">
              <div className="w-16 h-16 rounded-2xl bg-white/10 flex items-center justify-center overflow-hidden flex-shrink-0 ring-2 ring-white/10">
                {creator.picture ? (
                  <img src={creator.picture} alt="" className="w-full h-full object-cover" />
                ) : (
                  <span className={`font-bold text-2xl ${colors.text}`}>
                    {creator.name?.[0]?.toUpperCase() || "C"}
                  </span>
                )}
              </div>
              <div className="flex-1">
                <h1 className="font-display font-bold text-2xl text-white mb-1">
                  {creator.name || "Creator"}
                </h1>
                <div className="flex items-center gap-2 flex-wrap">
                  <span className={`text-sm font-semibold px-3 py-1 rounded-full border ${colors.bg} ${colors.text} ${colors.border}`}>
                    {archetype}
                  </span>
                  {card.regional_english && (
                    <span className="text-sm text-zinc-400">
                      {REGIONAL_FLAGS[card.regional_english]} {card.regional_english}
                    </span>
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* Card body */}
          <div className="p-8 space-y-6">
            {/* Voice descriptor */}
            {card.writing_voice_descriptor && (
              <div>
                <p className="text-xs text-zinc-600 uppercase tracking-wider mb-2">Voice</p>
                <p className="text-white text-lg leading-relaxed">"{card.writing_voice_descriptor}"</p>
              </div>
            )}

            {/* Niche & Audience */}
            <div className="grid grid-cols-2 gap-4">
              {card.content_niche_signature && (
                <div className="bg-white/5 rounded-xl p-4">
                  <div className="flex items-center gap-2 mb-2">
                    <Target size={14} className={colors.text} />
                    <span className="text-xs text-zinc-500">Niche</span>
                  </div>
                  <p className="text-white text-sm">{card.content_niche_signature}</p>
                </div>
              )}
              {card.inferred_audience_profile && (
                <div className="bg-white/5 rounded-xl p-4">
                  <div className="flex items-center gap-2 mb-2">
                    <Users size={14} className={colors.text} />
                    <span className="text-xs text-zinc-500">Audience</span>
                  </div>
                  <p className="text-white text-sm">{card.inferred_audience_profile}</p>
                </div>
              )}
            </div>

            {/* Content pillars */}
            {card.content_pillars?.length > 0 && (
              <div>
                <p className="text-xs text-zinc-600 uppercase tracking-wider mb-3">Content Pillars</p>
                <div className="flex flex-wrap gap-2">
                  {card.content_pillars.map((pillar, i) => (
                    <span 
                      key={i} 
                      className={`text-sm px-3 py-1.5 rounded-full ${colors.bg} ${colors.text} border ${colors.border}`}
                    >
                      {pillar}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Focus platforms */}
            {card.focus_platforms?.length > 0 && (
              <div>
                <p className="text-xs text-zinc-600 uppercase tracking-wider mb-3">Platforms</p>
                <div className="flex gap-2">
                  {card.focus_platforms.map((platform, i) => (
                    <span 
                      key={i} 
                      className="text-sm px-3 py-1.5 rounded-full bg-white/5 text-zinc-300 border border-white/10"
                    >
                      {platform}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Voice metrics */}
            <div className="bg-white/5 rounded-xl p-5">
              <div className="flex items-center gap-2 mb-4">
                <Sparkles size={14} className={colors.text} />
                <span className="text-xs text-zinc-500 uppercase tracking-wider">Voice Fingerprint</span>
              </div>
              <div className="space-y-3">
                <VoiceMetricBar 
                  label="Vocabulary Depth" 
                  value={voiceMetrics.vocabulary_complexity || 0.65} 
                />
                <VoiceMetricBar 
                  label="Emoji Style" 
                  value={voiceMetrics.emoji_frequency || 0.05} 
                />
              </div>
              {voiceMetrics.hook_style_preferences?.length > 0 && (
                <div className="mt-4 pt-4 border-t border-white/5">
                  <p className="text-xs text-zinc-500 mb-2">Hook Style</p>
                  <p className="text-white text-sm">{voiceMetrics.hook_style_preferences[0]}</p>
                </div>
              )}
            </div>

            {/* Share info */}
            <div className="flex items-center justify-between text-xs text-zinc-600 pt-4 border-t border-white/5">
              <div className="flex items-center gap-1">
                <Calendar size={12} />
                <span>Shared {new Date(shareInfo.shared_since).toLocaleDateString()}</span>
              </div>
              <div className="flex items-center gap-1">
                <Eye size={12} />
                <span>{shareInfo.view_count?.toLocaleString() || 0} views</span>
              </div>
            </div>
          </div>

          {/* Thook watermark */}
          <div className="px-8 py-4 bg-white/[0.02] border-t border-white/5 flex items-center justify-center">
            <div className="flex items-center gap-2 text-zinc-600 text-xs">
              <span>Powered by</span>
              <div className="flex items-center gap-1">
                <div className="w-4 h-4 rounded bg-lime flex items-center justify-center">
                  <Zap size={10} className="text-black" />
                </div>
                <span className="font-display font-semibold text-zinc-400">ThookAI</span>
              </div>
            </div>
          </div>
        </motion.div>

        {/* CTA Section */}
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3, duration: 0.5 }}
          className="mt-8 text-center"
        >
          <p className="text-zinc-500 text-sm mb-4">
            Want your own AI-powered persona card?
          </p>
          <Link 
            to="/?utm_source=shared_persona&utm_medium=public_card" 
            className="inline-flex items-center gap-2 btn-primary text-lg px-6 py-3"
          >
            <Sparkles size={18} />
            Create Your Persona Card
            <ExternalLink size={16} />
          </Link>
        </motion.div>
      </main>

      {/* Footer */}
      <footer className="relative z-10 p-6 text-center text-zinc-700 text-xs">
        <p>© 2025 ThookAI. AI-powered content creation platform.</p>
      </footer>
    </div>
  );
}
