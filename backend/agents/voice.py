"""Voice Agent for ThookAI.

Converts text to audio narration using multiple AI providers.
Supports: ElevenLabs, OpenAI TTS, Play.ht, Murf, Resemble, Google TTS
Also supports voice cloning via ElevenLabs "Add Voice" API.
"""
import base64
import asyncio
import logging
import httpx
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List

from config import settings
from database import db
from services.creative_providers import (
    get_best_available_provider,
    get_available_voice_providers,
    VOICE_PROVIDERS_INFO
)

logger = logging.getLogger(__name__)

MAX_CHARS = 5000  # Character limit for most providers

# Default voices per provider
DEFAULT_VOICES = {
    "elevenlabs": [
        {"id": "21m00Tcm4TlvDq8ikWAM", "name": "Rachel", "description": "American female, calm and professional"},
        {"id": "AZnzlk1XvdvUeBnXmlld", "name": "Domi", "description": "American female, strong and confident"},
        {"id": "EXAVITQu4vr4xnSDxMaL", "name": "Bella", "description": "American female, soft and warm"},
        {"id": "ErXwobaYiN019PkySvjV", "name": "Antoni", "description": "American male, well-rounded and calm"},
        {"id": "MF3mGyEYCl7XYWbV9V6O", "name": "Elli", "description": "American female, young and pleasant"},
        {"id": "TxGEqnHWrfWFTfGW9XjX", "name": "Josh", "description": "American male, deep and narrative"},
    ],
    "openai_tts": [
        {"id": "alloy", "name": "Alloy", "description": "Neutral and balanced"},
        {"id": "echo", "name": "Echo", "description": "Warm and engaging"},
        {"id": "fable", "name": "Fable", "description": "Expressive and dynamic"},
        {"id": "onyx", "name": "Onyx", "description": "Deep and authoritative"},
        {"id": "nova", "name": "Nova", "description": "Friendly and upbeat"},
        {"id": "shimmer", "name": "Shimmer", "description": "Clear and optimistic"},
    ],
    "playht": [
        {"id": "s3://voice-cloning-zero-shot/775ae416-49bb-4fb6-bd45-740f205d20a1/jennifersaad/manifest.json", "name": "Jennifer", "description": "American female, professional"},
        {"id": "s3://voice-cloning-zero-shot/d9ff78ba-d016-47f6-b0ef-dd630f59414e/male-cs/manifest.json", "name": "Michael", "description": "American male, conversational"},
    ],
    "murf": [
        {"id": "en-US-natalie", "name": "Natalie", "description": "American female, professional"},
        {"id": "en-US-marcus", "name": "Marcus", "description": "American male, authoritative"},
    ],
    "google_tts": [
        {"id": "en-US-Neural2-C", "name": "Neural2 Female", "description": "High quality female voice"},
        {"id": "en-US-Neural2-D", "name": "Neural2 Male", "description": "High quality male voice"},
        {"id": "en-US-Wavenet-F", "name": "Wavenet Female", "description": "Natural female voice"},
        {"id": "en-US-Wavenet-D", "name": "Wavenet Male", "description": "Natural male voice"},
    ]
}


def _valid_key(key: str) -> bool:
    if not key:
        return False
    placeholders = ['placeholder', 'sk-placeholder', 'your_', 'xxx']
    return not any(key.lower().startswith(p) for p in placeholders)


# ============ PROVIDER-SPECIFIC IMPLEMENTATIONS ============

