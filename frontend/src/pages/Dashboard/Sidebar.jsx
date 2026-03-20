import { NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import {
  LayoutDashboard, PenLine, Brain, Calendar, BarChart2,
  RefreshCw, Link2, BookOpen, Settings, Zap, LogOut, ChevronRight,
  Building2, LayoutTemplate
} from "lucide-react";

const navItems = [
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/dashboard/studio", label: "Content Studio", icon: PenLine },
  { to: "/dashboard/persona", label: "Persona Engine", icon: Brain },
  { to: "/dashboard/repurpose", label: "Repurpose Agent", icon: RefreshCw },
  { to: "/dashboard/calendar", label: "Content Calendar", icon: Calendar },
  { to: "/dashboard/analytics", label: "Analytics", icon: BarChart2 },
  { to: "/dashboard/library", label: "Content Library", icon: BookOpen },
  { to: "/dashboard/templates", label: "Templates", icon: LayoutTemplate, badge: "New" },
  { to: "/dashboard/connections", label: "Connections", icon: Link2 },
  { to: "/dashboard/agency", label: "Agency Workspace", icon: Building2, badge: "Pro" },
  { to: "/dashboard/settings", label: "Settings", icon: Settings },
];

export default function Sidebar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate("/", { replace: true });
  };

  return (
    <aside className="w-64 bg-[#050505] border-r border-white/5 flex flex-col h-screen fixed left-0 top-0 z-50" data-testid="sidebar">
      {/* Logo */}
      <div className="h-16 flex items-center px-5 border-b border-white/5">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 bg-lime rounded-lg flex items-center justify-center flex-shrink-0">
            <Zap size={16} className="text-black" fill="black" />
          </div>
          <span className="font-display font-bold text-lg text-white">Thook</span>
          <span className="text-[10px] font-mono text-lime bg-lime/10 px-1.5 py-0.5 rounded-md ml-1">AI</span>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4 overflow-y-auto space-y-0.5">
        {navItems.map(({ to, label, icon: Icon, end, badge }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            data-testid={`nav-${label.toLowerCase().replace(/\s+/g, '-')}`}
            className={({ isActive }) =>
              `sidebar-nav-item ${isActive ? "active" : ""}`
            }
          >
            <Icon size={17} />
            <span>{label}</span>
            {badge && (
              <span className={`ml-auto text-[10px] rounded-full px-1.5 py-0.5 ${
                badge === "Pro" 
                  ? "bg-violet/15 text-violet" 
                  : "bg-lime/15 text-lime"
              }`}>{badge}</span>
            )}
          </NavLink>
        ))}
      </nav>

      {/* Credits banner */}
      <div className="px-3 py-2">
        <div className="bg-surface-2 rounded-xl p-3 border border-white/5">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs text-zinc-400">Credits</span>
            <span className="text-xs font-mono text-lime">{user?.credits ?? 100}</span>
          </div>
          <div className="w-full bg-white/5 rounded-full h-1.5">
            <div
              className="bg-lime h-1.5 rounded-full transition-all"
              style={{ width: `${Math.min(100, ((user?.credits ?? 100) / 200) * 100)}%` }}
            />
          </div>
          <p className="text-[11px] text-zinc-600 mt-1.5">of 200 free credits</p>
        </div>
      </div>

      {/* User profile */}
      <div className="p-3 border-t border-white/5">
        <div className="flex items-center gap-3 p-2 rounded-xl hover:bg-white/5 transition-colors cursor-pointer group" data-testid="user-profile-area">
          <div className="w-8 h-8 rounded-full bg-violet/20 flex items-center justify-center flex-shrink-0 overflow-hidden">
            {user?.picture ? (
              <img src={user.picture} alt={user.name} className="w-full h-full object-cover" />
            ) : (
              <span className="text-xs font-bold text-violet">{user?.name?.[0]?.toUpperCase() || "U"}</span>
            )}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-white truncate">{user?.name || "Creator"}</p>
            <p className="text-xs text-zinc-500 truncate capitalize">{user?.plan || "free"} plan</p>
          </div>
          <button
            onClick={handleLogout}
            data-testid="logout-btn"
            className="opacity-0 group-hover:opacity-100 transition-opacity p-1 hover:text-red-400 text-zinc-600"
            title="Logout"
          >
            <LogOut size={14} />
          </button>
        </div>
      </div>
    </aside>
  );
}
