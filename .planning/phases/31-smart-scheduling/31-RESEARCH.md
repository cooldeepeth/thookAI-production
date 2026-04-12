# Phase 31: Smart Scheduling - Research

**Researched:** 2026-04-12
**Domain:** Celery Beat scheduling, AI-optimal posting times, React calendar UI, MongoDB scheduled_posts collection
**Confidence:** HIGH (all findings based on direct codebase analysis)

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SCHD-01 | AI suggests optimal posting times per platform based on engagement patterns | `agents/planner.py::get_optimal_posting_times` exists. `services/persona_refinement.py::calculate_optimal_posting_times` persists results to `persona_engines.optimal_posting_times`. Need to wire them together. |
| SCHD-02 | User can approve/modify suggested schedule | `ContentCalendar.jsx` renders AI suggestions panel. `POST /api/dashboard/schedule/content` exists. Gap: no per-slot "approve" or date/time picker for rescheduling. |
| SCHD-03 | Calendar view shows all scheduled posts across platforms | `ContentCalendar.jsx` already exists and is routed at `/dashboard/calendar`. Gap: fetches only `status=scheduled` content_jobs (not `scheduled_posts` collection). |
| SCHD-04 | Scheduled posts publish automatically at scheduled time via Celery Beat | `celeryconfig.py` beat_schedule has `process-scheduled-posts` running every 5 min via `tasks.scheduled_tasks.process_scheduled_posts`. Gap: `planner.py::schedule_content` writes to `content_jobs` only; Beat task reads from `scheduled_posts` collection — bridging insert missing. |
</phase_requirements>

## Summary

Phase 31 sits on a nearly complete foundation. Three major subsystems already exist: (1) `agents/planner.py` computes optimal times using PLATFORM_PEAKS heuristics + UOM burnout adjustment, (2) `ContentCalendar.jsx` renders a monthly grid, a date sidebar, and an AI suggestions panel, and (3) Celery Beat runs `process_scheduled_posts` every 5 minutes. The primary gap is an architectural disconnect: `planner.py::schedule_content` writes schedule data to `content_jobs` (status="scheduled"), but the Beat publisher reads from the `scheduled_posts` collection. Nothing ever inserts into `scheduled_posts` via the current approval flow.

A secondary gap is the AI signal chain: `services/persona_refinement.py::calculate_optimal_posting_times` computes evidence-based optimal times from real engagement data and persists them to `persona_engines.optimal_posting_times`, but `agents/planner.py::get_optimal_posting_times` ignores that stored field and uses only static `PLATFORM_PEAKS` heuristics. Wiring the planner to prefer stored optimal times when available (falling back to heuristics) fulfills SCHD-01 as a genuine AI-based suggestion.

For the calendar (SCHD-03), the UI already works but only queries `content_jobs` via `/api/dashboard/schedule/upcoming`. This endpoint must be supplemented or replaced with an endpoint that queries `scheduled_posts` as well (or both), since scheduled_posts is the authoritative state for the Beat publisher.

**Primary recommendation:** Fix the scheduling pipeline by (1) inserting into `scheduled_posts` when `schedule_content` is called, (2) wiring `get_optimal_posting_times` to read from `persona_engines.optimal_posting_times` first, (3) adding a reschedule endpoint that revokes/re-creates the `scheduled_posts` record, and (4) expanding the calendar data source to include published posts.

## Project Constraints (from CLAUDE.md)

### Locked Decisions
- **Config pattern**: All settings via `backend/config.py` dataclasses. Never use `os.environ.get()` directly.
- **Database pattern**: Always `from database import db` with Motor async. Never synchronous PyMongo.
- **LLM model**: `claude-sonnet-4-20250514` (Anthropic primary). OpenAI (`gpt-4o-mini`) acceptable for lightweight planning reasoning (planner already uses gpt-4o-mini).
- **Branch strategy**: All work branches from `dev`, PRs target `dev`. Never commit to `main` directly.
- **Billing changes**: Flag for human review — no auto-merge on billing code.
- **Agent pipeline**: After any change to `backend/agents/`, verify full pipeline flow.
- **No new Python packages** without adding to `backend/requirements.txt`.
- **No direct `os.environ.get()`** in route/agent/service files.

