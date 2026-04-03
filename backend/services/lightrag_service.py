"""LightRAG Knowledge Graph HTTP Client.

Wraps the LightRAG REST API sidecar (port 9621) for ThookAI.
All calls are non-fatal — content generation proceeds if LightRAG is down.

RETRIEVAL ROUTING CONTRACT:
- Thinker agent: calls query_knowledge_graph() (READ from LightRAG)
- Writer agent: calls Pinecone only (NEVER imports this module)
- Learning agent: calls insert_content() (WRITE to LightRAG)
"""

import logging
from typing import Optional

import httpx

from config import settings

logger = logging.getLogger(__name__)

LIGHTRAG_URL = settings.lightrag.url
LIGHTRAG_API_KEY: Optional[str] = settings.lightrag.api_key


async def health_check() -> bool:
    """Check if LightRAG sidecar is reachable. Used in server.py lifespan."""
    if not settings.lightrag.is_configured():
        return False
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{LIGHTRAG_URL}/health")
        return resp.status_code == 200
    except Exception:
        return False


async def assert_lightrag_embedding_config() -> None:
    """Fail loudly if LightRAG embedding config is wrong.

    Called once at FastAPI startup. Does NOT block startup if LightRAG
    is unreachable (sidecar may not be up yet).
    """
    if not settings.lightrag.is_configured():
        logger.warning("LightRAG not configured - knowledge graph features disabled")
        return

    try:
        settings.lightrag.assert_embedding_config()
        logger.info(
            "LightRAG embedding config validated: %s (%d dims)",
            settings.lightrag.embedding_model,
            settings.lightrag.embedding_dim,
        )
    except AssertionError as e:
        logger.critical("LightRAG embedding config mismatch: %s", e)
        raise  # CRITICAL misconfiguration - fail startup


async def insert_content(user_id: str, content: str, metadata: dict) -> bool:
    """Insert approved content into LightRAG knowledge graph.

    Called from agents/learning.py on content approval.
    Non-fatal: logs warning and returns False on failure.

    Metadata (platform, content_type, was_edited) is forwarded in the
    payload so LightRAG entity extraction can leverage content context.
    """
    if not settings.lightrag.is_configured():
        return False

    doc_id = f"{user_id}_{metadata.get('job_id', '')}"
    # Build metadata header so entity extraction sees structured context
    meta_header = (
        f"[CREATOR:{user_id}]"
        f" [PLATFORM:{metadata.get('platform', 'unknown')}]"
        f" [TYPE:{metadata.get('content_type', 'post')}]"
        f" [EDITED:{metadata.get('was_edited', False)}]"
    )
    tagged_content = f"{meta_header}\n\n{content}"
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{LIGHTRAG_URL}/documents/insert_text",
                json={
                    "text": tagged_content,
                    "doc_id": doc_id,
                    "metadata": {
                        "user_id": user_id,
                        "platform": metadata.get("platform", "unknown"),
                        "content_type": metadata.get("content_type", "post"),
                        "was_edited": metadata.get("was_edited", False),
                        "job_id": metadata.get("job_id", ""),
                    },
                },
                headers={"X-API-Key": LIGHTRAG_API_KEY} if LIGHTRAG_API_KEY else {},
            )
        resp.raise_for_status()
        logger.info("LightRAG insert queued: user=%s doc=%s", user_id, doc_id)
        return True
    except Exception as e:
        logger.warning("LightRAG insert failed for %s (non-fatal): %s", doc_id, e)
        return False


async def query_knowledge_graph(
    user_id: str,
    topic: str,
    mode: str = "hybrid",
) -> str:
    """Query knowledge graph for topic gap analysis.

    Called from agents/thinker.py before angle selection.
    Returns empty string on any failure - Thinker proceeds without graph context.
    Timeout: 15s (aggressive - Thinker prompt building must stay fast).

    ISOLATION: user_id is passed as a query filter via the `param` dict
    so LightRAG scopes retrieval to documents tagged with CREATOR:{user_id}.
    The natural language query also includes user_id as a secondary signal.
    """
    if not settings.lightrag.is_configured():
        return ""

    query = (
        f"For creator {user_id}: What topic domains, hook archetypes, and emotional tones "
        f"have already been used when writing about '{topic}'? "
        f"What angles, framings, and approaches have NOT been explored yet?"
    )
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{LIGHTRAG_URL}/query",
                json={
                    "query": query,
                    "param": {
                        "mode": mode,
                        "top_k": 20,
                        "ids": None,
                        "doc_filter_func": f"lambda meta: meta.get('user_id') == '{user_id}'",
                    },
                },
                headers={"X-API-Key": LIGHTRAG_API_KEY} if LIGHTRAG_API_KEY else {},
            )
        resp.raise_for_status()
        return resp.json().get("response", "")
    except Exception as e:
        logger.warning("LightRAG query failed for user %s (non-fatal): %s", user_id, e)
        return ""
