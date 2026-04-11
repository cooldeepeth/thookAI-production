# Phase 27: Onboarding Reimagination - Research

**Researched:** 2026-04-12
**Domain:** React multi-step wizard, browser MediaRecorder API, persona schema extension, FastAPI route patching
**Confidence:** HIGH

## Summary

Phase 27 extends the existing three-phase onboarding wizard to collect voice samples (via browser MediaRecorder), writing-style posts, and visual identity preferences, then fixes the LLM model name bug so real Claude-powered persona generation works in production. The existing frontend wizard (`Onboarding/index.jsx` + `PhaseOne|Two|Three.jsx`) is a solid foundation — all three phases exist and render correctly. The backend route (`backend/routes/onboarding.py`) already uses the correct model string `"claude-sonnet-4-20250514"` in its current state after prior Phase 26 work; the "known bug" string `"claude-4-sonnet-20250514"` mentioned in STATE.md has **already been corrected** in the current source files. Verify this in the file before adding a separate fix task.

The new persona fields (`voice_style`, `visual_preferences`, `writing_samples`, `personality_traits`) do not yet exist anywhere in the backend — they must be added to the `persona_doc` written by `generate_persona`. The frontend has no save-as-you-go (localStorage resume) logic, no voice recording UI, no visual palette selector, and no style fingerprint step beyond the existing `PhaseOne` paste-and-analyze flow.

**Primary recommendation:** Extend the existing wizard with two new steps (voice recording, visual palette) inserted between the current PhaseOne and PhaseTwo, persist draft state to localStorage for resume, extend the backend persona schema with the four new fields, and pass them into the PERSONA_PROMPT for richer LLM output.

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| ONBD-01 | Multi-step wizard with progress indicator and animations | Existing wizard has 3 steps + progress stepper; needs to expand to 5 steps and show step N of total explicitly |
| ONBD-02 | Voice sample recording in browser (no upload required) | Browser MediaRecorder API available in all modern browsers; needs new wizard step + backend upload endpoint |
| ONBD-03 | Paste 3-5 past posts for writing style analysis with style fingerprint summary | PhaseOne already handles paste + analyze-posts; needs style fingerprint confirmation UI overlay |
| ONBD-04 | Visual identity palette — at least 6 options stored in persona.visual_preferences | No palette step exists; needs new wizard step + persona schema field |
| ONBD-05 | Persona generation uses all inputs; no null fields for voice_style, visual_preferences, writing_samples, personality_traits | Backend PERSONA_PROMPT and persona_doc must include all four new fields |
| ONBD-06 | Persona stores voice_style, visual_preferences, writing_samples, personality_traits | None of these four fields exist in the current persona_doc; all four must be added |
| ONBD-07 | Save-as-you-go, skip/back navigation, error recovery at every step | No localStorage persistence today; needs draft state saved on every step transition |
| ONBD-08 | LLM model name bug fixed | Current code in onboarding.py already shows the correct model string; verify file to confirm, then mark done or fix if still wrong |
</phase_requirements>

---

## Project Constraints (from CLAUDE.md)

- Branch naming: `feat/onboarding-reimagination` from `dev`, PR targeting `dev`
- Config: All settings via `backend/config.py` dataclasses — never `os.environ.get()` directly in route files
- Database: Always `from database import db` with Motor async methods
- LLM model: `claude-sonnet-4-20250514` (Anthropic primary)
- All new Python packages must be added to `backend/requirements.txt`
- All new npm packages must be noted in PR description
- After any change to `backend/agents/`, verify full pipeline flow
- Frontend: Use `apiFetch()` from `@/lib/api` — never raw `fetch()`
- Frontend: Use design system tokens (`lime`, `surface`, `violet`, `font-display`, Framer Motion entry animations)
- Frontend: File naming — PascalCase for React components, camelCase for utilities
- Tests: `cd backend && pytest` before commit; 80% coverage minimum
- Functions < 50 lines; files < 800 lines