### Claude's Discretion
- How to expose the reschedule capability in the UI (modal, inline picker, etc.)
- Whether the calendar endpoint reads from `content_jobs` + `scheduled_posts` via join or a dedicated unified query
- Whether to add a compound MongoDB index on `(user_id, scheduled_at)` for calendar range queries

### Deferred Ideas (OUT OF SCOPE)
- Real social analytics ingestion for engagement-based optimal times (analytics polling exists but simulated; the scoring in planner.py should consume `persona_engines.optimal_posting_times` if populated, not call real platform APIs)
- Timezone-aware optimal times (current implementation works in UTC only — keep as-is for v3.0)
- Push notifications when a scheduled post publishes (notification_service scaffolded but not required for this phase)

---

## Standard Stack

### Core (already in use — no new installs needed)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Celery | 5.3.0 | Beat scheduler + task execution | Already configured; `process_scheduled_posts` runs every 5 min |
| Motor (via MongoDB) | 3.3.1 | Async DB driver for `scheduled_posts` and `content_jobs` | Project standard |
| FastAPI | 0.110.1 | Route layer for schedule endpoints | Project standard |
| React | 18.3.1 | Frontend calendar component | Already shipping `ContentCalendar.jsx` |
| Framer Motion | 12.38.0 | Animations for suggestion cards | Already imported in ContentCalendar |
| shadcn/ui | New York | Card, Button, Badge, Dialog primitives | Already imported in ContentCalendar |
| Lucide React | 0.507.0 | Icons (CalendarIcon, Clock, etc.) | Already used in ContentCalendar |

### No New Dependencies Required
The entire phase can be implemented without adding any new Python packages or npm packages. The existing stack covers all needs.

**Installation:** None required.

## Architecture Patterns

### Recommended Project Structure — What Changes

```
backend/
├── agents/
│   └── planner.py         # MODIFY: wire optimal_posting_times from persona_engines
├── routes/
│   └── dashboard.py       # MODIFY: add /schedule/calendar endpoint + /schedule/{id}/reschedule
├── tasks/
│   └── scheduled_tasks.py # VERIFY: process_scheduled_posts reads scheduled_posts correctly

frontend/
└── src/pages/Dashboard/
    └── ContentCalendar.jsx  # MODIFY: add reschedule UI + fix data source to include all statuses
```

### Pattern 1: Scheduling Insert Bridge (Critical Gap Fix)

**What:** When `planner.schedule_content` is called, it must write into BOTH `content_jobs` (status="scheduled") AND `scheduled_posts` (status="scheduled"). Currently it only writes to `content_jobs`. The Beat task only reads `scheduled_posts`.

**When to use:** Every time a user schedules a post.

**Canonical `scheduled_posts` document shape** (verified from `scheduled_tasks.py` and `db_indexes.py`):
```python
{
    "schedule_id": f"sch_{uuid.uuid4().hex[:12]}",
    "user_id": user_id,
    "job_id": job_id,
    "platform": platform,          # one document per platform per job
    "final_content": final_content,
    "scheduled_at": scheduled_at,  # datetime with timezone.utc
    "status": "scheduled",         # Beat task matches "pending" or "scheduled"
    "media_assets": media_assets,  # list or None
    "created_at": datetime.now(timezone.utc),
}
```

Note: The Beat task (`scheduled_tasks.py::_process_scheduled_posts`) matches `status IN ["pending", "scheduled"]`. The content_tasks variant matches only `"scheduled"`. Use `"scheduled"` for new inserts to be compatible with both.

**Reschedule pattern:** Cancel = update `scheduled_posts.status = "cancelled"` AND update `content_jobs.status = "approved"` (unschedule). Reschedule = insert new `scheduled_posts` doc with new `schedule_id` + new `scheduled_at`. Do NOT reuse the old schedule_id.

### Pattern 2: AI Optimal Times — Prefer Stored Data, Fall Back to Heuristics

**What:** `calculate_optimal_posting_times` (persona_refinement.py) computes real engagement-based times from published post performance data and stores them in `persona_engines.optimal_posting_times`. `get_optimal_posting_times` (planner.py) ignores this field and uses static `PLATFORM_PEAKS`.

