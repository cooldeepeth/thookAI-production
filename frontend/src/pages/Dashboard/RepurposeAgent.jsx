import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useToast } from "@/hooks/use-toast";
import {
  RefreshCw, Linkedin, Twitter, Instagram, ArrowRight, Check,
  Loader2, Sparkles, Eye, ChevronDown, ChevronUp, Zap, Copy
} from "lucide-react";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const PLATFORM_CONFIG = {
  linkedin: { name: "LinkedIn", icon: Linkedin, color: "bg-blue-600", textColor: "text-blue-400" },
  x: { name: "X", icon: Twitter, color: "bg-zinc-700", textColor: "text-zinc-300" },
  instagram: { name: "Instagram", icon: Instagram, color: "bg-gradient-to-r from-pink-500 to-orange-400", textColor: "text-pink-400" }
};

export default function RepurposeAgent() {
  const [suggestions, setSuggestions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedContent, setSelectedContent] = useState(null);
  const [selectedPlatforms, setSelectedPlatforms] = useState([]);
  const [previews, setPreviews] = useState(null);
  const [loadingPreview, setLoadingPreview] = useState(false);
  const [repurposing, setRepurposing] = useState(false);
  const [expandedPreview, setExpandedPreview] = useState(null);
  const { toast } = useToast();
  const navigate = useNavigate();

  useEffect(() => {
    fetchSuggestions();
  }, []);

  const fetchSuggestions = async () => {
    try {
      const token = localStorage.getItem("thook_token");
      const res = await fetch(`${BACKEND_URL}/api/content/repurpose/suggestions?limit=6`, {
        headers: { Authorization: `Bearer ${token}` }
      });

      if (!res.ok) throw new Error("Failed to fetch suggestions");
      const data = await res.json();
      setSuggestions(data.suggestions || []);
    } catch (err) {
      console.error("Error:", err);
      toast({ title: "Error", description: "Failed to load content suggestions", variant: "destructive" });
    } finally {
      setLoading(false);
    }
  };

  const togglePlatform = (platform) => {
    setSelectedPlatforms(prev => 
      prev.includes(platform) 
        ? prev.filter(p => p !== platform)
        : [...prev, platform]
    );
    setPreviews(null);
  };

  const fetchPreview = async () => {
    if (!selectedContent || selectedPlatforms.length === 0) return;

    setLoadingPreview(true);
    setPreviews(null);

    try {
      const token = localStorage.getItem("thook_token");
      const platforms = selectedPlatforms.join(",");
      const res = await fetch(
        `${BACKEND_URL}/api/content/repurpose/preview/${selectedContent.job_id}?platforms=${platforms}`,
        { headers: { Authorization: `Bearer ${token}` } }
      );

      if (!res.ok) throw new Error("Preview failed");
      const data = await res.json();
      setPreviews(data.repurposed_previews);
    } catch (err) {
      console.error("Preview error:", err);
      toast({ title: "Error", description: "Failed to generate preview", variant: "destructive" });
    } finally {
      setLoadingPreview(false);
    }
  };

  const handleRepurpose = async () => {
    if (!selectedContent || selectedPlatforms.length === 0) return;

    setRepurposing(true);

    try {
      const token = localStorage.getItem("thook_token");
      const res = await fetch(`${BACKEND_URL}/api/content/repurpose`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          job_id: selectedContent.job_id,
          target_platforms: selectedPlatforms
        })
      });

      if (!res.ok) throw new Error("Repurpose failed");
      const data = await res.json();

      toast({
        title: "Content Repurposed!",
        description: `Created ${data.total_created} new drafts ready for review`
      });

      // Reset and refresh
      setSelectedContent(null);
      setSelectedPlatforms([]);
      setPreviews(null);
      fetchSuggestions();
    } catch (err) {
      console.error("Repurpose error:", err);
      toast({ title: "Error", description: "Failed to repurpose content", variant: "destructive" });
    } finally {
      setRepurposing(false);
    }
  };

  if (loading) {
    return (
      <main className="p-6">
        <div className="max-w-5xl mx-auto">
          <div className="space-y-4">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-32 bg-surface-2 rounded-2xl animate-pulse" />
            ))}
          </div>
        </div>
      </main>
    );
  }

  return (
    <main className="p-6">
      <div className="max-w-5xl mx-auto space-y-8">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-display font-bold text-white flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-violet/10 flex items-center justify-center">
                <RefreshCw className="text-violet" size={20} />
              </div>
              Repurpose Agent
            </h1>
            <p className="text-zinc-400 mt-1">Transform one piece of content into platform-native variants</p>
          </div>
          <Button variant="outline" onClick={fetchSuggestions} className="gap-2">
            <RefreshCw size={14} />
            Refresh
          </Button>
        </div>

        {/* How it works */}
        <Card className="bg-violet/5 border-violet/20">
          <CardContent className="py-4">
            <div className="flex items-center gap-6">
              <div className="flex items-center gap-2 text-sm">
                <span className="w-6 h-6 rounded-full bg-violet/20 text-violet flex items-center justify-center text-xs font-bold">1</span>
                <span className="text-zinc-400">Select content</span>
              </div>
              <ArrowRight size={14} className="text-zinc-600" />
              <div className="flex items-center gap-2 text-sm">
                <span className="w-6 h-6 rounded-full bg-violet/20 text-violet flex items-center justify-center text-xs font-bold">2</span>
                <span className="text-zinc-400">Choose platforms</span>
              </div>
              <ArrowRight size={14} className="text-zinc-600" />
              <div className="flex items-center gap-2 text-sm">
                <span className="w-6 h-6 rounded-full bg-violet/20 text-violet flex items-center justify-center text-xs font-bold">3</span>
                <span className="text-zinc-400">Preview & Create</span>
              </div>
            </div>
          </CardContent>
        </Card>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Content Selection */}
          <div className="space-y-4">
            <h2 className="text-lg font-semibold text-white">Select Source Content</h2>
            
            {suggestions.length === 0 ? (
              <Card className="bg-surface-2 border-white/5">
                <CardContent className="py-8 text-center">
                  <Sparkles className="mx-auto text-zinc-600 mb-3" size={32} />
                  <p className="text-zinc-500">No approved content to repurpose yet</p>
                  <Button variant="link" onClick={() => navigate("/dashboard/studio")} className="mt-2 text-lime">
                    Create content first
                  </Button>
                </CardContent>
              </Card>
            ) : (
              <div className="space-y-3">
                {suggestions.map((item) => {
                  const isSelected = selectedContent?.job_id === item.job_id;
                  const PlatformIcon = PLATFORM_CONFIG[item.platform]?.icon || Linkedin;
                  
                  return (
                    <Card
                      key={item.job_id}
                      className={`bg-surface-2 border-white/5 cursor-pointer transition-all hover:border-white/10 ${
                        isSelected ? "ring-2 ring-lime/50 border-lime/30" : ""
                      }`}
                      onClick={() => {
                        setSelectedContent(item);
                        setSelectedPlatforms([]);
                        setPreviews(null);
                      }}
                    >
                      <CardContent className="py-4">
                        <div className="flex items-start gap-4">
                          <div className={`w-10 h-10 rounded-xl ${PLATFORM_CONFIG[item.platform]?.color} flex items-center justify-center flex-shrink-0`}>
                            <PlatformIcon size={18} className="text-white" />
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 mb-1">
                              <span className="text-sm font-medium text-white capitalize">{item.platform}</span>
                              {item.persona_match && (
                                <Badge variant="outline" className="text-xs text-lime border-lime/30">
                                  {item.persona_match}/10 match
                                </Badge>
                              )}
                            </div>
                            <p className="text-xs text-zinc-400 line-clamp-2">{item.content_preview}</p>
                            <div className="flex gap-2 mt-2">
                              {item.available_platforms?.map((p) => {
                                const Icon = PLATFORM_CONFIG[p]?.icon;
                                return Icon && (
                                  <span key={p} className="text-zinc-600">
                                    <Icon size={12} />
                                  </span>
                                );
                              })}
                            </div>
                          </div>
                          {isSelected && (
                            <Check className="text-lime flex-shrink-0" size={18} />
                          )}
                        </div>
                      </CardContent>
                    </Card>
                  );
                })}
              </div>
            )}
          </div>

          {/* Platform Selection & Preview */}
          <div className="space-y-4">
            <h2 className="text-lg font-semibold text-white">Target Platforms</h2>
            
            {!selectedContent ? (
              <Card className="bg-surface-2 border-white/5">
                <CardContent className="py-8 text-center">
                  <p className="text-zinc-500">Select content to see available platforms</p>
                </CardContent>
              </Card>
            ) : (
              <>
                {/* Platform buttons */}
                <div className="flex gap-3">
                  {selectedContent.available_platforms?.map((platform) => {
                    const config = PLATFORM_CONFIG[platform];
                    const Icon = config?.icon;
                    const isSelected = selectedPlatforms.includes(platform);
                    
                    return (
                      <button
                        key={platform}
                        onClick={() => togglePlatform(platform)}
                        className={`flex-1 p-4 rounded-xl border transition-all ${
                          isSelected
                            ? "bg-white/10 border-lime/50"
                            : "bg-surface-2 border-white/5 hover:border-white/10"
                        }`}
                      >
                        <div className={`w-10 h-10 rounded-xl ${config?.color} flex items-center justify-center mx-auto mb-2`}>
                          {Icon && <Icon size={18} className="text-white" />}
                        </div>
                        <p className="text-sm text-white font-medium">{config?.name}</p>
                        {isSelected && <Check className="mx-auto mt-2 text-lime" size={16} />}
                      </button>
                    );
                  })}
                </div>

                {/* Preview button */}
                {selectedPlatforms.length > 0 && (
                  <Button
                    onClick={fetchPreview}
                    disabled={loadingPreview}
                    variant="outline"
                    className="w-full gap-2"
                  >
                    {loadingPreview ? (
                      <>
                        <Loader2 size={14} className="animate-spin" />
                        Generating previews...
                      </>
                    ) : (
                      <>
                        <Eye size={14} />
                        Preview Repurposed Content
                      </>
                    )}
                  </Button>
                )}

                {/* Previews */}
                {previews && (
                  <div className="space-y-3">
                    {Object.entries(previews).map(([platform, data]) => {
                      const config = PLATFORM_CONFIG[platform];
                      const Icon = config?.icon;
                      const isExpanded = expandedPreview === platform;
                      const content = Array.isArray(data.content) 
                        ? data.content.join("\n\n---\n\n") 
                        : data.content;
                      
                      return (
                        <Card key={platform} className="bg-surface-2 border-white/5">
                          <CardContent className="py-4">
                            <button
                              onClick={() => setExpandedPreview(isExpanded ? null : platform)}
                              className="w-full flex items-center justify-between"
                            >
                              <div className="flex items-center gap-3">
                                <div className={`w-8 h-8 rounded-lg ${config?.color} flex items-center justify-center`}>
                                  {Icon && <Icon size={14} className="text-white" />}
                                </div>
                                <span className="text-sm font-medium text-white">{config?.name}</span>
                                {data.is_thread && (
                                  <Badge variant="outline" className="text-xs">Thread</Badge>
                                )}
                              </div>
                              {isExpanded ? <ChevronUp size={16} className="text-zinc-400" /> : <ChevronDown size={16} className="text-zinc-400" />}
                            </button>
                            
                            <AnimatePresence>
                              {isExpanded && (
                                <motion.div
                                  initial={{ opacity: 0, height: 0 }}
                                  animate={{ opacity: 1, height: "auto" }}
                                  exit={{ opacity: 0, height: 0 }}
                                  className="mt-4 pt-4 border-t border-white/5"
                                >
                                  <p className="text-xs text-zinc-400 whitespace-pre-line">{content}</p>
                                  <p className="text-[10px] text-zinc-600 mt-2">{data.adaptation_notes}</p>
                                </motion.div>
                              )}
                            </AnimatePresence>
                          </CardContent>
                        </Card>
                      );
                    })}
                  </div>
                )}

                {/* Repurpose button */}
                {selectedPlatforms.length > 0 && (
                  <Button
                    onClick={handleRepurpose}
                    disabled={repurposing}
                    className="w-full bg-lime text-black hover:bg-lime/90 gap-2"
                  >
                    {repurposing ? (
                      <>
                        <Loader2 size={14} className="animate-spin" />
                        Creating content...
                      </>
                    ) : (
                      <>
                        <Zap size={14} />
                        Repurpose to {selectedPlatforms.length} Platform{selectedPlatforms.length > 1 ? "s" : ""}
                      </>
                    )}
                  </Button>
                )}
              </>
            )}
          </div>
        </div>
      </div>
    </main>
  );
}
