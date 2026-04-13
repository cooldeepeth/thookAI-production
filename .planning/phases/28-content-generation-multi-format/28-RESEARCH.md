# Phase 28: Content Generation Multi-Format — Research

**Researched:** 2026-04-12
**Domain:** Multi-format content generation pipeline, platform-specific Writer prompts, ContentStudio UI, real-time progress polling, inline edit/approve/schedule
**Confidence:** HIGH

---

## Summary

Phase 28 is primarily a **wiring and completion** phase — not greenfield. The backend pipeline, all 5 agents, the ContentStudio UI, and the polling mechanism all exist and work. The gap is that 3 of the 9 required content formats are missing or incomplete, the Writer's `PLATFORM_RULES` dict is a single-key-per-platform flat string (no format differentiation), and the `PLATFORM_CONTENT_TYPES` allowlist on the backend does not yet include `story_sequence` for Instagram. The frontend `InputPanel` already renders platform and format pickers for all 3 platforms, but only exposes 2 LinkedIn types, 2 X types, and 2 Instagram types — missing LinkedIn article as a first-class UI choice and Instagram story_sequence entirely. Real-time pipeline progress already works via 2-second polling and `current_agent` field updates in `content_jobs`.

The biggest work items are: (1) adding per-format `PLATFORM_RULES` strings in `writer.py` so each of the 9 formats has a distinct prompt; (2) adding `story_sequence` to the backend allowlist and the frontend PLATFORMS config; (3) verifying the LinkedIn `article` content_type flows through to the Writer correctly; (4) hooking the existing `PublishPanel` schedule flow to the content calendar for CONT-11; (5) writing tests that assert format-specific output characteristics (tweet under 280 chars, IG hashtag count, LinkedIn article has header).

**Primary recommendation:** Make targeted, surgical changes to `writer.py` (format-specific rules), `content.py` (add story_sequence to allowlist), `InputPanel.jsx` (expose all 9 types), and add pytest/Jest tests per format. Do not refactor the pipeline — it works.

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CONT-01 | User can generate LinkedIn text post with persona-aware voice | Backend: `post` content_type already in allowlist; Writer uses `PLATFORM_RULES["linkedin"]` — needs format-specific string |
| CONT-02 | User can generate LinkedIn article with persona-aware voice | Backend: `article` in allowlist; Writer has no article-specific rules — needs format rules in WRITER_PROMPT |
| CONT-03 | User can generate LinkedIn carousel with persona-aware voice | Backend: `carousel_caption` in allowlist; Designer agent handles slides separately; Writer needs carousel-specific prompt rules |
| CONT-04 | User can generate X tweet with persona-aware voice | Backend: `tweet` in allowlist; Writer uses `PLATFORM_RULES["x"]` flat rule — needs tweet-specific rule enforcing 280 char limit |
| CONT-05 | User can generate X thread with persona-aware voice | Backend: `thread` in allowlist; Writer mock outputs numbered format; needs explicit thread rules in Writer |
| CONT-06 | User can generate Instagram feed caption with persona-aware voice | Backend: `feed_caption` in allowlist; Writer uses `PLATFORM_RULES["instagram"]` — needs feed-specific rules |
| CONT-07 | User can generate Instagram reel script | Backend: `reel_caption` in allowlist; Writer uses generic instagram rule — needs reel script rules |
| CONT-08 | User can generate Instagram story sequence | Backend: `story_sequence` is MISSING from `PLATFORM_CONTENT_TYPES` — must add; Writer has no story rules; frontend has no story type button |
| CONT-09 | Each format uses platform-specific Writer prompts | `PLATFORM_RULES` in writer.py has only 3 keys (linkedin, x, instagram) — needs 9 format keys |
| CONT-10 | ContentStudio UI has format selection per platform | `InputPanel.jsx` PLATFORMS constant already renders format tabs; missing: LinkedIn `article` tab, Instagram `story_sequence` tab |
| CONT-11 | User can edit, approve, and schedule generated content | Edit+approve: fully implemented via ContentOutput/PlatformShell; Schedule: PublishPanel exists with date/time picker — needs verify e2e |
| CONT-12 | Content generation shows real-time pipeline progress | AgentPipeline.jsx polls `current_agent` every 2s — fully implemented; needs verify each stage actually advances |
</phase_requirements>

