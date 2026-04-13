import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Slider } from "@/components/ui/slider";
import { apiFetch } from "@/lib/api";

const PLAN_BUILDER_DEFAULTS = {
  text_posts: 20,
  images: 5,
  videos: 0,
  carousels: 2,
  repurposes: 5,
  voice_narrations: 0,
  series_plans: 0,
};

const PLAN_BUILDER_LABELS = {
  text_posts: { name: "Text Posts", credits: 10, max: 200 },
  images: { name: "Images", credits: 8, max: 100 },
  videos: { name: "Videos", credits: 50, max: 20 },
  carousels: { name: "Carousels", credits: 15, max: 50 },
  repurposes: { name: "Repurposes", credits: 3, max: 100 },
  voice_narrations: { name: "Voice Narrations", credits: 12, max: 50 },
  series_plans: { name: "Series Plans", credits: 6, max: 20 },
};

export function PlanBuilder({ mode = "landing", onCheckout, subscription, upgrading }) {
  const navigate = useNavigate();
  const [planUsage, setPlanUsage] = useState({ ...PLAN_BUILDER_DEFAULTS });
  const [planPreview, setPlanPreview] = useState(null);
  const [previewLoading, setPreviewLoading] = useState(false);

  const fetchPlanPreview = async (usage) => {
    setPreviewLoading(true);
    try {
      const res = await apiFetch("/api/billing/plan/preview", {
        method: "POST",
        body: JSON.stringify(usage),
      });
      if (res.ok) {
        const data = await res.json();
        setPlanPreview(data);
      }
    } catch {
      // Silent — preview is non-critical
    } finally {
      setPreviewLoading(false);
    }
  };

  useEffect(() => {
    const totalUsage = Object.values(planUsage).reduce((a, b) => a + b, 0);
    if (totalUsage > 0) {
      const timer = setTimeout(() => fetchPlanPreview(planUsage), 400);
      return () => clearTimeout(timer);
    } else {
      setPlanPreview(null);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [planUsage]);

  const handleCtaClick = () => {
    if (mode === "landing") {
      navigate("/auth");
    } else {
      onCheckout?.(planUsage);
    }
  };

  const ctaLabel =
    mode === "landing"
      ? "Get Started Free"
      : upgrading === "custom"
        ? "Processing..."
        : subscription?.tier === "custom"
          ? "Update My Plan"
          : "Customize My Plan";

  const ctaTestId = mode === "landing" ? "plan-builder-cta" : "plan-builder-checkout";

  return (
    <div className="card-thook p-6 space-y-6" data-testid="plan-builder">
      <div>
        <h3 className="font-display font-bold text-xl text-white mb-1">
          Build your plan
        </h3>
        <p className="text-sm text-zinc-500">
          Pick how much content you'll create each month — we'll calculate the price.
        </p>
      </div>

      <div className="space-y-5">
        {Object.entries(PLAN_BUILDER_LABELS).map(([key, config]) => (
          <div key={key} className="space-y-2">
            <div className="flex justify-between text-sm">
              <span className="text-white">{config.name}</span>
              <span className="font-mono text-lime">
                {planUsage[key]} × {config.credits} cr
              </span>
            </div>
            <Slider
              min={0}
              max={config.max}
              step={1}
              value={[planUsage[key]]}
              onValueChange={([val]) =>
                setPlanUsage((prev) => ({ ...prev, [key]: val }))
              }
              className="w-full"
              aria-label={`${config.name} count`}
            />
          </div>
        ))}
      </div>

      <div className="border-t border-white/5 pt-6 space-y-4">
        {previewLoading && (
          <div className="h-12 bg-surface-2 rounded-lg animate-pulse" />
        )}
        {!previewLoading && planPreview && (
          <div className="flex items-end justify-between" data-testid="plan-builder-preview">
            <div>
              <p className="text-xs text-zinc-500 mb-1">Estimated price</p>
              <p className="font-display font-bold text-3xl text-lime">
                ${planPreview.total_price ?? 0}
                <span className="text-sm text-zinc-500 font-normal">/mo</span>
              </p>
            </div>
            <div className="text-right">
              <p className="text-xs text-zinc-500 mb-1">Credits / month</p>
              <p className="font-mono text-lg text-white">
                {planPreview.total_credits ?? 0}
              </p>
            </div>
          </div>
        )}
        {!previewLoading && !planPreview && (
          <p className="text-xs text-zinc-500 text-center">
            Move a slider to see pricing.
          </p>
        )}

        <button
          type="button"
          onClick={handleCtaClick}
          disabled={mode === "settings" && upgrading === "custom"}
          className="btn-primary w-full focus-ring disabled:opacity-60 disabled:cursor-not-allowed"
          data-testid={ctaTestId}
        >
          {ctaLabel}
        </button>
      </div>
    </div>
  );
}
