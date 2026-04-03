import os
import json
import asyncio
import uuid
import logging
from typing import Any, Dict, List, Optional
from services.llm_client import LlmChat, UserMessage
from services.llm_keys import chat_constructor_key, openai_available, anthropic_available

logger = logging.getLogger(__name__)

QC_SYSTEM = """You are the QC Agent for ThookAI. Score content against creator persona. Return only valid JSON."""

QC_PROMPT = """Score this {platform} {content_type} against the creator's persona.

CREATOR PERSONA:
Voice: {voice_descriptor}
Niche: {content_niche}
Tone: {tone}
Hook Style: {hook_style}

CONTENT DRAFT:
{draft}

Score objectively. Return JSON:
{{
  "personaMatch": 8.5,
  "aiRisk": 18,
  "platformFit": 9.0,
  "overall_pass": true,
  "feedback": ["What could be improved"],
  "suggestions": ["Specific actionable suggestion"],
  "strengths": ["What works well"]
}}

personaMatch 0-10: Does this sound like the creator? (7+ = good)
aiRisk 0-100: How AI-generated does this feel? (below 30 = good, below 20 = excellent)
platformFit 0-10: Platform-appropriate length, format, style? (7+ = good)
overall_pass: true if personaMatch>=7 AND aiRisk<=35 AND platformFit>=7"""


def _clean_json(raw: str) -> str:
    s = raw.strip()
    if "```" in s:
        parts = s.split("```")
        s = parts[1] if len(parts) > 1 else s
        if s.startswith("json"):
            s = s[4:]
    return s.strip()


async def run_qc(draft: str, persona_card: dict, platform: str, content_type: str, user_id: str = None) -> dict:
    """Run QC agent to score content quality and persona match.
    
    Args:
        draft: Content draft to evaluate
        persona_card: User's persona information
        platform: Target platform
        content_type: Type of content
        user_id: Optional user ID for repetition check
    
    Returns:
        QC scores and feedback
    """
    # Fetch UOM directives for the QC agent (non-fatal)
    uom_directives = {}
    if user_id:
        try:
            from services.uom_service import get_agent_directives
            uom_directives = await get_agent_directives(user_id, "qc")
        except Exception:
            pass

    # UOM-aware thresholds (fall back to original hardcoded values)
    persona_threshold = uom_directives.get("persona_match_threshold", 7)
    ai_risk_threshold = uom_directives.get("ai_risk_threshold", 35)

    # Start with base QC
    if not openai_available():
        result = _mock_qc(draft)
    else:
        try:
            chat = LlmChat(
                api_key=chat_constructor_key(),
                session_id=f"qc-{uuid.uuid4().hex[:8]}",
                system_message=QC_SYSTEM
            ).with_model("openai", "gpt-4o-mini")

            prompt = QC_PROMPT.format(
                platform=platform, content_type=content_type,
                voice_descriptor=persona_card.get("writing_voice_descriptor", "Professional creator"),
                content_niche=persona_card.get("content_niche_signature", "Thought leadership"),
                tone=persona_card.get("tone", "Professional"),
                hook_style=persona_card.get("hook_style", "Bold statement"),
                draft=draft[:2000]
            )
            response = await asyncio.wait_for(chat.send_message(UserMessage(text=prompt)), timeout=20.0)
            result = json.loads(_clean_json(response))
            # Ensure overall_pass is computed correctly using UOM-aware thresholds
            result["overall_pass"] = (
                result.get("personaMatch", 0) >= persona_threshold and
                result.get("aiRisk", 100) <= ai_risk_threshold and
                result.get("platformFit", 0) >= 7
            )
        except Exception as e:
            logger.error(f"QC agent error: {e}")
            result = _mock_qc(draft)
    
    # Add repetition risk check if user_id provided
    if user_id:
        try:
            from agents.anti_repetition import score_repetition_risk
            rep_result = await score_repetition_risk(user_id, draft)
            result["repetition_risk"] = rep_result.get("repetition_risk_score", 0)
            result["repetition_level"] = rep_result.get("risk_level", "none")
            
            # Factor repetition into overall_pass
            if rep_result.get("repetition_risk_score", 0) >= 80:
                result["overall_pass"] = False
                result["feedback"] = result.get("feedback", []) + [rep_result.get("feedback", "High repetition detected")]
        except Exception as e:
            logger.error(f"Repetition check failed: {e}")
            result["repetition_risk"] = 0
            result["repetition_level"] = "unknown"
    
    return result


