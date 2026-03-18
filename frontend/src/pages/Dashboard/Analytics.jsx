import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useToast } from "@/hooks/use-toast";
import {
  BarChart3, TrendingUp, TrendingDown, Minus, Eye, Heart, Share2,
  MessageCircle, RefreshCw, Sparkles, Lightbulb, AlertTriangle,
  Shield, ChevronRight, Linkedin, Twitter, Instagram, Zap,
  Target, Brain, LineChart, ArrowUpRight, ArrowDownRight
} from "lucide-react";

const BACKEND_URL = import.meta.env.REACT_APP_BACKEND_URL || process.env.REACT_APP_BACKEND_URL;

const PLATFORM_CONFIG = {
  linkedin: { name: "LinkedIn", icon: Linkedin, color: "bg-blue-600", textColor: "text-blue-400" },
  x: { name: "X", icon: Twitter, color: "bg-zinc-700", textColor: "text-zinc-300" },
  instagram: { name: "Instagram", icon: Instagram, color: "bg-gradient-to-r from-pink-500 to-orange-400", textColor: "text-pink-400" }
};

const TREND_ICONS = {
  improving: { icon: TrendingUp, color: "text-green-400", bg: "bg-green-500/10" },
  stable: { icon: Minus, color: "text-yellow-400", bg: "bg-yellow-500/10" },
  declining: { icon: TrendingDown, color: "text-red-400", bg: "bg-red-500/10" },
  insufficient_data: { icon: Minus, color: "text-zinc-400", bg: "bg-zinc-500/10" }
};

const SHIELD_STATUS_CONFIG = {
  healthy: { color: "bg-green-500/10 text-green-400 border-green-500/20", icon: Shield },
  caution: { color: "bg-yellow-500/10 text-yellow-400 border-yellow-500/20", icon: AlertTriangle },
  warning: { color: "bg-orange-500/10 text-orange-400 border-orange-500/20", icon: AlertTriangle },
  critical: { color: "bg-red-500/10 text-red-400 border-red-500/20", icon: AlertTriangle }
};

