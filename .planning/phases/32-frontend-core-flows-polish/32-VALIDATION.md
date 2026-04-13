---
phase: 32
slug: frontend-core-flows-polish
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-12
---

# Phase 32 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework (frontend)** | Jest (CRACO) + React Testing Library 14 + MSW v2 |
| **Quick run command** | `cd frontend && npm test -- --watchAll=false --testPathPattern="AuthPage\|DashboardHome\|Settings\|ContentStudio"` |
| **Full suite command** | `cd frontend && npm test -- --watchAll=false` |
| **Estimated runtime** | ~45 seconds |

---

## Sampling Rate

- **After every task commit:** Run quick command
- **After every plan wave:** Run full suite
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 45 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | Status |
|---------|------|------|-------------|-----------|-------------------|--------|
| (populated during planning) | | | FEND-01 | integration | Jest AuthPage tests | ⬜ pending |
| (populated during planning) | | | FEND-02 | integration | Jest DashboardHome tests | ⬜ pending |
| (populated during planning) | | | FEND-03 | integration | Jest ContentStudio tests | ⬜ pending |
| (populated during planning) | | | FEND-04 | integration | Jest Settings tabs tests | ⬜ pending |
| (populated during planning) | | | FEND-05 | integration | Jest loading/error/empty state tests | ⬜ pending |
| (populated during planning) | | | FEND-06 | integration | Jest responsive class tests | ⬜ pending |
| (populated during planning) | | | FEND-07 | integration | Jest keyboard navigation tests | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] Frontend test stubs for AuthPage (loading, error, empty states)
- [ ] Frontend test stubs for DashboardHome (retry button, empty state CTA)
- [ ] Frontend test stubs for Settings (4 tabs, keyboard nav)
- [ ] Frontend test stubs for responsive classes (grep-based)
- [ ] Shadcn tabs component (if missing)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Responsive at 375px mobile | FEND-06 | Visual layout | Resize browser, verify no horizontal scroll |
| Keyboard-only ContentStudio workflow | FEND-07 | Interaction flow | Tab through all elements, verify focus visible |
| Screen reader announces state changes | FEND-07 | Accessibility | VoiceOver/NVDA announces loading, errors, success |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 45s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
