---
phase: 26
slug: backend-endpoint-hardening
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-12
---

# Phase 26 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.0.0 + pytest-asyncio 0.23.0 |
| **Config file** | backend/pytest.ini |
| **Quick run command** | `cd backend && pytest tests/ -x -q --timeout=30` |
| **Full suite command** | `cd backend && pytest tests/ -v --cov --cov-branch` |
| **Estimated runtime** | ~45 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && pytest tests/ -x -q --timeout=30`
- **After every plan wave:** Run `cd backend && pytest tests/ -v --cov --cov-branch`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 45 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| (populated during planning) | | | BACK-01 | integration | `curl` against production endpoints | N/A | ⬜ pending |
| (populated during planning) | | | BACK-02 | unit | `pytest tests/` validation tests | ❌ W0 | ⬜ pending |
| (populated during planning) | | | BACK-03 | unit | `pytest tests/` error format tests | ❌ W0 | ⬜ pending |
| (populated during planning) | | | BACK-04 | unit | `pytest tests/` auth guard tests | ✅ exists | ⬜ pending |
| (populated during planning) | | | BACK-05 | unit | `pytest tests/` malformed body tests | ❌ W0 | ⬜ pending |
| (populated during planning) | | | BACK-06 | unit | `pytest tests/` credit refund tests | ✅ exists | ⬜ pending |
| (populated during planning) | | | BACK-07 | unit | `pytest tests/` rate limit tests | ✅ exists | ⬜ pending |
| (populated during planning) | | | BACK-08 | manual | Review BACKEND-API-AUDIT.md | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_validation_hardening.py` — stubs for BACK-02, BACK-03, BACK-05 (input validation + error format)
- [ ] `tests/test_credit_refund_media.py` — stubs for BACK-06 (media endpoint credit refund)

*Existing infrastructure covers auth guard (BACK-04) and rate limiting (BACK-07) tests from v2.1.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| All endpoints tested via curl against production | BACK-01 | Requires live production deployment | curl each endpoint with valid/invalid auth, check response |
| BACKEND-API-AUDIT.md completeness | BACK-08 | Document review | Verify all 26 route files and ~209 endpoints listed |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 45s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