---

## Project Constraints (from CLAUDE.md)

### Required Patterns
- All settings via `backend/config.py` dataclasses. Never `os.environ.get()` directly.
- Database: `from database import db` with Motor async. Never synchronous PyMongo.
- LLM model: `claude-sonnet-4-20250514` (Anthropic primary)
- After any change to `backend/agents/`, manually verify full pipeline: Commander → Scout → Thinker → Writer → QC
- Branch from `dev`, PR targets `dev`. Never commit to `main`.
- Branch naming: `feat/short-description`
- New Python packages: add to `backend/requirements.txt`
- Frontend: use `apiFetch()` from `@/lib/api`, never raw `fetch()`
- Frontend: cookie-based auth, `apiFetch` injects `X-CSRF-Token` automatically
- Frontend: `@/` maps to `src/`

### Design System
- Colors: `lime` (`#D4FF00`) for primary CTA, `violet` (`#7000FF`) for secondary
- Typography: `font-display` for headings, default for body, `font-mono` for stats/counts
- Cards: `card-thook` and `card-thook-interactive` classes
- Animations: Framer Motion with `motion.div`, `AnimatePresence`
- Icons: Lucide React only
- Buttons: `btn-primary` for CTA, `btn-ghost` for secondary

### Testing
- Backend: `cd backend && pytest` — test files in `backend/tests/`
- Frontend: Jest + React Testing Library, MSW for API mocking, test files in `frontend/src/__tests__/`
- Minimum 80% coverage on new code

---

## Standard Stack

### Core (all already installed — no new packages needed)
| Library | Version | Purpose | Status |
|---------|---------|---------|--------|
| FastAPI | 0.110.1 | Backend API | Installed |
| Pydantic | 2.6.4+ | Request validation | Installed |
| Motor | 3.3.1 | Async MongoDB | Installed |
| Anthropic | 0.34.0 | Claude LLM (Writer) | Installed |
| React | 18.3.1 | Frontend UI | Installed |
| Framer Motion | 12.38.0 | Animations | Installed |
| Lucide React | 0.507.0 | Icons | Installed |
| pytest | 8.0.0 | Backend tests | Installed |
| pytest-asyncio | 0.23.0 | Async tests | Installed |

**No new packages required for this phase.** All required libraries are already installed.

---

## Architecture Patterns

### The 9 Formats Matrix

| Platform | Content Type (backend key) | UI Label | Status |
|----------|---------------------------|----------|--------|
| linkedin | `post` | Post | Allowed, has writer rules |
| linkedin | `article` | Article | Allowed, NO writer rules |
| linkedin | `carousel_caption` | Carousel | Allowed, NO format-specific rules |
| x | `tweet` | Tweet | Allowed, has writer rules |
| x | `thread` | Thread | Allowed, NO explicit thread rules |
| instagram | `feed_caption` | Feed Post | Allowed, has writer rules |
| instagram | `reel_caption` | Reel | Allowed, NO reel-specific rules |
| instagram | `story_sequence` | Story | MISSING from backend + frontend |

**Note:** LinkedIn `article` is in `PLATFORM_CONTENT_TYPES` (line 27 of content.py) but missing from the frontend `InputPanel.jsx` PLATFORMS constant. Instagram `story_sequence` is missing from both.

### Current Writer PLATFORM_RULES (writer.py lines 9-13)
```python
PLATFORM_RULES = {
    "linkedin": "LinkedIn post (max 3000 chars)...",
    "x": "X (Twitter) post or thread. Single tweet = max 280 chars...",
    "instagram": "Instagram caption (max 2200 chars)...",
}
```

The lookup on line 204 uses `platform.lower()` not `content_type` — so all LinkedIn formats (post, article, carousel) get the same `"linkedin"` rule. This is the core gap for CONT-09.

### Required Change: Format-Specific PLATFORM_RULES

Replace the platform-keyed dict with a format-keyed dict:

```python
FORMAT_RULES = {
    "post": "LinkedIn text post (max 3,000 chars). Line breaks are essential — every 2-3 sentences. Hook in first line. Max 3-5 hashtags at the end. No salesy language.",
    "article": "LinkedIn long-form article (min 600 words, max 3,000). Start with a compelling headline (H1-style bold line). Use ## section headers. End with a strong conclusion and question CTA. No hashtags in articles.",
    "carousel_caption": "LinkedIn carousel intro post (max 1,500 chars). This is the text that appears with a multi-slide carousel. Tease the slides: '5 lessons inside. Swipe →'. Emoji sparingly. Max 3 hashtags.",
    "tweet": "X/Twitter single tweet (HARD LIMIT: 280 chars including spaces). Punchy. No fluff. One idea only. No hashtags unless essential (max 1).",
    "thread": "X/Twitter thread (3-8 tweets). Number each: '1/' through 'n/'. Each tweet max 280 chars. First tweet = hook/bold claim. Last tweet = summary + CTA. 'RT if you agree' style endings are optional.",
    "feed_caption": "Instagram feed caption (max 2,200 chars). Conversational opener. Visual description optional. 10-15 relevant hashtags at the end after line breaks. Include call-to-action. Emojis welcome but not excessive.",
    "reel_caption": "Instagram Reel caption + script. Caption: 1-2 sentence hook (under 125 chars visible before 'more'). Script: bullet-point talking points for the reel video (on-screen text suggestions). End with hashtags (8-12).",
    "story_sequence": "Instagram Story sequence (3-5 slides). Each slide: 1-3 short lines max (stories are read in 2-3 seconds). Format as:\nSlide 1: [hook/question]\nSlide 2: [key point]\nSlide 3: [CTA or reveal]\nUse polls or questions where natural.",
}
```

The Writer prompt lookup should use `content_type` first, falling back to `platform`:
```python
platform_rules = FORMAT_RULES.get(content_type, FORMAT_RULES.get(platform.lower(), ""))
```

### Backend Change: Add story_sequence to Allowlist

In `backend/routes/content.py` line 26-30:
```python
PLATFORM_CONTENT_TYPES = {
    "linkedin": ["post", "carousel_caption", "article"],
    "x": ["tweet", "thread"],
    "instagram": ["feed_caption", "reel_caption", "story_sequence"],  # add story_sequence
}
```

### Frontend Change: Add Article + Story to InputPanel

In `frontend/src/pages/Dashboard/ContentStudio/InputPanel.jsx`, the `PLATFORMS` constant needs:
```javascript
const PLATFORMS = [
  { id: "linkedin", label: "LinkedIn", icon: Linkedin, color: "#0A66C2",
    types: [
      { id: "post", label: "Post" },
      { id: "article", label: "Article" },
      { id: "carousel_caption", label: "Carousel" }
    ]
  },
  { id: "x", label: "X", icon: Twitter, color: "#1D9BF0",
    types: [{ id: "tweet", label: "Tweet" }, { id: "thread", label: "Thread" }] },
  { id: "instagram", label: "Instagram", icon: Instagram, color: "#E1306C",
    types: [
      { id: "feed_caption", label: "Feed" },
      { id: "reel_caption", label: "Reel" },
      { id: "story_sequence", label: "Story" }
    ]
  },
];
```

**Note:** LinkedIn has 3 types now — the format picker may need to scroll or wrap on narrow screens. Use `flex-wrap` or reduce button padding.

### Real-Time Pipeline Progress (CONT-12)

Already fully implemented:
- `pipeline.py` calls `update_job(job_id, {"current_agent": "commander"})` before each agent stage
- `AgentPipeline.jsx` polls `GET /api/content/job/{id}` every 2 seconds
- `getAgentStatus()` in AgentPipeline.jsx maps `current_agent` to visual states (waiting/running/done)
- All 5 stages (commander, scout, thinker, writer, qc) have `agent_summaries` written back

**Gap:** The frontend AgentPipeline only displays 5 hard-coded agents. No changes needed — the display already works correctly. Only verify that `update_job` calls in the orchestrator actually fire for each stage (they do — confirmed in pipeline.py lines 288, 307, 337, 346, 369).

### Edit + Approve + Schedule (CONT-11)

All three actions are implemented:
- **Edit:** `ContentOutput.jsx` toggles `editing` state, `PlatformShell` renders as textarea
- **Approve:** `handleApprove()` calls `PATCH /api/content/job/{id}/status` with `{status: "approved", edited_content: ...}`
- **Schedule:** `PublishPanel` component (lines 700-end of ContentOutput.jsx) has date/time picker and calls `POST /api/dashboard/schedule/create`

