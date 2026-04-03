# Phase 12: Strategist Agent - Research

**Researched:** 2026-04-01
**Domain:** Proactive AI recommendation agent — nightly synthesis of LightRAG + analytics + persona memory into ranked recommendation cards
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| STRAT-01 | Strategist Agent (`backend/agents/strategist.py`) — nightly n8n-triggered, synthesizes LightRAG + analytics + persona memory | n8n execute-endpoint pattern (Phase 09) + LightRAG query_knowledge_graph pattern (Phase 10) + LLM pattern (analyst.py, learning.py) documented below |
| STRAT-02 | Recommendation cards written to `db.strategy_recommendations` with `status: "pending_approval"` — never triggers generation directly | New MongoDB collection design documented below; execute-endpoint pattern from n8n_bridge.py is the model |
| STRAT-03 | Every card includes "Why now: [signal]" rationale explaining the recommendation source | Prompt design pattern documented; rationale field required in db schema |
| STRAT-04 | Cadence controls — max 3 new cards per user per day, hard cap enforced | MongoDB count query + guard block pattern documented; must run before LLM call |
| STRAT-05 | Dismissal tracking — 14-day topic suppression on dismiss, dismissal rate monitored per user | Suppression query pattern and dismissal_rate field documented |
| STRAT-06 | If 5 consecutive dismissals, halve generation rate and surface "calibrate preferences" prompt | consecutive_dismissals field + halve_rate flag pattern documented |
| STRAT-07 | Recommendation cards include pre-filled `generate_payload` for one-click content generation | generate_payload schema matches `POST /api/content/generate` request body documented |
</phase_requirements>

---

## Summary

Phase 12 builds `backend/agents/strategist.py` — a nightly agent invoked via n8n's execute-endpoint pattern that synthesizes per-user signal from three sources (LightRAG knowledge graph, MongoDB analytics/persona, content job history) and writes ranked recommendation cards to a new `db.strategy_recommendations` collection. It is a write-only agent: it never calls the content generation pipeline directly.

The architectural foundation is already in place. The n8n execute-endpoint pattern is established in `backend/routes/n8n_bridge.py` (Phase 09). LightRAG querying is established in `backend/services/lightrag_service.py::query_knowledge_graph()` (Phase 10). The LLM invocation pattern is established in `learning.py` and `analyst.py`. The Strategist is the synthesis layer on top of these three components.

The two highest-risk areas for this phase are: (1) the cadence controls and dismissal-tracking data model — these must be correct from day one because retrofitting trust after spam is impossible; and (2) the n8n workflow configuration for nightly triggering — the execute endpoint must be added to `n8n_bridge.py` and `config.py` before the n8n cron workflow is created.

**Primary recommendation:** Model `strategist.py` on `learning.py`'s pattern — async agent with lazy LightRAG import, `asyncio.wait_for` timeout, LLM with `claude-sonnet-4-20250514`, JSON output, non-fatal fallback. Add the execute endpoint in `n8n_bridge.py` following the exact shape of existing execute endpoints. Keep `strategy_recommendations` as a separate, purpose-built collection with the cadence and suppression fields baked in from the start.

---

## Project Constraints (from CLAUDE.md)

- **Branch strategy**: All work branches from `dev`, PRs target `dev`. Never commit to `main` directly.
- **Branch naming**: `fix/short-description`, `feat/short-description`, `infra/short-description`
- **Config pattern**: All settings via `backend/config.py` dataclasses. Never use `os.environ.get()` directly in route/agent/service files. Always `from config import settings`.
- **Database pattern**: Always `from database import db` with Motor async. Never synchronous PyMongo.
- **LLM model**: `claude-sonnet-4-20250514` (Anthropic primary)
- **Billing changes**: Flag for human review
- **Agent pipeline**: After any change to `backend/agents/`, verify full pipeline flow
- **Never delete or modify `backend/db_indexes.py`** without adding indexes inline
- **requirements.txt**: Add any new Python packages
- **n8n Webhook authentication**: HMAC-SHA256 via `X-ThookAI-Signature` header, `hmac.compare_digest` for constant-time comparison

---

## Standard Stack

