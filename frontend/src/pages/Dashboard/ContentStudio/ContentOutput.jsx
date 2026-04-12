import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Check, Edit2, RefreshCw, X, ChevronDown, ChevronUp, AlertTriangle,
  Image, Mic, Download, Play, Pause, Loader2, Sparkles, Video,
  Calendar, Send, Clock, Linkedin, ExternalLink, Copy, ClipboardCheck
} from "lucide-react";
import { LinkedInShell, XShell, InstagramShell } from "./Shells";
import { apiFetch } from '@/lib/api';
import { ExportActionsBar } from './ExportActionsBar';

function QCBadge({ label, value, max, isRisk = false }) {
  const pct = (value / max) * 100;
  const isGood = isRisk ? value <= 35 : value >= 7;
  const color = isGood ? "bg-lime" : value >= (isRisk ? 60 : 5) ? "bg-yellow-400" : "bg-red-400";
  const textColor = isGood ? "text-lime" : "text-yellow-400";

  return (
    <div className="bg-white/3 rounded-xl p-3 flex-1">
      <div className="flex items-center justify-between mb-1.5">
        <span className="text-xs text-zinc-500">{label}</span>
        <span className={`text-xs font-mono font-bold ${textColor}`}>
          {value}{max === 10 ? "/10" : "/100"}
        </span>
      </div>
      <div className="h-1.5 bg-white/5 rounded-full overflow-hidden">
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${isRisk ? 100 - pct : pct}%` }}
          transition={{ duration: 0.8, ease: "easeOut" }}
          className={`h-full rounded-full ${color}`}
        />
      </div>
      <p className="text-[10px] text-zinc-700 mt-1">{isGood ? "Good" : "Needs work"}</p>
    </div>
  );
}

function RepetitionBadge({ score, level }) {
  if (!level || level === "none" || level === "unknown") return null;
  
  const colors = {
    low: "text-green-400 bg-green-400/10",
    medium: "text-yellow-400 bg-yellow-400/10",
    high: "text-red-400 bg-red-400/10"
  };
  
  const colorClass = colors[level] || colors.low;
  
  return (
    <div className={`flex items-center gap-1.5 text-xs px-2 py-1 rounded-lg ${colorClass}`}>
      <AlertTriangle size={12} />
      <span>Repetition: {level}</span>
      {score > 0 && <span className="font-mono">({Math.round(score)}%)</span>}
    </div>
  );
}

function ScoutResearch({ scout }) {
  const [expanded, setExpanded] = useState(false);
  if (!scout?.findings) return null;

  return (
    <div className="card-thook p-4 mt-4">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center justify-between w-full"
      >
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold text-zinc-400">Scout Research</span>
          {scout.sources_found > 0 && (
            <span className="text-[10px] text-lime bg-lime/10 rounded-full px-2 py-0.5">{scout.sources_found} sources</span>
          )}
        </div>
        {expanded ? <ChevronUp size={13} className="text-zinc-500" /> : <ChevronDown size={13} className="text-zinc-500" />}
      </button>
      {expanded && (
        <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }} className="mt-3">
          <p className="text-xs text-zinc-500 leading-relaxed whitespace-pre-line">{scout.findings}</p>
        </motion.div>
      )}
    </div>
  );
}

function PlatformShell({ platform, content, onContentChange, isEditing, readOnly }) {
  switch (platform) {
    case "linkedin":
      return (
        <LinkedInShell
          content={content}
          onContentChange={onContentChange}
          isEditing={isEditing}
          readOnly={readOnly}
        />
      );
    case "x":
      return (
        <XShell
          content={content}
          onContentChange={onContentChange}
          isEditing={isEditing}
          readOnly={readOnly}
        />
      );
    case "instagram":
      return (
        <InstagramShell
          content={content}
          onContentChange={onContentChange}
          isEditing={isEditing}
          readOnly={readOnly}
        />
      );
    default:
      return (
        <LinkedInShell
          content={content}
          onContentChange={onContentChange}
          isEditing={isEditing}
          readOnly={readOnly}
        />
      );
  }
}

// Image Style Selector
const IMAGE_STYLES = [
  { id: "minimal", name: "Minimal", desc: "Clean and simple" },
  { id: "bold", name: "Bold", desc: "Vibrant colors" },
  { id: "data-viz", name: "Data Viz", desc: "Infographic style" },
  { id: "personal", name: "Personal", desc: "Warm and authentic" },
];

function VideoStatusBadge({ job }) {
  const status = job.video_status;
  if (!status) return null;

  const statusConfig = {
    queued: { label: "Video: Queued", color: "text-zinc-400 bg-zinc-400/10", spinning: false },
    generating: { label: "Video: Generating...", color: "text-violet bg-violet/10", spinning: true },
    completed: { label: "Video: Ready", color: "text-lime bg-lime/10", spinning: false },
    failed: { label: "Video: Failed", color: "text-red-400 bg-red-400/10", spinning: false },
    skipped: { label: "Video: Skipped", color: "text-yellow-400 bg-yellow-400/10", spinning: false },
  };

  const cfg = statusConfig[status] || statusConfig.queued;

  return (
    <div className={`card-thook p-4 mt-4`} data-testid="video-status-badge">
      <div className="flex items-center gap-3">
        <div className={`flex items-center gap-2 text-sm px-3 py-1.5 rounded-lg ${cfg.color}`}>
          {cfg.spinning ? <Loader2 size={14} className="animate-spin" /> : <Video size={14} />}
          <span className="font-medium">{cfg.label}</span>
        </div>
        {status === "completed" && job.video_url && (
          <a
            href={job.video_url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs text-violet hover:underline flex items-center gap-1"
          >
            View video <ExternalLink size={10} />
          </a>
        )}
      </div>
      {status === "failed" && job.video_error && (
        <p className="text-xs text-red-400/70 mt-2">{job.video_error}</p>
      )}
      {status === "skipped" && job.video_error && (
        <p className="text-xs text-yellow-400/70 mt-2">{job.video_error}</p>
      )}
      {status === "completed" && job.video_url && (
        <div className="mt-3 rounded-xl overflow-hidden bg-black">
          <video
            src={job.video_url}
            controls
            className="w-full max-h-64"
            preload="metadata"
          />
        </div>
      )}
    </div>
  );
}

function MediaPanel({ job, onMediaUpdate }) {
  const [generating, setGenerating] = useState(false);
  const [generatingVoice, setGeneratingVoice] = useState(false);
  const [selectedStyle, setSelectedStyle] = useState("minimal");
  const [generatedImage, setGeneratedImage] = useState(job.media_assets?.[0]?.image_url || null);
  const [audioUrl, setAudioUrl] = useState(job.audio_url || null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [error, setError] = useState(null);

  const handleGenerateImage = async () => {
    setGenerating(true);
    setError(null);

    try {
      const response = await apiFetch('/api/content/generate-image', {
        method: "POST",
        body: JSON.stringify({
          job_id: job.job_id,
          style: selectedStyle
        })
      });
      
      const data = await response.json();
      
      if (data.generated && data.image_url) {
        setGeneratedImage(data.image_url);
        onMediaUpdate?.({ type: "image", data });
      } else {
        setError(data.message || "Failed to generate image");
      }
    } catch (err) {
      setError("Failed to generate image. Please try again.");
    } finally {
      setGenerating(false);
    }
  };

  const handleGenerateVoice = async () => {
    setGeneratingVoice(true);
    setError(null);

    try {
      const response = await apiFetch('/api/content/narrate', {
        method: "POST",
        body: JSON.stringify({
          job_id: job.job_id
        })
      });
      
      const data = await response.json();
      
      if (data.generated && data.audio_url) {
        setAudioUrl(data.audio_url);
        onMediaUpdate?.({ type: "voice", data });
      } else {
        setError(data.message || "Failed to generate voice");
      }
    } catch (err) {
      setError("Failed to generate voice. Please try again.");
    } finally {
      setGeneratingVoice(false);
    }
  };

  const toggleAudio = () => {
    const audio = document.getElementById("voice-audio");
    if (audio) {
      if (isPlaying) {
        audio.pause();
      } else {
        audio.play();
      }
      setIsPlaying(!isPlaying);
    }
  };

  return (
    <div className="card-thook p-4 mt-4" data-testid="media-panel">
      <div className="flex items-center gap-2 mb-3">
        <Sparkles size={14} className="text-violet" />
        <span className="text-xs font-semibold text-zinc-400 uppercase tracking-wider">Media Enhancement</span>
      </div>

      {error && (
        <div className="text-xs text-red-400 bg-red-400/10 rounded-lg p-2 mb-3">
          {error}
        </div>
      )}

      {/* Image Generation */}
      <div className="mb-4">
        <p className="text-xs text-zinc-500 mb-2">Generate Image</p>
        
        {generatedImage ? (
          <div className="relative rounded-xl overflow-hidden mb-2">
            <img 
              src={generatedImage} 
              alt="Generated content" 
              className="w-full h-48 object-cover"
            />
            <button
              onClick={() => setGeneratedImage(null)}
              className="absolute top-2 right-2 p-1.5 bg-black/50 rounded-full hover:bg-black/70 transition-colors"
            >
              <X size={14} className="text-white" />
            </button>
          </div>
        ) : (
          <>
            <div className="flex gap-2 mb-2">
              {IMAGE_STYLES.map((style) => (
                <button
                  key={style.id}
                  onClick={() => setSelectedStyle(style.id)}
                  className={`flex-1 p-2 rounded-lg text-xs transition-all ${
                    selectedStyle === style.id
                      ? "bg-violet/20 border border-violet text-violet"
                      : "bg-white/5 border border-transparent text-zinc-400 hover:bg-white/10"
                  }`}
                >
                  {style.name}
                </button>
              ))}
            </div>
            
            <button
              onClick={handleGenerateImage}
              disabled={generating}
              className="w-full py-2.5 bg-violet/10 hover:bg-violet/20 text-violet rounded-lg text-sm font-medium transition-colors flex items-center justify-center gap-2 disabled:opacity-50"
            >
              {generating ? (
                <>
                  <Loader2 size={14} className="animate-spin" />
                  Generating... (up to 60s)
                </>
              ) : (
                <>
                  <Image size={14} />
                  Generate Image
                </>
              )}
            </button>
          </>
        )}
      </div>

      {/* Voice Generation */}
      <div>
        <p className="text-xs text-zinc-500 mb-2">Add Voice Narration</p>
        
        {audioUrl ? (
          <div className="flex items-center gap-3 bg-white/5 rounded-xl p-3">
            <button
              onClick={toggleAudio}
              className="w-10 h-10 rounded-full bg-lime flex items-center justify-center hover:bg-lime/80 transition-colors"
            >
              {isPlaying ? <Pause size={16} className="text-black" /> : <Play size={16} className="text-black ml-0.5" />}
            </button>
            <div className="flex-1">
              <div className="h-8 bg-white/10 rounded-full overflow-hidden flex items-center px-3">
                <div className="flex items-center gap-0.5 w-full">
                  {[...Array(30)].map((_, i) => (
                    <div
                      key={i}
                      className="w-1 bg-lime/60 rounded-full"
                      style={{ height: `${Math.random() * 20 + 8}px` }}
                    />
                  ))}
                </div>
              </div>
              <audio 
                id="voice-audio" 
                src={audioUrl} 
                onEnded={() => setIsPlaying(false)}
                className="hidden"
              />
            </div>
            <a
              href={audioUrl}
              download={`narration-${job.job_id}.mp3`}
              className="p-2 hover:bg-white/10 rounded-lg transition-colors"
            >
              <Download size={16} className="text-zinc-400" />
            </a>
          </div>
        ) : (
          <button
            onClick={handleGenerateVoice}
            disabled={generatingVoice}
            className="w-full py-2.5 bg-white/5 hover:bg-white/10 text-zinc-300 rounded-lg text-sm font-medium transition-colors flex items-center justify-center gap-2 disabled:opacity-50"
          >
            {generatingVoice ? (
              <>
                <Loader2 size={14} className="animate-spin" />
                Generating voice...
              </>
            ) : (
              <>
                <Mic size={14} />
                Add Voice
              </>
            )}
          </button>
        )}
      </div>
    </div>
  );
}

// Rejection Modal
function RejectionModal({ isOpen, onClose, onSubmit }) {
  const [reason, setReason] = useState("");
  
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className="bg-zinc-900 rounded-2xl p-6 max-w-md w-full border border-zinc-800"
      >
        <h3 className="text-lg font-display font-semibold text-white mb-2">Reject Content</h3>
        <p className="text-sm text-zinc-500 mb-4">
          Optionally add feedback so we can learn from this and improve.
        </p>
        
        <textarea
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          placeholder="What didn't work? (optional)"
          className="w-full h-24 bg-white/5 border border-zinc-800 rounded-xl px-4 py-3 text-sm text-white placeholder:text-zinc-600 focus:outline-none focus:border-zinc-700 resize-none"
        />
        
        <div className="flex gap-3 mt-4">
          <button
            onClick={onClose}
            className="flex-1 py-2.5 bg-white/5 hover:bg-white/10 text-zinc-300 rounded-lg text-sm font-medium transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={() => onSubmit(reason)}
            className="flex-1 py-2.5 bg-red-500/20 hover:bg-red-500/30 text-red-400 rounded-lg text-sm font-medium transition-colors"
          >
            Reject
          </button>
        </div>
      </motion.div>
    </div>
  );
}

const FORMAT_LABEL_MAP = {
  post: "Post",
  article: "Article",
  carousel_caption: "Carousel",
  tweet: "Tweet",
  thread: "Thread",
  feed_caption: "Feed",
  reel_caption: "Reel",
  story_sequence: "Story",
};

const PLATFORM_LABEL_MAP = {
  linkedin: "LinkedIn",
  x: "X",
  twitter: "X",
  instagram: "Instagram",
};

function finalContentToText(fc) {
  if (fc == null) return "";
  if (typeof fc === "string") return fc;
  if (typeof fc === "object" && fc.post != null) return String(fc.post);
  return "";
}

function ContentOutput({ job, onApprove, onRegenerate, onDiscard }) {
  const bodyText = finalContentToText(job.final_content);
  const [editing, setEditing] = useState(false);
  const [editedContent, setEditedContent] = useState(bodyText);
  const [approved, setApproved] = useState(job.status === "approved");
  const [showRejectionModal, setShowRejectionModal] = useState(false);
  const [copied, setCopied] = useState(false);
  useEffect(() => {
    setEditedContent(finalContentToText(job.final_content));
  }, [job.final_content, job.job_id]);

  const qc = job.qc_score || {};
  const scout = job.agent_outputs?.scout;
  const platform = job.platform || "linkedin";
  const isApproved = approved || job.status === "approved";
  const version = job.version || 1;

  const handleApprove = async () => {
    await onApprove(editing ? editedContent : bodyText);
    setApproved(true);
    setEditing(false);
  };

  const handleReject = async (reason) => {
    setShowRejectionModal(false);
    await onDiscard(reason);
  };

  const handleContentChange = (newContent) => {
    setEditedContent(newContent);
  };

  const handleMediaUpdate = () => {
    // No-op handler for future use
  };

  const handleCopy = async () => {
    const textToCopy = editing ? editedContent : bodyText;
    if (!textToCopy) return;
    try {
      await navigator.clipboard.writeText(textToCopy);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error("Failed to copy:", err);
    }
  };

  const contentType = job.content_type || "post";
  const formatLabel = FORMAT_LABEL_MAP[contentType] || "Post";
  const platformLabel = PLATFORM_LABEL_MAP[platform] || platform;

  return (
    <div className="max-w-2xl mx-auto" data-testid="content-output">
      {/* Output header */}
      <div className="flex items-center justify-between mb-3">
        <h2
          data-testid="content-output-header"
          className="font-display font-bold text-3xl text-white"
        >
          Your {formatLabel} is ready
        </h2>
        <span
          data-testid="content-format-badge"
          className="text-xs font-mono text-zinc-400 bg-white/5 px-2 py-1 rounded"
        >
          {platformLabel} · {formatLabel}
        </span>
      </div>

      {/* Version indicator */}
      {version > 1 && (
        <div className="flex items-center gap-2 mb-2">
          <span className="text-xs font-mono text-zinc-600 bg-white/5 px-2 py-1 rounded">
            Version {version}
          </span>
        </div>
      )}

      {/* Success banner if approved */}
      {isApproved && (
        <motion.div
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-center gap-3 bg-lime/10 border border-lime/20 rounded-xl p-3 mb-4"
          data-testid="approved-banner"
        >
          <Check size={16} className="text-lime" />
          <p className="text-sm text-white font-medium">Content approved — saved to your library</p>
        </motion.div>
      )}

      {/* QC Scores */}
      <div className="mb-4" data-testid="qc-scores">
        <div className="flex items-center justify-between mb-2">
          <p className="text-xs text-zinc-500 uppercase tracking-wider font-mono">Quality Scores</p>
          <div className="flex items-center gap-2">
            <RepetitionBadge score={qc.repetition_risk} level={qc.repetition_level} />
            <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${
              qc.overall_pass ? "bg-lime/15 text-lime" : "bg-yellow-400/10 text-yellow-400"
            }`} data-testid="qc-overall-badge">
              {qc.overall_pass ? "✓ PASS" : "⚠ REVIEW"}
            </span>
          </div>
        </div>
        <div className="flex gap-2">
          <QCBadge label="Persona Match" value={qc.personaMatch || 0} max={10} />
          <QCBadge label="AI Risk" value={qc.aiRisk || 0} max={100} isRisk />
          <QCBadge label="Platform Fit" value={qc.platformFit || 0} max={10} />
        </div>
      </div>

      {/* Platform-Native Shell */}
      <div className="mb-4" data-testid="platform-shell">
        <PlatformShell
          platform={platform}
          content={editing ? editedContent : bodyText}
          onContentChange={handleContentChange}
          isEditing={editing}
          readOnly={isApproved}
        />
      </div>

      {/* QC Feedback */}
      {qc.feedback?.length > 0 && !isApproved && (
        <div className="card-thook p-4 mb-4">
          <p className="text-xs text-zinc-500 uppercase tracking-wider mb-2 font-mono">Agent Feedback</p>
          <div className="space-y-1.5">
            {qc.feedback.slice(0, 2).map((f, i) => (
              <div key={i} className="flex items-start gap-2">
                <span className="text-yellow-400 text-xs flex-shrink-0 mt-0.5">→</span>
                <p className="text-xs text-zinc-400">{f}</p>
              </div>
            ))}
          </div>
          {qc.strengths?.length > 0 && (
            <div className="mt-3 space-y-1">
              {qc.strengths.slice(0, 1).map((s, i) => (
                <div key={i} className="flex items-start gap-2">
                  <span className="text-lime text-xs flex-shrink-0 mt-0.5">✓</span>
                  <p className="text-xs text-zinc-500">{s}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Scout research (expandable) */}
      <ScoutResearch scout={scout} />

      {/* Media Panel (for approved or reviewing content) */}
      {(isApproved || job.status === "reviewing" || job.status === "completed") && (
        <MediaPanel job={job} onMediaUpdate={handleMediaUpdate} />
      )}

      {/* Video generation status */}
      {job.video_status && <VideoStatusBadge job={job} />}

      {/* Export & Redirect Actions — visible whenever content text exists */}
      {bodyText && (
        <ExportActionsBar job={job} contentText={bodyText} />
      )}

      {/* Publish Panel (for approved content) */}
      {isApproved && job.status !== "published" && job.status !== "scheduled" && (
        <PublishPanel job={job} onPublished={() => {}} />
      )}

      {/* Show status for published/scheduled */}
      {(job.status === "published" || job.status === "scheduled") && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className={`mt-4 p-4 rounded-xl flex items-center gap-3 ${
            job.status === "published" ? "bg-green-500/10 border border-green-500/20" : "bg-violet/10 border border-violet/20"
          }`}
        >
          {job.status === "published" ? (
            <>
              <Check size={18} className="text-green-400" />
              <div>
                <p className="text-sm text-white font-medium">Published</p>
                <p className="text-xs text-zinc-500">
                  {job.published_at ? new Date(job.published_at).toLocaleString() : ""}
                </p>
              </div>
            </>
          ) : (
            <>
              <Clock size={18} className="text-violet" />
              <div>
                <p className="text-sm text-white font-medium">Scheduled</p>
                <p className="text-xs text-zinc-500">
                  {job.scheduled_at ? new Date(job.scheduled_at).toLocaleString() : ""}
                </p>
              </div>
            </>
          )}
        </motion.div>
      )}

      {/* Copy button (always visible when content exists) */}
      {bodyText && (
        <div className="flex justify-end mt-4">
          <button
            onClick={handleCopy}
            data-testid="copy-btn"
            className="btn-ghost text-sm px-4 flex items-center gap-2 transition-colors"
            title={copied ? "Copied!" : "Copy to clipboard"}
          >
            {copied ? (
              <>
                <ClipboardCheck size={14} className="text-lime" />
                <span className="text-lime">Copied!</span>
              </>
            ) : (
              <>
                <Copy size={14} />
                <span>Copy</span>
              </>
            )}
          </button>
        </div>
      )}

      {/* Action buttons */}
      {!isApproved && (
        <div className="flex gap-2 mt-2">
          <button
            onClick={handleApprove}
            data-testid="approve-content-btn"
            aria-label="Approve content"
            className="flex-1 btn-primary flex items-center justify-center gap-2 text-sm"
          >
            <Check size={14} /> {editing ? "Save & Approve" : "Approve Content"}
          </button>
          <button
            onClick={() => setEditing(!editing)}
            data-testid="edit-btn"
            className={`btn-ghost text-sm px-4 flex items-center gap-2 ${editing ? "border-lime/30 text-lime" : ""}`}
          >
            <Edit2 size={13} /> {editing ? "Preview" : "Edit"}
          </button>
          <button
            onClick={onRegenerate}
            data-testid="regenerate-btn"
            className="btn-ghost text-sm px-4 flex items-center gap-2"
            title="Regenerate"
          >
            <RefreshCw size={13} />
          </button>
          <button
            onClick={() => setShowRejectionModal(true)}
            data-testid="discard-btn"
            className="btn-ghost text-sm px-3 text-zinc-600 hover:text-red-400"
            title="Reject"
          >
            <X size={14} />
          </button>
        </div>
      )}

      {/* Rejection Modal */}
      <RejectionModal
        isOpen={showRejectionModal}
        onClose={() => setShowRejectionModal(false)}
        onSubmit={handleReject}
      />
    </div>
  );
}

// Schedule/Publish Panel for approved content
function PublishPanel({ job, onPublished }) {
  const [showSchedule, setShowSchedule] = useState(false);
  const [selectedDate, setSelectedDate] = useState("");
  const [selectedTime, setSelectedTime] = useState("");
  const [publishing, setPublishing] = useState(false);
  const [scheduling, setScheduling] = useState(false);
  const [optimalTimes, setOptimalTimes] = useState(null);
  const [loadingTimes, setLoadingTimes] = useState(false);
  const [result, setResult] = useState(null);

  const platform = job.platform || "linkedin";

  const fetchOptimalTimes = async () => {
    setLoadingTimes(true);
    try {
      const res = await apiFetch(`/api/dashboard/schedule/optimal-times?platform=${platform}&count=3`);
      
      if (res.ok) {
        const data = await res.json();
        setOptimalTimes(data);
      }
    } catch (err) {
      console.error("Failed to fetch optimal times:", err);
    } finally {
      setLoadingTimes(false);
    }
  };

  const handlePublishNow = async () => {
    setPublishing(true);
    setResult(null);

    try {
      const res = await apiFetch(`/api/dashboard/publish/${job.job_id}?platforms=${platform}`, {
        method: "POST"
      });
      
      const data = await res.json();
      
      if (data.all_success) {
        setResult({ success: true, message: "Published successfully!", url: data.results?.[platform]?.post_url });
        onPublished?.();
      } else if (data.partial_success) {
        setResult({ success: true, message: "Partially published", platforms: data.successful_platforms });
      } else {
        const error = data.results?.[platform]?.error || "Failed to publish";
        setResult({ success: false, message: error });
      }
    } catch (err) {
      setResult({ success: false, message: "Failed to publish. Please try again." });
    } finally {
      setPublishing(false);
    }
  };

  const handleSchedule = async () => {
    if (!selectedDate || !selectedTime) return;

    setScheduling(true);
    setResult(null);

    try {
      const scheduledAt = new Date(`${selectedDate}T${selectedTime}:00`).toISOString();

      const res = await apiFetch(`/api/dashboard/schedule/content`, {
        method: "POST",
        body: JSON.stringify({
          job_id: job.job_id,
          scheduled_at: scheduledAt,
          platforms: [platform],
        }),
      });
      
      const data = await res.json();
      
      if (data.scheduled) {
        setResult({ success: true, message: data.message || "Content scheduled!" });
        onPublished?.();
      } else {
        setResult({ success: false, message: data.error || "Failed to schedule" });
      }
    } catch (err) {
      setResult({ success: false, message: "Failed to schedule. Please try again." });
    } finally {
      setScheduling(false);
    }
  };

  const selectOptimalTime = (slot) => {
    const dt = new Date(slot.datetime);
    setSelectedDate(dt.toISOString().split("T")[0]);
    setSelectedTime(dt.toTimeString().slice(0, 5));
    setShowSchedule(true);
  };

  // Get min date (today)
  const minDate = new Date().toISOString().split("T")[0];

  return (
    <div className="card-thook p-4 mt-4" data-testid="publish-panel">
      <div className="flex items-center gap-2 mb-3">
        <Send size={14} className="text-lime" />
        <span className="text-xs font-semibold text-zinc-400 uppercase tracking-wider">Publish</span>
      </div>

      {result && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className={`mb-4 p-3 rounded-lg flex items-center gap-3 ${
            result.success ? "bg-lime/10 border border-lime/20" : "bg-red-500/10 border border-red-500/20"
          }`}
        >
          {result.success ? <Check size={16} className="text-lime" /> : <X size={16} className="text-red-400" />}
          <div className="flex-1">
            <p className={`text-sm ${result.success ? "text-white" : "text-red-400"}`}>{result.message}</p>
            {result.url && (
              <a href={result.url} target="_blank" rel="noopener noreferrer" className="text-xs text-lime hover:underline flex items-center gap-1 mt-1">
                View post <ExternalLink size={10} />
              </a>
            )}
          </div>
        </motion.div>
      )}

      {!result?.success && (
        <>
          {/* Quick publish button */}
          <button
            onClick={handlePublishNow}
            disabled={publishing}
            className="w-full py-3 bg-lime text-black rounded-xl text-sm font-semibold hover:bg-lime/90 transition-colors flex items-center justify-center gap-2 disabled:opacity-50"
          >
            {publishing ? (
              <>
                <Loader2 size={14} className="animate-spin" />
                Publishing...
              </>
            ) : (
              <>
                <Send size={14} />
                Publish Now to {platform.charAt(0).toUpperCase() + platform.slice(1)}
              </>
            )}
          </button>

          {/* Schedule toggle */}
          <button
            onClick={() => {
              setShowSchedule(!showSchedule);
              if (!showSchedule && !optimalTimes) fetchOptimalTimes();
            }}
            data-testid="schedule-content-btn"
            aria-label="Open schedule options"
            className="w-full mt-3 py-2 text-xs text-zinc-400 hover:text-white transition-colors flex items-center justify-center gap-2"
          >
            <Calendar size={12} />
            {showSchedule ? "Hide scheduling options" : "Schedule for later"}
          </button>

          {/* Schedule panel */}
          <AnimatePresence>
            {showSchedule && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: "auto" }}
                exit={{ opacity: 0, height: 0 }}
                className="overflow-hidden"
              >
                <div className="pt-4 border-t border-white/5 mt-4">
                  {/* Optimal times suggestions */}
                  {loadingTimes ? (
                    <div className="flex items-center gap-2 text-xs text-zinc-500 mb-4">
                      <Loader2 size={12} className="animate-spin" />
                      Loading optimal times...
                    </div>
                  ) : optimalTimes?.best_times?.length > 0 && (
                    <div className="mb-4">
                      <p className="text-xs text-zinc-500 mb-2">Suggested times:</p>
                      <div className="flex flex-wrap gap-2">
                        {optimalTimes.best_times.map((slot, i) => (
                          <button
                            key={i}
                            onClick={() => selectOptimalTime(slot)}
                            className="text-xs px-3 py-1.5 bg-violet/10 text-violet rounded-lg hover:bg-violet/20 transition-colors"
                          >
                            {slot.display_time}
                          </button>
                        ))}
                      </div>
                      {optimalTimes.reasoning && (
                        <p className="text-[10px] text-zinc-600 mt-2">{optimalTimes.reasoning}</p>
                      )}
                    </div>
                  )}

                  {/* Manual date/time picker */}
                  <div className="flex gap-3">
                    <div className="flex-1">
                      <label className="text-xs text-zinc-500 block mb-1">Date</label>
                      <input
                        type="date"
                        data-testid="schedule-datetime-input"
                        value={selectedDate}
                        onChange={(e) => setSelectedDate(e.target.value)}
                        min={minDate}
                        className="w-full bg-white/5 border border-zinc-800 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-violet"
                      />
                    </div>
                    <div className="flex-1">
                      <label className="text-xs text-zinc-500 block mb-1">Time</label>
                      <input
                        type="time"
                        value={selectedTime}
                        onChange={(e) => setSelectedTime(e.target.value)}
                        className="w-full bg-white/5 border border-zinc-800 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-violet"
                      />
                    </div>
                  </div>

                  <button
                    onClick={handleSchedule}
                    data-testid="schedule-submit-btn"
                    disabled={scheduling || !selectedDate || !selectedTime}
                    className="w-full mt-4 py-2.5 bg-violet/20 text-violet rounded-lg text-sm font-medium hover:bg-violet/30 transition-colors flex items-center justify-center gap-2 disabled:opacity-50"
                  >
                    {scheduling ? (
                      <>
                        <Loader2 size={14} className="animate-spin" />
                        Scheduling...
                      </>
                    ) : (
                      <>
                        <Clock size={14} />
                        Schedule Post
                      </>
                    )}
                  </button>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </>
      )}
    </div>
  );
}

export { ContentOutput as default, PublishPanel };
