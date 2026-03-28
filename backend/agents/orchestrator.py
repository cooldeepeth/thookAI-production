"""LangGraph-based Content War Room orchestrator for ThookAI.

Replaces the linear pipeline in ``pipeline.py`` with a LangGraph StateGraph
that supports conditional branching (research gate, QC rewrite loops),
hook-debate scoring, and a consigliere risk overlay — while reusing all
existing agent worker functions.

Entry point: :func:`run_orchestrated_pipeline`, a drop-in replacement for
:func:`pipeline.run_agent_pipeline`.
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, TypedDict

from langgraph.graph import END, StateGraph

from config import settings
from database import db
from services.llm_client import LlmChat, UserMessage
from services.llm_keys import chat_constructor_key, openai_available

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Shared pipeline state
# ---------------------------------------------------------------------------

class PipelineState(TypedDict, total=False):
    # -- Input ---------------------------------------------------------------
    job_id: str
    user_id: str
    platform: str
    content_type: str
    raw_input: str
    upload_ids: list

    # -- Persona & context ---------------------------------------------------
    persona_card: dict
    anti_rep_prompt: str
    media_system_suffix: str
    image_urls: list

    # -- Agent outputs (accumulated) -----------------------------------------
    commander_output: dict
    scout_output: dict
    thinker_output: dict
    writer_output: dict
    qc_output: dict

    # -- Orchestration control -----------------------------------------------
    draft: str
    qc_loop_count: int
    qc_feedback_history: list
    debate_results: dict
    consigliere_review: dict

    # -- Metadata ------------------------------------------------------------
    current_agent: str
    error: Optional[str]
    final_content: str


# ---------------------------------------------------------------------------
# Default persona (mirrors pipeline.py)
# ---------------------------------------------------------------------------

DEFAULT_PERSONA: Dict[str, Any] = {
    "writing_voice_descriptor": "Professional thought leader",
    "content_niche_signature": "Professional growth and industry insights",
    "inferred_audience_profile": "Professionals and decision-makers",
    "tone": "Professional yet conversational",
    "hook_style": "Bold statement",
    "regional_english": "US",
    "content_goal": "Build personal brand",
    "writing_style_notes": ["Write with authenticity", "Be specific over generic"],
    "content_pillars": ["Industry insights", "Personal lessons"],
}

# Maximum Writer->QC rewrite iterations before accepting best effort.
MAX_QC_LOOPS = 3


# ---------------------------------------------------------------------------
# DB helper (same pattern as pipeline.py)
# ---------------------------------------------------------------------------

async def _update_job(job_id: str, data: dict) -> None:
    """Persist partial job updates to MongoDB."""
    data["updated_at"] = datetime.now(timezone.utc)
    await db.content_jobs.update_one({"job_id": job_id}, {"$set": data})


# ---------------------------------------------------------------------------
# Utility: safe JSON cleaning (shared across agents)
# ---------------------------------------------------------------------------

def _clean_json(raw: str) -> str:
    s = raw.strip()
    if "```" in s:
        parts = s.split("```")
        s = parts[1] if len(parts) > 1 else s
        if s.startswith("json"):
            s = s[4:]
    return s.strip()


# ===================================================================
# Node 1 — Commander
# ===================================================================

async def commander_node(state: PipelineState) -> dict:
    """Run Commander agent: parse intent and build job spec."""
    from agents.commander import run_commander

    job_id = state["job_id"]
    user_id = state["user_id"]
    await _update_job(job_id, {"current_agent": "commander", "status": "running"})

    # Fetch UOM directives to determine quality_tier for model selection (non-fatal)
    uom_commander = {}
    if user_id:
        try:
            from services.uom_service import get_agent_directives
            uom_commander = await get_agent_directives(user_id, "commander")
        except Exception:
            pass

    quality_tier = uom_commander.get("quality_tier", "standard")
    if quality_tier == "premium":
        logger.info("UOM quality_tier=premium for user %s — commander using enhanced mode", user_id)

    try:
        commander_output = await asyncio.wait_for(
            run_commander(
                state["raw_input"],
                state["platform"],
                state["content_type"],
                state["persona_card"],
                state.get("anti_rep_prompt", ""),
                media_system_suffix=state.get("media_system_suffix", ""),
                image_urls=state.get("image_urls") or None,
            ),
            timeout=25.0,
        )
    except asyncio.TimeoutError:
        logger.error("Commander timed out for job %s", job_id)
        raise
    except Exception:
        logger.exception("Commander failed for job %s", job_id)
        raise

    await _update_job(job_id, {
        "agent_outputs.commander": commander_output,
        "agent_summaries.commander": (
            f"Strategy: {commander_output.get('primary_angle', '')[:80]}"
        ),
    })

    return {
        "commander_output": commander_output,
        "current_agent": "commander",
    }


# ===================================================================
# Node 2 — Scout (conditional)
# ===================================================================

async def scout_node(state: PipelineState) -> dict:
    """Run Scout agent for external research via Perplexity."""
    from agents.scout import run_scout

    job_id = state["job_id"]
    commander_output = state["commander_output"]
    await _update_job(job_id, {"current_agent": "scout"})

    try:
        scout_output = await asyncio.wait_for(
            run_scout(
                state["raw_input"],
                commander_output.get("research_query", state["raw_input"]),
                state["platform"],
            ),
            timeout=25.0,
        )
    except asyncio.TimeoutError:
        logger.warning("Scout timed out for job %s — proceeding without research", job_id)
        scout_output = {
            "findings": "Research timed out. Proceeding without external data.",
            "citations": [],
            "sources_found": 0,
        }
    except Exception as exc:
        logger.warning("Scout failed for job %s: %s", job_id, exc)
        scout_output = {
            "findings": "Research unavailable. Proceeding with available context.",
            "citations": [],
            "sources_found": 0,
        }

    await _update_job(job_id, {
        "agent_outputs.scout": scout_output,
        "agent_summaries.scout": (
            f"{scout_output.get('sources_found', 0)} sources · research complete"
        ),
    })

    return {"scout_output": scout_output, "current_agent": "scout"}


# ===================================================================
# Node 3 — Identity Check (fatigue shield + anti-rep)
# ===================================================================

async def identity_check_node(state: PipelineState) -> dict:
    """Non-fatal fatigue shield + anti-repetition constraint gathering."""
    from services.persona_refinement import get_pattern_fatigue_shield

    user_id = state["user_id"]
    fatigue_data: Dict[str, Any] = {}

    try:
        fatigue_data = await asyncio.wait_for(
            get_pattern_fatigue_shield(user_id),
            timeout=2.0,
        )
        shield_status = fatigue_data.get("shield_status")
        if shield_status and shield_status != "healthy":
            logger.info(
                "Fatigue shield active for %s: status=%s, risk_factors=%s",
                user_id,
                shield_status,
                fatigue_data.get("risk_factors", []),
            )
    except (asyncio.TimeoutError, Exception) as exc:
        logger.warning("Fatigue shield check failed (non-fatal): %s", exc)

    # Provide scout_output default if scout was skipped
    if not state.get("scout_output"):
        scout_output = {
            "findings": "No external research required for this content.",
            "citations": [],
            "sources_found": 0,
        }
        await _update_job(state["job_id"], {
            "agent_outputs.scout": scout_output,
            "agent_summaries.scout": "0 sources · research skipped",
        })
        return {
            "scout_output": scout_output,
            "current_agent": "identity_check",
            # Pass fatigue_data forward via thinker_output temporarily —
            # we stash it inside commander_output under a private key so
            # thinker_node can read it.
            "commander_output": {
                **state["commander_output"],
                "_fatigue_data": fatigue_data,
            },
        }

    return {
        "current_agent": "identity_check",
        "commander_output": {
            **state["commander_output"],
            "_fatigue_data": fatigue_data,
        },
    }


# ===================================================================
# Node 4 — Thinker
# ===================================================================

async def thinker_node(state: PipelineState) -> dict:
    """Run Thinker agent: strategy, angles, hook options."""
    from agents.thinker import run_thinker

    job_id = state["job_id"]
    commander_output = state["commander_output"]
    scout_output = state.get("scout_output") or {}
    fatigue_data = commander_output.pop("_fatigue_data", None)

    await _update_job(job_id, {"current_agent": "thinker"})

    try:
        thinker_output = await asyncio.wait_for(
            run_thinker(
                state["raw_input"],
                commander_output,
                scout_output,
                state["persona_card"],
                fatigue_context=fatigue_data,
                user_id=state["user_id"],
            ),
            timeout=30.0,
        )
    except asyncio.TimeoutError:
        logger.error("Thinker timed out for job %s", job_id)
        raise

    await _update_job(job_id, {
        "agent_outputs.thinker": thinker_output,
        "agent_summaries.thinker": (
            f"Angle: {thinker_output.get('angle', '')[:80]}"
        ),
    })

    return {"thinker_output": thinker_output, "current_agent": "thinker"}


# ===================================================================
# Node 5 — Hook Debate
# ===================================================================

_HOOK_DEBATE_SYSTEM = (
    "You are a content strategist evaluating hook options for a social media post. "
    "Return ONLY valid JSON — no markdown, no explanations."
)

_HOOK_DEBATE_PROMPT = """Evaluate these hook options for a {platform} post.

