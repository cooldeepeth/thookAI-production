import { motion } from "framer-motion";
import { PlanBuilder } from "@/components/PlanBuilder";

export function PricingSection() {
  return (
    <section
      id="pricing"
      className="py-24 px-6 max-w-7xl mx-auto"
      data-testid="pricing-section"
    >
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        transition={{ duration: 0.5 }}
        className="text-center mb-16"
      >
        <h2 className="font-display font-bold text-4xl text-white mb-4">
          Pay for what you actually use
        </h2>
        <p className="text-zinc-400 text-lg max-w-2xl mx-auto">
          No rigid tiers. Slide the controls to match your content needs — see the exact price before you commit.
        </p>
      </motion.div>
      <div className="max-w-2xl mx-auto">
        <PlanBuilder mode="landing" />
      </div>
    </section>
  );
}
