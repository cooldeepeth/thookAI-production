import { Navbar } from "@/pages/Landing/Navbar";
import { Hero } from "@/pages/Landing/Hero";
import { Features } from "@/pages/Landing/Features";
import { HowItWorks } from "@/pages/Landing/HowItWorks";
import { DiscoverBanner } from "@/pages/Landing/DiscoverBanner";
import { SocialProof } from "@/pages/Landing/SocialProof";
import { AgentCouncil } from "@/pages/Landing/AgentCouncil";
import { PricingSection } from "@/pages/Landing/PricingSection";
import { Footer } from "@/pages/Landing/Footer";

export default function LandingPage() {
  return (
    <div
      className="bg-[#050505] min-h-screen text-white overflow-x-hidden"
      data-testid="landing-page"
    >
      <Navbar />
      <Hero />
      <Features />
      <HowItWorks />
      <DiscoverBanner />
      <SocialProof />
      <AgentCouncil />
      <PricingSection />
      <Footer />
    </div>
  );
}
