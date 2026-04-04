import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useToast } from "@/hooks/use-toast";
import {
  Linkedin, Twitter, Instagram, Link2, Unlink, CheckCircle2,
  AlertCircle, ExternalLink, RefreshCw, Shield, Zap
} from "lucide-react";
import { apiFetch } from '@/lib/api';

const PLATFORM_CONFIG = {
  linkedin: {
    name: "LinkedIn",
    icon: Linkedin,
    color: "from-blue-600 to-blue-700",
    bgColor: "bg-blue-500/10",
    textColor: "text-blue-400",
    description: "Posts, carousels, and articles",
    features: ["Text posts up to 3,000 chars", "Carousel documents", "Direct publishing"]
  },
  x: {
    name: "X (Twitter)",
    icon: Twitter,
    color: "from-zinc-700 to-zinc-800",
    bgColor: "bg-zinc-500/10",
    textColor: "text-zinc-300",
    description: "Tweets and threads",
    features: ["Tweets up to 280 chars", "Thread auto-posting", "Media attachments"]
  },
  instagram: {
    name: "Instagram",
    icon: Instagram,
    color: "from-pink-500 via-purple-500 to-orange-400",
    bgColor: "bg-pink-500/10",
    textColor: "text-pink-400",
    description: "Feed posts and reels",
    features: ["Image posts", "Carousels", "Business account required"]
  }
};