---

## Standard Stack

### Core (already in project)

| Library | Version | Purpose | Notes |
|---------|---------|---------|-------|
| React | 18.3.1 | UI framework | Already installed |
| Framer Motion | 12.38.0 | Step transition animations | Already used in wizard |
| Lucide React | 0.507.0 | Icons | Already used |
| `apiFetch` | project-internal | API calls | Must use — never raw fetch |
| FastAPI | 0.110.1 | Backend routes | Already installed |
| Motor / MongoDB | 3.3.1 / 7+ | Persona persistence | Already in use |
| anthropic SDK | 0.34.0 | LLM persona generation | Already in use |

### New Browser APIs (no install)

| API | Purpose | Support | Notes |
|-----|---------|---------|-------|
| `MediaRecorder` | Record voice sample in-browser | Chrome 47+, Firefox 25+, Safari 14.1+ | Available globally via window; no npm package needed |
| `navigator.mediaDevices.getUserMedia` | Mic permission + audio stream | Same as MediaRecorder | Requires HTTPS in production (Vercel satisfies this) |
| `URL.createObjectURL` | Local audio playback blob | Universal | Used for playback control after recording |

### Supporting (new endpoints/fields)

| Item | Type | Purpose |
|------|------|---------|
| `POST /api/onboarding/save-progress` | New backend endpoint | Save partial wizard state to MongoDB for resume |
| `GET /api/onboarding/progress` | New backend endpoint | Retrieve saved draft on return visit |
| `POST /api/onboarding/upload-voice` | New backend endpoint | Upload recorded voice blob to R2 (fallback: store as base64 metadata) |
| `persona_engines.voice_style` | New schema field | Textual description of voice style derived from recording metadata |
| `persona_engines.visual_preferences` | New schema field | Palette key selected by user |
| `persona_engines.writing_samples` | New schema field | Array of pasted post texts used for analysis |
| `persona_engines.personality_traits` | New schema field | Array of traits derived by LLM from all inputs |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Browser MediaRecorder | File upload (audio) | MediaRecorder is no-upload UX; requirement explicitly says "no upload required" — locked |
| R2 for voice storage | Store as base64 in MongoDB | R2 may not be configured in dev/staging; base64 (< 1MB for 30s audio at low bitrate) is acceptable fallback; use R2 when available |
| New save-progress endpoint | localStorage only | localStorage is sufficient for resume; backend endpoint adds resilience but adds complexity — localStorage is the primary mechanism per ONBD-07 |

**Installation:** No new npm packages required. No new Python packages required (MediaRecorder is browser-native; voice blob upload uses existing `media_storage.py` pattern).

---

## Architecture Patterns

### Recommended Wizard Structure (expanded from 3 to 5 wizard steps)

```
OnboardingWizard (index.jsx)
├── Step 1: WritingStyleStep  (renamed/extended PhaseOne — paste posts, get style fingerprint)
├── Step 2: VoiceRecordingStep (NEW — 30s browser recording, playback confirm)
├── Step 3: VisualPaletteStep  (NEW — pick from 6 palette options)
├── Step 4: InterviewStep      (current PhaseTwo — 7 interview questions)
└── Step 5: PersonaRevealStep  (current PhaseThree — persona card display)
```

Each step renders inside `AnimatePresence mode="wait"` with `motion.div` entry animations — consistent with existing pattern.

### Pattern 1: Browser MediaRecorder for Voice Capture

**What:** Use native `MediaRecorder` API to capture mic audio as a WebM/Opus blob. Playback immediately via `URL.createObjectURL`.
**When to use:** Step 2 (VoiceRecordingStep). The 30-second limit is enforced by a `setTimeout` that stops recording automatically.

