import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Zap, Sparkles, Menu } from "lucide-react";
import { Sheet, SheetContent, SheetTitle, SheetDescription } from "@/components/ui/sheet";

export function Navbar() {
  const navigate = useNavigate();
  const [scrolled, setScrolled] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 20);
    window.addEventListener("scroll", onScroll);
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  const links = [
    { href: "#features", label: "Product" },
    { href: "#agents", label: "Agents" },
    { href: "#pricing", label: "Pricing" },
  ];

  return (
    <nav
      className={`fixed top-0 left-0 right-0 z-50 flex items-center justify-between px-6 md:px-12 h-16 transition-all ${
        scrolled ? "bg-[#050505]/90 backdrop-blur-md border-b border-white/5" : ""
      }`}
      data-testid="landing-navbar"
    >
      <div className="flex items-center gap-2">
        <div className="w-8 h-8 bg-lime rounded-lg flex items-center justify-center">
          <Zap size={16} className="text-black" fill="black" />
        </div>
        <span className="font-display font-bold text-lg text-white">Thook</span>
        <span className="text-[10px] font-mono text-lime bg-lime/10 px-1.5 py-0.5 rounded-md">
          AI
        </span>
      </div>

      <div className="hidden md:flex items-center gap-8 text-sm text-zinc-400">
        {links.map((l) => (
          <a key={l.href} href={l.href} className="hover:text-white transition-colors">
            {l.label}
          </a>
        ))}
        <button
          type="button"
          onClick={() => navigate("/discover")}
          className="text-lime hover:text-lime/80 transition-colors flex items-center gap-1.5 font-medium focus-ring"
        >
          <Sparkles size={14} />
          Discover Your Voice
        </button>
      </div>

      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={() => navigate("/auth")}
          data-testid="nav-signin-btn"
          className="text-sm text-zinc-400 hover:text-white transition-colors hidden md:block focus-ring"
        >
          Sign in
        </button>
        <button
          type="button"
          onClick={() => navigate("/auth")}
          data-testid="nav-cta-btn"
          className="btn-primary text-sm py-2 px-5 focus-ring"
        >
          Get started
        </button>
        <button
          type="button"
          className="md:hidden text-zinc-400 hover:text-white focus-ring rounded p-1"
          aria-label="Open navigation menu"
          data-testid="mobile-menu-btn"
          onClick={() => setMobileOpen(true)}
        >
          <Menu size={20} />
        </button>
      </div>

      <Sheet open={mobileOpen} onOpenChange={setMobileOpen}>
        <SheetContent
          side="right"
          className="bg-surface w-[260px] border-l border-white/5"
          data-testid="mobile-nav-drawer"
        >
          {/* Radix DialogContent requires a Title + Description for screen readers.
              Visually hidden via Tailwind `sr-only` — keeps WCAG 2.1 SC 1.3.1 / 4.1.2
              compliant without affecting the visible drawer layout. */}
          <SheetTitle className="sr-only">Navigation menu</SheetTitle>
          <SheetDescription className="sr-only">
            Main site navigation: product, agents, pricing, sign in, and get started.
          </SheetDescription>
          <div className="flex flex-col gap-6 pt-8">
            {links.map((l) => (
              <a
                key={l.href}
                href={l.href}
                className="text-zinc-400 hover:text-white transition-colors text-base focus-ring"
                onClick={() => setMobileOpen(false)}
              >
                {l.label}
              </a>
            ))}
            <button
              type="button"
              onClick={() => {
                setMobileOpen(false);
                navigate("/discover");
              }}
              className="text-lime text-left font-medium focus-ring"
            >
              Discover Your Voice
            </button>
            <div className="border-t border-white/5 pt-4 flex flex-col gap-3">
              <button
                type="button"
                onClick={() => {
                  setMobileOpen(false);
                  navigate("/auth");
                }}
                className="text-zinc-400 hover:text-white text-sm text-left focus-ring"
              >
                Sign in
              </button>
              <button
                type="button"
                onClick={() => {
                  setMobileOpen(false);
                  navigate("/auth");
                }}
                className="btn-primary text-sm py-2 px-5 w-full focus-ring"
              >
                Get started
              </button>
            </div>
          </div>
        </SheetContent>
      </Sheet>
    </nav>
  );
}
