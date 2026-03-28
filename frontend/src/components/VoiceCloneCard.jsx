import { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Mic, Upload, Trash2, Play, Pause, AlertCircle, Lock, CheckCircle2, Loader2, X } from "lucide-react";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const ALLOWED_AUDIO_TYPES = [
  "audio/mpeg",
  "audio/wav",
  "audio/x-wav",
  "audio/mp4",
  "audio/ogg",
  "audio/aac",
  "audio/flac",
  "audio/mp3",
];

const MAX_SAMPLES = 5;
const MAX_FILE_SIZE = 25 * 1024 * 1024; // 25 MB

function formatBytes(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function AudioSampleItem({ file, onRemove, index }) {
  const [playing, setPlaying] = useState(false);
  const audioRef = useRef(null);
  const urlRef = useRef(null);

  // Create object URL for preview
  useEffect(() => {
    urlRef.current = URL.createObjectURL(file);
    return () => {
      if (urlRef.current) URL.revokeObjectURL(urlRef.current);
    };
  }, [file]);

  const togglePlay = () => {
    if (!audioRef.current) return;
    if (playing) {
      audioRef.current.pause();
    } else {
      audioRef.current.play();
    }
    setPlaying(!playing);
  };

  return (
    <div className="flex items-center gap-3 bg-white/5 rounded-lg px-3 py-2.5 border border-white/5">
      <button
        onClick={togglePlay}
        className="w-7 h-7 rounded-full bg-violet/20 flex items-center justify-center flex-shrink-0 hover:bg-violet/30 transition-colors"
      >
        {playing ? <Pause size={12} className="text-violet" /> : <Play size={12} className="text-violet ml-0.5" />}
      </button>
      <audio
        ref={audioRef}
        src={urlRef.current}
        onEnded={() => setPlaying(false)}
        preload="metadata"
      />
      <div className="flex-1 min-w-0">
        <p className="text-xs text-white truncate">{file.name}</p>
        <p className="text-[10px] text-zinc-600">{formatBytes(file.size)}</p>
      </div>
      <button
        onClick={() => onRemove(index)}
        className="w-6 h-6 rounded flex items-center justify-center text-zinc-600 hover:text-red-400 hover:bg-red-400/10 transition-colors"
      >
        <X size={13} />
      </button>
    </div>
  );
}

export default function VoiceCloneCard({ user }) {
  const tier = user?.subscription_tier || user?.plan || "free";
  const isEligible = tier === "studio" || tier === "agency";

  const [cloneStatus, setCloneStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [files, setFiles] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [creating, setCreating] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [voiceName, setVoiceName] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

  const fileInputRef = useRef(null);

  // Fetch clone status on mount
  useEffect(() => {
    fetchCloneStatus();
  }, []);

  const fetchCloneStatus = async () => {
    try {
      const res = await fetch(`${BACKEND_URL}/api/persona/voice-clone`, {
        credentials: "include",
      });
      if (res.ok) {
        const data = await res.json();
        setCloneStatus(data);
      }
    } catch {
      // Swallow
    } finally {
      setLoading(false);
    }
  };

  const handleFileSelect = (e) => {
    setError("");
    const selected = Array.from(e.target.files || []);

    // Validate
    for (const f of selected) {
      if (!ALLOWED_AUDIO_TYPES.includes(f.type)) {
        setError(`"${f.name}" is not a supported audio format.`);
        return;
      }
      if (f.size > MAX_FILE_SIZE) {
        setError(`"${f.name}" exceeds the 25 MB limit.`);
        return;
      }
    }

    const combined = [...files, ...selected].slice(0, MAX_SAMPLES);
    setFiles(combined);

    // Reset the input so the same file can be selected again
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const removeFile = (index) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const handleUploadSamples = async () => {
    if (files.length === 0) return;
    setUploading(true);
    setError("");
    setSuccess("");

    try {
      const formData = new FormData();
      for (const f of files) {
        formData.append("files", f);
      }

      const res = await fetch(`${BACKEND_URL}/api/persona/voice-clone/samples`, {
        method: "POST",
        credentials: "include",
        body: formData,
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        setError(err.detail || "Failed to upload samples.");
        return;
      }

      const data = await res.json();
      setSuccess(data.message || "Samples uploaded.");
      setFiles([]);
      await fetchCloneStatus();
    } catch {
      setError("Network error. Please try again.");
    } finally {
      setUploading(false);
    }
  };

  const handleCreateClone = async () => {
    if (!voiceName.trim()) {
      setError("Please enter a name for your voice clone.");
      return;
    }
    setCreating(true);
    setError("");
    setSuccess("");

    try {
      const res = await fetch(`${BACKEND_URL}/api/persona/voice-clone/create`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ voice_name: voiceName.trim() }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        setError(err.detail || "Voice clone creation failed.");
        return;
      }

      const data = await res.json();
      setSuccess(data.message || "Voice clone created!");
      setVoiceName("");
      await fetchCloneStatus();
    } catch {
      setError("Network error. Please try again.");
    } finally {
      setCreating(false);
    }
  };

  const handleDeleteClone = async () => {
    setDeleting(true);
    setError("");
    setSuccess("");

    try {
      const res = await fetch(`${BACKEND_URL}/api/persona/voice-clone`, {
        method: "DELETE",
        credentials: "include",
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        setError(err.detail || "Failed to delete voice clone.");
        return;
      }

      setSuccess("Voice clone deleted.");
      setShowDeleteConfirm(false);
      await fetchCloneStatus();
    } catch {
      setError("Network error. Please try again.");
    } finally {
      setDeleting(false);
    }
  };

  // ---- Locked state for free/pro ----
  if (!isEligible) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.25 }}
        className="card-thook p-5 relative overflow-hidden"
      >
        <div className="absolute inset-0 bg-black/40 backdrop-blur-[2px] z-10 flex flex-col items-center justify-center">
          <Lock size={24} className="text-zinc-500 mb-2" />
          <p className="text-sm text-zinc-400 font-semibold">Voice Cloning</p>
          <p className="text-xs text-zinc-600 mt-1">Available on Studio & Agency plans</p>
          <a
            href="/dashboard/settings"
            className="mt-3 text-xs text-violet font-semibold hover:underline"
          >
            Upgrade to unlock
          </a>
        </div>
        <div className="opacity-30 pointer-events-none">
          <div className="flex items-center gap-2 mb-3">
            <Mic size={16} className="text-violet" />
            <h3 className="font-display font-semibold text-white text-sm">Voice Clone</h3>
          </div>
          <p className="text-zinc-500 text-xs">Clone your voice from audio samples for AI-narrated content.</p>
          <div className="mt-4 h-20 bg-white/5 rounded-lg" />
        </div>
      </motion.div>
    );
  }

  // ---- Loading ----
  if (loading) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.25 }}
        className="card-thook p-5 flex items-center justify-center min-h-[120px]"
      >
        <div className="w-5 h-5 border-2 border-lime border-t-transparent rounded-full animate-spin" />
      </motion.div>
    );
  }

  const hasClone = cloneStatus?.has_clone;
  const hasSamples = (cloneStatus?.sample_count || 0) > 0;

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.25 }}
      className="card-thook p-5"
      data-testid="voice-clone-card"
    >
      <div className="flex items-center gap-2 mb-1">
        <Mic size={16} className="text-violet" />
        <h3 className="font-display font-semibold text-white text-sm">Voice Clone</h3>
        {hasClone && (
          <span className="ml-auto flex items-center gap-1 text-[10px] text-lime font-mono">
            <CheckCircle2 size={11} /> ACTIVE
          </span>
        )}
      </div>
      <p className="text-zinc-500 text-xs mb-4">
        {hasClone
          ? "Your voice clone is active and will be used for AI narrations."
          : "Upload 1-5 audio samples of your voice to create a custom clone."}
      </p>

      {/* ---- Error / Success ---- */}
      <AnimatePresence>
        {error && (
          <motion.div
            initial={{ opacity: 0, y: -4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className="flex items-start gap-2 bg-red-500/10 border border-red-500/20 rounded-lg px-3 py-2.5 mb-3"
          >
            <AlertCircle size={14} className="text-red-400 mt-0.5 flex-shrink-0" />
            <p className="text-xs text-red-400">{error}</p>
          </motion.div>
        )}
        {success && (
          <motion.div
            initial={{ opacity: 0, y: -4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className="flex items-start gap-2 bg-lime/10 border border-lime/20 rounded-lg px-3 py-2.5 mb-3"
          >
            <CheckCircle2 size={14} className="text-lime mt-0.5 flex-shrink-0" />
            <p className="text-xs text-lime">{success}</p>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ---- Active clone display ---- */}
      {hasClone && (
        <div className="space-y-3">
          <div className="bg-violet/5 border border-violet/20 rounded-lg px-4 py-3">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-white font-semibold">{cloneStatus.voice_name}</p>
                <p className="text-[10px] text-zinc-500 mt-0.5">
                  Voice ID: {cloneStatus.voice_id?.slice(0, 12)}...
                </p>
              </div>
              <button
                onClick={() => setShowDeleteConfirm(true)}
                className="text-xs text-zinc-500 hover:text-red-400 flex items-center gap-1 transition-colors"
              >
                <Trash2 size={12} /> Delete
              </button>
            </div>
          </div>

          {/* Delete confirmation */}
          <AnimatePresence>
            {showDeleteConfirm && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: "auto" }}
                exit={{ opacity: 0, height: 0 }}
                className="overflow-hidden"
              >
                <div className="bg-red-500/5 border border-red-500/20 rounded-lg px-4 py-3">
                  <p className="text-xs text-red-400 mb-2">
                    This will permanently delete your voice clone from ElevenLabs. Are you sure?
                  </p>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={handleDeleteClone}
                      disabled={deleting}
                      className="flex items-center gap-1 text-xs bg-red-500/20 text-red-400 border border-red-500/30 rounded-lg px-3 py-1.5 hover:bg-red-500/30 transition-colors disabled:opacity-50"
                    >
                      {deleting && <Loader2 size={12} className="animate-spin" />}
                      {deleting ? "Deleting..." : "Yes, delete"}
                    </button>
                    <button
                      onClick={() => setShowDeleteConfirm(false)}
                      className="text-xs text-zinc-500 hover:text-white px-3 py-1.5"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      )}

      {/* ---- Upload & create flow (no clone yet) ---- */}
      {!hasClone && (
        <div className="space-y-3">
          {/* File list */}
          {files.length > 0 && (
            <div className="space-y-2">
              {files.map((f, i) => (
                <AudioSampleItem key={`${f.name}-${i}`} file={f} index={i} onRemove={removeFile} />
              ))}
            </div>
          )}

          {/* Upload zone */}
          {files.length < MAX_SAMPLES && (
            <label
              className="flex flex-col items-center justify-center border-2 border-dashed border-white/10 rounded-lg py-5 px-4 cursor-pointer hover:border-violet/40 hover:bg-violet/5 transition-colors"
            >
              <Upload size={20} className="text-zinc-500 mb-2" />
              <p className="text-xs text-zinc-400 text-center">
                Drop audio files or <span className="text-violet font-semibold">browse</span>
              </p>
              <p className="text-[10px] text-zinc-600 mt-1">
                MP3, WAV, OGG, M4A -- up to 25 MB each -- {MAX_SAMPLES - files.length} slot{MAX_SAMPLES - files.length !== 1 ? "s" : ""} remaining
              </p>
              <input
                ref={fileInputRef}
                type="file"
                accept="audio/*"
                multiple
                className="hidden"
                onChange={handleFileSelect}
              />
            </label>
          )}

          {/* Upload button (when files selected but not yet uploaded) */}
          {files.length > 0 && !hasSamples && (
            <button
              onClick={handleUploadSamples}
              disabled={uploading}
              className="w-full flex items-center justify-center gap-2 bg-violet/20 text-violet border border-violet/30 rounded-lg px-4 py-2.5 text-sm font-semibold hover:bg-violet/30 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {uploading ? (
                <Loader2 size={14} className="animate-spin" />
              ) : (
                <Upload size={14} />
              )}
              {uploading ? "Uploading..." : `Upload ${files.length} Sample${files.length !== 1 ? "s" : ""}`}
            </button>
          )}

          {/* Samples uploaded, show create button */}
          {hasSamples && !hasClone && (
            <div className="space-y-3 pt-1">
              <div className="bg-white/5 rounded-lg px-3 py-2.5 border border-white/5">
                <p className="text-xs text-zinc-400">
                  {cloneStatus.sample_count} sample{cloneStatus.sample_count !== 1 ? "s" : ""} uploaded
                </p>
              </div>

              {/* If user wants to replace samples */}
              {files.length > 0 && (
                <button
                  onClick={handleUploadSamples}
                  disabled={uploading}
                  className="w-full flex items-center justify-center gap-2 bg-white/5 text-zinc-300 border border-white/10 rounded-lg px-4 py-2 text-xs font-semibold hover:bg-white/10 transition-colors disabled:opacity-50"
                >
                  {uploading ? (
                    <Loader2 size={12} className="animate-spin" />
                  ) : (
                    <Upload size={12} />
                  )}
                  {uploading ? "Uploading..." : "Replace samples"}
                </button>
              )}

              {/* Voice name input + create button */}
              <div>
                <label className="text-[10px] text-zinc-600 uppercase tracking-wider mb-1 block">
                  Voice Name
                </label>
                <input
                  type="text"
                  value={voiceName}
                  onChange={(e) => setVoiceName(e.target.value)}
                  placeholder="e.g., My Voice"
                  maxLength={50}
                  className="w-full bg-[#18181B] border border-white/10 text-white rounded-lg px-3 py-2 text-sm outline-none focus:border-violet/40 placeholder-zinc-700"
                />
              </div>

              <button
                onClick={handleCreateClone}
                disabled={creating || !voiceName.trim()}
                className="w-full flex items-center justify-center gap-2 bg-violet text-white rounded-lg px-4 py-2.5 text-sm font-semibold hover:bg-violet/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {creating ? (
                  <Loader2 size={14} className="animate-spin" />
                ) : (
                  <Mic size={14} />
                )}
                {creating ? "Creating Voice Clone..." : "Create My Voice Clone"}
              </button>
            </div>
          )}
        </div>
      )}
    </motion.div>
  );
}