export default function Connections() {
  const [platforms, setPlatforms] = useState(null);
  const [loading, setLoading] = useState(true);
  const [connecting, setConnecting] = useState(null);
  const [disconnecting, setDisconnecting] = useState(null);
  const { toast } = useToast();

  // Check URL params for OAuth callback results
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const success = params.get("success");
    const error = params.get("error");

    if (success) {
      toast({
        title: "Platform Connected!",
        description: `Successfully connected to ${success.charAt(0).toUpperCase() + success.slice(1)}`,
      });
      // Clean URL
      window.history.replaceState({}, document.title, window.location.pathname);
    } else if (error) {
      const errorMessages = {
        invalid_state: "Session expired. Please try connecting again.",
        token_exchange_failed: "Failed to complete authorization. Please try again.",
        connection_failed: "Connection failed. Please check your account settings."
      };
      toast({
        title: "Connection Failed",
        description: errorMessages[error] || "An error occurred during connection.",
        variant: "destructive"
      });
      window.history.replaceState({}, document.title, window.location.pathname);
    }
  }, [toast]);

  // Fetch platform status
  useEffect(() => {
    fetchPlatformStatus();
  }, []);

  const fetchPlatformStatus = async () => {
    try {
      const res = await apiFetch('/api/platforms/status');

      if (!res.ok) throw new Error("Failed to fetch platform status");
      const data = await res.json();
      setPlatforms(data.platforms);
    } catch (err) {
      console.error("Error fetching platforms:", err);
      toast({
        title: "Error",
        description: "Failed to load platform connections",
        variant: "destructive"
      });
    } finally {
      setLoading(false);
    }
  };

  const connectPlatform = async (platform) => {
    setConnecting(platform);
    try {
      const res = await apiFetch(`/api/platforms/connect/${platform}`);

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || "Failed to start connection");
      }

      const data = await res.json();
      // Redirect to OAuth URL
      window.location.href = data.auth_url;
    } catch (err) {
      console.error("Connection error:", err);
      toast({
        title: "Connection Error",
        description: err.message,
        variant: "destructive"
      });
      setConnecting(null);
    }
  };

  const disconnectPlatform = async (platform) => {
    setDisconnecting(platform);
    try {
      const res = await apiFetch(`/api/platforms/disconnect/${platform}`, {
        method: "DELETE"
      });

      if (!res.ok) throw new Error("Failed to disconnect");

      toast({
        title: "Disconnected",
        description: `Successfully disconnected from ${PLATFORM_CONFIG[platform].name}`
      });

      // Refresh status
      await fetchPlatformStatus();
    } catch (err) {
      console.error("Disconnect error:", err);
      toast({
        title: "Error",
        description: "Failed to disconnect platform",
        variant: "destructive"
      });
    } finally {
      setDisconnecting(null);
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

  return (
    <main className="p-6">
      <div className="max-w-5xl mx-auto space-y-8">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-display font-bold text-white">Platform Connections</h1>
            <p className="text-zinc-400 mt-1">Connect your social accounts for seamless publishing</p>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={fetchPlatformStatus}
            className="gap-2"
          >
            <RefreshCw size={14} />
            Refresh
          </Button>
        </div>

        {/* Connected Count */}
        <Card className="bg-surface-2 border-white/5">
          <CardContent className="py-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-lime/10 flex items-center justify-center">
                  <Link2 className="text-lime" size={18} />
                </div>
                <div>
                  <p className="text-white font-medium">
                    {platforms ? Object.values(platforms).filter(p => p.connected).length : 0} of 3 platforms connected
                  </p>
                  <p className="text-xs text-zinc-500">Connect all platforms for maximum reach</p>
                </div>
              </div>
              {platforms && Object.values(platforms).every(p => p.connected) && (
                <Badge className="bg-lime/10 text-lime border-lime/20">All Connected</Badge>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Platform Cards */}
        <div className="space-y-4">
          {Object.entries(PLATFORM_CONFIG).map(([key, config]) => {
            const platform = platforms?.[key] || { connected: false, configured: false };
            const Icon = config.icon;
            const isConnecting = connecting === key;
            const isDisconnecting = disconnecting === key;

            return (
              <motion.div
                key={key}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: Object.keys(PLATFORM_CONFIG).indexOf(key) * 0.1 }}
              >
                <Card className={`bg-surface-2 border-white/5 overflow-hidden ${platform.connected ? 'ring-1 ring-lime/20' : ''}`}>
                  <CardContent className="p-6">
                    <div className="flex items-start gap-6">
                      {/* Platform Icon */}
                      <div className={`w-16 h-16 rounded-2xl bg-gradient-to-br ${config.color} flex items-center justify-center flex-shrink-0`}>
                        <Icon className="text-white" size={28} />
                      </div>

                      {/* Platform Info */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-3 mb-1">
                          <h3 className="text-lg font-semibold text-white">{config.name}</h3>
                          {platform.connected ? (
                            <Badge className="bg-green-500/10 text-green-400 border-green-500/20 gap-1">
                              <CheckCircle2 size={12} />
                              Connected
                            </Badge>
                          ) : !platform.configured ? (
                            <Badge variant="outline" className="text-zinc-500 border-zinc-700 gap-1">
                              <AlertCircle size={12} />
                              Not Configured
                            </Badge>
                          ) : null}
                        </div>

                        <p className="text-zinc-400 text-sm mb-3">{config.description}</p>

                        {/* Features */}
                        <div className="flex flex-wrap gap-2 mb-4">
                          {config.features.map((feature, i) => (
                            <span
                              key={i}
                              className="text-xs px-2 py-1 rounded-md bg-white/5 text-zinc-400"
                            >
                              {feature}
                            </span>
                          ))}
                        </div>

                        {/* Connection Details */}
                        {platform.connected && (
                          <div className="flex items-center gap-4 text-sm">
                            <span className="text-zinc-400">
                              Account: <span className="text-white">{platform.account_name}</span>
                            </span>
                            {platform.needs_reconnect && (
                              <Badge variant="outline" className="text-orange-400 border-orange-400/30">
                                Token Expired
                              </Badge>
                            )}
                          </div>
                        )}

                        {!platform.configured && (
                          <p className="text-xs text-zinc-500 flex items-center gap-1">
                            <Shield size={12} />
                            API credentials need to be configured in settings
                          </p>
                        )}
                      </div>

                      {/* Action Button */}
                      <div className="flex-shrink-0">
                        {platform.connected ? (
                          <div className="flex gap-2">
                            {platform.needs_reconnect && (
                              <Button
                                onClick={() => connectPlatform(key)}
                                disabled={isConnecting}
                                size="sm"
                                className="bg-orange-500/10 text-orange-400 hover:bg-orange-500/20 gap-2"
                              >
                                <RefreshCw size={14} className={isConnecting ? "animate-spin" : ""} />
                                Reconnect
                              </Button>
                            )}
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => disconnectPlatform(key)}
                              disabled={isDisconnecting}
                              className="text-zinc-400 hover:text-red-400 hover:bg-red-500/10 gap-2"
                            >
                              {isDisconnecting ? (
                                <RefreshCw size={14} className="animate-spin" />
                              ) : (
                                <Unlink size={14} />
                              )}
                              Disconnect
                            </Button>
                          </div>
                        ) : (
                          <Button
                            onClick={() => connectPlatform(key)}
                            disabled={isConnecting || !platform.configured}
                            className={`gap-2 ${platform.configured ? 'bg-gradient-to-r ' + config.color + ' text-white' : 'bg-zinc-800 text-zinc-500'}`}
                          >
                            {isConnecting ? (
                              <>
                                <RefreshCw size={14} className="animate-spin" />
                                Connecting...
                              </>
                            ) : (
                              <>
                                <Link2 size={14} />
                                Connect
                              </>
                            )}
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

        {/* Info Card */}
        <Card className="bg-violet/5 border-violet/20">
          <CardContent className="py-4">
            <div className="flex items-start gap-4">
              <div className="w-10 h-10 rounded-xl bg-violet/10 flex items-center justify-center flex-shrink-0">
                <Zap className="text-violet" size={18} />
              </div>
              <div>
                <h4 className="text-white font-medium mb-1">Why connect platforms?</h4>
                <p className="text-sm text-zinc-400">
                  Connected platforms enable one-click publishing, optimal timing suggestions based on your audience,
                  and performance analytics to help your content reach more people.
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </main>
  );
}