export default function Analytics() {
  const [overview, setOverview] = useState(null);
  const [trends, setTrends] = useState(null);
  const [insights, setInsights] = useState(null);
  const [fatigueShield, setFatigueShield] = useState(null);
  const [loading, setLoading] = useState(true);
  const [loadingInsights, setLoadingInsights] = useState(false);
  const [activeTab, setActiveTab] = useState("overview");
  const { toast } = useToast();

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem("thook_token");
      const headers = { Authorization: `Bearer ${token}` };

      const [overviewRes, trendsRes, fatigueRes] = await Promise.all([
        fetch(`${BACKEND_URL}/api/analytics/overview?days=30`, { headers }),
        fetch(`${BACKEND_URL}/api/analytics/trends?days=30&granularity=week`, { headers }),
        fetch(`${BACKEND_URL}/api/analytics/fatigue-shield`, { headers })
      ]);

      if (overviewRes.ok) setOverview(await overviewRes.json());
      if (trendsRes.ok) setTrends(await trendsRes.json());
      if (fatigueRes.ok) setFatigueShield(await fatigueRes.json());
    } catch (err) {
      console.error("Fetch error:", err);
      toast({ title: "Error", description: "Failed to load analytics", variant: "destructive" });
    } finally {
      setLoading(false);
    }
  };

  const fetchInsights = async () => {
    setLoadingInsights(true);
    try {
      const token = localStorage.getItem("thook_token");
      const res = await fetch(`${BACKEND_URL}/api/analytics/insights?days=30`, {
        headers: { Authorization: `Bearer ${token}` }
      });

      if (!res.ok) throw new Error("Failed to fetch insights");
      const data = await res.json();
      setInsights(data);
    } catch (err) {
      console.error("Insights error:", err);
      toast({ title: "Error", description: "Failed to generate insights", variant: "destructive" });
    } finally {
      setLoadingInsights(false);
    }
  };

  if (loading) {
    return (
      <main className="p-6">
        <div className="max-w-6xl mx-auto">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-32 bg-surface-2 rounded-2xl animate-pulse" />
            ))}
          </div>
          <div className="h-96 bg-surface-2 rounded-2xl animate-pulse" />
        </div>
      </main>
    );
  }

  const hasData = overview?.has_data;
  const summary = overview?.summary || {};
  const trendConfig = TREND_ICONS[trends?.trend] || TREND_ICONS.insufficient_data;
  const TrendIcon = trendConfig.icon;

  return (
    <main className="p-6">
      <div className="max-w-6xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-display font-bold text-white flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-violet/10 flex items-center justify-center">
                <BarChart3 className="text-violet" size={20} />
              </div>
              Analytics
            </h1>
            <p className="text-zinc-400 mt-1">Performance intelligence and insights</p>
          </div>
          <div className="flex gap-3">
            <Button variant="outline" onClick={fetchData} className="gap-2">
              <RefreshCw size={14} />
              Refresh
            </Button>
            <Button
              onClick={fetchInsights}
              disabled={loadingInsights || !hasData}
              className="bg-violet text-white hover:bg-violet/90 gap-2"
            >
              {loadingInsights ? (
                <RefreshCw size={14} className="animate-spin" />
              ) : (
                <Sparkles size={14} />
              )}
              Generate Insights
            </Button>
          </div>
        </div>

        {!hasData ? (
          <Card className="bg-surface-2 border-white/5">
            <CardContent className="py-12 text-center">
              <BarChart3 className="mx-auto text-zinc-600 mb-3" size={48} />
              <h3 className="text-white font-semibold mb-2">No Analytics Data Yet</h3>
              <p className="text-zinc-500">Create and approve some content to see performance analytics</p>
            </CardContent>
          </Card>
        ) : (
          <>
            {/* Summary Cards */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <Card className="bg-surface-2 border-white/5">
                <CardContent className="py-4">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs text-zinc-500">Total Posts</span>
                    <LineChart size={14} className="text-zinc-600" />
                  </div>
                  <p className="text-2xl font-bold text-white">{summary.total_posts || 0}</p>
                  <p className="text-xs text-zinc-500 mt-1">Last 30 days</p>
                </CardContent>
              </Card>

              <Card className="bg-surface-2 border-white/5">
                <CardContent className="py-4">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs text-zinc-500">Total Impressions</span>
                    <Eye size={14} className="text-zinc-600" />
                  </div>
                  <p className="text-2xl font-bold text-white">
                    {summary.total_impressions?.toLocaleString() || 0}
                  </p>
                  <p className="text-xs text-zinc-500 mt-1">Reach across platforms</p>
                </CardContent>
              </Card>

              <Card className="bg-surface-2 border-white/5">
                <CardContent className="py-4">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs text-zinc-500">Avg Performance</span>
                    <Target size={14} className="text-zinc-600" />
                  </div>
                  <p className="text-2xl font-bold text-white">{summary.avg_performance_score || 0}</p>
                  <p className="text-xs text-zinc-500 mt-1">Score out of 100</p>
                </CardContent>
              </Card>

              <Card className="bg-surface-2 border-white/5">
                <CardContent className="py-4">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs text-zinc-500">Engagement Rate</span>
                    <Heart size={14} className="text-zinc-600" />
                  </div>
                  <p className="text-2xl font-bold text-white">
                    {((summary.overall_engagement_rate || 0) * 100).toFixed(2)}%
                  </p>
                  <div className={`flex items-center gap-1 mt-1 ${trendConfig.color}`}>
                    <TrendIcon size={12} />
                    <span className="text-xs capitalize">{trends?.trend || "stable"}</span>
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Fatigue Shield */}
            {fatigueShield && (
              <Card className={`border ${SHIELD_STATUS_CONFIG[fatigueShield.shield_status]?.color || "border-white/5"}`}>
                <CardContent className="py-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                      <div className={`w-12 h-12 rounded-xl ${SHIELD_STATUS_CONFIG[fatigueShield.shield_status]?.color?.split(" ")[0]} flex items-center justify-center`}>
                        <Shield size={24} className={SHIELD_STATUS_CONFIG[fatigueShield.shield_status]?.color?.split(" ")[1]} />
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <h3 className="text-white font-semibold">Pattern Fatigue Shield</h3>
                          <Badge className={SHIELD_STATUS_CONFIG[fatigueShield.shield_status]?.color}>
                            {fatigueShield.shield_status?.toUpperCase()}
                          </Badge>
                        </div>
                        <p className="text-sm text-zinc-400 mt-1">{fatigueShield.shield_message}</p>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className="text-3xl font-bold text-white">{fatigueShield.fatigue_risk_score}</p>
                      <p className="text-xs text-zinc-500">Risk Score</p>
                    </div>
                  </div>

                  {fatigueShield.recommendations?.length > 0 && (
                    <div className="mt-4 pt-4 border-t border-white/5">
                      <p className="text-xs text-zinc-500 mb-2">Recommendations:</p>
                      <div className="flex flex-wrap gap-2">
                        {fatigueShield.recommendations.slice(0, 3).map((rec, i) => (
                          <span key={i} className="text-xs px-3 py-1.5 bg-white/5 text-zinc-300 rounded-lg">
                            {rec}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>
            )}

            {/* AI Insights */}
            <AnimatePresence>
              {insights?.has_insights && (
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -20 }}
                >
                  <Card className="bg-violet/5 border-violet/20">
                    <CardHeader>
                      <CardTitle className="text-white flex items-center gap-2">
                        <Brain size={18} className="text-violet" />
                        AI-Powered Insights
                      </CardTitle>
                      <CardDescription>{insights.summary}</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                      {/* Key Insights */}
                      <div>
                        <p className="text-xs text-zinc-500 mb-2">Key Insights</p>
                        <div className="space-y-2">
                          {insights.key_insights?.map((insight, i) => (
                            <div key={i} className="flex items-start gap-2">
                              <Lightbulb size={14} className="text-yellow-400 mt-0.5 flex-shrink-0" />
                              <p className="text-sm text-zinc-300">{insight}</p>
                            </div>
                          ))}
                        </div>
                      </div>

                      {/* Recommendations */}
                      {insights.recommendations?.length > 0 && (
                        <div>
                          <p className="text-xs text-zinc-500 mb-2">Recommendations</p>
                          <div className="space-y-2">
                            {insights.recommendations.map((rec, i) => (
                              <div key={i} className="p-3 bg-white/5 rounded-lg">
                                <div className="flex items-center gap-2 mb-1">
                                  <Badge className={
                                    rec.priority === "high" ? "bg-red-500/20 text-red-400" :
                                    rec.priority === "medium" ? "bg-yellow-500/20 text-yellow-400" :
                                    "bg-green-500/20 text-green-400"
                                  }>
                                    {rec.priority}
                                  </Badge>
                                </div>
                                <p className="text-sm text-white">{rec.action}</p>
                                <p className="text-xs text-zinc-500 mt-1">{rec.expected_impact}</p>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* 30-Day Focus */}
                      {insights.next_30_day_focus && (
                        <div className="p-3 bg-lime/10 border border-lime/20 rounded-lg">
                          <p className="text-xs text-lime mb-1">30-Day Strategic Focus</p>
                          <p className="text-sm text-white">{insights.next_30_day_focus}</p>
                        </div>
                      )}
                    </CardContent>
                  </Card>
                </motion.div>
              )}
            </AnimatePresence>

            {/* Platform Breakdown */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {Object.entries(overview?.by_platform || {}).map(([platform, stats]) => {
                const config = PLATFORM_CONFIG[platform] || PLATFORM_CONFIG.linkedin;
                const PlatformIcon = config.icon;

                return (
                  <Card key={platform} className="bg-surface-2 border-white/5">
                    <CardContent className="py-4">
                      <div className="flex items-center gap-3 mb-4">
                        <div className={`w-10 h-10 rounded-xl ${config.color} flex items-center justify-center`}>
                          <PlatformIcon size={18} className="text-white" />
                        </div>
                        <div>
                          <h3 className="text-white font-medium">{config.name}</h3>
                          <p className="text-xs text-zinc-500">{stats.total_posts} posts</p>
                        </div>
                      </div>

                      <div className="space-y-3">
                        <div className="flex justify-between">
                          <span className="text-xs text-zinc-500">Impressions</span>
                          <span className="text-sm text-white">{stats.total_impressions?.toLocaleString()}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-xs text-zinc-500">Engagements</span>
                          <span className="text-sm text-white">{stats.total_engagements?.toLocaleString()}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-xs text-zinc-500">Avg Engagement</span>
                          <span className="text-sm text-lime">{((stats.avg_engagement_rate || 0) * 100).toFixed(2)}%</span>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                );
              })}
            </div>

            {/* Top Performing Content */}
            {overview?.top_performing?.length > 0 && (
              <Card className="bg-surface-2 border-white/5">
                <CardHeader>
                  <CardTitle className="text-white flex items-center gap-2">
                    <TrendingUp size={18} className="text-green-400" />
                    Top Performing Content
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    {overview.top_performing.slice(0, 5).map((content, i) => {
                      const config = PLATFORM_CONFIG[content.platform] || PLATFORM_CONFIG.linkedin;
                      const PlatformIcon = config.icon;

                      return (
                        <div key={i} className="flex items-center gap-4 p-3 bg-white/5 rounded-lg">
                          <span className="text-lg font-bold text-zinc-600 w-6">#{i + 1}</span>
                          <div className={`w-8 h-8 rounded-lg ${config.color} flex items-center justify-center`}>
                            <PlatformIcon size={14} className="text-white" />
                          </div>
                          <div className="flex-1 min-w-0">
                            <p className="text-sm text-white truncate">{content.preview}</p>
                            <p className="text-xs text-zinc-500">
                              {content.impressions?.toLocaleString()} impressions • {((content.engagement_rate || 0) * 100).toFixed(2)}% engagement
                            </p>
                          </div>
                          <div className="text-right">
                            <p className="text-lg font-bold text-lime">{content.score}</p>
                            <p className="text-xs text-zinc-500">score</p>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </CardContent>
              </Card>
            )}
          </>
        )}
      </div>
    </main>
  );
}
