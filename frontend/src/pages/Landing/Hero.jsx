import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowRight, ChevronRight } from "lucide-react";

export function Hero() {
  const navigate = useNavigate();
  return (
    <section
      className="relative min-h-screen flex items-center justify-center px-6 pt-16 overflow-hidden"
      data-testid="hero-section"
    >
      {/* Background */}
      <div className="absolute inset-0 hero-glow" />
      <div className="absolute top-1/3 left-1/2 -translate-x-1/2 w-[600px] h-[600px] bg-violet/8 rounded-full blur-[120px]" />
      <div className="absolute top-1/2 left-1/4 w-64 h-64 bg-lime/4 rounded-full blur-[80px]" />

      <div className="relative z-10 text-center max-w-4xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          <div className="inline-flex items-center gap-2 bg-lime/10 border border-lime/20 rounded-full px-4 py-1.5 mb-8 text-sm">
            <span className="w-2 h-2 bg-lime rounded-full animate-pulse" />
            <span className="text-lime font-medium">
              Early Bird Launch — Save up to 38% for a limited time
            </span>
            <ChevronRight size={14} className="text-lime/60" />
          </div>
        </motion.div>

        <motion.h1
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.1 }}
          className="font-display font-bold text-5xl md:text-6xl lg:text-7xl text-white leading-[1.05] mb-6"
        >
          Your Voice. <span className="text-lime">Infinite</span> Content.
        </motion.h1>

        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.2 }}
          className="text-lg md:text-xl text-zinc-400 max-w-2xl mx-auto mb-10 leading-relaxed"
        >
          15+ specialized AI agents that learn your exact voice and style — then
          craft platform-native content for LinkedIn, X, and Instagram.{" "}
          <strong className="text-white">Without burning you out.</strong>
        </motion.p>

        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.3 }}
          className="flex flex-col sm:flex-row items-center justify-center gap-4"
        >
          <button
            onClick={() => navigate("/auth")}
            data-testid="hero-cta-primary"
            className="btn-primary text-base px-8 py-3.5 flex items-center gap-2"
          >
            Get Started
            <ArrowRight size={16} />
          </button>
          <a
            href="#features"
            data-testid="hero-cta-secondary"
            className="btn-ghost text-base flex items-center gap-2"
          >
            <ChevronRight size={16} className="text-lime" />
            <span>See how it works</span>
          </a>
        </motion.div>

        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.5 }}
          className="text-zinc-600 text-sm mt-6"
        >
          50 free credits on signup · No credit card for Free tier
        </motion.p>
      </div>

      {/* Platform logos */}
      <div className="absolute bottom-12 left-1/2 -translate-x-1/2 flex items-center gap-6 opacity-40">
        <span className="text-xs text-zinc-600 uppercase tracking-wider">
          Publishes to
        </span>
        <img
          src="https://upload.wikimedia.org/wikipedia/commons/c/ca/LinkedIn_logo_initials.png"
          alt="LinkedIn"
          className="h-5 w-5 object-contain"
        />
        <img
          src="https://upload.wikimedia.org/wikipedia/commons/thumb/c/ce/X_logo_2023.svg/450px-X_logo_2023.svg.png"
          alt="X"
          className="h-5 w-5 object-contain invert"
        />
        <img
          src="https://upload.wikimedia.org/wikipedia/commons/thumb/e/e7/Instagram_logo_2016.svg/2048px-Instagram_logo_2016.svg.png"
          alt="Instagram"
          className="h-5 w-5 object-contain"
        />
      </div>
    </section>
  );
}
