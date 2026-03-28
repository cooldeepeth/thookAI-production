"""Persona Learning Agent for ThookAI.

Captures learning signals from user interactions:
- Edit deltas (what users change in AI content)
- Approval patterns (what users accept)
- Rejection patterns (what users reject)
- UOM (User Operating Model) updates
"""
import json
import asyncio
import uuid
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List
from database import db

from services.llm_keys import anthropic_available, chat_constructor_key

logger = logging.getLogger(__name__)


def _clean_json(raw: str) -> str:
    s = raw.strip()
    if "```" in s:
        parts = s.split("```")
        s = parts[1] if len(parts) > 1 else s
        if s.startswith("json"):
            s = s[4:]
    return s.strip()


LEARNING_SYSTEM = """You are a learning analyst for ThookAI. Analyze content edits to extract style preferences.
Return ONLY valid JSON - no markdown, no explanations."""

LEARNING_PROMPT = """Analyze the difference between AI-generated content and user's edited version.

ORIGINAL AI DRAFT:
{original_content}

USER'S EDITED VERSION:
{edited_content}

Extract what we can learn about the user's preferences. Return JSON:
{{
  "changes_made": ["List of specific changes the user made"],
  "style_learnings": ["What we learned about their preferred style"],
  "patterns_to_adopt": ["Patterns we should use more often"],
  "patterns_to_avoid": ["Patterns we should stop using"],
  "tone_shift": "more_formal|more_casual|more_technical|more_emotional|no_change",
  "structure_preference": "What structure changes they prefer"
}}"""


async def analyze_edit_delta(
    original_content: str,
    edited_content: str
) -> Dict[str, Any]:
    """Use AI to analyze what a user changed and why.
    
    Args:
        original_content: The AI-generated draft
        edited_content: The user's edited version
    
    Returns:
        Analysis of changes with learnings
    """
    # Skip if edit is minimal (< 10 chars difference)
    if abs(len(original_content) - len(edited_content)) < 10:
        return {
            "changes_made": ["Minimal edits"],
            "style_learnings": [],
            "patterns_to_adopt": [],
            "patterns_to_avoid": [],
            "tone_shift": "no_change",
            "structure_preference": "No significant structure changes"
        }
    
    if not anthropic_available():
        return _mock_analysis(original_content, edited_content)
    
    try:
        from services.llm_client import LlmChat, UserMessage
        
        chat = LlmChat(
            api_key=chat_constructor_key(),
            session_id=f"learn-{uuid.uuid4().hex[:8]}",
            system_message=LEARNING_SYSTEM
        ).with_model("anthropic", "claude-sonnet-4-20250514")
        
        prompt = LEARNING_PROMPT.format(
            original_content=original_content[:2000],
            edited_content=edited_content[:2000]
        )
        
        response = await asyncio.wait_for(
            chat.send_message(UserMessage(text=prompt)),
            timeout=15.0
        )
        return json.loads(_clean_json(response))
    
    except Exception as e:
        logger.error(f"Edit analysis failed: {e}")
        return _mock_analysis(original_content, edited_content)


def _mock_analysis(original: str, edited: str) -> Dict[str, Any]:
    """Fallback analysis when AI is unavailable."""
    orig_words = set(original.lower().split())
    edit_words = set(edited.lower().split())
    
    added_words = edit_words - orig_words
    # Note: removed_words could be used for future analysis
    
    changes = []
    if len(edited) < len(original) * 0.9:
        changes.append("Made content more concise")
    elif len(edited) > len(original) * 1.1:
        changes.append("Added more detail/context")
    
    if any(w in added_words for w in ['i', 'my', 'we', 'our']):
        changes.append("Added more personal language")
    
    return {
        "changes_made": changes or ["Various edits to improve flow"],
        "style_learnings": ["User prefers a more personalized tone"],
        "patterns_to_adopt": [],
        "patterns_to_avoid": [],
        "tone_shift": "no_change",
        "structure_preference": "Standard structure maintained"
    }


