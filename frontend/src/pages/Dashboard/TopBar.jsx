import { Plus, Search, Menu } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { useNavigate } from "react-router-dom";
import NotificationBell from "@/components/NotificationBell";

export default function TopBar({ title = "Dashboard", onMenuClick }) {
  const { user } = useAuth();
  const navigate = useNavigate();

  return (
    <header className="h-16 bg-[#050505]/80 backdrop-blur-md border-b border-white/5 sticky top-0 z-40 flex items-center justify-between px-6" data-testid="topbar">
      <div className="flex items-center gap-4">
        {onMenuClick && (
          <button
            onClick={onMenuClick}
            data-testid="mobile-menu-btn"
            className="md:hidden w-9 h-9 flex items-center justify-center rounded-lg hover:bg-white/5 text-zinc-400 hover:text-white transition-colors"
          >
            <Menu size={20} />
          </button>
        )}
        <h1 className="font-display font-semibold text-lg text-white">{title}</h1>
      </div>

      <div className="flex items-center gap-3">
        {/* Search */}
        <button data-testid="search-btn" className="w-9 h-9 flex items-center justify-center rounded-lg hover:bg-white/5 text-zinc-500 hover:text-white transition-colors">
          <Search size={16} />
        </button>

        {/* Notifications */}
        <NotificationBell />

        {/* Create button */}
        <button
          onClick={() => navigate("/dashboard/studio")}
          data-testid="create-content-btn"
          className="flex items-center gap-2 btn-primary text-sm py-2 px-4"
        >
          <Plus size={15} />
          Create
        </button>
      </div>
    </header>
  );
}
