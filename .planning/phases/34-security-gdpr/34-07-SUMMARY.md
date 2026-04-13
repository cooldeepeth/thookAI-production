---
phase: 34-security-gdpr
plan: 07
status: complete
retroactive: true
commit: a9e2cb5
requirements:
  - SECR-11
---

# Plan 34-07: PostHog Cookie Consent Gate — SUMMARY

> Retroactive summary reconstructed from `.planning/phases/34-security-gdpr/34-VERIFICATION.md` and commit `a9e2cb5` (`feat(34-07): gate PostHog init behind explicit cookie consent`).
>
> **CONTEXT FLAG (2026-04-14):** The operator audit noted this fix is currently dev-only — the production deploy at `frontend/public/index.html:119` still carries the unconditional `posthog.init(...)` call until the next Vercel deploy picks up this commit. See H3 in `.planning/audit/OPERATOR-ACTIONS.md`. The code change below is correct and merged to `dev`; the gap is a deployment step, not an implementation defect.

## Files Modified
- `frontend/public/index.html`
- `frontend/src/components/CookieConsent.jsx`

## Changes — index.html (the critical #1 GDPR gap from research)

The unconditional `posthog.init(...)` call that fired on every page load before the React consent banner rendered has been wrapped in a consent-gated IIFE:

```javascript
// SECR-11: Only initialize PostHog after GDPR cookie consent
(function() {
  var consent = localStorage.getItem('thookai_cookie_consent');
  if (consent === 'accepted') {
    posthog.init("phc_xAvL2Iq4tFmANRE7kzbKwaSqp1HJjN7x48s3vr0CMjs", {
      api_host: "https://us.i.posthog.com",
      person_profiles: "identified_only",
      session_recording: {
        recordCrossOriginIframes: true,
        capturePerformance: false
      }
    });
  }
  // If consent !== 'accepted': stub is loaded for later use, but no data is sent
})();
```

The PostHog snippet/stub (`!(function(t,e){...})(document, window.posthog || [])`) is preserved unchanged — only the `init()` call is gated. This lets `opt_in_capturing()` work later once init is triggered.

React `useEffect`-based gating would not work here because the `<script>` block runs synchronously at DOM parse time, before React hydrates.

## Changes — CookieConsent.jsx

Accept handler updated to retroactively initialize PostHog for first-time visitors (who had no stub init at page load):

```javascript
const accept = () => {
  localStorage.setItem(CONSENT_KEY, 'accepted');
  setVisible(false);
  if (window.posthog) {
    if (typeof window.posthog.__loaded === 'undefined' || !window.posthog.__loaded) {
      // First-time visitor — init now
      window.posthog.init('phc_xAvL2Iq4tFmANRE7kzbKwaSqp1HJjN7x48s3vr0CMjs', {
        api_host: 'https://us.i.posthog.com',
        person_profiles: 'identified_only',
      });
    } else if (window.posthog.has_opted_out_capturing?.()) {
      // Previously declined, now accepting — reverse opt-out
      window.posthog.opt_in_capturing();
    }
    // else: already initialized and tracking — no-op
  }
};
```

Decline handler unchanged — still calls `opt_out_capturing()` and sets `CONSENT_KEY` to `'declined'`.

## Consent state matrix

| Visitor state | Page load behavior | Accept click |
|---|---|---|
| First-time visitor (no localStorage) | Stub loads, init NOT called, no data sent | `posthog.init()` called once, tracking begins |
| Returning visitor — previously accepted | `init()` fires automatically inside IIFE, tracking active | (banner hidden) |
| Returning visitor — previously declined | Stub loaded, init NOT called, no data sent | `opt_in_capturing()` called (switch from opt-out to opt-in) |

## Phase 33 integrity check

Phase 33's OG meta tags, canonical link, and `og-image.png` reference (added in 33-05) confirmed intact after the `index.html` edit. The consent-gate IIFE was inserted inside the existing `<script>` block without touching any `<meta>` tag.

## Verification
```
$ grep -n "thookai_cookie_consent" frontend/public/index.html
(1 line inside the IIFE)

$ grep -n "posthog.init(" frontend/public/index.html
(1 line — inside the consent IIFE, not at top level)

$ grep -n "posthog.init\|__loaded" frontend/src/components/CookieConsent.jsx
(init call + __loaded check both present)

$ grep -c "og:title\|og:image\|twitter:card\|canonical" frontend/public/index.html
4  # Phase 33 tags intact

$ cd frontend && npm run build
(PASS)
```

## Requirements Satisfied
- **SECR-11** — PostHog consent gate (the #1 critical GDPR gap from research): PASS on `dev` branch. **Production redeploy pending** to pick up this commit — see operator audit H3.

## Notes
- PostHog API key `phc_xAvL2Iq4tFmANRE7kzbKwaSqp1HJjN7x48s3vr0CMjs` preserved exactly between index.html and CookieConsent.jsx — both must stay in sync if rotated.
- Inline execution by orchestrator.