```jsx
// Source: MDN Web Docs — MediaRecorder API
const [recording, setRecording] = useState(false);
const [audioBlob, setAudioBlob] = useState(null);
const [audioUrl, setAudioUrl] = useState(null);
const mediaRecorderRef = useRef(null);
const chunksRef = useRef([]);

const startRecording = async () => {
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  const recorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });
  chunksRef.current = [];
  recorder.ondataavailable = (e) => chunksRef.current.push(e.data);
  recorder.onstop = () => {
    const blob = new Blob(chunksRef.current, { type: 'audio/webm' });
    setAudioBlob(blob);
    setAudioUrl(URL.createObjectURL(blob));
    stream.getTracks().forEach(t => t.stop()); // release mic
  };
  mediaRecorderRef.current = recorder;
  recorder.start();
  setRecording(true);
  // Auto-stop at 30 seconds
  setTimeout(() => {
    if (recorder.state === 'recording') recorder.stop();
    setRecording(false);
  }, 30000);
};

const stopRecording = () => {
  mediaRecorderRef.current?.stop();
  setRecording(false);
};
```

**MIME type fallback:** Safari supports `audio/mp4` not `audio/webm`. Check `MediaRecorder.isTypeSupported('audio/webm')` first.

```jsx
const mimeType = MediaRecorder.isTypeSupported('audio/webm') ? 'audio/webm' : 'audio/mp4';
```

### Pattern 2: localStorage Draft Persistence for Resume (ONBD-07)

**What:** Save the current wizard step and all collected answers to `localStorage` on every transition. Read on mount to resume.
**When to use:** `OnboardingWizard` (index.jsx) — single source of truth for wizard state.

```jsx
// On every step transition — save current state
const DRAFT_KEY = 'thook_onboarding_draft';

const saveDraft = (step, data) => {
  localStorage.setItem(DRAFT_KEY, JSON.stringify({ step, ...data, savedAt: Date.now() }));
};

const loadDraft = () => {
  try {
    const raw = localStorage.getItem(DRAFT_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch { return null; }
};

const clearDraft = () => localStorage.removeItem(DRAFT_KEY);

// In useEffect on mount:
useEffect(() => {
  const draft = loadDraft();
  if (draft && !user?.onboarding_completed) {
    setStep(draft.step || 1);
    // restore other state fields from draft
  }
}, []);

// Clear draft after persona is saved:
// Call clearDraft() after successful generate-persona call
```

### Pattern 3: Visual Palette Step

**What:** Display 6 palette options as clickable cards. Store the selected key in state and pass to generate-persona.
**When to use:** Step 3 (VisualPaletteStep).

The 6 palette options (confirmed by ONBD-04):

| Key | Label | Description |
|-----|-------|-------------|
| `bold` | Bold | High contrast, strong typography, dark backgrounds |
| `minimal` | Minimal | Clean whites, generous whitespace, subtle accents |
| `corporate` | Corporate | Navy/grey, structured, professional |
| `creative` | Creative | Colorful, playful, expressive |
| `warm` | Warm | Earth tones, amber, approachable |
| `dark` | Dark | Deep blacks, neon accents, tech aesthetic |

### Pattern 4: Backend Persona Schema Extension

**What:** Add four new fields to the `persona_doc` dictionary in `generate_persona` endpoint and include them in `PERSONA_PROMPT`.
**When to use:** `backend/routes/onboarding.py` — `generate_persona` function.

```python
# New fields in GeneratePersonaRequest
class GeneratePersonaRequest(BaseModel):
    answers: List[Dict[str, Any]] = Field(min_length=1)
    posts_analysis: Optional[str] = None
    voice_sample_url: Optional[str] = None      # NEW
    visual_preference: Optional[str] = None      # NEW — palette key
    writing_samples: Optional[List[str]] = None  # NEW — list of pasted posts

# New fields in persona_doc (added to the $set payload)
persona_doc = {
    ...existing fields...,
    "voice_style": _derive_voice_style(data.voice_sample_url, persona_card),   # NEW
    "visual_preferences": data.visual_preference or "minimal",                   # NEW
    "writing_samples": data.writing_samples or [],                               # NEW
    "personality_traits": persona_card.get("personality_traits", []),            # NEW — from LLM output
}
```

