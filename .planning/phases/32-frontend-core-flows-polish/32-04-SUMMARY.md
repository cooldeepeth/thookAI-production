---
phase: 32-frontend-core-flows-polish
plan: 04
status: complete
---

# Plan 32-04: ContentStudio A11y + Responsive Polish — SUMMARY

## Files Modified
- `frontend/src/pages/Dashboard/ContentStudio/InputPanel.jsx`
- `frontend/src/pages/Dashboard/ContentStudio/index.jsx`
- `frontend/src/pages/Dashboard/ContentStudio/AgentPipeline.jsx`

## Files Verified (no changes)
- `frontend/src/pages/Dashboard/ContentStudio/ContentOutput.jsx` — Phase 28 schedule action already in place at lines 1097, 1185, 1235, 1255.

## Changes — InputPanel.jsx (video toggle a11y)
The video toggle button now has:
- `type="button"` (was missing)
- `role="switch"`
- `aria-checked={generateVideo}` (boolean)
- `aria-label="Generate video with content"`
- `onKeyDown` handler for Enter and Space keys (with `e.preventDefault()` and the gating `videoEnabled` check)
- `focus-ring` appended to the className (only when not disabled)

## Changes — ContentStudio/index.jsx (responsive layout)
- Outer container className: removed `h-[calc(100vh-4rem)] overflow-hidden`, added `md:h-[calc(100vh-4rem)] overflow-x-hidden`. Mobile no longer forces full viewport height; horizontal scroll prevented at 375px.
- Left panel (InputPanel wrapper) className: now `w-full md:w-[400px] flex-shrink-0 h-auto md:h-[calc(100vh-4rem)] overflow-y-auto border-b md:border-b-0 md:border-r border-white/5`. Mobile gets `h-auto`, desktop gets the calc height.
- Right panel (output area) className: now `flex-1 min-h-[50vh] md:h-[calc(100vh-4rem)] overflow-y-auto`. Mobile guarantees a 50vh minimum; desktop matches the left panel.

## Changes — AgentPipeline.jsx (aria-live)
- Wrapped the agent status cards container with `aria-live="polite" aria-label="Generation progress"` so screen readers announce progress updates as the pipeline advances.

## Acceptance Criteria — Verification
```
$ grep -n 'role="switch"|aria-checked|video-toggle|onKeyDown' InputPanel.jsx
186: role="switch"
187: aria-checked={generateVideo}
190: onKeyDown={(e) => {
197: data-testid="video-toggle"

$ grep -n "overflow-x-hidden|h-auto md:" index.jsx
165: <div ... md:h-[calc(100vh-4rem)] overflow-x-hidden ...>
167: <div ... h-auto md:h-[calc(100vh-4rem)] ...>

$ grep -n 'aria-live="polite"' AgentPipeline.jsx
42: <div className="space-y-3" aria-live="polite" aria-label="Generation progress">

$ grep -n "schedule-content-btn|schedule-datetime-input|schedule-submit-btn|schedule/content" ContentOutput.jsx
1097: const res = await apiFetch(`/api/dashboard/schedule/content`, { ... })
1185: data-testid="schedule-content-btn"
1235: data-testid="schedule-datetime-input"
1255: data-testid="schedule-submit-btn"
```

All four files parse cleanly via @babel/parser.

## Requirements Satisfied
- FEND-03 — Video toggle is now a true switch widget keyboard-navigable via Tab + Space/Enter.
- FEND-06 — ContentStudio no longer overflows horizontally at 375px; left/right panels stack and adapt height.
- FEND-07 — `aria-live="polite"` announces pipeline progress; `role="switch"` + `aria-checked` give the video toggle proper semantics.

## Notes
- Originally scheduled as a parallel worktree subagent in Wave 2. Completed inline by the orchestrator.
- ContentOutput.jsx required no changes — Phase 28 (CONT-11) already shipped the schedule action with all three data-testids and the correct PATCH endpoint.
