"""Resolve which LLM API keys are available (direct provider env vars + optional Emergent)."""
from __future__ import annotations

from typing import Optional

from config import settings

_BAD_PREFIXES = (
    "placeholder",
    "sk-placeholder",
    "sk-ant-placeholder",
    "your_",
    "xxx",
    "pplx-placeholder",
)


def strip_valid_key(key: Optional[str]) -> bool:
    if not key or not str(key).strip():
        return False
    kl = str(key).lower().strip()
    if any(kl.startswith(p) for p in _BAD_PREFIXES):
        return False
    if "placeholder" in kl:
        return False
    return True


def openai_available() -> bool:
    return strip_valid_key(settings.llm.openai_key) or strip_valid_key(
        settings.llm.emergent_key
    )


def anthropic_available() -> bool:
    return strip_valid_key(settings.llm.anthropic_key) or strip_valid_key(
        settings.llm.emergent_key
    )


def gemini_available() -> bool:
    return (
        strip_valid_key(settings.llm.gemini_key)
        or strip_valid_key(settings.llm.emergent_key)
    )


def chat_constructor_key() -> str:
    """Default `api_key` for `LlmChat`; per-provider env overrides in `llm_client._resolve_key`."""
    return (
        (settings.llm.emergent_key or "")
        or (settings.llm.openai_key or "")
        or (settings.llm.anthropic_key or "")
        or (settings.llm.gemini_key or "")
        or ""
    )


def openai_api_key_for_rest() -> str:
    """Bearer token for OpenAI HTTP APIs (embeddings, TTS). Prefers direct OpenAI key."""
    if strip_valid_key(settings.llm.openai_key):
        return (settings.llm.openai_key or "").strip()
    if strip_valid_key(settings.llm.emergent_key):
        return (settings.llm.emergent_key or "").strip()
    return ""
