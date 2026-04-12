# Phase 32: Frontend Core Flows Polish - Research

**Researched:** 2026-04-12
**Domain:** React 18 / TailwindCSS / shadcn/ui — frontend UX polish, accessibility, responsive design
**Confidence:** HIGH

---

## Summary

Phase 32 polishes four existing pages (AuthPage, DashboardHome, ContentStudio, Settings) to
production quality. These pages are already wired and functional — the phase is about adding
missing states (skeleton loaders, error+retry, empty CTAs), verifying responsive breakpoints,
and making every interactive element reachable via keyboard.

The codebase already has a solid design system (`card-thook`, `btn-primary`, `.skeleton`,
`.focus-ring` in `index.css`), a Framer Motion 12 animation library, and an established
testing stack (React Testing Library + MSW v2 + CRACO Jest). Most of what is needed is
additive — new state branches, ARIA attributes, `focus-visible` rings, and responsive
flex/grid switches — not structural rewrites.

The main risk is the Settings page, which currently renders only the billing section and has
no profile, connections, or notifications tabs. FEND-04 requires all four tabs to work.
A tab-panel structure needs to be built from scratch using Radix UI's accessible Tabs
primitive (already installed as `@radix-ui/react-tabs` via shadcn/ui).

**Primary recommendation:** Use the existing design system tokens and component primitives
throughout. Never add raw hex colours in JSX. Use Radix Tabs for Settings, `role="alert"`
for inline error messages, and `aria-live="polite"` for dynamic content regions.

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| FEND-01 | Auth page: social login buttons, password validation, inline error messages | Auth page is functionally complete; gaps are password strength indicator and ARIA live regions for error messages |
| FEND-02 | Dashboard: stats, recent content, quick actions with loading/empty states | DashboardHome has StatSkeleton and empty-state CTA; error state on stats fetch is missing (only console.error) |
| FEND-03 | ContentStudio: format picker, generation progress, preview, edit, schedule | All sub-components exist; keyboard nav on the custom toggle, accessible role on AgentPipeline status, schedule action in ContentOutput are gaps |
| FEND-04 | Settings: billing, connections, profile, notifications | Only billing rendered; connections/profile/notifications tabs must be built using Radix Tabs |
| FEND-05 | Every page handles loading, error, and empty states | Skeleton pattern exists; error+retry branch is missing on DashboardHome stats, ContentStudio tier fetch, and Settings fetch |
| FEND-06 | Every page is responsive at 375px / 768px / 1440px | Dashboard uses `grid-cols-2 md:grid-cols-4`; sidebar overlay on mobile exists; ContentStudio has `flex-col md:flex-row` — verify no horizontal overflow at 375px |
| FEND-07 | Keyboard navigation on all interactive elements | Custom buttons lack `type="button"` guarantees; video toggle toggle has no keyboard handler; focus-ring class exists but is not applied to all interactive elements |
</phase_requirements>

---

## Project Constraints (from CLAUDE.md)

- Branch from `dev`, PR targets `dev` — never commit to `main`
- Branch naming: `feat/32-frontend-core-flows-polish`
- No new npm packages without noting in PR description
- Frontend: always use `apiFetch()` from `@/lib/api`, never raw `fetch()`
- Auth: cookie-based `session_token` — no localStorage tokens
- CSRF: `apiFetch` auto-injects `X-CSRF-Token` on state-changing requests
- Path alias `@/` maps to `src/` via CRACO webpack alias
- Toast: `import { useToast } from '@/hooks/use-toast'`
- Never hardcode hex in JSX — always use Tailwind design system tokens
- Framer Motion: use `motion.div` + `AnimatePresence` for enter/exit transitions
- `data-testid` attributes required on all interactive and significant elements
- No `console.log` in production code
- Functions under 50 lines; components under 100 lines where possible

---

## Standard Stack

### Core Libraries (already installed)

| Library | Version | Purpose | Usage in This Phase |
|---------|---------|---------|---------------------|
| React | 18.3.1 | UI framework | All pages |
| TailwindCSS | 3.4.17 | Utility CSS | Responsive classes, skeleton states |
| Framer Motion | 12.38.0 | Animations | Page/state transitions |
| shadcn/ui | New York style | Component primitives | Tabs, Dialog, Badge |
| Radix UI Tabs | via shadcn | Accessible tab panels | Settings page tabs |
| Lucide React | 0.507.0 | Icons | State icons (AlertCircle, RefreshCw) |
| React Hook Form | 7.56.2 | Form state | Auth password validation |
| Zod | 3.24.4 | Schema validation | Auth password rules |
| Sonner / useToast | 2.0.3 | Toast notifications | Error toasts |

