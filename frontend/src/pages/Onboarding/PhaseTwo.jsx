import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ArrowRight, ChevronLeft, Zap } from "lucide-react";

const QUESTIONS = [
  { id: 0, type: "text", question: "Let's start — who are you and what do you create? Tell me in 2-3 sentences.", placeholder: "e.g. I'm a B2B SaaS founder sharing lessons on growing from 0 to $1M ARR...", hint: "Be specific — 'content creator' is too broad. What's your unique angle?" },
  { id: 1, type: "multi_choice", question: "Which platforms are most important to your content strategy right now?", options: ["LinkedIn", "X (Twitter)", "Instagram", "LinkedIn + X", "All three"], hint: "Focus beats presence. Pick where your audience actually lives." },
  { id: 2, type: "text", question: "Describe your content style in exactly 3 words. No more, no less.", placeholder: "e.g. Bold, Strategic, Human", hint: "These 3 words shape your entire voice fingerprint." },
  { id: 3, type: "text", question: "Name 1–2 creators you admire for their content style. Why them specifically?", placeholder: "e.g. Lenny Rachitsky — depth + accessibility. Paul Graham for razor-sharp clarity.", hint: "Style admiration is a signal — we extract voice patterns from your choices." },
  { id: 4, type: "text", question: "What topics do you want to NEVER write about — even if they're trending?", placeholder: "e.g. Crypto speculation, hustle culture, corporate jargon...", hint: "Your 'never list' defines your brand as much as your content pillars." },
  { id: 5, type: "multi_choice", question: "What's your primary goal with content creation?", options: ["Grow my audience", "Generate leads/clients", "Build personal brand", "Monetize directly", "All of the above"], hint: "Every agent will optimize outputs for this goal." },
  { id: 6, type: "multi_choice", question: "How much time can you realistically give to content each week?", options: ["Under 1 hour", "1–3 hours", "3–5 hours", "5+ hours"], hint: "Be honest — Thook adjusts your output volume to match your capacity." },
];

