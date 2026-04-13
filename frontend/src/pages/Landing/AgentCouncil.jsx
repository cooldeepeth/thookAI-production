import { motion } from "framer-motion";

const agents = [
  { name: "Commander", model: "Claude Sonnet 4", role: "Orchestrates all flows" },
  { name: "Scout", model: "Perplexity", role: "Research & trends" },
  { name: "Thinker", model: "Claude Haiku", role: "Content strategy" },
  { name: "Writer", model: "Claude Sonnet 4", role: "Voice-matched copy" },
  { name: "Persona", model: "Claude Sonnet 4", role: "Identity cloning" },
  { name: "Visual", model: "Gemini Vision", role: "Media analysis" },
  { name: "Designer", model: "DALL-E", role: "Carousels & graphics" },
  { name: "Director", model: "Kling/Runway", role: "Video generation" },
  { name: "Clone", model: "HeyGen", role: "AI avatar videos" },
  { name: "Voice", model: "ElevenLabs", role: "Voice cloning" },
  { name: "QC", model: "Claude Haiku", role: "Quality control" },
  { name: "Analyst", model: "Claude Sonnet 4", role: "Performance tracking" },
  { name: "Planner", model: "Claude Haiku", role: "Optimal scheduling" },
  { name: "Editor", model: "Vizard", role: "Video editing" },
  { name: "Sound", model: "Suno", role: "Audio branding" },
];

export function AgentCouncil() {
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
