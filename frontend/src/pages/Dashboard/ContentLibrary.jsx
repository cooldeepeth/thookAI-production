import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useToast } from "@/hooks/use-toast";
import {
  BookOpen, Linkedin, Twitter, Instagram, Filter, Search,
  RefreshCw, Eye, Clock, Check, X, Send, Trash2, MoreVertical,
  Layers, Plus, ChevronRight, Download, Copy, ClipboardCheck, ChevronDown
} from "lucide-react";
import { apiFetch } from '@/lib/api';

const PLATFORM_CONFIG = {
  linkedin: { name: "LinkedIn", icon: Linkedin, color: "bg-blue-600" },
  x: { name: "X", icon: Twitter, color: "bg-zinc-700" },
  instagram: { name: "Instagram", icon: Instagram, color: "bg-gradient-to-r from-pink-500 to-orange-400" }
};

const STATUS_CONFIG = {
  draft: { label: "Draft", color: "bg-zinc-500/20 text-zinc-400" },
  processing: { label: "Processing", color: "bg-yellow-500/20 text-yellow-400" },
  reviewing: { label: "Ready for Review", color: "bg-blue-500/20 text-blue-400" },
  completed: { label: "Ready for Review", color: "bg-blue-500/20 text-blue-400" },
  approved: { label: "Approved", color: "bg-lime/20 text-lime" },
  scheduled: { label: "Scheduled", color: "bg-violet/20 text-violet" },
  published: { label: "Published", color: "bg-green-500/20 text-green-400" },
  rejected: { label: "Rejected", color: "bg-red-500/20 text-red-400" }
};

