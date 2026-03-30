from __future__ import annotations

import asyncio
import base64
import logging
import mimetypes
import re
from datetime import datetime, timezone
from html import unescape
from pathlib import Path
from typing import List, Optional

import httpx

from database import db
from agents.commander import run_commander
from agents.scout import run_scout
from agents.thinker import run_thinker
from agents.writer import run_writer
from agents.qc import run_qc
from agents.anti_repetition import get_anti_repetition_context, build_anti_repetition_prompt
from services.persona_refinement import get_pattern_fatigue_shield

logger = logging.getLogger(__name__)


def _extract_title_and_text(html: str) -> tuple[str, str]:
    m = re.search(
        r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']*)["\']',
        html,
        re.I,
    )
    if m:
        title = unescape(m.group(1).strip())
    else:
        m2 = re.search(r"<title[^>]*>([^<]+)</title>", html, re.I)
        title = unescape(m2.group(1).strip()) if m2 else ""
    text = re.sub(r"(?is)<script[^>]*>.*?</script>", " ", html)
    text = re.sub(r"(?is)<style[^>]*>.*?</style>", " ", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()[:500]
    return title, text


async def _read_local_image_data_url(path: str, content_type: str) -> str:
    def read_bytes():
        return Path(path).read_bytes()

    raw = await asyncio.to_thread(read_bytes)
    b64 = base64.b64encode(raw).decode("ascii")
    ct = (content_type or "").split(";")[0].strip() or mimetypes.guess_type(path)[0] or "image/jpeg"
    return f"data:{ct};base64,{b64}"


async def _build_upload_media_context(upload_ids: List[str], user_id: str) -> tuple[str, list]:
    """Returns (system suffix for commander/writer, image refs for commander vision)."""
    if not upload_ids:
        return "", []
    lines: list[str] = []
    image_urls: list[str] = []

    async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
        for uid in upload_ids:
            doc = await db.uploads.find_one({"upload_id": uid, "user_id": user_id})
            if not doc:
                continue
            ct = doc.get("context_type") or ""
            if ct == "image":
                url = doc.get("url") or ""
                if url.startswith("/"):
                    try:
                        data_url = await _read_local_image_data_url(url, doc.get("content_type", ""))
                        image_urls.append(data_url)
                    except OSError:
                        logger.warning("Could not read local image %s", url)
                else:
                    image_urls.append(url)
            elif ct == "video":
                u = doc.get("url", "")
                lines.append(
                    f"User has provided a video at {u}. Describe its likely content "
                    "and incorporate it into the post."
                )
            elif ct == "document":
                fn = doc.get("filename", "document")
                u = doc.get("url", "")
                lines.append(
                    f"User uploaded a document ({fn}) at {u}. Use it as reference for the post where relevant."
                )
            elif ct == "link":
                url = doc.get("url", "")
                title = doc.get("title") or url
                excerpt = ""
                try:
                    r = await client.get(url)
                    r.raise_for_status()
                    _, excerpt = _extract_title_and_text(r.text[:200_000])
                except Exception as e:
                    logger.debug("Link fetch for pipeline failed %s: %s", url, e)
                lines.append(
                    f"User shared a link: {url}\nPage title: {title}\nContent excerpt: {excerpt}"
                )

    suffix = ""
    if lines:
        suffix = "Additional context from user-provided media:\n" + "\n".join(lines)
    return suffix, image_urls


DEFAULT_PERSONA = {
    "writing_voice_descriptor": "Professional thought leader",
    "content_niche_signature": "Professional growth and industry insights",
    "inferred_audience_profile": "Professionals and decision-makers",
    "tone": "Professional yet conversational",
    "hook_style": "Bold statement",
    "regional_english": "US",
    "content_goal": "Build personal brand",
    "writing_style_notes": ["Write with authenticity", "Be specific over generic"],
    "content_pillars": ["Industry insights", "Personal lessons"]
}


async def update_job(job_id: str, data: dict):
    data["updated_at"] = datetime.now(timezone.utc)
    await db.content_jobs.update_one({"job_id": job_id}, {"$set": data})


PIPELINE_TIMEOUT_SECONDS = 180.0  # 3-minute global timeout


async def run_agent_pipeline(
    job_id: str,
    user_id: str,
    platform: str,
    content_type: str,
    raw_input: str,
    upload_ids: Optional[List[str]] = None,
    generate_video: bool = False,
    video_style: str = "cinematic",
) -> None:
    """Main entry point for content generation pipeline.

    Uses the LangGraph orchestrator for hierarchical execution with debate
    and quality loops.  Falls back to the legacy linear pipeline if the
    orchestrator fails to initialise.

    A global timeout of ``PIPELINE_TIMEOUT_SECONDS`` (180 s) wraps both
    the orchestrator and the legacy path.  If any agent hangs, the job is
    marked as ``error`` with a clear timeout message.
    """
    try:
        await asyncio.wait_for(
            _run_agent_pipeline_inner(
                job_id=job_id,
                user_id=user_id,
                platform=platform,
                content_type=content_type,
                raw_input=raw_input,
                upload_ids=upload_ids,
                generate_video=generate_video,
                video_style=video_style,
            ),
            timeout=PIPELINE_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
        logger.error(
            "Pipeline timed out after %ss for job %s", PIPELINE_TIMEOUT_SECONDS, job_id
        )
        await update_job(job_id, {
            "status": "error",
            "current_agent": "error",
            "error": "Content generation timed out. Please try again.",
        })
        logger.info("Job %s marked as error after timeout — returning early", job_id)
        return


async def _run_agent_pipeline_inner(
    job_id: str,
    user_id: str,
    platform: str,
    content_type: str,
    raw_input: str,
    upload_ids: Optional[List[str]] = None,
    generate_video: bool = False,
    video_style: str = "cinematic",
) -> None:
    """Inner dispatch — try orchestrator, fall back to legacy."""
    try:
        from agents.orchestrator import run_orchestrated_pipeline
        await run_orchestrated_pipeline(
            job_id=job_id,
            user_id=user_id,
            platform=platform,
            content_type=content_type,
            raw_input=raw_input,
            upload_ids=upload_ids,
        )
    except ImportError:
        logger.warning("LangGraph orchestrator not available, falling back to legacy pipeline")
        await run_agent_pipeline_legacy(
            job_id=job_id,
            user_id=user_id,
            platform=platform,
            content_type=content_type,
            raw_input=raw_input,
            upload_ids=upload_ids,
            generate_video=generate_video,
            video_style=video_style,
        )
    except Exception as e:
        logger.error(f"Orchestrator failed: {e}, falling back to legacy pipeline")
        await run_agent_pipeline_legacy(
            job_id=job_id,
            user_id=user_id,
            platform=platform,
            content_type=content_type,
            raw_input=raw_input,
            upload_ids=upload_ids,
            generate_video=generate_video,
            video_style=video_style,
        )


async def run_agent_pipeline_legacy(
    job_id: str,
    user_id: str,
    platform: str,
    content_type: str,
    raw_input: str,
    upload_ids: Optional[List[str]] = None,
    generate_video: bool = False,
    video_style: str = "cinematic",
):
    """Legacy linear pipeline orchestrator. Runs all 5 agents sequentially, updates DB at each step."""
    try:
        # Load persona (fallback to default if not onboarded)
        persona = await db.persona_engines.find_one({"user_id": user_id}, {"_id": 0})
        persona_card = {**DEFAULT_PERSONA, **(persona.get("card", {}) if persona else {})}
        # Inject creator name if available from users collection
        user = await db.users.find_one({"user_id": user_id}, {"_id": 0, "name": 1})
        if user:
            persona_card["creator_name"] = user.get("name", "the creator")

        # Get anti-repetition context before Commander runs
        anti_rep_context = await get_anti_repetition_context(user_id)
        anti_rep_prompt = build_anti_repetition_prompt(anti_rep_context) if anti_rep_context.get("has_patterns") else ""

        uids = upload_ids or []
        media_suffix, commander_images = await _build_upload_media_context(uids, user_id)

        # COMMANDER — strategy (with anti-repetition context)
        await update_job(job_id, {"current_agent": "commander", "status": "running"})
        commander_output = await asyncio.wait_for(
            run_commander(
                raw_input,
                platform,
                content_type,
                persona_card,
                anti_rep_prompt,
                media_system_suffix=media_suffix,
                image_urls=commander_images or None,
            ),
            timeout=25.0,
        )
        await update_job(job_id, {
            "agent_outputs.commander": commander_output,
            "agent_summaries.commander": f"Strategy: {commander_output.get('primary_angle', '')[:80]}"
        })

        # SCOUT — research
        await update_job(job_id, {"current_agent": "scout"})
        research_needed = commander_output.get("research_needed", True)
        if research_needed:
            scout_output = await asyncio.wait_for(
                run_scout(raw_input, commander_output.get("research_query", raw_input), platform), timeout=25.0
            )
        else:
            scout_output = {"findings": "No external research required for this content.", "citations": [], "sources_found": 0}
        await update_job(job_id, {
            "agent_outputs.scout": scout_output,
            "agent_summaries.scout": f"{scout_output.get('sources_found', 0)} sources · research complete"
        })

        # FATIGUE SHIELD — gather pattern fatigue data before Thinker
        fatigue_data = {}
        try:
            # FIXED: add timeout to prevent fatigue shield from blocking pipeline
            fatigue_data = await asyncio.wait_for(
                get_pattern_fatigue_shield(user_id), timeout=2.0
            )
            # FIXED: use correct key names from get_pattern_fatigue_shield() response
            shield_status = fatigue_data.get("shield_status")
            if shield_status and shield_status != "healthy":
                logger.info(
                    "Fatigue shield active for %s: status=%s, risk_factors=%s",
                    user_id, shield_status, fatigue_data.get("risk_factors", [])
                )
        except (asyncio.TimeoutError, Exception) as e:
            logger.warning("Fatigue shield check failed (non-fatal): %s", e)

        # THINKER — strategy + structure
        await update_job(job_id, {"current_agent": "thinker"})
        thinker_output = await asyncio.wait_for(
            run_thinker(raw_input, commander_output, scout_output, persona_card, fatigue_context=fatigue_data, user_id=user_id), timeout=30.0
        )
        await update_job(job_id, {
            "agent_outputs.thinker": thinker_output,
            "agent_summaries.thinker": f"Angle: {thinker_output.get('angle', '')[:80]}"
        })

        # WRITER — voice-matched copy
        await update_job(job_id, {"current_agent": "writer"})
        writer_output = await asyncio.wait_for(
            run_writer(
                platform,
                content_type,
                commander_output,
                scout_output,
                thinker_output,
                persona_card,
                media_system_suffix=media_suffix,
                user_id=user_id,
            ),
            timeout=40.0,
        )
        draft = writer_output.get("draft", "") if isinstance(writer_output, dict) else writer_output
        await update_job(job_id, {
            "agent_outputs.writer": writer_output if isinstance(writer_output, dict) else {"draft": draft},
            "final_content": draft,
            "agent_summaries.writer": f"{len(draft.split())} words drafted in your voice"
        })

        # QC — persona match + AI risk + repetition scoring
        await update_job(job_id, {"current_agent": "qc"})
        qc_output = await asyncio.wait_for(
            run_qc(draft, persona_card, platform, content_type, user_id=user_id), timeout=25.0
        )
        pass_fail = "PASS" if qc_output.get("overall_pass") else "NEEDS REVIEW"
        rep_level = qc_output.get("repetition_level", "none")
        await update_job(job_id, {
            "agent_outputs.qc": qc_output,
            "qc_score": qc_output,
            "agent_summaries.qc": f"Persona {qc_output.get('personaMatch', 0)}/10 · AI Risk {qc_output.get('aiRisk', 0)}/100 · Rep: {rep_level} · {pass_fail}"
        })
        doc = await db.content_jobs.find_one({"job_id": job_id}, {"final_content": 1})
        if doc is not None and doc.get("final_content") is not None:
            now = datetime.now(timezone.utc)
            await db.content_jobs.update_one(
                {"job_id": job_id},
                {"$set": {
                    "status": "completed",
                    "current_agent": "done",
                    "completed_at": now,
                    "updated_at": now,
                }},
            )

            # VIDEO STEP — dispatch async video generation if requested
            if generate_video and draft:
                try:
                    # Tier-gate: only studio and agency users can generate video
                    user_doc = await db.users.find_one({"user_id": user_id}, {"subscription_tier": 1})
                    user_tier = user_doc.get("subscription_tier", "free") if user_doc else "free"
                    if user_tier in ("studio", "agency"):
                        from tasks.media_tasks import generate_video_for_job
                        from tasks import is_redis_configured
                        if is_redis_configured():
                            generate_video_for_job.apply_async(
                                args=[job_id, user_id, draft, video_style],
                                countdown=2,
                            )
                            await update_job(job_id, {"video_status": "queued"})
                            logger.info("Video generation queued for job %s (style=%s)", job_id, video_style)
                        else:
                            logger.warning("Video requested for job %s but Redis/Celery not available", job_id)
                            await update_job(job_id, {
                                "video_status": "skipped",
                                "video_error": "Task queue not available"
                            })
                    else:
                        logger.info("Video requested for job %s but user tier '%s' is not eligible", job_id, user_tier)
                        await update_job(job_id, {
                            "video_status": "skipped",
                            "video_error": f"Video generation requires Studio or Agency tier (current: {user_tier})"
                        })
                except Exception as vid_err:
                    logger.warning("Failed to dispatch video generation for job %s: %s", job_id, vid_err)
                    await update_job(job_id, {"video_status": "failed", "video_error": str(vid_err)})

            # Notify user that content generation is complete
            try:
                from services.notification_service import create_notification

                await create_notification(
                    user_id=user_id,
                    type="job_completed",
                    title=f"Your {platform} content is ready",
                    body=f"Your {content_type} has been generated and is ready for review.",
                    metadata={
                        "job_id": job_id,
                        "platform": platform,
                        "content_type": content_type,
                    },
                )
            except Exception as notif_err:
                logger.warning("Failed to create job completion notification: %s", notif_err)

            # Fire outbound webhooks for job.completed
            try:
                from services.webhook_service import fire_webhook

                asyncio.create_task(fire_webhook(user_id, "job.completed", {
                    "job_id": job_id,
                    "platform": platform,
                    "content_type": content_type,
                    "status": "completed",
                    "qc_score": qc_output.get("personaMatch"),
                    "completed_at": now.isoformat(),
                }))
            except Exception as wh_err:
                logger.warning("Failed to fire job.completed webhook: %s", wh_err)

           

    except asyncio.CancelledError:
        await update_job(job_id, {"status": "error", "current_agent": "error", "error": "Pipeline was cancelled"})
    except Exception as e:
        logger.error(f"Pipeline error for job {job_id}: {e}")
        await update_job(job_id, {"status": "error", "current_agent": "error", "error": str(e)})
