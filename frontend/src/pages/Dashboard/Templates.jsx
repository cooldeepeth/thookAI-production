import { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import {
  LayoutTemplate, Search, Filter,
  Sparkles, Loader2, X, TrendingUp, Plus,
  ChevronLeft, ChevronRight, BookOpen, Upload, Trash2
} from "lucide-react";
import TemplateCard, { CATEGORY_LABELS } from "@/components/TemplateCard";
import {
  getTemplates,
  getCategories,
  getFeaturedTemplates,
  upvoteTemplate,
  useTemplate as apiUseTemplate,
  getMyPublishedTemplates,
  getMyUsedTemplates,
  createTemplate,
  deleteTemplate,
} from "@/lib/templatesApi";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const PAGE_SIZE = 20;

// ==================== Share Template Dialog ====================

function ShareTemplateDialog({ onClose, onSubmit }) {
  const [jobs, setJobs] = useState([]);
  const [loadingJobs, setLoadingJobs] = useState(true);
  const [selectedJobId, setSelectedJobId] = useState("");
  const [title, setTitle] = useState("");
  const [category, setCategory] = useState("");
  const [description, setDescription] = useState("");
  const [tags, setTags] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [categories, setCategories] = useState([]);

  useEffect(() => {
    const fetchData = async () => {
      setLoadingJobs(true);
      try {
        // Fetch approved content jobs
        const token = localStorage.getItem("thook_token");
        const res = await fetch(`${BACKEND_URL}/api/content?status=approved`, {
          credentials: "include",
          headers: token ? { Authorization: `Bearer ${token}` } : {},
        });
        if (res.ok) {
          const data = await res.json();
          setJobs(data.jobs || []);
        }

        // Fetch categories
        const catData = await getCategories();
        if (catData.success) {
          setCategories(catData.categories || []);
        }
      } catch (err) {
        console.error("Failed to load data:", err);
      } finally {
        setLoadingJobs(false);
      }
    };
    fetchData();
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!selectedJobId || !title.trim() || !category) return;

    setSubmitting(true);
    setError(null);
    try {
      const tagList = tags
        .split(",")
        .map((t) => t.trim())
        .filter(Boolean);

      await onSubmit({
        job_id: selectedJobId,
        title: title.trim(),
        category,
        description: description.trim() || undefined,
        tags: tagList,
      });
      onClose();
    } catch (err) {
      setError(err.message || "Failed to publish template");
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
            <div className="w-10 h-10 bg-lime/10 rounded-xl flex items-center justify-center">
              <Upload size={18} className="text-lime" />
            </div>
            <div>
              <h3 className="font-display font-bold text-white">Share Your Template</h3>
              <p className="text-xs text-zinc-500">
                Publish approved content as a community template
              </p>
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
          {/* Select content */}
          <div>
            <label className="text-xs text-zinc-500 mb-1.5 block">
              Select Approved Content *
            </label>
            {loadingJobs ? (
              <div className="flex items-center gap-2 text-sm text-zinc-500 py-3">
                <Loader2 size={14} className="animate-spin" /> Loading your content...
              </div>
            ) : jobs.length === 0 ? (
              <p className="text-sm text-zinc-600 py-3">
                No approved content available. Approve a post first to share it as a template.
              </p>
            ) : (
              <select
                value={selectedJobId}
                onChange={(e) => setSelectedJobId(e.target.value)}
                required
                className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-2.5 text-white outline-none focus:border-lime/50"
              >
                <option value="">Choose content...</option>
                {jobs.map((job) => (
                  <option key={job.job_id} value={job.job_id}>
                    [{job.platform}] {job.draft?.substring(0, 60) || job.job_id}...
                  </option>
                ))}
              </select>
            )}
          </div>

          {/* Title */}
          <div>
            <label className="text-xs text-zinc-500 mb-1.5 block">Template Title *</label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              required
              maxLength={100}
              placeholder="e.g. The Bold Opener Framework"
              className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-2.5 text-white placeholder-zinc-600 outline-none focus:border-lime/50"
            />
          </div>

          {/* Category */}
          <div>
            <label className="text-xs text-zinc-500 mb-1.5 block">Category *</label>
            <select
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              required
              className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-2.5 text-white outline-none focus:border-lime/50"
            >
              <option value="">Select category...</option>
              {categories.map((cat) => (
                <option key={cat} value={cat}>
                  {CATEGORY_LABELS[cat] || cat}
                </option>
              ))}
            </select>
          </div>

          {/* Description */}
          <div>
            <label className="text-xs text-zinc-500 mb-1.5 block">Description (optional)</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              maxLength={500}
              rows={3}
              placeholder="What makes this template effective?"
              className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-2.5 text-white placeholder-zinc-600 outline-none focus:border-lime/50 resize-none"
            />
          </div>

          {/* Tags */}
          <div>
            <label className="text-xs text-zinc-500 mb-1.5 block">
              Tags (comma separated, optional)
            </label>
            <input
              type="text"
              value={tags}
              onChange={(e) => setTags(e.target.value)}
              placeholder="e.g. leadership, growth, startup"
              className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-2.5 text-white placeholder-zinc-600 outline-none focus:border-lime/50"
            />
          </div>

          <button
            type="submit"
            disabled={submitting || !selectedJobId || !title.trim() || !category}
            className="w-full btn-primary py-3 flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {submitting ? (
              <Loader2 size={18} className="animate-spin" />
            ) : (
              <Sparkles size={18} />
            )}
            Publish Template
          </button>
        </form>
      </motion.div>
    </motion.div>
  );
}

