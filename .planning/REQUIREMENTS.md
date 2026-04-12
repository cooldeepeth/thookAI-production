# Requirements: ThookAI v3.0 — Distribution-Ready Platform Rebuild

**Defined:** 2026-04-12
**Core Value:** Proactive, personalized content creation at scale — every feature works perfectly end-to-end, ready for real users.

## v3.0 Requirements

Requirements for distribution-ready launch. Each maps to roadmap phases 26-35.

### Backend Hardening

- [x] **BACK-01**: Every route file (26 files) tested against production with curl — each endpoint returns correct data
- [x] **BACK-02**: Every endpoint has Pydantic input validation with field constraints
- [x] **BACK-03**: All error responses follow standardized format (status code, detail message, error_code)
- [x] **BACK-04**: Every protected endpoint rejects unauthenticated requests with 401
- [x] **BACK-05**: Every endpoint handles missing/malformed request body gracefully (400, not 500)
- [x] **BACK-06**: Credit-consuming endpoints check balance before executing and refund on failure
- [x] **BACK-07**: Rate limiting configured per endpoint (auth endpoints stricter)
- [x] **BACK-08**: Endpoint registry document (.planning/audit/BACKEND-API-AUDIT.md) with status per endpoint

### Onboarding

- [x] **ONBD-01**: User completes multi-step onboarding wizard with progress indicator and animations
- [x] **ONBD-02**: User can record voice sample in browser or upload audio file during onboarding
- [x] **ONBD-03**: User can paste 3-5 past posts for writing style analysis during onboarding
- [x] **ONBD-04**: User can pick visual identity preferences (color palette, aesthetic) during onboarding
- [x] **ONBD-05**: Persona generation uses all inputs (questions + voice + writing + visual) to produce rich persona
- [x] **ONBD-06**: Persona stores voice_style, visual_preferences, writing_samples, personality_traits
- [x] **ONBD-07**: Onboarding supports save-as-you-go, skip/back navigation, and error recovery at every step
- [x] **ONBD-08**: LLM model name bug in onboarding.py fixed — real persona generation works

### Content Generation

- [x] **CONT-01**: User can generate LinkedIn text post with persona-aware voice
- [x] **CONT-02**: User can generate LinkedIn article with persona-aware voice
- [x] **CONT-03**: User can generate LinkedIn carousel (text + design slides)
- [x] **CONT-04**: User can generate X tweet with persona-aware voice
- [x] **CONT-05**: User can generate X thread (3-10 tweets with hooks)
- [x] **CONT-06**: User can generate Instagram feed caption with persona-aware voice
- [x] **CONT-07**: User can generate Instagram reel script
- [x] **CONT-08**: User can generate Instagram story sequence
- [x] **CONT-09**: Each format uses platform-specific Writer prompts (not generic)
- [x] **CONT-10**: ContentStudio UI has format selection per platform
- [x] **CONT-11**: User can edit, approve, and schedule generated content
- [x] **CONT-12**: Content generation shows real-time pipeline progress (Commander→Scout→Thinker→Writer→QC)

### Media Pipeline

- [ ] **MDIA-01**: Auto-generate featured image for every post (DALL-E/FAL.ai)
- [x] **MDIA-02**: Generate LinkedIn carousel slides (text + design) via Remotion
- [ ] **MDIA-03**: Generate short-form video from script (Runway/Luma)
- [ ] **MDIA-04**: Generate voice narration from post text (ElevenLabs/OpenAI TTS)
- [x] **MDIA-05**: Remotion renders compositions into downloadable video files
- [x] **MDIA-06**: Generated media attached to content jobs and downloadable
- [ ] **MDIA-07**: Media display works in content preview (images, videos, audio players)
- [ ] **MDIA-08**: R2 upload flow works end-to-end (presigned URL, browser upload, confirm)

### Social Publishing

- [ ] **PUBL-01**: User can connect LinkedIn account via OAuth and publish UGC posts with media
- [ ] **PUBL-02**: User can connect X account via OAuth and publish tweets/threads with media
- [ ] **PUBL-03**: User can connect Instagram account via Meta OAuth and publish posts with media
- [x] **PUBL-04**: OAuth token auto-refresh before expiry for all platforms
- [ ] **PUBL-05**: Publishing status tracked: pending → publishing → published/failed
- [ ] **PUBL-06**: Platform token encryption verified working in production (Fernet)
- [ ] **PUBL-07**: Published content shows real engagement metrics when available

