---
phase: 15-obsidian-vault-integration
plan: 02
subsystem: agents
tags: [obsidian, scout, strategist, vault-enrichment, lazy-import, non-fatal, python, tdd]

# Dependency graph
requires:
  - phase: 15-obsidian-vault-integration
    plan: 01
    provides: "obsidian_service.py with search_vault() and get_recent_notes() — lazy import targets"

provides:
  - "backend/agents/scout.py: run_scout() accepts optional user_id, merges vault findings"
  - "backend/agents/strategist.py: _gather_user_context() includes vault_notes, _build_synthesis_prompt() injects VAULT SIGNALS section"
  - "backend/agents/pipeline.py: run_scout call updated to pass user_id=user_id"
  - "backend/tests/test_obsidian_agents.py: 14 unit tests for Scout + Strategist integration"

affects:
  - "15-03: Frontend opt-in Settings page uses is_configured() and API routes for vault config"
  - "Content generation pipeline: scout step now enriches findings with vault notes when connected"
  - "Nightly strategist run: vault_notes surface as VAULT SIGNALS in recommendation synthesis prompt"

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Lazy import of obsidian_service in agent body — consistent with lightrag_service lazy import in strategist.py"
    - "result = {**result, ...} immutable dict copy before vault enrichment in scout.py"
    - "vault_notes: list = [] default before try block — type-annotated variable even when empty"
    - "VAULT SIGNALS section conditionally injected in synthesis prompt — f-string with vault_block variable"

key-files:
  created:
    - "backend/tests/test_obsidian_agents.py"
  modified:
    - "backend/agents/scout.py"
    - "backend/agents/strategist.py"
    - "backend/agents/pipeline.py"

key-decisions:
  - "run_scout() signature extended with Optional[user_id] defaulting to None — fully backward compatible, all existing callers continue to work"
  - "Vault enrichment uses {**result, ...} spread to create new dict (immutable pattern) before appending vault_sources"
  - "vault_notes: list = [] initialized before try/except so the key is always present in context dict even on exception"
  - "vault_block f-string variable (empty string when no notes) avoids conditional in the main prompt f-string — cleaner than conditional inline"
  - "STRATEGIST_SYSTEM_PROMPT updated to include 'vault' as valid signal_source and vault note guidance in why_now section — enables LLM to cite vault correctly"

patterns-established:
  - "Agent vault enrichment: lazy import + try/except + logger.warning non-fatal pattern — same as LightRAG pattern in strategist._query_content_gaps"
  - "Scout vault section appended after Perplexity/mock results under 'From your research vault:' header — consistent with research notation style"
  - "Strategist context dict always includes vault_notes key — empty list when not configured, populated list when connected"

requirements-completed:
  - OBS-01
  - OBS-02
  - OBS-04

# Metrics
duration: ~10min
completed: 2026-04-01
---

# Phase 15 Plan 02: Obsidian Vault Integration — Scout + Strategist Agents Summary

**Scout vault search merging and Strategist vault signal injection — both non-fatal, 14 tests pass.**

## Performance

- **Duration:** ~10 min
- **Started:** 2026-04-01T11:54:39Z
- **Completed:** 2026-04-01T12:03:09Z
- **Tasks:** 2 (both TDD: RED + GREEN)
- **Files modified:** 4

## Accomplishments

- Modified `backend/agents/scout.py`: `run_scout()` now accepts optional `user_id` parameter; lazily imports `search_vault` and appends vault findings to research output with "From your research vault:" header; `vault_sources` list included in return dict when vault returns results (OBS-01)
- Modified `backend/agents/strategist.py`: `_gather_user_context()` lazily imports `get_recent_notes` and adds `vault_notes` key to returned context dict; `_build_synthesis_prompt()` injects "VAULT SIGNALS" section when vault notes exist; `STRATEGIST_SYSTEM_PROMPT` updated with `vault` as valid `signal_source` and vault-specific `why_now` guidance (OBS-02)
- Modified `backend/agents/pipeline.py`: `run_scout` call updated to pass `user_id=user_id` keyword arg
- Created `backend/tests/test_obsidian_agents.py`: 14 unit tests covering all Scout and Strategist Obsidian integration behaviors (OBS-04 graceful degradation covered comprehensively)
- All 14 tests pass; both agents degrade gracefully to pre-Obsidian behavior when vault not configured

## Task Commits

Each task was committed atomically:

1. **TDD RED: test_obsidian_agents.py (failing tests for Scout + Strategist)** - `dadb566` (test)
2. **TDD GREEN: Scout + Strategist Obsidian vault integration** - `e950be9` (feat)

## Files Created/Modified

- `backend/agents/scout.py` - Added Optional[user_id] param, lazy obsidian_service import, vault findings merge, immutable dict pattern
- `backend/agents/strategist.py` - Added vault_notes to _gather_user_context, VAULT SIGNALS to _build_synthesis_prompt, updated STRATEGIST_SYSTEM_PROMPT
- `backend/agents/pipeline.py` - One-line change: pass user_id=user_id to run_scout call
- `backend/tests/test_obsidian_agents.py` - 14 unit tests: 7 for Scout, 7 for Strategist

## Decisions Made

- **Backward compatible signature**: `user_id: Optional[str] = None` in run_scout — all existing callers (including pipeline before the one-line update) continue to work without vault enrichment
- **Immutable dict update in scout**: `result = {**result, "findings": ...}` creates new dict rather than mutating in place — consistent with coding-style.md immutability rule
- **vault_notes always in context**: Initialized as `vault_notes: list = []` before the try block so `_build_synthesis_prompt` can always call `context.get("vault_notes", [])` safely
- **VAULT SIGNALS injection via vault_block**: Empty string when no notes, formatted block when notes exist — avoids conditional logic inside the f-string prompt

## Deviations from Plan

None — plan executed exactly as written. The merge of dev branch into worktree was required before execution (worktree branch was behind dev by all phase 9-15 commits) but that is infrastructure, not a deviation.

## Known Stubs

None — vault enrichment is fully wired. When `user_id` is provided and Obsidian is configured, real `search_vault()` and `get_recent_notes()` calls flow through to the Obsidian REST API. The underlying `obsidian_service.py` was implemented in Plan 01.

## Self-Check: PASSED

- FOUND: backend/agents/scout.py (modified with vault enrichment)
- FOUND: backend/agents/strategist.py (modified with vault signals)
- FOUND: backend/agents/pipeline.py (updated run_scout call)
- FOUND: backend/tests/test_obsidian_agents.py (14 tests)
- FOUND commit: dadb566 (test RED phase)
- FOUND commit: e950be9 (feat GREEN phase)
- VERIFIED: grep -c "search_vault" backend/agents/scout.py = 2
- VERIFIED: grep -c "get_recent_notes" backend/agents/strategist.py = 2
- VERIFIED: grep "user_id=user_id" backend/agents/pipeline.py shows scout call
- VERIFIED: 14 tests pass

---
*Phase: 15-obsidian-vault-integration*
*Completed: 2026-04-01*