**Gap to verify:** The `POST /api/dashboard/schedule/create` endpoint needs to exist and accept `{job_id, platform, scheduled_at}`. If it does not exist, CONT-11 is blocked on scheduling. Need to verify the endpoint in `backend/routes/` — likely in a `dashboard.py` or separate scheduling route.

### Persona-Aware Voice (CONT-01 through CONT-08)

The persona voice injection is already working:
- `pipeline.py` loads `persona_engines` doc and builds `persona_card`
- `writer.py` injects: `voice_descriptor`, `tone`, `hook_style`, `style_notes`, `regional_english_rules` into the prompt
- `_fetch_style_examples()` retrieves approved past content from Pinecone for style reference
- UOM (Unit of Measure) adaptive directives are injected when available

**Gap:** The persona voice affects the writing style but the format rules are the same for all formats on the same platform. After adding FORMAT_RULES keyed by `content_type`, persona voice will be correctly combined with format-specific rules.

### Platform-Shell Rendering (CONT-09 / CONT-10)

The `ContentOutput.jsx` `PlatformShell` component routes to `LinkedInShell`, `XShell`, or `InstagramShell` based on `job.platform`. The shells render platform-native previews.

**Gap:** No separate shell for LinkedIn article vs LinkedIn post. The `LinkedInShell` renders a LinkedIn-style card which is appropriate for posts but articles should ideally have a different visual treatment. However, the requirement says "header" in the article — the Writer's article rules will produce a bold opening header line in the content, which `LinkedInShell` will render inline. This is acceptable for v3.0. A dedicated `LinkedInArticleShell` is a Phase 33 (Frontend Polish) concern.

Similarly, Instagram story has no dedicated shell — the `InstagramShell` renders a feed-post style layout. For v3.0, using `InstagramShell` for story output is acceptable (stories have no web compose URL anyway). The shell is primarily for preview.

### Character Limit Enforcement

| Format | Hard Limit | Soft Warning | Enforcement Location |
|--------|-----------|-------------|---------------------|
| LinkedIn post | 3,000 | 2,700 | LinkedInShell.jsx (enforced) |
| LinkedIn article | 3,000 | — | Same shell (adequate) |
| LinkedIn carousel | 1,500 | — | FORMAT_RULES instructs Writer |
| X tweet | 280 | 224 (80%) | XShell.jsx (enforced per tweet) |
| X thread | 280/tweet | — | XShell.jsx (enforced) |
| Instagram feed | 2,200 | — | InstagramShell.jsx (enforced) |
| Instagram reel | 2,200 | — | InstagramShell.jsx (adequate) |
| Instagram story | 150/slide | — | FORMAT_RULES instructs Writer; no shell enforcement |

The X tweet 280-char limit is the most critical — the Writer prompt currently says "Single tweet = max 280 chars" in the generic `PLATFORM_RULES["x"]` but the content_type is `tweet` vs `thread`. The XShell enforces the limit during editing. The primary fix is making the Writer's tweet rule explicit about 280 chars being a hard limit.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead |
|---------|-------------|-------------|
| Progress tracking | Custom WebSocket or SSE | Existing 2-second polling with `current_agent` field |
| Content formatting | Custom parsers | Writer prompt rules — instruct the LLM to output correct format |
| Thread parsing | Custom split logic | XShell.jsx already parses `1/ 2/ 3/` format (lines 17-40) |
| Story slide parsing | New parser | Follow same `Slide 1: ... Slide 2: ...` convention; add simple display in InstagramShell |
| Scheduling UI | New date picker | Existing `PublishPanel` in ContentOutput already has date/time picker |
| Character counting | Custom counter | Each Shell component already implements platform-specific counting |

---

## Common Pitfalls

### Pitfall 1: Writer Returns Full Post for Tweet
**What goes wrong:** If FORMAT_RULES for `tweet` doesn't enforce the 280-char limit with extreme clarity, the LLM will write a full paragraph because the persona WRITER_PROMPT says "~{word_count} words" and the Commander sets `estimated_word_count: 100`.
**Why it happens:** The `estimated_word_count` from Commander takes precedence in the Writer's mental model.
**How to avoid:** In the tweet FORMAT_RULE: "HARD LIMIT: 280 characters total including spaces. DO NOT exceed this. Write shorter if needed."
**Warning signs:** Generated tweet is >280 chars in tests.

