import { motion } from "framer-motion";
import { Zap } from "lucide-react";

export default function ComingSoon({ title, desc, sprint }) {
  return (
    <main className="flex-1 flex items-center justify-center p-6" data-testid="coming-soon-page">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="text-center max-w-md"
      >
        <div className="w-16 h-16 bg-lime/10 rounded-2xl flex items-center justify-center mx-auto mb-5">
          <Zap size={28} className="text-lime" />
        </div>
        <div className="inline-flex items-center gap-1.5 bg-lime/10 text-lime text-xs font-mono rounded-full px-3 py-1 mb-4">
          Sprint {sprint}
        </div>
        <h2 className="font-display font-bold text-2xl text-white mb-2">{title}</h2>
        <p className="text-zinc-500 text-sm leading-relaxed">{desc}</p>
        <p className="text-zinc-700 text-xs mt-4 font-mono">In active development</p>
      </motion.div>
    </main>
  );
}
