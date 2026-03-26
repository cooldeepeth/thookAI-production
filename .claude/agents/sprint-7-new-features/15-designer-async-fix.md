# Agent: Designer Agent — Fix Async Blocking + Attach Images to Jobs
Sprint: 7 | Branch: fix/designer-async-fix | PR target: dev
Depends on: Sprint 1 (Celery must be configured)

## Context
agents/designer.py has two bugs:
1. The image polling loop (5-minute timeout) runs synchronously when Celery is
   unavailable, which BLOCKS FastAPI's async event loop, freezing the entire server
   under concurrent requests.
2. Generated images are stored in db.media_assets but are NEVER linked back to the
   content job's media_assets field — the post goes out without the image.
   Also, Midjourney integration uses an unofficial proxy API (fragile, violates ToS).

## Files You Will Touch
- backend/agents/designer.py            (MODIFY)
- backend/routes/content.py             (MODIFY — attach generated images to jobs)

## Files You Must Read First
- backend/agents/designer.py           (read fully — all generation paths)
- backend/routes/content.py            (find where media_assets is stored on jobs)
- backend/tasks/media_tasks.py         (understand async media task pattern)

## Step 1: Fix the blocking poll loop in designer.py
Find the image generation polling loop. Wrap it in `asyncio.wait_for`:
```python
try:
    result = await asyncio.wait_for(
        _poll_for_image_result(task_id, provider),
        timeout=60.0  # 60 second timeout, not 5 minutes
    )
except asyncio.TimeoutError:
    logger.error(f"Image generation timed out after 60s for task {task_id}")
    return {"error": "generation_timeout", "task_id": task_id}
```

All polling functions that were sync must be converted to async using
`asyncio.sleep(2)` between polls instead of `time.sleep(2)`.

## Step 2: Remove Midjourney unofficial proxy
Find the Midjourney section in designer.py. Replace the unofficial proxy call
(`https://api.userapi.ai`) with a graceful unavailable response:
```python
async def _generate_midjourney(self, prompt: str) -> dict:
    # Midjourney does not have an official API suitable for production use.
    # Redirect to fal.ai Flux Pro as equivalent quality alternative.
    logger.warning("Midjourney requested but unavailable — routing to Flux Pro")
    return await self._generate_fal_flux(prompt)
```

## Step 3: Auto-attach generated images to content jobs
After a successful image generation (wherever the result URL is obtained), add:
```python
if result.get("url") and job_id:
    await db.content_jobs.update_one(
        {"job_id": job_id},
        {"$push": {"media_assets": {
            "url": result["url"],
            "type": "image",
            "provider": provider,
            "generated_at": datetime.utcnow()
        }}}
    )
    logger.info(f"Image attached to job {job_id}: {result['url']}")
```

The designer's generate function must accept `job_id: str = None` as a parameter
so callers can pass it in. Update the call site in content.py to pass job_id.

## Definition of Done
- No `time.sleep()` calls remain in designer.py (all converted to asyncio.sleep)
- Midjourney proxy URL (`userapi.ai`) does not appear in designer.py
- Image generation attaches result URL to content job's media_assets
- PR created to dev with title: "fix: designer agent async blocking + image auto-attachment"