# Agent: Video Agent — Wire Into Content Pipeline
Sprint: 8 | Branch: feat/video-pipeline-wiring | PR target: dev
Depends on: Sprint 1 merged (Celery running), Sprint 4 merged (billing gates video)

## Context
agents/video.py is fully implemented with Luma, Kling, Runway, Pika, and HeyGen
support — but it is NEVER called from the main content pipeline or any scheduled
flow. Video generation only exists as a dead endpoint. Additionally, HeyGen talking
head videos require a pre-created avatar_id that users have no way to create.
There is also no user flow to request video content at generation time.

## Files You Will Touch
- backend/routes/content.py              (MODIFY — add video generation request option)
- backend/agents/pipeline.py            (MODIFY — add optional video step at end)
- backend/agents/video.py              (MODIFY — add avatar creation + fix mock fallbacks)
- backend/tasks/media_tasks.py          (MODIFY — add async video generation task)
- backend/routes/persona.py            (MODIFY — add avatar creation endpoint)
- frontend/src/pages/ContentCreate.jsx  (MODIFY — add "Generate video" toggle, check filename)

## Files You Must Read First (do not modify)
- backend/agents/video.py              (read fully — all providers, mock patterns)
- backend/routes/content.py            (find ContentGenerationRequest model)
- backend/agents/pipeline.py           (find end of pipeline — after QC step)
- backend/tasks/media_tasks.py         (understand async media task pattern)
- backend/services/credits.py         (TIER_CONFIGS — video credit costs)

## Step 1: Add video request flag to content generation
In content.py, find the `ContentGenerationRequest` Pydantic model. Add:
```python
generate_video: bool = False
video_style: str = "cinematic"  # cinematic | talking_head | slideshow | abstract
video_provider: str = "auto"    # auto | luma | kling | runway
```

## Step 2: Add optional video step to pipeline.py
At the very end of the pipeline (after QC, before returning result), add:

```python
# Optional video generation step
if job_request.get("generate_video") and job.get("status") == "reviewing":
    video_tier_access = current_user.get("subscription_tier") in ("studio", "agency")
    if not video_tier_access:
        logger.info(f"Video generation skipped — user {user_id} on free/pro tier")
    else:
        # Dispatch async video task — do not block pipeline
        from tasks.media_tasks import generate_video_for_job
        generate_video_for_job.apply_async(
            args=[job_id, user_id, final_content, job_request.get("video_style", "cinematic")],
            countdown=2  # slight delay to let job save complete
        )
        logger.info(f"Video generation dispatched for job {job_id}")
```

## Step 3: Add generate_video_for_job Celery task to media_tasks.py
```python
@shared_task(bind=True, max_retries=2)
def generate_video_for_job(self, job_id: str, user_id: str, content: str, style: str):
    """
    Generates a video for a content job asynchronously.
    1. Updates job status: adds video_status: "generating"
    2. Calls video.generate_video(content, style, user_id)
    3. On success: stores video URL in db.content_jobs[job_id].video_url
                   stores in db.media_assets
                   sets video_status: "ready"
    4. On failure: sets video_status: "failed", logs error
    5. Creates a notification (if notification service available): "Your video is ready"
    """
```

## Step 4: Fix mock fallbacks in video.py
For every provider that falls back to `mock_video_generation()`, replace with:
```python
if not self._valid_key(provider_key):
    logger.warning(f"{provider} API key not configured — video generation unavailable")
    return {
        "error": "provider_not_configured",
        "provider": provider,
        "message": f"Set {provider.upper()}_API_KEY to enable video generation"
    }
```
Remove all calls to `mock_video_generation()` that return fake URLs.

## Step 5: Add HeyGen avatar creation endpoint to persona.py
```python
# POST /api/persona/avatar/create
# Body: { "photo_url": str }  — URL of user's photo (must be R2 URL or public URL)
# Tier gate: studio or agency
# Calls: POST https://api.heygen.com/v2/photo_avatar/avatar/create
# Headers: X-Api-Key: {heygen_key}
# Stores returned avatar_id in db.persona_engines[user_id].heygen_avatar_id

# GET /api/persona/avatar
# Returns: { "has_avatar": bool, "avatar_id": str|None, "preview_url": str|None }
```

## Step 6: Frontend — video toggle in ContentCreate
Find the content creation page/component. Add a toggle at the bottom of the form:
"Also generate a video version" (disabled/locked for free/pro with upgrade tooltip).
When enabled, show video style selector (cinematic / talking head / slideshow).
After content is approved and video is generating, show a "Video: Generating..." 
status badge on the content card that polls `GET /api/content/{id}` for video_status.

## Definition of Done
- ContentGenerationRequest accepts generate_video flag
- Pipeline dispatches video task for studio/agency users when requested
- No mock_video_generation() calls remain — replaced with clear "not configured" errors
- HeyGen avatar creation endpoint exists in persona.py
- PR created to dev: "feat: wire video agent into content pipeline + avatar creation"