**Fix:**
```python
async def get_optimal_posting_times(user_id, platform, content_type=None, num_suggestions=3):
    from database import db
    
    persona = await db.persona_engines.find_one({"user_id": user_id})
    uom = persona.get("uom", {}) if persona else {}
    burnout_risk = uom.get("burnout_risk", "low")
    
    # SCHD-01: Prefer AI-calculated times from engagement data
    stored_times = (persona or {}).get("optimal_posting_times", {})
    platform_stored = stored_times.get(platform, [])
    
    if platform_stored:
        # Use stored times — they're engagement-evidence-based
        # Convert stored slot format to suggestion format
        # stored format from persona_refinement: [{day_of_week, hour, avg_engagement_rate, post_count}]
        suggestions = _convert_stored_to_suggestions(platform_stored, num_suggestions)
    else:
        # Fall back to PLATFORM_PEAKS heuristics (new users, no data)
        suggestions = _compute_heuristic_suggestions(platform, num_suggestions)
    
    # Apply burnout cap on count
    # ... existing logic ...
```

**Stored format** (from `calculate_optimal_posting_times` in persona_refinement.py):
```python
# optimal_posting_times = {
#   "linkedin": [
#     {"day_of_week": 1, "hour": 9, "avg_engagement_rate": 0.045, "post_count": 5},
#     ...
#   ]
# }
```

### Pattern 3: Calendar Data — Unified Query Across Both Collections

**What:** The calendar needs to show scheduled AND published posts. Currently `GET /api/dashboard/schedule/upcoming` only queries `content_jobs` with `status="scheduled"`. The Beat publisher stores results in `scheduled_posts`. A reschedule flow must reflect updated times.

**Recommended new endpoint:** `GET /api/dashboard/schedule/calendar?year=YYYY&month=MM`

```python
@router.get("/schedule/calendar")
async def get_calendar_data(
    year: int = Query(...),
    month: int = Query(...),
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Return all scheduled + published posts for the given month."""
    user_id = current_user["user_id"]
    start = datetime(year, month, 1, tzinfo=timezone.utc)
    end = datetime(year, month + 1, 1, tzinfo=timezone.utc) if month < 12 else datetime(year + 1, 1, 1, tzinfo=timezone.utc)
    
    posts = await db.scheduled_posts.find({
        "user_id": user_id,
        "scheduled_at": {"$gte": start, "$lt": end},
        "status": {"$in": ["scheduled", "pending", "published", "failed"]}
    }, {"_id": 0, "schedule_id": 1, "job_id": 1, "platform": 1, "scheduled_at": 1, "status": 1}).to_list(200)
    
    # Enrich with content preview from content_jobs (one lookup per unique job_id)
    ...
    return {"posts": posts, "year": year, "month": month}
```

### Pattern 4: Reschedule Endpoint

**What:** SCHD-04 success criterion requires "Rescheduling a post cancels old Celery task and creates new one." Since tasks are driven by Beat (not individual task IDs), "cancelling" means marking the old `scheduled_posts` record and inserting a new one.

```python
@router.patch("/schedule/{schedule_id}/reschedule")
async def reschedule_post(
    schedule_id: str,
    body: RescheduleRequest,  # {new_scheduled_at: datetime}
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    # 1. Find and verify ownership
    post = await db.scheduled_posts.find_one({"schedule_id": schedule_id, "user_id": user_id})
    if not post or post["status"] not in ["scheduled", "pending"]:
        raise HTTPException(404, "Scheduled post not found or already processed")
    
    # 2. Cancel old record atomically
    await db.scheduled_posts.update_one(
        {"schedule_id": schedule_id, "status": {"$in": ["scheduled", "pending"]}},
        {"$set": {"status": "cancelled", "cancelled_at": now}}
    )
    
    # 3. Insert new record with new schedule_id + new scheduled_at
    new_doc = {**post, "schedule_id": f"sch_{uuid.uuid4().hex[:12]}", 
               "scheduled_at": body.new_scheduled_at, "status": "scheduled",
               "created_at": now}
    await db.scheduled_posts.insert_one(new_doc)
    
    # 4. Update content_jobs.scheduled_at to reflect new time
    await db.content_jobs.update_one(
        {"job_id": post["job_id"]},
        {"$set": {"scheduled_at": body.new_scheduled_at, "updated_at": now}}
    )
    return {"rescheduled": True, "new_schedule_id": new_doc["schedule_id"], ...}
```

