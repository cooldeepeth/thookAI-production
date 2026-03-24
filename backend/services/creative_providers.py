"""Multi-Provider Creative AI Service for ThookAI.

Supports multiple providers for:
- Image Generation: OpenAI, Stability AI, FAL, Replicate, Leonardo, Ideogram
- Video Generation: Runway, Kling, Pika, Luma, HeyGen, D-ID
- Voice/Audio: ElevenLabs, OpenAI TTS, Play.ht, Murf, Resemble

Provides automatic fallback and load distribution.
"""
import os
import logging
from typing import Dict, Any, List, Optional, Literal
from enum import Enum

logger = logging.getLogger(__name__)


def _valid_key(key: str) -> bool:
    """Check if API key is valid (not a placeholder)."""
    if not key:
        return False
    placeholders = ['placeholder', 'sk-placeholder', 'your_', 'xxx', 'test']
    return not any(key.lower().startswith(p) or key.lower() == p for p in placeholders)


def _env_value_for_config(env_key: str) -> str:
    """Resolve env value; OpenAI image/TTS accept OPENAI_API_KEY or legacy EMERGENT_LLM_KEY."""
    if env_key == "EMERGENT_LLM_KEY":
        return os.environ.get("OPENAI_API_KEY") or os.environ.get("EMERGENT_LLM_KEY") or ""
    if env_key == "FAL_API_KEY":
        return os.environ.get("FAL_KEY") or os.environ.get("FAL_API_KEY") or ""
    return os.environ.get(env_key, "") or ""


# ============ PROVIDER CONFIGURATIONS ============

class ImageProvider(str, Enum):
    OPENAI = "openai"
    STABILITY = "stability"
    FAL = "fal"
    REPLICATE = "replicate"
    LEONARDO = "leonardo"
    IDEOGRAM = "ideogram"


class VideoProvider(str, Enum):
    RUNWAY = "runway"
    KLING = "kling"
    PIKA = "pika"
    LUMA = "luma"
    HEYGEN = "heygen"
    DID = "did"
    SYNTHESIA = "synthesia"


class VoiceProvider(str, Enum):
    ELEVENLABS = "elevenlabs"
    OPENAI_TTS = "openai_tts"
    PLAYHT = "playht"
    MURF = "murf"
    RESEMBLE = "resemble"
    GOOGLE_TTS = "google_tts"


# Provider metadata for UI
IMAGE_PROVIDERS_INFO = {
    "openai": {
        "name": "OpenAI GPT Image",
        "description": "High quality, creative images with excellent prompt understanding",
        "models": ["gpt-image-1", "dall-e-3"],
        "env_key": "EMERGENT_LLM_KEY",  # Resolved: OPENAI_API_KEY or EMERGENT_LLM_KEY
        "speed": "medium",
        "quality": "high"
    },
    "stability": {
        "name": "Stability AI",
        "description": "Stable Diffusion models - fast and customizable",
        "models": ["sd3-large", "sdxl-1.0", "sd3-medium"],
        "env_key": "STABILITY_API_KEY",
        "speed": "fast",
        "quality": "high"
    },
    "fal": {
        "name": "FAL AI",
        "description": "Ultra-fast inference - FLUX Pro 1.1, SDXL Lightning",
        "models": ["flux-pro-1.1", "flux-dev", "sdxl-lightning"],
        "env_key": "FAL_API_KEY",
        "speed": "very_fast",
        "quality": "high"
    },
    "replicate": {
        "name": "Replicate",
        "description": "Access to many open-source models",
        "models": ["sdxl", "kandinsky", "playground-v2"],
        "env_key": "REPLICATE_API_TOKEN",
        "speed": "medium",
        "quality": "varies"
    },
    "leonardo": {
        "name": "Leonardo AI",
        "description": "Creative and artistic image generation",
        "models": ["leonardo-diffusion-xl", "phoenix"],
        "env_key": "LEONARDO_API_KEY",
        "speed": "medium",
        "quality": "high"
    },
    "ideogram": {
        "name": "Ideogram",
        "description": "Best for text rendering in images",
        "models": ["ideogram-v2", "ideogram-v2-turbo"],
        "env_key": "IDEOGRAM_API_KEY",
        "speed": "fast",
        "quality": "high"
    }
}