async def capture_learning_signal(
    user_id: str,
    job_id: str,
    original_content: str,
    final_content: str,
    action: str = "approved"  # approved | rejected | edited
) -> bool:
    """Capture and store learning signal from user interaction.
    
    Called when user approves, edits, or rejects content.
    Updates persona_engines.learning_signals.
    
    Args:
        user_id: User ID
        job_id: Content job ID
        original_content: AI-generated draft
        final_content: User's final version (may be edited)
        action: Type of action taken
    
    Returns:
        True if signal was captured successfully
    """
    try:
        now = datetime.now(timezone.utc)
        
        # Analyze the edit if content was modified
        edit_analysis = None
        if action in ["approved", "edited"] and original_content != final_content:
            edit_analysis = await analyze_edit_delta(original_content, final_content)
        
        # Build the learning signal
        signal = {
            "job_id": job_id,
            "action": action,
            "timestamp": now,
            "content_preview": final_content[:200] if final_content else "",
            "edit_analysis": edit_analysis
        }
        
        # Update persona_engines document
        update_ops = {
            "$push": {
                "learning_signals.edit_deltas": {
                    "$each": [signal],
                    "$slice": -50  # Keep last 50 signals
                }
            },
            "$set": {
                "learning_signals.last_updated": now
            }
        }
        
        # If approved, also store embedding reference
        if action == "approved":
            # Fetch job metadata for richer vector store context
            job_doc = await db.content_jobs.find_one(
                {"job_id": job_id},
                {"_id": 0, "platform": 1, "content_type": 1, "was_edited": 1}
            )
            job_meta = job_doc or {}

            # Store approved embedding in vector store (non-fatal on failure)
            try:
                from services.vector_store import upsert_approved_embedding
                await upsert_approved_embedding(
                    user_id=user_id,
                    content_text=final_content,
                    content_id=job_id,
                    metadata={
                        "action": "approved",
                        "platform": job_meta.get("platform", "unknown"),
                        "content_type": job_meta.get("content_type", "post"),
                        "was_edited": job_meta.get("was_edited", False),
                        "job_id": job_id,
                        "patterns_to_adopt": edit_analysis.get("patterns_to_adopt", []) if edit_analysis else []
                    }
                )
            except Exception as e:
                logger.warning(f"Vector store embedding failed (non-fatal): {e}")

            # Increment approved count
            update_ops["$inc"] = {"learning_signals.approved_count": 1}
        
        elif action == "rejected":
            # Store rejection patterns
            update_ops["$push"]["learning_signals.rejected_patterns"] = {
                "$each": [{
                    "job_id": job_id,
                    "content_preview": original_content[:200],
                    "timestamp": now
                }],
                "$slice": -20  # Keep last 20 rejections
            }
            update_ops["$inc"] = {"learning_signals.rejected_count": 1}
        
        # Update the persona engine document
        result = await db.persona_engines.update_one(
            {"user_id": user_id},
            update_ops
        )
        
        if result.modified_count == 0:
            # If no persona exists yet, create minimal structure
            await db.persona_engines.update_one(
                {"user_id": user_id},
                {
                    "$setOnInsert": {
                        "user_id": user_id,
                        "created_at": now,
                        "learning_signals": {
                            "edit_deltas": [signal],
                            "approved_count": 1 if action == "approved" else 0,
                            "rejected_count": 1 if action == "rejected" else 0,
                            "rejected_patterns": [],
                            "last_updated": now
                        }
                    }
                },
                upsert=True
            )
        
        # Update UOM after interaction
        await update_uom_after_interaction(user_id, action)
        
        logger.info(f"Captured learning signal for user {user_id}, job {job_id}, action: {action}")
        return True
    
    except Exception as e:
        logger.error(f"Failed to capture learning signal: {e}")
        return False


async def update_uom_after_interaction(user_id: str, action: str, data: dict = None):
    """
    Update UOM after a user interaction (approve, reject, edit).
    Delegates to the comprehensive UOM inference service.
    """
    try:
        from services.uom_service import get_uom, update_uom, maybe_trigger_periodic_update

        current_uom = await get_uom(user_id)

        # Immediate trust adjustment (kept for responsiveness)
        trust = current_uom.get("trust_in_thook", 0.5)
        if action == "approved":
            trust = min(1.0, trust + 0.03)  # Smaller increments for smoother curve
        elif action == "rejected":
            trust = max(0.0, trust - 0.04)  # Slightly larger penalty
        elif action == "edited":
            # Edits are mixed signals — slight trust increase (they're engaging)
            trust = min(1.0, trust + 0.01)

        await update_uom(user_id, {"trust_in_thook": round(trust, 3)})

        # Check if we should run full inference (every 5 interactions)
        await maybe_trigger_periodic_update(user_id)

    except Exception as e:
        logger.warning(f"UOM update failed for {user_id}: {e}")
        # Fall through — UOM update failure should never block the learning flow


