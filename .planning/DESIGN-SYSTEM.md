# ThookAI Design System

## Colors

| Token         | Value   | Usage                                                |
| ------------- | ------- | ---------------------------------------------------- |
| lime          | #D4FF00 | Primary accent, CTAs, success states, credit display |
| violet        | #7000FF | Secondary accent, video features, premium badges     |
| surface       | #0F0F10 | Page backgrounds                                     |
| surface-2     | #18181B | Card backgrounds, inputs                             |
| border-subtle | #27272A | Dividers, card borders                               |
| background    | #050505 | App background (via CSS var)                         |

## Typography

| Font              | Stack          | Usage                |
| ----------------- | -------------- | -------------------- |
| Clash Display     | `font-display` | Headings, hero text  |
| Plus Jakarta Sans | `font-body`    | Body text, UI labels |
| JetBrains Mono    | `font-mono`    | Code, credits, stats |

## Spacing & Border Radius

- Cards: `rounded-2xl` (16px)
- Buttons: `rounded-xl` (12px) or `rounded-lg` (8px)
- Inputs: `rounded-xl` with `border-white/10`
- Standard padding: `p-4` (cards), `p-5` or `p-6` (sections)

## Component Patterns

- **Card:** `bg-surface-2 border border-white/5 rounded-2xl p-4` → class `card-thook`
- **Button primary:** `bg-lime text-black font-semibold rounded-xl` → class `btn-primary`
- **Button ghost:** `text-zinc-400 hover:text-white` → class `btn-ghost`
- **Input:** `bg-[#18181B] border border-white/10 focus:border-lime/50 rounded-xl h-12 px-4`

## Shadows

| Name        | Value                               | Usage                     |
| ----------- | ----------------------------------- | ------------------------- |
| glow-lime   | `0 0 20px rgba(212,255,0,0.25)`     | Hover on primary elements |
| glow-violet | `0 0 20px rgba(112,0,255,0.3)`      | Video/premium features    |
| card-hover  | `0 8px 32px rgba(0,0,0,0.4)`        | Card hover state          |
| modal       | `0 25px 50px -12px rgba(0,0,0,0.5)` | Dialogs, sheets           |

## Animations

| Name       | Duration | Usage                    |
| ---------- | -------- | ------------------------ |
| fade-in    | 0.4s     | Page enter               |
| fade-in-up | 0.5s     | Content sections         |
| scale-in   | 0.3s     | Modals, tooltips         |
| pulse-lime | 2s loop  | Active/processing states |
| float      | 4s loop  | Hero decorative elements |
| shimmer    | 2s loop  | Skeleton loading         |

## Framer Motion Presets

```jsx
// Page transitions
initial={{ opacity: 0, y: 20 }}
animate={{ opacity: 1, y: 0 }}
transition={{ duration: 0.4 }}

// Staggered list items
transition={{ delay: 0.1 + i * 0.05 }}

// Phase transitions (onboarding)
exit={{ opacity: 0, x: -20 }}
```

## Responsive Breakpoints

- Mobile: default (< 768px)
- Tablet: `md:` (768px+)
- Desktop: `lg:` (1024px+)
- Wide: `xl:` (1280px+)

## Icon Library

- Lucide React (`lucide-react`) — consistent 24px icons
- Common: Zap (branding), ArrowRight (CTAs), Check (success)

## Toast Notifications (Sonner)

```jsx
toast({ title: "Success", description: "...", variant: "default" }); // Green
toast({ title: "Error", description: "...", variant: "destructive" }); // Red
```