### Core (all already in requirements.txt)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| motor | 3.3.1 | Async MongoDB — `db.strategy_recommendations` CRUD | Project-standard DB driver |
| anthropic | 0.34.0 | Claude API via `LlmChat` wrapper in `services/llm_client.py` | Primary LLM for synthesis |
| httpx | 0.28.1 | HTTP calls to LightRAG sidecar | Already used in `lightrag_service.py` |
| fastapi | 0.110.1 | New `/api/n8n/execute/run-strategist` endpoint in `n8n_bridge.py` | Project framework |
| pymongo | 4.5.0 (via motor) | `IndexModel`, `ASCENDING`, `DESCENDING` for new indexes | Used throughout `db_indexes.py` |

### No New Packages Required

All dependencies for Phase 12 are already in `backend/requirements.txt`. The Strategist agent uses only the existing `LlmChat`, Motor, and httpx stack.

**No `pip install` step is needed for this phase.**

---

## Architecture Patterns

### Recommended New Files

```
backend/
├── agents/
│   └── strategist.py          # NEW — nightly synthesis agent (STRAT-01..07)
├── routes/
│   └── n8n_bridge.py          # MODIFY — add execute/run-nightly-strategist endpoint
├── config.py                  # MODIFY — add workflow_nightly_strategist to N8nConfig
│                              #          add StrategistConfig dataclass
└── db_indexes.py              # MODIFY — add strategy_recommendations indexes
```

### Pattern 1: Execute Endpoint (n8n_bridge.py)

The nightly Strategist is invoked by n8n via an execute endpoint, exactly like all other migrated Celery tasks. n8n's cron workflow hits `POST /api/n8n/execute/run-nightly-strategist` with HMAC-SHA256 authentication.

The execute endpoint in `n8n_bridge.py` follows this exact structure (established in Phase 09):

```python
# Source: backend/routes/n8n_bridge.py — existing execute endpoint pattern
@router.post("/execute/run-nightly-strategist")
async def execute_run_nightly_strategist(
    request: Request,
    _payload: dict = Depends(_verify_n8n_request),
) -> Dict[str, Any]:
    """
    Run the nightly Strategist agent for all eligible users.
    Called by n8n at 02:00 UTC daily.
    """
    from agents.strategist import run_strategist_for_all_users

    result = await run_strategist_for_all_users()
    return {
        "status": "completed",
        "result": result,
        "executed_at": datetime.now(timezone.utc).isoformat(),
    }
```

**Critical:** The `_verify_n8n_request` dependency handles HMAC verification — do not re-implement it.

Add the workflow ID to `N8nConfig` in `config.py`:

```python
# In N8nConfig dataclass (config.py)
workflow_nightly_strategist: Optional[str] = field(
    default_factory=lambda: os.environ.get('N8N_WORKFLOW_NIGHTLY_STRATEGIST')
)
```

Add to `_get_workflow_map()` in `n8n_bridge.py`:
```python
"nightly-strategist": settings.n8n.workflow_nightly_strategist,
```

### Pattern 2: Strategist Agent Structure (agents/strategist.py)

Model the Strategist on `learning.py`:
- Module-level logger: `logger = logging.getLogger(__name__)`
- `_clean_json()` helper (copy from `learning.py` — identical across all agents)
- Lazy import for `lightrag_service` (non-fatal if LightRAG is down)
- `asyncio.wait_for(...)` with explicit timeout on all LLM calls
- Return `False` / empty result on any exception — never raise from the agent

```python
# Source: backend/agents/learning.py — established LLM call pattern
async def _synthesize_recommendations(
    user_id: str,
    context: dict,
) -> list[dict]:
    """Call Claude to synthesize context into recommendation cards."""
    if not anthropic_available():
        return []

    from services.llm_client import LlmChat, UserMessage

    chat = LlmChat(
        api_key=chat_constructor_key(),
        session_id=f"strategist-{uuid.uuid4().hex[:8]}",
        system_message=STRATEGIST_SYSTEM_PROMPT,
    ).with_model("anthropic", "claude-sonnet-4-20250514")

    try:
        response = await asyncio.wait_for(
            chat.send_message(UserMessage(text=_build_synthesis_prompt(context))),
            timeout=30.0,  # Longer than learning.py's 15s — synthesis is richer
        )
        return json.loads(_clean_json(response))
    except Exception as e:
        logger.error(f"Strategist synthesis failed for {user_id}: {e}")
        return []
```

### Pattern 3: db.strategy_recommendations Collection Schema

This is a new purpose-built collection. Design reflects all 7 requirements in one document shape:

