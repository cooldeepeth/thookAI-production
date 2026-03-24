"""Visual Agent for ThookAI.

Analyzes images using GPT-4o Vision to extract visual insights
for content creation.
"""
import os
import json
import asyncio
import uuid
import base64
import logging
import httpx
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


def _clean_json(raw: str) -> str:
    s = raw.strip()
    if "```" in s:
        parts = s.split("```")
        s = parts[1] if len(parts) > 1 else s
        if s.startswith("json"):
            s = s[4:]
    return s.strip()


VISUAL_SYSTEM = """You are a visual content analyst for social media creators.
Analyze images to extract insights that can inform content creation.
Return only valid JSON - no markdown, no explanations."""

VISUAL_PROMPT = """Analyze this image for a {platform} {content_type}.

Context: {content_context}

Provide a detailed analysis in JSON format:
{{
  "subject": "Main subject/focus of the image",
  "tone": "Visual tone (professional/casual/dramatic/minimal/etc)",
  "key_message": "What story or message the image conveys",
  "caption_angles": ["Angle 1 for caption", "Angle 2 for caption", "Angle 3 for caption"],
  "visual_elements": ["Notable visual elements or details"],
  "brand_alignment": "How this fits a personal brand",
  "is_safe": true
}}

Set is_safe to false if the image contains inappropriate, NSFW, or potentially harmful content."""


async def run_visual(
    image_url_or_base64: str,
    platform: str = "linkedin",
    content_type: str = "post",
    content_context: str = ""
) -> Dict[str, Any]:
    """Analyze an image using GPT-4o Vision.
    
    Args:
        image_url_or_base64: URL or base64-encoded image
        platform: Target platform (linkedin, x, instagram)
        content_type: Type of content being created
        content_context: Additional context about the content
    
    Returns:
        Visual analysis with subject, tone, key_message, caption_angles, is_safe
    """
    from services.llm_keys import chat_constructor_key, openai_available

    if not openai_available():
        return _mock_visual(platform)
    
    try:
        from services.llm_client import LlmChat, UserMessage
        
        # Prepare image content - will be passed via the images parameter
        if image_url_or_base64.startswith('data:') or not image_url_or_base64.startswith('http'):
            # Base64 encoded - ensure proper format
            if not image_url_or_base64.startswith('data:'):
                image_url_or_base64 = f"data:image/jpeg;base64,{image_url_or_base64}"
        
        chat = LlmChat(
            api_key=chat_constructor_key(),
            session_id=f"visual-{uuid.uuid4().hex[:8]}",
            system_message=VISUAL_SYSTEM
        ).with_model("openai", "gpt-4o")
        
        prompt = VISUAL_PROMPT.format(
            platform=platform,
            content_type=content_type,
            content_context=content_context or "General content creation"
        )
        
        # GPT-4o vision call with image
        response = await asyncio.wait_for(
            chat.send_message(UserMessage(text=prompt, images=[image_url_or_base64])),
            timeout=30.0
        )
        
        result = json.loads(_clean_json(response))
        result["analyzed"] = True
        return result
    
    except asyncio.TimeoutError:
        logger.warning("Visual agent timed out")
        return {"analyzed": False, "error": "timeout", "is_safe": True}
    except Exception as e:
        logger.error(f"Visual agent error: {e}")
        return _mock_visual(platform)


def _mock_visual(platform: str) -> Dict[str, Any]:
    """Return mock visual analysis when API unavailable."""
    return {
        "subject": "Professional content image",
        "tone": "Professional and engaging",
        "key_message": "Visual storytelling for audience engagement",
        "caption_angles": [
            "Share the story behind this moment",
            "Lessons learned from this experience",
            "How this connects to your audience's challenges"
        ],
        "visual_elements": ["Clean composition", "Professional lighting"],
        "brand_alignment": "Aligns with professional personal brand",
        "is_safe": True,
        "analyzed": False,
        "mock": True
    }


async def analyze_url_content(url: str) -> Dict[str, Any]:
    """Analyze a URL to determine if it's an image or article.
    
    Returns:
        {type: 'image'|'article'|'unknown', data: ...}
    """
    try:
        async with httpx.AsyncClient() as client:
            # HEAD request to check content type
            response = await client.head(url, timeout=10.0, follow_redirects=True)
            content_type = response.headers.get('content-type', '')
            
            if 'image' in content_type:
                return {"type": "image", "url": url}
            elif 'text/html' in content_type:
                return {"type": "article", "url": url}
            else:
                return {"type": "unknown", "url": url, "content_type": content_type}
    except Exception as e:
        logger.error(f"URL analysis failed: {e}")
        return {"type": "error", "error": str(e)}
