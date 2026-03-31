---
phase: 10
slug: lightrag-knowledge-graph
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-01
---

# Phase 10 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.0.0 + pytest-asyncio 0.23.0 |
| **Config file** | `backend/pytest.ini` |
| **Quick run command** | `cd backend && pytest tests/test_lightrag_service.py -x -q` |
| **Full suite command** | `cd backend && pytest tests/ -x -q` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && pytest tests/test_lightrag_service.py -x -q`
- **After every plan wave:** Run `cd backend && pytest tests/ -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 10-01-01 | 01 | 1 | LRAG-01 | integration | `pytest tests/test_lightrag_service.py::test_config` | W0 | pending |
| 10-01-02 | 01 | 1 | LRAG-02 | unit | `pytest tests/test_lightrag_service.py::test_user_isolation` | W0 | pending |
| 10-01-03 | 01 | 1 | LRAG-04 | unit | `pytest tests/test_lightrag_service.py::test_embedding_lock` | W0 | pending |
| 10-02-01 | 02 | 2 | LRAG-03 | unit | `pytest tests/test_lightrag_service.py::test_entity_extraction` | W0 | pending |
| 10-02-02 | 02 | 2 | LRAG-05 | integration | `pytest tests/test_lightrag_service.py::test_thinker_query` | W0 | pending |
| 10-02-03 | 02 | 2 | LRAG-06 | integration | `pytest tests/test_lightrag_service.py::test_learning_write` | W0 | pending |
| 10-02-04 | 02 | 2 | LRAG-07 | unit | `pytest tests/test_lightrag_service.py::test_routing_contract` | W0 | pending |

*Status: pending / green / red / flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/test_lightrag_service.py` — stubs for LRAG-01 through LRAG-07
- [ ] LightRAG service mock fixtures for httpx calls

*Existing pytest infrastructure (conftest.py, fixtures) covers shared requirements.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| LightRAG Docker container starts and connects to thookai_lightrag DB | LRAG-01 | Requires Docker runtime | Run `docker-compose up lightrag` and verify /health returns OK |
| Multi-hop retrieval surfaces different angles on covered topics | LRAG-05 | Requires populated graph + LLM judgment | Generate content on same topic 3x, verify angle diversity |

---

## Validation Sign-Off

- [ ] All tasks have automated verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