### Testing Stack (already installed)

| Library | Version | Purpose |
|---------|---------|---------|
| @testing-library/react | 14.3.1 | Component render + query |
| @testing-library/user-event | 14.6.1 | Keyboard/mouse interaction |
| msw | 2.12.14 | API mocking (handlers in `src/mocks/`) |
| jest (via craco) | CRA built-in | Test runner |
| @testing-library/jest-dom | 6.9.1 | Custom matchers |

**Test run command:** `cd frontend && npm test -- --watchAll=false`

### No New Dependencies Needed

All required primitives exist. Do NOT install:
- `react-aria` (Radix already covers a11y needs)
- `react-hot-toast` (Sonner is already configured)
- `react-query` (apiFetch + useState is the project pattern)

---

## Architecture Patterns

### Pattern 1: Three-State Async UI (loading / error / data)

Every page that fetches on mount MUST implement all three branches:

```jsx
// Source: existing DashboardHome.jsx — extend this pattern everywhere
if (loading) return <SkeletonLayout />;
if (error) return <ErrorState message={error} onRetry={fetchData} />;
return <DataView data={data} />;
```

**Skeleton pattern** — use project's `.skeleton` class:

```jsx
function SkeletonCard() {
  return (
    <div className="card-thook p-4">
      <div className="skeleton h-3 w-24 mb-2" />
      <div className="skeleton h-8 w-32" />
    </div>
  );
}
```

**Error + retry pattern** — use toast AND inline error:

```jsx
function ErrorState({ message, onRetry }) {
  return (
    <div className="card-thook p-6 text-center" role="alert">
      <AlertCircle className="text-red-400 mx-auto mb-3" size={24} />
      <p className="text-red-400 text-sm mb-4">{message || "Something went wrong"}</p>
      <button
        type="button"
        onClick={onRetry}
        className="btn-ghost text-sm gap-2 inline-flex items-center"
      >
        <RefreshCw size={14} /> Try Again
      </button>
    </div>
  );
}
```

**Empty state pattern** — always include a CTA:

```jsx
function EmptyState({ message, action, actionLabel }) {
  return (
    <div className="card-thook p-8 text-center">
      <p className="text-zinc-500 text-sm mb-3">{message}</p>
      {action && (
        <button type="button" onClick={action} className="text-lime text-sm hover:text-lime/80">
          {actionLabel} →
        </button>
      )}
    </div>
  );
}
```

### Pattern 2: Settings Tab Panel (Radix Tabs)

The Settings page needs tabs for Billing, Connections, Profile, Notifications. Use the
shadcn/ui Tabs primitive that wraps Radix UI — keyboard navigation (arrow keys, Home/End)
is built in.

```jsx
// Source: shadcn/ui Tabs — already in @/components/ui/tabs
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";

export default function Settings() {
  return (
    <Tabs defaultValue="billing" className="space-y-6">
      <TabsList className="bg-surface-2 border border-white/5">
        <TabsTrigger value="billing">Billing</TabsTrigger>
        <TabsTrigger value="connections">Connections</TabsTrigger>
        <TabsTrigger value="profile">Profile</TabsTrigger>
        <TabsTrigger value="notifications">Notifications</TabsTrigger>
      </TabsList>
      <TabsContent value="billing"><BillingTab /></TabsContent>
      <TabsContent value="connections"><ConnectionsTab /></TabsContent>
      <TabsContent value="profile"><ProfileTab /></TabsContent>
      <TabsContent value="notifications"><NotificationsTab /></TabsContent>
    </Tabs>
  );
}
```

Radix Tabs provides `role="tablist"`, `role="tab"`, `role="tabpanel"`, `aria-selected`,
`aria-controls`, `aria-labelledby` automatically. No manual ARIA attributes needed.

### Pattern 3: Keyboard-Accessible Custom Controls

