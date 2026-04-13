import { useState, useEffect, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useToast } from "@/hooks/use-toast";
import {
  Calendar as CalendarIcon, Clock, ChevronLeft, ChevronRight,
  Linkedin, Twitter, Instagram, Plus, Trash2, Eye, Send,
  Sparkles, RefreshCw, Zap, AlertCircle, CheckCircle2
} from "lucide-react";
import { apiFetch } from '@/lib/api';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";

const PLATFORM_ICONS = {
  linkedin: Linkedin,
  x: Twitter,
  instagram: Instagram
};

const PLATFORM_COLORS = {
  linkedin: "bg-blue-500",
  x: "bg-zinc-600",
  instagram: "bg-gradient-to-r from-pink-500 to-orange-400"
};

const STATUS_STYLES = {
  scheduled: { bg: "bg-lime/10", text: "text-lime", label: "Scheduled" },
  approved: { bg: "bg-blue-500/10", text: "text-blue-400", label: "Ready" },
  published: { bg: "bg-lime/10", text: "text-lime", label: "Published" },
  failed: { bg: "bg-red-500/10", text: "text-red-400", label: "Failed" }
};

export default function ContentCalendar() {
  const [selectedDate, setSelectedDate] = useState(new Date());
  const [currentMonth, setCurrentMonth] = useState(new Date());
  const [scheduledContent, setScheduledContent] = useState([]);
  const [optimalTimes, setOptimalTimes] = useState(null);
  const [weeklySchedule, setWeeklySchedule] = useState(null);
  const [loading, setLoading] = useState(true);
  const [loadingSuggestions, setLoadingSuggestions] = useState(false);
  const [rescheduleModal, setRescheduleModal] = useState(null); // {schedule_id, platform, current_time}
  const [newScheduledAt, setNewScheduledAt] = useState("");
  const [rescheduling, setRescheduling] = useState(false);
  const { toast } = useToast();
  const navigate = useNavigate();

  // Fetch calendar data for the current month
  useEffect(() => {
    fetchCalendarData();
  }, [currentMonth]); // Re-fetch when user navigates to a different month

  const fetchCalendarData = async () => {
    setLoading(true);
    try {
      const year = currentMonth.getFullYear();
      const month = currentMonth.getMonth() + 1; // JS months are 0-indexed
      const res = await apiFetch(
        `/api/dashboard/schedule/calendar?year=${year}&month=${month}`
      );
      if (!res.ok) throw new Error("Failed to fetch calendar data");
      const data = await res.json();
      setScheduledContent(data.posts || []);
    } catch (err) {
      console.error("Calendar fetch error:", err);
      toast({
        title: "Error",
        description: "Failed to load calendar data",
        variant: "destructive"
      });
    } finally {
      setLoading(false);
    }
  };

  const fetchWeeklySuggestions = async () => {
    setLoadingSuggestions(true);
    try {
      const res = await apiFetch('/api/dashboard/schedule/weekly?posts_per_week=5');

      if (!res.ok) throw new Error("Failed to fetch suggestions");
      const data = await res.json();
      setWeeklySchedule(data);
      
      toast({
        title: "Schedule Generated",
        description: data.recommendation || `${data.total_posts} optimal posting times suggested`
      });
    } catch (err) {
      console.error("Error fetching weekly schedule:", err);
      toast({
        title: "Error",
        description: "Failed to generate schedule suggestions",
        variant: "destructive"
      });
    } finally {
      setLoadingSuggestions(false);
    }
  };

  const cancelScheduled = async (jobId) => {
    try {
      const res = await apiFetch(`/api/dashboard/schedule/${jobId}`, {
        method: "DELETE"
      });

      if (!res.ok) throw new Error("Failed to cancel");

      toast({ title: "Cancelled", description: "Scheduled post has been cancelled" });
      await fetchCalendarData();
    } catch (err) {
      console.error("Cancel error:", err);
      toast({
        title: "Error",
        description: "Failed to cancel scheduled post",
        variant: "destructive"
      });
    }
  };

  const reschedulePost = async () => {
    if (!rescheduleModal || !newScheduledAt) return;
    setRescheduling(true);
    try {
      const res = await apiFetch(
        `/api/dashboard/schedule/${rescheduleModal.schedule_id}/reschedule`,
        {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            new_scheduled_at: new Date(newScheduledAt).toISOString(),
          }),
        }
      );
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Reschedule failed");

      toast({
        title: "Rescheduled",
        description: `Post rescheduled to ${new Date(data.new_scheduled_at).toLocaleString()}`,
      });
      setRescheduleModal(null);
      setNewScheduledAt("");
      await fetchCalendarData();
    } catch (err) {
      console.error("Reschedule error:", err);
      toast({
        title: "Reschedule Failed",
        description: err.message,
        variant: "destructive",
      });
    } finally {
      setRescheduling(false);
    }
  };

  const publishNow = async (jobId, platform) => {
    try {
      const res = await apiFetch(`/api/dashboard/publish/${jobId}?platforms=${platform}`, {
        method: "POST"
      });

      const data = await res.json();
      
      if (data.all_success) {
        toast({ title: "Published!", description: "Content published successfully" });
      } else if (data.partial_success) {
        toast({ 
          title: "Partially Published", 
          description: `Published to: ${data.successful_platforms.join(", ")}` 
        });
      } else {
        throw new Error(data.results?.[platform]?.error || "Publish failed");
      }

      await fetchCalendarData();
    } catch (err) {
      console.error("Publish error:", err);
      toast({
        title: "Publish Failed",
        description: err.message,
        variant: "destructive"
      });
    }
  };

  // Calendar helpers
  const daysInMonth = useMemo(() => {
    const year = currentMonth.getFullYear();
    const month = currentMonth.getMonth();
    const firstDay = new Date(year, month, 1);
    const lastDay = new Date(year, month + 1, 0);
    const startPadding = firstDay.getDay();
    
    const days = [];
    // Padding for days before month starts
    for (let i = 0; i < startPadding; i++) {
      days.push(null);
    }
    // Days in month
    for (let i = 1; i <= lastDay.getDate(); i++) {
      days.push(new Date(year, month, i));
    }
    return days;
  }, [currentMonth]);

  const getContentForDate = (date) => {
    if (!date) return [];
    return scheduledContent.filter(item => {
      const itemDate = new Date(item.scheduled_at);
      return itemDate.toDateString() === date.toDateString();
    });
  };

  const navigateMonth = (direction) => {
    setCurrentMonth(prev => {
      const newDate = new Date(prev);
      newDate.setMonth(prev.getMonth() + direction);
      return newDate;
    });
  };

  const isToday = (date) => {
    if (!date) return false;
    return date.toDateString() === new Date().toDateString();
  };

  const isSelected = (date) => {
    if (!date) return false;
    return date.toDateString() === selectedDate.toDateString();
  };

  if (loading) {
    return (
      <main className="p-6">
        <div className="max-w-6xl mx-auto">
          <div className="h-96 bg-surface-2 rounded-2xl animate-pulse" />
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
            <h1 className="text-2xl font-display font-bold text-white">Content Calendar</h1>
            <p className="text-zinc-400 mt-1">Schedule and manage your content publication</p>
          </div>
          <div className="flex gap-3">
            <Button
              variant="outline"
              onClick={fetchWeeklySuggestions}
              disabled={loadingSuggestions}
              className="gap-2"
            >
              {loadingSuggestions ? (
                <RefreshCw size={14} className="animate-spin" />
              ) : (
                <Sparkles size={14} />
              )}
              Get AI Suggestions
            </Button>
            <Button
              onClick={() => navigate("/dashboard/studio")}
              className="bg-lime text-black hover:bg-lime/90 gap-2"
            >
              <Plus size={14} />
              Create Content
            </Button>
          </div>
        </div>

        {/* Weekly AI Suggestions */}
        <AnimatePresence>
          {weeklySchedule && (
            <motion.div
              initial={{ opacity: 0, y: -20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
            >
              <Card className="bg-violet/5 border-violet/20">
                <CardContent className="py-4">
                  <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-xl bg-violet/10 flex items-center justify-center">
                        <Zap className="text-violet" size={18} />
                      </div>
                      <div>
                        <h3 className="text-white font-semibold">AI-Suggested Schedule</h3>
                        <p className="text-xs text-zinc-400">{weeklySchedule.recommendation}</p>
                      </div>
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setWeeklySchedule(null)}
                      className="text-zinc-400"
                    >
                      Dismiss
                    </Button>
                  </div>
                  <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
                    {weeklySchedule.schedule?.slice(0, 5).map((slot, i) => {
                      const PlatformIcon = PLATFORM_ICONS[slot.platform] || CalendarIcon;
                      return (
                        <div
                          key={i}
                          className="p-3 rounded-xl bg-white/5 border border-white/5 hover:border-violet/30 transition-colors cursor-pointer"
                          onClick={() => navigate(`/dashboard/studio?platform=${slot.platform}`)}
                        >
                          <div className="flex items-center gap-2 mb-2">
                            <div className={`w-6 h-6 rounded-md ${PLATFORM_COLORS[slot.platform]} flex items-center justify-center`}>
                              <PlatformIcon size={12} className="text-white" />
                            </div>
                            <span className="text-xs text-white capitalize">{slot.platform}</span>
                          </div>
                          <p className="text-[11px] text-zinc-400 line-clamp-2">{slot.display_time}</p>
                        </div>
                      );
                    })}
                  </div>
                  {weeklySchedule.burnout_adjusted && (
                    <p className="text-xs text-orange-400 mt-3 flex items-center gap-1">
                      <AlertCircle size={12} />
                      Schedule adjusted based on your energy levels
                    </p>
                  )}
                </CardContent>
              </Card>
            </motion.div>
          )}
        </AnimatePresence>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Calendar Grid */}
          <Card className="lg:col-span-2 bg-surface-2 border-white/5">
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => navigateMonth(-1)}
                    className="text-zinc-400"
                  >
                    <ChevronLeft size={18} />
                  </Button>
                  <h2 className="text-lg font-semibold text-white">
                    {currentMonth.toLocaleDateString("en-US", { month: "long", year: "numeric" })}
                  </h2>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => navigateMonth(1)}
                    className="text-zinc-400"
                  >
                    <ChevronRight size={18} />
                  </Button>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => {
                    setCurrentMonth(new Date());
                    setSelectedDate(new Date());
                  }}
                  className="text-zinc-400"
                >
                  Today
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              {/* Day headers */}
              <div className="grid grid-cols-7 mb-2">
                {["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"].map(day => (
                  <div key={day} className="text-center text-xs text-zinc-500 py-2">
                    {day}
                  </div>
                ))}
              </div>
              
              {/* Calendar grid */}
              <div className="grid grid-cols-7 gap-1">
                {daysInMonth.map((date, i) => {
                  const content = getContentForDate(date);
                  const hasContent = content.length > 0;
                  
                  return (
                    <button
                      key={i}
                      onClick={() => date && setSelectedDate(date)}
                      disabled={!date}
                      className={`
                        aspect-square p-1 rounded-lg relative flex flex-col items-center justify-start
                        ${!date ? "cursor-default" : "hover:bg-white/5 cursor-pointer"}
                        ${isSelected(date) ? "bg-lime/10 ring-1 ring-lime/30" : ""}
                        ${isToday(date) ? "ring-1 ring-violet/30" : ""}
                      `}
                    >
                      {date && (
                        <>
                          <span className={`
                            text-sm mt-1
                            ${isToday(date) ? "text-violet font-bold" : "text-zinc-400"}
                            ${isSelected(date) ? "text-lime" : ""}
                          `}>
                            {date.getDate()}
                          </span>
                          {hasContent && (
                            <div className="flex gap-0.5 mt-1">
                              {content.slice(0, 3).map((item, j) => (
                                <div
                                  key={j}
                                  className={`w-1.5 h-1.5 rounded-full ${PLATFORM_COLORS[item.platform]}`}
                                />
                              ))}
                            </div>
                          )}
                        </>
                      )}
                    </button>
                  );
                })}
              </div>
            </CardContent>
          </Card>

          {/* Selected Date Panel */}
          <Card className="bg-surface-2 border-white/5">
            <CardHeader>
              <CardTitle className="text-white text-lg">
                {selectedDate.toLocaleDateString("en-US", { 
                  weekday: "long", 
                  month: "long", 
                  day: "numeric" 
                })}
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {getContentForDate(selectedDate).length === 0 ? (
                <div className="text-center py-8">
                  <CalendarIcon className="mx-auto text-zinc-600 mb-3" size={32} />
                  <p className="text-zinc-500 text-sm">No content scheduled</p>
                  <Button
                    variant="outline"
                    size="sm"
                    className="mt-4"
                    onClick={() => navigate("/dashboard/studio")}
                  >
                    Create Content
                  </Button>
                </div>
              ) : (
                getContentForDate(selectedDate).map((item, i) => {
                  const PlatformIcon = PLATFORM_ICONS[item.platform] || CalendarIcon;
                  const statusStyle = STATUS_STYLES[item.status] || STATUS_STYLES.scheduled;
                  
                  return (
                    <motion.div
                      key={item.job_id}
                      initial={{ opacity: 0, x: 20 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: i * 0.1 }}
                      className="p-4 rounded-xl bg-white/5 border border-white/5 space-y-3"
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <div className={`w-8 h-8 rounded-lg ${PLATFORM_COLORS[item.platform]} flex items-center justify-center`}>
                            <PlatformIcon size={14} className="text-white" />
                          </div>
                          <div>
                            <p className="text-sm text-white capitalize">{item.platform}</p>
                            <p className="text-xs text-zinc-500">
                              {new Date(item.scheduled_at).toLocaleTimeString([], { 
                                hour: "2-digit", 
                                minute: "2-digit" 
                              })}
                            </p>
                          </div>
                        </div>
                        <Badge className={`${statusStyle.bg} ${statusStyle.text} border-0`}>
                          {statusStyle.label}
                        </Badge>
                      </div>

                      {item.preview && (
                        <p className="text-xs text-zinc-400 line-clamp-2">{item.preview}</p>
                      )}

                      <div className="flex gap-2">
                        <Button
                          variant="ghost"
                          size="sm"
                          className="flex-1 text-zinc-400 hover:text-white"
                          onClick={() => navigate(`/dashboard/studio?job=${item.job_id}`)}
                        >
                          <Eye size={12} className="mr-1" />
                          View
                        </Button>
                        {item.status === "scheduled" && (
                          <>
                            <Button
                              variant="ghost"
                              size="sm"
                              className="flex-1 text-lime hover:text-lime hover:bg-lime/10"
                              onClick={() => publishNow(item.job_id, item.platform)}
                            >
                              <Send size={12} className="mr-1" />
                              Now
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              className="flex-1 text-blue-400 hover:text-blue-300 hover:bg-blue-500/10"
                              onClick={() => {
                                // Pre-fill with current scheduled time in datetime-local format
                                const dt = new Date(item.scheduled_at);
                                // datetime-local format: "YYYY-MM-DDTHH:mm"
                                const localDt = new Date(dt.getTime() - dt.getTimezoneOffset() * 60000)
                                  .toISOString()
                                  .slice(0, 16);
                                setNewScheduledAt(localDt);
                                setRescheduleModal({
                                  schedule_id: item.schedule_id,
                                  platform: item.platform,
                                  current_time: item.scheduled_at,
                                });
                              }}
                            >
                              <Clock size={12} className="mr-1" />
                              Edit
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              className="text-zinc-400 hover:text-red-400 hover:bg-red-500/10"
                              onClick={() => cancelScheduled(item.job_id)}
                            >
                              <Trash2 size={12} />
                            </Button>
                          </>
                        )}
                      </div>
                    </motion.div>
                  );
                })
              )}
            </CardContent>
          </Card>
        </div>

        {/* Upcoming List */}
        <Card className="bg-surface-2 border-white/5">
          <CardHeader>
            <CardTitle className="text-white flex items-center gap-2">
              <Clock size={18} />
              Upcoming Scheduled Content
            </CardTitle>
          </CardHeader>
          <CardContent>
            {scheduledContent.length === 0 ? (
              <div className="text-center py-8">
                <p className="text-zinc-500">No scheduled content yet</p>
                <p className="text-xs text-zinc-600 mt-1">
                  Create content in the studio and schedule it for publishing
                </p>
              </div>
            ) : (
              <div className="space-y-3">
                {scheduledContent.slice(0, 5).map((item, i) => {
                  const PlatformIcon = PLATFORM_ICONS[item.platform] || CalendarIcon;
                  const scheduledDate = new Date(item.scheduled_at);
                  
                  return (
                    <div
                      key={item.job_id}
                      className="flex items-center gap-4 p-3 rounded-xl bg-white/5 border border-white/5 hover:border-white/10 transition-colors"
                    >
                      <div className={`w-10 h-10 rounded-xl ${PLATFORM_COLORS[item.platform]} flex items-center justify-center`}>
                        <PlatformIcon size={18} className="text-white" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm text-white truncate">
                          {item.preview || `${item.platform} ${item.content_type || "post"}`}
                        </p>
                        <p className="text-xs text-zinc-500">
                          {scheduledDate.toLocaleDateString()} at {scheduledDate.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                        </p>
                      </div>
                      <div className="flex items-center gap-2">
                        <Button
                          variant="ghost"
                          size="sm"
                          className="text-lime hover:bg-lime/10"
                          onClick={() => publishNow(item.job_id, item.platform)}
                        >
                          <Send size={14} />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="text-zinc-400 hover:text-red-400"
                          onClick={() => cancelScheduled(item.job_id)}
                        >
                          <Trash2 size={14} />
                        </Button>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Reschedule Modal */}
      <Dialog open={!!rescheduleModal} onOpenChange={(open) => !open && setRescheduleModal(null)}>
        <DialogContent className="bg-surface-2 border-white/10 text-white max-w-sm">
          <DialogHeader>
            <DialogTitle className="text-white font-display">Reschedule Post</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <p className="text-sm text-zinc-400 capitalize">
              Platform: {rescheduleModal?.platform}
            </p>
            <div className="space-y-2">
              <label className="text-xs text-zinc-400 block">New date and time (UTC)</label>
              <input
                type="datetime-local"
                value={newScheduledAt}
                onChange={(e) => setNewScheduledAt(e.target.value)}
                className="w-full bg-surface border border-white/10 text-white rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-lime/40"
              />
            </div>
          </div>
          <DialogFooter className="gap-2">
            <Button
              variant="ghost"
              size="sm"
              className="text-zinc-400"
              onClick={() => setRescheduleModal(null)}
            >
              Cancel
            </Button>
            <Button
              size="sm"
              className="bg-lime text-black hover:bg-lime/90"
              disabled={!newScheduledAt || rescheduling}
              onClick={reschedulePost}
            >
              {rescheduling ? "Rescheduling..." : "Reschedule"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </main>
  );
}
