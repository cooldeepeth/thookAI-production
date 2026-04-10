import { useEffect } from "react";
import { Link } from "react-router-dom";
import { ArrowLeft } from "lucide-react";

export default function PrivacyPolicy() {
  useEffect(() => { document.title = "Privacy Policy — ThookAI"; }, []);

  return (
    <div className="min-h-screen bg-[#050505] text-zinc-300">
      <div className="max-w-3xl mx-auto px-6 py-16">
        <Link to="/" className="inline-flex items-center gap-2 text-zinc-500 hover:text-lime text-sm mb-8 transition-colors">
          <ArrowLeft size={14} /> Back to ThookAI
        </Link>

        <h1 className="font-display font-bold text-3xl text-white mb-2">Privacy Policy</h1>
        <p className="text-zinc-500 text-sm mb-8">Last updated: April 2026</p>

        <div className="space-y-6 text-sm leading-relaxed">
          <section>
            <h2 className="text-white font-semibold text-lg mb-2">1. Information We Collect</h2>
            <p>When you use ThookAI, we collect:</p>
            <ul className="list-disc ml-5 mt-2 space-y-1">
              <li><strong>Account information:</strong> name, email address, profile picture (if using Google sign-in)</li>
              <li><strong>Content data:</strong> your onboarding interview answers, generated content, edits, and approvals</li>
              <li><strong>Usage data:</strong> pages visited, features used, content generation history</li>
              <li><strong>Payment data:</strong> processed securely by Stripe — we do not store credit card numbers</li>
              <li><strong>Platform tokens:</strong> OAuth tokens for LinkedIn, X, and Instagram (encrypted at rest with Fernet)</li>
            </ul>
          </section>

          <section>
            <h2 className="text-white font-semibold text-lg mb-2">2. How We Use Your Data</h2>
            <ul className="list-disc ml-5 space-y-1">
              <li>To generate personalized content matching your voice and style</li>
              <li>To improve our AI models and content quality (aggregated, anonymized)</li>
              <li>To process payments and manage your subscription</li>
              <li>To publish content to your connected social media accounts</li>
              <li>To send transactional emails (password resets, billing notifications)</li>
            </ul>
          </section>

          <section>
            <h2 className="text-white font-semibold text-lg mb-2">3. Third-Party Services</h2>
            <p>We share data with these services to provide our platform:</p>
            <ul className="list-disc ml-5 mt-2 space-y-1">
              <li><strong>Anthropic / OpenAI:</strong> your content prompts are sent to LLM providers for generation</li>
              <li><strong>Stripe:</strong> payment processing</li>
              <li><strong>Sentry:</strong> error tracking (no PII in error reports)</li>
              <li><strong>PostHog:</strong> product analytics (anonymized usage data)</li>
              <li><strong>MongoDB Atlas:</strong> database hosting (encrypted at rest)</li>
              <li><strong>Cloudflare R2:</strong> media file storage</li>
            </ul>
          </section>

          <section>
            <h2 className="text-white font-semibold text-lg mb-2">4. Your Rights (GDPR)</h2>
            <p>You have the right to:</p>
            <ul className="list-disc ml-5 mt-2 space-y-1">
              <li><strong>Export your data:</strong> Settings → Data → Export (downloads all your data as JSON)</li>
              <li><strong>Delete your account:</strong> Settings → Data → Delete Account (anonymizes all PII)</li>
              <li><strong>Access your data:</strong> via the API at GET /api/auth/export</li>
              <li><strong>Withdraw consent:</strong> you can disconnect platforms and delete your account at any time</li>
            </ul>
          </section>

          <section>
            <h2 className="text-white font-semibold text-lg mb-2">5. Data Retention</h2>
            <p>We retain your data for as long as your account is active. After account deletion:</p>
            <ul className="list-disc ml-5 mt-2 space-y-1">
              <li>Personal data is anonymized immediately</li>
              <li>Content job records are anonymized (user_id replaced, raw_input deleted)</li>
              <li>Platform tokens are deleted</li>
              <li>Uploaded media metadata is deleted</li>
            </ul>
          </section>

          <section>
            <h2 className="text-white font-semibold text-lg mb-2">6. Cookies</h2>
            <p>We use essential cookies for authentication (session_token, csrf_token). We use PostHog for analytics which may set tracking cookies. You can manage cookie preferences in your browser settings.</p>
          </section>

          <section>
            <h2 className="text-white font-semibold text-lg mb-2">7. Contact</h2>
            <p>For privacy inquiries, contact us at <a href="mailto:privacy@thookai.com" className="text-lime hover:underline">privacy@thookai.com</a>.</p>
          </section>
        </div>
      </div>
    </div>
  );
}
