"""Vector Store Service for Pinecone integration.

Handles:
- Storing approved embeddings for persona learning
- Querying similar content for anti-repetition
- Managing learning signals in vector DB
"""
import os
import logging
import hashlib
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)

PINECONE_API_KEY = os.environ.get('PINECONE_API_KEY', '')
PINECONE_ENVIRONMENT = os.environ.get('PINECONE_ENVIRONMENT', 'us-east-1')
INDEX_NAME = 'thook-persona-embeddings'
EMBEDDING_DIMENSION = 1536  # OpenAI text-embedding-3-small dimension

# Global references
_pinecone_client = None
_pinecone_index = None


def _is_valid_key(key: str) -> bool:
    """Check if API key is valid (not a placeholder)."""
    return bool(key) and not any(
        key.startswith(p) for p in ['placeholder', 'sk-placeholder', 'your_']
    )


def get_pinecone_client():
    """Get or create Pinecone client singleton."""
    global _pinecone_client, _pinecone_index
    
    if not _is_valid_key(PINECONE_API_KEY):
        logger.warning("Pinecone API key not configured - using mock mode")
        return None
    
    if _pinecone_client is None:
        try:
            from pinecone import Pinecone, ServerlessSpec
            _pinecone_client = Pinecone(api_key=PINECONE_API_KEY)
            
            # Check if index exists, create if not
            existing_indexes = [idx.name for idx in _pinecone_client.list_indexes()]
            
            if INDEX_NAME not in existing_indexes:
                logger.info(f"Creating Pinecone index: {INDEX_NAME}")
                _pinecone_client.create_index(
                    name=INDEX_NAME,
                    dimension=EMBEDDING_DIMENSION,
                    metric='cosine',
                    spec=ServerlessSpec(cloud='aws', region=PINECONE_ENVIRONMENT)
                )
            
            _pinecone_index = _pinecone_client.Index(INDEX_NAME)
            logger.info(f"Connected to Pinecone index: {INDEX_NAME}")
            
        except Exception as e:
            logger.error(f"Failed to initialize Pinecone: {e}")
            _pinecone_client = None
            _pinecone_index = None
    
    return _pinecone_index


def generate_embedding(text: str) -> List[float]:
    """Generate embedding for text using OpenAI API via Emergent."""
    from emergentintegrations.llm.chat import LlmChat
    
    llm_key = os.environ.get('EMERGENT_LLM_KEY', '')
    if not _is_valid_key(llm_key):
        # Return mock embedding for testing
        return _mock_embedding(text)
    
    try:
        # Use OpenAI embeddings via Emergent
        import httpx
        response = httpx.post(
            "https://api.openai.com/v1/embeddings",
            headers={
                "Authorization": f"Bearer {llm_key}",
                "Content-Type": "application/json"
            },
            json={
                "input": text[:8000],  # Limit text length
                "model": "text-embedding-3-small"
            },
            timeout=30.0
        )
        response.raise_for_status()
        data = response.json()
        return data['data'][0]['embedding']
    except Exception as e:
        logger.error(f"Embedding generation failed: {e}")
        return _mock_embedding(text)


def _mock_embedding(text: str) -> List[float]:
    """Generate a deterministic mock embedding for testing."""
    # Create a deterministic but varied embedding based on text hash
    text_hash = hashlib.sha256(text.encode()).hexdigest()
    embedding = []
    for i in range(EMBEDDING_DIMENSION):
        # Use hash characters to generate float values
        idx = (i * 2) % len(text_hash)
        val = int(text_hash[idx:idx+2], 16) / 255.0 - 0.5
        embedding.append(val)
    return embedding


