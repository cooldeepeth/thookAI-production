# Agent: Media Storage Hardening — Block /tmp in Production
Sprint: 2 | Branch: fix/media-storage-hardening | PR target: dev
Depends on: Sprint 1 fully merged (can run in parallel with Agent 3)

## Context
If Cloudflare R2 is not configured, uploads.py silently saves files to /tmp and
stores the local path as the media URL in MongoDB. On all cloud deployments
(Render, Railway, Fly.io), /tmp is ephemeral — files are lost on restart, and the
stored URL becomes a permanent dead link. This is a silent data corruption bug.

## Files You Will Touch
- backend/routes/uploads.py     (MODIFY)
- backend/server.py             (MODIFY — add R2 startup warning)
- backend/services/media_storage.py  (MODIFY — improve error handling)

## Files You Must Read First (do not modify)
- backend/config.py             (settings.r2 — has_r2() method)
- backend/routes/uploads.py     (read fully — understand current fallback logic)
- backend/services/media_storage.py  (read fully — understand R2 client setup)

## Step 1: Block /tmp fallback in production (uploads.py)
Find the section in uploads.py where it checks for R2 credentials and falls back
to /tmp. Replace the fallback logic with:

```python
if not settings.r2.has_r2():
    if settings.app.is_production:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "media_storage_unavailable",
                "message": "Media storage is not configured. Contact support.",
                "fix": "Set R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_BUCKET_NAME, R2_PUBLIC_URL in environment"
            }
        )
    else:
        # Development: allow /tmp fallback but log a loud warning
        logger.warning(
            "⚠️  R2 not configured — using /tmp fallback. "
            "Files will be lost on restart. Set R2 env vars for persistence."
        )
        # Continue with existing /tmp logic
```

## Step 2: Add startup warning in server.py
In the lifespan startup section (where database indexes are checked), add:

```python
# Check media storage
if not settings.r2.has_r2():
    if settings.app.is_production:
        logger.error(
            "CRITICAL: R2 media storage not configured in production! "
            "File uploads will fail. Set R2_* environment variables."
        )
    else:
        logger.warning(
            "R2 media storage not configured — uploads use /tmp fallback in dev mode."
        )
```

## Step 3: Improve media_storage.py error handling
In the R2 upload function, ensure:
1. If the boto3 client fails to initialise (bad credentials), it raises a clear
   ValueError with message "R2 credentials invalid — check R2_ACCESS_KEY_ID and R2_SECRET_ACCESS_KEY"
2. If an upload fails, it logs the full error and raises HTTPException 500
   (not silently returning None or a local path)
3. The function docstring documents the required env vars

## Step 4: Add R2 status to /api/health endpoint (server.py)
In the health check endpoint, add:
```python
health_status["checks"]["media_storage"] = "r2_configured" if settings.r2.has_r2() else "not_configured"
```

## Definition of Done
- `ENVIRONMENT=production` + R2 unconfigured → uploads return HTTP 503
- `ENVIRONMENT=development` + R2 unconfigured → uploads work with /tmp and log warning
- Health endpoint returns `media_storage` key
- PR created to dev with title: "fix: block /tmp media fallback in production"