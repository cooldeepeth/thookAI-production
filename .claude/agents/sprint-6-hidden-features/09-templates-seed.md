# Agent: Template Marketplace — Seed Data + Admin Script
Sprint: 6 | Branch: feat/template-seed-data | PR target: dev
Depends on: Sprint 5 fully merged

## Context
The entire template marketplace (backend/routes/templates.py) is fully built but
the db.templates collection starts completely empty on every deployment. New users
see a blank marketplace, destroying first impressions and the community feature.

## Files You Will Touch
- backend/scripts/seed_templates.py     (CREATE — does not exist, create directory too)
- backend/routes/templates.py           (MODIFY — add admin seed endpoint)

## Files You Must Read First (do not modify)
- backend/routes/templates.py          (read fully — understand template schema)
- backend/database.py                  (understand db access pattern)

## Step 1: Create backend/scripts/seed_templates.py
Create 30 high-quality seed templates. The template schema (read from templates.py)
needs: title, body/hook_structure, platform, category, hook_type, content_pillars,
format_type, author_id (use "system"), is_official: True, upvotes: 0, uses_count: 0.

Create templates across these categories:
- thought_leadership (8 templates) — LinkedIn focus
- storytelling (6 templates) — LinkedIn + Instagram
- how_to (5 templates) — LinkedIn + X
- contrarian (4 templates) — X + LinkedIn
- behind_the_scenes (4 templates) — Instagram + LinkedIn
- social_proof (3 templates) — all platforms

For EACH template, write a real, complete hook structure with:
- A hook line pattern (e.g., "I [did X] for [time period]. Here's what I learned:")
- 3-5 body structure points
- A CTA pattern
- Example filled-in version
- Platform-specific formatting notes (LinkedIn: paragraphs + line breaks, X: concise + thread hint, IG: hook in first line)

The seed script must:
1. Connect to MongoDB using settings from config.py (not hardcoded connection strings)
2. Check if templates collection already has documents — skip if count > 10 (idempotent)
3. Insert all templates with `inserted_at: datetime.utcnow()`
4. Print count of templates inserted
5. Be runnable with: `cd backend && python scripts/seed_templates.py`

## Step 2: Add admin seed endpoint to templates.py
Add a protected endpoint (admin-only):
POST /api/templates/admin/seed

Guard: check if current_user has `role: "admin"` in their user document.
If user is not admin: return HTTP 403.
If templates already exist (count > 10): return {"message": "Already seeded", "count": N}
If empty: run the seed logic and return {"message": "Seeded", "inserted": N}

This allows re-seeding via API without SSH access to the server.

## Definition of Done
- `python backend/scripts/seed_templates.py` inserts 30 templates and exits cleanly
- Running it twice does NOT insert duplicates (idempotent)
- Admin seed endpoint returns 403 for non-admin users
- PR created to dev with title: "feat: seed template marketplace with 30 curated starter templates"