### Pitfall 2: Article Treated as Post
**What goes wrong:** LinkedIn article generates a short 200-word post-style text because `estimated_word_count` from Commander defaults to 200.
**Why it happens:** Commander sees `content_type: "article"` but its prompt doesn't differentiate word count by content_type.
**How to avoid:** In COMMANDER_PROMPT or in a content_type-based word count lookup: articles should use `estimated_word_count: 800`. Add content_type-aware defaults in Commander or override in the Writer's article FORMAT_RULE.
**Warning signs:** Article is under 400 words.

### Pitfall 3: Story Sequence Not Parsed Into Slides
**What goes wrong:** InstagramShell shows story content as one block instead of separate slide previews.
**Why it happens:** InstagramShell currently renders a single caption `<textarea>`. It doesn't know about `Slide 1: / Slide 2: /` format.
**How to avoid:** Either (a) accept this limitation for v3.0 (story is displayed as a single block in the shell) or (b) add minimal slide-split parsing to InstagramShell similar to XShell's thread parsing. Option (a) is safer for phase scope.
**Warning signs:** Story sequence looks like a single block with newlines in InstagramShell.

### Pitfall 4: InputPanel format picker overflow
**What goes wrong:** LinkedIn now has 3 format options. On narrow screens (mobile) the 3 format buttons overflow the container.
**Why it happens:** Current CSS is `flex gap-1.5` which wraps but looks messy with 3 short items.
**How to avoid:** Add `flex-wrap` and reduce `py-2` to `py-1.5`, or use `text-[9px]` for the format labels. Test at 375px.
**Warning signs:** Format buttons stack vertically or overflow the container on mobile.

### Pitfall 5: story_sequence rejected by backend validation
**What goes wrong:** Frontend sends `content_type: "story_sequence"` but backend `PLATFORM_CONTENT_TYPES` doesn't list it, returning 400.
**Why it happens:** `story_sequence` is new — not yet in the allowlist.
**How to avoid:** Add `"story_sequence"` to `instagram` list in `PLATFORM_CONTENT_TYPES` before testing frontend.
**Warning signs:** `POST /api/content/create` returns 400 "Invalid content type for instagram".

### Pitfall 6: Scheduling endpoint may not exist
**What goes wrong:** `PublishPanel` calls `POST /api/dashboard/schedule/create` but this endpoint may not be implemented.
**Why it happens:** Phase 28 says "User can schedule" (CONT-11) but scheduling implementation belongs to Phase 31 (Smart Scheduling).
**How to avoid:** Verify the endpoint exists in `backend/routes/dashboard.py`. If it does, CONT-11 is already covered. If not, CONT-11 needs a minimal `POST /api/content/schedule` endpoint that just saves `scheduled_at` to the job doc — the actual Celery Beat publishing is Phase 31.
**Warning signs:** PublishPanel "Schedule" button returns 404 or 500 in browser network tab.

---

## Code Examples

### FORMAT_RULES lookup in writer.py
```python
# Source: analysis of writer.py lines 200-205
# Current (broken for multi-format):
platform_rules = PLATFORM_RULES.get(platform.lower(), PLATFORM_RULES["linkedin"])

# Fixed (format-aware):
platform_rules = FORMAT_RULES.get(content_type, FORMAT_RULES.get(platform.lower(), ""))
```

### Commander word count by content_type (commander.py)
```python
# Add content_type-aware defaults to COMMANDER_PROMPT or mock:
WORD_COUNT_DEFAULTS = {
    "post": 220,
    "article": 800,
    "carousel_caption": 120,
    "tweet": 40,         # ~280 chars = ~40-50 words
    "thread": 400,       # 8 tweets x 50 words
    "feed_caption": 180,
    "reel_caption": 150,
    "story_sequence": 80, # 3-5 slides x ~15 words
}
# In run_commander():
estimated_word_count = WORD_COUNT_DEFAULTS.get(content_type, 200)
```

### XShell thread parse pattern (already works)
```javascript
// Source: XShell.jsx lines 17-41 — existing working pattern
const tweetPattern = /(?:^|\n)(?:\d+[\/\)]\s*)/g;
const parts = content.split(tweetPattern).filter(t => t.trim());
```

