# Phase 14: Strategy Dashboard + Notifications — Research

**Researched:** 2026-04-01
**Domain:** React page scaffold, FastAPI REST routes, SSE notification integration, shadcn/ui card components
**Confidence:** HIGH

---

## Summary

Phase 14 is entirely additive — it surfaces data that already exists in `db.strategy_recommendations` (written by Phase 12's Strategist Agent) and wires up notifications already flowing through `db.notifications` (written by the `notification_service` and n8n bridge). No new data pipelines need to be built; this phase is a UI + thin API layer on top of completed backend work.

The backend work is a single new file: `backend/routes/strategy.py` with three endpoints, registered in `server.py`. The frontend work is a new Dashboard page, a custom hook `useStrategyFeed`, and two new type icons in the `NotificationBell` component. All shadcn/ui components required (Card, Tabs, Badge, Button) are already installed. The SSE infrastructure is already running at `GET /api/notifications/stream` — the frontend `useNotifications` hook already handles reconnection and deduplication. No new npm packages are required.

The one non-trivial design decision is how "Approve" navigates the user after firing `POST /api/content/create`. The content generation job is async — the route returns a `job_id` immediately. The simplest correct pattern is: Approve fires the POST, then navigates to `/dashboard/studio?job={job_id}` so the user sees the generation in progress in the existing ContentStudio polling UI. This mirrors the pattern already used in `DashboardHome.jsx` (`navigate('/dashboard/studio?job=...')`).

**Primary recommendation:** Create `backend/routes/strategy.py` with three endpoints calling existing `strategist.handle_approval` / `handle_dismissal` functions, then create `frontend/src/pages/Dashboard/StrategyDashboard.jsx` with two tabs (Active / History) backed by a `useStrategyFeed` hook that polls the strategy API.

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DASH-01 | New React page with SSE-driven recommendation card feed (max 3 active cards shown) | SSE already running via `useNotifications`; a new `useStrategyFeed` hook polls `GET /api/strategy` and listens for `strategy_ready` SSE events to trigger re-fetch |
| DASH-02 | One-click "Approve" fires POST /api/content/generate with pre-filled payload from card | `generate_payload` already stored on each card (STRAT-07); content create endpoint is `POST /api/content/create`; navigation to `/dashboard/studio?job={job_id}` is the existing pattern |
| DASH-03 | Dismissed cards archived to History tab (not deleted) | `handle_dismissal` already sets `status: "dismissed"` in DB; History tab queries with `status=dismissed`; DB records are never deleted |
| DASH-04 | SSE notifications for job completion, trending topic alerts, scheduled post published | `notification_service.create_notification` is already called by n8n bridge; SSE stream at `/api/notifications/stream` already broadcasts to client; only missing part is new notification types for strategy cards |
| DASH-05 | Strategy routes (GET /api/strategy, POST /api/strategy/:id/approve, POST /api/strategy/:id/dismiss) | `handle_approval` and `handle_dismissal` already implemented in `agents/strategist.py`; routes are thin wrappers calling these functions |
</phase_requirements>

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | 0.110.1 | REST API routes (backend) | Existing stack — no change |
| React | 18.3.1 | New Dashboard page | Existing stack — no change |
| React Router DOM | 7.5.1 | New `/dashboard/strategy` route | Already used by all Dashboard pages |
| Motor (async MongoDB) | 3.3.1 | DB queries in strategy route | Existing stack — `from database import db` pattern |
| Starlette StreamingResponse | (via FastAPI 0.110.1) | SSE stream (already in use) | `routes/notifications.py` uses this exact pattern |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| shadcn/ui Card | installed | Recommendation card layout | Use `Card`, `CardHeader`, `CardContent`, `CardFooter` — already in `src/components/ui/card.jsx` |
| shadcn/ui Tabs | installed | Active / History tab view | Use `Tabs`, `TabsList`, `TabsTrigger`, `TabsContent` — already in `src/components/ui/tabs.jsx` |
| shadcn/ui Badge | installed | Platform label, signal_source chip | Already in `src/components/ui/badge.jsx` |
| shadcn/ui Button | installed | Approve / Dismiss buttons | Already in `src/components/ui/button.jsx` |
| framer-motion | 12.38.0 | Card entrance animation | Used on DashboardHome, Analytics — `motion.div initial/animate` pattern |
| lucide-react | 0.507.0 | Platform icons, signal icons | Used across all Dashboard pages |

### No New npm or pip Packages
This phase requires zero new dependencies on either side of the stack. All components, hooks infrastructure, and service functions are already installed and tested.

**Version verification:** Confirmed by reading `package.json` and `requirements.txt` — no additions needed.

---

## Architecture Patterns

### Recommended Project Structure

New files this phase creates:

```
backend/
  routes/
    strategy.py          # NEW — DASH-05: GET /api/strategy, POST /api/strategy/:id/approve|dismiss

frontend/src/
  pages/Dashboard/
    StrategyDashboard.jsx # NEW — DASH-01, DASH-02, DASH-03
  hooks/
    useStrategyFeed.js   # NEW — poll strategy API + react to SSE events
```

Files modified:

```
backend/
  server.py              # Add strategy_router import and registration
frontend/src/
  pages/Dashboard/index.jsx   # Add /strategy route
  pages/Dashboard/Sidebar.jsx # Add "Strategy" nav item with "New" badge
  components/NotificationBell.jsx # Add strategy_ready type icon
```

### Pattern 1: Strategy Routes (backend)

The three strategy endpoints are thin wrappers around already-implemented functions in `agents/strategist.py`. Pattern follows the exact style of existing routes in `routes/content.py`, `routes/notifications.py`.

```python
# Source: routes/notifications.py — established router pattern
from fastapi import APIRouter, Depends, HTTPException
from auth_utils import get_current_user
from agents.strategist import handle_approval, handle_dismissal
from database import db

router = APIRouter(prefix="/strategy", tags=["strategy"])

@router.get("")
async def get_strategy_feed(
    status: str = "pending_approval",
    limit: int = 20,
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user["user_id"]
    query = {"user_id": user_id, "status": status}
    cards = (
        await db.strategy_recommendations.find(query, {"_id": 0})
        .sort("created_at", -1)
        .limit(limit)
        .to_list(limit)
    )
    # Serialize datetime fields
    for card in cards:
        for field in ("created_at", "dismissed_at", "expires_at"):
            if hasattr(card.get(field), "isoformat"):
                card[field] = card[field].isoformat()
    return {"cards": cards, "count": len(cards)}

@router.post("/{recommendation_id}/approve")
async def approve_card(
    recommendation_id: str,
    current_user: dict = Depends(get_current_user),
):
    result = await handle_approval(
        user_id=current_user["user_id"],
        recommendation_id=recommendation_id,
    )
    if result.get("error") == "not_found":
        raise HTTPException(status_code=404, detail="Recommendation not found or already actioned")
    return result

@router.post("/{recommendation_id}/dismiss")
async def dismiss_card(
    recommendation_id: str,
    current_user: dict = Depends(get_current_user),
):
    result = await handle_dismissal(
        user_id=current_user["user_id"],
        recommendation_id=recommendation_id,
    )
    if result.get("error") == "not_found":
        raise HTTPException(status_code=404, detail="Recommendation not found or already actioned")
    return result
```

**Note on `generate_payload` field:** `handle_approval` returns `{"approved": True, "generate_payload": {...}}`. The `generate_payload` dict already contains `platform`, `content_type`, and `raw_input` — exactly what `POST /api/content/create` needs (see `ContentCreateRequest` in `routes/content.py`). The route does NOT call `/api/content/create` itself — that call happens on the frontend after receiving the `generate_payload`.

### Pattern 2: `useStrategyFeed` Hook (frontend)

The hook follows the same structure as `useNotifications.js` — initial fetch on mount, SSE event triggers re-fetch.

```javascript
// Source: frontend/src/hooks/useNotifications.js — established SSE hook pattern
import { useState, useEffect, useCallback } from "react";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

export default function useStrategyFeed() {
  const [activeCards, setActiveCards] = useState([]);
  const [historyCards, setHistoryCards] = useState([]);
  const [loading, setLoading] = useState(true);

  const getAuthHeaders = useCallback(() => {
    const token = localStorage.getItem("thook_token");
    return token ? { Authorization: `Bearer ${token}` } : {};
  }, []);

  const fetchActiveCards = useCallback(async () => {
    const res = await fetch(
      `${BACKEND_URL}/api/strategy?status=pending_approval&limit=3`,
      { headers: getAuthHeaders(), credentials: "include" }
    );
    if (!res.ok) return;
    const data = await res.json();
    setActiveCards(data.cards || []);
  }, [getAuthHeaders]);

  const fetchHistoryCards = useCallback(async () => {
    const res = await fetch(
      `${BACKEND_URL}/api/strategy?status=dismissed&limit=20`,
      { headers: getAuthHeaders(), credentials: "include" }
    );
    if (!res.ok) return;
    const data = await res.json();
    setHistoryCards(data.cards || []);
  }, [getAuthHeaders]);

  // Approve: call backend, then return generate_payload to caller
  const approveCard = useCallback(async (recommendationId) => {
    const res = await fetch(
      `${BACKEND_URL}/api/strategy/${recommendationId}/approve`,
      { method: "POST", headers: getAuthHeaders(), credentials: "include" }
    );
    if (!res.ok) throw new Error("Failed to approve card");
    const data = await res.json();
    await fetchActiveCards();
    return data.generate_payload;  // caller fires POST /api/content/create
  }, [getAuthHeaders, fetchActiveCards]);

  const dismissCard = useCallback(async (recommendationId) => {
    const res = await fetch(
      `${BACKEND_URL}/api/strategy/${recommendationId}/dismiss`,
      { method: "POST", headers: getAuthHeaders(), credentials: "include" }
    );
    if (!res.ok) throw new Error("Failed to dismiss card");
    await Promise.all([fetchActiveCards(), fetchHistoryCards()]);
  }, [getAuthHeaders, fetchActiveCards, fetchHistoryCards]);

  useEffect(() => {
    const init = async () => {
      setLoading(true);
      await Promise.all([fetchActiveCards(), fetchHistoryCards()]);
      setLoading(false);
    };
    init();
  }, [fetchActiveCards, fetchHistoryCards]);

  return { activeCards, historyCards, loading, approveCard, dismissCard, refresh: fetchActiveCards };
}
```

**SSE integration for strategy_ready:** The existing `useNotifications` hook already receives all SSE events. The `StrategyDashboard` page should call `useStrategyFeed().refresh()` when a `strategy_ready` or `workflow_status` notification arrives with `metadata.workflow_type === "nightly-strategist"`. The hook can subscribe to a prop/callback pattern or use a shared notification context.

### Pattern 3: One-Click Approve flow (frontend)

After `approveCard()` returns the `generate_payload`, the component fires `POST /api/content/create` then navigates:

```javascript
// Source: frontend/src/pages/Dashboard/ContentStudio/index.jsx lines 92-116 — established pattern
const handleApprove = async (card) => {
  try {
    const generatePayload = await approveCard(card.recommendation_id);
    const token = localStorage.getItem("thook_token");
    const res = await fetch(`${BACKEND_URL}/api/content/create`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
      credentials: "include",
      body: JSON.stringify(generatePayload),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Generation failed");
    }
    const data = await res.json();
    navigate(`/dashboard/studio?job=${data.job_id}`);
  } catch (e) {
    toast({ title: "Approval failed", description: e.message, variant: "destructive" });
  }
};
```

### Pattern 4: StrategyDashboard page tab layout

Active tab shows max 3 cards (enforced by API `limit=3`). History tab shows dismissed cards in a condensed read-only list. Follows the Analytics.jsx tab pattern already in use.

```javascript
// Source: frontend/src/pages/Dashboard/Analytics.jsx lines 1-12 — established page pattern
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { motion, AnimatePresence } from "framer-motion";
```

### Pattern 5: Server registration

Follows the pattern in `server.py` lines 29-52 and 290-311:

```python
# In server.py
from routes.strategy import router as strategy_router
# ... in the api_router.include_router block:
api_router.include_router(strategy_router)
```

### Anti-Patterns to Avoid

- **Calling `/api/content/create` from the backend route:** The `POST /api/strategy/:id/approve` route should only mark the card as approved and return `generate_payload`. It must NOT call the content pipeline itself — that would bypass the frontend's progress tracking UI and break the user experience. The frontend fires the content generation call after receiving the payload.
- **Deleting dismissed cards:** The DB record must remain — it is the 14-day suppression mechanism. `handle_dismissal` already sets `status: "dismissed"` with `dismissed_at` timestamp. Never delete from `db.strategy_recommendations`.
- **Showing all history at once:** History tab should use `limit=20` (same as notification list). Unlimited history fetch will slow the page after weeks of use.
- **Opening EventSource with auth header:** `EventSource` does not support custom headers. The existing SSE implementation relies on `withCredentials: true` (cookie-based). The strategy dashboard should not open a new SSE connection — it should consume the already-running notification stream via a shared hook or prop pattern.
- **Blocking on `POST /api/content/create` response:** Content generation runs as a background task and returns `job_id` immediately (see `routes/content.py` lines 94-116). The Approve button should navigate immediately on 200 response, not wait for generation to complete.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| SSE stream | New SSE endpoint for strategy cards | Existing `/api/notifications/stream` + new notification type `strategy_ready` | The full SSE infrastructure (heartbeat, reconnect, event generator, scoped by `user_id`) is already in `routes/notifications.py` and `useNotifications.js` |
| Card dismissal tracking | Custom suppression logic | `agents/strategist.handle_dismissal()` | Suppression window, consecutive dismissal counting, halved_rate flag — all already implemented with correct MongoDB atomic operations (Phase 12) |
| Approval side effects | Custom reset logic | `agents/strategist.handle_approval()` | Resets `consecutive_dismissals` to 0, `halved_rate` to False — already implemented and tested |
| SSE auto-reconnect | Manual `EventSource` reconnect logic | Browser native `EventSource` auto-reconnect | The browser reconnects automatically on error; `useNotifications` already handles this with `eventSource.onerror = () => {}` |
| Datetime serialization | Custom serializer | Standard `.isoformat()` pattern | Used in `routes/notifications.py` lines 70-71 — copy the same pattern for strategy routes |
| Strategy recommendations index | New compound index | Already defined in `db_indexes.py` lines 219-226 | `idx_user_status` and `idx_user_created` cover the queries needed by `GET /api/strategy` |

**Key insight:** The entire data layer and business logic for this phase was built in Phase 12. Phase 14 is the presentation layer only.

---

## Common Pitfalls

### Pitfall 1: `generate_payload` field mismatch with `ContentCreateRequest`

**What goes wrong:** The `generate_payload` stored on the card by the Strategist was validated against `ContentCreateRequest` schema by `_build_generate_payload()` in `strategist.py`. However, `ContentCreateRequest` has optional fields (`attachment_url`, `upload_ids`, `campaign_id`, `generate_video`, `video_style`). If the frontend sends extra fields not in the Pydantic model, FastAPI will silently ignore them (not error). If required fields are missing, a `422 Unprocessable Entity` is returned.

**Why it happens:** The Strategist only writes `platform`, `content_type`, `raw_input` to `generate_payload`. The content route expects exactly those three as required fields — all others are optional. This should work cleanly, but a `generate_payload` written by an older Strategist run might have different field names if the schema was ever changed.

**How to avoid:** In the frontend, before calling `POST /api/content/create`, verify the payload contains `platform`, `content_type`, and `raw_input`. If any is missing, show an error and do not fire the request. Do not add extra fields to the payload.

**Warning signs:** 422 response from `/api/content/create`; check DevTools network tab for the request body.

### Pitfall 2: SSE stream drops JWT auth

**What goes wrong:** `EventSource` cannot send `Authorization: Bearer` headers. The existing `useNotifications` hook uses `withCredentials: true`, which sends cookies. If the user's session cookie is not set (e.g., local dev without `credentials: include` on initial requests), the SSE stream will return 401 silently and the `onerror` handler suppresses it.

**Why it happens:** The `notifications/stream` endpoint uses `get_current_user` JWT dependency. For the stream to work, a prior request must have established the cookie session, or the `withCredentials` cookie must be present.

**How to avoid:** This is an existing constraint, not new to Phase 14. The `StrategyDashboard` page does not open its own SSE stream — it uses the already-running notification stream. No new auth handling is needed.

**Warning signs:** Empty notification feed in prod; `unreadCount` stuck at 0; check that `REACT_APP_BACKEND_URL` does not include a trailing slash (can break cookie scoping).

### Pitfall 3: Active card count exceeds 3 due to query not filtering approved status

**What goes wrong:** `GET /api/strategy?status=pending_approval` could return cards that were just approved (status changed to `"approved"`) if the client makes the request before the approval POST response completes.

**Why it happens:** Race condition between Approve POST and the subsequent `fetchActiveCards()` call in `useStrategyFeed.approveCard()`.

**How to avoid:** `fetchActiveCards()` is called inside `approveCard()` after `await` on the approve POST — sequential, not parallel. The re-fetch happens only after the status update is committed. No race condition if the hook implementation follows the sequential pattern shown above.

**Warning signs:** User sees a card still displayed after clicking Approve; resolved by ensuring `await` before `fetchActiveCards()`.

### Pitfall 4: `strategy_ready` notification type not in `TYPE_ICONS` map

**What goes wrong:** `NotificationBell.jsx` has a `TYPE_ICONS` map. If a notification of type `strategy_ready` (or `workflow_status`) arrives and is not in the map, it falls back to the `system` icon (`"🔔"`). This is acceptable behavior, but the planner should decide whether to add a dedicated icon.

**Why it happens:** The `nightly-strategist` workflow creates a `workflow_status` notification (not a new type). The existing `TYPE_ICONS` map in `NotificationBell.jsx` does not have a `workflow_status` entry.

**How to avoid:** Add `workflow_status: "🎯"` (or similar) to `TYPE_ICONS` in `NotificationBell.jsx` so strategy notifications are visually distinct from generic system notifications.

**Warning signs:** Strategy notifications show the default bell icon instead of a strategy-specific icon.

### Pitfall 5: `server.py` router registration ordering

**What goes wrong:** Adding `strategy_router` to `api_router` but forgetting to add the import and registration causes a `ImportError` at startup, not a 404.

**How to avoid:** Follow the exact pattern of the existing block in `server.py` lines 29-52 (import) and lines 290-311 (include_router). Add both in the same commit.

**Warning signs:** `ImportError: cannot import name 'strategy_router'`; startup fails cleanly with a clear error message.

---

## Code Examples

### GET /api/strategy response shape

The cards returned from `db.strategy_recommendations` have this shape (from `run_strategist_for_user` in `agents/strategist.py` lines 421-435):

```python
{
  "recommendation_id": "strat_abc123",
  "user_id": "user_xyz",
  "status": "pending_approval",   # or "dismissed" or "approved"
  "topic": "ai in content creation",
  "hook_options": ["Hook A", "Hook B", "Hook C"],
  "platform": "linkedin",
  "why_now": "Why now: Your last 3 posts on AI averaged 2x engagement",
  "signal_source": "performance",  # "persona" | "performance" | "knowledge_graph" | "trending"
  "generate_payload": {
    "platform": "linkedin",
    "content_type": "post",
    "raw_input": "Write about AI in content creation using contrarian hook"
  },
  "created_at": "2026-04-01T03:00:00+00:00",
  "dismissed_at": null,
  "dismissed_reason": null,
  "expires_at": null
}
```

### Dashboard route registration pattern

```javascript
// Source: frontend/src/pages/Dashboard/index.jsx — existing pattern
import StrategyDashboard from "./StrategyDashboard";

// Inside <Routes>:
<Route path="/strategy" element={
  <><TopBar onMenuClick={() => setSidebarOpen(true)} title="Strategy" />
  <StrategyDashboard /></>
} />
```

### Sidebar nav item pattern

```javascript
// Source: frontend/src/pages/Dashboard/Sidebar.jsx — existing navItems array
{ to: "/dashboard/strategy", label: "Strategy", icon: Lightbulb, badge: "New" },
```

Use `Lightbulb` from `lucide-react` (already imported in other pages like `Analytics.jsx`).

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Celery beat for notifications | n8n cron + n8n_bridge callback | Phase 9 | All notifications now flow through `create_notification()` called from `n8n_bridge.py`'s `_dispatch_workflow_notification` — the strategy notification is already wired |
| Strategist logic in route | Strategist logic in `agents/strategist.py` | Phase 12 | Routes are thin wrappers; all business logic, cadence controls, and suppression live in the agent |
| No strategy DB | `db.strategy_recommendations` with compound indexes | Phase 12 | `idx_user_status`, `idx_user_created`, `idx_user_topic_status` indexes already in `db_indexes.py` |

**Not deprecated or outdated:** The SSE stream (`_sse_event_generator` in `routes/notifications.py`) still uses polling (10-second interval) rather than MongoDB change streams. This is intentional — push-based change streams require more infrastructure. The polling approach works correctly for this use case.

---

## Open Questions

1. **Should "Approve" include the History tab?**
   - What we know: Approved cards change status to `"approved"` (not `"dismissed"`). The History tab as described in DASH-03 says "dismissed cards archived to History tab". Approved cards are a third state.
   - What's unclear: Should the History tab show only `dismissed` cards, or `dismissed + approved`? Showing approved cards in history would let users see "what they approved and when" — potentially useful.
   - Recommendation: Show both `dismissed` and `approved` cards in History, sorted by `created_at` descending. Two sub-filters (All / Dismissed / Approved) could be added as tab triggers, but start with All to keep Wave 0 simple.

2. **Calibration prompt display for consecutive dismissals**
   - What we know: `handle_dismissal` returns `{"needs_calibration_prompt": true}` when 5 consecutive dismissals occur (STRAT-06). The current `StrategyDashboard` spec does not mention where to show this.
   - What's unclear: Should Phase 14 render a calibration prompt/banner, or defer that UX to a later phase?
   - Recommendation: Check `needs_calibration_prompt` in the dismiss response and show a `toast` notification: "You've dismissed several recommendations — your strategy feed will be recalibrated." Simple, non-blocking.

3. **`limit=3` enforcement: server-side or client-side?**
   - What we know: DASH-01 requires max 3 active cards shown. The Strategist enforces max 3 cards written per day (STRAT-04). Over multiple days, `pending_approval` count could grow beyond 3 if the user does not act.
   - Recommendation: Apply `limit=3` in the API call (`GET /api/strategy?status=pending_approval&limit=3`), not only in the frontend. This ensures the "max 3 active cards shown" rule is enforced at the data layer too.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.13 | Backend routes | ✓ | 3.13.5 | — |
| FastAPI | Strategy routes | ✓ | 0.110.1 | — |
| Motor (async MongoDB) | `db.strategy_recommendations` queries | ✓ | 3.3.1 | — |
| Node.js | Frontend build | ✓ | 20.15.0 | — |
| npm | Package install | ✓ | 10.7.0 | — |
| `agents/strategist.py` | `handle_approval`, `handle_dismissal` | ✓ | Verified import | — |
| `services/notification_service.py` | `create_notification` | ✓ | Verified import | — |
| `db.strategy_recommendations` collection | Strategy feed | ✓ | Indexes in `db_indexes.py` lines 219-226 | — |
| `GET /api/notifications/stream` | SSE for DASH-04 | ✓ | Running in `routes/notifications.py` | — |

**Missing dependencies with no fallback:** None — all dependencies are already in place.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.0.0 + pytest-asyncio 0.23.0 |
| Config file | `backend/pytest.ini` (`asyncio_mode = auto`) |
| Quick run command | `cd backend && pytest tests/test_strategy_routes.py -x` |
| Full suite command | `cd backend && pytest` |

### Phase Requirements to Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DASH-05 | GET /api/strategy returns pending_approval cards for user | unit (mocked DB) | `pytest tests/test_strategy_routes.py::TestGetStrategyFeed -x` | ❌ Wave 0 |
| DASH-05 | GET /api/strategy with status=dismissed returns history | unit (mocked DB) | `pytest tests/test_strategy_routes.py::TestGetStrategyHistory -x` | ❌ Wave 0 |
| DASH-05 | POST /api/strategy/:id/approve calls handle_approval, returns generate_payload | unit (mocked strategist) | `pytest tests/test_strategy_routes.py::TestApproveCard -x` | ❌ Wave 0 |
| DASH-05 | POST /api/strategy/:id/dismiss calls handle_dismissal | unit (mocked strategist) | `pytest tests/test_strategy_routes.py::TestDismissCard -x` | ❌ Wave 0 |
| DASH-05 | 404 returned when recommendation_id not found or already actioned | unit | `pytest tests/test_strategy_routes.py::TestNotFound -x` | ❌ Wave 0 |
| DASH-02 | generate_payload from approve contains platform, content_type, raw_input | unit | `pytest tests/test_strategy_routes.py::TestGeneratePayloadShape -x` | ❌ Wave 0 |
| DASH-04 | Notification type `workflow_status` with workflow_type=nightly-strategist exists in DB after nightly run | integration | `pytest tests/test_n8n_bridge.py` (existing, already covers workflow notifications) | ✓ existing |

### Sampling Rate

- **Per task commit:** `cd backend && pytest tests/test_strategy_routes.py -x`
- **Per wave merge:** `cd backend && pytest`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `backend/tests/test_strategy_routes.py` — covers DASH-05, DASH-02
- [ ] No framework install needed — pytest + pytest-asyncio already installed
- [ ] No new conftest.py needed — existing `tests/conftest.py` covers Motor mocking patterns (see `test_strategist.py` and `test_n8n_bridge.py` for mock patterns to follow)

*(Frontend tests: No frontend test framework is configured — `package.json` has Jest via `react-scripts` but no test files for Dashboard pages exist. Frontend coverage is manual smoke testing per the existing project convention.)*

---

## Project Constraints (from CLAUDE.md)

The following directives from `CLAUDE.md` apply to this phase. The planner MUST verify compliance in every plan.

| Directive | Impact on Phase 14 |
|-----------|-------------------|
| Never commit to `main` — branch from `dev`, PR targets `dev` | All work on `feat/strategy-dashboard` branching from `dev` |
| Branch naming: `fix/`, `feat/`, `infra/` | Use `feat/strategy-dashboard-notifications` |
| Config pattern: all settings via `backend/config.py` dataclasses, never `os.environ.get()` directly | Strategy route has no new env vars; uses existing `settings` singleton |
| Database pattern: `from database import db`, Motor async | `await db.strategy_recommendations.find(...)` — no synchronous PyMongo |
| LLM model: `claude-sonnet-4-20250514` | Phase 14 does not call LLM directly — the strategist already wrote cards |
| After any change to `backend/agents/`, verify full pipeline flow | Phase 14 does NOT modify `agents/strategist.py` — only calls its public API from a new route |
| Never introduce a new Python package without adding to `requirements.txt` | No new packages needed |
| Never introduce a new npm package | No new packages needed |
| PR checklist: branch targets `dev`, no secrets, no `os.environ.get()` | Must be checked before PR |

---

## Sources

### Primary (HIGH confidence)

- `backend/agents/strategist.py` (lines 501-605) — `handle_approval`, `handle_dismissal` public API, `generate_payload` shape
- `backend/routes/notifications.py` — SSE endpoint pattern, `_sse_event_generator`, auth dependency pattern
- `backend/services/notification_service.py` — `create_notification` signature and notification document shape
- `frontend/src/hooks/useNotifications.js` — SSE hook pattern: `EventSource`, deduplication, unread count
- `frontend/src/pages/Dashboard/index.jsx` — Dashboard route registration pattern
- `frontend/src/pages/Dashboard/Sidebar.jsx` — `navItems` array pattern for adding new nav entry
- `frontend/src/pages/Dashboard/ContentStudio/index.jsx` lines 87-116 — `POST /api/content/create` call pattern and navigate-to-studio pattern
- `backend/routes/content.py` lines 33-41 — `ContentCreateRequest` required fields (`platform`, `content_type`, `raw_input`)
- `backend/server.py` lines 29-52, 290-311 — router import + registration pattern
- `backend/db_indexes.py` lines 219-226 — `strategy_recommendations` collection indexes (confirmed `idx_user_status` and `idx_user_created` cover needed queries)
- `frontend/src/components/ui/card.jsx`, `tabs.jsx` — shadcn/ui components already installed
- `backend/pytest.ini` — `asyncio_mode = auto` (no `@pytest.mark.asyncio` decorator needed)

### Secondary (MEDIUM confidence)

- `backend/routes/n8n_bridge.py` lines 115-117 — `nightly-strategist` notification title/body already wired in `WORKFLOW_NOTIFICATION_MAP`; strategy notification fires automatically when Strategist runs
- `frontend/src/pages/Dashboard/Analytics.jsx` lines 1-12 — confirmed `Tabs`, `Card`, `Badge`, `Button`, `motion`, `AnimatePresence` import pattern in a production Dashboard page

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — zero new dependencies; all components, hooks, and services confirmed present by direct file inspection
- Architecture: HIGH — route patterns, hook patterns, and component patterns all verified against existing production files
- Pitfalls: HIGH — all identified from reading actual production code (generate_payload shape, SSE auth constraint, EventSource limitations)

**Research date:** 2026-04-01
**Valid until:** 2026-05-01 (stable stack, no fast-moving dependencies in scope)