```python
# Source: architecture reasoning from STRAT-01..07 requirements
strategy_recommendation = {
    # Identity
    "recommendation_id": "strat_<uuid12>",   # unique key
    "user_id": "...",
    "status": "pending_approval",             # STRAT-02: always starts here
                                              # transitions: dismissed | approved
    # Content
    "topic": "...",                           # normalized topic string for suppression lookup
    "hook_options": ["...", "..."],           # 2-3 hook variants
    "platform": "linkedin",                  # target platform
    "why_now": "...",                         # STRAT-03: "Why now: [signal]" rationale
    "signal_source": "lightrag|analytics|persona",  # machine-readable signal type

    # Pre-filled generation payload (STRAT-07)
    "generate_payload": {
        "platform": "linkedin",
        "content_type": "post",
        "raw_input": "...",
        "topic": "...",
        "hook_strategy": "...",
    },

    # Cadence and suppression (STRAT-04, STRAT-05)
    "created_at": "<datetime>",
    "expires_at": "<datetime>",              # optional — for time-sensitive signals

    # Dismissal tracking (STRAT-05, STRAT-06)
    "dismissed_at": None,                    # set on dismiss
    "dismissed_reason": None,               # user-provided optional reason
}
```

Per-user cadence state is tracked separately in a lightweight `db.strategist_state` document to avoid per-card MongoDB aggregations at check time:

```python
strategist_state = {
    "user_id": "...",                        # unique key
    "cards_today": 2,                        # STRAT-04: incremented per card written
    "cards_today_date": "2026-04-01",        # reset when date changes
    "consecutive_dismissals": 0,             # STRAT-06: incremented on each dismiss
    "halved_rate": False,                    # STRAT-06: True when 5 consec dismissals
    "suppressed_topics": [                   # STRAT-05: 14-day suppression list
        {
            "topic": "...",
            "suppressed_until": "<datetime>",
        }
    ],
    "last_run_at": "<datetime>",
    "dismissal_rate_7d": 0.0,               # STRAT-05: rolling 7-day dismiss rate
}
```

**Why separate `strategist_state`?** Avoids `$count` + `$group` aggregation pipeline at cadence-check time. A single `find_one` on `user_id` gives the guard data needed before any LLM call. Cadence checks must be synchronous and fast — no aggregation.

### Pattern 4: Cadence Control Flow (STRAT-04)

The cadence guard runs BEFORE any LightRAG query or LLM call:

```python
async def _get_eligible_users() -> list[str]:
    """Return user IDs eligible for strategist run today."""
    # Only users with a persona AND at least 3 approved content jobs
    # (below this threshold, LightRAG has no meaningful signal)
    pipeline = [
        {"$match": {"onboarding_completed": True}},
        {"$project": {"user_id": 1}},
    ]
    users = await db.users.aggregate(pipeline).to_list(length=5000)
    return [u["user_id"] for u in users]


async def _cards_written_today(user_id: str) -> int:
    """Count strategy_recommendations written today for this user."""
    today_start = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    return await db.strategy_recommendations.count_documents({
        "user_id": user_id,
        "created_at": {"$gte": today_start},
    })
```

**Hard cap enforcement** — check before writing each card, not just at the top of the loop:

```python
cards_written = await _cards_written_today(user_id)
if cards_written >= MAX_CARDS_PER_DAY:  # MAX_CARDS_PER_DAY = 3
    logger.info(f"Cadence cap reached for user {user_id} — skipping")
    continue
```

### Pattern 5: Topic Suppression Check (STRAT-05)

```python
async def _is_topic_suppressed(user_id: str, topic: str) -> bool:
    """Check if topic was dismissed within last 14 days."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=14)
    existing = await db.strategy_recommendations.find_one({
        "user_id": user_id,
        "topic": topic,
        "status": "dismissed",
        "dismissed_at": {"$gte": cutoff},
    })
    return existing is not None
```

### Pattern 6: Dismissal Handler and Consecutive Tracking (STRAT-06)

The dismiss endpoint (in `backend/routes/strategy.py`, built in Phase 14) calls a helper that updates consecutive_dismissals:

```python
async def handle_dismissal(user_id: str, recommendation_id: str) -> dict:
    """Handle card dismissal — update suppression and consecutive tracking."""
    now = datetime.now(timezone.utc)

    # Mark card dismissed
    rec = await db.strategy_recommendations.find_one_and_update(
        {"recommendation_id": recommendation_id, "user_id": user_id},
        {"$set": {"status": "dismissed", "dismissed_at": now}},
        return_document=True,
    )
    if not rec:
        return {"error": "not_found"}

    # Suppress topic for 14 days
    topic = rec.get("topic", "")

    # Update strategist_state: increment consecutive_dismissals
    state = await db.strategist_state.find_one({"user_id": user_id}) or {}
    consec = state.get("consecutive_dismissals", 0) + 1
    halved = consec >= 5  # STRAT-06 threshold

    update = {
        "$inc": {"consecutive_dismissals": 1},
        "$set": {"last_dismissal_at": now},
    }
    if halved and not state.get("halved_rate", False):
        update["$set"]["halved_rate"] = True
        # Signal to surface "calibrate preferences" prompt (consumed by Phase 14 dashboard)
        update["$set"]["needs_calibration_prompt"] = True

    await db.strategist_state.update_one(
        {"user_id": user_id},
        update,
        upsert=True,
    )

    return {
        "dismissed": True,
        "topic_suppressed_until": (now + timedelta(days=14)).isoformat(),
        "needs_calibration_prompt": halved and not state.get("halved_rate", False),
    }
```

**Consecutive dismissal reset:** When a card is APPROVED (Phase 14 dashboard), reset `consecutive_dismissals` to 0 and `halved_rate` to False in `strategist_state`.

### Pattern 7: LightRAG Integration — Strategist Queries

The Strategist calls `query_knowledge_graph()` with a different query shape from the Thinker. The Thinker asks "what angles have NOT been used on topic X?" The Strategist asks "what topics SHOULD I write about next, given my content history?":

```python
# Source: backend/services/lightrag_service.py — query_knowledge_graph pattern
async def _query_content_gaps(user_id: str) -> str:
    """Ask LightRAG what topics/angles the user has not covered recently."""
    try:
        from services.lightrag_service import query_knowledge_graph
        return await query_knowledge_graph(
            user_id=user_id,
            topic="content strategy gaps and unexplored topic domains",
            mode="hybrid",
        )
    except Exception as e:
        logger.warning(f"LightRAG gap query failed for {user_id} (non-fatal): {e}")
        return ""
```

**Important:** LightRAG returns empty string when unavailable. The Strategist must degrade gracefully — if LightRAG returns empty, still generate cards using analytics + persona alone.

### Pattern 8: Strategist Prompt Design

The synthesis prompt must produce structured JSON. Based on the established pattern in `analyst.py` and `learning.py`:

```
STRATEGIST_SYSTEM_PROMPT = """You are the ThookAI Strategist Agent.
Your job is to recommend 1-3 high-signal content ideas for a creator,
based on their voice fingerprint, recent content history, and performance signals.

Rules:
- Each recommendation must include a clear "why_now" rationale tied to a specific signal
- Prioritize topic gaps (things they HAVEN'T written about recently)
- Prefer topics with high past engagement when analytics data is available
- Never recommend content that conflicts with their established voice/archetype
- Return ONLY valid JSON — no markdown, no preamble

Return a JSON array of objects with these exact keys:
[{
  "topic": "...",
  "hook_options": ["...", "..."],
  "platform": "linkedin|x|instagram",
  "why_now": "Why now: [specific signal]",
  "signal_source": "lightrag|analytics|persona",
  "generate_payload": {
    "platform": "...",
    "content_type": "post",
    "raw_input": "...",
    "topic": "...",
    "hook_strategy": "..."
  }
}]"""
```

### Pattern 9: MongoDB Indexes for strategy_recommendations

Follows the established `db_indexes.py` pattern:

```python
# Add to INDEXES dict in backend/db_indexes.py
'strategy_recommendations': [
    IndexModel([('recommendation_id', ASCENDING)], unique=True, name='idx_recommendation_id'),
    IndexModel([('user_id', ASCENDING)], name='idx_user_id'),
    IndexModel([('user_id', ASCENDING), ('status', ASCENDING)], name='idx_user_status'),
    IndexModel([('user_id', ASCENDING), ('created_at', DESCENDING)], name='idx_user_created'),
    IndexModel([('user_id', ASCENDING), ('topic', ASCENDING), ('status', ASCENDING)], name='idx_user_topic_status'),
    IndexModel([('created_at', DESCENDING)], name='idx_created_at'),
],
'strategist_state': [
    IndexModel([('user_id', ASCENDING)], unique=True, name='idx_user_id'),
    IndexModel([('last_run_at', DESCENDING)], name='idx_last_run'),
    IndexModel([('halved_rate', ASCENDING)], name='idx_halved_rate'),
],
```