The video toggle button in InputPanel has no keyboard event handler. Buttons that act as
checkboxes must use `role="switch"` and respond to Space/Enter:

```jsx
// Pattern for the video toggle in InputPanel.jsx
<button
  type="button"
  role="switch"
  aria-checked={generateVideo}
  aria-label="Generate video with content"
  onClick={() => videoEnabled && onGenerateVideoChange?.(!generateVideo)}
  onKeyDown={(e) => {
    if ((e.key === 'Enter' || e.key === ' ') && videoEnabled) {
      e.preventDefault();
      onGenerateVideoChange?.(!generateVideo);
    }
  }}
  disabled={!videoEnabled}
  className={`relative w-10 h-5 rounded-full transition-colors ${
    generateVideo && videoEnabled ? "bg-violet" : "bg-white/10"
  } ${!videoEnabled ? "opacity-40 cursor-not-allowed" : "cursor-pointer"}`}
  data-testid="video-toggle"
>
  ...
</button>
```

### Pattern 4: Responsive Layout — ContentStudio at 375px

The ContentStudio uses `flex-col md:flex-row` and `h-[calc(100vh-4rem)]`. At 375px the
left InputPanel takes full height in column mode. The `overflow-hidden` on the outer
container clips the right panel. The correct pattern:

```jsx
// Mobile: stacked, each section scrolls independently
// Tablet+: side by side with fixed widths
<div className="flex flex-col md:flex-row">
  {/* Left panel: fixed height on mobile to prevent full-page takeover */}
  <div className="w-full md:w-[400px] flex-shrink-0
                  h-auto md:h-[calc(100vh-4rem)]
                  overflow-y-auto
                  border-b md:border-b-0 md:border-r border-white/5">
    <InputPanel ... />
  </div>
  {/* Right panel */}
  <div className="flex-1 min-h-[50vh] md:h-[calc(100vh-4rem)] overflow-y-auto">
    ...
  </div>
</div>
```

### Pattern 5: Auth Password Validation (FEND-01)

Current state: password input has no client-side validation beyond `required`. For production
quality, add inline strength indicator and validation rules without introducing React Hook Form
for this simple form (project uses controlled state already).

```jsx
// Validate on change, display requirements inline
const passwordRules = [
  { test: (p) => p.length >= 8, label: "At least 8 characters" },
  { test: (p) => /[A-Z]/.test(p), label: "One uppercase letter" },
  { test: (p) => /[0-9]/.test(p), label: "One number" },
];

// Show only during registration, only after first interaction
{tab === "register" && passwordTouched && (
  <ul className="space-y-1 mt-1" role="list" aria-label="Password requirements">
    {passwordRules.map(rule => (
      <li key={rule.label} className={`text-xs flex items-center gap-1.5 ${
        rule.test(form.password) ? "text-lime" : "text-zinc-500"
      }`}>
        <Check size={10} className={rule.test(form.password) ? "opacity-100" : "opacity-0"} />
        {rule.label}
      </li>
    ))}
  </ul>
)}
```

### Pattern 6: ARIA Live Regions for Dynamic Content

Error messages rendered conditionally must be announced to screen readers:

```jsx
// For auth error — replace the current plain <p> with:
{error && (
  <p
    data-testid="auth-error"
    role="alert"
    aria-live="assertive"
    className="text-red-400 text-sm text-center"
  >
    {error}
  </p>
)}

// For non-urgent status updates (agent pipeline progress):
<div aria-live="polite" aria-label="Generation progress">
  ...agent status cards...
</div>
```

### Pattern 7: Focus Ring

The project has `.focus-ring` defined in `index.css`:
```css
.focus-ring:focus-visible {
  outline: none;
  box-shadow: 0 0 0 2px #050505, 0 0 0 4px #D4FF00;
}
```

Apply `focus-ring` class to ALL custom buttons and interactive elements that do not use
shadcn/ui primitives (which handle focus internally via Radix).

### Project Structure (relevant to this phase)

