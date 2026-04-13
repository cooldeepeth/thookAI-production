---
phase: 31
slug: smart-scheduling
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-12
---

# Phase 31 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework (backend)** | pytest 8.0.0 + pytest-asyncio 0.23.0 |
| **Framework (frontend)** | Jest + React Testing Library |
| **Quick run command** | `cd backend && pytest tests/test_scheduling*.py tests/test_schedule*.py -x -q` |
| **Full suite command** | `cd backend && pytest tests/ -v` |
| **Estimated runtime** | ~60 seconds |

---

## Sampling Rate

- **After every task commit:** Run quick command
- **After every plan wave:** Run full suite
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | Status |
|---------|------|------|-------------|-----------|-------------------|--------|
| (populated during planning) | | | SCHD-01 | unit | pytest optimal times from persona | ⬜ pending |
| (populated during planning) | | | SCHD-02 | unit | pytest reschedule endpoint | ⬜ pending |
| (populated during planning) | | | SCHD-03 | integration | pytest /schedule/calendar endpoint | ⬜ pending |
| (populated during planning) | | | SCHD-04 | integration | pytest scheduled_posts insert + Celery Beat flow | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] Backend test stubs for scheduled_posts insertion in planner.schedule_content
- [ ] Backend test stubs for optimal times from persona_engines
- [ ] Backend test stubs for calendar endpoint
- [ ] Backend test stubs for reschedule endpoint

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Calendar UI renders scheduled posts | SCHD-03 | Visual UX | Open /dashboard/calendar, verify monthly grid with scheduled posts |
| Scheduled post auto-publishes within 2 min | SCHD-04 | Requires Celery Beat + real time | Schedule post 3 min out, wait, verify publish_results saved |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
