---
phase: 30
slug: social-publishing-end-to-end
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-12
---

# Phase 30 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework (backend)** | pytest 8.0.0 + pytest-asyncio 0.23.0 |
| **Quick run command** | `cd backend && pytest tests/test_publisher*.py tests/test_platforms*.py -x -q` |
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

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| (populated during planning) | | | PUBL-01 | unit | pytest LinkedIn OAuth + publish | TBD | ⬜ pending |
| (populated during planning) | | | PUBL-02 | unit | pytest X OAuth + thread publish | TBD | ⬜ pending |
| (populated during planning) | | | PUBL-03 | unit | pytest Instagram Meta Graph + publish | TBD | ⬜ pending |
| (populated during planning) | | | PUBL-04 | unit | pytest token auto-refresh 24h before expiry | TBD | ⬜ pending |
| (populated during planning) | | | PUBL-05 | unit | pytest publishing status tracked | TBD | ⬜ pending |
| (populated during planning) | | | PUBL-06 | unit | pytest Fernet token encryption verified | TBD | ⬜ pending |
| (populated during planning) | | | PUBL-07 | unit | pytest engagement metrics fetched | TBD | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] Backend test stubs for `_publish_to_platform` decrypt + result dict
- [ ] Backend test stubs for proactive 24h token refresh
- [ ] Backend test stubs for Instagram token renewal branch
- [ ] Backend test stubs for publish_results stored in content_job
- [ ] Backend test stubs for Sentry capture on publish failure

*Existing: publisher.py has full LinkedIn UGC, X v2, Instagram Meta Graph code (just buggy in scheduled flow)*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Real LinkedIn post creation | PUBL-01 | Requires real OAuth + LinkedIn account | Connect LinkedIn, schedule post, verify appears at linkedin.com |
| Real X thread creation | PUBL-02 | Requires X Developer credentials | Connect X, post 3-tweet thread, verify thread visible |
| Real Instagram post via Meta Graph | PUBL-03 | Requires Meta Business app + IG Business account | Connect Instagram, post image+caption, verify on IG profile |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