```
frontend/src/
├── pages/
│   ├── AuthPage.jsx                # FEND-01 — add password validation + ARIA
│   ├── Dashboard/
│   │   ├── DashboardHome.jsx       # FEND-02 — add error+retry state
│   │   ├── ContentStudio/
│   │   │   ├── index.jsx           # FEND-03 — keyboard nav, responsive fix
│   │   │   ├── InputPanel.jsx      # FEND-03, FEND-07 — video toggle keyboard
│   │   │   ├── AgentPipeline.jsx   # FEND-05 — aria-live region
│   │   │   └── ContentOutput.jsx   # FEND-03 — schedule action
│   │   └── Settings.jsx            # FEND-04 — add Tabs, 3 new tab sections
├── components/
│   └── ErrorBoundary.jsx           # needs visual polish + Sentry integration
└── __tests__/
    └── pages/                      # test files live here (MSW v2 + RTL)
```

### Anti-Patterns to Avoid

- **Raw hex in JSX:** `style={{ color: '#D4FF00' }}` — use `className="text-lime"` instead
- **Global error boundary only:** Each page should have local error+retry before the global boundary catches it
- **`aria-label` on `<div>`:** Use semantic elements or proper roles. `<div role="alert">` is fine; `<div aria-label="...">` on a non-interactive div is noise
- **Missing `type="button"`:** Every `<button>` that is not a form submit needs `type="button"` to prevent accidental form submission
- **Inline `onKeyDown` for standard buttons:** Browsers handle Enter/Space for `<button>`. Only add `onKeyDown` for custom `role="switch"` / `role="checkbox"` patterns
- **Skipping `data-testid`:** Every new interactive element needs a testid for RTL and Playwright

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Accessible tab panels | Custom div with click handlers | `Tabs` from `@/components/ui/tabs` (Radix) | Keyboard nav (arrows, Home/End), ARIA attributes, roving tabindex — all free |
| Modal/dialog | Custom overlay div | `Dialog` from `@/components/ui/dialog` | Focus trap, Escape key, aria-modal — complex to get right |
| Form validation schema | Custom regex checks | Zod schemas + React Hook Form (already installed) | Field-level errors, touched state, async validation |
| Skeleton loading animation | Custom CSS | `.skeleton` class from `index.css` | Already has shimmer keyframe |
| Progress indicators | Custom CSS bar | `.progress-bar` + `.progress-bar-fill` from `index.css` | Consistent brand gradient |
| Toast notifications | Custom toast component | `useToast` from `@/hooks/use-toast` | Sonner is already wired, design consistent |
| Focus management in modals | `useRef` + `addEventListener` | Radix Dialog handles focus trap | Missing one case breaks a11y audit |

---

## Common Pitfalls

### Pitfall 1: ErrorBoundary Has Inconsistent Styling

**What goes wrong:** The existing `ErrorBoundary.jsx` uses `lime-400` Tailwind class (not in
design system — the correct token is `lime` = `#D4FF00`) and `bg-[#0a0a0b]` instead of
`bg-[#050505]`. The button text reads "Warning" as an emoji fallback (the actual emoji was
removed per project rules).

**Why it happens:** The boundary was written before the design system was finalized.

**How to avoid:** Update ErrorBoundary to use `bg-[#050505]`, `bg-lime`, `text-black` (for the
button), and remove the "Warning" text placeholder. Also add `componentDidCatch` logging to
Sentry if configured.

**Warning signs:** Visual mismatch between error boundary screen and the rest of the app.

### Pitfall 2: Settings Page Has No Profile / Connections / Notifications Data

**What goes wrong:** The backend already has `/api/platforms` (platform connections) and
`/api/auth/me` (profile data) endpoints. Connections tab can render live data. Profile tab
requires a `PATCH /api/auth/me` endpoint — verify it exists before building the form.

**Why it happens:** Settings was built incrementally around billing only.

**How to avoid:** Before building each tab, verify the backend endpoint exists via `apiFetch`
in a dev session. If `PATCH /api/auth/me` does not exist, the profile tab should be read-only
for this phase (display user data from `useAuth().user`, no edit form).

**Warning signs:** 404 errors on fetch calls in Settings tab panels.

### Pitfall 3: ContentStudio at 375px Has Horizontal Scroll

**What goes wrong:** The InputPanel's textarea has a fixed internal character counter row.
Combined with `flex-col` stacking, the content can overflow at 375px if any child has
`min-width` that exceeds viewport.

**Why it happens:** Platform selector buttons use `flex-1` inside a flex row — they shrink
correctly. But the character counter uses `font-mono` which can push widths on small screens.

