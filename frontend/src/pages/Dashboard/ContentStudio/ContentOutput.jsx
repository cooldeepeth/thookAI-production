import { useState } from "react";
import { motion } from "framer-motion";
import { Check, Edit2, RefreshCw, X, ChevronDown, ChevronUp } from "lucide-react";

function QCBadge({ label, value, max, isRisk = false }) {
  const pct = (value / max) * 100;
  const isGood = isRisk ? value <= 35 : value >= 7;
  const color = isGood ? "bg-lime" : value >= (isRisk ? 60 : 5) ? "bg-yellow-400" : "bg-red-400";
  const textColor = isGood ? "text-lime" : "text-yellow-400";

  return (
    <div className="bg-white/3 rounded-xl p-3 flex-1">
      <div className="flex items-center justify-between mb-1.5">
        <span className="text-xs text-zinc-500">{label}</span>
        <span className={`text-xs font-mono font-bold ${textColor}`}>
          {value}{max === 10 ? "/10" : "/100"}
        </span>
      </div>
      <div className="h-1.5 bg-white/5 rounded-full overflow-hidden">
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${isRisk ? 100 - pct : pct}%` }}
          transition={{ duration: 0.8, ease: "easeOut" }}
          className={`h-full rounded-full ${color}`}
        />
      </div>
      <p className="text-[10px] text-zinc-700 mt-1">{isGood ? "Good" : "Needs work"}</p>
    </div>
  );
}

function ScoutResearch({ scout }) {
  const [expanded, setExpanded] = useState(false);
  if (!scout?.findings) return null;

  return (
    <div className="card-thook p-4 mt-4">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center justify-between w-full"
      >
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold text-zinc-400">Scout Research</span>
          {scout.sources_found > 0 && (
            <span className="text-[10px] text-lime bg-lime/10 rounded-full px-2 py-0.5">{scout.sources_found} sources</span>
          )}
        </div>
        {expanded ? <ChevronUp size={13} className="text-zinc-500" /> : <ChevronDown size={13} className="text-zinc-500" />}
      </button>
      {expanded && (
        <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }} className="mt-3">
          <p className="text-xs text-zinc-500 leading-relaxed whitespace-pre-line">{scout.findings}</p>
        </motion.div>
      )}
    </div>
  );
}

export default function ContentOutput({ job, onApprove, onRegenerate, onDiscard }) {
  const [editing, setEditing] = useState(false);
  const [editedContent, setEditedContent] = useState(job.final_content || "");
  const [approved, setApproved] = useState(job.status === "approved");

  const qc = job.qc_score || {};
  const scout = job.agent_outputs?.scout;
  const platform = job.platform || "linkedin";
  const isApproved = approved || job.status === "approved";

  const platformStyles = {
    linkedin: { color: "#0A66C2", label: "LinkedIn" },
    x: { color: "#1D9BF0", label: "X" },
    instagram: { color: "#E1306C", label: "Instagram" },
  };
  const ps = platformStyles[platform] || platformStyles.linkedin;

  const handleApprove = async () => {
    await onApprove(editing ? editedContent : job.final_content);
    setApproved(true);
    setEditing(false);
  };

  return (
    <div className="max-w-xl mx-auto" data-testid="content-output">
      {/* Success banner if approved */}
      {isApproved && (
        <motion.div
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-center gap-3 bg-lime/10 border border-lime/20 rounded-xl p-3 mb-4"
          data-testid="approved-banner"
        >
          <Check size={16} className="text-lime" />
          <p className="text-sm text-white font-medium">Content approved — saved to your library</p>
        </motion.div>
      )}

      {/* QC Scores */}
      <div className="mb-4">
        <div className="flex items-center justify-between mb-2">
          <p className="text-xs text-zinc-500 uppercase tracking-wider font-mono">Quality Scores</p>
          <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${
            qc.overall_pass ? "bg-lime/15 text-lime" : "bg-yellow-400/10 text-yellow-400"
          }`} data-testid="qc-overall-badge">
            {qc.overall_pass ? "✓ PASS" : "⚠ REVIEW"}
          </span>
        </div>
        <div className="flex gap-2">
          <QCBadge label="Persona Match" value={qc.personaMatch || 0} max={10} />
          <QCBadge label="AI Risk" value={qc.aiRisk || 0} max={100} isRisk />
          <QCBadge label="Platform Fit" value={qc.platformFit || 0} max={10} />
        </div>
      </div>

      {/* Content Preview */}
      <div className="card-thook overflow-hidden mb-4" data-testid="content-draft-card">
        {/* Platform header */}
        <div className="flex items-center gap-2 px-4 py-2.5 border-b border-white/5"
          style={{ backgroundColor: `${ps.color}10` }}>
          <div className="w-2 h-2 rounded-full" style={{ backgroundColor: ps.color }} />
          <span className="text-xs font-medium" style={{ color: ps.color }}>{ps.label} · {job.content_type}</span>
          <span className="ml-auto text-[10px] font-mono text-zinc-600">
            {(job.final_content || "").split(" ").length} words
          </span>
        </div>

        {/* Content */}
        {editing ? (
          <textarea
            value={editedContent}
            onChange={e => setEditedContent(e.target.value)}
            data-testid="content-edit-textarea"
            className="w-full min-h-[200px] bg-[#18181B] text-white text-sm p-4 outline-none resize-y leading-relaxed"
            autoFocus
          />
        ) : (
          <div
            data-testid="content-text"
            className="p-4 text-sm text-zinc-200 leading-relaxed whitespace-pre-wrap cursor-text"
            onClick={() => setEditing(true)}
          >
            {job.final_content || "Content unavailable"}
          </div>
        )}
      </div>

      {/* QC Feedback */}
      {qc.feedback?.length > 0 && !isApproved && (
        <div className="card-thook p-4 mb-4">
          <p className="text-xs text-zinc-500 uppercase tracking-wider mb-2 font-mono">Agent Feedback</p>
          <div className="space-y-1.5">
            {qc.feedback.slice(0, 2).map((f, i) => (
              <div key={i} className="flex items-start gap-2">
                <span className="text-yellow-400 text-xs flex-shrink-0 mt-0.5">→</span>
                <p className="text-xs text-zinc-400">{f}</p>
              </div>
            ))}
          </div>
          {qc.strengths?.length > 0 && (
            <div className="mt-3 space-y-1">
              {qc.strengths.slice(0, 1).map((s, i) => (
                <div key={i} className="flex items-start gap-2">
                  <span className="text-lime text-xs flex-shrink-0 mt-0.5">✓</span>
                  <p className="text-xs text-zinc-500">{s}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Scout research (expandable) */}
      <ScoutResearch scout={scout} />

      {/* Action buttons */}
      {!isApproved && (
        <div className="flex gap-2 mt-4">
          <button
            onClick={handleApprove}
            data-testid="approve-btn"
            className="flex-1 btn-primary flex items-center justify-center gap-2 text-sm"
          >
            <Check size={14} /> {editing ? "Save & Approve" : "Looks great"}
          </button>
          <button
            onClick={() => setEditing(!editing)}
            data-testid="edit-btn"
            className={`btn-ghost text-sm px-4 flex items-center gap-2 ${editing ? "border-lime/30 text-lime" : ""}`}
          >
            <Edit2 size={13} /> {editing ? "Preview" : "Edit"}
          </button>
          <button
            onClick={onRegenerate}
            data-testid="regenerate-btn"
            className="btn-ghost text-sm px-4 flex items-center gap-2"
            title="Regenerate"
          >
            <RefreshCw size={13} />
          </button>
          <button
            onClick={onDiscard}
            data-testid="discard-btn"
            className="btn-ghost text-sm px-3 text-zinc-600 hover:text-red-400"
            title="Discard"
          >
            <X size={14} />
          </button>
        </div>
      )}
    </div>
  );
}