export default function PhaseTwo({ onComplete }) {
  const [currentQ, setCurrentQ] = useState(0);
  const [answers, setAnswers] = useState([]);
  const [inputVal, setInputVal] = useState("");
  const [direction, setDirection] = useState(1);

  const q = QUESTIONS[currentQ];
  const progress = ((currentQ) / QUESTIONS.length) * 100;

  const handleNext = (selectedAnswer) => {
    const answer = selectedAnswer || inputVal;
    if (!answer.trim()) return;
    const newAnswers = [...answers, { question_id: currentQ, question: q.question, answer }];
    setAnswers(newAnswers);
    setInputVal("");

    if (currentQ === QUESTIONS.length - 1) {
      onComplete(newAnswers);
    } else {
      setDirection(1);
      setCurrentQ(currentQ + 1);
    }
  };

  const handleBack = () => {
    if (currentQ === 0) return;
    setDirection(-1);
    setCurrentQ(currentQ - 1);
    const prevAnswer = answers[currentQ - 1];
    setInputVal(prevAnswer?.answer || "");
    setAnswers(answers.slice(0, -1));
  };

  return (
    <div className="flex min-h-full" data-testid="phase-two-interview">
      {/* Left Panel — Agent */}
      <div className="hidden md:flex w-72 bg-[#0A0A0B] border-r border-white/5 flex-col p-6">
        <div className="mb-6">
          <p className="text-xs text-zinc-600 uppercase tracking-wider mb-3 font-mono">Active Agent</p>
          <div className="card-thook p-4 border-violet/20 bg-violet/5">
            <div className="flex items-center gap-3 mb-3">
              <div className="w-9 h-9 bg-violet/20 rounded-xl flex items-center justify-center">
                <Zap size={16} className="text-violet" />
              </div>
              <div>
                <p className="text-sm font-bold text-white">Commander</p>
                <p className="text-xs text-violet font-mono">GPT-4o</p>
              </div>
            </div>
            <p className="text-xs text-zinc-500 leading-relaxed">Orchestrating your persona interview. Each answer calibrates your AI voice clone.</p>
          </div>
        </div>

        <div className="mb-6">
          <p className="text-xs text-zinc-600 uppercase tracking-wider mb-3 font-mono">Interview Progress</p>
          <div className="space-y-1.5">
            {QUESTIONS.map((_, i) => (
              <div key={i} className="flex items-center gap-2">
                <div className={`w-1.5 h-1.5 rounded-full flex-shrink-0 transition-colors ${i < currentQ ? "bg-lime" : i === currentQ ? "bg-white animate-pulse" : "bg-white/10"}`} />
                <span className={`text-xs transition-colors ${i === currentQ ? "text-white font-medium" : i < currentQ ? "text-zinc-500" : "text-zinc-700"}`}>
                  Question {i + 1}
                </span>
                {i < currentQ && <span className="text-lime text-xs ml-auto">✓</span>}
              </div>
            ))}
          </div>
        </div>

        <div className="mt-auto">
          <p className="text-xs text-zinc-700 font-mono">~5 min remaining</p>
        </div>
      </div>

      {/* Right Panel — Question */}
      <div className="flex-1 flex flex-col">
        {/* Progress bar */}
        <div className="h-1 bg-white/5">
          <motion.div
            className="h-full bg-lime"
            initial={{ width: 0 }}
            animate={{ width: `${progress}%` }}
            transition={{ duration: 0.4 }}
          />
        </div>

        <div className="flex-1 flex items-center justify-center p-8">
          <div className="max-w-lg w-full">
            {/* Question counter */}
            <div className="flex items-center justify-between mb-8">
              <span className="text-xs font-mono text-zinc-600">{currentQ + 1} / {QUESTIONS.length}</span>
              {currentQ > 0 && (
                <button onClick={handleBack} className="flex items-center gap-1 text-xs text-zinc-500 hover:text-white transition-colors">
                  <ChevronLeft size={14} /> Back
                </button>
              )}
            </div>

            {/* Question text */}
            <AnimatePresence mode="wait">
              <motion.div
                key={currentQ}
                initial={{ opacity: 0, y: 20 * direction }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 * direction }}
                transition={{ duration: 0.25 }}
              >
                <h2
                  className="font-display font-bold text-2xl md:text-3xl text-white mb-2 leading-tight"
                  data-testid="interview-question"
                >
                  {q.question}
                </h2>
                <p className="text-zinc-600 text-sm mb-6 italic">{q.hint}</p>

                {q.type === "text" ? (
                  <>
                    <textarea
                      value={inputVal}
                      onChange={e => setInputVal(e.target.value)}
                      placeholder={q.placeholder}
                      data-testid="interview-text-input"
                      onKeyDown={e => { if (e.key === "Enter" && e.metaKey) handleNext(); }}
                      rows={4}
                      className="w-full bg-[#18181B] border border-white/10 focus:border-lime/40 focus:ring-1 focus:ring-lime/20 text-white rounded-xl p-4 text-sm placeholder:text-zinc-600 outline-none resize-none transition-colors"
                      autoFocus
                    />
                    <p className="text-zinc-700 text-xs mt-2 mb-4">⌘ + Enter to continue</p>
                    <button
                      onClick={() => handleNext()}
                      disabled={!inputVal.trim()}
                      data-testid="interview-next-btn"
                      className="btn-primary flex items-center gap-2 text-sm disabled:opacity-40 disabled:cursor-not-allowed"
                    >
                      {currentQ === QUESTIONS.length - 1 ? "Generate my Persona" : "Next question"}
                      <ArrowRight size={15} />
                    </button>
                  </>
                ) : (
                  <div className="grid grid-cols-1 gap-2.5">
                    {q.options.map(opt => (
                      <button
                        key={opt}
                        onClick={() => handleNext(opt)}
                        data-testid={`choice-${opt.toLowerCase().replace(/\s+/g, '-')}`}
                        className="w-full text-left px-5 py-3.5 rounded-xl border border-white/8 bg-[#18181B] hover:border-lime/30 hover:bg-lime/5 text-white text-sm font-medium transition-all group"
                      >
                        <span className="text-zinc-600 text-xs mr-3 font-mono group-hover:text-lime transition-colors">→</span>
                        {opt}
                      </button>
                    ))}
                  </div>
                )}
              </motion.div>
            </AnimatePresence>
          </div>
        </div>
      </div>
    </div>
  );
}
