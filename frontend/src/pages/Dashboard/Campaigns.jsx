import { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import {
  FolderOpen, Plus, Loader2, Search, X, ArrowLeft,
  FileText, Calendar, Target, BarChart2, Trash2
} from "lucide-react";
import CampaignCard from "@/components/CampaignCard";
import {
  getCampaigns,
  createCampaign,
  getCampaign,
  updateCampaign,
  deleteCampaign,
  getCampaignStats,
  removeContentFromCampaign,
} from "@/lib/campaignsApi";

const PLATFORM_OPTIONS = [
  { value: "", label: "All Platforms" },
  { value: "linkedin", label: "💼 LinkedIn" },
  { value: "x", label: "𝕏 X" },
  { value: "instagram", label: "📸 Instagram" },
];

const STATUS_FILTER_OPTIONS = [
  { value: "", label: "Active" },
  { value: "paused", label: "Paused" },
  { value: "completed", label: "Completed" },
  { value: "archived", label: "Archived" },
];

// ==================== Create Campaign Dialog ====================

function CreateCampaignDialog({ onClose, onCreated }) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [platform, setPlatform] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [goal, setGoal] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!name.trim()) return;
    setSubmitting(true);
    setError(null);
    try {
      const payload = {
        name: name.trim(),
        description: description.trim() || undefined,
        platform: platform || undefined,
        start_date: startDate || undefined,
        end_date: endDate || undefined,
        goal: goal.trim() || undefined,
      };
      const campaign = await createCampaign(payload);
      onCreated(campaign);
      onClose();
    } catch (err) {
      setError(err.message || "Failed to create campaign");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 bg-black/70 z-50 flex items-center justify-center p-4"
      onClick={onClose}
    >
      <motion.div
        initial={{ scale: 0.95, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        exit={{ scale: 0.95, opacity: 0 }}
        className="bg-[#0F0F0F] border border-white/10 rounded-2xl p-6 max-w-lg w-full max-h-[85vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-5">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-violet/10 rounded-xl flex items-center justify-center">
              <FolderOpen size={18} className="text-violet" />
            </div>
            <div>
              <h3 className="font-display font-bold text-white">New Campaign</h3>
              <p className="text-xs text-zinc-500">Group your content under a project</p>
            </div>
          </div>
          <button onClick={onClose} className="text-zinc-500 hover:text-white">
            <X size={20} />
          </button>
        </div>

        {error && (
          <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-3 mb-4 text-sm text-red-400">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="text-xs text-zinc-500 mb-1.5 block">Campaign Name *</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              maxLength={120}
              placeholder="e.g. Q1 Thought Leadership Series"
              className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-2.5 text-white placeholder-zinc-600 outline-none focus:border-lime/50"
            />
          </div>

          <div>
            <label className="text-xs text-zinc-500 mb-1.5 block">Description (optional)</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              maxLength={500}
              rows={3}
              placeholder="What is this campaign about?"
              className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-2.5 text-white placeholder-zinc-600 outline-none focus:border-lime/50 resize-none"
            />
          </div>

          <div>
            <label className="text-xs text-zinc-500 mb-1.5 block">Platform</label>
            <select
              value={platform}
              onChange={(e) => setPlatform(e.target.value)}
              className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-2.5 text-white outline-none focus:border-lime/50"
            >
              <option value="">Multi-platform</option>
              <option value="linkedin">LinkedIn</option>
              <option value="x">X (Twitter)</option>
              <option value="instagram">Instagram</option>
            </select>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-xs text-zinc-500 mb-1.5 block">Start Date</label>
              <input
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-2.5 text-white outline-none focus:border-lime/50"
              />
            </div>
            <div>
              <label className="text-xs text-zinc-500 mb-1.5 block">End Date</label>
              <input
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-2.5 text-white outline-none focus:border-lime/50"
              />
            </div>
          </div>

          <div>
            <label className="text-xs text-zinc-500 mb-1.5 block">Goal (optional)</label>
            <input
              type="text"
              value={goal}
              onChange={(e) => setGoal(e.target.value)}
              maxLength={300}
              placeholder="e.g. Grow LinkedIn followers by 20%"
              className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-2.5 text-white placeholder-zinc-600 outline-none focus:border-lime/50"
            />
          </div>

          <button
            type="submit"
            disabled={submitting || !name.trim()}
            className="w-full btn-primary py-3 flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {submitting ? (
              <Loader2 size={18} className="animate-spin" />
            ) : (
              <Plus size={18} />
            )}
            Create Campaign
          </button>
        </form>
      </motion.div>
    </motion.div>
  );
}

// ==================== Campaign Detail View ====================

function CampaignDetail({ campaignId, onBack }) {
  const navigate = useNavigate();
  const [campaign, setCampaign] = useState(null);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [removing, setRemoving] = useState(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [campData, statsData] = await Promise.all([
        getCampaign(campaignId),
        getCampaignStats(campaignId),
      ]);
      setCampaign(campData);
      setStats(statsData);
    } catch (err) {
      console.error("Failed to fetch campaign:", err);
    } finally {
      setLoading(false);
    }
  }, [campaignId]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleRemoveContent = async (jobId) => {
    if (removing) return;
    setRemoving(jobId);
    try {
      await removeContentFromCampaign(campaignId, jobId);
      fetchData();
    } catch (err) {
      console.error("Failed to remove content:", err);
    } finally {
      setRemoving(null);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-16">
        <Loader2 size={32} className="animate-spin text-zinc-500" />
      </div>
    );
  }

  if (!campaign) {
    return (
      <div className="text-center py-16">
        <p className="text-zinc-500">Campaign not found.</p>
      </div>
    );
  }

  const jobs = campaign.content_jobs || [];

  const STATUS_COLORS = {
    running: "bg-blue-500/15 text-blue-400",
    reviewing: "bg-yellow-500/15 text-yellow-400",
    approved: "bg-lime/15 text-lime",
    published: "bg-emerald-500/15 text-emerald-400",
    rejected: "bg-red-500/15 text-red-400",
    failed: "bg-red-500/15 text-red-400",
  };

  return (
    <div>
      {/* Back + header */}
      <button
        onClick={onBack}
        className="flex items-center gap-1.5 text-sm text-zinc-500 hover:text-white transition-colors mb-4"
      >
        <ArrowLeft size={16} /> Back to Campaigns
      </button>

      <div className="flex items-start justify-between mb-6">
        <div>
          <h2 className="font-display font-bold text-2xl text-white">{campaign.name}</h2>
          {campaign.description && (
            <p className="text-zinc-500 text-sm mt-1">{campaign.description}</p>
          )}
        </div>
        <button
          onClick={() => navigate("/dashboard/studio")}
          className="btn-primary flex items-center gap-2 text-sm"
        >
          <Plus size={16} /> Create Content
        </button>
      </div>

      {/* Stats cards */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          <div className="bg-white/5 border border-white/10 rounded-xl p-4">
            <p className="text-xs text-zinc-500 mb-1">Total Content</p>
            <p className="text-2xl font-bold text-white">{stats.total_content}</p>
          </div>
          <div className="bg-white/5 border border-white/10 rounded-xl p-4">
            <p className="text-xs text-zinc-500 mb-1">Approved</p>
            <p className="text-2xl font-bold text-lime">{stats.by_status?.approved || 0}</p>
          </div>
          <div className="bg-white/5 border border-white/10 rounded-xl p-4">
            <p className="text-xs text-zinc-500 mb-1">Published</p>
            <p className="text-2xl font-bold text-emerald-400">{stats.by_status?.published || 0}</p>
          </div>
          <div className="bg-white/5 border border-white/10 rounded-xl p-4">
            <p className="text-xs text-zinc-500 mb-1">Avg QC Score</p>
            <p className="text-2xl font-bold text-violet">
              {stats.average_qc_score !== null ? stats.average_qc_score : "--"}
            </p>
          </div>
        </div>
      )}

      {/* Content jobs table */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-semibold text-white">Campaign Content</h3>
        <span className="text-sm text-zinc-500">{jobs.length} item{jobs.length !== 1 ? "s" : ""}</span>
      </div>

      {jobs.length === 0 ? (
        <div className="text-center py-16 bg-white/5 border border-white/10 rounded-xl">
          <FileText size={48} className="text-zinc-700 mx-auto mb-4" />
          <h3 className="text-lg text-zinc-500 mb-2">No content yet</h3>
          <p className="text-sm text-zinc-600 mb-4">
            Create content in the Studio and link it to this campaign, or add existing content jobs.
          </p>
          <button
            onClick={() => navigate("/dashboard/studio")}
            className="btn-primary text-sm inline-flex items-center gap-2"
          >
            <Plus size={16} /> Go to Studio
          </button>
        </div>
      ) : (
        <div className="space-y-2">
          {jobs.map((job) => (
            <div
              key={job.job_id}
              className="flex items-center justify-between bg-white/5 border border-white/10 rounded-xl p-4 hover:border-white/20 transition-colors group"
            >
              <div className="flex items-center gap-3 flex-1 min-w-0">
                <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${STATUS_COLORS[job.status] || "bg-white/10 text-zinc-400"}`}>
                  {job.status}
                </span>
                <span className="text-xs text-zinc-500 uppercase">{job.platform}</span>
                <p className="text-sm text-white truncate">
                  {job.raw_input?.substring(0, 80) || job.job_id}
                </p>
              </div>
              <div className="flex items-center gap-2 ml-4 flex-shrink-0">
                <span className="text-xs text-zinc-600">
                  {job.created_at ? new Date(job.created_at).toLocaleDateString() : ""}
                </span>
                <button
                  onClick={() => handleRemoveContent(job.job_id)}
                  disabled={removing === job.job_id}
                  className="p-1.5 rounded-lg text-zinc-600 hover:text-red-400 hover:bg-red-500/10 opacity-0 group-hover:opacity-100 transition-all"
                  title="Remove from campaign"
                >
                  {removing === job.job_id ? (
                    <Loader2 size={14} className="animate-spin" />
                  ) : (
                    <Trash2 size={14} />
                  )}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ==================== Main Campaigns Page ====================

export default function Campaigns() {
  const [campaigns, setCampaigns] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [selectedCampaignId, setSelectedCampaignId] = useState(null);

  const fetchCampaigns = useCallback(async () => {
    setLoading(true);
    try {
      const filters = {};
      if (statusFilter) filters.status = statusFilter;
      const data = await getCampaigns(filters);
      setCampaigns(data.campaigns || []);
    } catch (err) {
      console.error("Failed to fetch campaigns:", err);
    } finally {
      setLoading(false);
    }
  }, [statusFilter]);

  useEffect(() => {
    if (!selectedCampaignId) {
      fetchCampaigns();
    }
  }, [fetchCampaigns, selectedCampaignId]);

  const handleStatusChange = async (campaignId, newStatus) => {
    try {
      await updateCampaign(campaignId, { status: newStatus });
      fetchCampaigns();
    } catch (err) {
      console.error("Failed to update status:", err);
    }
  };

  const handleArchive = async (campaignId) => {
    try {
      await deleteCampaign(campaignId);
      fetchCampaigns();
    } catch (err) {
      console.error("Failed to archive campaign:", err);
    }
  };

  const handleCreated = (newCampaign) => {
    setCampaigns((prev) => [newCampaign, ...prev]);
  };

  const filteredCampaigns = campaigns.filter(
    (c) =>
      !searchQuery ||
      c.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (c.description || "").toLowerCase().includes(searchQuery.toLowerCase())
  );

  // Detail view
  if (selectedCampaignId) {
    return (
      <main className="flex-1 p-6" data-testid="campaign-detail-page">
        <CampaignDetail
          campaignId={selectedCampaignId}
          onBack={() => setSelectedCampaignId(null)}
        />
      </main>
    );
  }

  // List view
  return (
    <main className="flex-1 p-6" data-testid="campaigns-page">
      <AnimatePresence>
        {showCreateDialog && (
          <CreateCampaignDialog
            onClose={() => setShowCreateDialog(false)}
            onCreated={handleCreated}
          />
        )}
      </AnimatePresence>

      {/* Header */}
      <div className="flex items-start justify-between mb-6">
        <div>
          <h2 className="font-display font-bold text-2xl text-white">Campaigns</h2>
          <p className="text-zinc-500 text-sm">
            Organise your content under campaigns and track progress
          </p>
        </div>
        <button
          onClick={() => setShowCreateDialog(true)}
          className="btn-primary flex items-center gap-2 text-sm"
        >
          <Plus size={16} />
          New Campaign
        </button>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-4 mb-6">
        <div className="flex-1 relative">
          <Search size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search campaigns..."
            className="w-full bg-white/5 border border-white/10 rounded-xl pl-10 pr-4 py-2.5 text-white placeholder-zinc-600 outline-none focus:border-lime/50"
          />
        </div>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="bg-white/5 border border-white/10 rounded-xl px-4 py-2.5 text-white outline-none focus:border-lime/50"
        >
          {STATUS_FILTER_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>{opt.label}</option>
          ))}
        </select>
      </div>

      {/* Campaign grid */}
      {loading ? (
        <div className="flex items-center justify-center py-16">
          <Loader2 size={32} className="animate-spin text-zinc-500" />
        </div>
      ) : filteredCampaigns.length === 0 ? (
        <div className="text-center py-16">
          <FolderOpen size={48} className="text-zinc-700 mx-auto mb-4" />
          <h3 className="text-lg text-zinc-500 mb-2">
            {campaigns.length === 0 ? "No campaigns yet" : "No campaigns match your search"}
          </h3>
          <p className="text-sm text-zinc-600 mb-4">
            {campaigns.length === 0
              ? "Create your first campaign to organise your content."
              : "Try a different search term or filter."}
          </p>
          {campaigns.length === 0 && (
            <button
              onClick={() => setShowCreateDialog(true)}
              className="btn-primary text-sm inline-flex items-center gap-2"
            >
              <Plus size={16} /> Create Campaign
            </button>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredCampaigns.map((campaign) => (
            <CampaignCard
              key={campaign.campaign_id}
              campaign={campaign}
              onClick={(c) => setSelectedCampaignId(c.campaign_id)}
              onStatusChange={handleStatusChange}
              onArchive={handleArchive}
            />
          ))}
        </div>
      )}
    </main>
  );
}