### Anti-Patterns to Avoid

- **Writing only to `content_jobs` when scheduling**: The Beat task reads `scheduled_posts`. Without a `scheduled_posts` insert, posts will never auto-publish.
- **Revoke individual Celery tasks for reschedule**: The scheduler uses Beat (cron) not individual task IDs. There is nothing to revoke. Reschedule = cancel old DB record + insert new one.
- **Using `gpt-4o` (not mini)** for the planner reasoning fallback: The existing code uses `gpt-4o-mini` which is intentional for cost. Keep it.
- **Calling `calculate_optimal_posting_times` on every request**: It's an expensive aggregation. It runs as a Celery task (`update_performance_intelligence`) and persists results. The planner should read the stored value.
- **Hardcoding `timezone.utc`** in scheduled_at without communicating to users: All times are stored and displayed in UTC. The dashboard should show UTC explicitly.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Idempotency in Beat task | Custom locking table | `find_one_and_update` atomic claim (already in `scheduled_tasks.py`) | MongoDB atomic update prevents double-processing |
| Monthly calendar grid | Custom date math | `useMemo` in ContentCalendar.jsx (already exists) | Already computing `daysInMonth` correctly |
| Optimal time computation from analytics | Custom ML model | `services/persona_refinement.py::calculate_optimal_posting_times` | Already aggregates engagement by day/hour |
| Post scheduling state machine | Custom FSM | Follow existing `content_jobs` status flow: approved → scheduled → publishing → published | Existing Beat task and routes already handle this |

---

## Critical Gap: Dual-Collection Disconnect

This is the most important finding for the planner.

**Current state:**
1. User clicks "Schedule" → `POST /api/dashboard/schedule/content` → `planner.schedule_content()` → writes `content_jobs.status = "scheduled"`, `content_jobs.scheduled_at = T`
2. Beat task every 5 min → `process_scheduled_posts` → reads `db.scheduled_posts` where `status IN ["pending","scheduled"]` AND `scheduled_at <= now`
3. **Nothing ever inserts into `db.scheduled_posts`** in the user-facing schedule flow

**Result:** Posts appear scheduled in the UI but never publish automatically.

**Fix in `planner.schedule_content`:** After updating `content_jobs`, iterate over `platforms` and `insert_one` into `db.scheduled_posts` for each platform.

**Verify:** Check `routes/content.py` for any scheduling path — it has no schedule endpoint (confirmed: grep found no schedule in content.py). The only schedule path goes through `dashboard.py` → `agents/planner.py`.

---

## Common Pitfalls

### Pitfall 1: Beat Task Reads `scheduled_posts` — Not `content_jobs`
**What goes wrong:** Developer sees `content_jobs.status = "scheduled"` and assumes the Beat task will find it. It won't — the Beat task exclusively queries `db.scheduled_posts`.
**Why it happens:** Two code paths for scheduling evolved independently. `planner.schedule_content` predates the `scheduled_tasks.py` refactor.
**How to avoid:** Insert into `scheduled_posts` in `schedule_content`. Tests should assert a `scheduled_posts` record exists after calling the scheduling endpoint.
**Warning signs:** Posts show "Scheduled" in UI but never appear as "Published" even after their scheduled time passes.

### Pitfall 2: Duplicate Publishing (Idempotency)
**What goes wrong:** Beat runs every 5 min. If a task takes longer than 5 min, two workers could pick the same post.
**Why it happens:** `find_one_and_update` atomic claim exists in `scheduled_tasks.py` (`_process_scheduled_posts`) but NOT in the older `content_tasks.py` version. The beat schedule points to `tasks.scheduled_tasks.process_scheduled_posts` (verified in `celeryconfig.py`) so the correct idempotent version IS used. Do not change the task routing.
**How to avoid:** Do not change the beat schedule task name. Keep `task_acks_late = True` in celeryconfig.py.