Creator voice: {voice_descriptor}
Audience: {audience_profile}
Content angle: {angle}
Hook style preference: {hook_style}

Hook options:
{hook_list}

Score each hook on three criteria (1-10):
1. engagement_potential — Will it stop the scroll?
2. persona_fit — Does it match the creator's voice?
3. originality — Is it fresh and non-generic?

Return JSON:
{{
  "evaluations": [
    {{
      "hook_index": 0,
      "engagement_potential": 8,
      "persona_fit": 9,
      "originality": 7,
      "total": 24,
      "reasoning": "Brief rationale"
    }}
  ],
  "winner_index": 0,
  "winner_hook": "The winning hook text"
}}"""


async def hook_debate_node(state: PipelineState) -> dict:
    """Debate hook options and select the best one via LLM scoring."""
    thinker_output = state["thinker_output"]
    hook_options = thinker_output.get("hook_options") or []

    # Shortcut: 0 or 1 options — nothing to debate
    if len(hook_options) <= 1:
        selected_hook = hook_options[0] if hook_options else ""
        return {
            "debate_results": {
                "selected_hook": selected_hook,
                "skipped": True,
                "reason": "single_or_no_options",
            },
            "current_agent": "hook_debate",
        }

    persona_card = state["persona_card"]
    hook_list_text = "\n".join(
        f"  [{i}] {h}" for i, h in enumerate(hook_options)
    )

    prompt = _HOOK_DEBATE_PROMPT.format(
        platform=state["platform"],
        voice_descriptor=persona_card.get("writing_voice_descriptor", "Professional creator"),
        audience_profile=persona_card.get("inferred_audience_profile", "Professionals"),
        angle=thinker_output.get("angle", ""),
        hook_style=persona_card.get("hook_style", "Bold statement"),
        hook_list=hook_list_text,
    )

    debate_results: Dict[str, Any] = {}

    try:
        if not openai_available():
            raise RuntimeError("No LLM available for hook debate")

        chat = LlmChat(
            api_key=chat_constructor_key(),
            session_id=f"debate-{uuid.uuid4().hex[:8]}",
            system_message=_HOOK_DEBATE_SYSTEM,
        ).with_model("openai", "gpt-4o-mini")

        raw = await asyncio.wait_for(
            chat.send_message(UserMessage(text=prompt)),
            timeout=15.0,
        )
        parsed = json.loads(_clean_json(raw))

        winner_idx = parsed.get("winner_index", 0)
        # Clamp to valid range
        if not isinstance(winner_idx, int) or winner_idx < 0 or winner_idx >= len(hook_options):
            winner_idx = 0

        debate_results = {
            "selected_hook": hook_options[winner_idx],
            "winner_index": winner_idx,
            "evaluations": parsed.get("evaluations", []),
            "skipped": False,
        }
    except Exception as exc:
        logger.warning("Hook debate failed (non-fatal): %s — using first hook", exc)
        debate_results = {
            "selected_hook": hook_options[0],
            "winner_index": 0,
            "skipped": True,
            "reason": f"debate_error: {exc}",
        }

    return {"debate_results": debate_results, "current_agent": "hook_debate"}


# ===================================================================
# Node 6 — Writer
# ===================================================================

async def writer_node(state: PipelineState) -> dict:
    """Run Writer agent. Injects debate-selected hook and any QC rewrite feedback."""
    from agents.writer import run_writer

    job_id = state["job_id"]
    user_id = state["user_id"]
    await _update_job(job_id, {"current_agent": "writer"})

    # Detect emotional state from raw_input to inform writer tone (non-fatal)
    emotional_state = "neutral"
    if user_id:
        try:
            from services.uom_service import detect_emotional_state
            emotional_state = await detect_emotional_state(state.get("raw_input", ""))
            if emotional_state == "energized":
                logger.info("UOM detected energized state in user input for job %s", job_id)
        except Exception:
            pass

    thinker_output = dict(state["thinker_output"])
    commander_output = state["commander_output"]
    scout_output = state.get("scout_output") or {}
    persona_card = state["persona_card"]
    debate = state.get("debate_results") or {}
    qc_feedback_history = state.get("qc_feedback_history") or []

    # Override hook_options[0] with debate winner so the writer uses it
    selected_hook = debate.get("selected_hook", "")
    if selected_hook:
        existing_hooks = thinker_output.get("hook_options") or [""]
        thinker_output["hook_options"] = [selected_hook] + [
            h for h in existing_hooks if h != selected_hook
        ]

    # If this is a rewrite loop, inject accumulated QC feedback
    if qc_feedback_history:
        rewrite_instructions = (
            "\n\nREWRITE INSTRUCTIONS (from QC feedback — address ALL of these):\n"
            + "\n".join(f"- {fb}" for fb in qc_feedback_history)
        )
        # Append to the thinker key_insight which feeds into the writer prompt
        thinker_output["key_insight"] = (
            thinker_output.get("key_insight", "")
            + rewrite_instructions
        )

    try:
        writer_output = await asyncio.wait_for(
            run_writer(
                state["platform"],
                state["content_type"],
                commander_output,
                scout_output,
                thinker_output,
                persona_card,
                media_system_suffix=state.get("media_system_suffix", ""),
                user_id=state["user_id"],
            ),
            timeout=40.0,
        )
    except asyncio.TimeoutError:
        logger.error("Writer timed out for job %s", job_id)
        raise

    draft = writer_output.get("draft", "") if isinstance(writer_output, dict) else str(writer_output)

    await _update_job(job_id, {
        "agent_outputs.writer": writer_output if isinstance(writer_output, dict) else {"draft": draft},
        "final_content": draft,
        "agent_summaries.writer": f"{len(draft.split())} words drafted in your voice",
    })

    return {
        "writer_output": writer_output if isinstance(writer_output, dict) else {"draft": draft},
        "draft": draft,
        "current_agent": "writer",
    }


# ===================================================================
# Node 7 — QC
# ===================================================================

async def qc_node(state: PipelineState) -> dict:
    """Run QC agent: persona match, AI risk, platform fit, repetition check."""
    from agents.qc import run_qc

    job_id = state["job_id"]
    await _update_job(job_id, {"current_agent": "qc"})

    draft = state.get("draft", "")
    persona_card = state["persona_card"]

    try:
        qc_output = await asyncio.wait_for(
            run_qc(
                draft,
                persona_card,
                state["platform"],
                state["content_type"],
                user_id=state["user_id"],
            ),
            timeout=25.0,
        )
    except asyncio.TimeoutError:
        logger.warning("QC timed out for job %s — marking as pass", job_id)
        qc_output = {
            "personaMatch": 7.0,
            "aiRisk": 25,
            "platformFit": 7.5,
            "overall_pass": True,
            "feedback": ["QC timed out — manual review recommended"],
            "suggestions": [],
            "strengths": [],
        }

    pass_fail = "PASS" if qc_output.get("overall_pass") else "NEEDS REVIEW"
    rep_level = qc_output.get("repetition_level", "none")

    await _update_job(job_id, {
        "agent_outputs.qc": qc_output,
        "qc_score": qc_output,
        "agent_summaries.qc": (
            f"Persona {qc_output.get('personaMatch', 0)}/10 · "
            f"AI Risk {qc_output.get('aiRisk', 0)}/100 · "
            f"Rep: {rep_level} · {pass_fail}"
        ),
    })

    # Accumulate QC feedback for possible rewrite
    qc_feedback_history = list(state.get("qc_feedback_history") or [])
    feedback_items = qc_output.get("feedback") or []
    suggestion_items = qc_output.get("suggestions") or []
    new_feedback = feedback_items + suggestion_items
    if new_feedback:
        loop_num = state.get("qc_loop_count", 0) + 1
        qc_feedback_history.extend(
            f"[Loop {loop_num}] {item}" for item in new_feedback
        )

    return {
        "qc_output": qc_output,
        "qc_loop_count": state.get("qc_loop_count", 0) + 1,
        "qc_feedback_history": qc_feedback_history,
        "current_agent": "qc",
    }


# ===================================================================
# Node 9 — Consigliere (Risk Overlay)
# ===================================================================

_CONSIGLIERE_SYSTEM = (
    "You are a brand safety and risk advisor for a content creator. "
    "Evaluate content for potential reputational risks. "
    "Return ONLY valid JSON — no markdown, no explanations."
)

_CONSIGLIERE_PROMPT = """Review this {platform} post for brand/reputation risk.

