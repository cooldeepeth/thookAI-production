import { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Card, CardHeader, CardTitle, CardContent, CardFooter } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Lightbulb, Check, X, Linkedin, Twitter, Instagram,
  TrendingUp, Brain, BarChart2, Sparkles, Clock,
} from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import useStrategyFeed from "@/hooks/useStrategyFeed";
import useNotifications from "@/hooks/useNotifications";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const PLATFORM_ICONS = {
  linkedin: Linkedin,
  x: Twitter,
  instagram: Instagram,
};

const SIGNAL_ICONS = {
  performance: BarChart2,
  persona: Brain,
  knowledge_graph: Sparkles,
  trending: TrendingUp,
};

const SIGNAL_LABELS = {
  performance: "Performance",
  persona: "Persona",
  knowledge_graph: "Knowledge",
  trending: "Trending",
};

// --- Helpers ---

function timeAgo(dateString) {
  if (!dateString) return "";
  const now = new Date();
  const date = new Date(dateString);
  const seconds = Math.floor((now - date) / 1000);
  if (seconds < 60) return "just now";
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  return `${Math.floor(seconds / 86400)}d ago`;
}

// --- Sub-components ---

function SkeletonCard() {
  return (
    <div className="rounded-xl border border-white/5 bg-surface-2 p-5 animate-pulse">
      <div className="flex items-center gap-2 mb-4">
        <div className="h-5 w-20 bg-zinc-800 rounded-full" />
        <div className="h-5 w-24 bg-zinc-800 rounded-full" />
      </div>
      <div className="h-5 w-3/4 bg-zinc-800 rounded mb-3" />
      <div className="h-3 w-full bg-zinc-800 rounded mb-2" />
      <div className="h-3 w-5/6 bg-zinc-800 rounded mb-4" />
      <div className="flex gap-2 mt-4">
        <div className="h-9 w-24 bg-zinc-800 rounded" />
        <div className="h-9 w-24 bg-zinc-800 rounded" />
      </div>
    </div>
  );
}

function ActiveCard({ card, onApprove, onDismiss, isLoading }) {
  const PlatformIcon = PLATFORM_ICONS[card.platform] || Linkedin;
  const SignalIcon = SIGNAL_ICONS[card.signal_source] || Sparkles;

  return (
    <motion.div
      key={card.recommendation_id}
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -8, scale: 0.97 }}
      transition={{ duration: 0.22 }}
    >
      <Card className="bg-surface-2 border-white/5 hover:border-white/10 transition-colors">
        <CardHeader className="pb-2">
          <div className="flex items-center gap-2 flex-wrap mb-2">
            <Badge
              variant="outline"
              className="flex items-center gap-1 text-xs border-white/10 text-zinc-300"
            >
              <PlatformIcon size={12} />
              {card.platform === "x" ? "X / Twitter" : card.platform.charAt(0).toUpperCase() + card.platform.slice(1)}
            </Badge>
            <Badge
              variant="outline"
              className="flex items-center gap-1 text-xs border-white/10 text-zinc-400"
            >
              <SignalIcon size={12} />
              {SIGNAL_LABELS[card.signal_source] || card.signal_source}
            </Badge>
          </div>
          <CardTitle className="text-base text-white leading-snug capitalize">
            {card.topic}
          </CardTitle>
        </CardHeader>

        <CardContent className="pb-3">
          {card.why_now && (
            <p className="text-sm text-zinc-400 leading-relaxed mb-3">
              {card.why_now}
            </p>
          )}
          {card.hook_options && card.hook_options.length > 0 && (
            <div>
              <p className="text-[11px] text-zinc-600 uppercase tracking-wider font-mono mb-1.5">
                Hook ideas
              </p>
              <div className="flex flex-wrap gap-1.5">
                {card.hook_options.map((hook, idx) => (
                  <span
                    key={idx}
                    className="text-xs bg-white/5 text-zinc-300 rounded-full px-2.5 py-1 border border-white/5"
                  >
                    {hook}
                  </span>
                ))}
              </div>
            </div>
          )}
        </CardContent>

        <CardFooter className="pt-2 gap-2">
          <Button
            size="sm"
            disabled={isLoading}
            onClick={() => onApprove(card)}
            className="bg-lime text-black hover:bg-lime/90 gap-1.5 font-semibold"
          >
            <Check size={14} />
            Approve
          </Button>
          <Button
            size="sm"
            variant="ghost"
            disabled={isLoading}
            onClick={() => onDismiss(card)}
            className="text-zinc-400 hover:text-white gap-1.5"
          >
            <X size={14} />
            Dismiss
          </Button>
          <span className="ml-auto text-[11px] text-zinc-600 flex items-center gap-1">
            <Clock size={11} />
            {timeAgo(card.created_at)}
          </span>
        </CardFooter>
      </Card>
    </motion.div>
  );
}

function HistoryItem({ card }) {
  const isApproved = card.status === "approved";

  return (
    <div className="flex items-start gap-3 py-3 border-b border-white/5 last:border-b-0">
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap mb-0.5">
          <span className="text-sm font-medium text-zinc-300 truncate capitalize">
            {card.topic}
          </span>
          <Badge
            variant="outline"
            className={`text-[10px] shrink-0 ${
              isApproved
                ? "border-green-500/30 text-green-400"
                : "border-zinc-700 text-zinc-500"
            }`}
          >
            {isApproved ? "Approved" : "Dismissed"}
          </Badge>
        </div>
        {card.why_now && (
          <p className="text-xs text-zinc-500 truncate">{card.why_now}</p>
        )}
        <span className="text-[10px] text-zinc-600 mt-0.5 block">
          {timeAgo(card.created_at)}
        </span>
      </div>
      <Badge
        variant="outline"
        className="text-[10px] border-white/10 text-zinc-500 shrink-0 capitalize"
      >
        {card.platform === "x" ? "X" : card.platform}
      </Badge>
    </div>
  );
}

