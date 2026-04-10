# Agent Pipeline & Services Audit — Phase 3

**Date:** 2026-04-11
**Files audited:** 39 (21 agents, 18 services)
**OK:** 35 | **Issues:** 4 (false positives corrected — all services have logging)

## Pipeline Flow (verified working in production)

```
Commander (openai/gpt-4o → anthropic fallback)
    ↓
Scout (perplexity/sonar-pro → mock fallback)
    ↓
Thinker (openai/gpt-4o-mini → anthropic fallback)
    ↓
Writer (anthropic/claude-sonnet-4-20250514 → mock fallback)
    ↓
QC (openai/gpt-4o-mini → anthropic fallback → mock)
    ↓
Consigliere (risk assessment — NO mock fallback)
```

All pipeline agents: timeout-protected, error-logged, provider fallback (after Session 2 fixes).

## Issues Found

| File | Issue | Severity | Fix |
|------|-------|----------|-----|
| consigliere.py | No mock fallback on LLM failure | MEDIUM | Pipeline continues without consigliere |
| planner.py | No mock fallback on LLM failure | LOW | Timeout wrapper added in Phase 1 |
| strategist.py | No mock fallback on LLM failure | LOW | Runs via n8n cron, not user-facing |
| llm_client.py | No mock fallback | OK | By design — caller handles fallback |
| llm_keys.py | No timeout/error/logging | OK | Pure utility (key validation) |

## Agent Model Usage

| Agent | Provider | Model | Cost/call |
|-------|----------|-------|-----------|
| Commander | OpenAI | gpt-4o | ~$0.01 |
| Scout | Perplexity | sonar-pro | ~$0.005 |
| Thinker | OpenAI | gpt-4o-mini | ~$0.003 |
| Writer | Anthropic | claude-sonnet-4-20250514 | ~$0.02 |
| QC | OpenAI | gpt-4o-mini | ~$0.003 |
| Consigliere | OpenAI | gpt-4o | ~$0.01 |
| **Total per pipeline** | | | **~$0.05** |

Credit cost: 10 credits per pipeline = $0.50 at $0.05/credit = **86% margin** on text generation.

## Quality Assessment

- All agents have structured prompts with clear instructions
- Writer uses persona voice fingerprint, regional English, anti-repetition, UOM directives
- QC scores: personaMatch (0-10), aiRisk (0-100), platformFit (0-10), repetition check
- Anti-repetition system uses TF-IDF cosine similarity + hook pattern detection
- LLM retry (1 attempt with 1s backoff) added in Session 6
