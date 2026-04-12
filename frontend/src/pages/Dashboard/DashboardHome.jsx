import { useState, useEffect } from "react";
import { useAuth } from "@/context/AuthContext";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import {
  PenLine, Brain, RefreshCw, BarChart2, Zap, ArrowRight,
  Linkedin, Twitter, Instagram, Clock, CheckCircle2, XCircle, AlertCircle
} from "lucide-react";
import DailyBrief from "./DailyBrief";
import { apiFetch } from '@/lib/api';

const quickActions = [
  { label: "Write a LinkedIn post", icon: Linkedin, color: "#0A66C2", to: "/dashboard/studio", tag: "Text" },
  { label: "Write an X thread", icon: Twitter, color: "#1D9BF0", to: "/dashboard/studio", tag: "Thread" },
  { label: "Instagram caption", icon: Instagram, color: "#E1306C", to: "/dashboard/studio", tag: "Caption" },
  { label: "Repurpose content", icon: RefreshCw, color: "#D4FF00", to: "/dashboard/repurpose", tag: "Repurpose" },
];

const upcomingFeatures = [
  { title: "API Webhooks", desc: "Real-time notifications for content events", icon: Zap, status: "coming" },
  { title: "Team Analytics", desc: "Cross-creator performance insights", icon: BarChart2, status: "coming" },
  { title: "AI Voice Cloning", desc: "Generate audio content in your voice", icon: Brain, status: "coming" },
];

const platformIcons = {
  linkedin: Linkedin,
  x: Twitter,
  instagram: Instagram
};

const statusIcons = {
  approved: { icon: CheckCircle2, color: "text-green-500" },
  rejected: { icon: XCircle, color: "text-red-500" },
  reviewing: { icon: AlertCircle, color: "text-yellow-500" },
  completed: { icon: AlertCircle, color: "text-yellow-500" },
  running: { icon: Clock, color: "text-blue-500" },
  error: { icon: XCircle, color: "text-red-500" }
};

function StatSkeleton() {
  return (
    <div className="card-thook p-4 animate-pulse">
      <div className="h-3 w-16 bg-zinc-800 rounded mb-2" />
      <div className="h-8 w-20 bg-zinc-800 rounded" />
    </div>
  );
}

function RecentJobCard({ job }) {
  const navigate = useNavigate();
  const PlatformIcon = platformIcons[job.platform] || PenLine;
  const StatusConfig = statusIcons[job.status] || statusIcons.reviewing;
  const StatusIcon = StatusConfig.icon;
  
  const formatDate = (dateStr) => {
    if (!dateStr) return "";
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);
    
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    return `${diffDays}d ago`;
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="card-thook p-4 hover:border-zinc-700 transition-colors cursor-pointer"
      onClick={() => navigate(`/dashboard/studio?job=${job.job_id}`)}
    >
      <div className="flex items-start gap-3">
        <div className="w-9 h-9 rounded-xl bg-white/5 flex items-center justify-center flex-shrink-0">
          <PlatformIcon size={18} className="text-zinc-400" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-sm font-medium text-white capitalize">{job.platform} {job.content_type}</span>
            <StatusIcon size={14} className={StatusConfig.color} />
          </div>
          {job.preview && (
            <p className="text-xs text-zinc-500 truncate">{job.preview}</p>
          )}
          <div className="flex items-center gap-3 mt-2">
            <span className="text-[10px] text-zinc-600">{formatDate(job.created_at)}</span>
            {job.persona_match && (
              <span className="text-[10px] text-zinc-500">
                Persona: <span className="text-lime">{job.persona_match}/10</span>
              </span>
            )}
          </div>
        </div>
      </div>
    </motion.div>
  );
}

