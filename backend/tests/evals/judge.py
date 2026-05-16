"""LLM-as-judge for wedge content evals.

Scores a generated LinkedIn draft against the seed's persona card on five
dimensions. Uses Claude Sonnet directly via the Anthropic SDK (no fallback
to mock — a missing key should fail the eval loudly, not quietly).
"""
from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from typing import Any

import anthropic

logger = logging.getLogger(__name__)

JUDGE_MODEL = "claude-sonnet-4-20250514"
JUDGE_MAX_TOKENS = 1024
JUDGE_TIMEOUT_S = 45.0

JUDGE_SYSTEM = """You are an evaluation judge for a LinkedIn content generator used by non-native-English founders building in public. You score drafts on five dimensions with integer scores (0-10) and return STRICT JSON — no prose outside the JSON.

Scoring rubric:

1. voice_match (0-10): Does the draft sound like THIS specific persona (voice_descriptor, tone, hook_style, style_notes)? 10 = indistinguishable from the persona's own writing; 5 = generically professional; 0 = clearly a different voice.

2. ai_risk (0-10, LOWER IS BETTER): How AI-generated does it sound? 0 = reads as authored by a human; 5 = noticeably AI; 10 = obviously ChatGPT ("In today's fast-paced world", "Let's dive in", "The importance of", excessive em-dashes, tidy 3-beat structures, vague abstractions, motivational platitudes).

3. platform_fit (0-10): LinkedIn-appropriate for the content_type. For a post: hook in line 1, line breaks every 2-3 sentences, under 3000 chars, max 5 hashtags. 10 = ready to publish; 0 = wrong platform or format.

4. specificity (0-10): Does the draft use concrete numbers, specific events, named things, and first-person detail? 10 = every paragraph has a concrete artefact; 0 = entirely abstract.

5. regional_english_fit (0-10): Does the draft match the persona's regional English (US, UK, IN, AU)? 10 = natural in the target region; 0 = wrong register (e.g. American contractions in formal Indian English).

Additional boolean: overall_pass = true only if voice_match >= 7 AND ai_risk <= 4 AND platform_fit >= 7 AND specificity >= 6 AND regional_english_fit >= 7.

Return ONLY this JSON schema (no markdown fences, no commentary):

{
  "voice_match": <int 0-10>,
  "ai_risk": <int 0-10>,
  "platform_fit": <int 0-10>,
  "specificity": <int 0-10>,
  "regional_english_fit": <int 0-10>,
  "overall_pass": <bool>,
  "top_issue": "<one short sentence, the single biggest problem, or 'none' if overall_pass is true>"
}"""

JUDGE_USER_TEMPLATE = """PERSONA CARD:
creator_name: {creator_name}
writing_voice_descriptor: {voice_descriptor}
tone: {tone}
hook_style: {hook_style}
regional_english: {regional_english}
content_niche_signature: {niche}
writing_style_notes:
{style_notes}

SEED TOPIC: {topic}

PLATFORM: {platform}
CONTENT_TYPE: {content_type}

DRAFT TO SCORE:
---
{draft}
---

Return the JSON score object only."""


@dataclass(frozen=True)
class JudgeScore:
    voice_match: int
    ai_risk: int
    platform_fit: int
    specificity: int
    regional_english_fit: int
    overall_pass: bool
    top_issue: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "voice_match": self.voice_match,
            "ai_risk": self.ai_risk,
            "platform_fit": self.platform_fit,
            "specificity": self.specificity,
            "regional_english_fit": self.regional_english_fit,
            "overall_pass": self.overall_pass,
            "top_issue": self.top_issue,
        }


class JudgeError(RuntimeError):
    """Raised when the judge cannot produce a valid score."""


