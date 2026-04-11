import { useState } from 'react';
import { motion } from 'framer-motion';
import { Check } from 'lucide-react';

// Authoritative palette options from UI-SPEC.md
// Keys locked by ONBD-04 — do not rename
const PALETTES = [
  {
    key: 'bold',
    label: 'Bold',
    description: 'High contrast, strong typography',
    swatches: ['#D4FF00', '#000000', '#FFFFFF', '#1A1A1A'],
  },
  {
    key: 'minimal',
    label: 'Minimal',
    description: 'Clean and spacious, subtle accents',
    swatches: ['#FFFFFF', '#F5F5F5', '#E0E0E0', '#111111'],
  },
  {
    key: 'corporate',
    label: 'Corporate',
    description: 'Structured and professional',
    swatches: ['#1A3A6B', '#FFFFFF', '#E8ECF0', '#2D5299'],
  },
  {
    key: 'creative',
    label: 'Creative',
    description: 'Colorful and expressive',
    swatches: ['#FF5733', '#FFC300', '#36D7B7', '#8E44AD'],
  },
  {
    key: 'warm',
    label: 'Warm',
    description: 'Earth tones, approachable',
    swatches: ['#D4956A', '#8B4513', '#F5DEB3', '#2C1810'],
  },
  {
    key: 'dark',
    label: 'Dark',
    description: 'Deep and tech-forward',
    swatches: ['#000000', '#7000FF', '#D4FF00', '#1A1A1A'],
  },
];

export default function VisualPaletteStep({ onComplete }) {
  const [selectedKey, setSelectedKey] = useState(null);

  return (
    <div
      className="flex items-center justify-center min-h-full p-8"
      data-testid="visual-palette-step"
    >
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="max-w-2xl w-full"
      >
        <p className="text-lime text-xs font-bold uppercase tracking-widest mb-3 text-center">
          Step 3 of 5
        </p>
        <h2 className="font-display font-bold text-3xl text-white text-center mb-2">
          Pick your visual style
        </h2>
        <p className="text-zinc-500 text-sm text-center max-w-md mx-auto mb-8">
          Choose the aesthetic that best represents your brand. This shapes how your content looks visually.
        </p>

        {/* Palette grid — role="radiogroup" per accessibility contract */}
        <div
          className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-6"
          role="radiogroup"
          aria-label="Visual style palette"
        >
          {PALETTES.map((palette, i) => (
            <motion.button
              key={palette.key}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.05 * i, duration: 0.3 }}
              onClick={() => setSelectedKey(palette.key)}
              data-testid={`palette-option-${palette.key}`}
              role="radio"
              aria-checked={selectedKey === palette.key}
              className={`card-thook-interactive p-5 text-left relative transition-all ${
                selectedKey === palette.key
                  ? 'border-lime/30 bg-lime/5'
                  : ''
              }`}
            >
              {/* Selected check icon — top-right corner, only visible when selected */}
              {selectedKey === palette.key && (
                <div className="absolute top-3 right-3">
                  <Check size={14} className="text-lime" />
                </div>
              )}

              {/* Color swatches — inline style for hex values; no raw hex in className */}
              <div className="flex gap-1.5 mb-3">
                {palette.swatches.map((color, ci) => (
                  <div
                    key={ci}
                    className="w-4 h-4 rounded-full border border-white/10"
                    style={{ backgroundColor: color }}
                  />
                ))}
              </div>

              {/* Label */}
              <p className="font-display font-bold text-white text-sm mb-1">
                {palette.label}
              </p>

              {/* Description */}
              <p className="text-zinc-500 text-xs leading-relaxed">
                {palette.description}
              </p>
            </motion.button>
          ))}
        </div>

        {/* Continue button — disabled until a palette is selected */}
        <button
          onClick={() => selectedKey && onComplete(selectedKey)}
          data-testid="palette-confirm-btn"
          disabled={!selectedKey}
          className="btn-primary w-full disabled:opacity-40 disabled:cursor-not-allowed"
        >
          This feels right, continue
        </button>
      </motion.div>
    </div>
  );
}