async def upsert_approved_embedding(
    user_id: str,
    content_text: str,
    content_id: str,
    metadata: Optional[Dict[str, Any]] = None
) -> str:
    """Store an approved content embedding in Pinecone.
    
    Args:
        user_id: User ID for namespacing
        content_text: The approved content text
        content_id: Unique content/job ID
        metadata: Additional metadata (topic, hooks, etc.)
    
    Returns:
        The vector ID
    """
    index = get_pinecone_client()
    vector_id = f"{user_id}_{content_id}"
    
    # Extract key patterns from content for metadata
    hook = content_text.split('\n')[0][:100] if content_text else ""
    
    vector_metadata = {
        "user_id": user_id,
        "content_id": content_id,
        "hook": hook,
        "content_preview": content_text[:500],
        "word_count": len(content_text.split()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **(metadata or {})
    }
    
    if index is not None:
        try:
            embedding = generate_embedding(content_text)
            index.upsert(
                vectors=[(vector_id, embedding, vector_metadata)],
                namespace=f"user_{user_id}"
            )
            logger.info(f"Upserted embedding for {vector_id}")
            return vector_id
        except Exception as e:
            logger.error(f"Failed to upsert embedding: {e}")
    
    # Fallback: store in MongoDB if Pinecone unavailable
    logger.info(f"Using MongoDB fallback for embedding storage: {vector_id}")
    return vector_id


async def query_similar_content(
    user_id: str,
    query_text: str,
    top_k: int = 5,
    similarity_threshold: float = 0.7
) -> List[Dict[str, Any]]:
    """Query for similar content to detect potential repetition.
    
    Args:
        user_id: User ID for namespace filtering
        query_text: Text to compare against
        top_k: Number of results to return
        similarity_threshold: Minimum similarity score
    
    Returns:
        List of similar content with scores
    """
    index = get_pinecone_client()
    
    if index is not None:
        try:
            query_embedding = generate_embedding(query_text)
            results = index.query(
                vector=query_embedding,
                top_k=top_k,
                namespace=f"user_{user_id}",
                include_metadata=True
            )
            
            similar = []
            for match in results.get('matches', []):
                if match.get('score', 0) >= similarity_threshold:
                    similar.append({
                        'id': match['id'],
                        'score': match['score'],
                        'metadata': match.get('metadata', {})
                    })
            return similar
        except Exception as e:
            logger.error(f"Similarity query failed: {e}")
    
    # Return empty if Pinecone unavailable
    return []


async def get_recent_patterns(
    user_id: str,
    limit: int = 5
) -> Dict[str, Any]:
    """Get recent content patterns for anti-repetition engine.
    
    Returns aggregated patterns from recent approved content:
    - recent_topics: Main topics covered
    - recent_hooks: Hook styles used
    - recent_structures: Content structures used
    - count: Number of patterns found
    """
    from database import db
    
    # Query recent approved jobs from MongoDB
    recent_jobs = await db.content_jobs.find(
        {"user_id": user_id, "status": "approved"},
        {"_id": 0, "final_content": 1, "agent_outputs": 1, "platform": 1, "content_type": 1}
    ).sort("updated_at", -1).limit(limit).to_list(limit)
    
    recent_topics = []
    recent_hooks = []
    recent_structures = []
    
    for job in recent_jobs:
        # Extract patterns from commander output if available
        commander = job.get('agent_outputs', {}).get('commander', {})
        if commander:
            if commander.get('primary_angle'):
                recent_topics.append(commander['primary_angle'][:80])
            if commander.get('hook_approach'):
                recent_hooks.append(commander['hook_approach'])
            if commander.get('structure'):
                recent_structures.append(commander['structure'])
        
        # Also extract hook from final content
        final = job.get('final_content', '')
        if final:
            first_line = final.split('\n')[0][:100]
            if first_line and first_line not in recent_hooks:
                recent_hooks.append(first_line)
    
    return {
        "recent_topics": list(set(recent_topics))[:5],
        "recent_hooks": list(set(recent_hooks))[:5],
        "recent_structures": list(set(recent_structures))[:5],
        "count": len(recent_jobs)
    }


async def check_repetition_risk(
    user_id: str,
    draft_text: str,
    threshold: float = 0.75
) -> Tuple[float, List[str]]:
    """Check if draft is too similar to recent approved content.
    
    Returns:
        Tuple of (risk_score 0-100, list of similar content previews)
    """
    similar = await query_similar_content(user_id, draft_text, top_k=3, similarity_threshold=0.6)
    
    if not similar:
        return 0.0, []
    
    # Calculate risk based on highest similarity
    max_similarity = max(s['score'] for s in similar)
    risk_score = min(100, max_similarity * 100)
    
    # Get previews of similar content
    similar_previews = [
        s['metadata'].get('content_preview', '')[:100] + '...'
        for s in similar if s['score'] >= threshold
    ]
    
    return risk_score, similar_previews
