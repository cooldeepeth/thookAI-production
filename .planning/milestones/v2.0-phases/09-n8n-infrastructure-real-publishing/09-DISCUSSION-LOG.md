# Phase 9: n8n Infrastructure + Real Publishing - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-01
**Phase:** 09-n8n-infrastructure-real-publishing
**Areas discussed:** User deferred to Claude's discretion

---

## Gray Areas Presented

| Option | Description | Selected |
|--------|-------------|----------|
| n8n deployment topology | Where n8n runs, cost/latency tradeoffs | |
| Celery cutover strategy | Migration of 7 beat tasks, dual execution prevention | |
| n8n publishing approach | Built-in nodes vs existing publisher.py | |
| Workflow visibility UX | How users see workflow status | |

**User's choice:** "I think you can start planning for phase 9"
**Notes:** User opted to skip detailed discussion and proceed directly to planning. All gray areas resolved with Claude's discretion based on research findings and codebase analysis.

---

## Claude's Discretion

All four gray areas resolved using research recommendations:
- n8n as separate Docker sidecar with PostgreSQL queue mode
- Hard cutover per job category with idempotency keys
- Reuse existing publisher.py via n8n HTTP callback (don't rebuild)
- Inline workflow status on content cards + toast notifications

## Deferred Ideas

None
