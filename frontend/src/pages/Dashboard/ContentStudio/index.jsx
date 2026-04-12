import { useState, useEffect, useRef, useCallback } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import InputPanel from "./InputPanel";
import MediaUploader from "@/components/MediaUploader";
import AgentPipeline from "./AgentPipeline";
import ContentOutput from "./ContentOutput";
import { apiFetch } from '@/lib/api';

export default function ContentStudio() {
  const [searchParams] = useSearchParams();
  const [platform, setPlatform] = useState(searchParams.get("platform") || "linkedin");
  const [contentType, setContentType] = useState("post");
  const [rawInput, setRawInput] = useState(searchParams.get("prefill") || "");
  const [jobId, setJobId] = useState(null);
  const [job, setJob] = useState(null);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState("");
  const [uploadedItems, setUploadedItems] = useState([]);
  const [generateVideo, setGenerateVideo] = useState(false);
  const [videoStyle, setVideoStyle] = useState("cinematic");
  const [userTier, setUserTier] = useState("free");
  const pollRef = useRef(null);
  const navigate = useNavigate();

  // Fetch user tier on mount for feature gating
  useEffect(() => {
    const fetchTier = async () => {
      try {
        const res = await apiFetch('/api/billing/credits');
        if (res.ok) {
          const data = await res.json();
          setUserTier(data.tier || "free");
        }
      } catch {}
    };
    fetchTier();
  }, []);

  // Handle URL params for prefilling from Daily Brief
  useEffect(() => {
    const prefill = searchParams.get("prefill");
    const urlPlatform = searchParams.get("platform");
    
    if (prefill) {
      setRawInput(prefill);
    }
    if (urlPlatform && ["linkedin", "x", "instagram"].includes(urlPlatform)) {
      setPlatform(urlPlatform);
      // Set appropriate content type based on platform
      const defaultTypes = { linkedin: "post", x: "tweet", instagram: "feed_caption" };
      setContentType(defaultTypes[urlPlatform] || "post");
    }
  }, [searchParams]);

  // Poll job status
  const pollJob = useCallback(async (id) => {
    try {
      const res = await apiFetch(`/api/content/job/${id}`);
      if (!res.ok) return;
      const data = await res.json();
      setJob(data);
      if (data.status === "completed" || data.status === "reviewing" || data.status === "error" || data.status === "approved") {
        clearInterval(pollRef.current);
        pollRef.current = null;
        setCreating(false);
      }
    } catch {}
  }, []);

  useEffect(() => {
    if (!jobId) return;
    pollRef.current = setInterval(() => pollJob(jobId), 2000);
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, [jobId, pollJob]);

  const handleCreate = async () => {
    if (!rawInput.trim() || rawInput.trim().length < 5) {
      setError("Please describe what you want to write about");
      return;
    }
    setError("");
    setCreating(true);
    setJob(null);
    setJobId(null);
    try {
      const res = await apiFetch('/api/content/create', {
        method: "POST",
        body: JSON.stringify({
          platform,
          content_type: contentType,
          raw_input: rawInput,
          upload_ids: uploadedItems.map((u) => u.upload_id),
          generate_video: generateVideo,
          video_style: videoStyle,
        }),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Failed to start generation");
      }
      const data = await res.json();
      setJobId(data.job_id);
    } catch (e) {
      setError(e.message);
      setCreating(false);
    }
  };

  const handleApprove = async (editedContent) => {
    if (!job) return;
    await apiFetch(`/api/content/job/${job.job_id}/status`, {
      method: "PATCH",
      body: JSON.stringify({ status: "approved", edited_content: editedContent }),
    });
    setJob(j => ({ ...j, status: "approved", final_content: editedContent || j.final_content }));
  };

  const handleRegenerate = async () => {
    if (!job) {
      // No existing job, just create new
      handleCreate();
      return;
    }
    
    // Use the regeneration endpoint
    try {
      setCreating(true);
      const res = await apiFetch(`/api/content/job/${job.job_id}/regenerate`, {
        method: "PATCH",
        body: JSON.stringify({ hint: "" }),
      });
      
      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || "Regeneration failed");
      }
      
      const data = await res.json();
      setJob(null);
      setJobId(data.job_id);
    } catch (e) {
      setError(e.message);
      setCreating(false);
    }
  };

  const handleDiscard = async (reason) => {
    if (job) {
      // Mark as rejected with reason
      await apiFetch(`/api/content/job/${job.job_id}/status`, {
        method: "PATCH",
        body: JSON.stringify({ status: "rejected", notes: reason }),
      });
    }
    setJob(null);
    setJobId(null);
    setCreating(false);
  };

  const isRunning = creating || (job && job.status === "running");
  const isDone = job && (job.status === "completed" || job.status === "reviewing" || job.status === "approved");

  return (
    <div className="flex flex-col md:flex-row md:h-[calc(100vh-4rem)] overflow-x-hidden" data-testid="content-studio">
      {/* Left: Input Panel */}
      <div className="w-full md:w-[400px] flex-shrink-0 h-auto md:h-[calc(100vh-4rem)] overflow-y-auto border-b md:border-b-0 md:border-r border-white/5">
        <InputPanel
          platform={platform}
          contentType={contentType}
          rawInput={rawInput}
          onPlatformChange={setPlatform}
          onContentTypeChange={setContentType}
          onInputChange={setRawInput}
          onGenerate={handleCreate}
          isRunning={isRunning}
          error={error}
          generateVideo={generateVideo}
          onGenerateVideoChange={setGenerateVideo}
          videoStyle={videoStyle}
          onVideoStyleChange={setVideoStyle}
          userTier={userTier}
          mediaSection={
            <div className="mb-4">
              <p className="text-xs text-zinc-500 uppercase tracking-wider mb-1 font-mono">Add context (optional)</p>
              <p className="text-[11px] text-zinc-600 mb-2 leading-relaxed">
                Upload images, videos, or paste URLs — AI will use these to inform your content
              </p>
              <MediaUploader items={uploadedItems} onItemsChange={setUploadedItems} />
            </div>
          }
        />
      </div>

      {/* Right: Output Area */}
      <div className="flex-1 min-h-[50vh] md:h-[calc(100vh-4rem)] overflow-y-auto">
        <AnimatePresence mode="wait">
          {!isRunning && !isDone && (
            <motion.div key="empty" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
              <EmptyState platform={platform} />
            </motion.div>
          )}
          {isRunning && (
            <motion.div key="pipeline" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} className="p-6">
              <AgentPipeline job={job} platform={platform} rawInput={rawInput} />
            </motion.div>
          )}
          {isDone && job && (
            <motion.div key="output" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} className="p-6">
              <ContentOutput
                job={job}
                onApprove={handleApprove}
                onRegenerate={handleRegenerate}
                onDiscard={handleDiscard}
              />
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}

function EmptyState({ platform }) {
  const platformConfig = {
    linkedin: { color: "#0A66C2", label: "LinkedIn Post", desc: "Long-form professional insights", char: "3,000 chars" },
    x: { color: "#1D9BF0", label: "X Thread", desc: "Concise tweets, big ideas", char: "280 / tweet" },
    instagram: { color: "#E1306C", label: "Instagram Caption", desc: "Visual storytelling with hashtags", char: "2,200 chars" },
  };
  const cfg = platformConfig[platform] || platformConfig.linkedin;

  return (
    <div className="h-full flex items-center justify-center p-8">
      <div className="text-center max-w-sm">
        <div className="w-16 h-16 rounded-2xl flex items-center justify-center mx-auto mb-5 border border-white/10"
          style={{ backgroundColor: `${cfg.color}15` }}>
          <div className="w-3 h-3 rounded-full" style={{ backgroundColor: cfg.color }} />
        </div>
        <h3 className="font-display font-semibold text-white text-lg mb-2">{cfg.label}</h3>
        <p className="text-zinc-500 text-sm mb-1">{cfg.desc}</p>
        <p className="text-zinc-700 text-xs font-mono">{cfg.char}</p>
        <div className="mt-8 space-y-2">
          <p className="text-zinc-700 text-xs uppercase tracking-wider">5 agents will work for you</p>
          <div className="flex justify-center gap-2">
            {["Commander", "Scout", "Thinker", "Writer", "QC"].map(a => (
              <span key={a} className="text-[10px] bg-white/5 text-zinc-600 rounded-full px-2 py-1">{a}</span>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
