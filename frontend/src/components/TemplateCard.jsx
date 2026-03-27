import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { ThumbsUp, Copy, Sparkles } from "lucide-react";

const PLATFORM_ICONS = {
  linkedin: "💼",
  x: "𝕏",
  instagram: "📸",
};

const CATEGORY_LABELS = {
  thought_leadership: "Thought Leadership",
  storytelling: "Storytelling",
  how_to: "How-To Guide",
  listicle: "Listicle",
  contrarian: "Contrarian Take",
  case_study: "Case Study",
  personal_journey: "Personal Journey",
  industry_insights: "Industry Insights",
  tips_and_tricks: "Tips & Tricks",
  behind_the_scenes: "Behind the Scenes",
};

const HOOK_TYPE_COLORS = {
  question: "bg-cyan-500/20 text-cyan-400",
  bold_claim: "bg-orange-500/20 text-orange-400",
  story_opener: "bg-violet-500/20 text-violet-400",
  statistic: "bg-blue-500/20 text-blue-400",
  contrarian: "bg-pink-500/20 text-pink-400",
  curiosity_gap: "bg-yellow-500/20 text-yellow-400",
  direct_address: "bg-lime/20 text-lime",
  number_list: "bg-emerald-500/20 text-emerald-400",
};

export { PLATFORM_ICONS, CATEGORY_LABELS, HOOK_TYPE_COLORS };

export default function TemplateCard({ template, onUse, onUpvote, showUseButton = true }) {
  const navigate = useNavigate();
  const [upvoting, setUpvoting] = useState(false);

  const handleUpvote = async (e) => {
    e.stopPropagation();
    if (upvoting) return;
    setUpvoting(true);
    try {
      await onUpvote(template.template_id);
    } finally {
      setUpvoting(false);
    }
  };

  const handleUse = (e) => {
    e.stopPropagation();
    onUse(template);
  };

  const handleCardClick = () => {
    navigate(`/dashboard/templates/${template.template_id}`);
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      onClick={handleCardClick}
      className="bg-white/5 border border-white/10 rounded-xl overflow-hidden hover:border-white/20 transition-all group cursor-pointer"
    >
      {/* Header */}
      <div className="p-4 border-b border-white/5">
        <div className="flex items-start justify-between mb-2">
          <div className="flex items-center gap-2">
            <span className="text-lg">{PLATFORM_ICONS[template.platform] || "📝"}</span>
            <span className={`text-xs px-2 py-0.5 rounded-full ${HOOK_TYPE_COLORS[template.hook_type] || "bg-white/10 text-zinc-400"}`}>
              {template.hook_type?.replace(/_/g, " ")}
            </span>
          </div>
          <span className="text-xs text-zinc-600">
            {template.is_official ? "ThookAI Official" : template.author_archetype}
          </span>
        </div>
        <h3 className="font-semibold text-white line-clamp-1">{template.title}</h3>
        <p className="text-xs text-zinc-500 mt-1">
          {CATEGORY_LABELS[template.category] || template.category}
        </p>
      </div>

      {/* Preview */}
      <div className="p-4 bg-black/20">
        <p className="text-sm text-zinc-400 line-clamp-3 font-mono">
          &ldquo;{template.hook}&rdquo;
        </p>
        {template.structure_preview && (
          <p className="text-xs text-zinc-600 mt-2 line-clamp-2">
            {template.structure_preview}
          </p>
        )}
      </div>

      {/* Footer */}
      <div className="p-4 flex items-center justify-between">
        <div className="flex items-center gap-4 text-xs text-zinc-500">
          <button
            onClick={handleUpvote}
            disabled={upvoting}
            className={`flex items-center gap-1 hover:text-lime transition-colors ${template.user_upvoted ? "text-lime" : ""}`}
          >
            <ThumbsUp size={14} className={template.user_upvoted ? "fill-current" : ""} />
            {template.upvotes}
          </button>
          <span className="flex items-center gap-1">
            <Copy size={14} />
            Used {template.uses_count} times
          </span>
        </div>
        {showUseButton && (
          <button
            onClick={handleUse}
            className="btn-primary text-xs py-1.5 px-3 opacity-0 group-hover:opacity-100 transition-opacity flex items-center gap-1"
          >
            <Sparkles size={12} />
            Use Template
          </button>
        )}
      </div>
    </motion.div>
  );
}
