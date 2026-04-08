---
phase: 11
slug: multi-model-media-orchestration
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-04-01
---

# Phase 11 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework (backend)** | pytest 8.0.0 + pytest-asyncio 0.23.0 |
| **Framework (remotion)** | jest (via remotion-service) |
| **Config file** | `backend/pytest.ini` |
| **Quick run command** | `cd backend && pytest tests/test_media_orchestrator.py -x -q` |
| **Full suite command** | `cd backend && pytest tests/ -x -q` |
| **Estimated runtime** | ~45 seconds |

---

## Sampling Rate

- **After every task commit:** Run quick suite
- **After every plan wave:** Run full suite
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 45 seconds

---

## Verification Strategy

Plans use grep/import/AST verification inline for infrastructure tasks (Waves 1-2).
Comprehensive pytest tests are created in later waves. Remotion service tests use
Jest within the Node.js service directory.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Remotion renders actual image/video output | MEDIA-02 | Requires running Remotion service with Chrome | Start remotion-service, POST /render with test inputProps, verify output file |
| Generated media has correct platform dimensions | MEDIA-14 | Visual inspection | Generate LinkedIn vs Instagram image, verify pixel dimensions match specs |
| Anti-AI-slop detection catches generic output | MEDIA-14 | Requires LLM judgment | QC agent evaluates known-generic image, verify rejection |
| HeyGen talking-head syncs with ElevenLabs audio | MEDIA-09, MEDIA-10 | Requires live API + visual check | Generate 30s talking-head video, verify lip sync and audio alignment |

---

## Validation Sign-Off

- [x] Sampling continuity maintained
- [x] Feedback latency < 45s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