// ==================== My Templates Tab ====================

function MyTemplatesTab({ onUpvote, onUseTemplate }) {
  const [publishedTemplates, setPublishedTemplates] = useState([]);
  const [usedTemplates, setUsedTemplates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeSubTab, setActiveSubTab] = useState("published");
  const [deleting, setDeleting] = useState(null);

  useEffect(() => {
    const fetchMyTemplates = async () => {
      setLoading(true);
      try {
        const [pubData, usedData] = await Promise.all([
          getMyPublishedTemplates(),
          getMyUsedTemplates(),
        ]);
        if (pubData.success) setPublishedTemplates(pubData.templates || []);
        if (usedData.success) setUsedTemplates(usedData.templates || []);
      } catch (err) {
        console.error("Failed to fetch my templates:", err);
      } finally {
        setLoading(false);
      }
    };
    fetchMyTemplates();
  }, []);

  const handleDelete = async (templateId) => {
    if (deleting) return;
    setDeleting(templateId);
    try {
      const data = await deleteTemplate(templateId);
      if (data.success) {
        setPublishedTemplates((prev) =>
          prev.filter((t) => t.template_id !== templateId)
        );
      }
    } catch (err) {
      console.error("Failed to delete template:", err);
    } finally {
      setDeleting(null);
    }
  };

  const templates = activeSubTab === "published" ? publishedTemplates : usedTemplates;

  return (
    <div>
      {/* Sub-tabs */}
      <div className="flex gap-2 mb-6">
        <button
          onClick={() => setActiveSubTab("published")}
          className={`px-4 py-2 rounded-lg text-sm transition-colors ${
            activeSubTab === "published"
              ? "bg-lime text-black font-medium"
              : "bg-white/5 text-zinc-400 hover:bg-white/10"
          }`}
        >
          Published ({publishedTemplates.length})
        </button>
        <button
          onClick={() => setActiveSubTab("used")}
          className={`px-4 py-2 rounded-lg text-sm transition-colors ${
            activeSubTab === "used"
              ? "bg-lime text-black font-medium"
              : "bg-white/5 text-zinc-400 hover:bg-white/10"
          }`}
        >
          Used ({usedTemplates.length})
        </button>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-16">
          <Loader2 size={32} className="animate-spin text-zinc-500" />
        </div>
      ) : templates.length === 0 ? (
        <div className="text-center py-16">
          <BookOpen size={48} className="text-zinc-700 mx-auto mb-4" />
          <h3 className="text-lg text-zinc-500 mb-2">
            {activeSubTab === "published"
              ? "No templates published yet"
              : "No templates used yet"}
          </h3>
          <p className="text-sm text-zinc-600">
            {activeSubTab === "published"
              ? "Share your best content with the community!"
              : "Browse the marketplace to find templates to use."}
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {templates.map((template) => (
            <div key={template.template_id} className="relative group/card">
              <TemplateCard
                template={template}
                onUse={onUseTemplate}
                onUpvote={onUpvote}
                showUseButton={activeSubTab === "used"}
              />
              {activeSubTab === "published" && (
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    handleDelete(template.template_id);
                  }}
                  disabled={deleting === template.template_id}
                  className="absolute top-3 right-3 p-1.5 rounded-lg bg-red-500/10 text-red-400 hover:bg-red-500/20 opacity-0 group-hover/card:opacity-100 transition-opacity z-10"
                  title="Delete template"
                  aria-label="Delete template"
                >
                  {deleting === template.template_id ? (
                    <Loader2 size={14} className="animate-spin" />
                  ) : (
                    <Trash2 size={14} />
                  )}
                </button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ==================== Main Templates Page ====================

export default function Templates() {
  const navigate = useNavigate();
  const [templates, setTemplates] = useState([]);
  const [featured, setFeatured] = useState([]);
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedPlatform, setSelectedPlatform] = useState(null);
  const [selectedCategory, setSelectedCategory] = useState(null);
  const [sortBy, setSortBy] = useState("popular");
  const [showFilters, setShowFilters] = useState(false);
  const [showShareDialog, setShowShareDialog] = useState(false);
  const [activeTab, setActiveTab] = useState("browse"); // browse | my
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(0);

  const totalPages = Math.ceil(total / PAGE_SIZE);

  // Fetch templates
  const fetchTemplates = useCallback(async () => {
    setLoading(true);
    try {
      const data = await getTemplates({
        platform: selectedPlatform,
        category: selectedCategory,
        sort: sortBy,
        limit: PAGE_SIZE,
        offset: page * PAGE_SIZE,
      });
      if (data.success) {
        setTemplates(data.templates || []);
        setTotal(data.total || 0);
      }
    } catch (err) {
      console.error("Failed to fetch templates:", err);
    } finally {
      setLoading(false);
    }
  }, [selectedPlatform, selectedCategory, sortBy, page]);

  useEffect(() => {
    if (activeTab === "browse") {
      fetchTemplates();
    }
  }, [fetchTemplates, activeTab]);

  // Fetch categories and featured on mount
  useEffect(() => {
    const fetchMeta = async () => {
      try {
        const [catData, featData] = await Promise.all([
          getCategories(),
          getFeaturedTemplates(),
        ]);
        if (catData.success) setCategories(catData.categories || []);
        if (featData.success) setFeatured(featData.featured || []);
      } catch (err) {
        console.error("Failed to fetch metadata:", err);
      }
    };
    fetchMeta();
  }, []);

  // Reset page when filters change
  useEffect(() => {
    setPage(0);
  }, [selectedPlatform, selectedCategory, sortBy]);

  const handleUpvote = async (templateId) => {
    try {
      const data = await upvoteTemplate(templateId);
      if (data.success) {
        // FIXED: update ALL state arrays so upvote is reflected everywhere
        const updater = (prev) =>
          prev.map((t) =>
            t.template_id === templateId
              ? {
                  ...t,
                  upvotes: t.upvotes + (data.upvoted ? 1 : -1),
                  user_upvoted: data.upvoted,
                }
              : t
          );
        setTemplates(updater);
        setFeatured(updater);
      }
    } catch (err) {
      console.error("Failed to upvote:", err);
    }
  };

  const handleUseTemplate = async (template) => {
    try {
      const data = await apiUseTemplate(template.template_id);
      if (data.success && data.prefill) {
        const params = new URLSearchParams({
          platform: data.prefill.platform,
          prefill: data.prefill.raw_input,
          template: template.template_id,
        });
        navigate(`/dashboard/studio?${params}`);
      }
    } catch (err) {
      console.error("Failed to use template:", err);
    }
  };

  const handleShareTemplate = async (templateData) => {
    const data = await createTemplate(templateData);
    if (data.success) {
      // Refresh templates list
      fetchTemplates();
    }
    return data;
  };

  // Filter templates by search (client-side search on already fetched results)
  const filteredTemplates = templates.filter(
    (t) =>
      !searchQuery ||
      t.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      t.hook?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <main className="flex-1 p-6" data-testid="templates-page">
      {/* Share Template Dialog */}
      <AnimatePresence>
        {showShareDialog && (
          <ShareTemplateDialog
            onClose={() => setShowShareDialog(false)}
            onSubmit={handleShareTemplate}
          />
        )}
      </AnimatePresence>

      {/* Header */}
      <div className="flex items-start justify-between mb-6">
        <div>
          <h2 className="font-display font-bold text-2xl text-white">
            Templates Marketplace
          </h2>
          <p className="text-zinc-500 text-sm">
            Discover and use proven content templates from the community
          </p>
        </div>
        <button
          onClick={() => setShowShareDialog(true)}
          className="btn-primary flex items-center gap-2 text-sm"
        >
          <Plus size={16} />
          Share Your Template
        </button>
      </div>

      {/* Tab navigation */}
      <div className="flex items-center gap-2 mb-6 border-b border-white/5 pb-0">
        <button
          onClick={() => setActiveTab("browse")}
          className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors -mb-px ${
            activeTab === "browse"
              ? "border-lime text-lime"
              : "border-transparent text-zinc-500 hover:text-white"
          }`}
        >
          Browse
        </button>
        <button
          onClick={() => setActiveTab("my")}
          className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors -mb-px ${
            activeTab === "my"
              ? "border-lime text-lime"
              : "border-transparent text-zinc-500 hover:text-white"
          }`}
        >
          My Templates
        </button>
      </div>

      {/* My Templates Tab */}
      {activeTab === "my" && (
        <MyTemplatesTab
          onUpvote={handleUpvote}
          onUseTemplate={handleUseTemplate}
        />
      )}

      {/* Browse Tab */}
      {activeTab === "browse" && (
        <>
          {/* Search and Filters */}
          <div className="flex items-center gap-4 mb-6">
            <div className="flex-1 relative">
              <Search
                size={18}
                className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500"
              />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search templates..."
                className="w-full bg-white/5 border border-white/10 rounded-xl pl-10 pr-4 py-2.5 text-white placeholder-zinc-600 outline-none focus:border-lime/50"
              />
            </div>

            {/* Sort dropdown */}
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              className="bg-white/5 border border-white/10 rounded-xl px-4 py-2.5 text-white outline-none focus:border-lime/50"
            >
              <option value="popular">Most Popular</option>
              <option value="recent">Most Recent</option>
              <option value="most_used">Most Used</option>
            </select>

            <button
              onClick={() => setShowFilters(!showFilters)}
              className={`btn-ghost flex items-center gap-2 ${
                showFilters ? "text-lime" : ""
              }`}
            >
              <Filter size={18} />
              Filters
            </button>
          </div>

          {/* Filter bar */}
          <AnimatePresence>
            {showFilters && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: "auto", opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                className="overflow-hidden mb-6"
              >
                <div className="flex flex-wrap gap-4 p-4 bg-white/5 rounded-xl">
                  {/* Platform filter */}
                  <div>
                    <p className="text-xs text-zinc-500 mb-2">Platform</p>
                    <div className="flex gap-2">
                      {[
                        { value: null, label: "All" },
                        { value: "linkedin", label: "💼 LinkedIn" },
                        { value: "x", label: "𝕏 X" },
                        { value: "instagram", label: "📸 Instagram" },
                      ].map((p) => (
                        <button
                          key={p.value || "all"}
                          onClick={() => setSelectedPlatform(p.value)}
                          className={`px-3 py-1.5 rounded-lg text-sm transition-colors ${
                            selectedPlatform === p.value
                              ? "bg-lime text-black"
                              : "bg-white/5 text-zinc-400 hover:bg-white/10"
                          }`}
                        >
                          {p.label}
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Category filter */}
                  <div className="flex-1">
                    <p className="text-xs text-zinc-500 mb-2">Category</p>
                    <div className="flex flex-wrap gap-2">
                      <button
                        onClick={() => setSelectedCategory(null)}
                        className={`px-3 py-1.5 rounded-lg text-sm transition-colors ${
                          !selectedCategory
                            ? "bg-lime text-black"
                            : "bg-white/5 text-zinc-400 hover:bg-white/10"
                        }`}
                      >
                        All
                      </button>
                      {categories.map((cat) => (
                        <button
                          key={cat}
                          onClick={() => setSelectedCategory(cat)}
                          className={`px-3 py-1.5 rounded-lg text-sm transition-colors ${
                            selectedCategory === cat
                              ? "bg-lime text-black"
                              : "bg-white/5 text-zinc-400 hover:bg-white/10"
                          }`}
                        >
                          {CATEGORY_LABELS[cat] || cat}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Featured section */}
          {featured.length > 0 &&
            !searchQuery &&
            !selectedCategory &&
            !selectedPlatform &&
            page === 0 && (
              <div className="mb-8">
                <div className="flex items-center gap-2 mb-4">
                  <TrendingUp size={18} className="text-lime" />
                  <h3 className="font-semibold text-white">
                    Trending Templates
                  </h3>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {featured.slice(0, 3).map((template) => (
                    <TemplateCard
                      key={template.template_id}
                      template={template}
                      onUse={handleUseTemplate}
                      onUpvote={handleUpvote}
                    />
                  ))}
                </div>
              </div>
            )}

          {/* Main grid */}
          {loading ? (
            <div className="flex items-center justify-center py-16">
              <Loader2 size={32} className="animate-spin text-zinc-500" />
            </div>
          ) : filteredTemplates.length === 0 ? (
            <div className="text-center py-16">
              <LayoutTemplate
                size={48}
                className="text-zinc-700 mx-auto mb-4"
              />
              <h3 className="text-lg font-medium text-white mb-2">
                {searchQuery ? "No templates found" : "Discover templates from the community"}
              </h3>
              <p className="text-sm text-zinc-400 mb-6">
                {searchQuery
                  ? "Try a different search term or adjust your filters."
                  : "Browse proven content templates or be the first to share yours!"}
              </p>
              {!searchQuery && (
                <button
                  onClick={() => setShowShareDialog(true)}
                  className="px-6 py-2 bg-lime text-black font-medium rounded-lg hover:bg-lime/90 transition-colors inline-flex items-center gap-2"
                >
                  <Plus size={16} /> Share Your Template
                </button>
              )}
            </div>
          ) : (
            <>
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-semibold text-white">
                  {selectedCategory
                    ? CATEGORY_LABELS[selectedCategory]
                    : "All Templates"}
                </h3>
                <span className="text-sm text-zinc-500">
                  {total} template{total !== 1 ? "s" : ""}
                </span>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                {filteredTemplates.map((template) => (
                  <TemplateCard
                    key={template.template_id}
                    template={template}
                    onUse={handleUseTemplate}
                    onUpvote={handleUpvote}
                  />
                ))}
              </div>

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="flex items-center justify-center gap-3 mt-8">
                  <button
                    onClick={() => setPage((p) => Math.max(0, p - 1))}
                    disabled={page === 0}
                    aria-label="Previous page"
                    className="p-2 rounded-lg bg-white/5 text-zinc-400 hover:bg-white/10 hover:text-white disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                  >
                    <ChevronLeft size={18} />
                  </button>
                  <div className="flex items-center gap-1">
                    {Array.from({ length: Math.min(totalPages, 7) }, (_, i) => {
                      let pageNum;
                      if (totalPages <= 7) {
                        pageNum = i;
                      } else if (page < 3) {
                        pageNum = i;
                      } else if (page > totalPages - 4) {
                        pageNum = totalPages - 7 + i;
                      } else {
                        pageNum = page - 3 + i;
                      }
                      return (
                        <button
                          key={pageNum}
                          onClick={() => setPage(pageNum)}
                          className={`w-8 h-8 rounded-lg text-sm transition-colors ${
                            page === pageNum
                              ? "bg-lime text-black font-medium"
                              : "text-zinc-500 hover:bg-white/10 hover:text-white"
                          }`}
                        >
                          {pageNum + 1}
                        </button>
                      );
                    })}
                  </div>
                  <button
                    onClick={() =>
                      setPage((p) => Math.min(totalPages - 1, p + 1))
                    }
                    disabled={page >= totalPages - 1}
                    aria-label="Next page"
                    className="p-2 rounded-lg bg-white/5 text-zinc-400 hover:bg-white/10 hover:text-white disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                  >
                    <ChevronRight size={18} />
                  </button>
                </div>
              )}
            </>
          )}
        </>
      )}
    </main>
  );
}
