import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import {
  LayoutTemplate, Search, Filter, ThumbsUp, Eye, 
  Copy, Sparkles, ChevronRight, Loader2, X,
  TrendingUp, Clock, Award, Hash
} from "lucide-react";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const PLATFORM_ICONS = {
  linkedin: "💼",
  x: "𝕏",
  instagram: "📸",
};

const CATEGORY_LABELS = {
  thought_leadership: "Thought Leadership",
  storytelling: "Storytelling",
  how_to: "How-To Guide",
  listicle: "Listicle",
  contrarian: "Contrarian Take",
  case_study: "Case Study",
  personal_journey: "Personal Journey",
  industry_insights: "Industry Insights",
  tips_and_tricks: "Tips & Tricks",
  behind_the_scenes: "Behind the Scenes",
};

const HOOK_TYPE_COLORS = {
  question: "bg-cyan-500/20 text-cyan-400",
  bold_claim: "bg-orange-500/20 text-orange-400",
  story_opener: "bg-violet-500/20 text-violet-400",
  statistic: "bg-blue-500/20 text-blue-400",
  contrarian: "bg-pink-500/20 text-pink-400",
  curiosity_gap: "bg-yellow-500/20 text-yellow-400",
  direct_address: "bg-lime/20 text-lime",
  number_list: "bg-emerald-500/20 text-emerald-400",
};

function TemplateCard({ template, onUse, onUpvote }) {
  const [isHovered, setIsHovered] = useState(false);
  
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      className="bg-white/5 border border-white/10 rounded-xl overflow-hidden hover:border-white/20 transition-all group"
    >
      {/* Header */}
      <div className="p-4 border-b border-white/5">
        <div className="flex items-start justify-between mb-2">
          <div className="flex items-center gap-2">
            <span className="text-lg">{PLATFORM_ICONS[template.platform] || "📝"}</span>
            <span className={`text-xs px-2 py-0.5 rounded-full ${HOOK_TYPE_COLORS[template.hook_type] || "bg-white/10 text-zinc-400"}`}>
              {template.hook_type?.replace("_", " ")}
            </span>
          </div>
          <span className="text-xs text-zinc-600">{template.author_archetype}</span>
        </div>
        <h3 className="font-semibold text-white line-clamp-1">{template.title}</h3>
        <p className="text-xs text-zinc-500 mt-1">
          {CATEGORY_LABELS[template.category] || template.category}
        </p>
      </div>
      
      {/* Preview */}
      <div className="p-4 bg-black/20">
        <p className="text-sm text-zinc-400 line-clamp-3 font-mono">
          "{template.hook}"
        </p>
        {template.structure_preview && (
          <p className="text-xs text-zinc-600 mt-2 line-clamp-2">
            {template.structure_preview}
          </p>
        )}
      </div>
      
      {/* Footer */}
      <div className="p-4 flex items-center justify-between">
        <div className="flex items-center gap-4 text-xs text-zinc-500">
          <button
            onClick={() => onUpvote(template.template_id)}
            className={`flex items-center gap-1 hover:text-lime transition-colors ${template.user_upvoted ? "text-lime" : ""}`}
          >
            <ThumbsUp size={14} className={template.user_upvoted ? "fill-current" : ""} />
            {template.upvotes}
          </button>
          <span className="flex items-center gap-1">
            <Copy size={14} />
            {template.uses_count}
          </span>
        </div>
        <button
          onClick={() => onUse(template)}
          className="btn-primary text-xs py-1.5 px-3 opacity-0 group-hover:opacity-100 transition-opacity"
        >
          Use Template
        </button>
      </div>
    </motion.div>
  );
}