### Story sequence display (simple approach for v3.0)
```javascript
// In InstagramShell.jsx — minimal story slide split
// Add alongside existing caption rendering:
const isStoryFormat = content && content.includes("Slide 1:");
const storySlides = isStoryFormat
  ? content.split(/Slide \d+:\s*/i).filter(Boolean)
  : null;
```

### Backend schedule endpoint (minimal, if missing)
```python
# In backend/routes/content.py or new route:
class ScheduleRequest(BaseModel):
    job_id: str
    scheduled_at: str  # ISO datetime string

@router.post("/schedule")
async def schedule_content(data: ScheduleRequest, current_user: dict = Depends(get_current_user)):
    job = await db.content_jobs.find_one({"job_id": data.job_id, "user_id": current_user["user_id"]})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    await db.content_jobs.update_one(
        {"job_id": data.job_id},
        {"$set": {"status": "scheduled", "scheduled_at": data.scheduled_at, "updated_at": datetime.now(timezone.utc)}}
    )
    return {"message": "Scheduled", "scheduled_at": data.scheduled_at}
```

---

## State of the Art

| Old Approach | Current Approach | Impact for Phase 28 |
|--------------|------------------|---------------------|
| Generic platform rules (3 keys) | Format-specific rules (9 keys) | Core change required for CONT-09 |
| No story_sequence support | Add to allowlist + Writer rules | New format for CONT-08 |
| 2 LinkedIn formats in UI | 3 LinkedIn formats in UI | Add article button to InputPanel |
| 2 Instagram formats in UI | 3 Instagram formats in UI | Add story button to InputPanel |

**Deprecated/outdated:**
- `PLATFORM_RULES` dict in writer.py: Replace entirely with `FORMAT_RULES` keyed by content_type

---

## Open Questions

1. **Does `POST /api/dashboard/schedule/create` exist?**
   - What we know: `PublishPanel` in ContentOutput.jsx calls this endpoint (line 715 references `/api/dashboard/schedule/optimal-times` and schedule creation)
   - What's unclear: Whether the endpoint is implemented in `backend/routes/dashboard.py`
   - Recommendation: Verify before planning CONT-11. If missing, implement minimal `POST /api/content/schedule` that saves `scheduled_at` to the job document. Full scheduling (Celery Beat auto-publish) is Phase 31.

2. **Should LinkedIn article use a different Shell for preview?**
   - What we know: `PlatformShell` in ContentOutput routes on `platform` not `content_type`, so articles use `LinkedInShell` (card style)
   - What's unclear: Whether v3.0 requires article-specific preview
   - Recommendation: For v3.0, `LinkedInShell` is acceptable for articles. The Writer's article FORMAT_RULE will produce a properly formatted article with a header — the shell just renders it as text. A dedicated article shell is Phase 33 scope.

3. **InstagramShell for story_sequence — render slides or single block?**
   - What we know: `InstagramShell` is designed for feed posts with a square image placeholder + caption
   - What's unclear: Whether story-specific visual treatment is required for CONT-08
   - Recommendation: For v3.0, display story_sequence in `InstagramShell` with minimal slide-split in the caption area. A dedicated story shell (vertical frame, etc.) is Phase 33 scope.

---

## Environment Availability