**How to avoid:** Add `overflow-x-hidden` to the outer ContentStudio container. Verify by
setting Chrome DevTools to 375px. Look for any absolute-width or `min-w-[Npx]` classes in
InputPanel.

**Warning signs:** Horizontal scroll indicator appears at the bottom of viewport on mobile.

### Pitfall 4: Radix Tabs Styles Need Dark Theme Override

**What goes wrong:** shadcn/ui Tabs are styled with light-mode defaults. The ThookAI dark
design system needs overrides for `TabsTrigger` active/inactive states to use lime/zinc
palette.

**How to avoid:** Apply Tailwind classes directly on the shadcn Tabs components:

```jsx
<TabsList className="bg-surface-2 border border-white/5 p-1 h-auto">
  <TabsTrigger
    value="billing"
    className="data-[state=active]:bg-white/10 data-[state=active]:text-white
               text-zinc-500 rounded-md text-sm"
  >
    Billing
  </TabsTrigger>
</TabsList>
```

**Warning signs:** Tab triggers render with white background or default blue ring on active.

### Pitfall 5: MSW Handlers Missing for New Settings Tabs

**What goes wrong:** New Settings tabs fetch `/api/platforms`, `PATCH /api/auth/me`,
`/api/auth/me` profile fields. If MSW handlers are not added to `src/mocks/handlers.js`,
RTL tests will get network errors and `console.error` spam.

**How to avoid:** For every new `apiFetch` call added in this phase, add a corresponding
handler to `src/mocks/handlers.js` with realistic mock data.

### Pitfall 6: Keyboard Navigation — Tab Order in ContentStudio

**What goes wrong:** ContentStudio has a left panel (InputPanel) and right panel
(ContentOutput). Tab order naturally flows left-to-right, but the Generate button is at the
bottom of the left panel. After tabbing through the button, focus jumps to the right panel's
edit/approve controls — which are only visible when a job is done. When no job exists,
focus falls into the empty state, which has no interactive elements.

**How to avoid:** Ensure the empty state has at least one focusable element, or use
`tabIndex={-1}` on the empty state container and manage focus programmatically when the job
state transitions from running to done. This is a LOW priority enhancement — document it as
a known limitation if not fixed in this phase.

---

## Code Examples

### Skeleton Loader Pattern (verified from existing code)

```jsx
// Source: DashboardHome.jsx StatSkeleton — use as model
function SkeletonCard() {
  return (
    <div className="card-thook p-4 animate-pulse">
      <div className="h-3 w-24 bg-zinc-800 rounded mb-2" />
      <div className="h-8 w-32 bg-zinc-800 rounded" />
    </div>
  );
}

// Alternative using the .skeleton CSS class (index.css)
function SkeletonCard() {
  return (
    <div className="card-thook p-4">
      <div className="skeleton h-3 w-24 mb-2 rounded" />
      <div className="skeleton h-8 w-32 rounded" />
    </div>
  );
}
```

### Error State with Retry (new pattern to implement)

```jsx
function PageErrorState({ message, onRetry }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 px-6" role="alert">
      <AlertCircle className="text-red-400 mb-3" size={28} />
      <p className="text-red-400 text-sm text-center mb-4">
        {message || "Failed to load. Please try again."}
      </p>
      <button
        type="button"
        onClick={onRetry}
        className="btn-ghost text-sm flex items-center gap-2"
      >
        <RefreshCw size={14} />
        Try Again
      </button>
    </div>
  );
}
```

### apiFetch with Error Handling Pattern

```jsx
// Source: Settings.jsx fetchData — this is the project's established pattern
const fetchData = async () => {
  setLoading(true);
  setError(null);
  try {
    const res = await apiFetch('/api/endpoint');
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    setData(data);
  } catch (err) {
    setError(err.message || "Failed to load");
    toast({ title: "Error", description: "Failed to load data", variant: "destructive" });
  } finally {
    setLoading(false);
  }
};
```

### Test Pattern (RTL + MSW v2)