function TemplateDetailModal({ template, onClose, onUse }) {
  if (!template) return null;
  
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
        className="bg-[#0F0F0F] border border-white/10 rounded-2xl p-6 max-w-lg w-full max-h-[80vh] overflow-y-auto"
        onClick={e => e.stopPropagation()}
      >
        <div className="flex items-start justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 bg-violet/10 rounded-xl flex items-center justify-center text-2xl">
              {PLATFORM_ICONS[template.platform] || "📝"}
            </div>
            <div>
              <h3 className="font-display font-bold text-white">{template.title}</h3>
              <p className="text-xs text-zinc-500">
                {CATEGORY_LABELS[template.category]} • {template.author_archetype}
              </p>
            </div>
          </div>
          <button onClick={onClose} className="text-zinc-500 hover:text-white">
            <X size={20} />
          </button>
        </div>
        
        {/* Tags */}
        <div className="flex flex-wrap gap-2 mb-4">
          <span className={`text-xs px-2 py-1 rounded-full ${HOOK_TYPE_COLORS[template.hook_type] || "bg-white/10"}`}>
            {template.hook_type?.replace("_", " ")}
          </span>
          {template.tags?.map(tag => (
            <span key={tag} className="text-xs px-2 py-1 rounded-full bg-white/5 text-zinc-400">
              #{tag}
            </span>
          ))}
        </div>
        
        {/* Hook preview */}
        <div className="bg-white/5 rounded-xl p-4 mb-4">
          <p className="text-xs text-zinc-500 mb-2">Hook</p>
          <p className="text-white font-mono">"{template.hook}"</p>
        </div>
        
        {/* Structure */}
        {template.structure_preview && (
          <div className="bg-white/5 rounded-xl p-4 mb-4">
            <p className="text-xs text-zinc-500 mb-2">Structure Preview</p>
            <p className="text-zinc-400 text-sm whitespace-pre-line">{template.structure_preview}</p>
          </div>
        )}
        
        {/* Stats */}
        <div className="flex items-center justify-between text-sm text-zinc-500 mb-6">
          <span className="flex items-center gap-1">
            <ThumbsUp size={14} /> {template.upvotes} upvotes
          </span>
          <span className="flex items-center gap-1">
            <Copy size={14} /> {template.uses_count} uses
          </span>
          <span>{template.word_count} words</span>
        </div>
        
        <button
          onClick={() => onUse(template)}
          className="w-full btn-primary py-3 flex items-center justify-center gap-2"
        >
          <Sparkles size={18} />
          Use This Template
        </button>
      </motion.div>
    </motion.div>
  );
}

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
  const [selectedTemplate, setSelectedTemplate] = useState(null);
  const [showFilters, setShowFilters] = useState(false);

  // Fetch templates
  useEffect(() => {
    const fetchTemplates = async () => {
      setLoading(true);
      try {
        const params = new URLSearchParams();
        if (selectedPlatform) params.append("platform", selectedPlatform);
        if (selectedCategory) params.append("category", selectedCategory);
        params.append("sort", sortBy);
        params.append("limit", "50");
        
        const res = await fetch(`${BACKEND_URL}/api/templates?${params}`, { credentials: "include" });
        const data = await res.json();
        if (data.success) {
          setTemplates(data.templates || []);
        }
      } catch (err) {
        console.error("Failed to fetch templates:", err);
      } finally {
        setLoading(false);
      }
    };
    
    fetchTemplates();
  }, [selectedPlatform, selectedCategory, sortBy]);

  // Fetch categories and featured
  useEffect(() => {
    const fetchMeta = async () => {
      try {
        const [catRes, featRes] = await Promise.all([
          fetch(`${BACKEND_URL}/api/templates/categories`, { credentials: "include" }),
          fetch(`${BACKEND_URL}/api/templates/featured`, { credentials: "include" }),
        ]);
        
        const catData = await catRes.json();
        const featData = await featRes.json();
        
        if (catData.success) setCategories(catData.categories || []);
        if (featData.success) setFeatured(featData.featured || []);
      } catch (err) {
        console.error("Failed to fetch metadata:", err);
      }
    };
    
    fetchMeta();
  }, []);

  const handleUpvote = async (templateId) => {
    try {
      const res = await fetch(`${BACKEND_URL}/api/templates/${templateId}/upvote`, {
        method: "POST",
        credentials: "include",
      });
      const data = await res.json();
      
      if (data.success) {
        setTemplates(prev => prev.map(t => 
          t.template_id === templateId 
            ? { ...t, upvotes: t.upvotes + (data.upvoted ? 1 : -1), user_upvoted: data.upvoted }
            : t
        ));
      }
    } catch (err) {
      console.error("Failed to upvote:", err);
    }
  };

  const handleUseTemplate = async (template) => {
    try {
      const res = await fetch(`${BACKEND_URL}/api/templates/${template.template_id}/use`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({}),
      });
      const data = await res.json();
      
      if (data.success && data.prefill) {
        // Navigate to content studio with prefill
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

  // Filter templates by search
  const filteredTemplates = templates.filter(t => 
    !searchQuery || 
    t.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
    t.hook?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <main className="flex-1 p-6" data-testid="templates-page">
      {/* Template Detail Modal */}
      <AnimatePresence>
        {selectedTemplate && (
          <TemplateDetailModal
            template={selectedTemplate}
            onClose={() => setSelectedTemplate(null)}
            onUse={handleUseTemplate}
          />
        )}
      </AnimatePresence>

      {/* Header */}
      <div className="flex items-start justify-between mb-6">
        <div>
          <h2 className="font-display font-bold text-2xl text-white">Templates Marketplace</h2>
          <p className="text-zinc-500 text-sm">Discover and use proven content templates from the community</p>
        </div>
      </div>

      {/* Search and Filters */}
      <div className="flex items-center gap-4 mb-6">
        <div className="flex-1 relative">
          <Search size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500" />
          <input
            type="text"
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            placeholder="Search templates..."
            className="w-full bg-white/5 border border-white/10 rounded-xl pl-10 pr-4 py-2.5 text-white placeholder-zinc-600 outline-none focus:border-lime/50"
          />
        </div>
        
        {/* Sort dropdown */}
        <select
          value={sortBy}
          onChange={e => setSortBy(e.target.value)}
          className="bg-white/5 border border-white/10 rounded-xl px-4 py-2.5 text-white outline-none focus:border-lime/50"
        >
          <option value="popular">Most Popular</option>
          <option value="recent">Most Recent</option>
          <option value="most_used">Most Used</option>
        </select>
        
        <button
          onClick={() => setShowFilters(!showFilters)}
          className={`btn-ghost flex items-center gap-2 ${showFilters ? "text-lime" : ""}`}
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
                  {[null, "linkedin", "x", "instagram"].map(p => (
                    <button
                      key={p || "all"}
                      onClick={() => setSelectedPlatform(p)}
                      className={`px-3 py-1.5 rounded-lg text-sm transition-colors ${
                        selectedPlatform === p 
                          ? "bg-lime text-black" 
                          : "bg-white/5 text-zinc-400 hover:bg-white/10"
                      }`}
                    >
                      {p ? PLATFORM_ICONS[p] : "All"}
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
                  {categories.slice(0, 6).map(cat => (
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
      {featured.length > 0 && !searchQuery && !selectedCategory && (
        <div className="mb-8">
          <div className="flex items-center gap-2 mb-4">
            <TrendingUp size={18} className="text-lime" />
            <h3 className="font-semibold text-white">Trending Templates</h3>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {featured.slice(0, 3).map(template => (
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
          <LayoutTemplate size={48} className="text-zinc-700 mx-auto mb-4" />
          <h3 className="text-lg text-zinc-500 mb-2">No templates found</h3>
          <p className="text-sm text-zinc-600">
            {searchQuery ? "Try a different search term" : "Be the first to publish a template!"}
          </p>
        </div>
      ) : (
        <>
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-white">
              {selectedCategory ? CATEGORY_LABELS[selectedCategory] : "All Templates"}
            </h3>
            <span className="text-sm text-zinc-500">{filteredTemplates.length} templates</span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {filteredTemplates.map(template => (
              <TemplateCard
                key={template.template_id}
                template={template}
                onUse={handleUseTemplate}
                onUpvote={handleUpvote}
              />
            ))}
          </div>
        </>
      )}
    </main>
  );
}
