# Agent: Unify Fatigue Shield + Anti-Repetition
Sprint: 3 | Branch: fix/fatigue-shield-unification | PR target: dev
Depends on: Sprint 3 Agent 5 merged (vector store should be wired first)

## Context
There are TWO separate systems doing the same job with no coordination:
1. agents/anti_repetition.py — called by Commander during generation, uses TF-IDF cosine similarity in-memory
2. services/persona_refinement.py get_pattern_fatigue_shield() — exposed via GET /analytics/fatigue-shield
   but NEVER called during content generation

This means the pipeline gets one diversity check that doesn't know about pattern
fatigue, and the fatigue shield runs separately but never influences generation.
Users get duplicate/similar hooks despite the system "knowing" better.

## Files You Will Touch
- backend/agents/pipeline.py             (MODIFY — inject fatigue shield into Thinker step)
- backend/agents/thinker.py             (MODIFY — accept fatigue avoidance context)
- backend/services/persona_refinement.py (MODIFY — minor: ensure async compatibility)
- backend/agents/anti_repetition.py     (MODIFY — add deprecation note, reduce duplication)

## Files You Must Read First (do not modify)
- backend/agents/anti_repetition.py     (read fully — understand current check)
- backend/services/persona_refinement.py (read get_pattern_fatigue_shield() fully)
- backend/agents/pipeline.py            (read fully — find Thinker step)
- backend/agents/thinker.py            (read fully — understand input format)

## Step 1: Call fatigue shield in pipeline.py before the Thinker step
In pipeline.py, find the section where the Thinker agent is called. Insert before it:

```python
from services.persona_refinement import get_pattern_fatigue_shield

# Get fatigue analysis — what patterns is this user overusing?
fatigue_data = {}
try:
    fatigue_data = await get_pattern_fatigue_shield(user_id)
    if fatigue_data.get("fatigue_detected"):
        logger.info(f"Fatigue shield active for {user_id}: {fatigue_data.get('overused_patterns', [])}")
except Exception as e:
    logger.warning(f"Fatigue shield check failed (non-fatal): {e}")
```

Pass `fatigue_data` as a new parameter to the Thinker step.

## Step 2: Update thinker.py to accept and use fatigue context
Add `fatigue_context: dict = None` parameter to the Thinker's main function.
If `fatigue_context` has `fatigue_detected: True`, inject into the Thinker prompt:
CONTENT DIVERSITY CONSTRAINTS (do not ignore these):
The following hook patterns have been overused by this user recently and MUST be avoided:
{overused_patterns}

The following content pillars have been overused:
{overused_pillars}

Prioritise these underused patterns instead:
{underused_patterns}

## Step 3: Deprecate duplicate logic in anti_repetition.py
Add a module-level docstring:
NOTE: The core pattern fatigue detection logic has been consolidated into
services/persona_refinement.py (get_pattern_fatigue_shield). This module
now handles only exact-content deduplication (preventing word-for-word repeats).
Pattern diversity is handled upstream in the pipeline via the fatigue shield.

Remove any logic in anti_repetition.py that duplicates the "overused hook pattern"
detection — keep only the exact content similarity check.

## Definition of Done
- pipeline.py calls get_pattern_fatigue_shield before calling thinker
- thinker.py prompt includes fatigue avoidance when fatigue_detected is True
- No duplicate "overused hook" detection across both files
- PR created to dev with title: "fix: unify fatigue shield and anti-repetition into single pipeline step"