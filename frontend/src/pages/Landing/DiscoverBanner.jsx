import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowRight, Sparkles } from "lucide-react";

export function DiscoverBanner() {
  const navigate = useNavigate();
  return (
    <section className="px-6 md:px-12 py-16 max-w-7xl mx-auto">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        className="relative overflow-hidden rounded-2xl border border-lime/20 bg-gradient-to-br from-lime/[0.06] via-surface to-violet/[0.04] p-8 md:p-12"
      >
        <div className="absolute top-0 right-0 w-64 h-64 bg-lime/[0.06] rounded-full blur-[80px] pointer-events-none" />
        <div className="absolute bottom-0 left-0 w-48 h-48 bg-violet/[0.08] rounded-full blur-[60px] pointer-events-none" />
        <div className="relative z-10 flex flex-col md:flex-row items-center gap-8">
          <div className="flex-1 text-center md:text-left">
            <div className="inline-flex items-center gap-2 bg-lime/10 border border-lime/20 rounded-full px-3 py-1 text-xs font-semibold mb-4">
              <Sparkles size={12} className="text-lime" />
              <span className="text-lime">Free Tool</span>
            </div>
            <h3 className="font-display font-bold text-2xl md:text-3xl text-white mb-3">
              Discover Your Creator DNA
            </h3>
            <p className="text-zinc-400 text-sm md:text-base leading-relaxed max-w-lg">
              Paste your posts and get an AI-powered persona card that reveals
              your writing voice, content archetype, and strengths. No signup
              needed.
            </p>
          </div>
          <div className="flex-shrink-0">
            <button
              onClick={() => navigate("/discover")}
              className="btn-primary text-base px-8 py-3.5 flex items-center gap-2 whitespace-nowrap"
            >
              <Sparkles size={16} />
              Try It Free
              <ArrowRight size={16} />
            </button>
          </div>
        </div>
      </motion.div>
    </section>
  );
}
