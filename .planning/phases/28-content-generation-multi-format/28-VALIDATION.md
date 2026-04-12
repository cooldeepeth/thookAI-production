---
phase: 28
slug: content-generation-multi-format
status: draft
nyquist_compliant: false
wave_0_complete: false
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
| (populated during planning) | | | CONT-01 | unit | pytest writer LinkedIn post format | TBD | ⬜ pending |
| (populated during planning) | | | CONT-02 | unit | pytest writer LinkedIn article format | TBD | ⬜ pending |
| (populated during planning) | | | CONT-03 | unit | pytest writer LinkedIn carousel format | TBD | ⬜ pending |
| (populated during planning) | | | CONT-04 | unit | pytest writer X tweet format | TBD | ⬜ pending |
| (populated during planning) | | | CONT-05 | unit | pytest writer X thread format | TBD | ⬜ pending |
| (populated during planning) | | | CONT-06 | unit | pytest writer Instagram feed_caption format | TBD | ⬜ pending |
| (populated during planning) | | | CONT-07 | unit | pytest writer Instagram reel_caption format | TBD | ⬜ pending |
| (populated during planning) | | | CONT-08 | unit | pytest writer Instagram story_sequence format (NEW) | TBD | ⬜ pending |
| (populated during planning) | | | CONT-09 | unit | pytest FORMAT_RULES dict has 9 keys | TBD | ⬜ pending |
| (populated during planning) | | | CONT-10 | integration | Jest InputPanel format picker | TBD | ⬜ pending |
| (populated during planning) | | | CONT-11 | integration | Jest ContentOutput edit/approve/schedule | ✅ exists | ⬜ pending |
| (populated during planning) | | | CONT-12 | integration | Jest AgentPipeline progress polling | ✅ exists | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] Backend test stubs for FORMAT_RULES (9 format keys)
- [ ] Backend test stubs for word count defaults per content_type
- [ ] Frontend test stubs for InputPanel format picker (3-button rows)
- [ ] Frontend test stubs for InstagramShell story slide display

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

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 90s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