// --- Main page ---

export default function StrategyDashboard() {
  const navigate = useNavigate();
  const { toast } = useToast();
  const { activeCards, historyCards, loading, approveCard, dismissCard, refresh } =
    useStrategyFeed();
  const { notifications } = useNotifications();
  const [loadingCardId, setLoadingCardId] = useState(null);

  // Track seen notification IDs so refresh only fires on genuinely new ones
  const seenNotifIds = useRef(new Set());

  // SSE-driven refresh: watch for nightly-strategist workflow_status notifications
  useEffect(() => {
    notifications.forEach((notif) => {
      if (seenNotifIds.current.has(notif.notification_id)) return;
      seenNotifIds.current.add(notif.notification_id);

      if (
        notif.type === "workflow_status" &&
        notif.metadata?.workflow_type === "nightly-strategist"
      ) {
        refresh();
      }
    });
  }, [notifications, refresh]);

  const handleApprove = async (card) => {
    setLoadingCardId(card.recommendation_id);
    try {
      const generatePayload = await approveCard(card.recommendation_id);

      // Validate payload has required fields before firing content create
      if (
        !generatePayload?.platform ||
        !generatePayload?.content_type ||
        !generatePayload?.raw_input
      ) {
        throw new Error("Invalid generate payload — missing required fields");
      }

      const token = localStorage.getItem("thook_token");
      const res = await fetch(`${BACKEND_URL}/api/content/create`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        credentials: "include",
        body: JSON.stringify(generatePayload),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Content generation failed");
      }

      const data = await res.json();
      navigate(`/dashboard/studio?job=${data.job_id}`);
    } catch (e) {
      toast({
        title: "Approval failed",
        description: e.message,
        variant: "destructive",
      });
    } finally {
      setLoadingCardId(null);
    }
  };

  const handleDismiss = async (card) => {
    setLoadingCardId(card.recommendation_id);
    try {
      const result = await dismissCard(card.recommendation_id);
      if (result?.needs_calibration_prompt) {
        toast({
          title: "Strategy feed recalibrating",
          description:
            "You've dismissed several recommendations. Your strategy feed will be recalibrated to better match your preferences.",
        });
      }
    } catch (e) {
      toast({
        title: "Dismiss failed",
        description: e.message,
        variant: "destructive",
      });
    } finally {
      setLoadingCardId(null);
    }
  };

  return (
    <div className="flex-1 p-6 max-w-3xl mx-auto w-full">
      {/* Page header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-white flex items-center gap-2">
          <Lightbulb size={22} className="text-lime" />
          Strategy Feed
        </h1>
        <p className="text-sm text-zinc-500 mt-1">
          AI-generated content recommendations tailored to your persona and performance signals.
        </p>
      </div>

      <Tabs defaultValue="active">
        <TabsList className="bg-white/5 border border-white/5 mb-6">
          <TabsTrigger value="active" className="data-[state=active]:bg-white/10 data-[state=active]:text-white text-zinc-400">
            Active
            {!loading && activeCards.length > 0 && (
              <span className="ml-1.5 text-[10px] bg-lime/20 text-lime rounded-full px-1.5 py-0.5">
                {activeCards.length}
              </span>
            )}
          </TabsTrigger>
          <TabsTrigger value="history" className="data-[state=active]:bg-white/10 data-[state=active]:text-white text-zinc-400">
            History
          </TabsTrigger>
        </TabsList>

        {/* Active tab */}
        <TabsContent value="active">
          {loading ? (
            <div className="space-y-4">
              <SkeletonCard />
              <SkeletonCard />
              <SkeletonCard />
            </div>
          ) : activeCards.length === 0 ? (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="flex flex-col items-center justify-center py-16 text-zinc-500"
            >
              <Lightbulb size={36} className="mb-3 opacity-30" />
              <p className="text-base font-medium text-zinc-400">No recommendations right now.</p>
              <p className="text-sm mt-1">Check back tomorrow — the strategist runs nightly.</p>
            </motion.div>
          ) : (
            <AnimatePresence mode="popLayout">
              <div className="space-y-4">
                {activeCards.map((card) => (
                  <ActiveCard
                    key={card.recommendation_id}
                    card={card}
                    onApprove={handleApprove}
                    onDismiss={handleDismiss}
                    isLoading={loadingCardId === card.recommendation_id}
                  />
                ))}
              </div>
            </AnimatePresence>
          )}
        </TabsContent>

        {/* History tab */}
        <TabsContent value="history">
          {loading ? (
            <div className="space-y-2">
              {[1, 2, 3].map((i) => (
                <div key={i} className="h-14 bg-zinc-800 rounded animate-pulse" />
              ))}
            </div>
          ) : historyCards.length === 0 ? (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="flex flex-col items-center justify-center py-16 text-zinc-500"
            >
              <Clock size={36} className="mb-3 opacity-30" />
              <p className="text-sm">No recommendation history yet.</p>
            </motion.div>
          ) : (
            <div className="rounded-xl border border-white/5 bg-surface-2 px-4 divide-y divide-white/5">
              {historyCards.map((card) => (
                <HistoryItem key={card.recommendation_id} card={card} />
              ))}
            </div>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