### Pitfall 3: Rescheduling Leaves Orphan Records
**What goes wrong:** Reschedule updates `content_jobs.scheduled_at` but the old `scheduled_posts` record still has the old time and `status="scheduled"`. Beat will attempt to publish at the old time.
**Why it happens:** No reschedule endpoint existed before this phase.
**How to avoid:** Reschedule must atomically set old `scheduled_posts.status = "cancelled"` before inserting the new record.

### Pitfall 4: Calendar Shows Only `content_jobs` — Misses Scheduled_Posts State
**What goes wrong:** After a post publishes, `scheduled_posts.status = "published"` but `content_jobs.status` may or may not be updated (it is updated in `scheduled_tasks.py` but the calendar reads `content_jobs`).
**Why it happens:** The calendar endpoint queries `content_jobs` only.
**How to avoid:** The new `/schedule/calendar` endpoint should query `scheduled_posts` as the authoritative source.

### Pitfall 5: Optimal Times Empty for New Users
**What goes wrong:** `calculate_optimal_posting_times` requires published posts with real `performance_data`. New users have none. `persona_engines.optimal_posting_times` will be empty or absent.
**Why it happens:** Evidence-based calculation has a cold-start problem.
**How to avoid:** Always fall back to `PLATFORM_PEAKS` heuristics when stored times are absent. The planner should check `if platform_stored else use_heuristics`.

---

## Code Examples

### Example 1: Insert into scheduled_posts when scheduling (fix for SCHD-04)
```python
# In agents/planner.py::schedule_content (add after content_jobs update)
# Source: Verified shape from scheduled_tasks.py _process_scheduled_posts and db_indexes.py

import uuid

async def _insert_scheduled_posts(db, job, platforms, scheduled_at, final_content, media_assets):
    """Create one scheduled_posts record per platform."""
    now = datetime.now(timezone.utc)
    docs = []
    for platform in platforms:
        docs.append({
            "schedule_id": f"sch_{uuid.uuid4().hex[:12]}",
            "user_id": job["user_id"],
            "job_id": job["job_id"],
            "platform": platform,
            "final_content": final_content,
            "media_assets": media_assets or [],
            "scheduled_at": scheduled_at,
            "status": "scheduled",
            "created_at": now,
        })
    if docs:
        await db.scheduled_posts.insert_many(docs)
```

### Example 2: Read stored optimal times from persona_engines
```python
# In agents/planner.py::get_optimal_posting_times
# Source: persona_refinement.py calculate_optimal_posting_times output verified

persona = await db.persona_engines.find_one(
    {"user_id": user_id},
    {"uom": 1, "optimal_posting_times": 1}
)
stored_times = (persona or {}).get("optimal_posting_times", {})
platform_slots = stored_times.get(platform, [])

if platform_slots:
    # Evidence-based: convert {day_of_week, hour, avg_engagement_rate, post_count} to suggestions
    sorted_slots = sorted(platform_slots, key=lambda s: s.get("avg_engagement_rate", 0), reverse=True)
    # Map to next occurrence of that day/hour within 7 days
    ...
else:
    # Heuristic fallback (existing PLATFORM_PEAKS logic)
    ...
```