The `PERSONA_PROMPT` must be extended to include `visual_preference` in its context and must output `personality_traits` in the JSON schema.

### Pattern 5: Style Fingerprint Confirmation UI

**What:** After the existing post analysis API call in PhaseOne/WritingStyleStep, surface a "style fingerprint" summary the user must confirm before proceeding.
**When to use:** In the `result` rendering block of the writing style step.

Currently `PhaseOne` shows analysis text and has a "Continue to interview" button. The fingerprint summary is already surfaced via the `result.analysis` text. What's missing is explicit user confirmation framing. Add a "This looks right" / "Edit my posts" choice pair.

### Anti-Patterns to Avoid

- **Unmounted recorder still capturing:** Always call `stream.getTracks().forEach(t => t.stop())` in `recorder.onstop`. If recording is interrupted by navigation, also stop in a cleanup `useEffect` return function.
- **localStorage stale draft after completion:** Never read the draft once `user.onboarding_completed` is true. Clear the draft immediately after `generate-persona` succeeds.
- **Blocking generate-persona on voice upload:** Voice upload to R2 should be fire-and-forget or pre-upload in background. Persona generation should not wait for R2 — store the URL if available, use null/empty string if not.
- **Hardcoded model names in onboarding.py:** The model string must come from a constant or CLAUDE.md-mandated literal `"claude-sonnet-4-20250514"`. Never use a custom string.
- **Mutating answers array in PhaseTwo:** Current `handleBack` correctly slices the answers array (immutable pattern). Maintain this pattern in any changes.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Browser audio recording | Custom WebSocket streaming | Native `MediaRecorder` API | Built into every modern browser; handles codec selection, chunking, and streaming internally |
| Audio format detection | Manual codec negotiation | `MediaRecorder.isTypeSupported()` | Single call returns boolean; handles Safari/Chrome differences |
| Audio playback from blob | Custom audio player | HTML `<audio>` element with `src={audioUrl}` | Native controls (play/pause/seek) with zero code |
| Form state management | Custom state machine | React `useState` + localStorage | Existing pattern in codebase; Zod validation is frontend-only (no schema library needed here) |
| Palette selection persistence | Backend API call per click | `useState` + included in final generate-persona call | Palette choice is transient until generate-persona; no mid-step save needed |

**Key insight:** The MediaRecorder API eliminates all server-side streaming complexity. A 30-second audio sample at 128kbps ≈ 480KB — small enough to upload as a single multipart POST to R2 or encode as a URL once saved.

---

## Common Pitfalls

### Pitfall 1: MediaRecorder Not Available on HTTP (dev)

**What goes wrong:** `navigator.mediaDevices` is undefined on non-HTTPS pages. Local dev via `http://localhost` actually works (localhost is a secure context), but `http://` on any non-localhost origin fails.
**Why it happens:** Browser security requirement — mic access requires a secure context.
**How to avoid:** Always check `navigator.mediaDevices` exists before calling `getUserMedia`. Show a clear error if undefined (not a silent failure).
**Warning signs:** `TypeError: Cannot read properties of undefined (reading 'getUserMedia')`

```jsx
if (!navigator.mediaDevices?.getUserMedia) {
  setError('Voice recording requires a secure browser connection. Please use HTTPS.');
  return;
}
```

### Pitfall 2: Memory Leak from Object URLs

**What goes wrong:** Calling `URL.createObjectURL(blob)` creates a browser memory handle that is never released.
**Why it happens:** The browser holds a reference until `URL.revokeObjectURL()` is called.
**How to avoid:** Revoke in a `useEffect` cleanup or when the component unmounts.

```jsx
useEffect(() => {
  return () => { if (audioUrl) URL.revokeObjectURL(audioUrl); };
}, [audioUrl]);
```

