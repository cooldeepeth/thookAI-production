# Agent: Fix Model Name + Onboarding Pipeline
Sprint: 1 | Branch: fix/model-name-onboarding | PR target: dev
Depends on: nothing (first fix)

## Context
The onboarding route uses the wrong Anthropic model string, causing every user's
persona generation to silently fall back to a mock generator. This destroys the
core product value — every user gets a generic persona instead of their real voice.

## Files You Will Touch
- backend/routes/onboarding.py

## Files You Must Read First (do not modify)
- backend/services/llm_client.py       (understand LlmChat interface)
- backend/services/llm_keys.py         (understand anthropic_available() helper)
- backend/agents/pipeline.py           (understand how persona flows downstream)

## Exact Bug to Fix
Search onboarding.py for every occurrence of:
  "claude-4-sonnet-20250514"
Replace ALL occurrences with:
  "claude-sonnet-4-20250514"

There are at minimum 2 occurrences — one in the persona generation call, one in
the post analysis call. Find ALL occurrences with a grep before editing.

## Additional Improvements (do these in the same PR)
1. Add a `try/except` around the Anthropic API call that catches `anthropic.APIError`
   and logs the full error including the model name attempted, then raises HTTP 500
   with a descriptive message. Currently errors are silently swallowed.
2. Add a startup log line in the lifespan function in server.py that prints:
   `LLM model configured: claude-sonnet-4-20250514` when ANTHROPIC_API_KEY is set.
3. In onboarding.py, if the LLM call fails AND we fall back to mock persona,
   log a WARNING with: `[ONBOARDING FALLBACK] Using mock persona - LLM unavailable`
   so the owner can see it happening in logs.

## Definition of Done
- `grep -n "claude-4-sonnet" backend/routes/onboarding.py` returns zero results
- `grep -n "claude-sonnet-4-20250514" backend/routes/onboarding.py` returns 2+ results
- PR created to dev with title: "fix: correct Claude model name in onboarding"