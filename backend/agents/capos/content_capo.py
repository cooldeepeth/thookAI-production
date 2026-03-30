"""Content Capo for ThookAI.

Oversees: Thinker, Writer, Designer, Video, Voice

Coordinates the content creation flow including strategy generation,
draft writing, hook debate/selection, and media asset creation.
Does NOT replace existing agent functions -- provides orchestration,
error handling, and decision-making on top of them.
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from typing import Any, Dict, List, Optional

from config import settings
from services.llm_client import LlmChat, UserMessage
from services.llm_keys import chat_constructor_key, openai_available

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _clean_json(raw: str) -> str:
    """Strip markdown code fences from an LLM response so it can be parsed as JSON."""
    s = raw.strip()
    if "```" in s:
        parts = s.split("```")
        s = parts[1] if len(parts) > 1 else s
        if s.startswith("json"):
            s = s[4:]
    return s.strip()


# ---------------------------------------------------------------------------
# Content creation
# ---------------------------------------------------------------------------

async def run_content_creation(
    commander_output: dict,
    scout_output: dict,
    persona_card: dict,
    platform: str,
    content_type: str,
    raw_input: str,
    selected_hook: str,
    qc_feedback: Optional[list] = None,
    media_system_suffix: str = "",
    user_id: str = "",
) -> dict:
    """Coordinate the content creation flow: Thinker then Writer.

    1. Runs the Thinker agent to build a content strategy (angle, hooks,
       structure) from the commander output and research.
    2. If *selected_hook* is provided it is injected into the thinker output
       so the Writer uses it; otherwise the first hook option is used.
    3. Runs the Writer agent to produce the draft.
    4. If *qc_feedback* is provided (rewrite loop), it is appended to the
       Writer's media_system_suffix so the Writer can address the feedback.

    Returns a combined dict with keys from both agents:
        thinker_output, writer_output, draft, word_count, platform
    """
    from agents.thinker import run_thinker
    from agents.writer import run_writer

    # ------------------------------------------------------------------
    # Step 1 -- Thinker
    # ------------------------------------------------------------------
    try:
        thinker_output = await asyncio.wait_for(
            run_thinker(
                raw_input,
                commander_output,
                scout_output,
                persona_card,
                user_id=user_id,
            ),
            timeout=30.0,
        )
    except asyncio.TimeoutError:
        logger.error("Content Capo: Thinker timed out after 30s")
        thinker_output = _fallback_thinker(raw_input, commander_output)
    except Exception as exc:
        logger.error("Content Capo: Thinker failed: %s", exc)
        thinker_output = _fallback_thinker(raw_input, commander_output)

    # ------------------------------------------------------------------
    # Hook selection override
    # ------------------------------------------------------------------
    if selected_hook:
        # Push the explicitly selected hook to index 0 so the Writer uses it.
        hook_options = thinker_output.get("hook_options", [])
        if selected_hook in hook_options:
            hook_options.remove(selected_hook)
        hook_options.insert(0, selected_hook)
        thinker_output["hook_options"] = hook_options

    # ------------------------------------------------------------------
    # Step 2 -- Writer
    # ------------------------------------------------------------------
    writer_suffix = media_system_suffix
    if qc_feedback:
        feedback_block = "\n".join(f"- {fb}" for fb in qc_feedback)
        rewrite_instructions = (
            "\n\nREWRITE INSTRUCTIONS (address ALL of the following):\n"
            f"{feedback_block}\n"
            "Revise the draft to resolve every item above while keeping the "
            "creator's voice and overall structure intact."
        )
        writer_suffix = f"{writer_suffix}{rewrite_instructions}" if writer_suffix else rewrite_instructions

    try:
        writer_output = await asyncio.wait_for(
            run_writer(
                platform,
                content_type,
                commander_output,
                scout_output,
                thinker_output,
                persona_card,
                media_system_suffix=writer_suffix,
                user_id=user_id,
            ),
            timeout=40.0,
        )
    except asyncio.TimeoutError:
        logger.error("Content Capo: Writer timed out after 40s")
        writer_output = {"draft": "", "word_count": 0, "error": "writer_timeout"}
    except Exception as exc:
        logger.error("Content Capo: Writer failed: %s", exc)
        writer_output = {"draft": "", "word_count": 0, "error": str(exc)}

    draft = writer_output.get("draft", "") if isinstance(writer_output, dict) else str(writer_output)

    return {
        "thinker_output": thinker_output,
        "writer_output": writer_output,
        "draft": draft,
        "word_count": len(draft.split()) if draft else 0,
        "platform": platform,
        "content_type": content_type,
        "selected_hook": thinker_output.get("hook_options", [""])[0],
    }


# ---------------------------------------------------------------------------
# Hook debate
# ---------------------------------------------------------------------------

HOOK_DEBATE_SYSTEM = (
    "You are a content strategist evaluating hook options for a social media "
    "creator. Score each hook objectively. Return ONLY valid JSON."
)

HOOK_DEBATE_PROMPT = """Score the following hook options for a {platform} {content_type}.

