# Agent: Vector Store Integration — Wire Pinecone into Pipeline
Sprint: 3 | Branch: feat/vector-store-integration | PR target: dev
Depends on: Sprint 2 fully merged to dev

## Context
backend/services/vector_store.py is a complete Pinecone wrapper with store, search,
and delete functions — but NOTHING in the codebase ever calls it. The learning agent
stores approved content as raw strings in MongoDB. The writer agent never retrieves
past content for style reference. This means persona memory degrades over time as
text search becomes inadequate.

## Files You Will Touch
- backend/agents/learning.py             (MODIFY — add vector storage on approval)
- backend/agents/writer.py              (MODIFY — fetch style examples before writing)
- backend/services/vector_store.py      (MODIFY — add Pinecone initialisation guard)
- backend/server.py                     (MODIFY — add Pinecone startup check)

## Files You Must Read First (do not modify)
- backend/services/vector_store.py      (read the FULL file — all methods)
- backend/agents/learning.py            (read fully — find where approved content is stored)
- backend/agents/writer.py             (read fully — find the prompt construction section)
- backend/config.py                    (settings.llm.pinecone_key)

## Step 1: Add Pinecone startup initialisation to vector_store.py
At module load time, the vector store currently does nothing to check if Pinecone
is configured. Add an initialisation function:

```python
def get_vector_store_client():
    """Returns Pinecone index client if configured, None otherwise."""
    if not settings.llm.pinecone_key:
        logger.warning("PINECONE_API_KEY not set — vector store disabled, using MongoDB fallback")
        return None
    try:
        from pinecone import Pinecone
        pc = Pinecone(api_key=settings.llm.pinecone_key)
        index_name = os.environ.get('PINECONE_INDEX_NAME', 'thookai-personas')
        return pc.Index(index_name)
    except Exception as e:
        logger.error(f"Pinecone initialisation failed: {e}")
        return None
```

All store/search methods must check if the client is None and gracefully degrade
(log warning, return empty results) rather than crash.

## Step 2: Wire storage into learning.py
Find the function that processes content approval (where approved jobs are saved
to db.persona_engines.learning_signals). AFTER writing to MongoDB, add:

```python
from services.vector_store import store_content_embedding

# Store in vector store for semantic retrieval
try:
    await store_content_embedding(
        user_id=user_id,
        content=approved_content,
        metadata={
            "platform": job["platform"],
            "content_type": job.get("content_type", "post"),
            "hook_type": job.get("hook_type", "unknown"),
            "was_edited": job.get("was_edited", False),
            "job_id": str(job["_id"])
        }
    )
except Exception as e:
    logger.warning(f"Vector store embedding failed (non-fatal): {e}")
    # Never let vector store failure break the approval flow
```

## Step 3: Wire retrieval into writer.py
Find the section in writer.py where the writing prompt is constructed (where the
persona card and user input are combined). BEFORE building the prompt, add:

```python
from services.vector_store import find_similar_content

# Fetch semantically similar past approved content for style reference
style_examples = []
try:
    style_examples = await find_similar_content(
        user_id=user_id,
        query=topic_or_raw_input,
        platform=platform,
        top_k=3
    )
except Exception as e:
    logger.warning(f"Vector store retrieval failed (non-fatal): {e}")

# Inject into prompt as style examples
if style_examples:
    style_context = "\n\nREFERENCE EXAMPLES FROM THIS USER'S BEST PAST CONTENT:\n"
    for i, example in enumerate(style_examples, 1):
        style_context += f"\nExample {i}:\n{example['content']}\n"
    # Append style_context to the system prompt
```

## Step 4: Add vector store status to health endpoint
In server.py health check:
```python
health_status["checks"]["vector_store"] = "configured" if settings.llm.pinecone_key else "not_configured"
```

## Definition of Done
- learning.py calls store_content_embedding after every approval
- writer.py calls find_similar_content before every write
- If Pinecone is not configured, both calls gracefully log warning and continue
- PR created to dev with title: "feat: wire Pinecone vector store into learning and writer agents"