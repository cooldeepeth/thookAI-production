"""Resolve which LLM API keys are available (direct provider env vars + optional Emergent)."""
from __future__ import annotations

import os
from typing import Optional

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
    return strip_valid_key(os.environ.get("OPENAI_API_KEY")) or strip_valid_key(
        os.environ.get("EMERGENT_LLM_KEY")
    )


def anthropic_available() -> bool:
    return strip_valid_key(os.environ.get("ANTHROPIC_API_KEY")) or strip_valid_key(
        os.environ.get("EMERGENT_LLM_KEY")
    )


def gemini_available() -> bool:
    return (
        strip_valid_key(os.environ.get("GEMINI_API_KEY"))
        or strip_valid_key(os.environ.get("GOOGLE_API_KEY"))
        or strip_valid_key(os.environ.get("EMERGENT_LLM_KEY"))
    )


def chat_constructor_key() -> str:
    """Default `api_key` for `LlmChat`; per-provider env overrides in `llm_client._resolve_key`."""
    return (
        os.environ.get("EMERGENT_LLM_KEY", "")
        or os.environ.get("OPENAI_API_KEY", "")
        or os.environ.get("ANTHROPIC_API_KEY", "")
        or os.environ.get("GEMINI_API_KEY", "")
        or os.environ.get("GOOGLE_API_KEY", "")
        or ""
    )


def openai_api_key_for_rest() -> str:
    """Bearer token for OpenAI HTTP APIs (embeddings, TTS). Prefers direct OpenAI key."""
    if strip_valid_key(os.environ.get("OPENAI_API_KEY")):
        return os.environ.get("OPENAI_API_KEY", "").strip()
    if strip_valid_key(os.environ.get("EMERGENT_LLM_KEY")):
        return os.environ.get("EMERGENT_LLM_KEY", "").strip()
    return ""