### Example 3: Calendar endpoint pattern (new endpoint in dashboard.py)
```python
# Source: Verified field names from db_indexes.py and scheduled_tasks.py

@router.get("/schedule/calendar")
async def get_calendar_data(
    year: int = Query(..., ge=2024, le=2030),
    month: int = Query(..., ge=1, le=12),
    current_user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    user_id = current_user["user_id"]
    from calendar import monthrange
    _, last_day = monthrange(year, month)
    start = datetime(year, month, 1, tzinfo=timezone.utc)
    end = datetime(year, month, last_day, 23, 59, 59, tzinfo=timezone.utc)
    
    cursor = db.scheduled_posts.find(
        {
            "user_id": user_id,
            "scheduled_at": {"$gte": start, "$lte": end},
            "status": {"$in": ["scheduled", "pending", "publishing", "published", "failed"]},
        },
        {"_id": 0, "schedule_id": 1, "job_id": 1, "platform": 1,
         "scheduled_at": 1, "status": 1, "published_at": 1}
    ).sort("scheduled_at", 1)
    
    posts = await cursor.to_list(length=200)
    # Enrich with content preview via batch job lookup
    job_ids = list({p["job_id"] for p in posts if p.get("job_id")})
    jobs_map = {}
    if job_ids:
        async for job in db.content_jobs.find(
            {"job_id": {"$in": job_ids}},
            {"_id": 0, "job_id": 1, "final_content": 1, "content_type": 1}
        ):
            jobs_map[job["job_id"]] = job
    
    enriched = []
    for p in posts:
        job = jobs_map.get(p.get("job_id"), {})
        content = job.get("final_content", "")
        enriched.append({
            **p,
            "scheduled_at": p["scheduled_at"].isoformat() if p.get("scheduled_at") else None,
            "published_at": p.get("published_at", None),
            "preview": content[:100] + "..." if len(content) > 100 else content,
            "content_type": job.get("content_type"),
        })
    return {"posts": enriched, "year": year, "month": month}
```

### Example 4: ContentCalendar.jsx — fetch from new calendar endpoint
```jsx
// Replace fetchScheduledContent to use calendar endpoint
// Source: Existing ContentCalendar.jsx pattern adapted

const fetchCalendarData = async () => {
  const year = currentMonth.getFullYear();
  const month = currentMonth.getMonth() + 1;  // JS months are 0-indexed
  try {
    const res = await apiFetch(`/api/dashboard/schedule/calendar?year=${year}&month=${month}`);
    if (!res.ok) throw new Error("Failed to fetch calendar");
    const data = await res.json();
    setScheduledContent(data.posts || []);
  } catch (err) {
    console.error("Calendar fetch error:", err);
  } finally {
    setLoading(false);
  }
};

// Re-fetch when month changes
useEffect(() => {
  fetchCalendarData();
}, [currentMonth]);
```

---

## State of the Art

