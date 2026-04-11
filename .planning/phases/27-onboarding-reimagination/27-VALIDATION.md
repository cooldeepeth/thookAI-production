---
phase: 27
slug: onboarding-reimagination
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-12
---

# Phase 27 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework (backend)** | pytest 8.0.0 + pytest-asyncio 0.23.0 |
| **Framework (frontend)** | Jest (via CRA/CRACO) + React Testing Library |
| **Config file (backend)** | backend/pytest.ini |
| **Config file (frontend)** | frontend/craco.config.js (jest key) |
| **Quick run command (backend)** | `cd backend && pytest tests/test_onboarding*.py -x -q --timeout=30` |
| **Quick run command (frontend)** | `cd frontend && npx react-scripts test --watchAll=false --testPathPattern=Onboarding` |
| **Full suite command** | `cd backend && pytest tests/ -v --cov --cov-branch && cd ../frontend && npx react-scripts test --watchAll=false` |
| **Estimated runtime** | ~60 seconds |

---

## Sampling Rate

- **After every task commit:** Run relevant quick command (backend or frontend depending on task)
- **After every plan wave:** Run full suite
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| (populated during planning) | | | ONBD-01 | integration | Jest wizard navigation test | TBD | ⬜ pending |
| (populated during planning) | | | ONBD-02 | integration | Jest MediaRecorder mock test | TBD | ⬜ pending |
| (populated during planning) | | | ONBD-03 | integration | Jest writing style paste + API mock | TBD | ⬜ pending |
| (populated during planning) | | | ONBD-04 | integration | Jest palette selection test | TBD | ⬜ pending |
| (populated during planning) | | | ONBD-05 | unit | pytest persona generation fields | TBD | ⬜ pending |
| (populated during planning) | | | ONBD-06 | unit | pytest persona schema validation | TBD | ⬜ pending |
| (populated during planning) | | | ONBD-07 | integration | Jest localStorage draft test | TBD | ⬜ pending |
| (populated during planning) | | | ONBD-08 | unit | pytest LLM model name verification | ✅ exists | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] Backend test stubs for ONBD-05, ONBD-06 (persona field validation)
- [ ] Frontend test stubs for ONBD-01, ONBD-02, ONBD-03, ONBD-04, ONBD-07 (wizard steps)

*Existing test_onboarding_core.py covers 7-question interview flow — still valid after changes.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Voice recording in browser | ONBD-02 | Requires microphone hardware access | Open onboarding, click record, speak 5s, verify playback |
| Visual palette selection renders correctly | ONBD-04 | Visual appearance check | Open onboarding Step 3, verify 6 palettes render with distinct colors |
| Browser close + resume | ONBD-07 | Browser lifecycle event | Complete Step 1, close tab, reopen, verify Step 1 answers preserved |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
