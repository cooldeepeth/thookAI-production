import { motion } from "framer-motion";
import { Check, Loader2, Clock } from "lucide-react";

const AGENTS = [
  { key: "commander", name: "Commander", model: "GPT-4o", desc: "Building your content strategy...", doneDesc: (s) => s || "Strategy defined" },
  { key: "scout", name: "Scout", model: "Perplexity", desc: "Researching trends & data...", doneDesc: (s) => s || "Research complete" },
  { key: "thinker", name: "Thinker", model: "o4-mini", desc: "Developing the content angle...", doneDesc: (s) => s || "Angle defined" },
  { key: "writer", name: "Writer", model: "Claude", desc: "Writing in your voice...", doneDesc: (s) => s || "Draft ready" },
  { key: "qc", name: "QC", model: "GPT-4.1-mini", desc: "Scoring persona match & AI risk...", doneDesc: (s) => s || "Quality check done" },
];

const AGENT_ORDER = AGENTS.map(a => a.key);

function getAgentStatus(agentKey, currentAgent, jobStatus) {
  if (jobStatus === "error" && currentAgent === "error") return "error";
  const currentIdx = AGENT_ORDER.indexOf(currentAgent);
  const agentIdx = AGENT_ORDER.indexOf(agentKey);
  if (agentIdx < currentIdx) return "done";
  if (agentKey === currentAgent) return "running";
  if (currentAgent === "done" || jobStatus === "reviewing" || jobStatus === "completed") return "done";
  return "waiting";
}

export default function AgentPipeline({ job, platform, rawInput }) {
  const currentAgent = job?.current_agent || "commander";
  const jobStatus = job?.status || "running";
  const summaries = job?.agent_summaries || {};

  return (
    <div className="max-w-lg mx-auto" data-testid="agent-pipeline">
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center gap-2 mb-1">
          <div className="w-2 h-2 bg-lime rounded-full animate-pulse" />
          <span className="text-xs font-mono text-lime uppercase tracking-wider">Agents at work</span>
        </div>
        <h3 className="font-display font-semibold text-white text-lg">Creating your {platform} content</h3>
        {rawInput && <p className="text-zinc-500 text-sm mt-1 truncate">"{rawInput.substring(0, 60)}..."</p>}
      </div>

      {/* Agent cards */}
      <div className="space-y-3">
        {AGENTS.map((agent, i) => {
          const status = getAgentStatus(agent.key, currentAgent, jobStatus);
          const summary = summaries[agent.key];

          return (
            <motion.div
              key={agent.key}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.08 }}
              className={`card-thook p-4 transition-all ${
                status === "running" ? "border-lime/20 bg-lime/3" :
                status === "done" ? "border-white/10" :
                "opacity-40"
              }`}
              data-testid={`agent-${agent.key}`}
            >
              <div className="flex items-center gap-3">
                {/* Status icon */}
                <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${
                  status === "done" ? "bg-lime/15" :
                  status === "running" ? "bg-white/10" : "bg-white/5"
                }`}>
                  {status === "done" && <Check size={14} className="text-lime" />}
                  {status === "running" && <Loader2 size={14} className="text-white animate-spin" />}
                  {status === "waiting" && <Clock size={14} className="text-zinc-600" />}
                  {status === "error" && <span className="text-red-400 text-xs">!</span>}
                </div>

                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-0.5">
                    <p className={`text-sm font-semibold ${status === "done" ? "text-white" : status === "running" ? "text-white" : "text-zinc-600"}`}>
                      {agent.name}
                    </p>
                    <span className={`text-[10px] font-mono rounded-full px-1.5 py-0.5 ${
                      status === "running" ? "bg-lime/10 text-lime" : "bg-white/5 text-zinc-600"
                    }`}>{agent.model}</span>
                  </div>
                  <p className="text-xs text-zinc-500 truncate">
                    {status === "running" ? agent.desc :
                     status === "done" ? agent.doneDesc(summary) :
                     "Waiting..."}
                  </p>
                </div>

                {status === "done" && (
                  <span className="text-[10px] text-lime font-mono flex-shrink-0">✓</span>
                )}
              </div>
            </motion.div>
          );
        })}
      </div>

      {/* Error state */}
      {jobStatus === "error" && (
        <div className="mt-4 p-3 bg-red-500/10 border border-red-500/20 rounded-xl">
          <p className="text-red-400 text-sm">{job?.error || "Something went wrong. Please try again."}</p>
        </div>
      )}
    </div>
  );
}
