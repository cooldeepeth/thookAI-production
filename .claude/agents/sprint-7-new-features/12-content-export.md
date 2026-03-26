# Agent: Content Export — Copy, CSV, and Plain Text
Sprint: 7 | Branch: feat/content-export | PR target: dev
Depends on: Sprint 6 fully merged

## Context
Users cannot export their generated content. No copy-to-clipboard, no CSV download,
no plain text export. For a content creation platform, this is a basic missing feature.

## Files You Will Touch
- backend/routes/content.py              (MODIFY — add export endpoints)
- frontend/src/components/ContentCard.jsx (MODIFY — add export buttons, check filename)
- frontend/src/pages/ContentHistory.jsx  (MODIFY — add bulk export, check filename)

## Files You Must Read First
- backend/routes/content.py             (read fully — understand content job structure)
- frontend/src/pages/                   (list to find ContentHistory page filename)
- frontend/src/components/              (list to find ContentCard component filename)

## Step 1: Add export endpoints to content.py
```python
# GET /api/content/{job_id}/export?format=text|json|clipboard
# Returns formatted content based on format param

# GET /api/content/export/bulk?format=csv&platform=linkedin&status=approved&from_date=X&to_date=Y
# Returns CSV download of multiple posts
# CSV columns: date, platform, content_type, content, status, was_edited, virality_score
```

For the CSV endpoint, use Python's `csv` module (stdlib — no new dependency).
Return with `Content-Disposition: attachment; filename="thookai-export-{date}.csv"` header.

## Step 2: Add copy button to ContentCard component
Add a copy-to-clipboard icon button on each content card that:
1. Copies the final_content to clipboard using navigator.clipboard.writeText()
2. Shows a "Copied!" toast notification for 2 seconds (use existing toast component)
3. Works for both mobile and desktop

## Step 3: Add bulk export to ContentHistory page
Add an "Export" button in the ContentHistory page header that:
1. Opens a small dropdown with options: "Export as CSV", "Export as Text"
2. CSV: triggers download from GET /api/content/export/bulk?format=csv
3. Text: builds a plain text file client-side from the loaded content list
4. Allow filter by platform and date range before export

## Definition of Done
- GET /api/content/{id}/export returns formatted content
- GET /api/content/export/bulk returns valid CSV download
- ContentCard has working copy button
- ContentHistory has Export dropdown
- PR created to dev with title: "feat: content export — copy, CSV, and bulk download"