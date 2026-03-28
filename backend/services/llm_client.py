"""Local LLM chat shim replacing emergentintegrations.llm.chat.

Uses OpenAI, Anthropic, and Google Generative AI SDKs directly. Resolves API keys
per provider from environment when set (OPENAI_API_KEY, ANTHROPIC_API_KEY,
GEMINI_API_KEY / GOOGLE_API_KEY), otherwise falls back to the api_key passed to
LlmChat (e.g. EMERGENT_LLM_KEY) for backward compatibility.
"""
from __future__ import annotations

import asyncio
import base64
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, List, Optional

from config import settings

class MessageRole(str, Enum):
    """Role of a message in a conversation (OpenAI-compatible string values)."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


@dataclass(frozen=True)
class ConversationMessage:
    """Single message in a chat history."""

    role: MessageRole
    content: str


@dataclass
class UserMessage:
    """User input to LlmChat.send_message."""

    text: str
    images: Optional[List[str]] = None


def _parse_data_url(data_url: str) -> tuple[str, bytes]:
    """Return (mime_type, raw_bytes) for a data: URL; otherwise treat as raw base64."""
    if not data_url.startswith("data:"):
        try:
            return "image/jpeg", base64.b64decode(data_url, validate=False)
        except Exception:
            return "image/jpeg", data_url.encode()
    try:
        header, _, b64 = data_url.partition(",")
        mime = "image/jpeg"
        if ";" in header:
            mime = header[5:].split(";")[0].strip() or "image/jpeg"
        raw = base64.b64decode(b64, validate=False)
        return mime, raw
    except Exception:
        return "image/jpeg", b""


def _openai_user_content(text: str, images: Optional[List[str]]) -> Any:
    if not images:
        return text
    parts: List[dict[str, Any]] = [{"type": "text", "text": text}]
    for img in images:
        if img.startswith("http://") or img.startswith("https://"):
            parts.append({"type": "image_url", "image_url": {"url": img}})
        else:
            url = img if img.startswith("data:") else f"data:image/jpeg;base64,{img}"
            parts.append({"type": "image_url", "image_url": {"url": url}})
    return parts


def _anthropic_user_blocks(text: str, images: Optional[List[str]]) -> List[dict[str, Any]]:
    blocks: List[dict[str, Any]] = [{"type": "text", "text": text}]
    if not images:
        return blocks
    for img in images:
        if img.startswith("http://") or img.startswith("https://"):
            blocks.append({"type": "image", "source": {"type": "url", "url": img}})
        else:
            mime, raw = _parse_data_url(img if img.startswith("data:") else f"data:image/jpeg;base64,{img}")
            b64 = base64.b64encode(raw).decode("ascii")
            blocks.append(
                {
                    "type": "image",
                    "source": {"type": "base64", "media_type": mime, "data": b64},
                }
            )
    return blocks


async def _gemini_parts_async(text: str, images: Optional[List[str]]) -> List[Any]:
    import httpx

    parts: List[Any] = [text]
    if not images:
        return parts
    for img in images:
        if img.startswith("http://") or img.startswith("https://"):

            def _download() -> bytes:
                with httpx.Client(timeout=60.0) as client:
                    r = client.get(img)
                    r.raise_for_status()
                    return r.content

            data = await asyncio.to_thread(_download)
            parts.append({"mime_type": "image/jpeg", "data": data})
        else:
            mime, raw = _parse_data_url(img if img.startswith("data:") else f"data:image/jpeg;base64,{img}")
            parts.append({"mime_type": mime, "data": raw})
    return parts


def _resolve_key(provider: str, constructor_key: str) -> str:
    p = provider.lower()
    if p == "openai":
        return settings.llm.openai_key or constructor_key
    if p == "anthropic":
        return settings.llm.anthropic_key or constructor_key
    if p in ("google", "gemini"):
        return (
            settings.llm.gemini_key
            or constructor_key
        )
    return constructor_key


def _openai_reasoning_style_model(model: str) -> bool:
    return bool(re.match(r"^o[0-9]", model))


def _google_response_text(response: Any) -> str:
    t = getattr(response, "text", None)
    if t:
        return t
    chunks: List[str] = []
    for cand in getattr(response, "candidates", None) or []:
        content = getattr(cand, "content", None)
        if not content:
            continue
        for part in getattr(content, "parts", None) or []:
            pt = getattr(part, "text", None)
            if pt:
                chunks.append(pt)
    return "".join(chunks)


class LlmChat:
    """Multi-provider async chat client (OpenAI, Anthropic, Google)."""

    def __init__(self, api_key: str, session_id: str, system_message: str) -> None:
        self._api_key = api_key or ""
        self.session_id = session_id
        self.system_message = system_message
        self._provider: Optional[str] = None
        self._model: Optional[str] = None

    def with_model(self, provider: str, model: str) -> LlmChat:
        self._provider = provider.lower().strip()
        self._model = model
        return self

    async def send_message(self, message: UserMessage) -> str:
        if not self._provider or not self._model:
            raise RuntimeError("LlmChat.with_model(provider, model) must be called before send_message")
        key = _resolve_key(self._provider, self._api_key)
        if not key:
            raise ValueError(f"No API key available for provider {self._provider!r}")

        if self._provider == "openai":
            return await self._send_openai(key, message)
        if self._provider == "anthropic":
            return await self._send_anthropic(key, message)
        if self._provider in ("google", "gemini"):
            return await self._send_google(key, message)

        raise ValueError(f"Unsupported LLM provider: {self._provider!r}")

    async def _send_openai(self, api_key: str, message: UserMessage) -> str:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=api_key)
        user_content = _openai_user_content(message.text, message.images)
        msgs: List[dict[str, Any]] = [
            {"role": "system", "content": self.system_message},
            {"role": "user", "content": user_content},
        ]
        model = self._model or "gpt-4o"
        kwargs: dict[str, Any] = {"model": model, "messages": msgs}
        if _openai_reasoning_style_model(model):
            kwargs["max_completion_tokens"] = 8192
        else:
            kwargs["max_tokens"] = 8192
            kwargs["temperature"] = 0.7
        resp = await client.chat.completions.create(**kwargs)
        content = resp.choices[0].message.content
        return (content or "").strip()

    async def _send_anthropic(self, api_key: str, message: UserMessage) -> str:
        from anthropic import AsyncAnthropic

        client = AsyncAnthropic(api_key=api_key)
        blocks = _anthropic_user_blocks(message.text, message.images)
        resp = await client.messages.create(
            model=self._model or "claude-sonnet-4-20250514",
            max_tokens=8192,
            system=self.system_message,
            messages=[{"role": "user", "content": blocks}],
        )
        pieces: List[str] = []
        for block in resp.content:
            if block.type == "text":
                pieces.append(block.text)
        return "".join(pieces).strip()

    async def _send_google(self, api_key: str, message: UserMessage) -> str:
        import google.generativeai as genai

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(
            model_name=self._model or "gemini-1.5-flash",
            system_instruction=self.system_message,
        )
        parts = await _gemini_parts_async(message.text, message.images)

        def _run() -> Any:
            return model.generate_content(parts)

        response = await asyncio.to_thread(_run)
        return _google_response_text(response).strip()
