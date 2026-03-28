import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Users, Activity, FileText, AlertTriangle, TrendingUp,
  ShieldCheck, RefreshCw
} from "lucide-react";

const BACKEND_URL =
  import.meta.env.REACT_APP_BACKEND_URL || process.env.REACT_APP_BACKEND_URL;

function StatCard({ title, value, icon: Icon, subtitle, color = "text-lime" }) {
  return (
    <Card className="bg-surface-2 border-white/5">
      <CardContent className="p-5">
        <div className="flex items-start justify-between">
          <div>
            <p className="text-xs text-zinc-500 uppercase tracking-wider mb-1">{title}</p>
            <p className={`text-2xl font-bold font-mono ${color}`}>
              {value !== null && value !== undefined ? value.toLocaleString() : "--"}
            </p>
            {subtitle && <p className="text-xs text-zinc-500 mt-1">{subtitle}</p>}
          </div>
          <div className="w-10 h-10 rounded-xl bg-white/5 flex items-center justify-center">
            <Icon size={20} className="text-zinc-400" />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

export default function Admin() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [stats, setStats] = useState(null);
  const [errors, setErrors] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (user?.role !== "admin") {
      navigate("/dashboard", { replace: true });
      return;
    }
    fetchData();
  }, [user, navigate]);

  const fetchData = async () => {
    setLoading(true);
    const token = localStorage.getItem("thook_token");
    const headers = { Authorization: `Bearer ${token}` };

    try {
      const [statsRes, errorsRes] = await Promise.all([
        fetch(`${BACKEND_URL}/api/admin/stats/overview`, { headers }),
        fetch(`${BACKEND_URL}/api/admin/stats/errors`, { headers }),
      ]);

      if (statsRes.ok) setStats(await statsRes.json());
      if (errorsRes.ok) {
        const data = await errorsRes.json();
        setErrors(data.errors || []);
      }
    } catch (err) {
      console.error("Failed to fetch admin data:", err);
    } finally {
      setLoading(false);
    }
  };

  if (user?.role !== "admin") return null;

  const tiers = stats?.subscription_breakdown || {};

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white flex items-center gap-2">
            <ShieldCheck size={22} className="text-lime" />
            Admin Dashboard
          </h1>
          <p className="text-sm text-zinc-500 mt-1">Platform overview and management</p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate("/dashboard/admin/users")}
            className="btn-thook-secondary text-sm px-4 py-2"
          >
            <Users size={14} className="mr-1.5 inline" />
            Manage Users
          </button>
          <button
            onClick={fetchData}
            disabled={loading}
            className="btn-thook-ghost text-sm px-3 py-2"
          >
            <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
          </button>
        </div>
      </div>

      {/* Stats cards */}
      {loading && !stats ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <Card key={i} className="bg-surface-2 border-white/5 animate-pulse">
              <CardContent className="p-5">
                <div className="h-3 w-16 bg-zinc-800 rounded mb-3" />
                <div className="h-8 w-20 bg-zinc-800 rounded" />
              </CardContent>
            </Card>
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard
            title="Total Users"
            value={stats?.total_users}
            icon={Users}
            subtitle={`+${stats?.new_users_today || 0} today`}
          />
          <StatCard
            title="Active Today"
            value={stats?.active_users_today}
            icon={Activity}
            subtitle={`${stats?.new_users_7d || 0} new this week`}
            color="text-violet"
          />
          <StatCard
            title="Content Jobs Today"
            value={stats?.content_jobs_today}
            icon={FileText}
            subtitle={`${stats?.total_content_jobs?.toLocaleString() || 0} total`}
            color="text-blue-400"
          />
          <StatCard
            title="New Users (7d)"
            value={stats?.new_users_7d}
            icon={TrendingUp}
            subtitle={`+${stats?.new_users_today || 0} today`}
            color="text-emerald-400"
          />
        </div>
      )}

      {/* Subscription breakdown + Recent errors */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Subscription breakdown */}
        <Card className="bg-surface-2 border-white/5">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-zinc-300">
              Subscription Breakdown
            </CardTitle>
          </CardHeader>
          <CardContent>
            {stats ? (
              <div className="space-y-3">
                {Object.entries(tiers).map(([tierName, count]) => {
                  const total = stats.total_users || 1;
                  const pct = Math.round((count / total) * 100);
                  const colors = {
                    free: "bg-zinc-500",
                    pro: "bg-violet",
                    studio: "bg-blue-500",
                    agency: "bg-lime",
                  };
                  return (
                    <div key={tierName}>
                      <div className="flex items-center justify-between text-sm mb-1">
                        <span className="text-zinc-300 capitalize">{tierName}</span>
                        <span className="text-zinc-500 font-mono">
                          {count} <span className="text-zinc-600">({pct}%)</span>
                        </span>
                      </div>
                      <div className="w-full bg-white/5 rounded-full h-2">
                        <div
                          className={`h-2 rounded-full transition-all ${colors[tierName] || "bg-zinc-500"}`}
                          style={{ width: `${pct}%` }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="h-32 flex items-center justify-center text-zinc-600 text-sm">
                Loading...
              </div>
            )}
          </CardContent>
        </Card>

        {/* Recent errors */}
        <Card className="bg-surface-2 border-white/5">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-zinc-300 flex items-center gap-2">
              <AlertTriangle size={14} className="text-red-400" />
              Recent Errors
            </CardTitle>
          </CardHeader>
          <CardContent>
            {errors.length === 0 ? (
              <div className="h-32 flex items-center justify-center text-zinc-600 text-sm">
                No recent errors
              </div>
            ) : (
              <div className="space-y-2 max-h-80 overflow-y-auto">
                {errors.slice(0, 10).map((err) => (
                  <div
                    key={err.job_id}
                    className="p-3 rounded-lg bg-white/[0.02] border border-white/5 text-sm"
                  >
                    <div className="flex items-center justify-between mb-1">
                      <div className="flex items-center gap-2">
                        <Badge variant="destructive" className="text-[10px] px-1.5 py-0">
                          {err.status}
                        </Badge>
                        <span className="text-zinc-400 capitalize">{err.platform}</span>
                      </div>
                      <span className="text-[11px] text-zinc-600 font-mono">
                        {err.created_at
                          ? new Date(err.created_at).toLocaleDateString()
                          : ""}
                      </span>
                    </div>
                    <p className="text-xs text-zinc-500 truncate">
                      {err.error || "No error message"}
                    </p>
                    <p className="text-[10px] text-zinc-700 font-mono mt-1">
                      User: {err.user_id?.slice(0, 12)}...
                    </p>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