**The compound index on `(user_id, topic, status)` is mandatory** — it makes the 14-day suppression check a single indexed query rather than a full user collection scan.

### Anti-Patterns to Avoid

- **Never call the content generation pipeline from the Strategist.** Write `status: "pending_approval"` cards only. The pipeline is triggered by the user clicking "Approve" in the dashboard (Phase 14). Violating this destroys the human-in-the-loop guarantee.
- **Never generate cards for users with < 3 approved content jobs.** LightRAG has insufficient signal and recommendations will be generic. Check `learning_signals.approved_count >= 3` before running synthesis for a user.
- **Never write more than 3 cards per user per day**, even if synthesis returns more. Truncate the LLM output after 3.
- **Never use `$count` aggregation for cadence enforcement.** Use `count_documents()` — simpler and sufficient for the MAX_CARDS_PER_DAY=3 cap.
- **Never import `lightrag_service` at module top-level in strategist.py.** Use lazy import (same pattern as `learning.py`) so LightRAG being down does not prevent `strategist.py` from being imported.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| HMAC webhook auth for execute endpoint | Custom signature verification | `_verify_n8n_request` dependency from `n8n_bridge.py` | Already built, constant-time, tested |
| LightRAG content gap query | Direct LightRAG HTTP call | `lightrag_service.query_knowledge_graph()` | Handles timeout, auth header, non-fatal fallback |
| LLM synthesis call | Direct Anthropic API call | `LlmChat(...).with_model("anthropic", "claude-sonnet-4-20250514")` | Handles retries, fallback providers |
| Topic suppression timing | Date arithmetic in application code | MongoDB `created_at: {"$gte": cutoff}` query | Consistent with rest of codebase, no timezone bugs |
| Cadence counting | Redis counter | `db.strategy_recommendations.count_documents()` | No new infrastructure; sufficient for max=3 |
| Consecutive dismissal state | Complex event log | Single `strategist_state` document with `consecutive_dismissals` int | Simple, queryable, upsert pattern |

**Key insight:** Everything the Strategist needs already exists. The work is integration — not inventing new infrastructure.

---

## Common Pitfalls

### Pitfall 1: LLM Returns More Than 3 Cards

**What goes wrong:** Claude synthesizes 5-6 strong ideas and returns them all. All get written to the database, violating STRAT-04.
**Why it happens:** The prompt says "1-3 recommendations" but LLM outputs vary. The cadence guard only checks total for the day, not per-batch.
**How to avoid:** After parsing the LLM JSON, slice to `cards[:remaining_slots]` where `remaining_slots = MAX_CARDS_PER_DAY - cards_written_today`. Write the cards one at a time, re-checking the count between each write.
**Warning signs:** `db.strategy_recommendations.count_documents({"user_id": x, "created_at": {$gte: today}})` > 3 for any user.

### Pitfall 2: Race Condition on Cadence Check

**What goes wrong:** Two concurrent Strategist runs for the same user (e.g., n8n retried the cron) each see `cards_today = 2`, both proceed to write, resulting in 4 cards.
**Why it happens:** `count_documents` check + `insert_one` is not atomic.
**How to avoid:** Use a MongoDB upsert with `$inc` and read-after-write pattern:
```python
# Atomic cap guard using strategist_state
result = await db.strategist_state.find_one_and_update(
    {"user_id": user_id, "cards_today_count": {"$lt": 3}},
    {"$inc": {"cards_today_count": 1}},
    return_document=True, upsert=False,
)
if not result:
    continue  # Cap already reached — skip this user
```
**Warning signs:** Per-user card counts occasionally exceeding 3.

### Pitfall 3: LightRAG Returns Empty for New Users

**What goes wrong:** Users with a persona but no approved content get empty LightRAG responses. Strategist falls through to persona-only synthesis and generates generic recommendations that feel wrong.
**Why it happens:** LightRAG has no documents for the user yet — `query_knowledge_graph` returns `""`.
**How to avoid:** Gate on minimum approved content count before any LLM call. Check `learning_signals.approved_count >= 3` from `db.persona_engines`. Log a clear skip reason: `"Skipping strategist for {user_id}: insufficient content history (< 3 approved)"`
**Warning signs:** Generic "thought leadership" cards appearing for users on their second day.

