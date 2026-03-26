# Agent: Template Marketplace — Full Frontend UI
Sprint: 6 | Branch: feat/template-marketplace-frontend | PR target: dev
Depends on: Sprint 6 Agent 9 merged (seed data must exist first)
Note: This agent works on the FRONTEND (frontend/src/)

## Context
backend/routes/templates.py has complete marketplace endpoints — browse, filter,
search, upvote, use template — but there is zero frontend UI for any of it.
Users cannot discover or use the template marketplace at all.

## Files You Will Touch
- frontend/src/pages/Templates.jsx          (CREATE)
- frontend/src/pages/TemplateDetail.jsx     (CREATE)
- frontend/src/components/TemplateCard.jsx  (CREATE)
- frontend/src/api/templates.js             (CREATE — or add to existing API client)
- frontend/src/App.jsx (or router file)     (MODIFY — add /templates routes)

## Files You Must Read First (do not modify)
- backend/routes/templates.py              (read ALL endpoints — understand full API)
- frontend/src/                            (list directory — understand project structure)
- frontend/src/pages/                      (list — understand existing page patterns)
- frontend/src/api/                        (list — find existing API client pattern to replicate)
- frontend/src/components/                 (list — find what UI components are available)

## Step 1: Create API client functions (templates.js or add to existing api client)
```javascript
// Replicate the exact pattern used in other API files in frontend/src/api/

export const getTemplates = (filters) =>
  // GET /api/templates?category=X&platform=Y&hook_type=Z&search=Q&page=N
  
export const getTemplate = (templateId) =>
  // GET /api/templates/{id}
  
export const upvoteTemplate = (templateId) =>
  // POST /api/templates/{id}/upvote
  
export const useTemplate = (templateId) =>
  // POST /api/templates/{id}/use  — increments uses_count, returns template data
  
export const createTemplate = (templateData) =>
  // POST /api/templates  — user publishes their own template
  
export const getMyTemplates = () =>
  // GET /api/templates/my  — user's own published templates
```

## Step 2: Create TemplateCard component
A card component showing:
- Template title and category badge
- Platform tags (LinkedIn / X / Instagram icons)
- Hook type label
- First 3 lines of the hook structure (truncated with "...")
- Upvote button with count (heart or thumbs up icon)
- Uses count ("Used 247 times")
- Author name (show "ThookAI Official" for is_official templates)
- "Use This Template" button

## Step 3: Create Templates page (marketplace listing)
Layout:
1. Header: "Template Marketplace" + "Share Your Template" button (opens CreateTemplateModal)
2. Filter bar: tabs for All / LinkedIn / X / Instagram, dropdown for Category, search input
3. Featured row: top 3 most-used official templates (highlighted)
4. Grid: TemplateCards with infinite scroll or pagination (20 per page)
5. Empty state if no results match filters

## Step 4: Create TemplateDetail page
Route: `/templates/:id`
Shows:
1. Full template with complete hook structure, body patterns, CTA examples
2. Filled-in example post
3. Platform formatting notes
4. Upvote button (toggle)
5. "Use This Template" button — pre-fills the content creation form with this template
   On click: navigate to content creation page with template data in state/URL params

## Step 5: Create Template in Content Creation
In the content creation page (find the file), add a "Start from Template" option:
- Small button "Browse Templates" near the top
- Clicking opens a compact template picker modal (simplified TemplateCard list)
- Selecting a template pre-fills the content form hook/structure area

## Step 6: Create Template Submit flow
"Share Your Template" button opens a modal:
- Fields: title, category (dropdown), platform (multi-select), hook_type, 
  hook_structure (textarea), example_post (textarea)
- Submit calls POST /api/templates
- On success: show "Template submitted for review" toast

Register `/templates` and `/templates/:id` routes in the app router.

## Definition of Done
- /templates page loads with filters, search, and TemplateCard grid
- Upvote button works (toggles, updates count)
- "Use This Template" navigates to content creation with template pre-filled
- TemplateDetail page renders full template
- PR created to dev: "feat: template marketplace frontend — browse, filter, use, share"