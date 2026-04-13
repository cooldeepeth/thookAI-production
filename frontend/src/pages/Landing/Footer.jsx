import { Zap } from "lucide-react";

export function Footer() {
  return (
    <footer className="border-t border-white/5 px-6 md:px-12 py-8" data-testid="landing-footer">
      <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 bg-lime rounded-md flex items-center justify-center">
            <Zap size={12} className="text-black" fill="black" />
          </div>
          <span className="font-display font-bold text-sm text-white">
            Thook AI
          </span>
        </div>
        <p className="text-zinc-600 text-xs">
          © {new Date().getFullYear()} ThookAI. Your AI Creative Agency.
        </p>
        <div className="flex gap-5 text-xs text-zinc-600">
          <a href="/privacy" className="hover:text-white transition-colors">
            Privacy
          </a>
          <a href="/terms" className="hover:text-white transition-colors">
            Terms
          </a>
          <a
            href="mailto:support@thookai.com"
            className="hover:text-white transition-colors"
          >
            Contact
          </a>
        </div>
      </div>
    </footer>
  );
}
