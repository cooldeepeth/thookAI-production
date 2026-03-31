import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import {
  Sparkles, TrendingUp, Lightbulb, Clock, Battery, BatteryLow, BatteryMedium,
  ChevronDown, ChevronUp, X, RefreshCw, Linkedin, Twitter, Instagram, ArrowRight
} from "lucide-react";

const API_URL = process.env.REACT_APP_BACKEND_URL;

const platformIcons = {
  linkedin: { icon: Linkedin, color: "#0A66C2" },
  x: { icon: Twitter, color: "#1D9BF0" },
  instagram: { icon: Instagram, color: "#E1306C" }
};

const energyIcons = {
  energized: { icon: Battery, color: "text-green-400", bg: "bg-green-400/10" },
  balanced: { icon: BatteryMedium, color: "text-yellow-400", bg: "bg-yellow-400/10" },
  rest: { icon: BatteryLow, color: "text-red-400", bg: "bg-red-400/10" }
};

function BriefSkeleton() {
  return (
    <div className="animate-pulse space-y-4">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-zinc-800" />
        <div className="space-y-2">
          <div className="h-4 w-40 bg-zinc-800 rounded" />
          <div className="h-3 w-24 bg-zinc-800 rounded" />
        </div>
      </div>
      <div className="grid grid-cols-3 gap-3">
        <div className="h-24 bg-zinc-800 rounded-xl" />
        <div className="h-24 bg-zinc-800 rounded-xl" />
        <div className="h-24 bg-zinc-800 rounded-xl" />
      </div>
    </div>
  );
}

function ContentIdeaCard({ idea, onSelect }) {
  const PlatformConfig = platformIcons[idea.platform] || platformIcons.linkedin;
  const PlatformIcon = PlatformConfig.icon;

  return (
    <motion.button
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
      onClick={() => onSelect(idea)}
      className="card-thook p-4 text-left hover:border-lime/30 transition-all group"
    >
      <div className="flex items-start gap-3">
        <div
          className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0"
          style={{ backgroundColor: `${PlatformConfig.color}15` }}
        >
          <PlatformIcon size={16} style={{ color: PlatformConfig.color }} />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-white group-hover:text-lime transition-colors line-clamp-1">
            {idea.title}
          </p>
          <p className="text-xs text-zinc-500 mt-1 line-clamp-2">
            "{idea.hook}"
          </p>
        </div>
        <ArrowRight size={14} className="text-zinc-600 group-hover:text-lime transition-colors flex-shrink-0 mt-1" />
      </div>
    </motion.button>
  );
}

function TrendingChip({ topic }) {
  return (
    <span className="inline-flex items-center gap-1.5 text-xs bg-violet/10 text-violet px-3 py-1.5 rounded-full">
      <TrendingUp size={12} />
      {topic}
    </span>
  );
}

