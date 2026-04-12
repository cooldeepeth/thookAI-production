import { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Users, Search, ChevronLeft, ChevronRight, ShieldCheck,
  ArrowLeft, CreditCard, Ban, CheckCircle2, RefreshCw
} from "lucide-react";
import { apiFetch } from '@/lib/api';

const TIER_COLORS = {
  free: "bg-zinc-700 text-zinc-300",
  pro: "bg-violet/20 text-violet",
  studio: "bg-blue-500/20 text-blue-400",
  agency: "bg-lime/20 text-lime",
};

export default function AdminUsers() {
  const { user } = useAuth();
  const navigate = useNavigate();

  const [users, setUsers] = useState([]);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);
  const [search, setSearch] = useState("");
  const [tierFilter, setTierFilter] = useState("");
  const [loading, setLoading] = useState(true);

  // Modal states
  const [creditsModal, setCreditsModal] = useState(null);
  const [creditsAmount, setCreditsAmount] = useState("");
  const [creditsReason, setCreditsReason] = useState("");
  const [tierModal, setTierModal] = useState(null);
  const [newTier, setNewTier] = useState("");
  const [actionLoading, setActionLoading] = useState(false);

  const fetchUsers = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({ page: String(page) });
      if (search) params.set("search", search);
      if (tierFilter) params.set("tier", tierFilter);

      const res = await apiFetch(`/api/admin/users?${params.toString()}`);
      if (res.ok) {
        const data = await res.json();
        setUsers(data.users || []);
        setTotalPages(data.total_pages || 1);
        setTotal(data.total || 0);
      }
    } catch (err) {
      console.error("Failed to fetch users:", err);
    } finally {
      setLoading(false);
    }
  }, [page, search, tierFilter]);

  useEffect(() => {
    if (user?.role !== "admin") {
      navigate("/dashboard", { replace: true });
      return;
    }
    fetchUsers();
  }, [user, navigate, fetchUsers]);

  // Debounced search
  useEffect(() => {
    const timer = setTimeout(() => {
      setPage(1);
    }, 300);
    return () => clearTimeout(timer);
  }, [search, tierFilter]);

  const handleGrantCredits = async () => {
    if (!creditsModal || !creditsAmount || !creditsReason) return;
    setActionLoading(true);
    try {
      const res = await apiFetch(
        `/api/admin/users/${creditsModal.user_id}/credits`,
        {
          method: "POST",
          body: JSON.stringify({
            credits: parseInt(creditsAmount, 10),
            reason: creditsReason,
          }),
        }
      );
      if (res.ok) {
        setCreditsModal(null);
        setCreditsAmount("");
        setCreditsReason("");
        fetchUsers();
      }
    } catch (err) {
      console.error("Failed to grant credits:", err);
    } finally {
      setActionLoading(false);
    }
  };

  const handleChangeTier = async () => {
    if (!tierModal || !newTier) return;
    setActionLoading(true);
    try {
      const res = await apiFetch(
        `/api/admin/users/${tierModal.user_id}/tier`,
        {
          method: "POST",
          body: JSON.stringify({ tier: newTier }),
        }
      );
      if (res.ok) {
        setTierModal(null);
        setNewTier("");
        fetchUsers();
      }
    } catch (err) {
      console.error("Failed to change tier:", err);
    } finally {
      setActionLoading(false);
    }
  };

  const handleToggleSuspend = async (u) => {
    const endpoint = u.active === false ? "unsuspend" : "suspend";
    try {
      const res = await apiFetch(
        `/api/admin/users/${u.user_id}/${endpoint}`,
        { method: "POST" }
      );
      if (res.ok) fetchUsers();
    } catch (err) {
      console.error(`Failed to ${endpoint} user:`, err);
    }
  };

  if (user?.role !== "admin") return null;

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate("/dashboard/admin")}
            className="btn-thook-ghost p-2"
          >
            <ArrowLeft size={16} />
          </button>
          <div>
            <h1 className="text-xl font-bold text-white flex items-center gap-2">
              <Users size={22} className="text-lime" />
              User Management
            </h1>
            <p className="text-sm text-zinc-500 mt-0.5">
              {total} total user{total !== 1 ? "s" : ""}
            </p>
          </div>
        </div>
        <button
          onClick={fetchUsers}
          disabled={loading}
          className="btn-thook-ghost text-sm px-3 py-2"
        >
          <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
        </button>
      </div>

      {/* Search and filters */}
      <div className="flex items-center gap-3">
        <div className="relative flex-1 max-w-sm">
          <Search
            size={14}
            className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500"
          />
          <Input
            placeholder="Search by email or name..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9 bg-surface-2 border-white/10 text-sm"
          />
        </div>
        <Select value={tierFilter} onValueChange={(v) => { setTierFilter(v === "all" ? "" : v); setPage(1); }}>
          <SelectTrigger className="w-36 bg-surface-2 border-white/10 text-sm">
            <SelectValue placeholder="All tiers" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All tiers</SelectItem>
            <SelectItem value="free">Free</SelectItem>
            <SelectItem value="pro">Pro</SelectItem>
            <SelectItem value="studio">Studio</SelectItem>
            <SelectItem value="agency">Agency</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Users table */}
      <Card className="bg-surface-2 border-white/5 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-white/5 text-zinc-500 text-xs uppercase tracking-wider">
                <th className="text-left p-3 pl-4">User</th>
                <th className="text-left p-3">Tier</th>
                <th className="text-right p-3">Credits</th>
                <th className="text-right p-3">Jobs</th>
                <th className="text-left p-3">Joined</th>
                <th className="text-left p-3">Status</th>
                <th className="text-right p-3 pr-4">Actions</th>
              </tr>
            </thead>
            <tbody>
              {loading && users.length === 0 ? (
                Array.from({ length: 5 }).map((_, i) => (
                  <tr key={i} className="border-b border-white/5 animate-pulse">
                    <td className="p-3 pl-4"><div className="h-4 w-40 bg-zinc-800 rounded" /></td>
                    <td className="p-3"><div className="h-4 w-12 bg-zinc-800 rounded" /></td>
                    <td className="p-3"><div className="h-4 w-10 bg-zinc-800 rounded ml-auto" /></td>
                    <td className="p-3"><div className="h-4 w-8 bg-zinc-800 rounded ml-auto" /></td>
                    <td className="p-3"><div className="h-4 w-20 bg-zinc-800 rounded" /></td>
                    <td className="p-3"><div className="h-4 w-16 bg-zinc-800 rounded" /></td>
                    <td className="p-3 pr-4"><div className="h-4 w-24 bg-zinc-800 rounded ml-auto" /></td>
                  </tr>
                ))
              ) : users.length === 0 ? (
                <tr>
                  <td colSpan={7} className="text-center py-12 text-zinc-600">
                    No users found
                  </td>
                </tr>
              ) : (
                users.map((u) => (
                  <tr
                    key={u.user_id}
                    className="border-b border-white/5 hover:bg-white/[0.02] transition-colors"
                  >
                    <td className="p-3 pl-4">
                      <div>
                        <p className="text-zinc-200 font-medium text-sm">
                          {u.name || "Unnamed"}
                          {u.role === "admin" && (
                            <ShieldCheck
                              size={12}
                              className="inline ml-1.5 text-lime"
                            />
                          )}
                        </p>
                        <p className="text-xs text-zinc-500">{u.email}</p>
                      </div>
                    </td>
                    <td className="p-3">
                      <Badge
                        className={`text-[10px] capitalize ${
                          TIER_COLORS[u.subscription_tier] || TIER_COLORS.free
                        }`}
                      >
                        {u.subscription_tier || "free"}
                      </Badge>
                    </td>
                    <td className="p-3 text-right font-mono text-zinc-300">
                      {(u.credits ?? 0).toLocaleString()}
                    </td>
                    <td className="p-3 text-right font-mono text-zinc-400">
                      {u.jobs_count ?? 0}
                    </td>
                    <td className="p-3 text-xs text-zinc-500">
                      {u.created_at
                        ? new Date(u.created_at).toLocaleDateString()
                        : "--"}
                    </td>
                    <td className="p-3">
                      {u.active === false ? (
                        <Badge variant="destructive" className="text-[10px]">
                          Suspended
                        </Badge>
                      ) : (
                        <Badge className="text-[10px] bg-lime/15 text-lime">
                          Active
                        </Badge>
                      )}
                    </td>
                    <td className="p-3 pr-4">
                      <div className="flex items-center justify-end gap-1">
                        <button
                          onClick={() => {
                            setCreditsModal(u);
                            setCreditsAmount("");
                            setCreditsReason("");
                          }}
                          className="btn-thook-ghost text-[11px] px-2 py-1"
                          title="Grant Credits"
                        >
                          <CreditCard size={12} className="mr-1" />
                          Credits
                        </button>
                        <button
                          onClick={() => {
                            setTierModal(u);
                            setNewTier(u.subscription_tier || "free");
                          }}
                          className="btn-thook-ghost text-[11px] px-2 py-1"
                          title="Change Tier"
                        >
                          Tier
                        </button>
                        <button
                          onClick={() => handleToggleSuspend(u)}
                          className={`btn-thook-ghost text-[11px] px-2 py-1 ${
                            u.active === false
                              ? "text-lime hover:text-lime/80"
                              : "text-red-400 hover:text-red-300"
                          }`}
                          title={u.active === false ? "Unsuspend" : "Suspend"}
                        >
                          {u.active === false ? (
                            <CheckCircle2 size={12} />
                          ) : (
                            <Ban size={12} />
                          )}
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between p-3 border-t border-white/5">
            <p className="text-xs text-zinc-600">
              Page {page} of {totalPages}
            </p>
            <div className="flex items-center gap-1">
              <Button
                variant="ghost"
                size="sm"
                disabled={page <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                className="h-7 px-2 text-xs"
              >
                <ChevronLeft size={14} />
                Prev
              </Button>
              <Button
                variant="ghost"
                size="sm"
                disabled={page >= totalPages}
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                className="h-7 px-2 text-xs"
              >
                Next
                <ChevronRight size={14} />
              </Button>
            </div>
          </div>
        )}
      </Card>

      {/* Grant Credits Modal */}
      <Dialog open={!!creditsModal} onOpenChange={() => setCreditsModal(null)}>
        <DialogContent className="bg-[#111] border-white/10">
          <DialogHeader>
            <DialogTitle className="text-white">
              Grant Credits to {creditsModal?.name || creditsModal?.email}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-3 py-2">
            <div>
              <label className="text-xs text-zinc-400 mb-1 block">Amount</label>
              <Input
                type="number"
                placeholder="100"
                min={1}
                value={creditsAmount}
                onChange={(e) => setCreditsAmount(e.target.value)}
                className="bg-surface-2 border-white/10"
              />
            </div>
            <div>
              <label className="text-xs text-zinc-400 mb-1 block">Reason</label>
              <Input
                placeholder="e.g. Beta tester reward"
                value={creditsReason}
                onChange={(e) => setCreditsReason(e.target.value)}
                className="bg-surface-2 border-white/10"
              />
            </div>
          </div>
          <DialogFooter>
            <Button
              variant="ghost"
              onClick={() => setCreditsModal(null)}
              className="text-zinc-400"
            >
              Cancel
            </Button>
            <Button
              onClick={handleGrantCredits}
              disabled={
                actionLoading ||
                !creditsAmount ||
                parseInt(creditsAmount, 10) <= 0 ||
                !creditsReason
              }
              className="bg-lime text-black hover:bg-lime/90"
            >
              {actionLoading ? "Granting..." : "Grant Credits"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Change Tier Modal */}
      <Dialog open={!!tierModal} onOpenChange={() => setTierModal(null)}>
        <DialogContent className="bg-[#111] border-white/10">
          <DialogHeader>
            <DialogTitle className="text-white">
              Change Tier for {tierModal?.name || tierModal?.email}
            </DialogTitle>
          </DialogHeader>
          <div className="py-2">
            <label className="text-xs text-zinc-400 mb-1 block">
              New Tier
            </label>
            <Select value={newTier} onValueChange={setNewTier}>
              <SelectTrigger className="bg-surface-2 border-white/10">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="free">Free</SelectItem>
                <SelectItem value="pro">Pro</SelectItem>
                <SelectItem value="studio">Studio</SelectItem>
                <SelectItem value="agency">Agency</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <DialogFooter>
            <Button
              variant="ghost"
              onClick={() => setTierModal(null)}
              className="text-zinc-400"
            >
              Cancel
            </Button>
            <Button
              onClick={handleChangeTier}
              disabled={actionLoading || !newTier}
              className="bg-lime text-black hover:bg-lime/90"
            >
              {actionLoading ? "Updating..." : "Update Tier"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