### Pitfall 3: LLM Returning null/generic for New Fields

**What goes wrong:** If `personality_traits` is not in the PERSONA_PROMPT JSON schema, the LLM does not include it, and the persona_doc stores an empty list — violating ONBD-05.
**Why it happens:** The current PERSONA_PROMPT schema has no `personality_traits` field.
**How to avoid:** Explicitly add `personality_traits` (array of strings) to the PERSONA_PROMPT JSON structure with an example. Also add it to the `_generate_smart_persona` fallback.

### Pitfall 4: Draft Resume Conflict with onboarding_completed Flag

**What goes wrong:** User completes onboarding, draft remains in localStorage. Next session loads draft and tries to resume a completed onboarding.
**Why it happens:** Draft is not cleared after successful persona generation.
**How to avoid:** Call `clearDraft()` immediately after `generate-persona` succeeds AND in the `useEffect` that checks `user.onboarding_completed`.

### Pitfall 5: Test Count Mismatch — 7 vs N Questions

**What goes wrong:** `test_questions_module_has_7_questions` in `test_onboarding_core.py` will fail if additional questions are added to `INTERVIEW_QUESTIONS`.
**Why it happens:** The test hardcodes `assert len(INTERVIEW_QUESTIONS) == 7`.
**How to avoid:** Do NOT add questions to `INTERVIEW_QUESTIONS`. The voice recording and visual palette steps are new wizard steps in the frontend only — they are not interview questions served from the backend questions endpoint. This keeps the test passing without modification.

### Pitfall 6: Model Name Bug — Verify Before Creating a Fix Task

**What goes wrong:** STATE.md and CLAUDE.md both say the bug is `"claude-4-sonnet-20250514"` in onboarding.py. However, the current file at `backend/routes/onboarding.py` lines 124 and 168 both read `"claude-sonnet-4-20250514"` — the correct string. The fix may have been applied already.
**How to avoid:** The planner should verify the current file state before writing a fix task. If the correct string is present, ONBD-08 is already satisfied by the current code — document it but don't create redundant work.
**Warning signs:** If `persona_source` consistently returns `"smart_fallback"` in production despite `ANTHROPIC_API_KEY` being set, the model name is wrong (or the key is invalid).

### Pitfall 7: CSRF Token on Voice Upload (multipart/form-data)

**What goes wrong:** Uploading an audio blob via `FormData` POST fails CSRF validation if the CSRF header is missing.
**Why it happens:** The existing `apiFetch()` correctly skips `Content-Type: application/json` for `FormData` bodies but still injects `X-CSRF-Token` — this is correct behavior. Direct `fetch()` calls would miss the CSRF header.
**How to avoid:** Always use `apiFetch()` for the voice upload call. Pass the `FormData` blob as the body directly.

---

## Code Examples

### Voice Recording Component (verified against MDN spec)