### Pitfall 4: generate_payload Does Not Match Content Route

**What goes wrong:** The `generate_payload` stored in the recommendation card does not exactly match the schema expected by `POST /api/content/generate`. The Phase 14 dashboard one-click approve fires this payload and gets a 422 Unprocessable Entity.
**Why it happens:** The Strategist writes the payload from LLM output without validating it against the actual content route request model.
**How to avoid:** Define a `_build_generate_payload()` function in `strategist.py` that always returns a dict with the exact required fields from `content.py`'s request model. Do not pass raw LLM JSON as the payload — map it through this builder.
**Warning signs:** Dashboard "Approve" button returns 422 in Phase 14.

### Pitfall 5: N8n Workflow ID Not Configured

**What goes wrong:** `N8N_WORKFLOW_NIGHTLY_STRATEGIST` is not set in `.env`. The n8n cron fires, calls `POST /api/n8n/trigger/nightly-strategist`, gets a 404 because workflow ID is None.
**Why it happens:** The trigger endpoint returns 404 for unconfigured workflow IDs (established behavior from Phase 09 decision).
**How to avoid:** Add `N8N_WORKFLOW_NIGHTLY_STRATEGIST` to `.env.example` with a comment. The execute-endpoint pattern does not require this env var (it is called directly by n8n, not triggered via the trigger endpoint), but the trigger endpoint does. Document both paths.
**Warning signs:** 404 on `POST /api/n8n/trigger/nightly-strategist`.

### Pitfall 6: Dismissal Does Not Reset Consecutive Count on Approval

**What goes wrong:** User approves a card after 3 dismissals. On the 5th dismissal (after 2 more), `halved_rate` is set. But the reset on approval was not implemented, so the consecutive chain was not broken by the intervening approval.
**Why it happens:** Phase 12 implements the Strategist and dismissal tracking. The approval path belongs to Phase 14. If Phase 14 does not reset `consecutive_dismissals` on card approval, STRAT-06 fires incorrectly.
**How to avoid:** Explicitly document in Phase 14 planning that `handle_approval()` must `$set: {consecutive_dismissals: 0, halved_rate: false, needs_calibration_prompt: false}` in `strategist_state`.

---

## Code Examples

Verified patterns from existing codebase:

### LLM Call Pattern (from learning.py)

```python
# Source: backend/agents/learning.py lines 81-103
if not anthropic_available():
    return _mock_result()

from services.llm_client import LlmChat, UserMessage

chat = LlmChat(
    api_key=chat_constructor_key(),
    session_id=f"strategist-{uuid.uuid4().hex[:8]}",
    system_message=STRATEGIST_SYSTEM_PROMPT
).with_model("anthropic", "claude-sonnet-4-20250514")

response = await asyncio.wait_for(
    chat.send_message(UserMessage(text=prompt)),
    timeout=30.0,
)
return json.loads(_clean_json(response))
```

### n8n Execute Endpoint Pattern (from n8n_bridge.py)

```python
# Source: backend/routes/n8n_bridge.py lines 287-330 (cleanup-stale-jobs example)
@router.post("/execute/run-nightly-strategist")
async def execute_run_nightly_strategist(
    request: Request,
    _payload: dict = Depends(_verify_n8n_request),
) -> Dict[str, Any]:
    from agents.strategist import run_strategist_for_all_users
    result = await run_strategist_for_all_users()
    return {
        "status": "completed",
        "result": result,
        "executed_at": datetime.now(timezone.utc).isoformat(),
    }
```

### Motor Upsert Pattern (from n8n_bridge.py)

```python
# Source: backend/routes/n8n_bridge.py lines 586-592 (daily stats upsert)
await db.daily_stats.update_one(
    {"date": date_str},
    {"$set": stats},
    upsert=True,
)
```

### Index Definition Pattern (from db_indexes.py)

```python
# Source: backend/db_indexes.py lines 203-210 (media_pipeline_ledger example)
'strategy_recommendations': [
    IndexModel([('recommendation_id', ASCENDING)], unique=True, name='idx_recommendation_id'),
    IndexModel([('user_id', ASCENDING), ('status', ASCENDING)], name='idx_user_status'),
    IndexModel([('user_id', ASCENDING), ('topic', ASCENDING), ('status', ASCENDING)], name='idx_user_topic_status'),
],
```

