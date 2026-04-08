---
phase: 9
slug: n8n-infrastructure-real-publishing
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-01
---

# Phase 9 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.0.0 + pytest-asyncio 0.23.0 |
| **Config file** | `backend/pytest.ini` |
| **Quick run command** | `cd backend && pytest tests/test_n8n_bridge.py -x -q` |
| **Full suite command** | `cd backend && pytest tests/ -x -q` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && pytest tests/test_n8n_bridge.py -x -q`
- **After every plan wave:** Run `cd backend && pytest tests/ -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 09-01-01 | 01 | 1 | N8N-01 | integration | `pytest tests/test_n8n_bridge.py::test_n8n_config` | ❌ W0 | ⬜ pending |
| 09-01-02 | 01 | 1 | N8N-02 | unit | `pytest tests/test_n8n_bridge.py::test_hmac_verification` | ❌ W0 | ⬜ pending |
| 09-02-01 | 02 | 1 | N8N-03 | integration | `pytest tests/test_n8n_bridge.py::test_celery_tasks_migrated` | ❌ W0 | ⬜ pending |
| 09-02-02 | 02 | 1 | N8N-04 | unit | `pytest tests/test_n8n_bridge.py::test_idempotency_key` | ❌ W0 | ⬜ pending |
| 09-03-01 | 03 | 2 | N8N-05 | integration | `pytest tests/test_n8n_bridge.py::test_celery_media_retained` | ❌ W0 | ⬜ pending |
| 09-03-02 | 03 | 2 | N8N-06 | integration | `pytest tests/test_n8n_bridge.py::test_workflow_status_notification` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/test_n8n_bridge.py` — stubs for N8N-01 through N8N-06
- [ ] HMAC verification test fixtures
- [ ] n8n config validation test fixtures

*Existing pytest infrastructure (conftest.py, fixtures) covers shared requirements.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| n8n Docker container starts and connects | N8N-01 | Requires Docker runtime | Run `docker-compose up n8n` and verify logs show "Editor is now accessible" |
| Real social platform publishing via n8n | N8N-03 | Requires live OAuth tokens | Create test scheduled post, verify it appears on LinkedIn/X test accounts |
| Workflow status visible in frontend | N8N-06 | Requires browser verification | Trigger publish workflow, check UI shows status toast/inline indicator |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
