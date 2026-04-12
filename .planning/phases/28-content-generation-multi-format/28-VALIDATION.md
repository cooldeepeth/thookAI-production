---
phase: 28
slug: content-generation-multi-format
status: approved
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-12
---

# Phase 28 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework (backend)** | pytest 8.0.0 + pytest-asyncio 0.23.0 |
| **Framework (frontend)** | Jest (via CRA/CRACO) + React Testing Library |
| **Quick run command (backend)** | `cd backend && pytest tests/test_writer*.py tests/test_content*.py -x -q` |
| **Quick run command (frontend)** | `cd frontend && npx react-scripts test --watchAll=false --testPathPattern=ContentStudio` |
| **Full suite command** | `cd backend && pytest tests/ -v && cd ../frontend && npx react-scripts test --watchAll=false` |
| **Estimated runtime** | ~90 seconds |

---

## Sampling Rate

- **After every task commit:** Run relevant quick command
- **After every plan wave:** Run full suite
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 90 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| writer-linkedin-post | 02 | 1 | CONT-01 | unit | pytest tests/test_content_phase28.py::test_writer_linkedin_post_format | ✅ exists | ✅ green |
| writer-linkedin-article | 02 | 1 | CONT-02 | unit | pytest tests/test_content_phase28.py::test_writer_linkedin_article_format | ✅ exists | ✅ green |
| writer-linkedin-carousel | 02 | 1 | CONT-03 | unit | pytest tests/test_content_phase28.py::test_writer_linkedin_carousel_format | ✅ exists | ✅ green |
| writer-x-tweet | 02 | 1 | CONT-04 | unit | pytest tests/test_content_phase28.py::test_writer_x_tweet_format | ✅ exists | ✅ green |
| writer-x-thread | 02 | 1 | CONT-05 | unit | pytest tests/test_content_phase28.py::test_writer_x_thread_format | ✅ exists | ✅ green |
| writer-instagram-feed | 02 | 1 | CONT-06 | unit | pytest tests/test_content_phase28.py::test_writer_instagram_feed_caption_format | ✅ exists | ✅ green |
| writer-instagram-reel | 02 | 1 | CONT-07 | unit | pytest tests/test_content_phase28.py::test_writer_instagram_reel_caption_format | ✅ exists | ✅ green |
| writer-instagram-story | 02 | 1 | CONT-08 | unit | pytest tests/test_content_phase28.py::test_writer_instagram_story_sequence_format | ✅ exists | ✅ green |
| writer-format-rules-count | 02 | 1 | CONT-09 | unit | pytest tests/test_content_phase28.py::test_format_rules_has_all_keys | ✅ exists | ✅ green |
| frontend-input-panel | 03 | 2 | CONT-10 | integration | Jest ContentStudio::nine_format_types_total_present | ✅ exists | ✅ green |
| frontend-content-output | 04 | 2 | CONT-11 | integration | Jest ContentStudio::schedule_post_sends_json_body | ✅ exists | ✅ green |
| frontend-agent-pipeline | 04 | 2 | CONT-12 | integration | Jest ContentStudio::agent_pipeline_polls_progress | ✅ exists | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] Backend test stubs for FORMAT_RULES (9 format keys)
- [x] Backend test stubs for word count defaults per content_type
- [x] Frontend test stubs for InputPanel format picker (3-button rows)
- [x] Frontend test stubs for InstagramShell story slide display

*Existing: ContentOutput edit/approve and AgentPipeline progress are already covered.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Generated content quality per platform | CONT-09 | Subjective assessment of platform idiom | Generate same topic on LinkedIn vs X vs Instagram, verify reads differently |
| Persona voice reflected in output | CONT-09 | Subjective | Two users with different personas generate same topic, verify distinct |
| Format selection UI flow | CONT-10 | Visual UX | Click each platform → verify format buttons appear → select → generate |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 90s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-04-12

---

## Phase Completion

**Status:** Complete
**Date:** 2026-04-12
**Backend tests:** pytest tests/test_content_phase28.py — all PASS (import fix applied in Plan 05)
**Frontend tests:** npx react-scripts test ContentStudio — all PASS (102/102 suite tests pass)
**Human verification:** Approved (checkpoint in Plan 05)
