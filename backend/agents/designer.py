"""Designer Agent for ThookAI.

Generates custom images and carousel slides using OpenAI GPT Image.
"""
import os
import json
import asyncio
import uuid
import base64
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

LLM_KEY = os.environ.get('EMERGENT_LLM_KEY', '')

# Style presets for image generation
STYLE_PRESETS = {
    "minimal": {
        "description": "Clean, simple, lots of whitespace, modern typography",
        "prompt_suffix": "minimalist design, clean lines, simple composition, white background, modern aesthetic, professional"
    },
    "bold": {
        "description": "Vibrant colors, strong contrast, attention-grabbing",
        "prompt_suffix": "bold colors, high contrast, dynamic composition, eye-catching, vibrant, impactful visual"
    },
    "data-viz": {
        "description": "Charts, graphs, infographic style",
        "prompt_suffix": "data visualization style, infographic aesthetic, charts and graphs, professional presentation, clean data display"
    },
    "personal": {
        "description": "Warm, authentic, personal brand focused",
        "prompt_suffix": "warm tones, authentic feel, personal brand aesthetic, approachable, genuine, lifestyle photography style"
    }
}

# Platform-specific settings
PLATFORM_SETTINGS = {
    "linkedin": {
        "aspect": "1:1",
        "size": "1024x1024",
        "carousel_slides": 5
    },
    "instagram": {
        "aspect": "1:1", 
        "size": "1024x1024",
        "carousel_slides": 10
    },
    "x": {
        "aspect": "16:9",
        "size": "1792x1024",
        "carousel_slides": 0
    }
}


def _valid_key(key: str) -> bool:
    return bool(key) and not any(key.startswith(p) for p in ['placeholder', 'sk-placeholder'])


