"""Designer Agent for ThookAI.

Generates custom images and carousel slides using multiple AI providers.
Supports: OpenAI, Stability AI, FAL, Replicate, Leonardo, Ideogram
"""
import os
import json
import asyncio
import uuid
import base64
import logging
import httpx
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from services.creative_providers import (
    get_best_available_provider, 
    get_available_image_providers,
    IMAGE_PROVIDERS_INFO
)

logger = logging.getLogger(__name__)

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
    },
    "cinematic": {
        "description": "Movie-like, dramatic lighting",
        "prompt_suffix": "cinematic lighting, dramatic atmosphere, film grain, movie still, professional cinematography"
    },
    "illustration": {
        "description": "Hand-drawn, artistic style",
        "prompt_suffix": "digital illustration, artistic style, hand-drawn feel, creative artwork, detailed illustration"
    },
    "3d": {
        "description": "3D rendered, modern look",
        "prompt_suffix": "3D render, modern 3D style, octane render, blender, realistic materials, professional 3D"
    },
    "retro": {
        "description": "Vintage, nostalgic aesthetic",
        "prompt_suffix": "retro style, vintage aesthetic, 80s/90s vibes, nostalgic, analog feel, warm colors"
    }
}

# Platform-specific settings
PLATFORM_SETTINGS = {
    "linkedin": {"aspect": "1:1", "size": "1024x1024", "carousel_slides": 5},
    "instagram": {"aspect": "1:1", "size": "1024x1024", "carousel_slides": 10},
    "x": {"aspect": "16:9", "size": "1792x1024", "carousel_slides": 0}
}


def _valid_key(key: str) -> bool:
    if not key:
        return False
    placeholders = ['placeholder', 'sk-placeholder', 'your_', 'xxx']
    return not any(key.lower().startswith(p) for p in placeholders)


# ============ PROVIDER-SPECIFIC IMPLEMENTATIONS ============

async def _generate_openai(prompt: str, model: str = "gpt-image-1") -> Dict[str, Any]:
    """Generate image using OpenAI GPT Image."""
    api_key = os.environ.get('EMERGENT_LLM_KEY', '')
    if not _valid_key(api_key):
        return {"generated": False, "error": "no_key", "provider": "openai"}
    
    try:
        from emergentintegrations.llm.openai.image_generation import OpenAIImageGeneration
        
        image_gen = OpenAIImageGeneration(api_key=api_key)
        images = await asyncio.wait_for(
            image_gen.generate_images(prompt=prompt, model=model, number_of_images=1),
            timeout=90.0
        )
        
        if images and len(images) > 0:
            image_base64 = base64.b64encode(images[0]).decode('utf-8')
            return {
                "image_base64": image_base64,
                "image_url": f"data:image/png;base64,{image_base64}",
                "generated": True,
                "provider": "openai",
                "model": model
            }
        return {"generated": False, "error": "no_image", "provider": "openai"}
    except Exception as e:
        logger.error(f"OpenAI image generation error: {e}")
        return {"generated": False, "error": str(e), "provider": "openai"}


