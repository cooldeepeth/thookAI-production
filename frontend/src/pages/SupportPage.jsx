import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import {
  ArrowLeft,
  Mail,
  MessageSquare,
  HelpCircle,
  ChevronDown,
  ChevronUp,
  Zap,
} from "lucide-react";

const FAQ_ITEMS = [
  {
    q: "What is ThookAI?",
    a: "ThookAI is an AI-powered content creation platform that helps creators, founders, and agencies generate personalised, platform-specific content for LinkedIn, X (Twitter), and Instagram. It uses a 5-agent AI pipeline trained on your unique voice and style.",
  },
  {
    q: "How does the Persona Engine work?",
    a: 'During onboarding, you answer a short interactive questionnaire about your content style, audience, and goals. Our AI builds a "Persona Engine" — a voice fingerprint that ensures every piece of content sounds like you, not generic AI.',
  },
  {
    q: "What content formats can I create?",
    a: "Text posts, articles, carousels, threads, image captions, video scripts, voice narrations, and more — optimised for each platform's algorithm and best practices.",
  },
  {
    q: "How do credits work?",
    a: "Every action costs credits: text posts (10), images (8), carousels (15), videos (50), voice narration (12). You start with 200 free credits. Buy more or subscribe to a custom plan for monthly credits.",
  },
  {
    q: "Can I connect my social media accounts?",
    a: "Yes! Connect LinkedIn, X (Twitter), and Instagram to publish content directly from ThookAI. You can also download content and post it manually.",
  },
  {
    q: "Is my data safe?",
    a: "Absolutely. We use encryption for all stored tokens, secure HTTP-only cookies for authentication, and never share your personal data. See our Privacy Policy for details.",
  },
  {
    q: "Can I cancel my subscription?",
    a: "Yes, you can cancel anytime from Settings > Billing. Your plan stays active until the end of the billing period.",
  },
  {
    q: "What if I run out of credits?",
    a: "You can purchase additional credit packs (100, 500, or 1000 credits) or upgrade your plan for more monthly credits at volume-discounted rates.",
  },
];

function FaqItem({ item, isOpen, onToggle }) {
  return (
    <div className="border border-white/5 rounded-lg overflow-hidden">
      <button
        onClick={onToggle}
        className="w-full flex items-center justify-between p-4 text-left hover:bg-white/[0.02] transition-colors"
      >
        <span className="text-white font-medium pr-4">{item.q}</span>
        {isOpen ? (
          <ChevronUp size={16} className="text-zinc-500 shrink-0" />
        ) : (
          <ChevronDown size={16} className="text-zinc-500 shrink-0" />
        )}
      </button>
      {isOpen && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: "auto" }}
          transition={{ duration: 0.2 }}
          className="px-4 pb-4 text-zinc-400 text-sm leading-relaxed border-t border-white/5"
        >
          <p className="pt-3">{item.a}</p>
        </motion.div>
      )}
    </div>
  );
}

export default function SupportPage() {
  useEffect(() => {
    document.title = "Support — ThookAI";
  }, []);
  const [openFaq, setOpenFaq] = useState(null);

  return (
    <div className="min-h-screen bg-[#050505] text-zinc-300">
      <div className="max-w-3xl mx-auto px-6 py-16">
        <Link
          to="/"
          className="inline-flex items-center gap-2 text-zinc-500 hover:text-lime text-sm mb-8 transition-colors"
        >
          <ArrowLeft size={14} /> Back to ThookAI
        </Link>

        <div className="flex items-center gap-3 mb-2">
          <Zap size={24} className="text-lime" />
          <h1 className="font-display font-bold text-3xl text-white">
            Support
          </h1>
        </div>
        <p className="text-zinc-500 mb-12">
          Get help with ThookAI — we are here to assist.
        </p>

        {/* Contact Section */}
        <section className="mb-16">
          <h2 className="font-display font-semibold text-xl text-white mb-6">
            Contact Us
          </h2>
          <div className="grid gap-4 md:grid-cols-2">
            <a
              href="mailto:kuldeep@thook.ai"
              className="card-thook p-5 flex items-start gap-4 hover:border-lime/30 transition-colors group"
            >
              <div className="w-10 h-10 rounded-lg bg-lime/10 flex items-center justify-center shrink-0">
                <Mail size={18} className="text-lime" />
              </div>
              <div>
                <h3 className="text-white font-medium mb-1 group-hover:text-lime transition-colors">
                  Email Support
                </h3>
                <p className="text-zinc-500 text-sm">kuldeep@thook.ai</p>
                <p className="text-zinc-600 text-xs mt-1">
                  We typically respond within 24 hours
                </p>
              </div>
            </a>
            <a
              href="mailto:kuldeep@thook.ai?subject=Bug Report"
              className="card-thook p-5 flex items-start gap-4 hover:border-lime/30 transition-colors group"
            >
              <div className="w-10 h-10 rounded-lg bg-violet/10 flex items-center justify-center shrink-0">
                <MessageSquare size={18} className="text-violet-400" />
              </div>
              <div>
                <h3 className="text-white font-medium mb-1 group-hover:text-lime transition-colors">
                  Report a Bug
                </h3>
                <p className="text-zinc-500 text-sm">Found something broken?</p>
                <p className="text-zinc-600 text-xs mt-1">
                  Include steps to reproduce and we will fix it fast
                </p>
              </div>
            </a>
          </div>
        </section>

        {/* FAQ Section */}
        <section className="mb-16">
          <div className="flex items-center gap-2 mb-6">
            <HelpCircle size={20} className="text-lime" />
            <h2 className="font-display font-semibold text-xl text-white">
              Frequently Asked Questions
            </h2>
          </div>
          <div className="space-y-2">
            {FAQ_ITEMS.map((item, i) => (
              <FaqItem
                key={i}
                item={item}
                isOpen={openFaq === i}
                onToggle={() => setOpenFaq(openFaq === i ? null : i)}
              />
            ))}
          </div>
        </section>

        {/* Quick Links */}
        <section className="border-t border-white/5 pt-8">
          <h2 className="font-display font-semibold text-xl text-white mb-4">
            Quick Links
          </h2>
          <div className="flex flex-wrap gap-4 text-sm">
            <Link
              to="/privacy"
              className="text-zinc-500 hover:text-lime transition-colors"
            >
              Privacy Policy
            </Link>
            <Link
              to="/terms"
              className="text-zinc-500 hover:text-lime transition-colors"
            >
              Terms of Service
            </Link>
            <a
              href="mailto:kuldeep@thook.ai"
              className="text-zinc-500 hover:text-lime transition-colors"
            >
              Contact
            </a>
          </div>
        </section>
      </div>
    </div>
  );
}