### Smart Scheduling

- [ ] **SCHD-01**: AI suggests optimal posting times per platform based on engagement patterns
- [ ] **SCHD-02**: User can approve/modify suggested schedule
- [ ] **SCHD-03**: Calendar view shows all scheduled posts across platforms
- [ ] **SCHD-04**: Scheduled posts publish automatically at scheduled time via Celery Beat

### Frontend Polish

- [ ] **FEND-01**: Auth page works flawlessly — social login buttons, password validation, error messages
- [ ] **FEND-02**: Dashboard shows stats, recent content, quick actions with loading/empty states
- [ ] **FEND-03**: ContentStudio has format picker, generation progress, preview, edit, schedule
- [ ] **FEND-04**: Settings page works: billing, connections, profile, notifications
- [ ] **FEND-05**: Every page handles loading, error, and empty states
- [ ] **FEND-06**: Every page is responsive (375px mobile, 768px tablet, 1440px desktop)
- [ ] **FEND-07**: Keyboard navigation works on all interactive elements

### Design & Landing

- [ ] **DSGN-01**: Consistent design system applied across all pages (colors, typography, spacing, components)
- [ ] **DSGN-02**: Landing page has hero, features, how-it-works, pricing (plan builder), CTA, footer
- [ ] **DSGN-03**: Landing page is conversion-optimized with animations and social proof section
- [ ] **DSGN-04**: Mobile-first responsive design on landing page
- [ ] **DSGN-05**: SEO meta tags and Open Graph tags on all public pages

### Security & GDPR

- [ ] **SECR-01**: Every POST endpoint has Pydantic models with field constraints (input validation)
- [ ] **SECR-02**: All text inputs sanitized for XSS before storage
- [ ] **SECR-03**: No string interpolation in MongoDB queries (injection prevention)
- [ ] **SECR-04**: Every state-changing endpoint has CSRF protection
- [ ] **SECR-05**: Rate limiting tuned per endpoint with per-user limits
- [ ] **SECR-06**: No hardcoded secrets in codebase (grep verification)
- [ ] **SECR-07**: No stack traces in production error responses
- [ ] **SECR-08**: Dependency audit passes — 0 critical/high vulnerabilities
- [ ] **SECR-09**: GDPR: user can export all their data via API
- [ ] **SECR-10**: GDPR: user can delete account and all data is anonymized
- [ ] **SECR-11**: GDPR: cookie consent banner implemented
- [ ] **SECR-12**: Privacy policy page at /privacy
- [ ] **SECR-13**: Terms of service page at /terms

### Performance & Launch

- [ ] **PERF-01**: All API endpoints respond in <500ms (p95)
- [ ] **PERF-02**: Frontend bundle optimized (code splitting, lazy loading, tree shaking)
- [ ] **PERF-03**: Lighthouse performance score >90 on key pages
- [ ] **PERF-04**: Sentry monitoring active and clean (zero unresolved errors for 48 hours)
- [ ] **PERF-05**: PostHog analytics verified tracking user flows
- [ ] **PERF-06**: E2E smoke test passes: register → onboard → generate → schedule → publish
- [ ] **PERF-07**: Load test passes: 50 concurrent users, <2s response time
- [ ] **PERF-08**: Cross-browser verified: Chrome, Firefox, Safari, Mobile Safari
- [ ] **PERF-09**: Pre-launch checklist complete and signed off

## Future Requirements

Deferred to v4.0 or later. Tracked but not in current roadmap.

### Advanced Media

