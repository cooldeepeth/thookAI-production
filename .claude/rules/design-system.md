# ThookAI Design System Rules — Figma-to-Code Integration

> Rules for translating Figma designs into ThookAI frontend code.
> Read this before implementing any design from Figma MCP.

## 1. Token Definitions

### Colors — CSS Custom Properties (`frontend/src/index.css`)

```css
:root {
  --background: 0 0% 2%; /* #050505 — app background */
  --foreground: 0 0% 100%; /* white — default text */
  --primary: 74 100% 50%; /* #D4FF00 — lime accent */
  --secondary: 270 100% 50%; /* #7000FF — violet accent */
  --muted: 0 0% 11%; /* #1C1C1C — muted backgrounds */
  --destructive: 0 72% 51%; /* red — error states */
  --border: 0 0% 15%; /* #262626 — borders */
  --radius: 0.5rem; /* base border radius */
}
```

### Named Color Tokens (`tailwind.config.js`)

| Token           | Hex       | Usage                                        |
| --------------- | --------- | -------------------------------------------- |
| `lime`          | `#D4FF00` | Primary CTA, success, credits, active states |
| `violet`        | `#7000FF` | Secondary accent, video, premium features    |
| `surface`       | `#0F0F10` | Card backgrounds                             |
| `surface-2`     | `#18181B` | Input backgrounds, elevated surfaces         |
| `border-subtle` | `#27272A` | Subtle dividers                              |

**Usage:** Always use Tailwind classes, never raw hex in JSX.

```jsx
// CORRECT
<div className="bg-surface text-lime border-white/10" />

// WRONG — don't hardcode hex
<div style={{ color: '#D4FF00' }} />
```

### Typography (`frontend/src/index.css` + `tailwind.config.js`)

| Font                      | Tailwind Class        | Usage                          |
| ------------------------- | --------------------- | ------------------------------ |
| Clash Display 600/700     | `font-display`        | Headings (h1, h2, h3)          |
| Plus Jakarta Sans 400-700 | `font-body` (default) | Body text, UI labels           |
| JetBrains Mono 400/500    | `font-mono`           | Code, credits, stats, counters |

```jsx
<h1 className="font-display font-bold text-3xl text-white">Heading</h1>
<p className="text-sm text-zinc-400">Body text</p>
<span className="font-mono text-lime">200 credits</span>
```

### Spacing

Standard Tailwind spacing scale. Common patterns:

- Card padding: `p-4` (16px) or `p-5` (20px) or `p-6` (24px)
- Section gap: `space-y-6` between sections
- Grid gap: `gap-3` or `gap-4`
- Page padding: `p-6`

## 2. Component Library

### Location: `frontend/src/components/ui/`

47 shadcn/ui components (New York style, JSX, no TypeScript).

### Key Components

```jsx
// Button — use shadcn Button for standard, custom classes for branded
import { Button } from "@/components/ui/button";
<Button variant="outline" size="sm">Standard</Button>
<button className="btn-primary">Branded CTA</button>

// Card
import { Card, CardContent } from "@/components/ui/card";
<Card className="bg-surface-2 border-white/5">
  <CardContent className="py-4">...</CardContent>
</Card>

// Or use the custom card class
<div className="card-thook p-4">...</div>
<div className="card-thook-interactive p-4">Clickable card</div>
```

### Custom Components: `frontend/src/components/`

| Component         | File                    | Purpose                        |
| ----------------- | ----------------------- | ------------------------------ |
| MediaUploader     | `MediaUploader.jsx`     | File/URL upload with preview   |
| NotificationBell  | `NotificationBell.jsx`  | SSE-powered notification badge |
| PersonaShareModal | `PersonaShareModal.jsx` | Share persona link dialog      |
| TemplateCard      | `TemplateCard.jsx`      | Template marketplace card      |
| CampaignCard      | `CampaignCard.jsx`      | Campaign overview card         |
| VoiceCloneCard    | `VoiceCloneCard.jsx`    | Voice clone management         |
| CookieConsent     | `CookieConsent.jsx`     | GDPR cookie banner             |
| ErrorBoundary     | `ErrorBoundary.jsx`     | React error boundary           |

### Configuration: `frontend/components.json`

```json
{
  "style": "new-york",
  "rsc": false,
  "tsx": false,
  "iconLibrary": "lucide",
  "aliases": {
    "components": "@/components",
    "ui": "@/components/ui",
    "lib": "@/lib",
    "hooks": "@/hooks"
  }
}
```

## 3. Frameworks & Libraries

| Library          | Version        | Purpose                                           |
| ---------------- | -------------- | ------------------------------------------------- |
| React            | 18.3.1         | UI framework                                      |
| React Router DOM | 7.5.1          | Client-side routing                               |
| Tailwind CSS     | 3.4.17         | Utility-first styling                             |
| shadcn/ui        | New York style | Component primitives (Radix UI)                   |
| Framer Motion    | 12.38.0        | Animations                                        |
| Lucide React     | 0.507.0        | Icon library                                      |
| Sonner           | 2.0.3          | Toast notifications                               |
| CRACO            | 7.1.0          | CRA config override (webpack alias `@/` → `src/`) |

**Build:** `npm run build` (uses `craco build`)
**Dev:** `npm start` (uses `craco start`)

## 4. Asset Management

- **Media storage:** Cloudflare R2 (S3-compatible)
- **Upload flow:** `POST /api/media/upload-url` → presigned URL → `POST /api/media/confirm`
- **Image references:** R2 public URLs stored in MongoDB `media_assets` collection
- **No local asset directory** — all media is remote via R2
- **Fonts:** Loaded via Google Fonts + Fontshare CDN (no local font files)

## 5. Icon System