async def generate_image(
    prompt: str,
    style: str = "minimal",
    platform: str = "linkedin",
    persona_card: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Generate a custom image using OpenAI GPT Image.
    
    Args:
        prompt: Description of the image to generate
        style: Style preset (minimal, bold, data-viz, personal)
        platform: Target platform
        persona_card: User's persona for style customization
    
    Returns:
        {image_base64, prompt_used, style, platform}
    """
    if not _valid_key(LLM_KEY):
        return _mock_image(prompt, style, platform)
    
    try:
        from emergentintegrations.llm.openai.image_generation import OpenAIImageGeneration
        
        # Build enhanced prompt
        style_config = STYLE_PRESETS.get(style, STYLE_PRESETS["minimal"])
        
        # Incorporate persona if available
        brand_context = ""
        if persona_card:
            brand_context = f"Brand voice: {persona_card.get('writing_voice_descriptor', 'professional')}. "
            brand_context += f"Aesthetic: {persona_card.get('visual_aesthetic', 'modern and clean')}. "
        
        enhanced_prompt = f"{brand_context}{prompt}. Style: {style_config['prompt_suffix']}. High quality, professional."
        
        # Generate image
        image_gen = OpenAIImageGeneration(api_key=LLM_KEY)
        
        images = await asyncio.wait_for(
            image_gen.generate_images(
                prompt=enhanced_prompt,
                model="gpt-image-1",
                number_of_images=1
            ),
            timeout=90.0  # Image generation can take up to 60s
        )
        
        if images and len(images) > 0:
            image_base64 = base64.b64encode(images[0]).decode('utf-8')
            return {
                "image_base64": image_base64,
                "image_url": f"data:image/png;base64,{image_base64}",
                "prompt_used": enhanced_prompt[:500],
                "style": style,
                "platform": platform,
                "generated": True
            }
        else:
            raise Exception("No image was generated")
    
    except asyncio.TimeoutError:
        logger.warning("Designer agent timed out")
        return {"generated": False, "error": "timeout", "prompt_used": prompt}
    except Exception as e:
        logger.error(f"Designer agent error: {e}")
        error_msg = str(e)
        # Check for content policy rejection
        if "content_policy" in error_msg.lower() or "safety" in error_msg.lower():
            return {
                "generated": False,
                "error": "content_policy",
                "message": "Image couldn't be generated due to content policy. Try a different style or prompt.",
                "prompt_used": prompt
            }
        return _mock_image(prompt, style, platform)


async def generate_carousel(
    topic: str,
    key_points: List[str],
    style: str = "minimal",
    platform: str = "linkedin",
    persona_card: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Generate a carousel of slides (cover + content + CTA).
    
    Args:
        topic: Main topic/title for the carousel
        key_points: List of key points for content slides
        style: Style preset
        platform: Target platform
        persona_card: User's persona
    
    Returns:
        {slides: [{image_base64, slide_type, content}], total_slides}
    """
    platform_config = PLATFORM_SETTINGS.get(platform, PLATFORM_SETTINGS["linkedin"])
    max_slides = platform_config.get("carousel_slides", 5)
    
    if not _valid_key(LLM_KEY):
        return _mock_carousel(topic, key_points, style, max_slides)
    
    slides = []
    
    try:
        # Slide 1: Cover
        cover_prompt = f"Title slide for carousel about '{topic}'. Eye-catching cover with bold typography."
        cover = await generate_image(cover_prompt, style, platform, persona_card)
        slides.append({
            "slide_type": "cover",
            "content": topic,
            **cover
        })
        
        # Content slides (limit to max_slides - 2 for cover and CTA)
        content_points = key_points[:max_slides - 2]
        for i, point in enumerate(content_points):
            slide_prompt = f"Content slide {i+1}: '{point}'. Clean layout with text area."
            slide = await generate_image(slide_prompt, style, platform, persona_card)
            slides.append({
                "slide_type": "content",
                "content": point,
                "slide_number": i + 2,
                **slide
            })
        
        # CTA slide
        cta_prompt = f"Call-to-action slide: 'Follow for more {topic} content'. Engaging CTA design."
        cta = await generate_image(cta_prompt, style, platform, persona_card)
        slides.append({
            "slide_type": "cta",
            "content": f"Follow for more on {topic}",
            **cta
        })
        
        return {
            "slides": slides,
            "total_slides": len(slides),
            "topic": topic,
            "style": style,
            "generated": True
        }
    
    except Exception as e:
        logger.error(f"Carousel generation error: {e}")
        return _mock_carousel(topic, key_points, style, max_slides)


def _mock_image(prompt: str, style: str, platform: str) -> Dict[str, Any]:
    """Return mock image data when API unavailable."""
    # Generate a simple placeholder
    return {
        "image_base64": None,
        "image_url": None,
        "prompt_used": prompt[:500],
        "style": style,
        "platform": platform,
        "generated": False,
        "mock": True,
        "message": "Image generation unavailable. Configure EMERGENT_LLM_KEY to enable."
    }


def _mock_carousel(topic: str, key_points: List[str], style: str, max_slides: int) -> Dict[str, Any]:
    """Return mock carousel data when API unavailable."""
    slides = [
        {"slide_type": "cover", "content": topic, "mock": True, "generated": False},
    ]
    for i, point in enumerate(key_points[:max_slides - 2]):
        slides.append({
            "slide_type": "content",
            "content": point,
            "slide_number": i + 2,
            "mock": True,
            "generated": False
        })
    slides.append({
        "slide_type": "cta",
        "content": f"Follow for more on {topic}",
        "mock": True,
        "generated": False
    })
    
    return {
        "slides": slides,
        "total_slides": len(slides),
        "topic": topic,
        "style": style,
        "generated": False,
        "mock": True,
        "message": "Carousel generation unavailable. Configure EMERGENT_LLM_KEY to enable."
    }


def get_available_styles() -> List[Dict[str, str]]:
    """Return list of available style presets."""
    return [
        {"id": key, "name": key.replace("-", " ").title(), "description": val["description"]}
        for key, val in STYLE_PRESETS.items()
    ]
