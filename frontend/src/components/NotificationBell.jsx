import { useState, useRef, useEffect } from "react";
import { Bell, Check, CheckCheck } from "lucide-react";
import useNotifications from "@/hooks/useNotifications";

const TYPE_ICONS = {
  post_published: "📤",
  job_completed: "✅",
  billing_event: "💳",
  workflow_status: "🎯",
  system: "🔔",
};

function timeAgo(dateString) {
  if (!dateString) return "";
  const now = new Date();
  const date = new Date(dateString);
  const seconds = Math.floor((now - date) / 1000);

  if (seconds < 60) return "just now";
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  return `${Math.floor(seconds / 86400)}d ago`;
}

export default function NotificationBell() {
  const [open, setOpen] = useState(false);
  const dropdownRef = useRef(null);
  const { notifications, unreadCount, markRead, markAllRead, loading } =
    useNotifications();

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setOpen(false);
      }
    }
    if (open) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [open]);

  const handleNotificationClick = async (notif) => {
    if (!notif.read) {
      await markRead(notif.notification_id);
    }
  };

  const displayNotifications = notifications.slice(0, 10);

  return (
    <div className="relative" ref={dropdownRef}>
      {/* Bell button */}
      <button
        data-testid="notifications-btn"
        onClick={() => setOpen((prev) => !prev)}
        className="w-9 h-9 flex items-center justify-center rounded-lg hover:bg-white/5 text-zinc-500 hover:text-white transition-colors relative"
      >
        <Bell size={16} />
        {unreadCount > 0 && (
          <span className="absolute -top-0.5 -right-0.5 min-w-[18px] h-[18px] flex items-center justify-center rounded-full bg-red-500 text-white text-[10px] font-bold px-1 leading-none">
            {unreadCount > 99 ? "99+" : unreadCount}
          </span>
        )}
      </button>

      {/* Dropdown */}
      {open && (
        <div className="absolute right-0 top-full mt-2 w-80 max-h-[420px] rounded-xl border border-white/10 bg-[#0a0a0a] shadow-2xl z-50 overflow-hidden flex flex-col">
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-white/5">
            <h3 className="text-sm font-semibold text-white">Notifications</h3>
            {unreadCount > 0 && (
              <button
                onClick={markAllRead}
                className="flex items-center gap-1 text-xs text-zinc-400 hover:text-lime transition-colors"
              >
                <CheckCheck size={12} />
                Mark all read
              </button>
            )}
          </div>

          {/* Notification list */}
          <div className="overflow-y-auto flex-1">
            {loading ? (
              <div className="flex items-center justify-center py-8">
                <div className="w-5 h-5 border-2 border-lime border-t-transparent rounded-full animate-spin" />
              </div>
            ) : displayNotifications.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-8 text-zinc-500">
                <Bell size={24} className="mb-2 opacity-40" />
                <span className="text-sm">No notifications yet</span>
              </div>
            ) : (
              displayNotifications.map((notif) => (
                <button
                  key={notif.notification_id}
                  onClick={() => handleNotificationClick(notif)}
                  className={`w-full text-left px-4 py-3 border-b border-white/5 last:border-b-0 hover:bg-white/5 transition-colors ${
                    !notif.read ? "bg-white/[0.02]" : ""
                  }`}
                >
                  <div className="flex items-start gap-3">
                    {/* Type icon */}
                    <span className="text-base mt-0.5 shrink-0">
                      {TYPE_ICONS[notif.type] || TYPE_ICONS.system}
                    </span>

                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span
                          className={`text-sm font-medium truncate ${
                            notif.read ? "text-zinc-400" : "text-white"
                          }`}
                        >
                          {notif.title}
                        </span>
                        {!notif.read && (
                          <span className="w-1.5 h-1.5 rounded-full bg-lime shrink-0" />
                        )}
                      </div>
                      <p className="text-xs text-zinc-500 mt-0.5 line-clamp-2">
                        {notif.body}
                      </p>
                      <span className="text-[10px] text-zinc-600 mt-1 block">
                        {timeAgo(notif.created_at)}
                      </span>
                    </div>

                    {/* Read indicator */}
                    {notif.read && (
                      <Check size={12} className="text-zinc-600 mt-1 shrink-0" />
                    )}
                  </div>
                </button>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}