### LightRAG Lazy Import Pattern (from learning.py)

```python
# Source: backend/agents/learning.py lines 213-227
try:
    from services.lightrag_service import insert_content  # lazy — non-fatal if unavailable
    await insert_content(...)
except Exception as e:
    logger.warning(f"LightRAG operation failed (non-fatal): {e}")
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Analyst agent generates recommendations during dashboard load | Nightly agent pre-generates cards and stores them | Phase 12 (now) | Recommendations are always ready instantly; no generation latency in dashboard UX |
| Generic trending-topics recommendations | LightRAG-grounded gap analysis per user | Phase 12 | Each card reflects the specific user's content history, not just market trends |
| No dismissal tracking | 14-day topic suppression + consecutive dismissal rate | Phase 12 | Prevents recommendation spam from destroying trust |

**Not yet implemented (defer to Phase 14):**
- Strategy routes: `GET /api/strategy`, `POST /api/strategy/:id/approve`, `POST /api/strategy/:id/dismiss`
- Dashboard card feed (Phase 14)
- Calibration preferences prompt UI (Phase 14)

---

## Open Questions

1. **Analytics data availability at Phase 12 execution time**
   - What we know: Phase 13 (analytics polling) is planned but not complete at Phase 12 planning time. `content_jobs.performance_data` may not be populated for most users.
   - What's unclear: Should Phase 12 hard-depend on Phase 13 being complete, or should Strategist degrade gracefully when analytics are absent (using only LightRAG + persona)?
   - Recommendation: Build Strategist to degrade gracefully — if `performance_data` is empty for a user, skip the analytics synthesis and use LightRAG + persona alone. Log which signal source was used in each card's `signal_source` field. This way Phase 12 can execute without Phase 13 being complete. Phase 13 completion upgrades card quality automatically once it runs.

2. **LightRAG per-user signal quality threshold**
   - What we know: LightRAG requires at least 3-5 approved documents before entity relationship extraction produces meaningful output (per Phase 10 research).
   - What's unclear: The exact threshold where LightRAG recommendations become useful versus generic.
   - Recommendation: Use `approved_count >= 3` from `persona_engines.learning_signals` as the minimum gate. Acceptable to start lower since the degradation path (persona-only) is still valuable.

3. **N8n `nightly-strategist` cron schedule**
   - What we know: Existing cron tasks run between midnight and 02:30 UTC (reset-daily-limits=00:00, refresh-monthly-credits=00:05, aggregate-daily-analytics=01:00, cleanup-old-jobs=02:00, cleanup-expired-shares=02:30).
   - What's unclear: Ideal time slot to avoid contending with other n8n workflows.
   - Recommendation: Schedule nightly-strategist at 03:00 UTC — after all cleanup/aggregation tasks complete. This ensures aggregate-daily-analytics has run first, giving Strategist fresh aggregated data.

4. **User notification on new recommendation cards**
   - What we know: `notification_service.create_notification()` exists. WORKFLOW_NOTIFICATION_MAP in `n8n_bridge.py` handles workflow-level notifications.
   - What's unclear: Whether to notify every user whose cards were generated, or only when a particularly high-signal card is created.
   - Recommendation: Add `"nightly-strategist"` to `WORKFLOW_NOTIFICATION_MAP` with title "Your daily content strategy is ready" and body "3 new recommendations waiting for your review". Fire per affected user ID, same as `process-scheduled-posts` pattern.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|-------------|-----------|---------|----------|
| Python 3.11 | All backend code | Checked via runtime.txt | 3.11.x | — |
| MongoDB / Motor | `db.strategy_recommendations`, `db.strategist_state` | Existing project dependency | 3.3.1 | — |
| Anthropic API key | LLM synthesis | Present when ANTHROPIC_API_KEY set | 0.34.0 | Agent returns empty cards; degrade gracefully |
| LightRAG sidecar | Content gap query | Phase 10 sidecar — may not be running in all envs | 1.4.12 | Degrade to analytics + persona only (lazy import pattern) |
| n8n instance | Execute endpoint trigger | Phase 09 — present in production env | stable | Manual test via direct HTTP call with HMAC signature |

**Missing dependencies with no fallback:** None — all critical dependencies are already in the stack.

**Missing dependencies with fallback:** LightRAG sidecar — the lazy import pattern established in `learning.py` and `lightrag_service.py` ensures graceful degradation.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.0.0 + pytest-asyncio 0.23.0 |
| Config file | `backend/pytest.ini` (`asyncio_mode = auto`) |
| Quick run command | `cd backend && pytest tests/test_strategist.py -x` |
| Full suite command | `cd backend && pytest` |

### Phase Requirements to Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| STRAT-01 | Strategist agent runs synthesis and writes cards to DB | unit | `pytest tests/test_strategist.py::TestStrategistAgent -x` | Wave 0 |
| STRAT-02 | Cards always written with `status: "pending_approval"`, never trigger pipeline | unit | `pytest tests/test_strategist.py::TestRecommendationCardSchema -x` | Wave 0 |
| STRAT-03 | Every card has non-empty `why_now` field | unit | `pytest tests/test_strategist.py::TestWhyNowRationale -x` | Wave 0 |
| STRAT-04 | Cadence cap: no more than 3 cards per user per day | unit | `pytest tests/test_strategist.py::TestCadenceControls -x` | Wave 0 |
| STRAT-05 | Topic dismissed within 14 days is not re-recommended | unit | `pytest tests/test_strategist.py::TestDismissalTracking -x` | Wave 0 |
| STRAT-06 | 5 consecutive dismissals triggers halved rate + calibration prompt flag | unit | `pytest tests/test_strategist.py::TestConsecutiveDismissalThreshold -x` | Wave 0 |
| STRAT-07 | `generate_payload` on each card matches content route schema | unit | `pytest tests/test_strategist.py::TestGeneratePayloadSchema -x` | Wave 0 |

### Sampling Rate

- **Per task commit:** `cd backend && pytest tests/test_strategist.py -x`
- **Per wave merge:** `cd backend && pytest`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `backend/tests/test_strategist.py` — covers STRAT-01 through STRAT-07
- [ ] No new fixtures required — existing `conftest.py` pattern with `AsyncMock` + `patch` is sufficient

---

## Sources

### Primary (HIGH confidence)

- `backend/routes/n8n_bridge.py` — execute endpoint pattern, `_verify_n8n_request` dependency, WORKFLOW_NOTIFICATION_MAP
- `backend/agents/learning.py` — agent module pattern: lazy imports, `asyncio.wait_for`, `_clean_json`, LLM invocation with `claude-sonnet-4-20250514`
- `backend/services/lightrag_service.py` — `query_knowledge_graph()` interface, non-fatal fallback pattern
- `backend/config.py` — `N8nConfig` dataclass, `LightRAGConfig`, how to add new workflow ID fields
- `backend/db_indexes.py` — `IndexModel` + `INDEXES` dict pattern for new collections
- `backend/tests/test_n8n_bridge.py` — test pattern for execute endpoints (HMAC mock + AsyncMock)
- `backend/tests/test_lightrag_service.py` — `_FakeLightRAGConfig` pattern to avoid MagicMock assertion collision
- `.planning/research/SUMMARY.md` — Strategist architecture requirements, cadence control rationale
- `.planning/REQUIREMENTS.md` — STRAT-01 through STRAT-07 verbatim requirements

### Secondary (MEDIUM confidence)

- `backend/agents/analyst.py` — analytics data structure, performance_data field names, LLM prompt pattern for content strategy
- `backend/agents/pipeline.py` — RETRIEVAL ROUTING CONTRACT comments (Thinker = LightRAG read, Writer = Pinecone, Learning = both write)
- `backend/services/social_analytics.py` — `performance_data` field structure (engagement, reach, impressions) that Strategist reads
- `backend/services/notification_service.py` — `create_notification()` signature for per-user notification on card creation

### Tertiary (LOW confidence)

- None — all critical claims are verified against existing codebase files.

---

## Metadata

**Confidence breakdown:**

- Standard stack: HIGH — no new dependencies; all existing patterns verified against source files
- Architecture patterns: HIGH — derived directly from Phase 09/10 codebase artifacts, not from external docs
- Collection schema: HIGH — designed to address all 7 requirements with no ambiguity; standard Motor patterns
- Cadence logic: HIGH — straightforward MongoDB count + conditional logic; no novel algorithms
- Pitfalls: HIGH — all identified from direct code inspection and established project decisions

**Research date:** 2026-04-01
**Valid until:** 2026-05-01 (stable — all findings based on internal codebase, not external APIs)
