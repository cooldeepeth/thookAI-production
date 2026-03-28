"""Video Agent for ThookAI.

Generates videos using multiple AI providers.
Supports: Runway, Kling, Pika, Luma, HeyGen, D-ID
"""
import base64
import asyncio
import logging
import httpx
import fal_client
from typing import Dict, Any, Optional, List
from lumaai import AsyncLumaAI
from config import settings
from services.creative_providers import (
    get_best_available_provider,
    get_available_video_providers,
    VIDEO_PROVIDERS_INFO
)

logger = logging.getLogger(__name__)


def _valid_key(key: str) -> bool:
    if not key:
        return False
    placeholders = ['placeholder', 'sk-placeholder', 'your_', 'xxx']
    return not any(key.lower().startswith(p) for p in placeholders)


# ============ PROVIDER-SPECIFIC IMPLEMENTATIONS ============

async def _generate_runway(prompt: str, model: str = "gen-3-alpha-turbo", duration: int = 5) -> Dict[str, Any]:
    """Generate video using Runway Gen-3."""
    api_key = settings.video.runway_api_key or ''
    if not _valid_key(api_key):
        return {"generated": False, "error": "no_key", "provider": "runway"}
    
    try:
        async with httpx.AsyncClient() as client:
            # Create generation task
            response = await client.post(
                "https://api.runwayml.com/v1/image_to_video" if model != "gen-3-alpha" else "https://api.runwayml.com/v1/generations",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "text_prompt": prompt,
                    "model": model,
                    "duration": duration,
                    "ratio": "16:9"
                },
                timeout=30.0
            )
            
            if response.status_code in [200, 201]:
                data = response.json()
                task_id = data.get("id")
                
                if task_id:
                    # Poll for completion (video generation takes 30-120 seconds)
                    for _ in range(120):
                        await asyncio.sleep(2)
                        status_response = await client.get(
                            f"https://api.runwayml.com/v1/tasks/{task_id}",
                            headers={"Authorization": f"Bearer {api_key}"},
                            timeout=10.0
                        )
                        status_data = status_response.json()
                        
                        if status_data.get("status") == "succeeded":
                            video_url = status_data.get("output", {}).get("video_url")
                            if video_url:
                                return {
                                    "video_url": video_url,
                                    "generated": True,
                                    "provider": "runway",
                                    "model": model,
                                    "duration": duration
                                }
                        elif status_data.get("status") == "failed":
                            return {"generated": False, "error": status_data.get("error", "failed"), "provider": "runway"}
            
            return {"generated": False, "error": "generation_failed", "provider": "runway"}
    except Exception as e:
        logger.error(f"Runway error: {e}")
        return {"generated": False, "error": str(e), "provider": "runway"}


async def _generate_kling(prompt: str, model: str = "kling-v1.5", duration: int = 5) -> Dict[str, Any]:
    """Generate video using Kling AI."""
    api_key = settings.video.kling_api_key or ''
    if not _valid_key(api_key):
        return {"generated": False, "error": "no_key", "provider": "kling"}
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.klingai.com/v1/videos/generations",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "prompt": prompt,
                    "model": model,
                    "duration": duration,
                    "aspect_ratio": "16:9"
                },
                timeout=30.0
            )
            
            if response.status_code in [200, 201]:
                data = response.json()
                task_id = data.get("task_id")
                
                if task_id:
                    for _ in range(120):
                        await asyncio.sleep(3)
                        status_response = await client.get(
                            f"https://api.klingai.com/v1/videos/generations/{task_id}",
                            headers={"Authorization": f"Bearer {api_key}"},
                            timeout=10.0
                        )
                        status_data = status_response.json()
                        
                        if status_data.get("status") == "completed":
                            video_url = status_data.get("video_url")
                            if video_url:
                                return {
                                    "video_url": video_url,
                                    "generated": True,
                                    "provider": "kling",
                                    "model": model,
                                    "duration": duration
                                }
                        elif status_data.get("status") == "failed":
                            return {"generated": False, "error": "generation_failed", "provider": "kling"}
            
            return {"generated": False, "error": "request_failed", "provider": "kling"}
    except Exception as e:
        logger.error(f"Kling error: {e}")
        return {"generated": False, "error": str(e), "provider": "kling"}


async def _generate_luma(prompt: str, model: str = "dream-machine") -> Dict[str, Any]:
    """Generate video using Luma Dream Machine (official async SDK)."""
    api_key = settings.video.luma_api_key or ''
    if not _valid_key(api_key):
        return {"generated": False, "error": "no_key", "provider": "luma"}

    luma_model = "ray-flash-2" if model and "flash" in model.lower() else "ray-2"

    try:
        client = AsyncLumaAI(auth_token=api_key)
        generation = await client.generations.create(
            model=luma_model,
            prompt=prompt,
            aspect_ratio="16:9",
            loop=False,
        )
        gid = generation.id

        for _ in range(60):
            await asyncio.sleep(5)
            gen = await client.generations.get(gid)
            if gen.state == "completed":
                video_url = gen.assets.video if gen.assets else None
                if video_url:
                    return {
                        "video_url": video_url,
                        "generated": True,
                        "provider": "luma",
                        "model": model,
                        "duration": 5,
                        "generation_id": gid,
                    }
                return {"generated": False, "error": "no_video_asset", "provider": "luma"}
            if gen.state == "failed":
                return {
                    "generated": False,
                    "error": gen.failure_reason or "failed",
                    "provider": "luma",
                }

        return {"generated": False, "error": "timeout", "provider": "luma"}
    except Exception as e:
        logger.error(f"Luma error: {e}")
        return {"generated": False, "error": str(e), "provider": "luma"}


