import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '@/context/AuthContext';
import { motion, AnimatePresence } from 'framer-motion';
import PhaseOne from './PhaseOne';
import PhaseTwo from './PhaseTwo';
import PhaseThree from './PhaseThree';
import { Zap } from 'lucide-react';
import { apiFetch } from '@/lib/api';

const phases = [
  { num: 1, label: 'Profile Analysis' },
  { num: 2, label: 'Interview' },
  { num: 3, label: 'Persona Reveal' },
];

export default function OnboardingWizard() {
  const [phase, setPhase] = useState(1);
  const [postsAnalysis, setPostsAnalysis] = useState(null);
  const [personaCard, setPersonaCard] = useState(null);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState('');
  const [lastAnswers, setLastAnswers] = useState(null);
  const { user, checkAuth } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (user?.onboarding_completed) navigate('/dashboard/persona', { replace: true });
  }, [user, navigate]);

  const handlePhaseOneComplete = (analysis) => {
    setPostsAnalysis(analysis);
    setPhase(2);
  };

  const submitPersona = async (answers) => {
    setPhase(3);
    setGenerating(true);
    setError('');
    setLastAnswers(answers);
    try {
      const res = await apiFetch('/api/onboarding/generate-persona', {
        method: 'POST',
        body: JSON.stringify({ answers, posts_analysis: postsAnalysis?.analysis || null }),
      });
      if (!res.ok) throw new Error('Failed to generate persona');
      const data = await res.json();
      setPersonaCard(data.persona_card);
      await checkAuth();
    } catch (e) {
      setError('Something went wrong generating your persona. Please try again.');
    } finally {
      setGenerating(false);
    }
  };

  const handlePhaseTwoComplete = (answers) => submitPersona(answers);

  const handleRetry = () => {
    if (lastAnswers) {
      submitPersona(lastAnswers);
    } else {
      setPhase(2);
    }
  };

  return (
    <div className="min-h-screen bg-[#050505] flex flex-col" data-testid="onboarding-wizard">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-white/5">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 bg-lime rounded-lg flex items-center justify-center">
            <Zap size={14} className="text-black" fill="black" />
          </div>
          <span className="font-display font-bold text-white">Thook</span>
        </div>

        {/* Progress stepper */}
        <div className="flex items-center gap-2">
          {phases.map((p, i) => (
            <div key={p.num} className="flex items-center gap-2">
              <div className={`flex items-center gap-2 transition-all ${phase === p.num ? 'opacity-100' : phase > p.num ? 'opacity-60' : 'opacity-30'}`}>
                <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold transition-colors ${
                  phase > p.num ? 'bg-lime text-black' : phase === p.num ? 'bg-white text-black' : 'bg-white/10 text-zinc-500'
                }`}>
                  {phase > p.num ? '✓' : p.num}
                </div>
                <span className="text-xs text-zinc-400 hidden sm:block">{p.label}</span>
              </div>
              {i < phases.length - 1 && (
                <div className={`w-8 h-px mx-1 transition-colors ${phase > p.num ? 'bg-lime/50' : 'bg-white/10'}`} />
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

      {/* Phase content */}
      <div className="flex-1 flex flex-col">
        <AnimatePresence mode="wait">
          {phase === 1 && (
            <motion.div key="phase1" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }} transition={{ duration: 0.3 }} className="flex-1">
              <PhaseOne onContinue={handlePhaseOneComplete} />
            </motion.div>
          )}
          {phase === 2 && (
            <motion.div key="phase2" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }} transition={{ duration: 0.3 }} className="flex-1">
              <PhaseTwo onComplete={handlePhaseTwoComplete} postsAnalysis={postsAnalysis} />
            </motion.div>
          )}
          {phase === 3 && (
            <motion.div key="phase3" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }} transition={{ duration: 0.3 }} className="flex-1">
              <PhaseThree personaCard={personaCard} generating={generating} error={error} user={user} onRetry={handleRetry} />
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
