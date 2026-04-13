import { motion } from "framer-motion";
import { Zap, ChevronRight } from "lucide-react";

export function Features() {
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
            <div className="bg-surface rounded-xl p-4 border border-white/5">
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
                          className={`w-1 rounded-sm transition-all ${
                            j < 5 + i ? "bg-lime" : "bg-border-subtle"
                          }`}
                          style={{
                            height: `${8 + Math.sin((i * 3 + j) * 0.8) * 6}px`,
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