VIDEO_PROVIDERS_INFO = {
    "runway": {
        "name": "Runway Gen-3",
        "description": "Cinematic quality video generation",
        "models": ["gen-3-alpha", "gen-3-alpha-turbo"],
        "env_key": "RUNWAY_API_KEY",
        "duration": "5-10s",
        "quality": "cinematic"
    },
    "kling": {
        "name": "Kling AI",
        "description": "High fidelity video with good motion",
        "models": ["kling-v1", "kling-v1.5"],
        "env_key": "KLING_API_KEY",
        "duration": "5-10s",
        "quality": "high"
    },
    "pika": {
        "name": "Pika Labs",
        "description": "Creative and stylized video generation",
        "models": ["pika-1.0"],
        "env_key": "PIKA_API_KEY",
        "duration": "3-4s",
        "quality": "good"
    },
    "luma": {
        "name": "Luma Dream Machine",
        "description": "Realistic and imaginative videos",
        "models": ["dream-machine"],
        "env_key": "LUMA_API_KEY",
        "duration": "5s",
        "quality": "high"
    },
    "heygen": {
        "name": "HeyGen",
        "description": "AI avatar videos with lip-sync",
        "models": ["avatar-v2"],
        "env_key": "HEYGEN_API_KEY",
        "duration": "unlimited",
        "quality": "high"
    },
    "did": {
        "name": "D-ID",
        "description": "Talking head videos from photos",
        "models": ["talks"],
        "env_key": "DID_API_KEY",
        "duration": "unlimited",
        "quality": "good"
    },
    "synthesia": {
        "name": "Synthesia",
        "description": "Professional AI presenter videos",
        "models": ["studio"],
        "env_key": "SYNTHESIA_API_KEY",
        "duration": "unlimited",
        "quality": "enterprise"
    }
}

VOICE_PROVIDERS_INFO = {
    "elevenlabs": {
        "name": "ElevenLabs",
        "description": "Best quality voice cloning and TTS",
        "models": ["eleven_multilingual_v2", "eleven_turbo_v2"],
        "env_key": "ELEVENLABS_API_KEY",
        "languages": 29,
        "quality": "premium"
    },
    "openai_tts": {
        "name": "OpenAI TTS",
        "description": "Fast and natural sounding voices",
        "models": ["tts-1", "tts-1-hd"],
        "env_key": "EMERGENT_LLM_KEY",  # Resolved: OPENAI_API_KEY or EMERGENT_LLM_KEY
        "languages": 50,
        "quality": "high"
    },
    "playht": {
        "name": "Play.ht",
        "description": "Ultra-realistic AI voices",
        "models": ["playht2.0", "playht2.0-turbo"],
        "env_key": "PLAYHT_API_KEY",
        "languages": 142,
        "quality": "premium"
    },
    "murf": {
        "name": "Murf AI",
        "description": "Studio-quality voiceovers",
        "models": ["murf-studio"],
        "env_key": "MURF_API_KEY",
        "languages": 20,
        "quality": "studio"
    },
    "resemble": {
        "name": "Resemble AI",
        "description": "Custom voice cloning",
        "models": ["resemble-v3"],
        "env_key": "RESEMBLE_API_KEY",
        "languages": 24,
        "quality": "high"
    },
    "google_tts": {
        "name": "Google Cloud TTS",
        "description": "Wide language support, reliable",
        "models": ["neural2", "wavenet"],
        "env_key": "GOOGLE_TTS_API_KEY",
        "languages": 220,
        "quality": "good"
    }
}