```jsx
// Source: existing ContentStudio.test.jsx and Sidebar.test.jsx — follow exactly
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { http, HttpResponse } from 'msw';
import { server } from '@/mocks/server';
import { AuthProvider } from '@/context/AuthContext';

function TestWrapper({ children, initialEntries = ['/dashboard/settings'] }) {
  return (
    <MemoryRouter initialEntries={initialEntries}>
      <AuthProvider>{children}</AuthProvider>
    </MemoryRouter>
  );
}

describe('Settings', () => {
  test('shows_skeleton_during_load: skeleton appears before data resolves', async () => {
    // Override handler to delay response
    server.use(
      http.get('*/api/billing/subscription', async () => {
        await new Promise(r => setTimeout(r, 100));
        return HttpResponse.json({ tier: 'free' });
      })
    );
    render(<TestWrapper><Settings /></TestWrapper>);
    // Skeleton should be visible immediately
    expect(document.querySelector('.animate-pulse')).toBeInTheDocument();
  });
});
```

### Radix Tabs (shadcn/ui) Integration

```jsx
// Source: shadcn/ui docs — Tabs component is at @/components/ui/tabs
// Verify file exists: frontend/src/components/ui/tabs.jsx
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";

// Usage in Settings.jsx
<Tabs defaultValue="billing">
  <TabsList className="bg-surface-2 border border-white/5 rounded-xl p-1 w-full justify-start h-auto">
    {["billing", "connections", "profile", "notifications"].map(tab => (
      <TabsTrigger
        key={tab}
        value={tab}
        className="capitalize text-sm text-zinc-500 rounded-lg px-4 py-2
                   data-[state=active]:bg-white/10 data-[state=active]:text-white
                   focus-ring"
        data-testid={`tab-${tab}`}
      >
        {tab}
      </TabsTrigger>
    ))}
  </TabsList>
  <TabsContent value="billing"><BillingSection /></TabsContent>
  <TabsContent value="connections"><ConnectionsSection /></TabsContent>
  <TabsContent value="profile"><ProfileSection /></TabsContent>
  <TabsContent value="notifications"><NotificationsSection /></TabsContent>
</Tabs>
```

---

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|------------------|--------|
| Manual focus management for tabs | Radix UI roving tabindex | No manual `onKeyDown` needed |
| `aria-label` on all things | Role-based semantics with Radix | Correct screen reader experience |
| `animate-pulse` only for skeletons | `.skeleton` shimmer keyframe | More polished loading feel |
| Custom modal with `onClickOutside` | Radix Dialog with `onOpenChange` | Escape key + focus trap handled |

**Deprecated/outdated in this codebase:**
- `ErrorBoundary` uses `lime-400` Tailwind class which does not exist in config — correct token is `lime` (no modifier)
- `ErrorBoundary` render shows the string "Warning" instead of a proper icon — should be `AlertTriangle` from lucide-react

---

## Open Questions

1. **Does `PATCH /api/auth/me` exist for profile editing?**
   - What we know: `/api/auth/me` GET returns `{ user_id, email, name, subscription_tier, credits, onboarding_completed }`
   - What's unclear: Whether a PATCH endpoint exists for updating `name` and email
   - Recommendation: If PATCH does not exist, make the Profile tab read-only in this phase. Do not build the endpoint in Phase 32 (scope is frontend only).

2. **Does the Connections tab need to call `/api/platforms` for live status?**
   - What we know: A Connections page exists at `Dashboard/Connections.jsx` — it can be rendered directly in the Connections tab
   - Recommendation: Embed the existing `Connections` component inside the tab panel rather than rebuilding it. This is the safest approach.

3. **What do Notifications settings control?**
   - What we know: `NotificationBell.jsx` exists; SSE-powered. No backend notification preferences endpoint identified.
   - Recommendation: Build a stub UI showing notification preference toggles as static (no-op) checkboxes for this phase. Flag as needing backend endpoint in Phase 34 (SECR).

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Node.js | Frontend build | Yes | 20.15.0 | — |
| npm | Package management | Yes | 10.7.0 | — |
| shadcn/ui tabs component | Settings tabs | Check at runtime | via Radix UI | Build manually |
| CRACO | Test runner | Yes | 7.1.0 | — |
| MSW | Test mocking | Yes | 2.12.14 | — |

