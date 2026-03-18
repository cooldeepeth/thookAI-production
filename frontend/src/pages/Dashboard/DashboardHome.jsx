import { useAuth } from "@/context/AuthContext";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import {
  PenLine, Brain, RefreshCw, BarChart2, Zap, ArrowRight,
  Linkedin, Twitter, Instagram
} from "lucide-react";

const quickActions = [
  { label: "Write a LinkedIn post", icon: Linkedin, color: "#0A66C2", to: "/dashboard/studio", tag: "Text" },
  { label: "Write an X thread", icon: Twitter, color: "#1D9BF0", to: "/dashboard/studio", tag: "Thread" },
  { label: "Instagram caption", icon: Instagram, color: "#E1306C", to: "/dashboard/studio", tag: "Caption" },
  { label: "Repurpose content", icon: RefreshCw, color: "#D4FF00", to: "/dashboard/repurpose", tag: "Repurpose" },
];

const upcomingFeatures = [
  { sprint: 2, title: "Persona Engine", desc: "Set up your AI voice clone", icon: Brain, ready: false },
  { sprint: 5, title: "Content Studio", desc: "Create your first AI post", icon: PenLine, ready: false },
  { sprint: 9, title: "Analytics", desc: "Track your content performance", icon: BarChart2, ready: false },
];

export default function DashboardHome() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const hour = new Date().getHours();
  const greeting = hour < 12 ? "Good morning" : hour < 18 ? "Good afternoon" : "Good evening";

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

      {/* Stats row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: "Credits", value: user?.credits ?? 100, unit: "", color: "text-lime" },
          { label: "Posts Created", value: 0, unit: "", color: "text-white" },
          { label: "Platforms", value: user?.platforms_connected?.length ?? 0, unit: "of 3", color: "text-white" },
          { label: "Persona Score", value: "–", unit: "/10", color: "text-zinc-500" },
        ].map((stat, i) => (
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
        ))}
      </div>

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
        <h3 className="text-sm font-semibold text-zinc-400 uppercase tracking-wider mb-3">Platform Roadmap</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {upcomingFeatures.map((f, i) => (
            <motion.div
              key={f.title}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 + i * 0.05 }}
              className="card-thook p-4 flex items-start gap-3"
            >
              <div className="w-9 h-9 rounded-xl bg-white/5 flex items-center justify-center flex-shrink-0">
                <f.icon size={18} className="text-zinc-500" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <p className="text-sm font-medium text-white">{f.title}</p>
                  <span className="text-[10px] font-mono text-zinc-600 bg-white/5 px-1.5 py-0.5 rounded">S{f.sprint}</span>
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