Step 2.6: SKIPPED — Phase 28 is code/config changes only (Writer prompt strings, route allowlist, frontend constants, tests). No new external tools, services, or CLIs required.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Backend framework | pytest 8.0.0 + pytest-asyncio 0.23.0 |
| Backend config | `backend/pytest.ini` (pythonpath=.) |
| Backend quick run | `cd backend && pytest tests/test_content_sprint3.py -x` |
| Backend full suite | `cd backend && pytest` |
| Frontend framework | Jest (via react-scripts) + React Testing Library |
| Frontend config | `frontend/package.json` (jest config in react-scripts) |
| Frontend quick run | `cd frontend && npm test -- --watchAll=false --testPathPattern=ContentStudio` |
| Frontend full suite | `cd frontend && npm test -- --watchAll=false` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CONT-01 | LinkedIn post generated with persona voice | integration | `pytest tests/test_content_phase28.py::test_linkedin_post_format -x` | ❌ Wave 0 |
| CONT-02 | LinkedIn article has header, 600+ words | integration | `pytest tests/test_content_phase28.py::test_linkedin_article_format -x` | ❌ Wave 0 |
| CONT-03 | LinkedIn carousel caption teases slides | integration | `pytest tests/test_content_phase28.py::test_linkedin_carousel_format -x` | ❌ Wave 0 |
| CONT-04 | X tweet under 280 chars | unit | `pytest tests/test_content_phase28.py::test_x_tweet_under_280 -x` | ❌ Wave 0 |
| CONT-05 | X thread has numbered format | unit | `pytest tests/test_content_phase28.py::test_x_thread_numbered -x` | ❌ Wave 0 |
| CONT-06 | Instagram feed caption has 10+ hashtags | unit | `pytest tests/test_content_phase28.py::test_instagram_feed_hashtags -x` | ❌ Wave 0 |
| CONT-07 | Instagram reel caption + script format | unit | `pytest tests/test_content_phase28.py::test_instagram_reel_format -x` | ❌ Wave 0 |
| CONT-08 | story_sequence creates 3+ slides | unit | `pytest tests/test_content_phase28.py::test_instagram_story_sequence -x` | ❌ Wave 0 |
| CONT-09 | FORMAT_RULES lookup uses content_type | unit | `pytest tests/test_content_phase28.py::test_format_rules_dispatch -x` | ❌ Wave 0 |
| CONT-10 | InputPanel shows 9 format buttons total | unit | `cd frontend && npm test -- --watchAll=false --testPathPattern=ContentStudio` | ✅ (extend existing) |
| CONT-11 | Approve sets status=approved; schedule saves scheduled_at | integration | `pytest tests/test_content_phase28.py::test_approve_and_schedule -x` | ❌ Wave 0 |
| CONT-12 | Pipeline updates current_agent per stage | integration | `pytest tests/test_content_phase28.py::test_pipeline_stage_progression -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `cd backend && pytest tests/test_content_phase28.py -x`
- **Per wave merge:** `cd backend && pytest tests/test_content_phase28.py && cd frontend && npm test -- --watchAll=false --testPathPattern=ContentStudio`
- **Phase gate:** Full suite green: `cd backend && pytest` + `cd frontend && npm test -- --watchAll=false`

### Wave 0 Gaps
- [ ] `backend/tests/test_content_phase28.py` — covers CONT-01 through CONT-12 (backend assertions)
- [ ] Extend `frontend/src/__tests__/pages/ContentStudio.test.jsx` — add tests for 9 format buttons, story type, article type

*(Existing `tests/test_content_sprint3.py` covers basic create/job/status endpoints. Phase 28 tests assert format-specific output characteristics.)*

---

## Sources

### Primary (HIGH confidence)
- Direct code reading: `backend/agents/writer.py` — confirmed PLATFORM_RULES dict, FORMAT_RULES gap
- Direct code reading: `backend/routes/content.py` — confirmed PLATFORM_CONTENT_TYPES, schedule endpoint gap
- Direct code reading: `backend/agents/commander.py` — confirmed no content_type-aware word count
- Direct code reading: `backend/agents/pipeline.py` — confirmed current_agent updates, stage progression
- Direct code reading: `frontend/src/pages/Dashboard/ContentStudio/InputPanel.jsx` — confirmed PLATFORMS constant, missing article + story
- Direct code reading: `frontend/src/pages/Dashboard/ContentStudio/ContentOutput.jsx` — confirmed approve/edit flow, PublishPanel
- Direct code reading: `frontend/src/pages/Dashboard/ContentStudio/Shells/` — confirmed existing shells for linkedin, x, instagram

### Secondary (MEDIUM confidence)
- `CLAUDE.md` section 4 (pipeline flow diagram) — confirmed Commander → Scout → Thinker → Writer → QC order
- `CLAUDE.md` section 7 (features not yet implemented) — confirmed `story_sequence` is missing

### Tertiary (LOW confidence)
- None — all findings from direct code reading

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all confirmed from installed packages in requirements.txt / package.json
- Architecture: HIGH — all confirmed from direct code reading
- Gap analysis: HIGH — confirmed by reading actual code, not assumptions
- Pitfalls: HIGH for tweet 280-char and story_sequence allowlist; MEDIUM for article word count (depends on LLM behavior)

**Research date:** 2026-04-12
**Valid until:** 2026-05-12 (stable codebase, no external moving parts for this phase)
