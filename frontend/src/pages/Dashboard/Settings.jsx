import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useToast } from "@/hooks/use-toast";
import {
  Settings as SettingsIcon, CreditCard, Zap, Crown, Building2, Users,
  ChevronRight, Check, RefreshCw, AlertTriangle, Sparkles, TrendingUp,
  Calendar, Shield, Mic, Video, Code, BarChart3
} from "lucide-react";

const BACKEND_URL = import.meta.env.REACT_APP_BACKEND_URL || process.env.REACT_APP_BACKEND_URL;

const TIER_ICONS = {
  free: Zap,
  pro: Sparkles,
  studio: Crown,
  agency: Building2
};

const TIER_COLORS = {
  free: "bg-zinc-500/10 text-zinc-400 border-zinc-500/20",
  pro: "bg-violet/10 text-violet border-violet/20",
  studio: "bg-lime/10 text-lime border-lime/20",
  agency: "bg-orange-500/10 text-orange-400 border-orange-500/20"
};

export default function Settings() {
  const [subscription, setSubscription] = useState(null);
  const [credits, setCredits] = useState(null);
  const [tiers, setTiers] = useState([]);
  const [limits, setLimits] = useState(null);
  const [loading, setLoading] = useState(true);
  const [upgrading, setUpgrading] = useState(false);
  const { toast } = useToast();

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem("thook_token");
      const headers = { Authorization: `Bearer ${token}` };

      const [subRes, creditsRes, tiersRes, limitsRes] = await Promise.all([
        fetch(`${BACKEND_URL}/api/billing/subscription`, { headers }),
        fetch(`${BACKEND_URL}/api/billing/credits`, { headers }),
        fetch(`${BACKEND_URL}/api/billing/subscription/tiers`, { headers }),
        fetch(`${BACKEND_URL}/api/billing/subscription/limits`, { headers })
      ]);

      if (subRes.ok) setSubscription(await subRes.json());
      if (creditsRes.ok) setCredits(await creditsRes.json());
      if (tiersRes.ok) {
        const data = await tiersRes.json();
        setTiers(data.tiers || []);
      }
      if (limitsRes.ok) setLimits(await limitsRes.json());
    } catch (err) {
      console.error("Fetch error:", err);
      toast({ title: "Error", description: "Failed to load settings", variant: "destructive" });
    } finally {
      setLoading(false);
    }
  };

  const handleUpgrade = async (tierId) => {
    setUpgrading(true);
    try {
      const token = localStorage.getItem("thook_token");
      const res = await fetch(`${BACKEND_URL}/api/billing/subscription/upgrade`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ tier: tierId, billing_period: "monthly" })
      });

      const data = await res.json();

      if (res.ok) {
        toast({
          title: data.is_upgrade ? "Upgraded!" : "Plan Changed",
          description: data.message
        });
        fetchData();
      } else {
        throw new Error(data.detail || "Upgrade failed");
      }
    } catch (err) {
      toast({ title: "Error", description: err.message, variant: "destructive" });
    } finally {
      setUpgrading(false);
    }
  };

  if (loading) {
    return (
      <main className="p-6">
        <div className="max-w-5xl mx-auto">
          <div className="space-y-4">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-48 bg-surface-2 rounded-2xl animate-pulse" />
            ))}
          </div>
        </div>
      </main>
    );
  }

  const TierIcon = TIER_ICONS[subscription?.tier] || Zap;

  return (
    <main className="p-6">
      <div className="max-w-5xl mx-auto space-y-8">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-display font-bold text-white flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-white/5 flex items-center justify-center">
                <SettingsIcon className="text-zinc-400" size={20} />
              </div>
              Settings
            </h1>
            <p className="text-zinc-400 mt-1">Manage your subscription and billing</p>
          </div>
          <Button variant="outline" onClick={fetchData} className="gap-2">
            <RefreshCw size={14} />
            Refresh
          </Button>
        </div>

        {/* Current Plan Card */}
        <Card className="bg-surface-2 border-white/5 overflow-hidden">
          <div className={`h-1 ${subscription?.tier === "agency" ? "bg-orange-500" : subscription?.tier === "studio" ? "bg-lime" : subscription?.tier === "pro" ? "bg-violet" : "bg-zinc-600"}`} />
          <CardContent className="py-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className={`w-14 h-14 rounded-xl ${TIER_COLORS[subscription?.tier]?.split(" ")[0]} flex items-center justify-center`}>
                  <TierIcon size={24} className={TIER_COLORS[subscription?.tier]?.split(" ")[1]} />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <h2 className="text-xl font-semibold text-white">{subscription?.tier_name} Plan</h2>
                    <Badge className={TIER_COLORS[subscription?.tier]}>
                      {subscription?.is_active ? "Active" : "Expired"}
                    </Badge>
                  </div>
                  <p className="text-sm text-zinc-500 mt-1">
                    {subscription?.price_monthly === 0 
                      ? "Free forever" 
                      : `$${subscription?.price_monthly}/month`}
                  </p>
                </div>
              </div>
              
              {/* Credits Display */}
              <div className="text-right">
                <p className="text-3xl font-bold text-white">{credits?.credits || 0}</p>
                <p className="text-sm text-zinc-500">
                  of {credits?.monthly_allowance || 0} credits
                </p>
                {credits?.is_low_balance && (
                  <div className="flex items-center gap-1 text-orange-400 text-xs mt-1">
                    <AlertTriangle size={12} />
                    Low balance
                  </div>
                )}
              </div>
            </div>

            {/* Credit Bar */}
            <div className="mt-6">
              <div className="flex justify-between text-xs text-zinc-500 mb-1">
                <span>Credits used this period</span>
                <span>{credits?.used_this_period || 0} / {credits?.monthly_allowance || 0}</span>
              </div>
              <div className="h-2 bg-white/5 rounded-full overflow-hidden">
                <div 
                  className={`h-full rounded-full transition-all ${credits?.is_low_balance ? "bg-orange-500" : "bg-lime"}`}
                  style={{ 
                    width: `${Math.min(100, ((credits?.used_this_period || 0) / (credits?.monthly_allowance || 1)) * 100)}%` 
                  }}
                />
              </div>
              {credits?.next_refresh && (
                <p className="text-xs text-zinc-600 mt-2">
                  Credits refresh: {new Date(credits.next_refresh).toLocaleDateString()}
                </p>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Feature Limits */}
        {limits && (
          <Card className="bg-surface-2 border-white/5">
            <CardHeader>
              <CardTitle className="text-white flex items-center gap-2">
                <BarChart3 size={18} />
                Your Limits
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="p-3 bg-white/5 rounded-lg">
                  <p className="text-xs text-zinc-500">Content/Day</p>
                  <p className="text-lg font-semibold text-white">
                    {limits.limits?.content_per_day?.used || 0}/{limits.limits?.content_per_day?.limit || 0}
                  </p>
                </div>
                <div className="p-3 bg-white/5 rounded-lg">
                  <p className="text-xs text-zinc-500">Personas</p>
                  <p className="text-lg font-semibold text-white">
                    {limits.limits?.max_personas?.used || 0}/{limits.limits?.max_personas?.limit || 0}
                  </p>
                </div>
                <div className="p-3 bg-white/5 rounded-lg">
                  <p className="text-xs text-zinc-500">Team Members</p>
                  <p className="text-lg font-semibold text-white">
                    {limits.limits?.team_members?.used || 0}/{limits.limits?.team_members?.limit || 0}
                  </p>
                </div>
                <div className="p-3 bg-white/5 rounded-lg">
                  <p className="text-xs text-zinc-500">Analytics Days</p>
                  <p className="text-lg font-semibold text-white">
                    {limits.limits?.analytics_days || 0}
                  </p>
                </div>
              </div>

              {/* Feature Access */}
              <div className="mt-4 pt-4 border-t border-white/5">
                <p className="text-xs text-zinc-500 mb-3">Feature Access</p>
                <div className="flex flex-wrap gap-2">
                  {limits.feature_access?.series_enabled && (
                    <Badge variant="outline" className="text-lime border-lime/30 gap-1">
                      <Check size={10} /> Series
                    </Badge>
                  )}
                  {limits.feature_access?.repurpose_enabled && (
                    <Badge variant="outline" className="text-lime border-lime/30 gap-1">
                      <Check size={10} /> Repurpose
                    </Badge>
                  )}
                  {limits.feature_access?.voice_enabled && (
                    <Badge variant="outline" className="text-lime border-lime/30 gap-1">
                      <Mic size={10} /> Voice
                    </Badge>
                  )}
                  {limits.feature_access?.video_enabled && (
                    <Badge variant="outline" className="text-lime border-lime/30 gap-1">
                      <Video size={10} /> Video
                    </Badge>
                  )}
                  {limits.feature_access?.api_access && (
                    <Badge variant="outline" className="text-lime border-lime/30 gap-1">
                      <Code size={10} /> API
                    </Badge>
                  )}
                  {limits.feature_access?.priority_support && (
                    <Badge variant="outline" className="text-lime border-lime/30 gap-1">
                      <Shield size={10} /> Priority Support
                    </Badge>
                  )}
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Available Plans */}
        <div>
          <h2 className="text-lg font-semibold text-white mb-4">Available Plans</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {tiers.map((tier) => {
              const Icon = TIER_ICONS[tier.id] || Zap;
              const isCurrent = tier.is_current;
              
              return (
                <Card 
                  key={tier.id} 
                  className={`bg-surface-2 border-white/5 ${isCurrent ? "ring-2 ring-lime/50" : ""}`}
                >
                  <CardContent className="py-6">
                    <div className={`w-12 h-12 rounded-xl ${TIER_COLORS[tier.id]?.split(" ")[0]} flex items-center justify-center mb-4`}>
                      <Icon size={20} className={TIER_COLORS[tier.id]?.split(" ")[1]} />
                    </div>
                    
                    <h3 className="text-lg font-semibold text-white">{tier.name}</h3>
                    <div className="flex items-baseline gap-1 mt-1">
                      <span className="text-2xl font-bold text-white">
                        ${tier.price_monthly}
                      </span>
                      {tier.price_monthly > 0 && (
                        <span className="text-sm text-zinc-500">/mo</span>
                      )}
                    </div>
                    
                    <p className="text-sm text-zinc-400 mt-2">
                      {tier.monthly_credits.toLocaleString()} credits/month
                    </p>

                    <div className="mt-4 space-y-2">
                      <div className="flex items-center gap-2 text-xs text-zinc-400">
                        <Check size={12} className="text-lime" />
                        {tier.features.content_per_day} posts/day
                      </div>
                      <div className="flex items-center gap-2 text-xs text-zinc-400">
                        <Check size={12} className="text-lime" />
                        {tier.features.max_personas} persona{tier.features.max_personas > 1 ? "s" : ""}
                      </div>
                      <div className="flex items-center gap-2 text-xs text-zinc-400">
                        <Check size={12} className="text-lime" />
                        {tier.features.platforms.length} platform{tier.features.platforms.length > 1 ? "s" : ""}
                      </div>
                      {tier.features.voice_enabled && (
                        <div className="flex items-center gap-2 text-xs text-zinc-400">
                          <Check size={12} className="text-lime" />
                          Voice narration
                        </div>
                      )}
                      {tier.features.video_enabled && (
                        <div className="flex items-center gap-2 text-xs text-zinc-400">
                          <Check size={12} className="text-lime" />
                          Video generation
                        </div>
                      )}
                    </div>

                    <Button
                      onClick={() => handleUpgrade(tier.id)}
                      disabled={isCurrent || upgrading}
                      className={`w-full mt-4 ${
                        isCurrent 
                          ? "bg-white/5 text-zinc-500" 
                          : tier.is_upgrade 
                            ? "bg-lime text-black hover:bg-lime/90" 
                            : "bg-white/10 text-white hover:bg-white/20"
                      }`}
                    >
                      {isCurrent 
                        ? "Current Plan" 
                        : tier.is_upgrade 
                          ? "Upgrade" 
                          : "Downgrade"}
                    </Button>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        </div>
      </div>
    </main>
  );
}
