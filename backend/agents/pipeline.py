import asyncio
import logging
from datetime import datetime, timezone
from database import db
from agents.commander import run_commander
from agents.scout import run_scout
from agents.thinker import run_thinker
from agents.writer import run_writer
from agents.qc import run_qc

logger = logging.getLogger(__name__)

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


async def run_agent_pipeline(job_id: str, user_id: str, platform: str, content_type: str, raw_input: str):
    """Main pipeline orchestrator. Runs all 5 agents sequentially, updates DB at each step."""
    try:
        # Load persona (fallback to default if not onboarded)
        persona = await db.persona_engines.find_one({"user_id": user_id}, {"_id": 0})
        persona_card = {**DEFAULT_PERSONA, **(persona.get("card", {}) if persona else {})}
        # Inject creator name if available from users collection
        user = await db.users.find_one({"user_id": user_id}, {"_id": 0, "name": 1})
        if user:
            persona_card["creator_name"] = user.get("name", "the creator")

        # COMMANDER — strategy
        await update_job(job_id, {"current_agent": "commander", "status": "running"})
        commander_output = await asyncio.wait_for(
            run_commander(raw_input, platform, content_type, persona_card), timeout=25.0
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

        # THINKER — strategy + structure
        await update_job(job_id, {"current_agent": "thinker"})
        thinker_output = await asyncio.wait_for(
            run_thinker(raw_input, commander_output, scout_output, persona_card), timeout=30.0
        )
        await update_job(job_id, {
            "agent_outputs.thinker": thinker_output,
            "agent_summaries.thinker": f"Angle: {thinker_output.get('angle', '')[:80]}"
        })

        # WRITER — voice-matched copy
        await update_job(job_id, {"current_agent": "writer"})
        writer_output = await asyncio.wait_for(
            run_writer(platform, content_type, commander_output, scout_output, thinker_output, persona_card), timeout=40.0
        )
        draft = writer_output.get("draft", "") if isinstance(writer_output, dict) else writer_output
        await update_job(job_id, {
            "agent_outputs.writer": writer_output if isinstance(writer_output, dict) else {"draft": draft},
            "final_content": draft,
            "agent_summaries.writer": f"{len(draft.split())} words drafted in your voice"
        })

        # QC — persona match + AI risk scoring
        await update_job(job_id, {"current_agent": "qc"})
        qc_output = await asyncio.wait_for(
            run_qc(draft, persona_card, platform, content_type), timeout=25.0
        )
        pass_fail = "PASS" if qc_output.get("overall_pass") else "NEEDS REVIEW"
        await update_job(job_id, {
            "agent_outputs.qc": qc_output,
            "qc_score": qc_output,
            "current_agent": "done",
            "status": "reviewing",
            "agent_summaries.qc": f"Persona Match {qc_output.get('personaMatch', 0)}/10 · AI Risk {qc_output.get('aiRisk', 0)}/100 · {pass_fail}"
        })

    except asyncio.CancelledError:
        await update_job(job_id, {"status": "error", "current_agent": "error", "error": "Pipeline was cancelled"})
    except Exception as e:
        logger.error(f"Pipeline error for job {job_id}: {e}")
        await update_job(job_id, {"status": "error", "current_agent": "error", "error": str(e)})