async def _generate_stability(prompt: str, model: str = "sd3-large") -> Dict[str, Any]:
    """Generate image using Stability AI."""
    api_key = os.environ.get('STABILITY_API_KEY', '')
    if not _valid_key(api_key):
        return {"generated": False, "error": "no_key", "provider": "stability"}
    
    try:
        async with httpx.AsyncClient() as client:
            # Stability AI API endpoint
            response = await client.post(
                "https://api.stability.ai/v2beta/stable-image/generate/sd3",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Accept": "image/*"
                },
                files={"none": ''},
                data={
                    "prompt": prompt,
                    "model": model,
                    "output_format": "png",
                    "aspect_ratio": "1:1"
                },
                timeout=90.0
            )
            
            if response.status_code == 200:
                image_base64 = base64.b64encode(response.content).decode('utf-8')
                return {
                    "image_base64": image_base64,
                    "image_url": f"data:image/png;base64,{image_base64}",
                    "generated": True,
                    "provider": "stability",
                    "model": model
                }
            else:
                return {"generated": False, "error": response.text, "provider": "stability"}
    except Exception as e:
        logger.error(f"Stability AI error: {e}")
        return {"generated": False, "error": str(e), "provider": "stability"}


async def _generate_fal(prompt: str, model: str = "flux-pro") -> Dict[str, Any]:
    """Generate image using FAL AI (FLUX, SDXL Lightning)."""
    api_key = os.environ.get('FAL_API_KEY', '')
    if not _valid_key(api_key):
        return {"generated": False, "error": "no_key", "provider": "fal"}
    
    try:
        async with httpx.AsyncClient() as client:
            # FAL AI endpoint for FLUX
            model_endpoint = {
                "flux-pro": "fal-ai/flux-pro",
                "flux-dev": "fal-ai/flux/dev",
                "sdxl-lightning": "fal-ai/fast-sdxl"
            }.get(model, "fal-ai/flux-pro")
            
            response = await client.post(
                f"https://fal.run/{model_endpoint}",
                headers={
                    "Authorization": f"Key {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "prompt": prompt,
                    "image_size": "square",
                    "num_images": 1
                },
                timeout=60.0
            )
            
            if response.status_code == 200:
                data = response.json()
                image_url = data.get("images", [{}])[0].get("url", "")
                if image_url:
                    # Download the image
                    img_response = await client.get(image_url, timeout=30.0)
                    image_base64 = base64.b64encode(img_response.content).decode('utf-8')
                    return {
                        "image_base64": image_base64,
                        "image_url": f"data:image/png;base64,{image_base64}",
                        "generated": True,
                        "provider": "fal",
                        "model": model
                    }
            return {"generated": False, "error": "no_image", "provider": "fal"}
    except Exception as e:
        logger.error(f"FAL AI error: {e}")
        return {"generated": False, "error": str(e), "provider": "fal"}


async def _generate_replicate(prompt: str, model: str = "sdxl") -> Dict[str, Any]:
    """Generate image using Replicate."""
    api_key = os.environ.get('REPLICATE_API_TOKEN', '')
    if not _valid_key(api_key):
        return {"generated": False, "error": "no_key", "provider": "replicate"}
    
    try:
        async with httpx.AsyncClient() as client:
            # Replicate model versions
            model_versions = {
                "sdxl": "stability-ai/sdxl:39ed52f2a78e934b3ba6e2a89f5b1c712de7dfea535525255b1aa35c5565e08b",
                "kandinsky": "ai-forever/kandinsky-2.2:ad9d7879fbffa2874e1d909d1d37d9bc682889cc65b31f7bb00d2362619f194a"
            }
            
            version = model_versions.get(model, model_versions["sdxl"])
            
            # Create prediction
            response = await client.post(
                "https://api.replicate.com/v1/predictions",
                headers={
                    "Authorization": f"Token {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "version": version.split(":")[-1],
                    "input": {"prompt": prompt}
                },
                timeout=30.0
            )
            
            if response.status_code == 201:
                prediction = response.json()
                prediction_id = prediction["id"]
                
                # Poll for completion
                for _ in range(60):  # Max 60 seconds
                    await asyncio.sleep(1)
                    status_response = await client.get(
                        f"https://api.replicate.com/v1/predictions/{prediction_id}",
                        headers={"Authorization": f"Token {api_key}"},
                        timeout=10.0
                    )
                    status_data = status_response.json()
                    
                    if status_data["status"] == "succeeded":
                        output = status_data.get("output", [])
                        if output:
                            image_url = output[0] if isinstance(output, list) else output
                            img_response = await client.get(image_url, timeout=30.0)
                            image_base64 = base64.b64encode(img_response.content).decode('utf-8')
                            return {
                                "image_base64": image_base64,
                                "image_url": f"data:image/png;base64,{image_base64}",
                                "generated": True,
                                "provider": "replicate",
                                "model": model
                            }
                    elif status_data["status"] == "failed":
                        return {"generated": False, "error": status_data.get("error", "failed"), "provider": "replicate"}
            
            return {"generated": False, "error": "timeout", "provider": "replicate"}
    except Exception as e:
        logger.error(f"Replicate error: {e}")
        return {"generated": False, "error": str(e), "provider": "replicate"}


async def _generate_leonardo(prompt: str, model: str = "leonardo-diffusion-xl") -> Dict[str, Any]:
    """Generate image using Leonardo AI."""
    api_key = os.environ.get('LEONARDO_API_KEY', '')
    if not _valid_key(api_key):
        return {"generated": False, "error": "no_key", "provider": "leonardo"}
    
    try:
        async with httpx.AsyncClient() as client:
            # Create generation
            response = await client.post(
                "https://cloud.leonardo.ai/api/rest/v1/generations",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "prompt": prompt,
                    "modelId": "6bef9f1b-29cb-40c7-b9df-32b51c1f67d3",  # Leonardo Diffusion XL
                    "width": 1024,
                    "height": 1024,
                    "num_images": 1
                },
                timeout=30.0
            )
            
            if response.status_code == 200:
                data = response.json()
                generation_id = data.get("sdGenerationJob", {}).get("generationId")
                
                if generation_id:
                    # Poll for completion
                    for _ in range(60):
                        await asyncio.sleep(2)
                        status_response = await client.get(
                            f"https://cloud.leonardo.ai/api/rest/v1/generations/{generation_id}",
                            headers={"Authorization": f"Bearer {api_key}"},
                            timeout=10.0
                        )
                        status_data = status_response.json()
                        images = status_data.get("generations_by_pk", {}).get("generated_images", [])
                        
                        if images:
                            image_url = images[0].get("url", "")
                            img_response = await client.get(image_url, timeout=30.0)
                            image_base64 = base64.b64encode(img_response.content).decode('utf-8')
                            return {
                                "image_base64": image_base64,
                                "image_url": f"data:image/png;base64,{image_base64}",
                                "generated": True,
                                "provider": "leonardo",
                                "model": model
                            }
            
            return {"generated": False, "error": "generation_failed", "provider": "leonardo"}
    except Exception as e:
        logger.error(f"Leonardo AI error: {e}")
        return {"generated": False, "error": str(e), "provider": "leonardo"}


async def _generate_ideogram(prompt: str, model: str = "ideogram-v2") -> Dict[str, Any]:
    """Generate image using Ideogram (best for text in images)."""
    api_key = os.environ.get('IDEOGRAM_API_KEY', '')
    if not _valid_key(api_key):
        return {"generated": False, "error": "no_key", "provider": "ideogram"}
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.ideogram.ai/generate",
                headers={
                    "Api-Key": api_key,
                    "Content-Type": "application/json"
                },
                json={
                    "image_request": {
                        "prompt": prompt,
                        "model": "V_2" if "v2" in model else "V_1",
                        "aspect_ratio": "ASPECT_1_1"
                    }
                },
                timeout=60.0
            )
            
            if response.status_code == 200:
                data = response.json()
                images = data.get("data", [])
                if images:
                    image_url = images[0].get("url", "")
                    img_response = await client.get(image_url, timeout=30.0)
                    image_base64 = base64.b64encode(img_response.content).decode('utf-8')
                    return {
                        "image_base64": image_base64,
                        "image_url": f"data:image/png;base64,{image_base64}",
                        "generated": True,
                        "provider": "ideogram",
                        "model": model
                    }
            
            return {"generated": False, "error": "generation_failed", "provider": "ideogram"}
    except Exception as e:
        logger.error(f"Ideogram error: {e}")
        return {"generated": False, "error": str(e), "provider": "ideogram"}


# ============ MAIN GENERATION FUNCTIONS ============

async def generate_image(
    prompt: str,
    style: str = "minimal",
    platform: str = "linkedin",
    persona_card: Optional[Dict[str, Any]] = None,
    provider: Optional[str] = None,
    model: Optional[str] = None
) -> Dict[str, Any]:
    """Generate a custom image using the best available provider.
    
    Args:
        prompt: Description of the image to generate
        style: Style preset (minimal, bold, data-viz, personal, etc.)
        platform: Target platform
        persona_card: User's persona for style customization
        provider: Specific provider to use (optional)
        model: Specific model to use (optional)
    
    Returns:
        {image_base64, image_url, prompt_used, style, platform, provider, model, generated}
    """
    # Build enhanced prompt
    style_config = STYLE_PRESETS.get(style, STYLE_PRESETS["minimal"])
    
    # Incorporate persona if available
    brand_context = ""
    if persona_card:
        brand_context = f"Brand voice: {persona_card.get('writing_voice_descriptor', 'professional')}. "
        brand_context += f"Aesthetic: {persona_card.get('visual_aesthetic', 'modern and clean')}. "
    
    enhanced_prompt = f"{brand_context}{prompt}. Style: {style_config['prompt_suffix']}. High quality, professional."
    
    # Determine provider
    selected_provider = provider or get_best_available_provider("image")
    
    if not selected_provider:
        return _mock_image(prompt, style, platform, enhanced_prompt)
    
    # Route to appropriate provider
    provider_funcs = {
        "openai": _generate_openai,
        "stability": _generate_stability,
        "fal": _generate_fal,
        "replicate": _generate_replicate,
        "leonardo": _generate_leonardo,
        "ideogram": _generate_ideogram
    }
    
    generate_func = provider_funcs.get(selected_provider)
    if not generate_func:
        return _mock_image(prompt, style, platform, enhanced_prompt)
    
    # Get default model for provider
    if not model:
        provider_info = IMAGE_PROVIDERS_INFO.get(selected_provider, {})
        model = provider_info.get("models", ["default"])[0]
    
    result = await generate_func(enhanced_prompt, model)
    
    # Add metadata
    result["prompt_used"] = enhanced_prompt[:500]
    result["style"] = style
    result["platform"] = platform
    
    # If this provider failed, try fallback
    if not result.get("generated") and provider is None:
        logger.warning(f"Provider {selected_provider} failed, trying fallback")
        fallback_providers = ["openai", "fal", "stability", "replicate"]
        for fallback in fallback_providers:
            if fallback != selected_provider:
                fallback_result = await provider_funcs.get(fallback, lambda p, m: {"generated": False})(enhanced_prompt, "default")
                if fallback_result.get("generated"):
                    fallback_result["prompt_used"] = enhanced_prompt[:500]
                    fallback_result["style"] = style
                    fallback_result["platform"] = platform
                    return fallback_result
        
        return _mock_image(prompt, style, platform, enhanced_prompt)
    
    return result


async def generate_carousel(
    topic: str,
    key_points: List[str],
    style: str = "minimal",
    platform: str = "linkedin",
    persona_card: Optional[Dict[str, Any]] = None,
    provider: Optional[str] = None
) -> Dict[str, Any]:
    """Generate a carousel of slides (cover + content + CTA)."""
    platform_config = PLATFORM_SETTINGS.get(platform, PLATFORM_SETTINGS["linkedin"])
    max_slides = platform_config.get("carousel_slides", 5)
    
    selected_provider = provider or get_best_available_provider("image")
    if not selected_provider:
        return _mock_carousel(topic, key_points, style, max_slides)
    
    slides = []
    
    try:
        # Slide 1: Cover
        cover_prompt = f"Title slide for carousel about '{topic}'. Eye-catching cover with bold typography."
        cover = await generate_image(cover_prompt, style, platform, persona_card, selected_provider)
        slides.append({"slide_type": "cover", "content": topic, **cover})
        
        # Content slides
        content_points = key_points[:max_slides - 2]
        for i, point in enumerate(content_points):
            slide_prompt = f"Content slide {i+1}: '{point}'. Clean layout with text area."
            slide = await generate_image(slide_prompt, style, platform, persona_card, selected_provider)
            slides.append({"slide_type": "content", "content": point, "slide_number": i + 2, **slide})
        
        # CTA slide
        cta_prompt = f"Call-to-action slide: 'Follow for more {topic} content'. Engaging CTA design."
        cta = await generate_image(cta_prompt, style, platform, persona_card, selected_provider)
        slides.append({"slide_type": "cta", "content": f"Follow for more on {topic}", **cta})
        
        return {
            "slides": slides,
            "total_slides": len(slides),
            "topic": topic,
            "style": style,
            "provider": selected_provider,
            "generated": True
        }
    
    except Exception as e:
        logger.error(f"Carousel generation error: {e}")
        return _mock_carousel(topic, key_points, style, max_slides)


def _mock_image(prompt: str, style: str, platform: str, enhanced_prompt: str = "") -> Dict[str, Any]:
    """Return mock image data when no providers available."""
    return {
        "image_base64": None,
        "image_url": None,
        "prompt_used": enhanced_prompt or prompt[:500],
        "style": style,
        "platform": platform,
        "generated": False,
        "mock": True,
        "provider": "none",
        "message": "No image provider configured. Add API keys in Settings to enable image generation."
    }


def _mock_carousel(topic: str, key_points: List[str], style: str, max_slides: int) -> Dict[str, Any]:
    """Return mock carousel data when no providers available."""
    slides = [{"slide_type": "cover", "content": topic, "mock": True, "generated": False}]
    for i, point in enumerate(key_points[:max_slides - 2]):
        slides.append({"slide_type": "content", "content": point, "slide_number": i + 2, "mock": True, "generated": False})
    slides.append({"slide_type": "cta", "content": f"Follow for more on {topic}", "mock": True, "generated": False})
    
    return {
        "slides": slides,
        "total_slides": len(slides),
        "topic": topic,
        "style": style,
        "generated": False,
        "mock": True,
        "message": "No image provider configured. Add API keys to enable carousel generation."
    }


def get_available_styles() -> List[Dict[str, str]]:
    """Return list of available style presets."""
    return [
        {"id": key, "name": key.replace("-", " ").title(), "description": val["description"]}
        for key, val in STYLE_PRESETS.items()
    ]