- **MDIA-F01**: A-roll / B-roll video editing workflow
- **MDIA-F02**: Meme generation from content
- **MDIA-F03**: Voice cloning (user's actual voice) for narration

### Platform Expansion

- **PLAT-F01**: Multi-language content generation (Sarvam AI, regional languages)
- **PLAT-F02**: Platform-native mobile apps (iOS/Android)
- **PLAT-F03**: Platform-specific workspaces per social account
- **PLAT-F04**: Real-time collaboration for agency teams

### Developer Experience

- **DX-F01**: Component library documentation (Storybook)
- **DX-F02**: API documentation (OpenAPI/Swagger auto-generated)

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature                    | Reason                                                  |
| -------------------------- | ------------------------------------------------------- |
| A-roll / B-roll video      | No codebase support, high complexity — deferred to v4.0 |
| Meme generation            | No codebase support — deferred to v4.0                  |
| Multi-language (Sarvam AI) | Regional languages need separate infrastructure — v4.0  |
| Mobile native apps         | Web-first approach — v4.0                               |
| Real-time collaboration    | Not needed for solo creators / small agencies yet       |
| Storybook                  | Nice-to-have, not launch-blocking                       |
| New feature development    | v3.0 is about making existing features work perfectly   |

## Traceability

Which phases cover which requirements.

| Requirement | Phase | Status   |
| ----------- | ----- | -------- |
| BACK-01     | 26    | Complete |
| BACK-02     | 26    | Complete |
| BACK-03     | 26    | Complete |
| BACK-04     | 26    | Complete |
| BACK-05     | 26    | Complete |
| BACK-06     | 26    | Complete |
| BACK-07     | 26    | Complete |
| BACK-08     | 26    | Complete |
| ONBD-01     | 27    | Complete |
| ONBD-02     | 27    | Complete |
| ONBD-03     | 27    | Complete |
| ONBD-04     | 27    | Complete |
| ONBD-05     | 27    | Complete |
| ONBD-06     | 27    | Complete |
| ONBD-07     | 27    | Complete |
| ONBD-08     | 27    | Complete |
| CONT-01     | 28    | Complete |
| CONT-02     | 28    | Complete |
| CONT-03     | 28    | Complete |
| CONT-04     | 28    | Complete |
| CONT-05     | 28    | Complete |
| CONT-06     | 28    | Complete |
| CONT-07     | 28    | Complete |
| CONT-08     | 28    | Complete |
| CONT-09     | 28    | Complete |
| CONT-10     | 28    | Complete |
| CONT-11     | 28    | Complete |
| CONT-12     | 28    | Complete |
| MDIA-01     | 29    | Pending  |
| MDIA-02     | 29    | Complete |
| MDIA-03     | 29    | Pending  |
| MDIA-04     | 29    | Pending  |
| MDIA-05     | 29    | Complete |
| MDIA-06     | 29    | Complete |
| MDIA-07     | 29    | Pending  |
| MDIA-08     | 29    | Pending  |
| PUBL-01     | 30    | Pending  |
| PUBL-02     | 30    | Pending  |
| PUBL-03     | 30    | Pending  |
| PUBL-04     | 30    | Complete |
| PUBL-05     | 30    | Pending  |
| PUBL-06     | 30    | Pending  |
| PUBL-07     | 30    | Pending  |
| SCHD-01     | 31    | Pending  |
| SCHD-02     | 31    | Pending  |
| SCHD-03     | 31    | Pending  |
| SCHD-04     | 31    | Pending  |
| FEND-01     | 32    | Pending  |
| FEND-02     | 32    | Pending  |
| FEND-03     | 32    | Pending  |
| FEND-04     | 32    | Pending  |
| FEND-05     | 32    | Pending  |
| FEND-06     | 32    | Pending  |
| FEND-07     | 32    | Pending  |
| DSGN-01     | 33    | Pending  |
| DSGN-02     | 33    | Pending  |
| DSGN-03     | 33    | Pending  |
| DSGN-04     | 33    | Pending  |
| DSGN-05     | 33    | Pending  |
| SECR-01     | 34    | Pending  |
| SECR-02     | 34    | Pending  |
| SECR-03     | 34    | Pending  |
| SECR-04     | 34    | Pending  |
| SECR-05     | 34    | Pending  |
| SECR-06     | 34    | Pending  |
| SECR-07     | 34    | Pending  |
| SECR-08     | 34    | Pending  |
| SECR-09     | 34    | Pending  |
| SECR-10     | 34    | Pending  |
| SECR-11     | 34    | Pending  |
| SECR-12     | 34    | Pending  |
| SECR-13     | 34    | Pending  |
| PERF-01     | 35    | Pending  |
| PERF-02     | 35    | Pending  |
| PERF-03     | 35    | Pending  |
| PERF-04     | 35    | Pending  |
| PERF-05     | 35    | Pending  |
| PERF-06     | 35    | Pending  |
| PERF-07     | 35    | Pending  |
| PERF-08     | 35    | Pending  |
| PERF-09     | 35    | Pending  |

**Coverage:**

- v3.0 requirements: 81 total (note: original header said 71 but actual count is 81)
- Mapped to phases: 71 / 71
- Unmapped: 0

---

_Requirements defined: 2026-04-12_
_Last updated: 2026-04-12 — traceability populated by roadmapper_