def get_available_image_providers() -> List[Dict[str, Any]]:
    """Get list of configured image generation providers."""
    available = []
    for provider_id, info in IMAGE_PROVIDERS_INFO.items():
        env_key = info["env_key"]
        api_key = _env_value_for_config(env_key)
        is_configured = _valid_key(api_key)
        
        available.append({
            "id": provider_id,
            "name": info["name"],
            "description": info["description"],
            "models": info["models"],
            "speed": info["speed"],
            "quality": info["quality"],
            "configured": is_configured,
            "status": "ready" if is_configured else "needs_api_key"
        })
    
    return available


def get_available_video_providers() -> List[Dict[str, Any]]:
    """Get list of configured video generation providers."""
    available = []
    for provider_id, info in VIDEO_PROVIDERS_INFO.items():
        env_key = info["env_key"]
        api_key = _env_value_for_config(env_key)
        is_configured = _valid_key(api_key)
        
        available.append({
            "id": provider_id,
            "name": info["name"],
            "description": info["description"],
            "models": info["models"],
            "duration": info["duration"],
            "quality": info["quality"],
            "configured": is_configured,
            "status": "ready" if is_configured else "needs_api_key"
        })
    
    return available


def get_available_voice_providers() -> List[Dict[str, Any]]:
    """Get list of configured voice providers."""
    available = []
    for provider_id, info in VOICE_PROVIDERS_INFO.items():
        env_key = info["env_key"]
        api_key = _env_value_for_config(env_key)
        is_configured = _valid_key(api_key)
        
        available.append({
            "id": provider_id,
            "name": info["name"],
            "description": info["description"],
            "models": info["models"],
            "languages": info["languages"],
            "quality": info["quality"],
            "configured": is_configured,
            "status": "ready" if is_configured else "needs_api_key"
        })
    
    return available


def get_best_available_provider(
    provider_type: Literal["image", "video", "voice"],
    preferred_provider: Optional[str] = None
) -> Optional[str]:
    """Get the best available provider, respecting user preference if configured."""
    if provider_type == "image":
        providers = IMAGE_PROVIDERS_INFO
    elif provider_type == "video":
        providers = VIDEO_PROVIDERS_INFO
    else:
        providers = VOICE_PROVIDERS_INFO
    
    # Check preferred provider first
    if preferred_provider and preferred_provider in providers:
        env_key = providers[preferred_provider]["env_key"]
        if _valid_key(_env_value_for_config(env_key)):
            return preferred_provider
    
    # Fallback priority order
    priority_order = {
        "image": ["openai", "fal", "stability", "leonardo", "ideogram", "replicate"],
        "video": ["runway", "kling", "luma", "pika", "heygen", "did"],
        "voice": ["elevenlabs", "openai_tts", "playht", "murf", "resemble", "google_tts"]
    }
    
    for provider_id in priority_order.get(provider_type, []):
        if provider_id in providers:
            env_key = providers[provider_id]["env_key"]
            if _valid_key(_env_value_for_config(env_key)):
                return provider_id
    
    return None


def get_provider_status_summary() -> Dict[str, Any]:
    """Get a summary of all provider configurations."""
    image_configured = sum(1 for p in get_available_image_providers() if p["configured"])
    video_configured = sum(1 for p in get_available_video_providers() if p["configured"])
    voice_configured = sum(1 for p in get_available_voice_providers() if p["configured"])
    
    return {
        "image": {
            "total": len(IMAGE_PROVIDERS_INFO),
            "configured": image_configured,
            "best_available": get_best_available_provider("image")
        },
        "video": {
            "total": len(VIDEO_PROVIDERS_INFO),
            "configured": video_configured,
            "best_available": get_best_available_provider("video")
        },
        "voice": {
            "total": len(VOICE_PROVIDERS_INFO),
            "configured": voice_configured,
            "best_available": get_best_available_provider("voice")
        }
    }
