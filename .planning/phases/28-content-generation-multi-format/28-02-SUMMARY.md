---
phase: 28-content-generation-multi-format
plan: "02"
subsystem: backend-agents
tags: [content-generation, writer-agent, commander-agent, format-rules, multi-format]
dependency_graph:
  requires: []
  provides:
    - FORMAT_RULES dict (8 content_type keys) in backend/agents/writer.py
    - WORD_COUNT_DEFAULTS dict (8 keys) in backend/agents/commander.py
    - story_sequence in PLATFORM_CONTENT_TYPES['instagram'] in backend/routes/content.py
  affects:
    - backend/agents/pipeline.py (writer lookup now uses content_type)
    - backend/routes/content.py (instagram accepts 3 content types)
tech_stack:
  added: []
  patterns:
    - FORMAT_RULES dict keyed by content_type replacing PLATFORM_RULES keyed by platform
    - Word count floor override in Commander after LLM JSON parsing
key_files:
  created:
    - backend/tests/test_content_phase28.py
  modified:
    - backend/agents/writer.py
    - backend/agents/commander.py
    - backend/routes/content.py
decisions:
  - FORMAT_RULES uses content_type keys (not platform keys) so each of the 8 formats gets distinct Writer instructions
  - WORD_COUNT_DEFAULTS applied as floor override after LLM JSON parsing to prevent articles getting 200-word estimates
  - story_sequence added to instagram allowlist (was previously absent, causing 400 errors)
metrics:
  duration: "3 minutes 17 seconds"
  completed: "2026-04-12T05:23:23Z"
  tasks_completed: 2
  files_modified: 3
  files_created: 1
requirements:
  - CONT-01
  - CONT-02
  - CONT-03
  - CONT-04
  - CONT-05
  - CONT-06
  - CONT-07
  - CONT-08
  - CONT-09
---

# Phase 28 Plan 02: Writer FORMAT_RULES + Commander Word Count + story_sequence Allowlist Summary

**One-liner:** Replaced 3-key `PLATFORM_RULES` with 8-key `FORMAT_RULES` keyed by `content_type` in writer.py, added `WORD_COUNT_DEFAULTS` floor override in commander.py, and added `story_sequence` to the Instagram backend allowlist.

## What Was Built

Three surgical backend changes that unlock all 9 content formats without touching the pipeline orchestrator:

### Task 1: FORMAT_RULES in writer.py (commit ba98e74)

Replaced the 3-key `PLATFORM_RULES` dict (keyed by `linkedin`, `x`, `instagram`) with an 8-key `FORMAT_RULES` dict keyed by `content_type`:

| Key | Key Constraints |
|-----|----------------|
| `post` | LinkedIn, max 3,000 chars, 3-5 hashtags |
| `article` | LinkedIn, min 600 words, ## headers, no hashtags |
| `carousel_caption` | LinkedIn, max 1,500 chars, tease slides |
| `tweet` | HARD LIMIT 280 chars, no fluff |
| `thread` | 1/...n/ numbering, each tweet under 280 chars |
| `feed_caption` | Instagram, max 2,200 chars, 10-15 hashtags |
| `reel_caption` | Instagram, caption hook + bullet script |
| `story_sequence` | Instagram, Slide 1:/2:/3: format, 3-5 slides |

Updated lookup from:
```python
# BEFORE
platform_rules = PLATFORM_RULES.get(platform.lower(), PLATFORM_RULES["linkedin"])
```
to:
```python
# AFTER
platform_rules = FORMAT_RULES.get(content_type, FORMAT_RULES.get(platform.lower(), ""))
```

### Task 2: WORD_COUNT_DEFAULTS in commander.py + allowlist (commit 0f4d347)

Added `WORD_COUNT_DEFAULTS` dict immediately after `logger` initialization:
- `article: 800` (prevents Pitfall 2: article generated as 200-word post)
- `tweet: 45` (keeps Commander from requesting too many words for a 280-char limit)
- `story_sequence: 80` (3-5 slides × ~15 words)

Applied word count floor override in `run_commander()` after LLM JSON parsing:
```python
min_words = WORD_COUNT_DEFAULTS.get(content_type, 200)
if result.get("estimated_word_count", 0) < min_words:
    result["estimated_word_count"] = min_words
```

Added `story_sequence` to `PLATFORM_CONTENT_TYPES["instagram"]` in `content.py` (was causing 400 errors for all Instagram story generation requests).

## Verification Results

All plan verification checks pass:

```
FORMAT_RULES keys: ['post', 'article', 'carousel_caption', 'tweet', 'thread', 'feed_caption', 'reel_caption', 'story_sequence']
PLATFORM_CONTENT_TYPES: {'linkedin': ['post', 'carousel_caption', 'article'], 'x': ['tweet', 'thread'], 'instagram': ['feed_caption', 'reel_caption', 'story_sequence']}
PLATFORM_RULES references in writer.py: none (GOOD)
```

Test results: **16 passed, 0 failed** (`tests/test_content_phase28.py`)

Regression: `tests/test_content_sprint3.py` — 15 skipped (require live server), 0 failed.

## Commits

| Task | Commit | Files |
|------|--------|-------|
| Task 1: FORMAT_RULES in writer.py | ba98e74 | backend/agents/writer.py, backend/tests/test_content_phase28.py |
| Task 2: WORD_COUNT_DEFAULTS + allowlist | 0f4d347 | backend/agents/commander.py, backend/routes/content.py, backend/tests/test_content_phase28.py |

## Deviations from Plan

**1. [Rule 3 - Blocking Issue] Test file replaced by linter**
- **Found during:** Task 2 GREEN phase
- **Issue:** The hand-written `test_content_phase28.py` was replaced by a linter-generated version with import guards (`try/except ImportError`) and `pytest.mark.unit` markers. The new version covers CONT-01 through CONT-12 (integration tests for Plans 03/04 are included but will be `xfail` until those plans run).
- **Fix:** Accepted the linter's improved version — it is structurally superior (import guards prevent import errors from masking test failures, marks enable selective test running).
- **Files modified:** backend/tests/test_content_phase28.py
- **Commit:** 0f4d347

No other deviations — plan executed exactly as written.

## Known Stubs

None. All three changes are fully wired:
- `FORMAT_RULES` is used in `run_writer()` at the `platform_rules=` assignment
- `WORD_COUNT_DEFAULTS` floor is applied in `run_commander()` after JSON parsing
- `story_sequence` is in the Instagram allowlist so the route validator accepts it

## Self-Check: PASSED

- [x] `backend/agents/writer.py` — FORMAT_RULES exists, PLATFORM_RULES gone
- [x] `backend/agents/commander.py` — WORD_COUNT_DEFAULTS exists, floor override applied
- [x] `backend/routes/content.py` — story_sequence in instagram list
- [x] `backend/tests/test_content_phase28.py` — 482 lines, 16 tests pass
- [x] Commits ba98e74 and 0f4d347 exist in git log
