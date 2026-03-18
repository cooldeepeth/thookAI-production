"""Voice Agent for ThookAI.

Converts text to audio narration using ElevenLabs API.
"""
import os
import base64
import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

ELEVENLABS_API_KEY = os.environ.get('ELEVENLABS_API_KEY', '')

# Default voices
DEFAULT_VOICES = [
    {"id": "21m00Tcm4TlvDq8ikWAM", "name": "Rachel", "description": "American female, calm and professional"},
    {"id": "AZnzlk1XvdvUeBnXmlld", "name": "Domi", "description": "American female, strong and confident"},
    {"id": "EXAVITQu4vr4xnSDxMaL", "name": "Bella", "description": "American female, soft and warm"},
    {"id": "ErXwobaYiN019PkySvjV", "name": "Antoni", "description": "American male, well-rounded and calm"},
    {"id": "MF3mGyEYCl7XYWbV9V6O", "name": "Elli", "description": "American female, young and pleasant"},
    {"id": "TxGEqnHWrfWFTfGW9XjX", "name": "Josh", "description": "American male, deep and narrative"},
]

MAX_CHARS = 5000  # ElevenLabs character limit for standard tier


def _valid_key(key: str) -> bool:
    return bool(key) and not any(key.startswith(p) for p in ['placeholder', 'sk-placeholder', 'el-placeholder'])


async def generate_voice_narration(
    text: str,
    voice_id: Optional[str] = None,
    stability: float = 0.5,
    similarity_boost: float = 0.75
) -> Dict[str, Any]:
    """Generate voice narration from text using ElevenLabs.
    
    Args:
        text: Text to convert to speech
        voice_id: ElevenLabs voice ID (defaults to Rachel)
        stability: Voice stability (0-1)
        similarity_boost: Voice similarity (0-1)
    
    Returns:
        {audio_base64, audio_url, duration_estimate, voice_used, truncated}
    """
    if not _valid_key(ELEVENLABS_API_KEY):
        return _mock_voice(text)
    
    # Truncate if too long
    truncated = False
    if len(text) > MAX_CHARS:
        text = text[:MAX_CHARS]
        truncated = True
        logger.warning(f"Text truncated to {MAX_CHARS} characters")
    
    # Default voice
    if not voice_id:
        voice_id = DEFAULT_VOICES[0]["id"]  # Rachel
    
    try:
        from elevenlabs import ElevenLabs
        from elevenlabs.types import VoiceSettings
        
        client = ElevenLabs(api_key=ELEVENLABS_API_KEY)
        
        voice_settings = VoiceSettings(
            stability=stability,
            similarity_boost=similarity_boost,
            style=0.0,
            use_speaker_boost=True
        )
        
        # Generate audio
        audio_generator = client.text_to_speech.convert(
            text=text,
            voice_id=voice_id,
            model_id="eleven_multilingual_v2",
            voice_settings=voice_settings
        )
        
        # Collect audio data
        audio_data = b""
        for chunk in audio_generator:
            audio_data += chunk
        
        # Convert to base64
        audio_base64 = base64.b64encode(audio_data).decode('utf-8')
        
        # Estimate duration (rough: ~150 words per minute, ~5 chars per word)
        word_count = len(text.split())
        duration_estimate = round(word_count / 150 * 60, 1)  # seconds
        
        # Find voice name
        voice_name = next((v["name"] for v in DEFAULT_VOICES if v["id"] == voice_id), "Custom Voice")
        
        return {
            "audio_base64": audio_base64,
            "audio_url": f"data:audio/mpeg;base64,{audio_base64}",
            "duration_estimate": duration_estimate,
            "voice_used": {"id": voice_id, "name": voice_name},
            "char_count": len(text),
            "truncated": truncated,
            "generated": True
        }
    
    except Exception as e:
        logger.error(f"Voice agent error: {e}")
        error_msg = str(e).lower()
        
        if "quota" in error_msg or "limit" in error_msg:
            return {
                "generated": False,
                "error": "quota_exceeded",
                "message": "Voice generation quota exceeded. Please try again later."
            }
        elif "unauthorized" in error_msg or "invalid" in error_msg:
            return {
                "generated": False,
                "error": "invalid_key",
                "message": "Invalid ElevenLabs API key. Please check your settings."
            }
        
        return _mock_voice(text)


def _mock_voice(text: str) -> Dict[str, Any]:
    """Return mock voice data when API unavailable."""
    word_count = len(text.split())
    duration_estimate = round(word_count / 150 * 60, 1)
    
    return {
        "audio_base64": None,
        "audio_url": None,
        "duration_estimate": duration_estimate,
        "voice_used": {"id": "mock", "name": "Mock Voice"},
        "char_count": len(text),
        "truncated": len(text) > MAX_CHARS,
        "generated": False,
        "mock": True,
        "message": "Voice generation unavailable. Configure ELEVENLABS_API_KEY to enable."
    }


def get_available_voices() -> List[Dict[str, str]]:
    """Return list of available default voices."""
    return DEFAULT_VOICES


async def get_user_voices() -> List[Dict[str, Any]]:
    """Fetch user's custom cloned voices from ElevenLabs."""
    if not _valid_key(ELEVENLABS_API_KEY):
        return []
    
    try:
        from elevenlabs import ElevenLabs
        
        client = ElevenLabs(api_key=ELEVENLABS_API_KEY)
        voices_response = client.voices.get_all()
        
        return [
            {
                "id": voice.voice_id,
                "name": voice.name,
                "description": voice.description or "Custom voice",
                "category": voice.category
            }
            for voice in voices_response.voices
            if voice.category == "cloned"
        ]
    except Exception as e:
        logger.error(f"Failed to fetch user voices: {e}")
        return []