**Note on shadcn/ui tabs:** The `components.json` declares shadcn/ui is installed. Verify
`frontend/src/components/ui/tabs.jsx` exists before the planning stage. If missing, the
planner must add a Wave 0 task to generate it via `npx shadcn@latest add tabs`.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | Jest (via CRACO + react-scripts), React Testing Library 14 |
| Config file | `frontend/craco.config.js` (jest key) |
| Quick run command | `cd frontend && npm test -- --watchAll=false --testPathPattern="__tests__/pages/(Auth|DashboardHome|ContentStudio|Settings)"` |
| Full suite command | `cd frontend && npm test -- --watchAll=false` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| FEND-01 | Auth page renders without crash | unit | `npm test -- --watchAll=false --testPathPattern="AuthPage"` | No — Wave 0 |
| FEND-01 | Inline password validation rules shown during registration | unit | same | No — Wave 0 |
| FEND-01 | Error message rendered when login fails | unit | same | No — Wave 0 |
| FEND-01 | Google auth button present | unit | same | No — Wave 0 |
| FEND-02 | DashboardHome shows skeleton during fetch | unit | `--testPathPattern="DashboardHome"` | No — Wave 0 |
| FEND-02 | DashboardHome shows error+retry when stats fetch fails | unit | same | No — Wave 0 |
| FEND-02 | DashboardHome empty state CTA visible when no jobs | unit | same | No — Wave 0 |
| FEND-03 | ContentStudio renders all three platform tabs | unit | `--testPathPattern="ContentStudio"` | Yes (partial) |
| FEND-03 | Video toggle responds to keyboard (Space key) | unit | same | No — Wave 0 |
| FEND-04 | Settings shows all four tab triggers | unit | `--testPathPattern="Settings"` | No — Wave 0 |
| FEND-04 | Settings billing tab shows credits card | unit | same | No — Wave 0 |
| FEND-05 | Settings shows skeleton while loading | unit | same | No — Wave 0 |
| FEND-05 | Settings shows error+retry when fetch fails | unit | same | No — Wave 0 |
| FEND-07 | All tab triggers are keyboard accessible (tabIndex check) | unit | via aria roles in RTL | No — Wave 0 |

### Sampling Rate

- **Per task commit:** `cd frontend && npm test -- --watchAll=false --testPathPattern="pages" --passWithNoTests`
- **Per wave merge:** `cd frontend && npm test -- --watchAll=false`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `src/__tests__/pages/AuthPage.test.jsx` — covers FEND-01
- [ ] `src/__tests__/pages/DashboardHome.test.jsx` — covers FEND-02, FEND-05
- [ ] `src/__tests__/pages/Settings.test.jsx` — covers FEND-04, FEND-05
- [ ] MSW handlers for new endpoints: `GET /api/platforms`, `GET /api/auth/me` (profile), `PATCH /api/auth/me` — add to `src/mocks/handlers.js`
- [ ] Verify `src/components/ui/tabs.jsx` exists — if not, run `npx shadcn@latest add tabs` from `frontend/`

---

## Sources

### Primary (HIGH confidence)
- Source code audit — `frontend/src/pages/AuthPage.jsx`, `DashboardHome.jsx`, `ContentStudio/index.jsx`, `Settings.jsx`, `ErrorBoundary.jsx`
- `frontend/tailwind.config.js` and `frontend/src/index.css` — verified all custom classes and tokens
- `frontend/src/mocks/handlers.js` — confirmed MSW v2 pattern
- `frontend/craco.config.js` — confirmed Jest/CRACO test setup
- `frontend/src/__tests__/pages/ContentStudio.test.jsx` and `Sidebar.test.jsx` — confirmed RTL test patterns
- `.planning/REQUIREMENTS.md` — all FEND-0x requirements

### Secondary (MEDIUM confidence)
- Radix UI Tabs documentation — accessible tab pattern (Radix is a production-grade library, confidence HIGH for its own a11y claims)
- shadcn/ui Tabs component pattern — consistent with installed library version

### Tertiary (LOW confidence)
- Assumption that `PATCH /api/auth/me` does not exist — not verified by reading backend routes directory (read backend routes for confirmation before building profile edit form)

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries confirmed installed and versioned in package.json
- Architecture: HIGH — patterns derived directly from existing codebase code
- Pitfalls: HIGH — identified from direct code audit
- Backend endpoint availability for new Settings tabs: LOW — needs verification during planning

**Research date:** 2026-04-12
**Valid until:** 2026-05-12 (stable stack, 30-day window)