async def _generate_elevenlabs(text: str, voice_id: str, stability: float, similarity_boost: float) -> Dict[str, Any]:
    """Generate voice using ElevenLabs (async SDK)."""
    api_key = settings.llm.elevenlabs_key or ""
    if not _valid_key(api_key):
        return {"generated": False, "error": "no_key", "provider": "elevenlabs"}

    try:
        from elevenlabs.client import AsyncElevenLabs
        from elevenlabs.types.voice_settings import VoiceSettings

        client = AsyncElevenLabs(api_key=api_key)
        vid = voice_id or DEFAULT_VOICES["elevenlabs"][0]["id"]
        model_id = "eleven_multilingual_v2"
        voice_settings = VoiceSettings(
            stability=stability,
            similarity_boost=similarity_boost,
            style=0.0,
            use_speaker_boost=True,
        )

        stream = client.text_to_speech.convert(
            vid,
            text=text,
            model_id=model_id,
            output_format="mp3_44100_128",
            voice_settings=voice_settings,
        )
        audio_data = b""
        async for chunk in stream:
            audio_data += chunk

        audio_base64 = base64.b64encode(audio_data).decode("utf-8")

        return {
            "audio_base64": audio_base64,
            "audio_url": f"data:audio/mpeg;base64,{audio_base64}",
            "generated": True,
            "provider": "elevenlabs",
            "model": model_id,
        }
    except Exception as e:
        logger.error(f"ElevenLabs error: {e}")
        return {"generated": False, "error": str(e), "provider": "elevenlabs"}


async def _generate_openai_tts(text: str, voice_id: str, model: str = "tts-1-hd") -> Dict[str, Any]:
    """Generate voice using OpenAI TTS."""
    from services.llm_keys import openai_api_key_for_rest

    api_key = openai_api_key_for_rest()
    if not _valid_key(api_key):
        return {"generated": False, "error": "no_key", "provider": "openai_tts"}
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.openai.com/v1/audio/speech",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": model,
                    "input": text,
                    "voice": voice_id or "alloy",
                    "response_format": "mp3"
                },
                timeout=60.0
            )
            
            if response.status_code == 200:
                audio_base64 = base64.b64encode(response.content).decode('utf-8')
                return {
                    "audio_base64": audio_base64,
                    "audio_url": f"data:audio/mpeg;base64,{audio_base64}",
                    "generated": True,
                    "provider": "openai_tts",
                    "model": model
                }
            else:
                return {"generated": False, "error": response.text, "provider": "openai_tts"}
    except Exception as e:
        logger.error(f"OpenAI TTS error: {e}")
        return {"generated": False, "error": str(e), "provider": "openai_tts"}


async def _generate_playht(text: str, voice_id: str) -> Dict[str, Any]:
    """Generate voice using Play.ht."""
    api_key = settings.voice.playht_api_key or ''
    user_id = settings.voice.playht_user_id or ''
    if not _valid_key(api_key) or not _valid_key(user_id):
        return {"generated": False, "error": "no_key", "provider": "playht"}
    
    try:
        async with httpx.AsyncClient() as client:
            # Create speech request
            response = await client.post(
                "https://api.play.ht/api/v2/tts",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "X-User-ID": user_id,
                    "Content-Type": "application/json"
                },
                json={
                    "text": text,
                    "voice": voice_id or DEFAULT_VOICES["playht"][0]["id"],
                    "output_format": "mp3",
                    "quality": "premium"
                },
                timeout=60.0
            )
            
            if response.status_code == 201:
                data = response.json()
                audio_url = data.get("url")
                
                if audio_url:
                    # Download audio
                    audio_response = await client.get(audio_url, timeout=30.0)
                    audio_base64 = base64.b64encode(audio_response.content).decode('utf-8')
                    return {
                        "audio_base64": audio_base64,
                        "audio_url": f"data:audio/mpeg;base64,{audio_base64}",
                        "generated": True,
                        "provider": "playht",
                        "model": "playht2.0"
                    }
            
            return {"generated": False, "error": "generation_failed", "provider": "playht"}
    except Exception as e:
        logger.error(f"Play.ht error: {e}")
        return {"generated": False, "error": str(e), "provider": "playht"}