def _resolve_anthropic_key() -> str:
    key = (
        os.environ.get("ANTHROPIC_API_KEY")
        or os.environ.get("EMERGENT_LLM_KEY")
        or ""
    ).strip()
    if not key or key.lower().startswith("placeholder"):
        raise JudgeError(
            "ANTHROPIC_API_KEY not configured. Evals require a real Anthropic key; "
            "silent mock fallback is explicitly disallowed."
        )
    return key


def _extract_json(text: str) -> dict[str, Any]:
    """Pull the first JSON object out of the response, tolerating stray markdown fences."""
    stripped = text.strip()
    if stripped.startswith("```"):
        fence_end = stripped.find("```", 3)
        if fence_end > 0:
            inner = stripped[3:fence_end]
            if inner.startswith("json\n"):
                inner = inner[5:]
            stripped = inner.strip()
    # Find the outermost {...}
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start < 0 or end < 0 or end < start:
        raise JudgeError(f"Judge response contained no JSON object: {text[:200]!r}")
    return json.loads(stripped[start : end + 1])


def _validate_score(obj: dict[str, Any]) -> JudgeScore:
    required = {
        "voice_match",
        "ai_risk",
        "platform_fit",
        "specificity",
        "regional_english_fit",
        "overall_pass",
        "top_issue",
    }
    missing = required - obj.keys()
    if missing:
        raise JudgeError(f"Judge response missing keys: {sorted(missing)}")
    for k in ("voice_match", "ai_risk", "platform_fit", "specificity", "regional_english_fit"):
        v = obj[k]
        if not isinstance(v, int) or not (0 <= v <= 10):
            raise JudgeError(f"Judge field {k!r} must be int 0-10, got {v!r}")
    if not isinstance(obj["overall_pass"], bool):
        raise JudgeError(f"Judge field 'overall_pass' must be bool, got {obj['overall_pass']!r}")
    if not isinstance(obj["top_issue"], str):
        raise JudgeError(f"Judge field 'top_issue' must be str, got {obj['top_issue']!r}")
    return JudgeScore(
        voice_match=obj["voice_match"],
        ai_risk=obj["ai_risk"],
        platform_fit=obj["platform_fit"],
        specificity=obj["specificity"],
        regional_english_fit=obj["regional_english_fit"],
        overall_pass=obj["overall_pass"],
        top_issue=obj["top_issue"],
    )


def score_draft(
    draft: str,
    persona_card: dict[str, Any],
    topic: str,
    platform: str = "linkedin",
    content_type: str = "post",
) -> JudgeScore:
    """Score a single draft. Raises JudgeError on any failure."""
    key = _resolve_anthropic_key()
    style_notes_lines = persona_card.get("writing_style_notes") or []
    style_notes_text = "\n".join(f"  - {line}" for line in style_notes_lines)

    user_content = JUDGE_USER_TEMPLATE.format(
        creator_name=persona_card.get("creator_name", ""),
        voice_descriptor=persona_card.get("writing_voice_descriptor", ""),
        tone=persona_card.get("tone", ""),
        hook_style=persona_card.get("hook_style", ""),
        regional_english=persona_card.get("regional_english", ""),
        niche=persona_card.get("content_niche_signature", ""),
        style_notes=style_notes_text,
        topic=topic,
        platform=platform,
        content_type=content_type,
        draft=draft,
    )

    client = anthropic.Anthropic(api_key=key, timeout=JUDGE_TIMEOUT_S)
    try:
        response = client.messages.create(
            model=JUDGE_MODEL,
            max_tokens=JUDGE_MAX_TOKENS,
            system=JUDGE_SYSTEM,
            messages=[{"role": "user", "content": user_content}],
        )
    except anthropic.APIError as exc:
        raise JudgeError(f"Judge API error: {exc}") from exc

    if not response.content:
        raise JudgeError("Judge returned empty content")
    text = "".join(
        block.text for block in response.content if getattr(block, "type", None) == "text"
    )
    if not text.strip():
        raise JudgeError("Judge returned no text content")
    obj = _extract_json(text)
    return _validate_score(obj)