export default function ContentLibrary() {
  const [contents, setContents] = useState([]);
  const [series, setSeries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState("all"); // all, series
  const [filterStatus, setFilterStatus] = useState("all");
  const [filterPlatform, setFilterPlatform] = useState("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [showExportMenu, setShowExportMenu] = useState(false);
  const [exportFromDate, setExportFromDate] = useState("");
  const [exportToDate, setExportToDate] = useState("");
  const [copiedJobId, setCopiedJobId] = useState(null);
  const { toast } = useToast();
  const navigate = useNavigate();

  useEffect(() => {
    fetchContent();
    fetchSeries();
  }, []);

  const fetchContent = async () => {
    try {
      const res = await apiFetch('/api/content/jobs');

      if (!res.ok) throw new Error("Failed to fetch content");
      const data = await res.json();
      setContents(data.jobs || []);
    } catch (err) {
      console.error("Error:", err);
    } finally {
      setLoading(false);
    }
  };

  const fetchSeries = async () => {
    try {
      const res = await apiFetch('/api/content/series');

      if (!res.ok) return;
      const data = await res.json();
      setSeries(data.series || []);
    } catch (err) {
      console.error("Series fetch error:", err);
    }
  };

  const filteredContents = contents.filter(item => {
    if (filterStatus !== "all" && item.status !== filterStatus) return false;
    if (filterPlatform !== "all" && item.platform !== filterPlatform) return false;
    if (searchQuery) {
      const search = searchQuery.toLowerCase();
      return (
        item.final_content?.toLowerCase().includes(search) ||
        item.raw_input?.toLowerCase().includes(search)
      );
    }
    return true;
  });

  const handleBulkExport = async (format) => {
    setShowExportMenu(false);
    try {
      const params = new URLSearchParams({ format });
      if (filterPlatform !== "all") params.set("platform", filterPlatform);
      if (filterStatus !== "all") params.set("status", filterStatus);
      if (exportFromDate) params.set("from_date", exportFromDate);
      if (exportToDate) params.set("to_date", exportToDate);

      const res = await apiFetch(`/api/content/export/bulk?${params.toString()}`);

      if (!res.ok) throw new Error("Export failed");

      const blob = await res.blob();
      const ext = format === "csv" ? "csv" : "txt";
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `thookai-export.${ext}`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);

      toast({ title: "Export complete", description: `Content exported as ${format.toUpperCase()}` });
    } catch (err) {
      console.error("Export error:", err);
      toast({ title: "Export failed", description: "Could not export content. Please try again.", variant: "destructive" });
    }
  };

  const handleCopyContent = async (item) => {
    const text = typeof item.final_content === "object"
      ? item.final_content?.post || ""
      : item.final_content || item.raw_input || "";
    if (!text) return;
    try {
      await navigator.clipboard.writeText(text);
      setCopiedJobId(item.job_id);
      setTimeout(() => setCopiedJobId(null), 2000);
    } catch (err) {
      console.error("Copy failed:", err);
    }
  };

  if (loading) {
    return (
      <main className="p-6">
        <div className="max-w-6xl mx-auto">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {[1, 2, 3, 4, 5, 6].map((i) => (
              <div key={i} className="h-48 bg-surface-2 rounded-2xl animate-pulse" />
            ))}
          </div>
        </div>
      </main>
    );
  }

  return (
    <main className="p-6">
      <div className="max-w-6xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-display font-bold text-white flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-lime/10 flex items-center justify-center">
                <BookOpen className="text-lime" size={20} />
              </div>
              Content Library
            </h1>
            <p className="text-zinc-400 mt-1">All your drafts, scheduled, and published content</p>
          </div>
          <div className="flex gap-3">
            <Button variant="outline" onClick={() => { fetchContent(); fetchSeries(); }} className="gap-2">
              <RefreshCw size={14} />
              Refresh
            </Button>

            {/* Export date range + dropdown */}
            <div className="flex items-center gap-2">
              <input
                type="date"
                value={exportFromDate}
                onChange={(e) => setExportFromDate(e.target.value)}
                className="px-2 py-1.5 bg-surface-2 border border-white/5 rounded-lg text-xs text-white focus:outline-none focus:border-white/10 w-[130px]"
                title="Export from date"
              />
              <span className="text-zinc-500 text-xs">to</span>
              <input
                type="date"
                value={exportToDate}
                onChange={(e) => setExportToDate(e.target.value)}
                className="px-2 py-1.5 bg-surface-2 border border-white/5 rounded-lg text-xs text-white focus:outline-none focus:border-white/10 w-[130px]"
                title="Export to date"
              />
            </div>
            <div className="relative">
              <Button
                variant="outline"
                onClick={() => setShowExportMenu(!showExportMenu)}
                className="gap-2"
                disabled={contents.length === 0}
              >
                <Download size={14} />
                Export
                <ChevronDown size={12} />
              </Button>
              {showExportMenu && (
                <>
                  <div className="fixed inset-0 z-40" onClick={() => setShowExportMenu(false)} />
                  <div className="absolute right-0 top-full mt-1 z-50 bg-zinc-900 border border-white/10 rounded-lg shadow-xl py-1 min-w-[160px]">
                    <button
                      onClick={() => handleBulkExport("csv")}
                      className="w-full px-4 py-2 text-left text-sm text-zinc-300 hover:bg-white/5 transition-colors flex items-center gap-2"
                    >
                      <Download size={13} />
                      Export as CSV
                    </button>
                    <button
                      onClick={() => handleBulkExport("text")}
                      className="w-full px-4 py-2 text-left text-sm text-zinc-300 hover:bg-white/5 transition-colors flex items-center gap-2"
                    >
                      <Download size={13} />
                      Export as Text
                    </button>
                  </div>
                </>
              )}
            </div>

            <Button onClick={() => navigate("/dashboard/studio")} className="bg-lime text-black hover:bg-lime/90 gap-2">
              <Plus size={14} />
              Create
            </Button>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex gap-4 border-b border-white/5 pb-4">
          <button
            onClick={() => setActiveTab("all")}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              activeTab === "all" ? "bg-white/10 text-white" : "text-zinc-400 hover:text-white"
            }`}
          >
            All Content ({contents.length})
          </button>
          <button
            onClick={() => setActiveTab("series")}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors flex items-center gap-2 ${
              activeTab === "series" ? "bg-white/10 text-white" : "text-zinc-400 hover:text-white"
            }`}
          >
            <Layers size={14} />
            Content Series ({series.length})
          </button>
        </div>

        {activeTab === "all" ? (
          <>
            {/* Filters */}
            <div className="flex flex-wrap gap-4">
              {/* Search */}
              <div className="relative flex-1 min-w-[200px]">
                <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500" />
                <input
                  type="text"
                  placeholder="Search content..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-9 pr-4 py-2 bg-surface-2 border border-white/5 rounded-lg text-sm text-white placeholder:text-zinc-600 focus:outline-none focus:border-white/10"
                />
              </div>

              {/* Status filter */}
              <select
                value={filterStatus}
                onChange={(e) => setFilterStatus(e.target.value)}
                className="px-4 py-2 bg-surface-2 border border-white/5 rounded-lg text-sm text-white focus:outline-none"
              >
                <option value="all">All Status</option>
                {Object.entries(STATUS_CONFIG).map(([key, config]) => (
                  <option key={key} value={key}>{config.label}</option>
                ))}
              </select>

              {/* Platform filter */}
              <select
                value={filterPlatform}
                onChange={(e) => setFilterPlatform(e.target.value)}
                className="px-4 py-2 bg-surface-2 border border-white/5 rounded-lg text-sm text-white focus:outline-none"
              >
                <option value="all">All Platforms</option>
                {Object.entries(PLATFORM_CONFIG).map(([key, config]) => (
                  <option key={key} value={key}>{config.name}</option>
                ))}
              </select>
            </div>

            {/* Content Grid */}
            {filteredContents.length === 0 ? (
              <Card className="bg-surface-2 border-white/5">
                <CardContent className="py-16 text-center">
                  <BookOpen className="mx-auto text-zinc-600 mb-4" size={48} />
                  {contents.length === 0 ? (
                    <>
                      <h3 className="text-lg font-medium text-white mb-2">No content yet</h3>
                      <p className="text-zinc-400 mb-6">Create your first post!</p>
                      <Button onClick={() => navigate("/dashboard/studio")} className="bg-lime text-black hover:bg-lime/90 px-6 py-2 font-medium rounded-lg">
                        Create Your First Content
                      </Button>
                    </>
                  ) : (
                    <>
                      <h3 className="text-lg font-medium text-white mb-2">No results</h3>
                      <p className="text-zinc-400">No content matches your filters. Try adjusting your search or filters.</p>
                    </>
                  )}
                </CardContent>
              </Card>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {filteredContents.map((item, i) => {
                  const platformConfig = PLATFORM_CONFIG[item.platform] || PLATFORM_CONFIG.linkedin;
                  const statusConfig = STATUS_CONFIG[item.status] || STATUS_CONFIG.draft;
                  const PlatformIcon = platformConfig.icon;
                  
                  return (
                    <motion.div
                      key={item.job_id}
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: i * 0.05 }}
                    >
                      <Card className="bg-surface-2 border-white/5 hover:border-white/10 transition-colors h-full flex flex-col">
                        <CardContent className="py-4 flex flex-col h-full">
                          {/* Header */}
                          <div className="flex items-center justify-between mb-3">
                            <div className="flex items-center gap-2">
                              <div className={`w-8 h-8 rounded-lg ${platformConfig.color} flex items-center justify-center`}>
                                <PlatformIcon size={14} className="text-white" />
                              </div>
                              <Badge className={`${statusConfig.color} border-0`}>
                                {statusConfig.label}
                              </Badge>
                            </div>
                            {item.is_repurposed && (
                              <Badge variant="outline" className="text-xs text-violet border-violet/30">
                                <RefreshCw size={10} className="mr-1" />
                                Repurposed
                              </Badge>
                            )}
                          </div>

                          {/* Content Preview */}
                          <p className="text-sm text-zinc-300 line-clamp-4 flex-1 mb-3">
                            {item.final_content || item.raw_input || "No content"}
                          </p>

                          {/* Footer */}
                          <div className="flex items-center justify-between pt-3 border-t border-white/5">
                            <span className="text-xs text-zinc-600">
                              {item.created_at ? new Date(item.created_at).toLocaleDateString() : ""}
                            </span>
                            <div className="flex gap-1">
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => handleCopyContent(item)}
                                className="h-7 px-2 text-zinc-400 hover:text-white"
                                title={copiedJobId === item.job_id ? "Copied!" : "Copy content"}
                              >
                                {copiedJobId === item.job_id ? (
                                  <ClipboardCheck size={14} className="text-lime" />
                                ) : (
                                  <Copy size={14} />
                                )}
                              </Button>
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => navigate(`/dashboard/studio?job=${item.job_id}`)}
                                className="h-7 px-2 text-zinc-400 hover:text-white"
                              >
                                <Eye size={14} />
                              </Button>
                              {item.status === "approved" && (
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  onClick={() => navigate(`/dashboard/repurpose?job=${item.job_id}`)}
                                  className="h-7 px-2 text-violet hover:text-violet"
                                >
                                  <RefreshCw size={14} />
                                </Button>
                              )}
                            </div>
                          </div>
                        </CardContent>
                      </Card>
                    </motion.div>
                  );
                })}
              </div>
            )}
          </>
        ) : (
          /* Series Tab */
          <div className="space-y-4">
            {series.length === 0 ? (
              <Card className="bg-surface-2 border-white/5">
                <CardContent className="py-12 text-center">
                  <Layers className="mx-auto text-zinc-600 mb-3" size={40} />
                  <p className="text-zinc-400 mb-4">No content series yet</p>
                  <Button 
                    onClick={() => navigate("/dashboard/studio")} 
                    className="bg-violet text-white hover:bg-violet/90"
                  >
                    Create a Series
                  </Button>
                </CardContent>
              </Card>
            ) : (
              series.map((item, i) => {
                const platformConfig = PLATFORM_CONFIG[item.platform] || PLATFORM_CONFIG.linkedin;
                const PlatformIcon = platformConfig.icon;
                const progress = item.progress || 0;
                
                return (
                  <motion.div
                    key={item.series_id}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: i * 0.1 }}
                  >
                    <Card className="bg-surface-2 border-white/5 hover:border-white/10 transition-colors">
                      <CardContent className="py-4">
                        <div className="flex items-center gap-4">
                          <div className={`w-12 h-12 rounded-xl ${platformConfig.color} flex items-center justify-center`}>
                            <PlatformIcon size={20} className="text-white" />
                          </div>
                          
                          <div className="flex-1">
                            <div className="flex items-center gap-2 mb-1">
                              <h3 className="text-white font-medium">{item.title}</h3>
                              <Badge className={item.status === "completed" ? "bg-green-500/20 text-green-400" : "bg-lime/20 text-lime"}>
                                {item.status}
                              </Badge>
                            </div>
                            <p className="text-xs text-zinc-500 mb-2">{item.description}</p>
                            
                            {/* Progress bar */}
                            <div className="flex items-center gap-3">
                              <div className="flex-1 h-1.5 bg-white/5 rounded-full overflow-hidden">
                                <div 
                                  className="h-full bg-lime rounded-full transition-all"
                                  style={{ width: `${progress}%` }}
                                />
                              </div>
                              <span className="text-xs text-zinc-500">
                                {item.completed_posts}/{item.total_posts} posts
                              </span>
                            </div>
                          </div>
                          
                          <Button variant="ghost" size="sm" className="text-zinc-400">
                            <ChevronRight size={18} />
                          </Button>
                        </div>
                      </CardContent>
                    </Card>
                  </motion.div>
                );
              })
            )}
          </div>
        )}
      </div>
    </main>
  );
}