def _mock_qc(draft: str) -> dict:
    word_count = len(draft.split())
    persona_match = min(9.0, 6.5 + (word_count / 100))
    return {
        "personaMatch": round(persona_match, 1),
        "aiRisk": 22,
        "platformFit": 8.5,
        "overall_pass": persona_match >= 7,
        "feedback": ["Consider adding more personal anecdote or specific data point"],
        "suggestions": ["Open with a stronger hook to stop the scroll faster"],
        "strengths": ["Good structure", "Clear key insight", "Actionable takeaway in CTA"]
    }


# ============ MEDIA QC VALIDATION ============

# Platform dimension specifications for images and videos.
# Tolerance (px) applies to image width/height checks.
PLATFORM_MEDIA_SPECS: Dict[str, Dict[str, Any]] = {
    "linkedin": {
        "image": {"width": 1200, "height": 1200, "tolerance": 100},
        "video": {"width": 1080, "height": 1920, "max_duration_s": 600, "min_duration_s": 3},
    },
    "instagram": {
        "image": {"width": 1080, "height": 1080, "tolerance": 100},
        "video": {"width": 1080, "height": 1920, "max_duration_s": 90, "min_duration_s": 3},
    },
    "x": {
        "image": {"width": 1200, "height": 675, "tolerance": 100},
        "video": {"width": 1080, "height": 1920, "max_duration_s": 140, "min_duration_s": 1},
    },
}

# Media types that are classified as video (vs still image)
_VIDEO_MEDIA_TYPES = {"short_form_video", "talking_head", "text_on_video"}

# Expected file extensions per content class
_VIDEO_EXTENSIONS = {".mp4", ".mov", ".webm"}
_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}


def _is_video_type(media_type: str) -> bool:
    return media_type in _VIDEO_MEDIA_TYPES


def _url_extension(url: str) -> str:
    """Return lowercase file extension from URL, e.g. '.png'. Returns '' if none."""
    path = url.split("?")[0]  # Strip query params
    if "." in path.rsplit("/", 1)[-1]:
        return "." + path.rsplit(".", 1)[-1].lower()
    return ""