async def _generate_pika(prompt: str, duration: int = 3) -> Dict[str, Any]:
    """Generate video using Pika Labs."""
    api_key = settings.video.pika_api_key or ''
    if not _valid_key(api_key):
        return {"generated": False, "error": "no_key", "provider": "pika"}
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.pika.art/v1/generate",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "prompt": prompt,
                    "aspect_ratio": "16:9",
                    "duration": duration
                },
                timeout=30.0
            )
            
            if response.status_code in [200, 201]:
                data = response.json()
                job_id = data.get("job_id")
                
                if job_id:
                    for _ in range(60):
                        await asyncio.sleep(3)
                        status_response = await client.get(
                            f"https://api.pika.art/v1/jobs/{job_id}",
                            headers={"Authorization": f"Bearer {api_key}"},
                            timeout=10.0
                        )
                        status_data = status_response.json()
                        
                        if status_data.get("status") == "complete":
                            video_url = status_data.get("video_url")
                            if video_url:
                                return {
                                    "video_url": video_url,
                                    "generated": True,
                                    "provider": "pika",
                                    "model": "pika-1.0",
                                    "duration": duration
                                }
                        elif status_data.get("status") == "failed":
                            return {"generated": False, "error": "generation_failed", "provider": "pika"}
            
            return {"generated": False, "error": "request_failed", "provider": "pika"}
    except Exception as e:
        logger.error(f"Pika error: {e}")
        return {"generated": False, "error": str(e), "provider": "pika"}


async def _generate_heygen_avatar(script: str, avatar_id: str = "default") -> Dict[str, Any]:
    """Generate avatar video using HeyGen."""
    api_key = settings.video.heygen_api_key or ''
    if not _valid_key(api_key):
        return {"generated": False, "error": "no_key", "provider": "heygen"}
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.heygen.com/v2/video/generate",
                headers={
                    "X-Api-Key": api_key,
                    "Content-Type": "application/json"
                },
                json={
                    "video_inputs": [{
                        "character": {
                            "type": "avatar",
                            "avatar_id": avatar_id,
                            "avatar_style": "normal"
                        },
                        "voice": {
                            "type": "text",
                            "input_text": script
                        }
                    }],
                    "dimension": {"width": 1920, "height": 1080}
                },
                timeout=30.0
            )
            
            if response.status_code in [200, 201]:
                data = response.json()
                video_id = data.get("data", {}).get("video_id")
                
                if video_id:
                    for _ in range(120):
                        await asyncio.sleep(5)
                        status_response = await client.get(
                            f"https://api.heygen.com/v1/video_status.get?video_id={video_id}",
                            headers={"X-Api-Key": api_key},
                            timeout=10.0
                        )
                        status_data = status_response.json()
                        
                        if status_data.get("data", {}).get("status") == "completed":
                            video_url = status_data.get("data", {}).get("video_url")
                            if video_url:
                                return {
                                    "video_url": video_url,
                                    "generated": True,
                                    "provider": "heygen",
                                    "model": "avatar-v2",
                                    "type": "avatar"
                                }
                        elif status_data.get("data", {}).get("status") == "failed":
                            return {"generated": False, "error": "generation_failed", "provider": "heygen"}
            
            return {"generated": False, "error": "request_failed", "provider": "heygen"}
    except Exception as e:
        logger.error(f"HeyGen error: {e}")
        return {"generated": False, "error": str(e), "provider": "heygen"}


async def _generate_did_avatar(script: str, source_url: str = None) -> Dict[str, Any]:
    """Generate talking head video using D-ID."""
    api_key = settings.video.did_api_key or ''
    if not _valid_key(api_key):
        return {"generated": False, "error": "no_key", "provider": "did"}
    
    try:
        async with httpx.AsyncClient() as client:
            payload = {
                "script": {
                    "type": "text",
                    "input": script
                },
                "config": {
                    "stitch": True
                }
            }
            
            if source_url:
                payload["source_url"] = source_url
            
            response = await client.post(
                "https://api.d-id.com/talks",
                headers={
                    "Authorization": f"Basic {api_key}",
                    "Content-Type": "application/json"
                },
                json=payload,
                timeout=30.0
            )
            
            if response.status_code in [200, 201]:
                data = response.json()
                talk_id = data.get("id")
                
                if talk_id:
                    for _ in range(60):
                        await asyncio.sleep(3)
                        status_response = await client.get(
                            f"https://api.d-id.com/talks/{talk_id}",
                            headers={"Authorization": f"Basic {api_key}"},
                            timeout=10.0
                        )
                        status_data = status_response.json()
                        
                        if status_data.get("status") == "done":
                            video_url = status_data.get("result_url")
                            if video_url:
                                return {
                                    "video_url": video_url,
                                    "generated": True,
                                    "provider": "did",
                                    "model": "talks",
                                    "type": "avatar"
                                }
                        elif status_data.get("status") == "error":
                            return {"generated": False, "error": status_data.get("error", "failed"), "provider": "did"}
            
            return {"generated": False, "error": "request_failed", "provider": "did"}
    except Exception as e:
        logger.error(f"D-ID error: {e}")
        return {"generated": False, "error": str(e), "provider": "did"}


