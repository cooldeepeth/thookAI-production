# Agent: Post History Import — Bulk Paste for Persona Training
Sprint: 7 | Branch: feat/post-history-import | PR target: dev
Depends on: Sprint 3 Agent 5 merged (vector store must be wired)

## Context
New users can only build their persona through the onboarding interview. There is
no way to paste or upload their existing posts (LinkedIn exports, tweet archives)
to immediately train the persona on real writing history. This significantly weakens
the persona quality for experienced creators joining the platform.

## Files You Will Touch
- backend/routes/onboarding.py          (MODIFY — add import endpoint)
- backend/agents/learning.py            (MODIFY — add bulk import processing)
- frontend/src/pages/Onboarding.jsx     (MODIFY — add import step, check filename)
- frontend/src/pages/Persona.jsx        (MODIFY — add "Import past posts" button)

## Files You Must Read First
- backend/routes/onboarding.py         (understand persona structure)
- backend/agents/learning.py           (understand how content is stored in persona)
- backend/services/vector_store.py     (understand store_content_embedding signature)

## Step 1: Add import endpoint to onboarding.py
```python
POST /api/onboarding/import-history
Body: {
  "posts": [
    {"content": "...", "platform": "linkedin", "date": "2024-01-15"},
    ...
  ],
  "source": "manual_paste" | "linkedin_export" | "twitter_archive"
}
Limits: max 100 posts per import, each post max 5000 chars
```

The endpoint must:
1. Validate post count and content length limits
2. Call `learning.process_bulk_import(user_id, posts)` 
3. Return: `{imported: N, skipped: N, persona_updated: bool}`

## Step 2: Add process_bulk_import to learning.py
```python
async def process_bulk_import(user_id: str, posts: list) -> dict:
    """
    Processes bulk post import for persona training.
    1. Deduplicates against existing content in db (avoid re-importing)
    2. Stores each post as a learning signal in persona_engines.learning_signals
    3. Stores each post in vector store for semantic retrieval
    4. Runs a mini-persona refinement pass using the new data
    5. Returns {imported, skipped, persona_updated}
    """
```

For the mini-persona refinement: after importing all posts, call the same
LLM analysis used in onboarding to identify new voice patterns and update
persona_engines.voice_fingerprint if significant new patterns are found.
Set a flag `last_import_analysis: datetime` to avoid re-analysing on every import.

## Step 3: Add import UI
In the Persona page, add an "Import Past Posts" section with:
1. A textarea for pasting posts (one post per paragraph, or JSON format)
2. Platform selector (LinkedIn / X / Instagram)
3. A simple parser that splits by double-newline to detect post boundaries
4. Preview of detected post count before submitting
5. Submit button that calls the import endpoint and shows result toast

In the Onboarding flow, add an optional "Import your past posts" step after the
interview (step 8 of 7+1) with the same UI, allowing users to seed their persona
immediately after creation.

## Definition of Done
- POST /api/onboarding/import-history accepts and processes up to 100 posts
- process_bulk_import deduplicates and calls vector store
- Persona page has Import Past Posts section
- Onboarding has optional import step
- PR created to dev with title: "feat: post history import for persona training"