async def _generate_google_tts(text: str, voice_id: str) -> Dict[str, Any]:
    """Generate voice using Google Cloud TTS."""
    api_key = settings.voice.google_tts_api_key or ''
    if not _valid_key(api_key):
        return {"generated": False, "error": "no_key", "provider": "google_tts"}
    
    try:
        async with httpx.AsyncClient() as client:
            voice_name = voice_id or "en-US-Neural2-C"
            
            response = await client.post(
                f"https://texttospeech.googleapis.com/v1/text:synthesize?key={api_key}",
                json={
                    "input": {"text": text},
                    "voice": {
                        "languageCode": "en-US",
                        "name": voice_name
                    },
                    "audioConfig": {
                        "audioEncoding": "MP3",
                        "speakingRate": 1.0,
                        "pitch": 0.0
                    }
                },
                timeout=60.0
            )
            
            if response.status_code == 200:
                data = response.json()
                audio_content = data.get("audioContent", "")
                
                if audio_content:
                    return {
                        "audio_base64": audio_content,
                        "audio_url": f"data:audio/mpeg;base64,{audio_content}",
                        "generated": True,
                        "provider": "google_tts",
                        "model": "neural2"
                    }
            
            return {"generated": False, "error": "generation_failed", "provider": "google_tts"}
    except Exception as e:
        logger.error(f"Google TTS error: {e}")
        return {"generated": False, "error": str(e), "provider": "google_tts"}


# ============ MAIN GENERATION FUNCTIONS ============

async def generate_voice_narration(
    text: str,
    voice_id: Optional[str] = None,
    stability: float = 0.5,
    similarity_boost: float = 0.75,
    provider: Optional[str] = None,
    model: Optional[str] = None
) -> Dict[str, Any]:
    """Generate voice narration using the best available provider.
    
    Args:
        text: Text to convert to speech
        voice_id: Voice ID (provider-specific)
        stability: Voice stability (0-1)
        similarity_boost: Voice similarity (0-1)
        provider: Specific provider to use (optional)
        model: Specific model to use (optional)
    
    Returns:
        {audio_base64, audio_url, duration_estimate, voice_used, truncated, provider, generated}
    """
    # Truncate if too long
    truncated = False
    original_length = len(text)
    if len(text) > MAX_CHARS:
        text = text[:MAX_CHARS]
        truncated = True
        logger.warning(f"Text truncated from {original_length} to {MAX_CHARS} characters")
    
    # Determine provider
    selected_provider = provider or get_best_available_provider("voice")
    
    if not selected_provider:
        return _mock_voice(text, truncated)
    
    # Get default voice for provider if not specified
    if not voice_id:
        provider_voices = DEFAULT_VOICES.get(selected_provider, [])
        voice_id = provider_voices[0]["id"] if provider_voices else None
    
    # Route to appropriate provider
    provider_funcs = {
        "elevenlabs": lambda: _generate_elevenlabs(text, voice_id, stability, similarity_boost),
        "openai_tts": lambda: _generate_openai_tts(text, voice_id, model or "tts-1-hd"),
        "playht": lambda: _generate_playht(text, voice_id),
        "google_tts": lambda: _generate_google_tts(text, voice_id),
    }
    
    generate_func = provider_funcs.get(selected_provider)
    if not generate_func:
        return _mock_voice(text, truncated)
    
    result = await generate_func()
    
    # Add metadata
    word_count = len(text.split())
    duration_estimate = round(word_count / 150 * 60, 1)  # ~150 words per minute
    
    result["duration_estimate"] = duration_estimate
    result["char_count"] = len(text)
    result["truncated"] = truncated
    result["voice_used"] = {"id": voice_id, "provider": selected_provider}
    
    # If this provider failed, try fallback
    if not result.get("generated") and provider is None:
        logger.warning(f"Provider {selected_provider} failed, trying fallback")
        fallback_providers = ["openai_tts", "elevenlabs", "google_tts", "playht"]
        for fallback in fallback_providers:
            if fallback != selected_provider and fallback in provider_funcs:
                fallback_voice = DEFAULT_VOICES.get(fallback, [{}])[0].get("id")
                fallback_result = await provider_funcs[fallback]()
                if fallback_result.get("generated"):
                    fallback_result["duration_estimate"] = duration_estimate
                    fallback_result["char_count"] = len(text)
                    fallback_result["truncated"] = truncated
                    fallback_result["voice_used"] = {"id": fallback_voice, "provider": fallback}
                    return fallback_result
        
        return _mock_voice(text, truncated)
    
    return result


