---
phase: 10
slug: lightrag-knowledge-graph
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-04-01
updated: 2026-04-01
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

## Verification Strategy

Plans 01 and 02 (Waves 1-2) use **grep/import/AST-based verification** inline in their task
`<verify>` blocks. These are the authoritative sampling mechanism for infrastructure and
integration tasks. No Wave 0 test stubs are required before Waves 1-2.

Plan 03 (Wave 3) creates all pytest test files. This is intentional: Plans 01/02 create the
production code, Plan 03 creates the comprehensive test suite that validates the full
implementation retroactively. The grep/import checks in Plans 01/02 provide sufficient
confidence for forward progress before Plan 03's tests exist.

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Verify Type | Automated Command | Status |
|---------|------|------|-------------|-------------|-------------------|--------|
| 10-01-01 | 01 | 1 | LRAG-01, LRAG-04 | grep/import | `python3 -c "from config import Settings; s=Settings(); s.lightrag.assert_embedding_config()"` + `grep "ghcr.io/hkuds/lightrag" docker-compose.yml` | pending |
| 10-01-02 | 01 | 1 | LRAG-01, LRAG-04 | grep/import | `python3 -c "from services.lightrag_service import health_check, insert_content, query_knowledge_graph"` + `grep "assert_lightrag_embedding_config" backend/server.py` | pending |
| 10-02-01 | 02 | 2 | LRAG-06, LRAG-07 | grep/AST | `grep -c "from services.lightrag_service import insert_content" backend/agents/learning.py` (expect 2) + `grep "RETRIEVAL ROUTING CONTRACT" backend/agents/pipeline.py` | pending |
| 10-02-02 | 02 | 2 | LRAG-02, LRAG-05 | grep/AST | `grep "from services.lightrag_service import query_knowledge_graph" backend/agents/thinker.py` + `grep "doc_filter_func\|ids.*CREATOR" backend/services/lightrag_service.py` | pending |
| 10-03-01 | 03 | 3 | LRAG-02, LRAG-07 | pytest | `cd backend && pytest tests/test_lightrag_service.py -v` (>= 14 tests, includes test_query_scoped_to_user) | pending |
| 10-03-02 | 03 | 3 | LRAG-03, LRAG-07 | pytest | `cd backend && pytest tests/test_lightrag_integration.py -v` (>= 10 tests, includes test_entity_types_extract_from_real_content) | pending |

*Status: pending / green / red / flaky*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| LightRAG Docker container starts and connects to thookai_lightrag DB | LRAG-01 | Requires Docker runtime | Run `docker-compose up lightrag` and verify /health returns OK |
| Multi-hop retrieval surfaces different angles on covered topics | LRAG-05 | Requires populated graph + LLM judgment | Generate content on same topic 3x, verify angle diversity |
| Cross-user isolation in live sidecar (end-to-end) | LRAG-02 | Requires running LightRAG with real data | Insert content as user_A, query as user_B, verify user_A content does NOT appear. Defer to Phase 16 E2E audit. |

---

## Validation Sign-Off

- [x] All tasks have automated verify (grep/import for Waves 1-2, pytest for Wave 3)
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 3 (Plan 03) creates all pytest tests — no Wave 0 stubs needed
- [x] Feedback latency < 30s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
