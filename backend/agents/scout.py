import asyncio
import logging
from typing import Optional

import httpx

from config import settings

logger = logging.getLogger(__name__)


def _valid(key: str) -> bool:
    return bool(key) and not key.startswith('pplx-placeholder') and not key.startswith('placeholder')


async def run_scout(
    topic: str,
    research_query: str,
    platform: str,
    user_id: Optional[str] = None,
) -> dict:
    """Scout Agent: Perplexity Sonar Pro for real-time research.

    Optionally enriches research with vault notes from the user's connected
    Obsidian vault (OBS-01). If user_id is provided and Obsidian is configured,
    vault search results are appended to findings as "From your research vault:"
    section. Falls back gracefully (OBS-04) when Obsidian is unavailable.
    """
    perplexity_key = settings.llm.perplexity_key or ''

    # Step 1: Get base research (Perplexity or mock fallback)
    result = None
    if _valid(perplexity_key):
        headers = {"Authorization": f"Bearer {perplexity_key}", "Content-Type": "application/json"}
        payload = {
            "model": "sonar-pro",
            "messages": [
                {
                    "role": "system",
                    "content": "You are a research assistant for content creators. Find recent, credible data. Be concise.",
                },
                {
                    "role": "user",
                    "content": (
                        f"Research for a {platform} content creator:\n\n{research_query}\n\n"
                        "Find: recent stats, trends, and 2-3 specific examples. Return 4-5 bullet points, each starting with •"
                    ),
                },
            ],
            "max_tokens": 600,
        }
        try:
            async with httpx.AsyncClient() as client:
                resp = await asyncio.wait_for(
                    client.post(
                        "https://api.perplexity.ai/chat/completions",
                        headers=headers,
                        json=payload,
                    ),
                    timeout=20.0,
                )
            if resp.status_code == 200:
                data = resp.json()
                content = data["choices"][0]["message"]["content"]
                citations = data.get("citations", [])
                result = {
                    "findings": content,
                    "citations": citations[:3],
                    "sources_found": len(citations),
                }
        except Exception as e:
            logger.warning("Scout Perplexity call failed: %s", e)

    if result is None:
        if not _valid(perplexity_key):
            raise RuntimeError("Scout agent failed: PERPLEXITY_API_KEY is missing or invalid. Cannot generate research.")
        raise RuntimeError("Scout agent failed: Perplexity API returned an error. Please try again.")

    # Step 2: Obsidian vault enrichment (OBS-01) — lazy import, non-fatal
    if user_id:
        try:
            from services.obsidian_service import search_vault  # noqa: PLC0415
            vault_result = await search_vault(topic=topic, user_id=user_id, max_results=5)
            if vault_result.get("sources_found", 0) > 0:
                vault_section = "\n\nFrom your research vault:\n" + vault_result["findings"]
                result = {**result, "findings": result["findings"] + vault_section}
                result["vault_sources"] = vault_result.get("vault_sources", [])
        except Exception as e:
            logger.warning("Obsidian vault search failed (non-fatal): %s", e)

    return result