def _mock_voice(text: str, truncated: bool = False) -> Dict[str, Any]:
    """Return mock voice data when no providers available."""
    word_count = len(text.split())
    duration_estimate = round(word_count / 150 * 60, 1)
    
    return {
        "audio_base64": None,
        "audio_url": None,
        "duration_estimate": duration_estimate,
        "voice_used": {"id": "mock", "name": "Mock Voice", "provider": "none"},
        "char_count": len(text),
        "truncated": truncated,
        "generated": False,
        "mock": True,
        "provider": "none",
        "message": "No voice provider configured. Add API keys in Settings to enable voice narration."
    }


def get_available_voices(provider: Optional[str] = None) -> Dict[str, List[Dict[str, str]]]:
    """Get available voices, optionally filtered by provider."""
    if provider:
        return {provider: DEFAULT_VOICES.get(provider, [])}
    return DEFAULT_VOICES


async def get_user_cloned_voices() -> List[Dict[str, Any]]:
    """Fetch user's custom cloned voices from supported providers."""
    cloned_voices = []

    # ElevenLabs cloned voices
    api_key = settings.llm.elevenlabs_key or ""
    if _valid_key(api_key):
        try:
            from elevenlabs import ElevenLabs
            client = ElevenLabs(api_key=api_key)
            voices_response = client.voices.get_all()

            for voice in voices_response.voices:
                if voice.category == "cloned":
                    cloned_voices.append({
                        "id": voice.voice_id,
                        "name": voice.name,
                        "description": voice.description or "Custom cloned voice",
                        "provider": "elevenlabs",
                        "category": "cloned"
                    })
        except Exception as e:
            logger.error(f"Failed to fetch ElevenLabs cloned voices: {e}")

    return cloned_voices


# ============ VOICE CLONING (ElevenLabs) ============

ELEVENLABS_API_BASE = "https://api.elevenlabs.io/v1"


def _get_elevenlabs_key() -> str:
    """Return the ElevenLabs API key from settings, or empty string."""
    return settings.llm.elevenlabs_key or ""


async def create_voice_clone(
    user_id: str,
    sample_urls: List[str],
    voice_name: str,
) -> Dict[str, Any]:
    """Create a voice clone on ElevenLabs from audio sample URLs.

    Downloads each sample from R2, then POSTs the raw audio files to the
    ElevenLabs ``/v1/voices/add`` endpoint as multipart form data.

    On success, stores ``voice_clone_id`` and ``voice_clone_name`` in the
    user's ``persona_engines`` document.

    Args:
        user_id: The owning user's ID.
        sample_urls: List of public R2 URLs pointing to audio samples.
        voice_name: Display name for the cloned voice.

    Returns:
        ``{voice_id, name, status}`` on success, or
        ``{error, status: "failed"}`` on failure.
    """
    api_key = _get_elevenlabs_key()
    if not _valid_key(api_key):
        return {"error": "ElevenLabs API key is not configured.", "status": "failed"}

    if not sample_urls:
        return {"error": "No sample URLs provided.", "status": "failed"}

    # 1. Download all audio samples
    downloaded_files: List[tuple] = []  # (filename, bytes)
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            for idx, url in enumerate(sample_urls):
                resp = await client.get(url)
                resp.raise_for_status()
                # Derive a filename from the URL or fall back
                fname = url.rsplit("/", 1)[-1] if "/" in url else f"sample_{idx}.mp3"
                downloaded_files.append((fname, resp.content))
    except Exception as e:
        logger.error(f"Failed to download voice samples for user {user_id}: {e}")
        return {"error": f"Could not download audio samples: {e}", "status": "failed"}

    # 2. POST to ElevenLabs /v1/voices/add
    try:
        files_payload = [
            ("files", (fname, data, "audio/mpeg"))
            for fname, data in downloaded_files
        ]

        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{ELEVENLABS_API_BASE}/voices/add",
                headers={"xi-api-key": api_key},
                data={"name": voice_name},
                files=files_payload,
            )

        if resp.status_code not in (200, 201):
            error_detail = resp.text[:500]
            logger.error(
                f"ElevenLabs voice/add failed ({resp.status_code}) for user {user_id}: {error_detail}"
            )
            return {
                "error": f"ElevenLabs returned {resp.status_code}: {error_detail}",
                "status": "failed",
            }

        body = resp.json()
        voice_id = body.get("voice_id")
        if not voice_id:
            return {"error": "ElevenLabs response did not include a voice_id.", "status": "failed"}

    except Exception as e:
        logger.error(f"ElevenLabs voice clone request error for user {user_id}: {e}")
        return {"error": str(e), "status": "failed"}

    # 3. Persist in persona_engines
    now = datetime.now(timezone.utc)
    await db.persona_engines.update_one(
        {"user_id": user_id},
        {
            "$set": {
                "voice_clone_id": voice_id,
                "voice_clone_name": voice_name,
                "voice_clone_created_at": now,
                "updated_at": now,
            }
        },
    )

    logger.info(f"Voice clone created for user {user_id}: voice_id={voice_id}")
    return {"voice_id": voice_id, "name": voice_name, "status": "created"}


