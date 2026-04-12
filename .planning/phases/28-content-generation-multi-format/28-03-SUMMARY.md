---
phase: 28-content-generation-multi-format
plan: "03"
subsystem: frontend/content-studio
tags: [content-studio, format-picker, instagram-shell, agent-pipeline, ui, tests]
dependency_graph:
  requires: [28-01, 28-02]
  provides: [9-format-buttons-ui, story-slide-rendering, agent-name-bold]
  affects: [InputPanel.jsx, InstagramShell.jsx, AgentPipeline.jsx, ContentStudio.test.jsx]
tech_stack:
  added: []
  patterns: [story-slide-detection, conditional-render-pattern, framer-motion-stagger]
key_files:
  created: []
  modified:
    - frontend/src/pages/Dashboard/ContentStudio/InputPanel.jsx
    - frontend/src/pages/Dashboard/ContentStudio/Shells/InstagramShell.jsx
    - frontend/src/pages/Dashboard/ContentStudio/AgentPipeline.jsx
    - frontend/src/__tests__/pages/ContentStudio.test.jsx
decisions:
  - "Used py-1 uniformly for all format buttons (not conditional) — minimal height difference, simpler code, prevents overflow at 375px"
  - "story slides in edit mode use single textarea over full content — no per-slide inputs (v3.0 simplification per UI-SPEC)"
  - "storySlides detection placed outside useEffect so it re-computes on every render without lag"
metrics:
  duration_minutes: 15
  completed_date: "2026-04-12"
  tasks_completed: 3
  files_modified: 4
---

# Phase 28 Plan 03: Expand ContentStudio to 9 Formats Summary

**One-liner:** 9-format ContentStudio with LinkedIn Article + Instagram Story buttons, story-sequence slide-block rendering in InstagramShell, and AgentPipeline agent name upgraded to font-bold (700).

## What Was Built

### Task 1: InputPanel PLATFORMS constant expanded to 9 formats (commit: 29fcb3a)

- `PLATFORMS` constant now has 3 types for LinkedIn (post, article, carousel_caption) and 3 types for Instagram (feed_caption, reel_caption, story_sequence), X unchanged at 2 (tweet, thread)
- Format button container uses `flex-wrap` to prevent overflow on narrow screens
- Format buttons use `py-1` uniformly (down from `py-2`) per UI-SPEC responsive contract
- All 9 format buttons have correct `data-testid="content-type-{id}"` via existing pattern

### Task 2: InstagramShell story slide rendering + AgentPipeline font weight (commit: a490270)

- Added `isStoryFormat` detection: `content.includes("Slide 1:")`
- Added `storySlides` parsing: `content.split(/Slide \d+:\s*/i).filter(s => s.trim())`
- Story preview renders as `motion.div` slide blocks with `data-testid="story-slide-{idx}"`, `role="listitem"`, stagger animation (`delay: idx * 0.05`)
- Slide container has `data-testid="story-slides-container"` and `role="list"`
- Slide badge: "Slide {n} of {total}" in `text-xs font-mono text-zinc-400` per copywriting contract
- Image placeholder subtitle changes to "Vertical story format (9:16)" when `isStoryFormat`
- Edit mode for stories: existing single `<textarea>` kept (no per-slide split)
- Hashtag chips updated from `py-0.5` to `py-1` per UI-SPEC spacing contract
- AgentPipeline agent name: `font-semibold` → `font-bold` per UI-SPEC typography contract

### Task 3: ContentStudio tests for all 9 formats (commit: fa7eedd)

- Added `nine_format_types_total_present`: verifies post, carousel_caption, and article all visible on default LinkedIn platform
- Added `instagram_story_format_button_present`: clicks Instagram tab, asserts `content-type-story_sequence` present
- Added `linkedin_article_format_button_present`: asserts `content-type-article` visible immediately on default LinkedIn
- All 11 tests pass (8 pre-existing + 3 new), 0 regressions

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Test command in plan uses `react-scripts test` which bypasses craco config**

- **Found during:** Task 3 verification
- **Issue:** Plan's verify command `npx react-scripts test` bypasses craco's `jest.configure` which sets up `setupFiles: ['<rootDir>/src/jest-polyfills.js']` and the MSW module mappers. Without craco, MSW 2.x fails with `TextEncoder is not defined`.
- **Fix:** Used `npm test` (which runs `craco test`) for verification. No code changes needed — the existing `jest-polyfills.js` and craco config already handled this correctly.
- **Files modified:** None (used correct test command)
- **Commit:** N/A (fix was using correct command, not code change)

**2. [Rule 1 - Cosmetic] setupTests.js quote style normalised by post-edit formatter**

- **Found during:** Task 3 — post-edit hook reformatted single quotes to double quotes
- **Fix:** Accepted the formatter's output; no functional change
- **Files modified:** `frontend/src/setupTests.js`
- **Commit:** fa7eedd (included in Task 3 commit)

## Known Stubs

None. All 9 format buttons are wired to real `onContentTypeChange` handlers. Story slide rendering is production-ready. No placeholder data.

## Verification Results

```
grep article|story_sequence InputPanel.jsx       → FOUND (lines 12, 34)
grep storySlides InstagramShell.jsx              → FOUND (lines 15, 137, 139, 150)
grep font-bold AgentPipeline.jsx                 → FOUND (line 74)
npm test --testPathPattern=ContentStudio         → 11/11 PASS (0 failures)
```

## Self-Check: PASSED
