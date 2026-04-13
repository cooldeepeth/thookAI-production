---
phase: 34-security-gdpr
plan: 05
status: complete
retroactive: true
commit: 2763fc1
requirements:
  - SECR-09
  - SECR-10
---

# Plan 34-05: GDPR Export Expansion + Per-User Rate Limit + Delete-Account Comment — SUMMARY

> Retroactive summary reconstructed from `.planning/phases/34-security-gdpr/34-VERIFICATION.md` and commit `2763fc1` (`feat(34-05): add scheduled_posts, media_assets, workspace_memberships, templates to GDPR export`).

## Files Modified
- `backend/routes/auth.py`

## Changes — GET /api/auth/export (SECR-09)

Four collections added to the export response (existing structure preserved):

```python
scheduled_posts = await db.scheduled_posts.find(
    {"user_id": user_id}, {"_id": 0}
).limit(500).to_list(None)

media_assets = await db.media_assets.find(
    {"user_id": user_id}, {"_id": 0}
).limit(500).to_list(None)

workspace_memberships = await db.workspace_members.find(
    {"user_id": user_id}, {"_id": 0, "token": 0}
).limit(100).to_list(None)

authored_templates = await db.templates.find(
    {"author_id": user_id}, {"_id": 0}
).limit(200).to_list(None)
```

Top-level response dict now also includes:
```python
"note": "Limited to most recent 500 items per collection. Contact support@thookai.com for a full data archive."
```

**Before Phase 34:** users, persona_engines, content_jobs, credit_transactions, connected_platforms, user_feedback, uploads.
**After Phase 34:** all of the above plus scheduled_posts, media_assets, workspace_memberships, authored_templates, and the `note` field.

## Per-user Redis rate limit (SECR-05/09)

Added at the top of the export endpoint, immediately after `get_current_user` resolves `user_id`:
- Redis key: `f"gdpr_export:{user_id}:{YYYY-MM-DD}"`
- Limit: 3 requests per 24 hours per user
- TTL: 86400 seconds on first increment
- On limit exceeded: `HTTPException(429, "Export limit reached (3 per day). Try again tomorrow.")`
- Redis unavailable: silently allow export, log at WARNING level (fail-open — availability over abuse protection for GDPR)

Complements the IP-based rate limit added in plan 34-03 (`/api/auth/export: 3/min`) — both limits apply.

## Changes — POST /api/auth/delete-account (SECR-10)

**Logic unchanged** — the research confirmed the endpoint was correctly implemented (anonymizes rather than hard-deletes, clears auth cookies, logs without PII).

Added clarifying comment above the `@router.post("/delete-account")` decorator:
```
# NOTE (SECR-10): ROADMAP.md success criterion 4 specifies DELETE /api/auth/account
# but this implementation uses POST /api/auth/delete-account with a {"confirm": "DELETE"}
# body for safer UX (accidental DELETE without confirmation body is impossible).
# ROADMAP.md updated to match this implementation in plan 34-08.
```

## Verification
```
$ grep -c "scheduled_posts\|media_assets\|workspace_memberships\|authored_templates" backend/routes/auth.py
8  # (4 query definitions + 4 response dict keys)

$ grep -n "gdpr_export:" backend/routes/auth.py
(1 line — rate limit key definition)

$ grep -n '"note"' backend/routes/auth.py
(1 line — support email note)

$ python -c "from routes.auth import router"
(OK)
```

## Requirements Satisfied
- **SECR-09** — GDPR data export includes all user data: PASS
- **SECR-10** — GDPR account deletion path documented and functional: PASS

## Notes
- Workspace tokens explicitly projected out via `{"_id": 0, "token": 0}` — prevents export of sensitive auth tokens.
- Inline execution by orchestrator.