| Old Approach | Current Approach | Status | Impact |
|--------------|------------------|--------|--------|
| n8n cron triggers for publishing | Celery Beat `process_scheduled_posts` every 5 min | Already migrated (celeryconfig.py beat_schedule active) | Beat is authoritative — no n8n dependency needed |
| Static heuristic optimal times | Evidence-based from engagement data | Partially built — persona_refinement computes it; planner doesn't read it | Wire planner to read stored times |
| Calendar reads content_jobs | Calendar reads scheduled_posts | Gap — needs new endpoint | Fix in this phase |

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Celery + Redis | Beat scheduler | Configurable via REDIS_URL / CELERY_BROKER_URL | 5.3.0 / 7+ | If Redis unavailable in dev, Beat won't run — test scheduling insert logic separately |
| MongoDB (Motor) | scheduled_posts reads/writes | Always available | 3.3.1 | None |
| Anthropic API | AI reasoning in planner | Optional | 0.34.0 | Falls back to heuristic string (existing code handles this) |
| OpenAI API | gpt-4o-mini reasoning in planner | Optional | 1.40.0 | Falls back to static string (existing code: `if not openai_available()`) |

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.0.0 + pytest-asyncio 0.23.0 |
| Config file | `backend/pytest.ini` |
| Quick run command | `cd backend && pytest tests/test_celery_cutover.py -x -q` |
| Full suite command | `cd backend && pytest -x -q` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SCHD-01 | `get_optimal_posting_times` returns stored engagement times when available; falls back to heuristics | unit | `pytest tests/test_scheduling_phase31.py::test_optimal_times_uses_stored_data -x` | Wave 0 |
| SCHD-01 | `get_optimal_posting_times` returns 3 slots per platform | unit | `pytest tests/test_scheduling_phase31.py::test_optimal_times_count -x` | Wave 0 |
| SCHD-02 | `POST /api/dashboard/schedule/content` inserts into `scheduled_posts` collection | integration | `pytest tests/test_scheduling_phase31.py::test_schedule_content_creates_scheduled_posts_doc -x` | Wave 0 |
| SCHD-03 | `GET /api/dashboard/schedule/calendar` returns posts for correct month | integration | `pytest tests/test_scheduling_phase31.py::test_calendar_endpoint_month_filter -x` | Wave 0 |
| SCHD-04 | Beat task publishes from `scheduled_posts` within 2 retries | unit | `pytest tests/test_celery_cutover.py -x -q` (existing, verify passes) | YES |
| SCHD-04 | Reschedule endpoint cancels old record and creates new | integration | `pytest tests/test_scheduling_phase31.py::test_reschedule_creates_new_record -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `cd backend && pytest tests/test_celery_cutover.py tests/test_scheduling_phase31.py -x -q`
- **Per wave merge:** `cd backend && pytest -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_scheduling_phase31.py` — covers SCHD-01, SCHD-02, SCHD-03, SCHD-04 new behaviors
- [ ] Add compound index `(user_id, scheduled_at)` to `db_indexes.py` `scheduled_posts` section if calendar endpoint is slow (currently has separate `idx_user_id` and `idx_scheduled_at` but no compound — acceptable for v3.0 scale)

---

## Open Questions

1. **Should `schedule_content` fan out one `scheduled_posts` doc per platform, or one doc with a platforms list?**
   - What we know: The Beat task processes one doc at a time with `post["platform"]` (singular). The n8n bridge does the same. The `db_indexes.py` has no unique constraint on `(job_id, platform)`.
   - Recommendation: **One doc per platform** — matches existing Beat task signature and allows per-platform status tracking (one could fail, one succeed).

2. **Should the calendar endpoint replace or supplement `/schedule/upcoming`?**
   - What we know: `ContentCalendar.jsx` uses `/schedule/upcoming`. The upcoming endpoint is fine for the sidebar list. The calendar grid needs month-scoped data.
   - Recommendation: **Add new `/schedule/calendar` endpoint** and update `ContentCalendar.jsx` to call it for grid rendering. Keep `/schedule/upcoming` for the list panel.

3. **Does `ContentCalendar.jsx` need a time picker for SCHD-02 (user can modify suggested schedule)?**
   - What we know: The current UI has "Get AI Suggestions" → shows weekly schedule cards → user clicks a card → navigates to studio. There is no inline time editing.
   - Recommendation: Add a simple reschedule modal with a `datetime-local` HTML input. The backend reschedule endpoint (new) handles the rest. This satisfies SCHD-02 without a full date-picker library.

---

## Sources

### Primary (HIGH confidence)
- Direct read of `backend/agents/planner.py` — full file, all functions verified
- Direct read of `backend/tasks/scheduled_tasks.py` — `_process_scheduled_posts` logic verified
- Direct read of `backend/tasks/content_tasks.py` — duplicate `process_scheduled_posts` and `update_performance_intelligence` verified
- Direct read of `backend/celeryconfig.py` — beat_schedule confirmed pointing to `tasks.scheduled_tasks.process_scheduled_posts`
- Direct read of `backend/routes/dashboard.py` — all schedule endpoints verified
- Direct read of `frontend/src/pages/Dashboard/ContentCalendar.jsx` — full component, all API calls verified
- Direct read of `backend/db_indexes.py` lines 79-87 — `scheduled_posts` index schema
- Direct read of `backend/agents/strategist.py` — performance_intelligence field structure
- Grep of `backend/services/persona_refinement.py` — `calculate_optimal_posting_times` and `calculate_performance_intelligence` confirmed

### Secondary (MEDIUM confidence)
- Grep of `backend` for `db.scheduled_posts` — confirmed no insert_one in user-facing paths
- Grep of `backend/routes/content.py` for schedule — confirmed no scheduling endpoints in content.py

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all code verified by direct file reads
- Architecture patterns: HIGH — derived from actual task shapes and index definitions
- Pitfalls: HIGH — the dual-collection disconnect is confirmed by code (no insert into scheduled_posts in planner.schedule_content)
- Gap analysis: HIGH — verified by grep that no code path inserts into scheduled_posts from user scheduling flow

**Research date:** 2026-04-12
**Valid until:** 2026-05-12 (stable codebase; no external APIs changing in this phase)