async def delete_voice_clone(user_id: str) -> bool:
    """Delete the user's cloned voice from ElevenLabs and clear local records.

    Args:
        user_id: The owning user's ID.

    Returns:
        True if deletion succeeded, False otherwise.
    """
    api_key = _get_elevenlabs_key()
    if not _valid_key(api_key):
        logger.error("Cannot delete voice clone: ElevenLabs API key not configured.")
        return False

    persona = await db.persona_engines.find_one({"user_id": user_id})
    if not persona:
        return False

    voice_id = persona.get("voice_clone_id")
    if not voice_id:
        return False

    # Call ElevenLabs DELETE
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.delete(
                f"{ELEVENLABS_API_BASE}/voices/{voice_id}",
                headers={"xi-api-key": api_key},
            )
        if resp.status_code not in (200, 204):
            logger.warning(
                f"ElevenLabs voice delete returned {resp.status_code} for voice {voice_id}: {resp.text[:300]}"
            )
            # Continue to clear local record even if remote fails (voice may already be gone)
    except Exception as e:
        logger.error(f"ElevenLabs voice delete request error: {e}")

    # Clear from persona_engines
    now = datetime.now(timezone.utc)
    await db.persona_engines.update_one(
        {"user_id": user_id},
        {
            "$set": {"updated_at": now},
            "$unset": {
                "voice_clone_id": "",
                "voice_clone_name": "",
                "voice_clone_created_at": "",
                "voice_sample_urls": "",
                "voice_samples_uploaded_at": "",
            },
        },
    )

    logger.info(f"Voice clone deleted for user {user_id} (voice_id={voice_id})")
    return True


async def generate_speech_with_clone(
    user_id: str,
    text: str,
    stability: float = 0.5,
    similarity_boost: float = 0.75,
) -> Dict[str, Any]:
    """Generate speech using the user's cloned voice, falling back to defaults.

    If the user has a ``voice_clone_id`` stored in ``persona_engines``, that
    voice is used.  Otherwise, the standard default ElevenLabs voice is used.

    Args:
        user_id: The owning user's ID.
        text: Text to synthesise.
        stability: ElevenLabs stability parameter (0-1).
        similarity_boost: ElevenLabs similarity boost (0-1).

    Returns:
        Same shape as ``_generate_elevenlabs`` result dict.
    """
    api_key = _get_elevenlabs_key()
    if not _valid_key(api_key):
        return {"generated": False, "error": "ElevenLabs API key not configured.", "provider": "elevenlabs"}

    # Look up clone
    persona = await db.persona_engines.find_one({"user_id": user_id})
    voice_id = None
    voice_source = "default"
    if persona and persona.get("voice_clone_id"):
        voice_id = persona["voice_clone_id"]
        voice_source = "clone"

    if not voice_id:
        voice_id = DEFAULT_VOICES["elevenlabs"][0]["id"]

    result = await _generate_elevenlabs(text, voice_id, stability, similarity_boost)
    result["voice_source"] = voice_source
    return result
