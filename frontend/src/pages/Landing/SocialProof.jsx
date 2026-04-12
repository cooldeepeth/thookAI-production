import { motion } from "framer-motion";

const METRICS = [
  { value: "15+", label: "Specialist AI Agents" },
  { value: "3", label: "Social Platforms" },
  { value: "200", label: "Free Credits to Start" },
  { value: "< 5 min", label: "To Your First Post" },
];

export function SocialProof() {
  return (
    <section
      className="py-16 px-6 max-w-7xl mx-auto"
      data-testid="social-proof-section"
    >
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        transition={{ duration: 0.5 }}
        className="text-center mb-10"
      >
        <p className="text-zinc-500 text-sm uppercase tracking-widest font-mono">
          By the numbers
        </p>
      </motion.div>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {METRICS.map((m, i) => (
          <motion.div
            key={m.label}
            initial={{ opacity: 0, y: 16 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.4, delay: i * 0.1 }}
            className="card-thook p-6 text-center"
          >
            <p className="font-mono text-4xl text-lime mb-2">{m.value}</p>
            <p className="text-sm text-zinc-400">{m.label}</p>
          </motion.div>
        ))}
      </div>
    </section>
  );
}