async def get_learning_insights(user_id: str) -> Dict[str, Any]:
    """Get aggregated learning insights for a user.
    
    Returns summary of:
    - Total approvals/rejections
    - Common patterns to adopt/avoid
    - Style preferences learned
    - UOM summary
    """
    persona = await db.persona_engines.find_one({"user_id": user_id})
    
    if not persona:
        return {
            "has_data": False,
            "message": "No learning data yet. Approve or edit some content to start learning."
        }
    
    learning = persona.get("learning_signals", {})
    uom = persona.get("uom", {})
    
    # Aggregate patterns from edit deltas
    patterns_to_adopt = []
    patterns_to_avoid = []
    style_learnings = []
    
    for delta in learning.get("edit_deltas", [])[-10:]:  # Last 10
        analysis = delta.get("edit_analysis", {})
        if analysis:
            patterns_to_adopt.extend(analysis.get("patterns_to_adopt", []))
            patterns_to_avoid.extend(analysis.get("patterns_to_avoid", []))
            style_learnings.extend(analysis.get("style_learnings", []))
    
    return {
        "has_data": True,
        "approved_count": learning.get("approved_count", 0),
        "rejected_count": learning.get("rejected_count", 0),
        "patterns_to_adopt": list(set(patterns_to_adopt))[:5],
        "patterns_to_avoid": list(set(patterns_to_avoid))[:5],
        "style_learnings": list(set(style_learnings))[:5],
        "uom": {
            "trust_score": uom.get("trust_in_thook", 0.5),
            "strategy_maturity": uom.get("strategy_maturity", 1),
            "burnout_risk": uom.get("burnout_risk", "low")
        },
        "last_updated": learning.get("last_updated")
    }


async def process_bulk_import(
    user_id: str,
    posts: List[Dict[str, Any]],
    source: str = "manual_paste"
) -> Dict[str, Any]:
    """Process a bulk import of historical posts for persona training.

    Deduplicates against existing learning signals, stores each post as an
    approved embedding in persona_engines.learning_signals, and attempts to
    index in the Pinecone vector store (non-fatal on failure).

    Args:
        user_id: User ID
        posts: List of dicts with keys: content, platform, date
        source: Import source type (manual_paste, linkedin_export, twitter_archive)

    Returns:
        Dict with imported count, skipped count, and persona_updated flag
    """
    now = datetime.now(timezone.utc)
    imported = 0
    skipped = 0

    # Fetch existing approved_embeddings to deduplicate
    persona = await db.persona_engines.find_one(
        {"user_id": user_id},
        {"_id": 0, "learning_signals.approved_embeddings": 1}
    )
    existing_previews = set()
    if persona:
        for emb in persona.get("learning_signals", {}).get("approved_embeddings", []):
            preview = emb.get("content_preview", "")
            if preview:
                existing_previews.add(preview)

    new_embeddings = []
    for post in posts:
        content = post["content"]
        platform = post.get("platform", "general")
        post_date = post.get("date")

        # Deduplicate: check if a post with the same first 200 chars already exists
        content_preview = content[:200]
        if content_preview in existing_previews:
            skipped += 1
            continue

        content_id = f"import_{uuid.uuid4().hex[:12]}"

        embedding_record = {
            "content_id": content_id,
            "content_preview": content_preview,
            "platform": platform,
            "source": source,
            "post_date": post_date,
            "imported_at": now,
        }
        new_embeddings.append(embedding_record)
        existing_previews.add(content_preview)

        # Store in vector store (non-fatal)
        try:
            from services.vector_store import upsert_approved_embedding
            await upsert_approved_embedding(
                user_id=user_id,
                content_text=content,
                content_id=content_id,
                metadata={
                    "action": "imported",
                    "platform": platform,
                    "source": source,
                    "post_date": post_date or "",
                }
            )
        except Exception as e:
            logger.warning(f"Vector store embedding failed for import (non-fatal): {e}")

        imported += 1

    # Batch update persona_engines with all new embeddings
    if new_embeddings:
        await db.persona_engines.update_one(
            {"user_id": user_id},
            {
                "$push": {
                    "learning_signals.approved_embeddings": {
                        "$each": new_embeddings,
                        "$slice": -500  # Keep last 500 embeddings
                    }
                },
                "$set": {
                    "learning_signals.last_updated": now,
                    "learning_signals.last_import": {
                        "source": source,
                        "count": imported,
                        "timestamp": now,
                    }
                },
                "$inc": {
                    "learning_signals.approved_count": imported
                }
            }
        )

    persona_updated = imported > 0

    logger.info(
        f"Bulk import for user {user_id}: imported={imported}, skipped={skipped}, source={source}"
    )

    return {
        "imported": imported,
        "skipped": skipped,
        "persona_updated": persona_updated,
    }