```jsx
// Source: MDN Web Docs — MediaRecorder API
import { useState, useRef, useEffect } from 'react';
import { Mic, Square, Play } from 'lucide-react';

export default function VoiceRecordingStep({ onComplete }) {
  const [recording, setRecording] = useState(false);
  const [audioUrl, setAudioUrl] = useState(null);
  const [audioBlob, setAudioBlob] = useState(null);
  const [secondsLeft, setSecondsLeft] = useState(30);
  const [error, setError] = useState(null);
  const recorderRef = useRef(null);
  const chunksRef = useRef([]);
  const timerRef = useRef(null);

  useEffect(() => {
    return () => {
      if (audioUrl) URL.revokeObjectURL(audioUrl);
      clearInterval(timerRef.current);
    };
  }, [audioUrl]);

  const startRecording = async () => {
    setError(null);
    if (!navigator.mediaDevices?.getUserMedia) {
      setError('Voice recording requires a secure connection (HTTPS).');
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mimeType = MediaRecorder.isTypeSupported('audio/webm') ? 'audio/webm' : 'audio/mp4';
      const recorder = new MediaRecorder(stream, { mimeType });
      chunksRef.current = [];
      recorder.ondataavailable = (e) => chunksRef.current.push(e.data);
      recorder.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: mimeType });
        setAudioBlob(blob);
        setAudioUrl(URL.createObjectURL(blob));
        stream.getTracks().forEach(t => t.stop());
      };
      recorderRef.current = recorder;
      recorder.start();
      setRecording(true);
      setSecondsLeft(30);
      let s = 30;
      timerRef.current = setInterval(() => {
        s -= 1;
        setSecondsLeft(s);
        if (s <= 0) {
          clearInterval(timerRef.current);
          recorder.stop();
          setRecording(false);
        }
      }, 1000);
    } catch (err) {
      setError('Microphone access denied. Please allow mic permissions and try again.');
    }
  };

  const stopEarly = () => {
    clearInterval(timerRef.current);
    recorderRef.current?.stop();
    setRecording(false);
  };

  return (
    <div className="flex items-center justify-center min-h-full p-8">
      <div className="max-w-lg w-full text-center">
        {/* UI rendered based on state: idle / recording / recorded */}
      </div>
    </div>
  );
}
```

### Backend: Extended GeneratePersonaRequest and persona_doc

```python
# Source: existing onboarding.py — extend in place

class GeneratePersonaRequest(BaseModel):
    answers: List[Dict[str, Any]] = Field(min_length=1, description="At least one answer required")
    posts_analysis: Optional[str] = None
    voice_sample_url: Optional[str] = None       # NEW: R2 URL or None
    visual_preference: Optional[str] = None       # NEW: palette key
    writing_samples: Optional[List[str]] = None   # NEW: list of raw post texts

# In generate_persona() after persona_card is obtained:
persona_doc = {
    "user_id": user_id,
    "card": persona_card,
    "voice_style": persona_card.get("voice_style", ""),          # NEW
    "visual_preferences": data.visual_preference or "minimal",    # NEW
    "writing_samples": data.writing_samples or [],                # NEW
    "personality_traits": persona_card.get("personality_traits", []),  # NEW
    # ... existing voice_fingerprint, content_identity, etc.
}
```

### Backend: Extended PERSONA_PROMPT schema

```python
# Add to PERSONA_PROMPT JSON schema — include personality_traits and voice_style:
PERSONA_PROMPT = """...
Return ONLY valid JSON:
{{
  ...existing fields...,
  "personality_traits": ["trait1", "trait2", "trait3"],
  "voice_style": "Description of inferred voice style from writing patterns",
}}
..."""
```

### Backend: _generate_smart_persona fallback extension

```python
def _generate_smart_persona(answers: list, visual_preference: str = "minimal", writing_samples: list = None) -> dict:
    """Add personality_traits and voice_style to fallback output."""
    result = { ...existing logic... }
    result["personality_traits"] = ["Analytical", "Strategic", "Authentic"]  # sensible defaults
    result["voice_style"] = f"Professional {style_words} voice with structured insights"
    return result
```

### Frontend: localStorage Draft Save/Load

```jsx
// In OnboardingWizard index.jsx
const DRAFT_KEY = 'thook_onboarding_draft_v2';  // v2 suffix to avoid old draft conflicts

const saveDraft = (updates) => {
  const existing = loadDraft() || {};
  localStorage.setItem(DRAFT_KEY, JSON.stringify({ ...existing, ...updates, savedAt: Date.now() }));
};

const loadDraft = () => {
  try { return JSON.parse(localStorage.getItem(DRAFT_KEY) || 'null'); }
  catch { return null; }
};

const clearDraft = () => localStorage.removeItem(DRAFT_KEY);
```

---

## Runtime State Inventory