export default function DashboardHome() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const hour = new Date().getHours();
  const greeting = hour < 12 ? "Good morning" : hour < 18 ? "Good afternoon" : "Good evening";

  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [statsError, setStatsError] = useState(null);

  const fetchStats = async () => {
    if (!user) return;

    try {
      setLoading(true);
      setStatsError(null);
      const response = await apiFetch('/api/dashboard/stats');

      if (!response.ok) {
        throw new Error("Failed to fetch stats");
      }

      const data = await response.json();
      setStats(data);
    } catch (err) {
      setStatsError(err.message || "Failed to load stats");
    } finally {
      setLoading(false);
    }
  };

  const handleRetryStats = () => {
    setStatsError(null);
    fetchStats();
  };

  useEffect(() => {
    fetchStats();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user]);

  const displayStats = [
    { 
      label: "Credits", 
      value: stats?.credits ?? user?.credits ?? 100, 
      unit: "", 
      color: "text-lime" 
    },
    { 
      label: "Posts Created", 
      value: stats?.posts_created ?? 0, 
      unit: "", 
      color: "text-white" 
    },
    { 
      label: "Platforms", 
      value: stats?.platforms_count ?? 0, 
      unit: "of 3", 
      color: "text-white" 
    },
    { 
      label: "Persona Score", 
      value: stats?.persona_score ?? "–", 
      unit: stats?.persona_score ? "/10" : "", 
      color: stats?.persona_score ? "text-lime" : "text-zinc-500" 
    },
  ];

  return (
    <main className="p-6 space-y-6" data-testid="dashboard-home">
      {/* Greeting */}
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
      >
        <h2 className="font-display text-2xl font-bold text-white">
          {greeting}, <span className="text-lime">{user?.name?.split(" ")[0] || "Creator"}</span>
        </h2>
        <p className="text-zinc-500 text-sm mt-1">Ready to create content that sounds like you?</p>
      </motion.div>

      {/* Onboarding banner */}
      {!user?.onboarding_completed && (
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="relative overflow-hidden rounded-2xl p-5 bg-gradient-to-r from-violet/20 to-transparent border border-violet/20"
          data-testid="onboarding-banner"
        >
          <div className="absolute right-4 top-1/2 -translate-y-1/2 text-5xl opacity-20">
            <Brain size={64} className="text-violet" />
          </div>
          <div className="relative z-10">
            <p className="text-xs text-violet font-semibold uppercase tracking-wider mb-1">Setup required</p>
            <h3 className="font-display font-semibold text-white text-lg">Complete your Persona Engine setup</h3>
            <p className="text-zinc-400 text-sm mt-1 mb-3">
              Your AI voice clone needs 15 minutes to learn your style. This unlocks all content creation features.
            </p>
            <button
              onClick={() => navigate("/onboarding")}
              data-testid="start-onboarding-btn"
              className="flex items-center gap-2 bg-violet text-white text-sm font-medium rounded-full px-5 py-2.5 hover:bg-violet/90 transition-colors"
            >
              <Zap size={14} />
              Set up Persona Engine
              <ArrowRight size={14} />
            </button>
          </div>
        </motion.div>
      )}

      {/* Daily Brief - AI-powered content suggestions */}
      {user?.onboarding_completed && <DailyBrief />}

      {/* Stats row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
        {loading ? (
          <>
            <StatSkeleton />
            <StatSkeleton />
            <StatSkeleton />
            <StatSkeleton />
          </>
        ) : statsError ? (
          <div className="col-span-full flex flex-col items-center justify-center py-16 px-6" role="alert" data-testid="stats-error">
            <AlertCircle className="text-red-400 mb-3" size={28} />
            <p className="text-red-400 text-sm text-center mb-4">{statsError}</p>
            <button
              type="button"
              onClick={handleRetryStats}
              className="btn-ghost text-sm flex items-center gap-2 focus-ring"
              data-testid="retry-stats-btn"
            >
              <RefreshCw size={14} />
              Try Again
            </button>
          </div>
        ) : (
          displayStats.map((stat, i) => (
            <motion.div
              key={stat.label}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 + i * 0.05 }}
              className="card-thook p-4"
              data-testid={`stat-${stat.label.toLowerCase().replace(/\s+/g, '-')}`}
            >
              <p className="text-zinc-500 text-xs mb-1">{stat.label}</p>
              <p className={`font-display font-bold text-2xl ${stat.color}`}>
                {stat.value}<span className="text-sm text-zinc-500 font-normal">{stat.unit}</span>
              </p>
            </motion.div>
          ))
        )}
      </div>

      {/* Recent Content */}
      {stats && (!stats.recent_jobs || stats.recent_jobs.length === 0) && user?.onboarding_completed && (
        <div className="card-thook p-8 text-center" data-testid="empty-content">
          <p className="text-zinc-500 text-sm mb-3">No content generated yet.</p>
          <button
            type="button"
            onClick={() => navigate("/dashboard/studio")}
            className="text-lime text-sm hover:text-lime/80 focus-ring"
            data-testid="empty-content-cta"
          >
            Generate your first post →
          </button>
        </div>
      )}
      {stats?.recent_jobs && stats.recent_jobs.length > 0 && (
        <div>
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-semibold text-zinc-400 uppercase tracking-wider">Recent Content</h3>
            <button 
              onClick={() => navigate("/dashboard/library")}
              className="text-xs text-lime hover:text-lime/80 transition-colors"
            >
              View All
            </button>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            {stats.recent_jobs.map((job, i) => (
              <RecentJobCard key={job.job_id} job={job} />
            ))}
          </div>
        </div>
      )}

      {/* Learning Insights Banner */}
      {stats?.learning_signals_count > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="card-thook p-4 border-lime/20"
        >
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-lime/10 flex items-center justify-center">
              <Brain size={20} className="text-lime" />
            </div>
            <div className="flex-1">
              <p className="text-sm font-medium text-white">Your AI is learning</p>
              <p className="text-xs text-zinc-500">
                {stats.learning_signals_count} interaction{stats.learning_signals_count !== 1 ? 's' : ''} recorded · 
                Persona getting smarter with each approval
              </p>
            </div>
            <button 
              onClick={() => navigate("/dashboard/persona")}
              className="text-xs text-lime hover:text-lime/80 transition-colors"
            >
              View Insights
            </button>
          </div>
        </motion.div>
      )}

      {/* Quick Actions */}
      <div>
        <h3 className="text-sm font-semibold text-zinc-400 uppercase tracking-wider mb-3">Quick Create</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {quickActions.map((action, i) => (
            <motion.button
              key={action.label}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 + i * 0.05 }}
              onClick={() => navigate(action.to)}
              data-testid={`quick-action-${i}`}
              className="card-thook p-4 text-left hover:scale-[1.02] transition-transform group"
            >
              <div className="w-9 h-9 rounded-xl flex items-center justify-center mb-3" style={{ backgroundColor: `${action.color}15` }}>
                <action.icon size={18} style={{ color: action.color }} />
              </div>
              <p className="text-sm font-medium text-white group-hover:text-lime transition-colors">{action.label}</p>
              <span className="text-xs text-zinc-600 mt-1 block">{action.tag}</span>
            </motion.button>
          ))}
        </div>
      </div>

      {/* Coming Soon Features */}
      <div>
        <h3 className="text-sm font-semibold text-zinc-400 uppercase tracking-wider mb-3">Coming Soon</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {upcomingFeatures.map((f, i) => (
            <motion.div
              key={f.title}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 + i * 0.05 }}
              className="card-thook p-4 flex items-start gap-3"
            >
              <div className="w-9 h-9 rounded-xl bg-violet/10 flex items-center justify-center flex-shrink-0">
                <f.icon size={18} className="text-violet" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <p className="text-sm font-medium text-white">{f.title}</p>
                  <span className="text-[10px] font-mono text-violet bg-violet/10 px-1.5 py-0.5 rounded">Soon</span>
                </div>
                <p className="text-xs text-zinc-500">{f.desc}</p>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </main>
  );
}