export default function DailyBrief() {
  const navigate = useNavigate();
  const [brief, setBrief] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [expanded, setExpanded] = useState(true);
  const [dismissed, setDismissed] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    checkAndFetchBrief();
  }, []);

  const checkAndFetchBrief = async () => {
    try {
      // Check if dismissed
      const statusRes = await fetch(`${API_URL}/api/dashboard/daily-brief/status`, {
        credentials: "include"
      });
      if (statusRes.ok) {
        const status = await statusRes.json();
        if (!status.show_brief) {
          setDismissed(true);
          setLoading(false);
          return;
        }
      }
      
      // Fetch brief
      await fetchBrief();
    } catch (err) {
      console.error("Brief check error:", err);
      setLoading(false);
    }
  };

  const fetchBrief = async (refresh = false) => {
    try {
      setLoading(!refresh);
      setRefreshing(refresh);
      
      const url = refresh 
        ? `${API_URL}/api/dashboard/daily-brief?refresh=true`
        : `${API_URL}/api/dashboard/daily-brief`;
      
      const response = await fetch(url, {
        credentials: "include"
      });
      
      if (!response.ok) throw new Error("Failed to fetch brief");
      
      const data = await response.json();
      setBrief(data);
      setError(null);
    } catch (err) {
      console.error("Brief fetch error:", err);
      setError(err.message);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const handleDismiss = async () => {
    try {
      await fetch(`${API_URL}/api/dashboard/daily-brief/dismiss`, {
        method: "POST",
        credentials: "include"
      });
      setDismissed(true);
    } catch (err) {
      console.error("Dismiss error:", err);
    }
  };

  const handleSelectIdea = (idea) => {
    // Navigate to Content Studio with pre-filled data
    const params = new URLSearchParams({
      platform: idea.platform,
      prefill: idea.hook
    });
    navigate(`/dashboard/studio?${params.toString()}`);
  };

  if (dismissed) return null;
  if (loading) {
    return (
      <div className="card-thook p-5 mb-6">
        <BriefSkeleton />
      </div>
    );
  }
  if (error || !brief) return null;

  const EnergyConfig = energyIcons[brief.energy_check?.status] || energyIcons.balanced;
  const EnergyIcon = EnergyConfig.icon;

  return (
    <motion.div
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-violet/10 via-transparent to-lime/5 border border-violet/20 mb-6"
      data-testid="daily-brief"
    >
      {/* Header */}
      <div className="px-5 py-4 flex items-center justify-between">
        <button
          onClick={() => setExpanded(!expanded)}
          className="flex items-center gap-3 text-left flex-1"
        >
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-violet to-lime/50 flex items-center justify-center">
            <Sparkles size={20} className="text-white" />
          </div>
          <div>
            <h3 className="font-display font-semibold text-white text-base">
              {brief.greeting}
            </h3>
            <p className="text-xs text-zinc-500">{brief.date_context}</p>
          </div>
          {expanded ? (
            <ChevronUp size={16} className="text-zinc-500 ml-2" />
          ) : (
            <ChevronDown size={16} className="text-zinc-500 ml-2" />
          )}
        </button>
        
        <div className="flex items-center gap-2">
          <button
            onClick={() => fetchBrief(true)}
            disabled={refreshing}
            className="p-2 hover:bg-white/5 rounded-lg transition-colors"
            title="Refresh brief"
          >
            <RefreshCw size={14} className={`text-zinc-500 ${refreshing ? 'animate-spin' : ''}`} />
          </button>
          <button
            onClick={handleDismiss}
            className="p-2 hover:bg-white/5 rounded-lg transition-colors"
            title="Dismiss for today"
          >
            <X size={14} className="text-zinc-500" />
          </button>
        </div>
      </div>

      {/* Expandable Content */}
      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="px-5 pb-5 space-y-4">
              {/* Energy Check */}
              <div className={`flex items-center gap-3 p-3 rounded-xl ${EnergyConfig.bg}`}>
                <EnergyIcon size={18} className={EnergyConfig.color} />
                <p className={`text-sm ${EnergyConfig.color}`}>
                  {brief.energy_check?.message}
                </p>
              </div>

              {/* Trending Topics */}
              {brief.trending_topics?.length > 0 && (
                <div>
                  <p className="text-[10px] text-zinc-600 uppercase tracking-wider mb-2 font-mono">
                    Trending in your niche
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {brief.trending_topics.map((topic, i) => (
                      <TrendingChip key={i} topic={topic} />
                    ))}
                  </div>
                </div>
              )}

              {/* Content Ideas */}
              {brief.content_ideas?.length > 0 && (
                <div>
                  <div className="flex items-center gap-2 mb-2">
                    <Lightbulb size={12} className="text-lime" />
                    <p className="text-[10px] text-zinc-600 uppercase tracking-wider font-mono">
                      Today's content ideas
                    </p>
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                    {brief.content_ideas.map((idea, i) => (
                      <ContentIdeaCard
                        key={i}
                        idea={idea}
                        onSelect={handleSelectIdea}
                      />
                    ))}
                  </div>
                </div>
              )}

              {/* Optimal Time */}
              {brief.optimal_time && (
                <div className="flex items-center gap-2 text-xs text-zinc-500">
                  <Clock size={12} />
                  <span>Best time to post today: <span className="text-white">{brief.optimal_time}</span></span>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
