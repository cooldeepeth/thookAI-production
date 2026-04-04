import { useState } from 'react';
import { motion } from 'framer-motion';
import { ArrowRight, FileText, UserPlus, Linkedin, Twitter, Instagram } from 'lucide-react';
import { apiFetch } from '@/lib/api';

export default function PhaseOne({ onContinue }) {
  const [mode, setMode] = useState(null); // "existing" | "new"
  const [postsText, setPostsText] = useState('');
  const [platform, setPlatform] = useState('LinkedIn');
  const [analyzing, setAnalyzing] = useState(false);
  const [result, setResult] = useState(null);

  const handleAnalyze = async () => {
    if (!postsText.trim()) { onContinue(null); return; }
    setAnalyzing(true);
    try {
      const res = await apiFetch('/api/onboarding/analyze-posts', {
        method: 'POST',
        body: JSON.stringify({ posts_text: postsText, platform }),
      });
      const data = await res.json();
      setResult(data);
    } catch {
      setResult({ analysis: "Posts noted. We'll use them to calibrate your voice.", demo_mode: true });
    } finally {
      setAnalyzing(false);
    }
  };

  const platformIcons = { LinkedIn: Linkedin, 'X (Twitter)': Twitter, Instagram };

  if (result) {
    return (
      <div className="flex items-center justify-center min-h-full p-8">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="max-w-xl w-full">
          <div className="w-12 h-12 bg-lime/15 rounded-2xl flex items-center justify-center mx-auto mb-6">
            <span className="text-xl">✓</span>
          </div>
          <h2 className="font-display font-bold text-2xl text-white text-center mb-2">Posts analyzed</h2>
          <p className="text-zinc-500 text-sm text-center mb-6">Here's what we learned from your writing</p>
          <div className="card-thook p-5 mb-6">
            <p className="text-sm text-zinc-300 leading-relaxed">{result.analysis}</p>
          </div>
          <button
            onClick={() => onContinue(result)}
            data-testid="proceed-to-interview-btn"
            className="w-full btn-primary flex items-center justify-center gap-2"
          >
            Continue to interview <ArrowRight size={16} />
          </button>
        </motion.div>
      </div>
    );
  }

  return (
    <div className="flex items-center justify-center min-h-full p-8">
      <div className="max-w-2xl w-full">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="text-center mb-10">
          <p className="text-lime text-xs font-semibold uppercase tracking-widest mb-3">Phase 1 of 3</p>
          <h2 className="font-display font-bold text-3xl md:text-4xl text-white mb-3">Do you have existing content?</h2>
          <p className="text-zinc-500 text-sm max-w-md mx-auto">
            Sharing your past posts gives Thook a head start on learning your voice. You can skip this if you're just starting out.
          </p>
        </motion.div>

        {!mode ? (
          <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }} className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <button
              onClick={() => setMode('existing')}
              data-testid="option-existing-creator"
              className="card-thook p-6 text-left hover:border-lime/20 transition-all group"
            >
              <div className="w-10 h-10 bg-lime/10 rounded-xl flex items-center justify-center mb-4 group-hover:bg-lime/20 transition-colors">
                <FileText size={20} className="text-lime" />
              </div>
              <h3 className="font-display font-semibold text-white mb-1">I'm an existing creator</h3>
              <p className="text-zinc-500 text-sm">Paste some posts and we'll analyze your writing style. Gives your Persona Engine a stronger start.</p>
              <div className="flex items-center gap-1 mt-4 text-lime text-xs font-semibold">
                Recommended <ArrowRight size={12} />
              </div>
            </button>

            <button
              onClick={() => onContinue(null)}
              data-testid="option-new-creator"
              className="card-thook p-6 text-left hover:border-white/10 transition-all group"
            >
              <div className="w-10 h-10 bg-white/5 rounded-xl flex items-center justify-center mb-4 group-hover:bg-white/10 transition-colors">
                <UserPlus size={20} className="text-zinc-400" />
              </div>
              <h3 className="font-display font-semibold text-white mb-1">I'm just starting out</h3>
              <p className="text-zinc-500 text-sm">No posts yet? No problem. We'll build your Persona through a short interview instead.</p>
              <div className="flex items-center gap-1 mt-4 text-zinc-500 text-xs">
                Skip to interview <ArrowRight size={12} />
              </div>
            </button>
          </motion.div>
        ) : (
          <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}>
            {/* Platform selector */}
            <div className="flex gap-2 mb-4">
              {['LinkedIn', 'X (Twitter)', 'Instagram'].map(p => {
                const Icon = platformIcons[p] || FileText;
                return (
                  <button
                    key={p}
                    onClick={() => setPlatform(p)}
                    data-testid={`platform-${p.toLowerCase().replace(/\s+/g, '-')}`}
                    className={`flex items-center gap-2 px-4 py-2 rounded-full text-xs font-medium transition-colors border ${
                      platform === p ? 'bg-lime/15 border-lime/30 text-lime' : 'bg-white/5 border-white/10 text-zinc-400 hover:text-white'
                    }`}
                  >
                    <Icon size={13} /> {p}
                  </button>
                );
              })}
            </div>

            <textarea
              value={postsText}
              onChange={e => setPostsText(e.target.value)}
              data-testid="posts-textarea"
              placeholder="Paste 5–10 of your best posts here. The more you share, the better your Persona Engine will be calibrated..."
              className="w-full h-52 bg-[#18181B] border border-white/10 focus:border-lime/40 focus:ring-1 focus:ring-lime/20 text-white rounded-xl p-4 text-sm placeholder:text-zinc-600 outline-none resize-none transition-colors"
            />
            <p className="text-zinc-600 text-xs mt-2 mb-6">
              Your posts are only used to train your personal Persona Engine and are never shared.
            </p>

            <div className="flex gap-3">
              <button onClick={() => setMode(null)} className="btn-ghost text-sm px-5 py-2.5">Back</button>
              <button
                onClick={handleAnalyze}
                disabled={analyzing}
                data-testid="analyze-posts-btn"
                className="flex-1 btn-primary flex items-center justify-center gap-2 text-sm disabled:opacity-60"
              >
                {analyzing ? (
                  <><span className="w-4 h-4 border-2 border-black/30 border-t-black rounded-full animate-spin" /> Analyzing your style...</>
                ) : (
                  <>{postsText.trim() ? 'Analyze my posts' : 'Skip this step'} <ArrowRight size={15} /></>
                )}
              </button>
            </div>
          </motion.div>
        )}
      </div>
    </div>
  );
}
