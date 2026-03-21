import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useToast } from "@/hooks/use-toast";
import {
  Settings as SettingsIcon, CreditCard, Zap, Crown, Building2, Users,
  ChevronRight, Check, RefreshCw, AlertTriangle, Sparkles, TrendingUp,
  Calendar, Shield, Mic, Video, Code, BarChart3, ExternalLink, 
  ShoppingCart, Gift, Percent, ArrowRight, Clock, Star, X
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

const TIER_GRADIENTS = {
  free: "from-zinc-500/20 to-zinc-600/20",
  pro: "from-violet/20 to-purple-600/20",
  studio: "from-lime/20 to-green-500/20",
  agency: "from-orange-500/20 to-red-500/20"
};

// Credit costs for reference
const CREDIT_COSTS = {
  content_create: { credits: 10, name: "Content Creation" },
  content_regenerate: { credits: 4, name: "Regenerate" },
  image_generate: { credits: 8, name: "Image Generation" },
  carousel_generate: { credits: 15, name: "Carousel" },
  voice_narration: { credits: 12, name: "Voice Narration" },
  video_generate: { credits: 50, name: "Video Generation" },
  repurpose: { credits: 3, name: "Repurpose" },
  series_plan: { credits: 6, name: "Series Plan" },
  ai_insights: { credits: 2, name: "AI Insights" },
  viral_predict: { credits: 1, name: "Viral Predict" }
};

export default function Settings() {
  const [subscription, setSubscription] = useState(null);
  const [credits, setCredits] = useState(null);
  const [tiers, setTiers] = useState([]);
  const [limits, setLimits] = useState(null);
  const [billingConfig, setBillingConfig] = useState(null);
  const [creditCosts, setCreditCosts] = useState(null);
  const [loading, setLoading] = useState(true);
  const [upgrading, setUpgrading] = useState(null);
  const [showCreditModal, setShowCreditModal] = useState(false);
  const [billingPeriod, setBillingPeriod] = useState("monthly");
  const { toast } = useToast();

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem("thook_token");
      const headers = { Authorization: `Bearer ${token}` };

      const [subRes, creditsRes, tiersRes, limitsRes, configRes, costsRes] = await Promise.all([
        fetch(`${BACKEND_URL}/api/billing/subscription`, { headers }),
        fetch(`${BACKEND_URL}/api/billing/credits`, { headers }),
        fetch(`${BACKEND_URL}/api/billing/subscription/tiers`, { headers }),
        fetch(`${BACKEND_URL}/api/billing/subscription/limits`, { headers }),
        fetch(`${BACKEND_URL}/api/billing/config`),
        fetch(`${BACKEND_URL}/api/billing/credits/costs`)
      ]);

      if (subRes.ok) setSubscription(await subRes.json());
      if (creditsRes.ok) setCredits(await creditsRes.json());
      if (tiersRes.ok) {
        const data = await tiersRes.json();
        setTiers(data.tiers || []);
      }
      if (limitsRes.ok) setLimits(await limitsRes.json());
      if (configRes.ok) setBillingConfig(await configRes.json());
      if (costsRes.ok) setCreditCosts(await costsRes.json());
    } catch (err) {
      console.error("Fetch error:", err);
      toast({ title: "Error", description: "Failed to load settings", variant: "destructive" });
    } finally {
      setLoading(false);
    }
  };

  const handleUpgrade = async (tierId) => {
    if (tierId === "free") {
      // Direct downgrade to free
      await handleDirectUpgrade(tierId);
      return;
    }

    setUpgrading(tierId);
    try {
      const token = localStorage.getItem("thook_token");
      const res = await fetch(`${BACKEND_URL}/api/billing/subscription/checkout`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ tier: tierId, billing_period: billingPeriod })
      });

      const data = await res.json();

      if (res.ok) {
        if (data.checkout_url) {
          // Redirect to Stripe checkout or simulated
          if (data.simulated) {
            toast({
              title: "Demo Mode",
              description: "Stripe not configured. Using simulated checkout."
            });
            // Simulate the upgrade
            await handleDirectUpgrade(tierId);
          } else {
            window.location.href = data.checkout_url;
          }
        } else {
          toast({ title: "Success", description: data.message });
          fetchData();
        }
      } else {
        throw new Error(data.detail || "Checkout failed");
      }
    } catch (err) {
      toast({ title: "Error", description: err.message, variant: "destructive" });
    } finally {
      setUpgrading(null);
    }
  };

  const handleDirectUpgrade = async (tierId) => {
    try {
      const token = localStorage.getItem("thook_token");
      const res = await fetch(`${BACKEND_URL}/api/billing/simulate/upgrade`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ tier: tierId, billing_period: billingPeriod })
      });

      const data = await res.json();

      if (res.ok) {
        toast({
          title: data.simulated ? "Demo Upgrade Complete!" : "Upgraded!",
          description: `You now have ${data.credits} credits on the ${tierId} plan.`
        });
        fetchData();
      } else {
        throw new Error(data.detail || "Upgrade failed");
      }
    } catch (err) {
      toast({ title: "Error", description: err.message, variant: "destructive" });
    } finally {
      setUpgrading(null);
    }
  };

  const handleBuyCredits = async (packageName) => {
    try {
      const token = localStorage.getItem("thook_token");
      const res = await fetch(`${BACKEND_URL}/api/billing/credits/checkout`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ package: packageName })
      });

      const data = await res.json();

      if (res.ok) {
        if (data.simulated) {
          // Simulate adding credits
          const addRes = await fetch(`${BACKEND_URL}/api/billing/simulate/credits?amount=${data.credits}`, {
            method: "POST",
            headers: { Authorization: `Bearer ${token}` }
          });
          
          if (addRes.ok) {
            toast({
              title: "Credits Added!",
              description: `${data.credits} credits have been added to your account (demo mode).`
            });
            setShowCreditModal(false);
            fetchData();
          }
        } else if (data.checkout_url) {
          window.location.href = data.checkout_url;
        }
      } else {
        throw new Error(data.detail || "Purchase failed");
      }
    } catch (err) {
      toast({ title: "Error", description: err.message, variant: "destructive" });
    }
  };

  const handleManageBilling = async () => {
    try {
      const token = localStorage.getItem("thook_token");
      const res = await fetch(`${BACKEND_URL}/api/billing/portal`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` }
      });

      const data = await res.json();

      if (res.ok && data.portal_url) {
        if (data.simulated) {
          toast({
            title: "Demo Mode",
            description: "Stripe Customer Portal not available in demo mode."
          });
        } else {
          window.open(data.portal_url, '_blank');
        }
      }
    } catch (err) {
      toast({ title: "Error", description: "Could not open billing portal", variant: "destructive" });
    }
  };

  if (loading) {
    return (
      <main className="p-6">
        <div className="max-w-6xl mx-auto">
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
  const creditPackages = billingConfig?.credit_packages || {};

  return (
    <main className="p-6">
      <div className="max-w-6xl mx-auto space-y-8">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-display font-bold text-white flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-white/5 flex items-center justify-center">
                <SettingsIcon className="text-zinc-400" size={20} />
              </div>
              Billing & Subscription
            </h1>
            <p className="text-zinc-400 mt-1">Manage your plan, credits, and billing</p>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" onClick={handleManageBilling} className="gap-2">
              <CreditCard size={14} />
              Manage Billing
            </Button>
            <Button variant="outline" onClick={fetchData} className="gap-2">
              <RefreshCw size={14} />
              Refresh
            </Button>
          </div>
        </div>

        {/* Early Bird Banner */}
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-gradient-to-r from-lime/20 via-lime/10 to-transparent border border-lime/20 rounded-2xl p-4 flex items-center justify-between"
        >
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-lime/20 flex items-center justify-center">
              <Gift className="text-lime" size={20} />
            </div>
            <div>
              <p className="text-white font-medium flex items-center gap-2">
                <Star className="text-lime" size={14} />
                Early Bird Pricing Active!
              </p>
              <p className="text-sm text-zinc-400">Save up to 35% on all plans - limited time offer</p>
            </div>
          </div>
          <Badge className="bg-lime/20 text-lime border-lime/30">
            <Percent size={12} className="mr-1" />
            35% OFF
          </Badge>
        </motion.div>

        {/* Current Plan + Credits Row */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Current Plan Card */}
          <Card className="lg:col-span-2 bg-surface-2 border-white/5 overflow-hidden">
            <div className={`h-1 bg-gradient-to-r ${TIER_GRADIENTS[subscription?.tier] || TIER_GRADIENTS.free}`} />
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
                      {subscription?.stripe_status && (
                        <span className="ml-2 text-xs text-zinc-600">
                          • Stripe: {subscription.stripe_status}
                        </span>
                      )}
                    </p>
                  </div>
                </div>
                
                {subscription?.cancel_at_period_end && (
                  <Badge variant="outline" className="text-orange-400 border-orange-400/30">
                    <AlertTriangle size={12} className="mr-1" />
                    Cancels at period end
                  </Badge>
                )}
              </div>

              {/* Feature Access Quick View */}
              <div className="mt-6 pt-4 border-t border-white/5">
                <p className="text-xs text-zinc-500 mb-3">Your Features</p>
                <div className="flex flex-wrap gap-2">
                  {limits?.feature_access?.series_enabled && (
                    <Badge variant="outline" className="text-lime border-lime/30 gap-1">
                      <Check size={10} /> Series
                    </Badge>
                  )}
                  {limits?.feature_access?.repurpose_enabled && (
                    <Badge variant="outline" className="text-lime border-lime/30 gap-1">
                      <Check size={10} /> Repurpose
                    </Badge>
                  )}
                  {limits?.feature_access?.voice_enabled && (
                    <Badge variant="outline" className="text-lime border-lime/30 gap-1">
                      <Mic size={10} /> Voice
                    </Badge>
                  )}
                  {limits?.feature_access?.video_enabled && (
                    <Badge variant="outline" className="text-lime border-lime/30 gap-1">
                      <Video size={10} /> Video
                    </Badge>
                  )}
                  {limits?.feature_access?.api_access && (
                    <Badge variant="outline" className="text-lime border-lime/30 gap-1">
                      <Code size={10} /> API
                    </Badge>
                  )}
                  {limits?.feature_access?.priority_support && (
                    <Badge variant="outline" className="text-lime border-lime/30 gap-1">
                      <Shield size={10} /> Priority Support
                    </Badge>
                  )}
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Credits Card */}
          <Card className="bg-surface-2 border-white/5">
            <CardContent className="py-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-sm font-medium text-zinc-400">Credits Balance</h3>
                <Button 
                  size="sm" 
                  variant="outline" 
                  onClick={() => setShowCreditModal(true)}
                  className="gap-1 text-xs"
                >
                  <ShoppingCart size={12} />
                  Buy More
                </Button>
              </div>
              
              <div className="text-center py-4">
                <p className="text-4xl font-bold text-white">{credits?.credits || 0}</p>
                <p className="text-sm text-zinc-500 mt-1">
                  of {credits?.monthly_allowance || 0} monthly
                </p>
              </div>

              {/* Credit Bar */}
              <div className="mt-4">
                <div className="h-2 bg-white/5 rounded-full overflow-hidden">
                  <div 
                    className={`h-full rounded-full transition-all ${
                      credits?.is_low_balance ? "bg-orange-500" : "bg-lime"
                    }`}
                    style={{ 
                      width: `${Math.min(100, ((credits?.credits || 0) / (credits?.monthly_allowance || 1)) * 100)}%` 
                    }}
                  />
                </div>
              </div>

              {credits?.is_low_balance && (
                <div className="flex items-center justify-center gap-1 text-orange-400 text-xs mt-3">
                  <AlertTriangle size={12} />
                  Low balance - consider buying more
                </div>
              )}

              {credits?.next_refresh && (
                <div className="flex items-center justify-center gap-1 text-zinc-600 text-xs mt-2">
                  <Clock size={12} />
                  Refreshes: {new Date(credits.next_refresh).toLocaleDateString()}
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Usage Limits */}
        {limits && (
          <Card className="bg-surface-2 border-white/5">
            <CardHeader className="pb-2">
              <CardTitle className="text-white text-base flex items-center gap-2">
                <BarChart3 size={16} />
                Usage Limits
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
            </CardContent>
          </Card>
        )}

        {/* Credit Costs Reference */}
        <Card className="bg-surface-2 border-white/5">
          <CardHeader className="pb-2">
            <CardTitle className="text-white text-base flex items-center gap-2">
              <Zap size={16} />
              Credit Costs
            </CardTitle>
            <CardDescription>How many credits each operation uses</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
              {creditCosts?.costs && Object.entries(creditCosts.costs).map(([key, value]) => (
                <div key={key} className="p-3 bg-white/5 rounded-lg text-center">
                  <p className="text-lg font-bold text-lime">{value.credits}</p>
                  <p className="text-xs text-zinc-400 mt-1">{value.name}</p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Billing Period Toggle */}
        <div className="flex items-center justify-center gap-4">
          <span className={`text-sm ${billingPeriod === "monthly" ? "text-white" : "text-zinc-500"}`}>
            Monthly
          </span>
          <button
            onClick={() => setBillingPeriod(billingPeriod === "monthly" ? "annual" : "monthly")}
            className={`w-14 h-7 rounded-full p-1 transition-colors ${
              billingPeriod === "annual" ? "bg-lime" : "bg-white/10"
            }`}
          >
            <div className={`w-5 h-5 rounded-full bg-white transition-transform ${
              billingPeriod === "annual" ? "translate-x-7" : ""
            }`} />
          </button>
          <span className={`text-sm ${billingPeriod === "annual" ? "text-white" : "text-zinc-500"}`}>
            Annual
            <Badge className="ml-2 bg-lime/20 text-lime text-xs">Save 20%</Badge>
          </span>
        </div>

        {/* Available Plans */}
        <div>
          <h2 className="text-lg font-semibold text-white mb-4">Choose Your Plan</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {tiers.map((tier) => {
              const Icon = TIER_ICONS[tier.id] || Zap;
              const isCurrent = tier.is_current;
              const isPopular = tier.id === "pro";
              const price = billingPeriod === "annual" 
                ? (tier.price_annual || tier.price_monthly * 12 * 0.8) 
                : tier.price_monthly;
              
              return (
                <Card 
                  key={tier.id} 
                  className={`bg-surface-2 border-white/5 relative overflow-hidden ${
                    isCurrent ? "ring-2 ring-lime/50" : ""
                  } ${isPopular ? "ring-2 ring-violet/50" : ""}`}
                >
                  {isPopular && (
                    <div className="absolute top-0 right-0 bg-violet text-white text-xs px-3 py-1 rounded-bl-lg">
                      Most Popular
                    </div>
                  )}
                  <CardContent className="py-6">
                    <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${TIER_GRADIENTS[tier.id]} flex items-center justify-center mb-4`}>
                      <Icon size={20} className={TIER_COLORS[tier.id]?.split(" ")[1]} />
                    </div>
                    
                    <h3 className="text-lg font-semibold text-white">{tier.name}</h3>
                    <div className="flex items-baseline gap-1 mt-1">
                      <span className="text-3xl font-bold text-white">
                        ${billingPeriod === "annual" ? Math.round(price / 12) : price}
                      </span>
                      {price > 0 && (
                        <span className="text-sm text-zinc-500">/mo</span>
                      )}
                    </div>
                    {billingPeriod === "annual" && price > 0 && (
                      <p className="text-xs text-zinc-500 mt-1">
                        ${price} billed annually
                      </p>
                    )}
                    
                    <p className="text-sm text-lime mt-2 font-medium">
                      {tier.credits_per_month?.toLocaleString() || tier.monthly_credits?.toLocaleString()} credits/month
                    </p>

                    <div className="mt-4 space-y-2">
                      <div className="flex items-center gap-2 text-xs text-zinc-400">
                        <Check size={12} className="text-lime" />
                        {tier.features?.content_per_day || "Unlimited"} posts/day
                      </div>
                      <div className="flex items-center gap-2 text-xs text-zinc-400">
                        <Check size={12} className="text-lime" />
                        {tier.features?.max_personas || 1} persona{(tier.features?.max_personas || 1) > 1 ? "s" : ""}
                      </div>
                      <div className="flex items-center gap-2 text-xs text-zinc-400">
                        <Check size={12} className="text-lime" />
                        {tier.features?.platforms?.length || 1} platform{(tier.features?.platforms?.length || 1) > 1 ? "s" : ""}
                      </div>
                      {tier.features?.voice_enabled && (
                        <div className="flex items-center gap-2 text-xs text-zinc-400">
                          <Check size={12} className="text-lime" />
                          Voice narration
                        </div>
                      )}
                      {tier.features?.video_enabled && (
                        <div className="flex items-center gap-2 text-xs text-zinc-400">
                          <Check size={12} className="text-lime" />
                          Video generation
                        </div>
                      )}
                      {tier.features?.api_access && (
                        <div className="flex items-center gap-2 text-xs text-zinc-400">
                          <Check size={12} className="text-lime" />
                          API access
                        </div>
                      )}
                    </div>

                    <Button
                      onClick={() => handleUpgrade(tier.id)}
                      disabled={isCurrent || upgrading === tier.id}
                      className={`w-full mt-4 gap-2 ${
                        isCurrent 
                          ? "bg-white/5 text-zinc-500" 
                          : tier.is_upgrade 
                            ? "bg-lime text-black hover:bg-lime/90" 
                            : "bg-white/10 text-white hover:bg-white/20"
                      }`}
                    >
                      {upgrading === tier.id ? (
                        <RefreshCw size={14} className="animate-spin" />
                      ) : isCurrent ? (
                        "Current Plan"
                      ) : tier.is_upgrade ? (
                        <>
                          Upgrade
                          <ArrowRight size={14} />
                        </>
                      ) : (
                        "Switch"
                      )}
                    </Button>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        </div>

        {/* Stripe Status Notice */}
        {billingConfig && !billingConfig.configured && (
          <div className="bg-zinc-800/50 border border-zinc-700 rounded-lg p-4 text-center">
            <p className="text-zinc-400 text-sm">
              <AlertTriangle className="inline mr-2" size={14} />
              Demo Mode: Stripe payments not configured. All purchases are simulated.
            </p>
          </div>
        )}
      </div>

      {/* Buy Credits Modal */}
      <AnimatePresence>
        {showCreditModal && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4"
            onClick={() => setShowCreditModal(false)}
          >
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              onClick={(e) => e.stopPropagation()}
              className="bg-surface-1 border border-white/10 rounded-2xl p-6 w-full max-w-lg"
            >
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl font-semibold text-white">Buy Credits</h2>
                <button 
                  onClick={() => setShowCreditModal(false)}
                  className="text-zinc-400 hover:text-white"
                >
                  <X size={20} />
                </button>
              </div>

              <div className="space-y-3">
                {Object.entries(creditPackages).map(([name, pkg]) => (
                  <button
                    key={name}
                    onClick={() => handleBuyCredits(name)}
                    className="w-full p-4 bg-white/5 hover:bg-white/10 border border-white/10 hover:border-lime/30 rounded-xl flex items-center justify-between transition-all"
                  >
                    <div className="flex items-center gap-4">
                      <div className="w-12 h-12 rounded-lg bg-lime/10 flex items-center justify-center">
                        <Zap className="text-lime" size={20} />
                      </div>
                      <div className="text-left">
                        <p className="text-white font-medium">{pkg.credits} Credits</p>
                        <p className="text-xs text-zinc-500">
                          ~{Math.round(pkg.credits / 10)} content pieces
                        </p>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className="text-lg font-bold text-white">${pkg.price}</p>
                      <p className="text-xs text-zinc-500">
                        ${(pkg.price / pkg.credits * 10).toFixed(2)}/10 credits
                      </p>
                    </div>
                  </button>
                ))}
              </div>

              <p className="text-xs text-zinc-500 text-center mt-4">
                Credits never expire. Use them anytime.
              </p>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </main>
  );
}