> This section is not applicable. This is a feature extension phase, not a rename/refactor/migration phase. No stored keys, collection names, or OS-registered state are being renamed.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|-------------|-----------|---------|----------|
| ANTHROPIC_API_KEY | LLM persona generation | Env-dependent | — | Smart fallback persona (already coded) |
| R2 storage (R2_* env vars) | Voice recording upload | Env-dependent | — | Skip R2 upload; store voice_sample_url as null; persona still generates |
| `navigator.mediaDevices` (browser) | Voice recording step | Available on HTTPS | — | Show informational error; skip voice step is allowed by ONBD-02 (user can "record or upload") |
| HTTPS (Vercel) | MediaRecorder secure context | Available in production | — | localhost dev also works (secure context) |
| Python 3.11 | Backend | Available | 3.11 | — |
| FastAPI 0.110.1 | Backend | Available | 0.110.1 | — |
| MongoDB Motor | Persona storage | Available | 3.3.1 | — |

**Missing dependencies with no fallback:** None — all blocking dependencies are already available.

**Missing dependencies with fallback:**
- R2: Voice blob can be skipped (voice_sample_url = null). Persona generation still works.
- ANTHROPIC_API_KEY not set: Smart fallback persona runs (already implemented).

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.0.0 + pytest-asyncio 0.23.0 |
| Config file | `backend/pytest.ini` (asyncio_mode=auto) |
| Quick run command | `cd backend && pytest tests/test_onboarding_core.py -x -q` |
| Full suite command | `cd backend && pytest -x -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| ONBD-01 | Wizard has 5 steps, progress indicator shows step N of total | unit (frontend — no pytest) | Manual Playwright check | No — Wave 0 gap |
| ONBD-02 | Voice recording captured in browser, playback confirmed | unit (browser API mock) | Manual Playwright check | No — Wave 0 gap |
| ONBD-03 | Paste posts, receive style fingerprint confirmation | unit: `test_analyze_posts_*` in test_onboarding_core.py | `pytest tests/test_onboarding_core.py -k analyze -x` | Partial — analyze-posts tested; fingerprint confirm UI is frontend-only |
| ONBD-04 | 6 visual palette options, stored in persona.visual_preferences | unit: new test for visual_preferences in persona_doc | `pytest tests/test_onboarding_core.py -k visual -x` | No — Wave 0 gap |
| ONBD-05 | persona_card includes non-null voice_style, visual_preferences, writing_samples, personality_traits | unit: extend TestPersonaDocStructure | `pytest tests/test_onboarding_core.py -k persona_doc -x` | Partial — existing tests cover voice_fingerprint; new fields not tested |
| ONBD-06 | Persona stores four new fields | unit: test persona_engines document after generate-persona | `pytest tests/test_onboarding_core.py::TestPersonaDocStructure -x` | Partial |
| ONBD-07 | Draft saved to localStorage; resume from last step | unit (frontend — no pytest) | Manual check or Playwright | No — Wave 0 gap |
| ONBD-08 | Correct model name `claude-sonnet-4-20250514` in onboarding.py | unit: `test_correct_model_name_in_generate_persona_source` (line 107) | `pytest tests/test_onboarding_core.py::TestModelNameCorrectness -x` | Yes — test already exists and passes |

### Sampling Rate

- **Per task commit:** `cd backend && pytest tests/test_onboarding_core.py -x -q`
- **Per wave merge:** `cd backend && pytest -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/test_onboarding_core.py` — add test class `TestNewPersonaFields` covering: `visual_preferences`, `writing_samples`, `personality_traits`, `voice_style` fields present in persona_doc after `generate_persona`
- [ ] `tests/test_onboarding_core.py` — add test `test_generate_persona_accepts_visual_preference` and `test_generate_persona_accepts_writing_samples`
- [ ] `tests/test_onboarding_core.py` — add test `test_smart_fallback_includes_personality_traits` and `test_smart_fallback_includes_voice_style`

*(Frontend wizard tests — no pytest gap; those are manual or Playwright. No Wave 0 blocking gap for backend pytest.)*

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| File upload for audio samples | Browser MediaRecorder (in-browser capture) | 2023+ best practice | Zero friction; no file picker needed |
| Wizard state in React only (lost on refresh) | localStorage persistence | Standard since React went SPA-first | Survives page close/reload |
| Generic LLM persona (text answers only) | Multi-modal input (text + voice + visual) | Emerging 2024-2025 | Richer, more accurate persona card |

**Deprecated/outdated:**
- `"claude-4-sonnet-20250514"` (wrong model string): Replaced by `"claude-sonnet-4-20250514"`. May or may not still be present — check current file.

---

## Open Questions

1. **Voice sample storage when R2 is not configured**
   - What we know: R2 is optional (`has_r2()` returns False in dev). Voice blob is ~480KB for 30s at 128kbps.
   - What's unclear: Should we skip upload entirely and store null, or store base64 in MongoDB?
   - Recommendation: Store `voice_sample_url = None` in persona_doc when R2 is unavailable. persona generation proceeds without it. This satisfies ONBD-02 (recording still captured in browser; playback control confirms it) without requiring R2 to be configured.

2. **Is ONBD-08 already done?**
   - What we know: Current `onboarding.py` (line 124, 168) shows `"claude-sonnet-4-20250514"` — correct.
   - What's unclear: Was this fixed during Phase 26 backend hardening or was it always correct?
   - Recommendation: Planner should make ONBD-08 a verification task (check file, run model name test, mark done) rather than a code-change task.

3. **Exact mapping of "style fingerprint" to UI**
   - What we know: The existing PhaseOne already shows `result.analysis` text after analyze-posts. ONBD-03 says to "surface a style fingerprint summary the user can confirm."
   - What's unclear: Does this require a structured fingerprint UI (e.g., bullet tags like "Long-form", "Analytical") or is the prose analysis sufficient?
   - Recommendation: Parse `result.detected_patterns` from analyze-posts response (already returned by backend) and display as tag chips. User clicks "This is me" to confirm or "Edit posts" to go back.

---

## Sources

### Primary (HIGH confidence)

- MDN Web Docs — MediaRecorder API: https://developer.mozilla.org/en-US/docs/Web/API/MediaRecorder (browser support, `isTypeSupported`, onstop/ondataavailable events)
- Source code: `backend/routes/onboarding.py` — direct read of current implementation
- Source code: `frontend/src/pages/Onboarding/index.jsx`, `PhaseOne.jsx`, `PhaseTwo.jsx`, `PhaseThree.jsx` — current wizard structure
- Source code: `backend/tests/test_onboarding_core.py` — existing test coverage
- Source code: `backend/config.py` — LLM provider configuration pattern
- Source code: `.planning/REQUIREMENTS.md` — locked requirements ONBD-01 through ONBD-08

### Secondary (MEDIUM confidence)

- MDN — MediaDevices.getUserMedia: https://developer.mozilla.org/en-US/docs/Web/API/MediaDevices/getUserMedia (secure context requirements)
- MDN — URL.createObjectURL: https://developer.mozilla.org/en-US/docs/Web/API/URL/createObjectURL (blob audio playback pattern)

### Tertiary (LOW confidence)

- None. All claims verified against project source code or official browser API documentation.

---

## Metadata

**Confidence breakdown:**
- Backend schema extension: HIGH — current persona_doc structure read directly from source; new fields are straightforward additions
- Frontend wizard expansion: HIGH — existing wizard pattern is clean and extensible; MediaRecorder is well-documented
- LLM model name bug (ONBD-08): HIGH — current source code shows correct string; no fix needed unless file differs at execution time
- localStorage persistence: HIGH — standard browser API; no library needed
- Voice R2 upload: MEDIUM — R2 not configured in dev; fallback (null URL) is safe and confirmed by config.py pattern

**Research date:** 2026-04-12
**Valid until:** 2026-05-12 (stable domain — browser APIs and FastAPI patterns are stable over 30 days)