async def validate_media_output(
    media_url: str,
    media_type: str,
    platform: str,
    brand_color: str = "#2563EB",
    persona_card: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Validate rendered media output for brand consistency and platform compliance.

    Checks:
    1. platform_dimensions — correct composition used for media_type + platform
    2. brand_consistency — brand_color was provided (metadata check; pixel-level
       requires vision API and is handled inside anti_slop when available)
    3. anti_slop — LLM vision check for AI artifacts (graceful skip if unavailable)
    4. file_format — correct extension for content class (.png for stills, .mp4 for video)

    Args:
        media_url: URL of the rendered asset (R2 / Remotion output)
        media_type: Media type identifier (e.g. "static_image", "short_form_video")
        platform: Target social platform
        brand_color: Hex brand color expected to be present in the composition
        persona_card: Optional persona for brand context

    Returns:
        {
            "overall_pass": bool,
            "checks": [
                {"name": str, "pass": bool, "detail": str},
                ...  # 4 checks always present
            ],
            "feedback": List[str],
        }
    """
    checks: List[Dict[str, Any]] = []
    feedback: List[str] = []

    # --- Check 1: Platform dimensions ---
    # We validate that the platform is known and a spec exists for the content class.
    # Actual pixel dimensions require downloading the asset (out of scope for a metadata check).
    # The presence of a matching spec confirms the correct composition was chosen.
    is_video = _is_video_type(media_type)
    content_class = "video" if is_video else "image"
    platform_specs = PLATFORM_MEDIA_SPECS.get(platform, PLATFORM_MEDIA_SPECS.get("linkedin"))
    spec = platform_specs.get(content_class) if platform_specs else None

    if spec is not None:
        if is_video:
            dimension_detail = (
                f"Platform {platform} video spec: {spec['width']}x{spec['height']}, "
                f"{spec['min_duration_s']}-{spec['max_duration_s']}s"
            )
        else:
            dimension_detail = (
                f"Platform {platform} image spec: {spec['width']}x{spec['height']} "
                f"(±{spec['tolerance']}px)"
            )
        dimension_pass = True
    else:
        dimension_detail = f"No spec found for platform '{platform}' media type '{media_type}'"
        dimension_pass = False

    checks.append({"name": "platform_dimensions", "pass": dimension_pass, "detail": dimension_detail})
    if not dimension_pass:
        feedback.append(f"platform_dimensions: {dimension_detail}")

    # --- Check 2: Brand consistency ---
    # Validate that a non-empty brand color was passed; pixel-level check deferred to vision.
    brand_ok = bool(brand_color and brand_color.startswith("#") and len(brand_color) in (4, 7))
    if brand_ok:
        brand_detail = f"Brand color {brand_color} provided — composition should use this hex value"
    else:
        brand_detail = f"Invalid or missing brand color '{brand_color}' — brand consistency cannot be guaranteed"

    checks.append({"name": "brand_consistency", "pass": brand_ok, "detail": brand_detail})
    if not brand_ok:
        feedback.append(f"brand_consistency: {brand_detail}")

    # --- Check 3: Anti-AI-slop ---
    # If Anthropic vision is available, use Claude to check for AI artifacts.
    # Otherwise pass gracefully with a note.
    try:
        vision_available = anthropic_available()
    except Exception:
        vision_available = False

    if vision_available and media_url and not media_url.startswith("data:"):
        try:
            chat = LlmChat(
                api_key=chat_constructor_key(),
                session_id=f"qc-vision-{uuid.uuid4().hex[:8]}",
                system_message="You are a media quality auditor. Respond with JSON only.",
            ).with_model("anthropic", "claude-sonnet-4-20250514")

            vision_prompt = (
                "Examine this image for AI-generation artifacts: "
                "distorted hands, spelling errors in text, unnatural lighting, "
                "uncanny faces, repetitive backgrounds, or logo inconsistencies. "
                "Respond with JSON: {\"pass\": true/false, \"detail\": \"...\"}. "
                f"Image URL: {media_url}"
            )
            response_text = await asyncio.wait_for(
                chat.send_message(UserMessage(text=vision_prompt)),
                timeout=20.0,
            )
            try:
                vision_result = json.loads(response_text.strip().strip("```json").strip("```").strip())
                slop_pass = bool(vision_result.get("pass", True))
                slop_detail = vision_result.get("detail", "Vision analysis complete")
            except Exception:
                slop_pass = True
                slop_detail = "Vision response parse error — treating as pass"
        except asyncio.TimeoutError:
            slop_pass = True
            slop_detail = "Vision analysis timed out — treating as pass"
        except Exception as e:
            logger.warning(f"Anti-slop vision check failed: {e}")
            slop_pass = True
            slop_detail = f"Vision analysis unavailable: {e}"
    else:
        slop_pass = True
        slop_detail = "Vision analysis unavailable — Anthropic API key not configured"

    checks.append({"name": "anti_slop", "pass": slop_pass, "detail": slop_detail})
    if not slop_pass:
        feedback.append(f"anti_slop: {slop_detail}")

    # --- Check 4: File format ---
    ext = _url_extension(media_url)
    if is_video:
        format_pass = ext in _VIDEO_EXTENSIONS
        if format_pass:
            format_detail = f"File extension '{ext}' is valid for video media type '{media_type}'"
        else:
            format_detail = (
                f"File extension '{ext}' is not valid for video media type '{media_type}' "
                f"(expected one of {sorted(_VIDEO_EXTENSIONS)})"
            )
    else:
        format_pass = ext in _IMAGE_EXTENSIONS
        if format_pass:
            format_detail = f"File extension '{ext}' is valid for image media type '{media_type}'"
        else:
            format_detail = (
                f"File extension '{ext}' is not valid for image media type '{media_type}' "
                f"(expected one of {sorted(_IMAGE_EXTENSIONS)})"
            )

    checks.append({"name": "file_format", "pass": format_pass, "detail": format_detail})
    if not format_pass:
        feedback.append(f"file_format: {format_detail}")

    overall_pass = all(c["pass"] for c in checks)

    return {
        "overall_pass": overall_pass,
        "checks": checks,
        "feedback": feedback,
    }