async def generate_motion_video(prompt: str, image_url: Optional[str] = None) -> Dict[str, Any]:
    """Motion / dance-style video via fal.ai Seadance (uses FAL_KEY)."""
    api_key = settings.video.fal_key or ''
    if not _valid_key(api_key):
        return {"generated": False, "error": "no_key", "provider": "fal-seadance"}

    try:
        arguments: Dict[str, Any] = {
            "prompt": prompt,
            "duration": 5,
            "aspect_ratio": "16:9",
        }
        if image_url:
            arguments["image_url"] = image_url

        handler = await fal_client.submit_async("fal-ai/seadance", arguments=arguments)
        result = await handler.get()
        video = result.get("video")
        vurl = video.get("url") if isinstance(video, dict) else None
        if not vurl:
            return {"generated": False, "error": "no_video", "provider": "fal-seadance"}

        return {
            "video_url": vurl,
            "generated": True,
            "provider": "fal-seadance",
            "generation_id": None,
        }
    except Exception as e:
        logger.error(f"fal Seadance error: {e}")
        return {"generated": False, "error": str(e), "provider": "fal-seadance"}


# ============ MAIN GENERATION FUNCTIONS ============

async def generate_video(
    prompt: str,
    duration: int = 5,
    provider: Optional[str] = None,
    model: Optional[str] = None
) -> Dict[str, Any]:
    """Generate video using the best available provider.
    
    Args:
        prompt: Description of the video to generate
        duration: Video duration in seconds
        provider: Specific provider to use (optional)
        model: Specific model to use (optional)
    
    Returns:
        {video_url, duration, provider, model, generated}
    """
    selected_provider = provider or get_best_available_provider("video")
    
    if not selected_provider:
        return {
            "error": "provider_not_configured",
            "provider": "none",
            "generated": False,
            "message": "No video provider is configured. Set RUNWAY_API_KEY, KLING_API_KEY, LUMA_API_KEY, or PIKA_API_KEY to enable video generation."
        }
    
    # Route to appropriate provider
    provider_funcs = {
        "runway": lambda: _generate_runway(prompt, model or "gen-3-alpha-turbo", duration),
        "kling": lambda: _generate_kling(prompt, model or "kling-v1.5", duration),
        "luma": lambda: _generate_luma(prompt, model or "dream-machine"),
        "pika": lambda: _generate_pika(prompt, min(duration, 4)),  # Pika max 4s
    }
    
    generate_func = provider_funcs.get(selected_provider)
    if not generate_func:
        return {
            "error": "provider_not_configured",
            "provider": selected_provider,
            "generated": False,
            "message": f"Provider '{selected_provider}' is not supported. Supported: runway, kling, luma, pika."
        }
    
    result = await generate_func()
    result["prompt_used"] = prompt[:500]
    
    return result


async def generate_avatar_video(
    script: str,
    avatar_id: Optional[str] = None,
    source_image_url: Optional[str] = None,
    provider: Optional[str] = None
) -> Dict[str, Any]:
    """Generate avatar/talking head video.
    
    Args:
        script: Text for the avatar to speak
        avatar_id: Specific avatar ID (for HeyGen)
        source_image_url: Image to animate (for D-ID)
        provider: heygen or did
    
    Returns:
        {video_url, provider, generated}
    """
    # Check which avatar providers are configured
    heygen_key = settings.video.heygen_api_key or ''
    did_key = settings.video.did_api_key or ''
    
    if provider == "heygen" or (_valid_key(heygen_key) and not provider):
        return await _generate_heygen_avatar(script, avatar_id or "default")
    elif provider == "did" or _valid_key(did_key):
        return await _generate_did_avatar(script, source_image_url)
    else:
        return {
            "error": "provider_not_configured",
            "provider": "none",
            "generated": False,
            "message": "No avatar provider configured. Set HEYGEN_API_KEY or DID_API_KEY to enable avatar video generation."
        }


def _mock_video(prompt: str, duration: int) -> Dict[str, Any]:
    """Return error response when no providers are available.

    Kept for backward compatibility but no longer returns fake URLs.
    """
    return {
        "error": "provider_not_configured",
        "provider": "none",
        "generated": False,
        "message": "No video provider configured. Set RUNWAY_API_KEY, KLING_API_KEY, LUMA_API_KEY, or PIKA_API_KEY to enable video generation."
    }


def get_video_provider_info() -> Dict[str, Any]:
    """Get information about configured video providers."""
    return get_available_video_providers()