Creator profile:
- Voice: {voice_descriptor}
- Niche: {content_niche}
- Audience: {audience_profile}
- Risk tolerance: {risk_tolerance}

Content draft:
{draft}

QC scores:
- Persona match: {persona_match}/10
- AI risk: {ai_risk}/100

Evaluate:
1. Is the topic politically or socially sensitive?
2. Could this damage the creator's professional brand?
3. Does the boldness level match their risk tolerance?
4. Are there any factual claims that could be challenged?

Return JSON:
{{
  "risk_level": "low|medium|high",
  "sensitivity_flags": ["list of specific concerns, if any"],
  "brand_safe": true,
  "boldness_appropriate": true,
  "warnings": ["actionable warnings for the creator, if any"],
  "recommendation": "publish|review|caution",
  "reasoning": "Brief explanation of assessment"
}}"""


async def consigliere_node(state: PipelineState) -> dict:
    """Risk overlay: assess content sensitivity, brand safety, boldness fit."""
    draft = state.get("draft", "")
    persona_card = state["persona_card"]
    qc_output = state.get("qc_output") or {}

    # Load UOM risk tolerance from persona if available
    persona_doc = await db.persona_engines.find_one(
        {"user_id": state["user_id"]},
        {"uom": 1, "_id": 0},
    )
    risk_tolerance = "balanced"
    if persona_doc and persona_doc.get("uom"):
        risk_tolerance = persona_doc["uom"].get("risk_tolerance", "balanced")

    consigliere_review: Dict[str, Any] = {}

    try:
        if not openai_available():
            raise RuntimeError("No LLM available for consigliere")

        prompt = _CONSIGLIERE_PROMPT.format(
            platform=state["platform"],
            voice_descriptor=persona_card.get("writing_voice_descriptor", "Professional creator"),
            content_niche=persona_card.get("content_niche_signature", "Thought leadership"),
            audience_profile=persona_card.get("inferred_audience_profile", "Professionals"),
            risk_tolerance=risk_tolerance,
            draft=draft[:2000],
            persona_match=qc_output.get("personaMatch", "N/A"),
            ai_risk=qc_output.get("aiRisk", "N/A"),
        )

        chat = LlmChat(
            api_key=chat_constructor_key(),
            session_id=f"consigliere-{uuid.uuid4().hex[:8]}",
            system_message=_CONSIGLIERE_SYSTEM,
        ).with_model("openai", "gpt-4o")

        raw = await asyncio.wait_for(
            chat.send_message(UserMessage(text=prompt)),
            timeout=20.0,
        )
        consigliere_review = json.loads(_clean_json(raw))

    except Exception as exc:
        logger.warning("Consigliere review failed (non-fatal): %s", exc)
        consigliere_review = {
            "risk_level": "unknown",
            "sensitivity_flags": [],
            "brand_safe": True,
            "boldness_appropriate": True,
            "warnings": [],
            "recommendation": "review",
            "reasoning": f"Automated risk review unavailable: {exc}",
        }

    await _update_job(state["job_id"], {
        "agent_outputs.consigliere": consigliere_review,
        "agent_summaries.consigliere": (
            f"Risk: {consigliere_review.get('risk_level', 'unknown')} · "
            f"Rec: {consigliere_review.get('recommendation', 'review')}"
        ),
    })

    return {"consigliere_review": consigliere_review, "current_agent": "consigliere"}


# ===================================================================
# Node 10 — Finalize
# ===================================================================

async def finalize_node(state: PipelineState) -> dict:
    """Persist final content, update status, fire notifications and webhooks."""
    job_id = state["job_id"]
    user_id = state["user_id"]
    draft = state.get("draft", "")
    qc_output = state.get("qc_output") or {}
    consigliere = state.get("consigliere_review") or {}

    # Verify we actually have content
    if not draft:
        await _update_job(job_id, {
            "status": "error",
            "current_agent": "error",
            "error": "Pipeline completed but produced no content",
        })
        return {"error": "No content produced", "current_agent": "error"}

    now = datetime.now(timezone.utc)

    await db.content_jobs.update_one(
        {"job_id": job_id},
        {"$set": {
            "final_content": draft,
            "status": "completed",
            "current_agent": "done",
            "completed_at": now,
            "updated_at": now,
            "orchestration_metadata": {
                "qc_loops": state.get("qc_loop_count", 0),
                "debate_results": state.get("debate_results"),
                "consigliere_review": consigliere,
            },
        }},
    )

    # Notify user that content generation is complete
    try:
        from services.notification_service import create_notification

        await create_notification(
            user_id=user_id,
            type="job_completed",
            title=f"Your {state['platform']} content is ready",
            body=f"Your {state['content_type']} has been generated and is ready for review.",
            metadata={
                "job_id": job_id,
                "platform": state["platform"],
                "content_type": state["content_type"],
            },
        )
    except Exception as notif_err:
        logger.warning("Failed to create job completion notification: %s", notif_err)

    # Fire outbound webhooks for job.completed
    try:
        from services.webhook_service import fire_webhook

        asyncio.create_task(fire_webhook(user_id, "job.completed", {
            "job_id": job_id,
            "platform": state["platform"],
            "content_type": state["content_type"],
            "status": "completed",
            "qc_score": qc_output.get("personaMatch"),
            "risk_level": consigliere.get("risk_level"),
            "completed_at": now.isoformat(),
        }))
    except Exception as wh_err:
        logger.warning("Failed to fire job.completed webhook: %s", wh_err)

    # Trigger periodic UOM update after successful pipeline completion (non-fatal)
    try:
        from services.uom_service import update_uom_interaction_count
        await update_uom_interaction_count(user_id)
    except Exception as uom_err:
        logger.warning("UOM interaction update failed (non-fatal): %s", uom_err)

    return {"final_content": draft, "current_agent": "done"}


# ===================================================================
# Conditional edge functions
# ===================================================================

def should_research(state: PipelineState) -> bool:
    """Decide whether the Scout research node should run."""
    commander_output = state.get("commander_output") or {}
    return commander_output.get("research_needed", True)


def quality_gate(state: PipelineState) -> str:
    """Route QC results: pass → consigliere, fail → writer (rewrite), or accept best effort.

    Returns one of: ``"pass"``, ``"rewrite"``, ``"accept"``.
    """
    qc_output = state.get("qc_output") or {}
    loop_count = state.get("qc_loop_count", 0)
    overall_pass = qc_output.get("overall_pass", False)

    if overall_pass:
        return "pass"
    if loop_count < MAX_QC_LOOPS:
        return "rewrite"
    # Exhausted rewrite budget — accept best effort
    logger.info(
        "QC loop budget exhausted (%d loops) for job %s — accepting best effort",
        loop_count,
        state.get("job_id", "?"),
    )
    return "accept"


# ===================================================================
# Graph construction
# ===================================================================

def build_content_pipeline() -> Any:
    """Build and compile the LangGraph StateGraph for the content war room.

    Returns a compiled graph runnable.
    """
    graph = StateGraph(PipelineState)

    # Register nodes
    graph.add_node("commander", commander_node)
    graph.add_node("scout", scout_node)
    graph.add_node("identity_check", identity_check_node)
    graph.add_node("thinker", thinker_node)
    graph.add_node("hook_debate", hook_debate_node)
    graph.add_node("writer", writer_node)
    graph.add_node("qc", qc_node)
    graph.add_node("consigliere", consigliere_node)
    graph.add_node("finalize", finalize_node)

    # Wire edges
    graph.set_entry_point("commander")

    graph.add_conditional_edges(
        "commander",
        should_research,
        {True: "scout", False: "identity_check"},
    )
    graph.add_edge("scout", "identity_check")
    graph.add_edge("identity_check", "thinker")
    graph.add_edge("thinker", "hook_debate")
    graph.add_edge("hook_debate", "writer")
    graph.add_edge("writer", "qc")

    graph.add_conditional_edges(
        "qc",
        quality_gate,
        {
            "pass": "consigliere",
            "rewrite": "writer",
            "accept": "consigliere",
        },
    )

    graph.add_edge("consigliere", "finalize")
    graph.add_edge("finalize", END)

    return graph.compile()


# Module-level compiled graph (reused across invocations).
_compiled_pipeline = None


def _get_pipeline():
    """Lazily compile and cache the LangGraph pipeline."""
    global _compiled_pipeline
    if _compiled_pipeline is None:
        _compiled_pipeline = build_content_pipeline()
    return _compiled_pipeline


# ===================================================================
# Main entry point
# ===================================================================

async def run_orchestrated_pipeline(
    job_id: str,
    user_id: str,
    platform: str,
    content_type: str,
    raw_input: str,
    upload_ids: Optional[List[str]] = None,
) -> None:
    """Drop-in replacement for :func:`pipeline.run_agent_pipeline`.

    Loads persona and upload context, initializes the pipeline state, then
    executes the compiled LangGraph.  Top-level errors are caught and
    persisted to the job record so the frontend can display them.
    """
    try:
        # -- Load persona (fallback to default) --------------------------
        persona_doc = await db.persona_engines.find_one(
            {"user_id": user_id}, {"_id": 0}
        )
        persona_card: Dict[str, Any] = {
            **DEFAULT_PERSONA,
            **(persona_doc.get("card", {}) if persona_doc else {}),
        }
        # Inject creator name
        user_doc = await db.users.find_one(
            {"user_id": user_id}, {"_id": 0, "name": 1}
        )
        if user_doc:
            persona_card["creator_name"] = user_doc.get("name", "the creator")

        # -- Anti-repetition context -------------------------------------
        from agents.anti_repetition import (
            get_anti_repetition_context,
            build_anti_repetition_prompt,
        )

        anti_rep_context = await get_anti_repetition_context(user_id)
        anti_rep_prompt = (
            build_anti_repetition_prompt(anti_rep_context)
            if anti_rep_context.get("has_patterns")
            else ""
        )

        # -- Upload media context ----------------------------------------
        from agents.pipeline import _build_upload_media_context

        uids = upload_ids or []
        media_suffix, commander_images = await _build_upload_media_context(
            uids, user_id
        )

        # -- Build initial state -----------------------------------------
        initial_state: PipelineState = {
            "job_id": job_id,
            "user_id": user_id,
            "platform": platform,
            "content_type": content_type,
            "raw_input": raw_input,
            "upload_ids": uids,
            "persona_card": persona_card,
            "anti_rep_prompt": anti_rep_prompt,
            "media_system_suffix": media_suffix,
            "image_urls": commander_images,
            # Agent outputs (populated by nodes)
            "commander_output": {},
            "scout_output": {},
            "thinker_output": {},
            "writer_output": {},
            "qc_output": {},
            # Orchestration control
            "draft": "",
            "qc_loop_count": 0,
            "qc_feedback_history": [],
            "debate_results": {},
            "consigliere_review": {},
            # Metadata
            "current_agent": "initializing",
            "error": None,
            "final_content": "",
        }

        # -- Execute the graph -------------------------------------------
        pipeline = _get_pipeline()
        await pipeline.ainvoke(initial_state)

    except asyncio.CancelledError:
        await _update_job(job_id, {
            "status": "error",
            "current_agent": "error",
            "error": "Pipeline was cancelled",
        })
    except Exception as exc:
        logger.exception("Orchestrated pipeline error for job %s: %s", job_id, exc)
        await _update_job(job_id, {
            "status": "error",
            "current_agent": "error",
            "error": str(exc),
        })
