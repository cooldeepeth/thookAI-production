import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import {
  ArrowLeft, ThumbsUp, Copy, Sparkles, Loader2,
  Hash, FileText, LayoutTemplate
} from "lucide-react";
import { getTemplate, upvoteTemplate, useTemplate as applyTemplate } from "@/lib/templatesApi";
import {
  PLATFORM_ICONS,
  CATEGORY_LABELS,
  HOOK_TYPE_COLORS,
} from "@/components/TemplateCard";

export default function TemplateDetail() {
  const { templateId } = useParams();
  const navigate = useNavigate();
  const [template, setTemplate] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [upvoting, setUpvoting] = useState(false);
  const [using, setUsing] = useState(false);

  useEffect(() => {
    const fetchTemplate = async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await getTemplate(templateId);
        if (data.success) {
          setTemplate(data.template);
        } else {
          setError("Template not found");
        }
      } catch (err) {
        console.error("Failed to fetch template:", err);
        setError("Template not found");
      } finally {
        setLoading(false);
      }
    };

    if (templateId) fetchTemplate();
  }, [templateId]);

  const handleUpvote = async () => {
    if (upvoting || !template) return;
    setUpvoting(true);
    try {
      const data = await upvoteTemplate(template.template_id);
      if (data.success) {
        setTemplate((prev) => ({
          ...prev,
          upvotes: prev.upvotes + (data.upvoted ? 1 : -1),
          user_upvoted: data.upvoted,
        }));
      }
    } catch (err) {
      console.error("Failed to upvote:", err);
    } finally {
      setUpvoting(false);
    }
  };

  const handleUseTemplate = async () => {
    if (using || !template) return;
    setUsing(true);
    try {
      const data = await applyTemplate(template.template_id);
      if (data.success && data.prefill) {
        const params = new URLSearchParams({
          platform: data.prefill.platform,
          prefill: data.prefill.raw_input,
          template: template.template_id,
        });
        navigate(`/dashboard/studio?${params}`);
      }
    } catch (err) {
      console.error("Failed to use template:", err);
    } finally {
      setUsing(false);
    }
  };

  if (loading) {
    return (
      <main className="flex-1 p-6">
        <div className="flex items-center justify-center py-32">
          <Loader2 size={32} className="animate-spin text-zinc-500" />
        </div>
      </main>
    );
  }

  if (error || !template) {
    return (
      <main className="flex-1 p-6">
        <div className="text-center py-32">
          <LayoutTemplate size={48} className="text-zinc-700 mx-auto mb-4" />
          <h3 className="text-lg text-zinc-500 mb-2">{error || "Template not found"}</h3>
          <button
            onClick={() => navigate("/dashboard/templates")}
            className="btn-ghost text-sm mt-4"
          >
            Back to Templates
          </button>
        </div>
      </main>
    );
  }

  const formattedDate = template.created_at
    ? new Date(template.created_at).toLocaleDateString("en-US", {
        year: "numeric",
        month: "short",
        day: "numeric",
      })
    : null;

  return (
    <main className="flex-1 p-6 max-w-3xl mx-auto">
      {/* Back button */}
      <button
        onClick={() => navigate("/dashboard/templates")}
        className="flex items-center gap-2 text-zinc-500 hover:text-white transition-colors mb-6 text-sm"
      >
        <ArrowLeft size={16} />
        Back to Templates
      </button>

      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
      >
        {/* Header */}
        <div className="flex items-start gap-4 mb-6">
          <div className="w-14 h-14 bg-violet/10 rounded-xl flex items-center justify-center text-2xl flex-shrink-0">
            {PLATFORM_ICONS[template.platform] || "📝"}
          </div>
          <div className="flex-1 min-w-0">
            <h1 className="font-display font-bold text-2xl text-white mb-1">
              {template.title}
            </h1>
            <div className="flex items-center gap-3 text-sm text-zinc-500">
              <span>{CATEGORY_LABELS[template.category] || template.category}</span>
              <span>·</span>
              <span>{template.is_official ? "ThookAI Official" : template.author_archetype}</span>
              {formattedDate && (
                <>
                  <span>·</span>
                  <span>{formattedDate}</span>
                </>
              )}
            </div>
          </div>
        </div>

        {/* Tags */}
        <div className="flex flex-wrap gap-2 mb-6">
          <span
            className={`text-xs px-2.5 py-1 rounded-full ${
              HOOK_TYPE_COLORS[template.hook_type] || "bg-white/10 text-zinc-400"
            }`}
          >
            {template.hook_type?.replace(/_/g, " ")}
          </span>
          <span className="text-xs px-2.5 py-1 rounded-full bg-white/5 text-zinc-400 capitalize">
            {template.platform}
          </span>
          {template.tags?.map((tag) => (
            <span
              key={tag}
              className="text-xs px-2.5 py-1 rounded-full bg-white/5 text-zinc-400"
            >
              <Hash size={10} className="inline mr-0.5" />
              {tag}
            </span>
          ))}
        </div>

        {/* Description */}
        {template.description && (
          <div className="bg-white/5 rounded-xl p-5 mb-4 border border-white/5">
            <p className="text-sm text-zinc-400">{template.description}</p>
          </div>
        )}

        {/* Hook section */}
        <div className="bg-white/5 rounded-xl p-5 mb-4 border border-white/5">
          <div className="flex items-center gap-2 mb-3">
            <Sparkles size={14} className="text-lime" />
            <p className="text-xs font-medium text-zinc-500 uppercase tracking-wider">Hook</p>
          </div>
          <p className="text-white font-mono text-base leading-relaxed">
            &ldquo;{template.hook}&rdquo;
          </p>
        </div>

        {/* Structure preview */}
        {template.structure_preview && (
          <div className="bg-white/5 rounded-xl p-5 mb-4 border border-white/5">
            <div className="flex items-center gap-2 mb-3">
              <FileText size={14} className="text-zinc-500" />
              <p className="text-xs font-medium text-zinc-500 uppercase tracking-wider">
                Body Structure
              </p>
            </div>
            <p className="text-zinc-400 text-sm whitespace-pre-line leading-relaxed">
              {template.structure_preview}
            </p>
          </div>
        )}

        {/* Platform formatting notes */}
        <div className="bg-white/5 rounded-xl p-5 mb-6 border border-white/5">
          <div className="flex items-center gap-2 mb-3">
            <LayoutTemplate size={14} className="text-zinc-500" />
            <p className="text-xs font-medium text-zinc-500 uppercase tracking-wider">
              Platform Notes
            </p>
          </div>
          <div className="text-sm text-zinc-500 space-y-1.5">
            {template.platform === "linkedin" && (
              <>
                <p>Optimized for LinkedIn feed engagement</p>
                <p>Best performed with line breaks between paragraphs</p>
                <p>Ideal length: 150-300 words for maximum reach</p>
              </>
            )}
            {template.platform === "x" && (
              <>
                <p>Formatted for X / Twitter thread structure</p>
                <p>Keep each section under 280 characters</p>
                <p>Strong hook in the first tweet is critical</p>
              </>
            )}
            {template.platform === "instagram" && (
              <>
                <p>Designed for Instagram caption format</p>
                <p>Pair with a compelling visual for best results</p>
                <p>Use hashtags strategically at the end</p>
              </>
            )}
            {template.word_count > 0 && (
              <p>Approximate word count: {template.word_count} words</p>
            )}
            {template.has_media && (
              <p>Original post included media assets</p>
            )}
          </div>
        </div>

        {/* Stats bar */}
        <div className="flex items-center gap-6 text-sm text-zinc-500 mb-6 px-1">
          <span className="flex items-center gap-1.5">
            <ThumbsUp size={15} />
            {template.upvotes} upvotes
          </span>
          <span className="flex items-center gap-1.5">
            <Copy size={15} />
            Used {template.uses_count} times
          </span>
          {template.views_count > 0 && (
            <span>{template.views_count} views</span>
          )}
        </div>

        {/* Action buttons */}
        <div className="flex items-center gap-3">
          <button
            onClick={handleUseTemplate}
            disabled={using}
            className="btn-primary py-3 px-6 flex items-center justify-center gap-2 flex-1"
          >
            {using ? (
              <Loader2 size={18} className="animate-spin" />
            ) : (
              <Sparkles size={18} />
            )}
            Use This Template
          </button>
          <button
            onClick={handleUpvote}
            disabled={upvoting}
            className={`py-3 px-5 rounded-xl border transition-colors flex items-center gap-2 ${
              template.user_upvoted
                ? "border-lime/30 bg-lime/10 text-lime"
                : "border-white/10 bg-white/5 text-zinc-400 hover:border-white/20 hover:text-white"
            }`}
          >
            <ThumbsUp
              size={18}
              className={template.user_upvoted ? "fill-current" : ""}
            />
            {template.user_upvoted ? "Upvoted" : "Upvote"}
          </button>
        </div>
      </motion.div>
    </main>
  );
}
