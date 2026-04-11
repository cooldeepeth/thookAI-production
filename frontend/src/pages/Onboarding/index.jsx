import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '@/context/AuthContext';
import { motion, AnimatePresence } from 'framer-motion';
import PhaseOne from './PhaseOne';
import PhaseTwo from './PhaseTwo';
import PhaseThree from './PhaseThree';
import { Zap, ChevronLeft } from 'lucide-react';
import { apiFetch } from '@/lib/api';

const steps = [
  { num: 1, label: 'Writing Style' },
  { num: 2, label: 'Voice Sample' },
  { num: 3, label: 'Visual Style' },
  { num: 4, label: 'Interview' },
  { num: 5, label: 'Your Persona' },
];

export default function OnboardingWizard() {
  const [phase, setPhase] = useState(1);
  const [postsAnalysis, setPostsAnalysis] = useState(null);
  const [personaCard, setPersonaCard] = useState(null);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState('');
  const [lastAnswers, setLastAnswers] = useState(null);
  const [voiceSampleUrl, setVoiceSampleUrl] = useState(null);
  const [visualPreference, setVisualPreference] = useState(null);
  const [writingSamples, setWritingSamples] = useState([]);
  const { user, checkAuth } = useAuth();
  const navigate = useNavigate();

  const DRAFT_KEY = 'thook_onboarding_draft_v2';

  const saveDraft = (updates) => {
    try {
      const existing = JSON.parse(localStorage.getItem(DRAFT_KEY) || '{}');
      localStorage.setItem(DRAFT_KEY, JSON.stringify({ ...existing, ...updates, savedAt: Date.now() }));
    } catch { /* ignore storage errors */ }
  };

  const loadDraft = () => {
    try { return JSON.parse(localStorage.getItem(DRAFT_KEY) || 'null'); }
    catch { return null; }
  };

  const clearDraft = () => { try { localStorage.removeItem(DRAFT_KEY); } catch { /* ignore */ } };

  useEffect(() => {
    if (user?.onboarding_completed) navigate('/dashboard/persona', { replace: true });
  }, [user, navigate]);

  useEffect(() => {
    if (user?.onboarding_completed) return; // never restore if already done
    const draft = loadDraft();
    if (draft && draft.step) {
      setPhase(Math.min(draft.step, 4)); // never restore to step 5 (persona reveal needs re-generation)
      if (draft.postsAnalysis) setPostsAnalysis(draft.postsAnalysis);
      if (draft.writingSamples) setWritingSamples(draft.writingSamples);
      if (draft.visualPreference) setVisualPreference(draft.visualPreference);
      if (draft.voiceSampleUrl) setVoiceSampleUrl(draft.voiceSampleUrl);
    }
  }, [user]); // eslint-disable-line react-hooks/exhaustive-deps

  const handlePhaseOneComplete = (analysis, samples = []) => {
    setPostsAnalysis(analysis);
    setWritingSamples(samples);
    saveDraft({ step: 2, postsAnalysis: analysis, writingSamples: samples });
    setPhase(2);
  };

  const handleVoiceComplete = (url) => {
    setVoiceSampleUrl(url);
    saveDraft({ step: 3, voiceSampleUrl: url });
    setPhase(3);
  };

  const handleVisualComplete = (preference) => {
    setVisualPreference(preference);
    saveDraft({ step: 4, visualPreference: preference });
    setPhase(4);
  };

  const handleInterviewComplete = (answers) => submitPersona(answers);

  const handleBack = () => {
    if (phase > 1 && phase < 5) setPhase(phase - 1);
  };

  const submitPersona = async (answers) => {
    if (generating) return; // Prevent double-submit
    setPhase(5);
    setGenerating(true);
    setError('');
    setLastAnswers(answers);
    try {
      const res = await apiFetch('/api/onboarding/generate-persona', {
        method: 'POST',
        body: JSON.stringify({
          answers,
          posts_analysis: postsAnalysis?.analysis || null,
          voice_sample_url: voiceSampleUrl || null,
          visual_preference: visualPreference || null,
          writing_samples: writingSamples.length > 0 ? writingSamples : null,
        }),
      });
      if (!res.ok) throw new Error('Failed to generate persona');
      const data = await res.json();
      setPersonaCard(data.persona_card);
      clearDraft(); // CRITICAL: clear draft after success
      await checkAuth();
    } catch (e) {
      setError('Something went wrong generating your persona. Please try again.');
    } finally {
      setGenerating(false);
    }
  };

  const handleRetry = () => {
    if (lastAnswers) {
      submitPersona(lastAnswers);
    } else {
      setPhase(4); // go back to interview step
    }
  };

  return (
    <div className="min-h-screen bg-[#050505] flex flex-col" data-testid="onboarding-wizard">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-white/5">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 bg-lime rounded-lg flex items-center justify-center">
              <Zap size={14} className="text-black" fill="black" />
            </div>
            <span className="font-display font-bold text-white">Thook</span>
          </div>

          {/* Back button — visible on steps 2-4 only */}
          {phase > 1 && phase < 5 && (
            <button
              onClick={handleBack}
              className="text-xs text-zinc-500 hover:text-white transition-colors flex items-center gap-1"
              aria-label="Go back to previous step"
            >
              <ChevronLeft size={14} /> Back
            </button>
          )}
        </div>

        {/* Progress stepper */}
        <div className="flex items-center gap-2" data-testid="onboarding-stepper">
          {steps.map((s, i) => (
            <div key={s.num} className="flex items-center gap-2">
              <div className={`flex items-center gap-2 transition-all ${phase === s.num ? 'opacity-100' : phase > s.num ? 'opacity-60' : 'opacity-30'}`}>
                <div
                  data-testid={`step-dot-${s.num}`}
                  className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold transition-colors ${
                    phase > s.num ? 'bg-lime text-black' : phase === s.num ? 'bg-white text-black' : 'bg-white/10 text-zinc-500'
                  }`}
                >
                  {phase > s.num ? '✓' : s.num}
                </div>
                <span className="text-xs text-zinc-400 hidden sm:block">{s.label}</span>
              </div>
              {i < steps.length - 1 && (
                <div className={`w-8 h-px mx-1 transition-colors ${phase > s.num ? 'bg-lime/50' : 'bg-white/10'}`} />
              )}
            </div>
          ))}
        </div>

        <button
          onClick={() => navigate('/dashboard')}
          className="text-xs text-zinc-600 hover:text-zinc-400 transition-colors"
          data-testid="skip-onboarding-btn"
        >
          Skip for now
        </button>
      </div>

      {/* Step content */}
      <div className="flex-1 flex flex-col">
        <AnimatePresence mode="wait">
          {phase === 1 && (
            <motion.div key="step1" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }} transition={{ duration: 0.3 }} className="flex-1">
              <PhaseOne onContinue={handlePhaseOneComplete} />
            </motion.div>
          )}
          {phase === 2 && (
            <motion.div key="step2" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }} transition={{ duration: 0.3 }} className="flex-1">
              {/* VoiceRecordingStep — wired in Plan 04 */}
              <div className="flex items-center justify-center min-h-full p-8">
                <div className="text-center">
                  <p className="text-zinc-500 text-sm">Voice recording step coming soon...</p>
                  <button onClick={() => handleVoiceComplete(null)} className="mt-4 btn-primary text-sm">Skip for now</button>
                </div>
              </div>
            </motion.div>
          )}
          {phase === 3 && (
            <motion.div key="step3" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }} transition={{ duration: 0.3 }} className="flex-1">
              {/* VisualPaletteStep — wired in Plan 04 */}
              <div className="flex items-center justify-center min-h-full p-8">
                <div className="text-center">
                  <p className="text-zinc-500 text-sm">Visual style step coming soon...</p>
                  <button onClick={() => handleVisualComplete('minimal')} className="mt-4 btn-primary text-sm">Continue</button>
                </div>
              </div>
            </motion.div>
          )}
          {phase === 4 && (
            <motion.div key="step4" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }} transition={{ duration: 0.3 }} className="flex-1">
              <PhaseTwo onComplete={handleInterviewComplete} postsAnalysis={postsAnalysis} />
            </motion.div>
          )}
          {phase === 5 && (
            <motion.div key="step5" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }} transition={{ duration: 0.3 }} className="flex-1">
              <PhaseThree personaCard={personaCard} generating={generating} error={error} user={user} onRetry={handleRetry} />
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