CREATOR PERSONA:
Voice: {voice_descriptor}
Niche: {content_niche}
Hook Style Preference: {hook_style}

HOOK OPTIONS:
{hooks_block}

For EACH hook, score on three dimensions (0-10):
- engagement_potential: How likely is this to stop the scroll?
- persona_fit: How well does this match the creator's voice?
- originality: How fresh and non-generic is this?

Return JSON:
{{
  "selected_hook": "The full text of the best hook",
  "scores": [
    {{
      "hook": "Hook text",
      "engagement_potential": 8,
      "persona_fit": 9,
      "originality": 7,
      "total": 24
    }}
  ],
  "reasoning": "One sentence explaining why the winner was chosen"
}}"""


async def run_hook_debate(
    hook_options: list,
    persona_card: dict,
    platform: str,
    content_type: str,
) -> dict:
    """Debate protocol for hook selection.

    Takes 2+ hook options (typically from Thinker), scores each using a fast
    LLM call (gpt-4o-mini) on engagement_potential, persona_fit, and
    originality, then returns the winner.

    Falls back to selecting the first hook if the LLM is unavailable.
    """
    if not hook_options:
        return {
            "selected_hook": "",
            "scores": [],
            "reasoning": "No hooks provided",
        }

    if len(hook_options) == 1:
        return {
            "selected_hook": hook_options[0],
            "scores": [
                {
                    "hook": hook_options[0],
                    "engagement_potential": 7,
                    "persona_fit": 7,
                    "originality": 7,
                    "total": 21,
                }
            ],
            "reasoning": "Only one hook provided; selected by default.",
        }

    if not openai_available():
        return _fallback_hook_selection(hook_options)

    try:
        hooks_block = "\n".join(
            f"{i + 1}. {hook}" for i, hook in enumerate(hook_options)
        )

        prompt = HOOK_DEBATE_PROMPT.format(
            platform=platform,
            content_type=content_type,
            voice_descriptor=persona_card.get("writing_voice_descriptor", "Professional thought leader"),
            content_niche=persona_card.get("content_niche_signature", "Thought leadership"),
            hook_style=persona_card.get("hook_style", "Bold statement"),
            hooks_block=hooks_block,
        )

        chat = LlmChat(
            api_key=chat_constructor_key(),
            session_id=f"hook-debate-{uuid.uuid4().hex[:8]}",
            system_message=HOOK_DEBATE_SYSTEM,
        ).with_model("openai", "gpt-4o-mini")

        response = await asyncio.wait_for(
            chat.send_message(UserMessage(text=prompt)),
            timeout=15.0,
        )
        result = json.loads(_clean_json(response))

        # Validate that selected_hook is one of the actual options
        if result.get("selected_hook") not in hook_options:
            # Pick the hook with the highest total from scores
            scores = result.get("scores", [])
            if scores:
                best = max(scores, key=lambda s: s.get("total", 0))
                result["selected_hook"] = best.get("hook", hook_options[0])
            else:
                result["selected_hook"] = hook_options[0]

        return result

    except asyncio.TimeoutError:
        logger.warning("Content Capo: Hook debate timed out, using fallback")
        return _fallback_hook_selection(hook_options)
    except Exception as exc:
        logger.warning("Content Capo: Hook debate failed (%s), using fallback", exc)
        return _fallback_hook_selection(hook_options)


# ---------------------------------------------------------------------------
# Media creation
# ---------------------------------------------------------------------------

async def run_media_creation(
    content: str,
    platform: str,
    content_type: str,
    persona_card: dict,
    media_type: str,
    user_id: str,
) -> dict:
    """Route to the appropriate media agent and return the result.

    Args:
        content: The text content to create media for.
        platform: Target platform (linkedin, x, instagram).
        content_type: Type of content (post, thread, carousel, etc.).
        persona_card: User persona card dict.
        media_type: One of "image", "video", "voice", "carousel".
        user_id: User ID for tracking.

    Returns:
        Dict with media_url, media_type, provider, and generated flag.
    """
    try:
        if media_type == "image":
            return await _create_image(content, platform, persona_card)
        elif media_type == "carousel":
            return await _create_carousel(content, platform, persona_card)
        elif media_type == "video":
            return await _create_video(content, platform)
        elif media_type == "voice":
            return await _create_voice(content)
        else:
            logger.warning("Content Capo: Unknown media type '%s'", media_type)
            return {
                "media_url": None,
                "media_type": media_type,
                "provider": "none",
                "generated": False,
                "error": f"Unsupported media type: {media_type}",
            }
    except Exception as exc:
        logger.error("Content Capo: Media creation failed for type=%s: %s", media_type, exc)
        return {
            "media_url": None,
            "media_type": media_type,
            "provider": "none",
            "generated": False,
            "error": str(exc),
        }


# ---------------------------------------------------------------------------
# Private helpers -- media sub-routes
# ---------------------------------------------------------------------------

async def _create_image(content: str, platform: str, persona_card: dict) -> dict:
    from agents.designer import generate_image

    # Use the first sentence or 200 chars as the image prompt
    prompt = content.split(".")[0][:200] if content else "Professional social media image"
    result = await asyncio.wait_for(
        generate_image(
            prompt=prompt,
            style="minimal",
            platform=platform,
            persona_card=persona_card,
        ),
        timeout=120.0,
    )
    return {
        "media_url": result.get("image_url"),
        "media_type": "image",
        "provider": result.get("provider", "unknown"),
        "generated": result.get("generated", False),
    }


async def _create_carousel(content: str, platform: str, persona_card: dict) -> dict:
    from agents.designer import generate_carousel

    # Split content into key points for carousel slides
    lines = [line.strip() for line in content.split("\n") if line.strip()]
    topic = lines[0][:100] if lines else "Content carousel"
    key_points = lines[1:6] if len(lines) > 1 else ["Key insight"]

    result = await asyncio.wait_for(
        generate_carousel(
            topic=topic,
            key_points=key_points,
            style="minimal",
            platform=platform,
            persona_card=persona_card,
        ),
        timeout=180.0,
    )
    return {
        "media_url": None,  # Carousel returns slides, not a single URL
        "media_type": "carousel",
        "provider": result.get("provider", "unknown"),
        "generated": result.get("generated", False),
        "slides": result.get("slides", []),
        "total_slides": result.get("total_slides", 0),
    }


async def _create_video(content: str, platform: str) -> dict:
    from agents.video import generate_video

    prompt = content[:300] if content else "Professional video clip"
    result = await asyncio.wait_for(
        generate_video(prompt=prompt, duration=5),
        timeout=180.0,
    )
    return {
        "media_url": result.get("video_url"),
        "media_type": "video",
        "provider": result.get("provider", "unknown"),
        "generated": result.get("generated", False),
    }


async def _create_voice(content: str) -> dict:
    from agents.voice import generate_voice_narration

    result = await asyncio.wait_for(
        generate_voice_narration(text=content),
        timeout=90.0,
    )
    return {
        "media_url": result.get("audio_url"),
        "media_type": "voice",
        "provider": result.get("provider", "unknown"),
        "generated": result.get("generated", False),
        "duration_estimate": result.get("duration_estimate"),
    }


# ---------------------------------------------------------------------------
# Fallbacks
# ---------------------------------------------------------------------------

def _fallback_thinker(raw_input: str, commander_output: dict) -> dict:
    """Minimal thinker output when the real agent is unavailable."""
    angle = commander_output.get("primary_angle", f"A perspective on {raw_input[:40]}")
    return {
        "angle": angle,
        "hook_options": [
            f"Most people get {raw_input[:30]} wrong. Here's what actually works.",
            f"After years of experience, here's the truth about {raw_input[:30]}.",
        ],
        "content_structure": [
            {"section": "Hook", "guidance": "Start with a bold, counter-intuitive claim"},
            {"section": "Body", "guidance": "3 concrete points backed by research"},
            {"section": "Insight", "guidance": "One sentence that captures the lesson"},
            {"section": "CTA", "guidance": "End with a thought-provoking question"},
        ],
        "key_insight": f"The key truth about {raw_input[:40]} that most miss",
        "differentiation": "First-person experience combined with data",
        "_fallback": True,
    }


def _fallback_hook_selection(hook_options: list) -> dict:
    """Select the first hook when LLM debate is unavailable."""
    scores = []
    for i, hook in enumerate(hook_options):
        # Simple heuristic: shorter hooks score slightly higher on engagement
        length_bonus = max(0, 10 - len(hook.split()) // 5)
        scores.append({
            "hook": hook,
            "engagement_potential": min(10, 6 + length_bonus),
            "persona_fit": 7,
            "originality": 6,
            "total": min(30, 19 + length_bonus),
        })
    scores.sort(key=lambda s: s["total"], reverse=True)
    return {
        "selected_hook": scores[0]["hook"],
        "scores": scores,
        "reasoning": "Selected using heuristic fallback (LLM unavailable).",
        "_fallback": True,
    }
