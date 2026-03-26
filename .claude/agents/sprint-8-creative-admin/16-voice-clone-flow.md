# Agent: Voice Cloning — Upload Sample + Create ElevenLabs Clone
Sprint: 8 | Branch: feat/voice-clone-flow | PR target: dev
Depends on: Sprint 4 merged (billing gates this), Sprint 2 merged (R2 hardened)

## Context
agents/voice.py supports ElevenLabs TTS but there is no flow for a user to upload
their own voice samples to create a personalised clone. ElevenLabs supports clone
creation via POST /v1/voices/add — we never built the intake flow. The voice_clone_id
field exists on persona_engines but is always null.

## Files You Will Touch
- backend/routes/persona.py              (MODIFY — add voice clone endpoints)
- backend/agents/voice.py               (MODIFY — add clone creation + deletion)
- backend/services/media_storage.py     (MODIFY — support audio MIME types)
- frontend/src/pages/Persona.jsx        (MODIFY — add Voice Clone section)

## Files You Must Read First (do not modify)
- backend/agents/voice.py              (read fully — current TTS flow and ElevenLabs key usage)
- backend/routes/uploads.py            (understand file upload pattern — replicate it)
- backend/services/media_storage.py    (understand R2 upload — add audio MIME support)
- backend/services/credits.py         (TIER_CONFIGS — confirm studio/agency have voice clone access)
- backend/config.py                   (settings.llm.elevenlabs_key)

## Step 1: Add audio MIME types to media_storage.py
Find the allowed file types list. Add:
`"audio/mpeg", "audio/wav", "audio/x-wav", "audio/mp4", "audio/ogg"`
Max size for audio: 25MB per file.

## Step 2: Add voice clone endpoints to persona.py

```python
# POST /api/persona/voice-clone/samples
# — Upload 1-5 audio samples (wav/mp3, 1-25MB each)
# — Saves to R2 at path: voice-samples/{user_id}/{filename}
# — Stores R2 URLs in db.persona_engines[user_id].voice_sample_urls list
# — Tier gate: studio or agency only

# POST /api/persona/voice-clone/create
# — Triggers clone creation from stored sample URLs
# — Body: { "voice_name": str }
# — Calls voice.create_voice_clone(user_id, sample_urls, voice_name)
# — Returns: { "voice_id": str, "status": "created" | "processing" }

# GET /api/persona/voice-clone
# — Returns current clone status:
#   { "has_clone": bool, "voice_id": str|None, "voice_name": str|None,
#     "sample_count": int, "created_at": datetime|None }

# DELETE /api/persona/voice-clone
# — Calls ElevenLabs DELETE /v1/voices/{voice_id}
# — Clears voice_clone_id and voice_sample_urls from persona_engines
```

Tier guard on all endpoints:
```python
if current_user.get("subscription_tier") not in ("studio", "agency"):
    raise HTTPException(
        status_code=403,
        detail="Voice cloning requires Studio or Agency plan"
    )
```

## Step 3: Add clone creation and deletion to voice.py

```python
async def create_voice_clone(
    user_id: str,
    sample_urls: list[str],
    voice_name: str
) -> dict:
    """
    Downloads audio files from R2 URLs and submits to ElevenLabs.
    ElevenLabs endpoint: POST https://api.elevenlabs.io/v1/voices/add
    Headers: xi-api-key: {elevenlabs_key}
    Form data: name={voice_name}, files[]={audio_bytes for each sample}
    
    On success: 
      - Stores voice_id in db.persona_engines[user_id].voice_clone_id
      - Stores voice_name in db.persona_engines[user_id].voice_clone_name
      - Returns {"voice_id": str, "status": "created", "name": voice_name}
    
    On failure:
      - Logs full ElevenLabs error response
      - Returns {"error": str, "status": "failed"}
    
    Important: Download each file from R2 using httpx before submitting.
    Do not pass R2 URLs directly to ElevenLabs — it cannot reach them.
    """

async def delete_voice_clone(user_id: str) -> bool:
    """
    Calls: DELETE https://api.elevenlabs.io/v1/voices/{voice_id}
    Headers: xi-api-key: {elevenlabs_key}
    Then clears voice_clone_id and voice_sample_urls from persona_engines.
    Returns True on success, False on failure.
    """

async def generate_speech_with_clone(
    user_id: str,
    text: str,
    stability: float = 0.5,
    similarity_boost: float = 0.75
) -> dict:
    """
    Uses the user's cloned voice_id if available, falls back to default voice.
    Checks db.persona_engines[user_id].voice_clone_id first.
    Calls: POST https://api.elevenlabs.io/v1/text-to-speech/{voice_id}
    """
```

## Step 4: Frontend — Voice Clone section in Persona page
Add a "Voice Clone" card/section in the Persona page (show only for studio/agency tiers):
1. Upload zone: drag-and-drop or click to select 1-5 audio files (show file size limits)
2. Sample preview list: show uploaded samples with play button and remove button
3. "Create My Voice Clone" button — triggers POST /create — shows loading spinner
4. Status display: "Clone Active ✓" with voice name when created
5. "Delete Clone" danger button with confirmation dialog
6. For free/pro users: show a locked card with upgrade CTA

## Definition of Done
- POST /api/persona/voice-clone/samples accepts and stores audio to R2
- POST /api/persona/voice-clone/create calls ElevenLabs and stores voice_id
- generate_speech_with_clone uses cloned voice_id when available
- Frontend shows voice clone UI for studio/agency, upgrade prompt for others
- PR created to dev: "feat: voice clone flow — sample upload and ElevenLabs clone creation"