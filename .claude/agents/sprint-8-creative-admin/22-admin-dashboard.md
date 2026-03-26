# Agent: Admin Dashboard — Platform Stats + User Management
Sprint: 8 | Branch: feat/admin-dashboard | PR target: dev
Depends on: All previous sprints (admin views everything — needs all data to exist)
⚠️ FLAG THIS PR FOR OWNER REVIEW before merge

## Context
There is no admin interface. The owner has no way to see platform-wide stats (DAU,
content generated, revenue, errors), manage users (change tier, reset credits,
ban), or inspect broken jobs — without direct MongoDB access. This is critical for
operating the platform in production.

## Files You Will Touch
- backend/routes/admin.py               (CREATE)
- backend/server.py                     (MODIFY — register admin router)
- backend/auth_utils.py                 (MODIFY — add is_admin dependency)
- frontend/src/pages/Admin.jsx          (CREATE)
- frontend/src/pages/AdminUsers.jsx     (CREATE)

## Files You Must Read First (do not modify)
- backend/auth_utils.py                (read fully — understand get_current_user pattern)
- backend/routes/dashboard.py          (read — understand DB query patterns for stats)
- backend/services/credits.py         (TIER_CONFIGS — understand tier structures)
- backend/database.py                 (db access pattern)

## ⚠️ Security Note
Register the admin router with:
  app.include_router(admin_router, prefix="/api/admin", include_in_schema=False)
The include_in_schema=False hides all admin endpoints from the public
/docs and /redoc Swagger UI pages.

## Step 1: Add admin role to auth_utils.py
Add a new dependency function:
```python
async def require_admin(current_user = Depends(get_current_user)):
    """Dependency that requires admin role."""
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=403,
            detail="Admin access required"
        )
    return current_user
```
To make a user admin: set `role: "admin"` in their users document in MongoDB.
Document this in a comment: `# Set via MongoDB: db.users.updateOne({email: "..."}, {$set: {role: "admin"}})`

## Step 2: Create backend/routes/admin.py
All routes require `Depends(require_admin)`.

### Platform stats endpoints
```python
# GET /api/admin/stats/overview
# Returns:
# {
#   total_users: int,
#   new_users_today: int,
#   new_users_7d: int,
#   active_users_today: int,    # users who generated content today
#   total_content_jobs: int,
#   content_jobs_today: int,
#   total_published: int,
#   published_today: int,
#   subscription_breakdown: {free: N, pro: N, studio: N, agency: N},
#   revenue_estimate: float     # calculated from subscription counts × tier prices
# }

# GET /api/admin/stats/errors
# Returns: last 50 jobs with status "failed" across all users
# Fields: job_id, user_id, platform, error_message, created_at

# GET /api/admin/stats/celery
# Returns: Redis queue lengths for content and media tasks (use redis-py)
# {worker_queue_length: int, beat_queue_length: int, failed_tasks: int}
```

### User management endpoints
```python
# GET /api/admin/users?page=1&search=email@example.com&tier=pro
# Returns paginated user list with: user_id, email, name, tier, credits,
#   onboarding_completed, created_at, last_active_at, total_jobs

# GET /api/admin/users/{user_id}
# Full user detail: all fields + content job count + persona summary

# POST /api/admin/users/{user_id}/tier
# Body: { "tier": "pro" | "studio" | "agency" | "free" }
# Overrides subscription tier without Stripe (for manual grants, testing, support)

# POST /api/admin/users/{user_id}/credits
# Body: { "credits": 500, "reason": "support_grant" }
# Adds credits to a user's account

# POST /api/admin/users/{user_id}/suspend
# Sets user active: False — prevents login

# POST /api/admin/users/{user_id}/unsuspend
# Sets user active: True
```

### Content management
```python
# GET /api/admin/content?status=failed&platform=linkedin&user_id=X&page=1
# Returns filtered content jobs across all users

# POST /api/admin/content/{job_id}/retry
# Re-queues a failed content job through the pipeline
```

## Step 3: Create frontend/src/pages/Admin.jsx
Route: `/admin` (guard: only accessible if user.role === "admin")

Overview dashboard with:
1. Stats cards: Total Users, Active Today, Content Generated Today, Published Today
2. Subscription pie chart (free/pro/studio/agency breakdown) — use recharts (already likely installed, check package.json)
3. Recent errors table: last 10 failed jobs with user email and error
4. Celery queue health: green/yellow/red indicator

Navigation sidebar to:
- /admin/users (user management)

## Step 4: Create frontend/src/pages/AdminUsers.jsx
Route: `/admin/users`

Table with:
1. Search by email input
2. Filter by tier dropdown
3. Columns: Email, Name, Tier (with inline edit dropdown), Credits, Jobs, Joined, Actions
4. Actions per row: "Grant Credits" (opens modal with amount input), "Change Tier", "Suspend"
5. Pagination (20 per page)

Register `/admin` and `/admin/users` routes with admin guard in the app router.
The admin guard in the frontend: check `user.role === "admin"` from auth state,
redirect to `/dashboard` if not admin.

## Definition of Done
- GET /api/admin/stats/overview returns real platform stats
- Tier override and credit grant endpoints work
- Admin user can access /admin and /admin/users in frontend
- Non-admin users are redirected away from /admin routes
- PR flagged for owner review before merge
- PR created to dev: "feat: admin dashboard — platform stats and user management"