**Library:** Lucide React (`lucide-react`)
**Import pattern:**

```jsx
import { Zap, ArrowRight, Check, Settings, Brain } from "lucide-react";

// Standard usage — 14-20px, current color
<Zap size={16} className="text-lime" />
<ArrowRight size={14} />

// Filled icons (rare, only for branding)
<Zap size={14} className="text-black" fill="black" />
```

**Common icons by domain:**
| Domain | Icons |
|--------|-------|
| Branding | `Zap` (logo), `Sparkles` |
| Navigation | `ArrowRight`, `ChevronRight`, `ArrowLeft` |
| Content | `PenLine`, `FileText`, `BookOpen` |
| Platforms | `Linkedin`, `Twitter`, `Instagram` |
| Status | `Check`, `CheckCircle2`, `XCircle`, `AlertCircle`, `Clock` |
| Actions | `RefreshCw`, `Download`, `Copy`, `Trash2`, `Settings` |
| AI/Brain | `Brain`, `Lightbulb`, `Wand2` |

## 6. Styling Approach

### Methodology: Tailwind CSS + Custom Utility Classes

**Custom classes** (defined in `index.css`):

```css
.card-thook        /* Dark card with subtle border, hover border brightens */
.card-thook-interactive  /* Clickable card with lime hover glow + lift */
.btn-primary       /* Lime pill button with glow shadow */
.btn-ghost         /* Glass-morphism button with blur backdrop */
.btn-danger        /* Red subtle button */
.glass             /* Glass-morphism panel */
.hero-glow         /* Background gradient glow effect */
```

### Global Styles

- Body: `bg-[#050505] text-white` with Plus Jakarta Sans
- Headings: `font-family: 'Clash Display'` with `-0.02em` letter-spacing
- All borders default to `border-border` (subtle dark)

### Responsive Design

```jsx
// Mobile-first. Standard breakpoints:
<div className="flex flex-col md:flex-row" />        // Stack on mobile, row on tablet+
<div className="grid grid-cols-1 md:grid-cols-3" />  // 1 col mobile, 3 col desktop
<div className="hidden md:block" />                   // Hide on mobile
<div className="p-4 md:p-6" />                       // Tighter padding on mobile
```

### Animation Patterns (Framer Motion)

```jsx
import { motion, AnimatePresence } from "framer-motion";

// Page enter
<motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}>

// Staggered list
{items.map((item, i) => (
  <motion.div key={item.id} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 + i * 0.05 }}>
))}

// Phase transitions
<AnimatePresence mode="wait">
  {phase === 1 && <motion.div key="p1" exit={{ opacity: 0, x: -20 }}>...</motion.div>}
</AnimatePresence>
```

### Tailwind Custom Animations (from config)

```jsx
<div className="animate-fade-in" />        // 0.4s fade + slide up
<div className="animate-pulse-lime" />      // Lime glow pulse loop
<div className="animate-shimmer" />         // Skeleton loading shimmer
<div className="animate-float" />           // Gentle float loop (hero elements)
```

## 7. Project Structure

```
frontend/src/
├── App.js                          # Root: BrowserRouter + AuthProvider + routes
├── index.css                       # Global styles, CSS vars, custom utilities
├── context/AuthContext.jsx          # Auth state (cookie-based JWT)
├── lib/
│   ├── api.js                      # apiFetch() — centralized API client
│   ├── constants.js                # API_BASE_URL, feature flags, timeouts
│   ├── utils.js                    # cn() merge utility
│   ├── contentExport.js            # Content export helpers
│   ├── campaignsApi.js             # Campaign CRUD helpers
│   └── templatesApi.js             # Template search/filter helpers
├── hooks/
│   ├── use-toast.js                # Sonner toast hook
│   ├── useNotifications.js         # SSE notification hook
│   └── useStrategyFeed.js          # Strategy card feed hook
├── components/
│   ├── ui/                         # 47 shadcn/ui primitives
│   ├── CookieConsent.jsx           # GDPR cookie banner
│   ├── ErrorBoundary.jsx           # Error boundary
│   ├── MediaUploader.jsx           # Upload component
│   └── ...                         # Other custom components
├── pages/
│   ├── LandingPage.jsx             # Public landing
│   ├── AuthPage.jsx                # Login/register
│   ├── PrivacyPolicy.jsx           # /privacy
│   ├── TermsOfService.jsx          # /terms
│   ├── Onboarding/                 # 3-phase wizard
│   ├── Dashboard/                  # 13 dashboard views
│   │   ├── index.jsx               # Dashboard router + sidebar layout
│   │   ├── ContentStudio/          # Core product — content creation
│   │   └── ...
│   └── Public/                     # Public shareable pages
└── __tests__/                      # Jest + RTL tests
```

### Key Patterns

1. **API calls:** Always use `apiFetch()` from `@/lib/api` — never raw `fetch()`
2. **Auth:** Cookie-based (`session_token` httpOnly cookie) — no localStorage tokens
3. **CSRF:** `apiFetch` auto-injects `X-CSRF-Token` header on state-changing requests
4. **Routing:** `ProtectedRoute` wrapper guards authenticated routes
5. **Path alias:** `@/` maps to `src/` via CRACO webpack alias
6. **Toast:** `import { useToast } from '@/hooks/use-toast'` → `toast({ title, description, variant })`

### When Implementing Figma Designs

1. **Check for existing component** in `components/ui/` before creating new ones
2. **Use Tailwind classes** — match the design system tokens above
3. **Use `font-display`** for headings, default font for body
4. **Use `lime` for primary actions**, `violet` for secondary/premium
5. **Wrap in `motion.div`** for entry animations
6. **Add `data-testid`** attributes for testing
7. **Use responsive classes** — `md:` breakpoint for tablet+
