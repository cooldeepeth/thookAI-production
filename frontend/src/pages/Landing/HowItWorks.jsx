import { motion } from "framer-motion";
import { Brain, Wand2, TrendingUp } from "lucide-react";

const STEPS = [
  {
    number: 1,
    testId: "how-it-works-step-1",
    icon: Brain,
    title: "Build Your Persona",
    description:
      "Answer 7 questions about your voice, goals, and audience. Our AI builds a deep persona fingerprint that captures exactly how you think and write.",
  },
  {
    number: 2,
    testId: "how-it-works-step-2",
    icon: Wand2,
    title: "Generate Content",
    description:
      "Describe what you want to say. 15 specialist AI agents craft platform-native posts for LinkedIn, X, and Instagram in your authentic voice.",
  },
  {
    number: 3,
    testId: "how-it-works-step-3",
    icon: TrendingUp,
    title: "Publish & Learn",
    description:
      "Schedule, publish, and watch ThookAI improve from your edits and real engagement data — getting sharper with every post.",
  },
];

export function HowItWorks() {
  return (
    <section
      id="how-it-works"
      className="py-24 px-6 max-w-7xl mx-auto"
      data-testid="how-it-works-section"
    >
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        transition={{ duration: 0.5 }}
        className="text-center mb-16"
      >
        <h2 className="font-display font-bold text-4xl text-white mb-4">
          From zero to published in 5 minutes
        </h2>
        <p className="text-zinc-400 text-lg max-w-2xl mx-auto">
          Three simple steps to go from idea to published post — no content expertise required.
        </p>
      </motion.div>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
        {STEPS.map((step, i) => {
          const Icon = step.icon;
          return (
            <motion.div
              key={step.number}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: i * 0.15 }}
              className="card-thook p-6 text-center"
              data-testid={step.testId}
            >
              <div className="w-10 h-10 rounded-full bg-lime text-black font-display font-bold text-lg flex items-center justify-center mx-auto mb-4">
                {step.number}
              </div>
              <Icon size={28} className="text-lime mx-auto mb-3" />
              <h3 className="font-display font-semibold text-white text-lg mb-2">
                {step.title}
              </h3>
              <p className="text-zinc-400 text-sm leading-relaxed">{step.description}</p>
            </motion.div>
          );
        })}
      </div>
    </section>
  );
}
