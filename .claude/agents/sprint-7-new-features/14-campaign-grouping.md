# Agent: Campaign Grouping — Group Content Under Projects
Sprint: 7 | Branch: feat/campaign-grouping | PR target: dev
Depends on: Sprint 6 fully merged

## Context
Users generate many posts but have no way to organise them into campaigns or
projects. There is no concept of a campaign, content series (beyond series_planner),
or project group. This makes managing launch campaigns, event content, or topic
clusters impossible.

## Files You Will Touch
- backend/routes/campaigns.py           (CREATE — does not exist)
- backend/routes/content.py             (MODIFY — add campaign_id field to jobs)
- backend/server.py                     (MODIFY — register campaigns router)
- frontend/src/pages/Campaigns.jsx      (CREATE)
- frontend/src/components/CampaignCard.jsx (CREATE)

## Files You Must Read First
- backend/routes/content.py            (understand content_job schema)
- backend/database.py                  (db access pattern)
- frontend/src/                        (understand routing and page structure)

## Step 1: Create backend/routes/campaigns.py
Schema for db.campaigns:
```python
{
  campaign_id: str,
  user_id: str,
  name: str,
  description: str,
  platform: str | list,  # target platforms
  status: "active" | "paused" | "completed",
  start_date: datetime | None,
  end_date: datetime | None,
  goal: str,  # e.g., "product launch", "thought leadership", "event promotion"
  content_count: int,  # denormalised count for performance
  created_at: datetime,
  updated_at: datetime
}
```

Endpoints:
- `POST /api/campaigns` — create campaign
- `GET /api/campaigns` — list user's campaigns
- `GET /api/campaigns/{id}` — get campaign + its content jobs
- `PUT /api/campaigns/{id}` — update campaign details
- `DELETE /api/campaigns/{id}` — soft delete (set status: "archived")
- `POST /api/campaigns/{id}/add-content/{job_id}` — assign a content job to campaign
- `DELETE /api/campaigns/{id}/content/{job_id}` — remove content from campaign
- `GET /api/campaigns/{id}/stats` — aggregate stats (total posts, published, scheduled, draft)

## Step 2: Add campaign_id to content jobs
In content.py, in the content generation request model, add optional `campaign_id: str = None`.
When a job is created with campaign_id, store it in db.content_jobs.
On campaign deletion, set campaign_id to None on all associated jobs (don't delete jobs).

## Step 3: Frontend Campaigns page
Create a Campaigns page with:
1. Campaign cards showing name, status, content count, platform tags
2. "New Campaign" button → modal with name, description, platform, goal, optional dates
3. Clicking a campaign card → campaign detail view showing all content in that campaign
4. Drag-to-assign (or a simple "Add to Campaign" dropdown on ContentCard)
5. Campaign stats: posts planned vs. published vs. scheduled

Register route `/campaigns` in the app router.

## Definition of Done
- CRUD endpoints for campaigns exist and work
- Content jobs accept and store campaign_id
- Frontend has Campaigns page with create/view/manage flows
- PR created to dev with title: "feat: campaign grouping for content organisation"