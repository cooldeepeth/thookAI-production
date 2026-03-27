import { motion } from "framer-motion";
import { FolderOpen, Calendar, Target, FileText, MoreVertical, Archive, Pause, Play, CheckCircle } from "lucide-react";
import { useState, useRef, useEffect } from "react";

const STATUS_CONFIG = {
  active: { label: "Active", color: "bg-lime/15 text-lime", icon: Play },
  paused: { label: "Paused", color: "bg-yellow-500/15 text-yellow-400", icon: Pause },
  completed: { label: "Completed", color: "bg-blue-500/15 text-blue-400", icon: CheckCircle },
  archived: { label: "Archived", color: "bg-zinc-500/15 text-zinc-400", icon: Archive },
};

const PLATFORM_LABELS = {
  linkedin: { label: "LinkedIn", emoji: "💼" },
  x: { label: "X", emoji: "𝕏" },
  instagram: { label: "Instagram", emoji: "📸" },
};

export default function CampaignCard({ campaign, onClick, onStatusChange, onArchive }) {
  const [showMenu, setShowMenu] = useState(false);
  const menuRef = useRef(null);
  const statusCfg = STATUS_CONFIG[campaign.status] || STATUS_CONFIG.active;
  const StatusIcon = statusCfg.icon;

  useEffect(() => {
    function handleClickOutside(e) {
      if (menuRef.current && !menuRef.current.contains(e.target)) {
        setShowMenu(false);
      }
    }
    if (showMenu) document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [showMenu]);

  const formatDate = (dateStr) => {
    if (!dateStr) return null;
    try {
      return new Date(dateStr).toLocaleDateString("en-US", { month: "short", day: "numeric" });
    } catch {
      return null;
    }
  };

  const dateRange = (() => {
    const s = formatDate(campaign.start_date);
    const e = formatDate(campaign.end_date);
    if (s && e) return `${s} - ${e}`;
    if (s) return `From ${s}`;
    if (e) return `Until ${e}`;
    return null;
  })();

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-white/5 border border-white/10 rounded-xl overflow-hidden hover:border-white/20 transition-all group cursor-pointer"
      onClick={() => onClick(campaign)}
    >
      {/* Header */}
      <div className="p-4">
        <div className="flex items-start justify-between mb-3">
          <div className="flex items-center gap-2">
            <div className="w-9 h-9 rounded-lg bg-violet/15 flex items-center justify-center flex-shrink-0">
              <FolderOpen size={16} className="text-violet" />
            </div>
            <div className="min-w-0">
              <h3 className="font-semibold text-white text-sm truncate">{campaign.name}</h3>
              {campaign.platform && (
                <span className="text-xs text-zinc-500">
                  {PLATFORM_LABELS[campaign.platform]?.emoji}{" "}
                  {PLATFORM_LABELS[campaign.platform]?.label || campaign.platform}
                </span>
              )}
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${statusCfg.color}`}>
              {statusCfg.label}
            </span>
            <div className="relative" ref={menuRef}>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  setShowMenu(!showMenu);
                }}
                className="p-1 rounded-lg hover:bg-white/10 text-zinc-500 hover:text-white transition-colors opacity-0 group-hover:opacity-100"
              >
                <MoreVertical size={14} />
              </button>
              {showMenu && (
                <div className="absolute right-0 top-8 w-40 bg-[#1A1A1A] border border-white/10 rounded-xl shadow-xl z-20 py-1">
                  {campaign.status !== "active" && campaign.status !== "archived" && (
                    <button
                      onClick={(e) => { e.stopPropagation(); setShowMenu(false); onStatusChange(campaign.campaign_id, "active"); }}
                      className="w-full text-left px-3 py-2 text-sm text-zinc-300 hover:bg-white/5 flex items-center gap-2"
                    >
                      <Play size={14} /> Set Active
                    </button>
                  )}
                  {campaign.status !== "paused" && campaign.status !== "archived" && (
                    <button
                      onClick={(e) => { e.stopPropagation(); setShowMenu(false); onStatusChange(campaign.campaign_id, "paused"); }}
                      className="w-full text-left px-3 py-2 text-sm text-zinc-300 hover:bg-white/5 flex items-center gap-2"
                    >
                      <Pause size={14} /> Pause
                    </button>
                  )}
                  {campaign.status !== "completed" && campaign.status !== "archived" && (
                    <button
                      onClick={(e) => { e.stopPropagation(); setShowMenu(false); onStatusChange(campaign.campaign_id, "completed"); }}
                      className="w-full text-left px-3 py-2 text-sm text-zinc-300 hover:bg-white/5 flex items-center gap-2"
                    >
                      <CheckCircle size={14} /> Complete
                    </button>
                  )}
                  {campaign.status !== "archived" && (
                    <button
                      onClick={(e) => { e.stopPropagation(); setShowMenu(false); onArchive(campaign.campaign_id); }}
                      className="w-full text-left px-3 py-2 text-sm text-red-400 hover:bg-red-500/10 flex items-center gap-2"
                    >
                      <Archive size={14} /> Archive
                    </button>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>

        {campaign.description && (
          <p className="text-xs text-zinc-500 line-clamp-2 mb-3">{campaign.description}</p>
        )}

        {/* Meta row */}
        <div className="flex items-center gap-4 text-xs text-zinc-500">
          <span className="flex items-center gap-1">
            <FileText size={12} />
            {campaign.content_count || 0} post{(campaign.content_count || 0) !== 1 ? "s" : ""}
          </span>
          {dateRange && (
            <span className="flex items-center gap-1">
              <Calendar size={12} />
              {dateRange}
            </span>
          )}
          {campaign.goal && (
            <span className="flex items-center gap-1 truncate">
              <Target size={12} />
              {campaign.goal}
            </span>
          )}
        </div>
      </div>
    </motion.div>
  );
}
