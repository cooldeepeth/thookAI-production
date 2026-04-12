---
phase: 29
slug: media-generation-pipeline
status: approved
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-12
approved: 2026-04-12
---

# Phase 29 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework (backend)** | pytest 8.0.0 + pytest-asyncio 0.23.0 |
| **Framework (frontend)** | Jest (via CRA/CRACO) + React Testing Library |
| **Quick run command (backend)** | `cd backend && pytest tests/test_media*.py tests/test_content_phase29*.py -x -q` |
| **Quick run command (frontend)** | `cd frontend && npm test -- --testPathPattern=MediaPanel` |
| **Full suite command** | `cd backend && pytest tests/ -v && cd ../frontend && npm test -- --watchAll=false` |
| **Estimated runtime** | ~120 seconds |

---

## Sampling Rate

- **After every task commit:** Run relevant quick command
- **After every plan wave:** Run full suite
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 120 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| (populated during planning) | | | MDIA-01 | unit | pytest auto-image generation | TBD | ⬜ pending |
| (populated during planning) | | | MDIA-02 | unit | pytest carousel via Remotion | TBD | ⬜ pending |
| (populated during planning) | | | MDIA-03 | unit | pytest video generation | TBD | ⬜ pending |
| (populated during planning) | | | MDIA-04 | unit | pytest voice narration + R2 upload | TBD | ⬜ pending |
| (populated during planning) | | | MDIA-05 | unit | pytest Remotion render to file | TBD | ⬜ pending |
| (populated during planning) | | | MDIA-06 | unit | pytest media attached to job + downloadable | TBD | ⬜ pending |
| (populated during planning) | | | MDIA-07 | integration | Jest MediaPanel display + polling | TBD | ⬜ pending |
| (populated during planning) | | | MDIA-08 | integration | pytest R2 presigned URL flow | TBD | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] Backend test stubs for media task fixes (CreativeProvidersService bug)
- [ ] Backend test stubs for voice → R2 upload
- [ ] Backend test stubs for Remotion carousel rendering
- [ ] Frontend test stubs for MediaPanel async polling

*Existing: media_storage R2 client tests exist. media_orchestrator tests exist for routing.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Image quality and dimensions | MDIA-01 | Visual + provider availability | Generate image, verify dimensions match platform (1200x627 LinkedIn, 1:1 Instagram) |
| Carousel renders correctly | MDIA-02 | Remotion render output | Generate LinkedIn carousel, download MP4, verify 3+ slides with consistent branding |
| Video plays back | MDIA-03 | Video quality + provider | Generate video, play in browser, verify smooth playback |
| R2 presigned upload (no CORS) | MDIA-08 | Browser CORS to Cloudflare R2 | Open MediaUploader, select image, verify upload succeeds without CORS error |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 120s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
