import { Linkedin, Twitter, Instagram, Zap } from "lucide-react";

const PLATFORMS = [
  { id: "linkedin", label: "LinkedIn", icon: Linkedin, color: "#0A66C2",
    types: [{ id: "post", label: "Post" }, { id: "carousel_caption", label: "Carousel" }] },
  { id: "x", label: "X", icon: Twitter, color: "#1D9BF0",
    types: [{ id: "tweet", label: "Tweet" }, { id: "thread", label: "Thread" }] },
  { id: "instagram", label: "Instagram", icon: Instagram, color: "#E1306C",
    types: [{ id: "feed_caption", label: "Feed Post" }, { id: "reel_caption", label: "Reel" }] },
];

const PLACEHOLDERS = {
  linkedin: "What do you want to write about?\n\ne.g. '5 lessons I learned scaling to $1M ARR' or 'Why remote teams outperform in-office teams'",
  x: "What's your take? What thread idea do you have?\n\ne.g. 'Thread: Why most LinkedIn advice is wrong (and what actually works)'",
  instagram: "Caption idea or topic?\n\ne.g. 'Behind-the-scenes of our product launch' or 'My morning routine for peak productivity'",
};

export default function InputPanel({ platform, contentType, rawInput, onPlatformChange, onContentTypeChange, onInputChange, onGenerate, isRunning, error }) {
  const cfg = PLATFORMS.find(p => p.id === platform) || PLATFORMS[0];
  const Icon = cfg.icon;

  const handlePlatformChange = (id) => {
    onPlatformChange(id);
    const p = PLATFORMS.find(pl => pl.id === id);
    if (p) onContentTypeChange(p.types[0].id);
  };

  return (
    <div className="p-5 flex flex-col h-full" data-testid="input-panel">
      {/* Platform selector */}
      <div className="mb-5">
        <p className="text-xs text-zinc-500 uppercase tracking-wider mb-2 font-mono">Platform</p>
        <div className="flex gap-1.5">
          {PLATFORMS.map(p => {
            const PIcon = p.icon;
            return (
              <button
                key={p.id}
                onClick={() => handlePlatformChange(p.id)}
                data-testid={`platform-tab-${p.id}`}
                className={`flex-1 flex flex-col items-center gap-1 py-2.5 rounded-xl border transition-all ${
                  platform === p.id ? "border-white/20 bg-white/5" : "border-white/5 hover:border-white/10"
                }`}
              >
                <PIcon size={16} style={{ color: platform === p.id ? p.color : "#52525B" }} />
                <span className={`text-[10px] font-medium ${platform === p.id ? "text-white" : "text-zinc-600"}`}>{p.label}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Content type */}
      <div className="mb-5">
        <p className="text-xs text-zinc-500 uppercase tracking-wider mb-2 font-mono">Format</p>
        <div className="flex gap-1.5">
          {cfg.types.map(t => (
            <button
              key={t.id}
              onClick={() => onContentTypeChange(t.id)}
              data-testid={`content-type-${t.id}`}
              className={`flex-1 py-2 rounded-lg text-xs font-medium transition-colors border ${
                contentType === t.id
                  ? "border-white/20 bg-white/8 text-white"
                  : "border-white/5 text-zinc-500 hover:text-zinc-300"
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>

      {/* Platform-native composer look */}
      <div className="flex-1 flex flex-col">
        <div
          className="flex-1 rounded-xl border overflow-hidden"
          style={{ borderColor: `${cfg.color}20` }}
        >
          {/* Composer header */}
          <div className="flex items-center gap-2 px-3 py-2 border-b" style={{ borderColor: `${cfg.color}15`, backgroundColor: `${cfg.color}08` }}>
            <Icon size={13} style={{ color: cfg.color }} />
            <span className="text-xs font-medium" style={{ color: cfg.color }}>{cfg.label} {cfg.types.find(t => t.id === contentType)?.label}</span>
          </div>

          <textarea
            value={rawInput}
            onChange={e => onInputChange(e.target.value)}
            placeholder={PLACEHOLDERS[platform]}
            data-testid="content-input-textarea"
            disabled={isRunning}
            className="w-full h-48 bg-[#18181B] text-white text-sm placeholder:text-zinc-700 p-4 outline-none resize-none disabled:opacity-50"
          />

          {/* Character counter */}
          <div className="px-3 py-2 border-t border-white/5 flex justify-end">
            <span className={`text-xs font-mono ${rawInput.length > 2500 ? "text-red-400" : "text-zinc-700"}`}>
              {rawInput.length} chars
            </span>
          </div>
        </div>

        {error && (
          <p data-testid="studio-error" className="text-red-400 text-xs mt-2">{error}</p>
        )}

        {/* Generate button */}
        <button
          onClick={onGenerate}
          disabled={isRunning || !rawInput.trim()}
          data-testid="generate-content-btn"
          className="mt-4 w-full btn-primary flex items-center justify-center gap-2 text-sm disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isRunning ? (
            <><span className="w-4 h-4 border-2 border-black/30 border-t-black rounded-full animate-spin" /> Agents at work...</>
          ) : (
            <><Zap size={14} fill="black" /> Generate with AI</>
          )}
        </button>

        <p className="text-center text-zinc-700 text-xs mt-2">~45–60 seconds · 5 agents · your voice</p>
      </div>
    </div>
  );
}
