"""
Database Index Management for ThookAI

This module defines all MongoDB indexes for optimal query performance.
Run this script to create/update indexes:
    python db_indexes.py
"""

import asyncio
import logging
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import IndexModel, ASCENDING, DESCENDING, TEXT
from config import settings

logger = logging.getLogger(__name__)

# ============================================================
# INDEX DEFINITIONS
# ============================================================

INDEXES = {
    # ========== USERS ==========
    'users': [
        IndexModel([('user_id', ASCENDING)], unique=True, name='idx_user_id'),
        IndexModel([('email', ASCENDING)], unique=True, name='idx_email'),
        IndexModel([('google_id', ASCENDING)], sparse=True, name='idx_google_id'),
        IndexModel([('subscription_tier', ASCENDING)], name='idx_subscription_tier'),
        IndexModel([('created_at', DESCENDING)], name='idx_created_at'),
    ],
    
    # ========== USER SESSIONS ==========
    'user_sessions': [
        IndexModel([('session_token', ASCENDING)], unique=True, name='idx_session_token'),
        IndexModel([('user_id', ASCENDING)], name='idx_user_id'),
        IndexModel([('expires_at', ASCENDING)], expireAfterSeconds=0, name='idx_expires_ttl'),
    ],
    
    # ========== PERSONA ENGINES ==========
    'persona_engines': [
        IndexModel([('user_id', ASCENDING)], unique=True, name='idx_user_id'),
        IndexModel([('card.archetype', ASCENDING)], name='idx_archetype'),
        IndexModel([('created_at', DESCENDING)], name='idx_created_at'),
    ],
    
    # ========== PERSONA SHARES ==========
    'persona_shares': [
        IndexModel([('share_token', ASCENDING)], unique=True, name='idx_share_token'),
        IndexModel([('user_id', ASCENDING)], name='idx_user_id'),
        IndexModel([('is_active', ASCENDING), ('expires_at', ASCENDING)], name='idx_active_expires'),
        IndexModel([('created_at', DESCENDING)], name='idx_created_at'),
    ],
    
    # ========== CONTENT JOBS ==========
    'content_jobs': [
        IndexModel([('job_id', ASCENDING)], unique=True, name='idx_job_id'),
        IndexModel([('user_id', ASCENDING)], name='idx_user_id'),
        IndexModel([('user_id', ASCENDING), ('status', ASCENDING)], name='idx_user_status'),
        IndexModel([('user_id', ASCENDING), ('created_at', DESCENDING)], name='idx_user_created'),
        IndexModel([('user_id', ASCENDING), ('platform', ASCENDING)], name='idx_user_platform'),
        IndexModel([('status', ASCENDING)], name='idx_status'),
        IndexModel([('platform', ASCENDING)], name='idx_platform'),
        IndexModel([('created_at', DESCENDING)], name='idx_created_at'),
        IndexModel([('scheduled_at', ASCENDING)], sparse=True, name='idx_scheduled_at'),
        IndexModel([('series_id', ASCENDING)], sparse=True, name='idx_series_id'),
        IndexModel([('is_repurposed', ASCENDING)], sparse=True, name='idx_is_repurposed'),
    ],
    
    # ========== CONTENT SERIES ==========
    'content_series': [
        IndexModel([('series_id', ASCENDING)], unique=True, name='idx_series_id'),
        IndexModel([('user_id', ASCENDING)], name='idx_user_id'),
        IndexModel([('user_id', ASCENDING), ('status', ASCENDING)], name='idx_user_status'),
        IndexModel([('created_at', DESCENDING)], name='idx_created_at'),
    ],
    
    # ========== SCHEDULED POSTS ==========
    'scheduled_posts': [
        IndexModel([('schedule_id', ASCENDING)], unique=True, name='idx_schedule_id'),
        IndexModel([('user_id', ASCENDING)], name='idx_user_id'),
        IndexModel([('job_id', ASCENDING)], name='idx_job_id'),
        IndexModel([('scheduled_at', ASCENDING)], name='idx_scheduled_at'),
        IndexModel([('status', ASCENDING), ('scheduled_at', ASCENDING)], name='idx_status_scheduled'),
    ],
    
    # ========== PLATFORM TOKENS ==========
    'platform_tokens': [
        IndexModel([('user_id', ASCENDING), ('platform', ASCENDING)], unique=True, name='idx_user_platform'),
        IndexModel([('user_id', ASCENDING)], name='idx_user_id'),
        IndexModel([('expires_at', ASCENDING)], name='idx_expires_at'),
    ],
    
    # ========== OAUTH STATES ==========
    'oauth_states': [
        IndexModel([('state', ASCENDING)], unique=True, name='idx_state'),
        IndexModel([('created_at', ASCENDING)], expireAfterSeconds=600, name='idx_created_ttl'),  # 10 min TTL
    ],
    
    # ========== TEMPLATES ==========
    'templates': [
        IndexModel([('template_id', ASCENDING)], unique=True, name='idx_template_id'),
        IndexModel([('platform', ASCENDING)], name='idx_platform'),
        IndexModel([('category', ASCENDING)], name='idx_category'),
        IndexModel([('hook_type', ASCENDING)], name='idx_hook_type'),
        IndexModel([('is_active', ASCENDING), ('upvotes', DESCENDING)], name='idx_active_popular'),
        IndexModel([('is_active', ASCENDING), ('created_at', DESCENDING)], name='idx_active_recent'),
        IndexModel([('is_active', ASCENDING), ('uses_count', DESCENDING)], name='idx_active_used'),
        IndexModel([('author_id', ASCENDING)], name='idx_author_id'),
        # Text search on title and description
        IndexModel([('title', TEXT), ('description', TEXT)], name='idx_text_search'),
    ],
    
    # ========== TEMPLATE UPVOTES ==========
    'template_upvotes': [
        IndexModel([('template_id', ASCENDING), ('user_id', ASCENDING)], unique=True, name='idx_template_user'),
        IndexModel([('user_id', ASCENDING)], name='idx_user_id'),
    ],
    
    # ========== TEMPLATE USAGE ==========
    'template_usage': [
        IndexModel([('template_id', ASCENDING)], name='idx_template_id'),
        IndexModel([('user_id', ASCENDING)], name='idx_user_id'),
        IndexModel([('used_at', DESCENDING)], name='idx_used_at'),
    ],
    
    # ========== WORKSPACES ==========
    'workspaces': [
        IndexModel([('workspace_id', ASCENDING)], unique=True, name='idx_workspace_id'),
        IndexModel([('owner_id', ASCENDING)], name='idx_owner_id'),
        IndexModel([('created_at', DESCENDING)], name='idx_created_at'),
    ],
    
    # ========== WORKSPACE MEMBERS ==========
    'workspace_members': [
        IndexModel([('invite_id', ASCENDING)], unique=True, name='idx_invite_id'),
        IndexModel([('workspace_id', ASCENDING)], name='idx_workspace_id'),
        IndexModel([('user_id', ASCENDING)], sparse=True, name='idx_user_id'),
        IndexModel([('email', ASCENDING)], name='idx_email'),
        IndexModel([('workspace_id', ASCENDING), ('status', ASCENDING)], name='idx_workspace_status'),
        IndexModel([('user_id', ASCENDING), ('status', ASCENDING)], name='idx_user_status'),
    ],
    
    # ========== CREDIT TRANSACTIONS ==========
    'credit_transactions': [
        IndexModel([('transaction_id', ASCENDING)], unique=True, name='idx_transaction_id'),
        IndexModel([('user_id', ASCENDING)], name='idx_user_id'),
        IndexModel([('user_id', ASCENDING), ('created_at', DESCENDING)], name='idx_user_created'),
        IndexModel([('user_id', ASCENDING), ('operation', ASCENDING)], name='idx_user_operation'),
        IndexModel([('created_at', DESCENDING)], name='idx_created_at'),
    ],
    
    # ========== SUBSCRIPTION HISTORY ==========
    'subscription_history': [
        IndexModel([('user_id', ASCENDING)], name='idx_user_id'),
        IndexModel([('user_id', ASCENDING), ('created_at', DESCENDING)], name='idx_user_created'),
    ],
    
    # ========== DAILY BRIEFS ==========
    'daily_briefs': [
        IndexModel([('user_id', ASCENDING), ('date', ASCENDING)], unique=True, name='idx_user_date'),
        IndexModel([('created_at', ASCENDING)], expireAfterSeconds=172800, name='idx_created_ttl'),  # 48hr TTL
    ],
    
    # ========== DAILY BRIEF DISMISSALS ==========
    'daily_brief_dismissals': [
        IndexModel([('user_id', ASCENDING), ('date', ASCENDING)], unique=True, name='idx_user_date'),
        IndexModel([('created_at', ASCENDING)], expireAfterSeconds=172800, name='idx_created_ttl'),  # 48hr TTL
    ],
    
    # ========== LEARNING SIGNALS (embedded in persona_engines, but separate collection too) ==========
    'learning_signals': [
        IndexModel([('user_id', ASCENDING)], name='idx_user_id'),
        IndexModel([('user_id', ASCENDING), ('created_at', DESCENDING)], name='idx_user_created'),
        IndexModel([('created_at', DESCENDING)], name='idx_created_at'),
    ],
    
    # ========== ONBOARDING SESSIONS ==========
    'onboarding_sessions': [
        IndexModel([('session_id', ASCENDING)], unique=True, name='idx_session_id'),
        IndexModel([('user_id', ASCENDING)], name='idx_user_id'),
        IndexModel([('created_at', ASCENDING)], expireAfterSeconds=86400, name='idx_created_ttl'),  # 24hr TTL
    ],

    # ========== PASSWORD RESETS ==========
    'password_resets': [
        IndexModel([('token_hash', ASCENDING)], unique=True, name='idx_token_hash'),
        IndexModel([('user_id', ASCENDING)], name='idx_user_id'),
        IndexModel([('expires_at', ASCENDING)], name='idx_expires_at'),
    ],

    # ========== CONTEXT UPLOADS (content creation) ==========
    'uploads': [
        IndexModel([('upload_id', ASCENDING)], unique=True, name='idx_upload_id'),
        IndexModel([('user_id', ASCENDING)], name='idx_user_id'),
        IndexModel([('user_id', ASCENDING), ('created_at', DESCENDING)], name='idx_user_created'),
    ],

    # ========== VIRAL CARDS (public persona cards — 30-day TTL) ==========
    'viral_cards': [
        IndexModel([('card_id', ASCENDING)], unique=True, name='idx_card_id'),
        IndexModel([('created_at', ASCENDING)], expireAfterSeconds=2592000, name='idx_ttl_30d'),
    ],

    # ========== MEDIA PIPELINE LEDGER ==========
    # Tracks per-stage credits for every orchestrated media job.
    # Every provider call is preceded by a pending entry here — no silent credit drain.
    'media_pipeline_ledger': [
        IndexModel([('job_id', ASCENDING)], name='idx_job_id'),
        IndexModel([('user_id', ASCENDING), ('created_at', DESCENDING)], name='idx_user_created'),
        IndexModel([('status', ASCENDING), ('created_at', ASCENDING)], name='idx_status_created'),
    ],
}


# ============================================================
# INDEX MANAGEMENT FUNCTIONS
# ============================================================

async def create_indexes(db):
    """
    Create all indexes for all collections.
    Safe to run multiple times - will skip existing indexes.
    """
    created = 0
    skipped = 0
    errors = []
    
    for collection_name, indexes in INDEXES.items():
        collection = db[collection_name]
        
        try:
            # Get existing index names
            existing_indexes = set()
            async for idx in collection.list_indexes():
                existing_indexes.add(idx['name'])
            
            for index_model in indexes:
                index_name = index_model.document.get('name', 'unnamed')
                
                if index_name in existing_indexes:
                    logger.debug(f"Index {collection_name}.{index_name} already exists, skipping")
                    skipped += 1
                    continue
                
                try:
                    await collection.create_indexes([index_model])
                    logger.info(f"Created index: {collection_name}.{index_name}")
                    created += 1
                except Exception as e:
                    error_msg = f"Failed to create {collection_name}.{index_name}: {str(e)}"
                    logger.error(error_msg)
                    errors.append(error_msg)
        
        except Exception as e:
            error_msg = f"Error processing collection {collection_name}: {str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)
    
    return {
        'created': created,
        'skipped': skipped,
        'errors': errors,
        'total_defined': sum(len(indexes) for indexes in INDEXES.values())
    }


async def drop_all_indexes(db, confirm: bool = False):
    """
    Drop all custom indexes (keeps _id index).
    USE WITH CAUTION - mainly for development/testing.
    """
    if not confirm:
        raise ValueError("Must pass confirm=True to drop indexes")
    
    dropped = 0
    for collection_name in INDEXES.keys():
        collection = db[collection_name]
        try:
            await collection.drop_indexes()
            logger.info(f"Dropped indexes for {collection_name}")
            dropped += 1
        except Exception as e:
            logger.error(f"Failed to drop indexes for {collection_name}: {e}")
    
    return dropped


async def get_index_stats(db):
    """
    Get statistics about indexes for all collections.
    """
    stats = {}
    
    for collection_name in INDEXES.keys():
        collection = db[collection_name]
        try:
            indexes = []
            async for idx in collection.list_indexes():
                indexes.append({
                    'name': idx['name'],
                    'key': dict(idx['key']),
                    'unique': idx.get('unique', False),
                    'sparse': idx.get('sparse', False),
                })
            
            # Get collection stats
            try:
                coll_stats = await db.command('collStats', collection_name)
                stats[collection_name] = {
                    'indexes': indexes,
                    'index_count': len(indexes),
                    'total_index_size': coll_stats.get('totalIndexSize', 0),
                    'document_count': coll_stats.get('count', 0),
                }
            except Exception:
                stats[collection_name] = {
                    'indexes': indexes,
                    'index_count': len(indexes),
                }
        except Exception as e:
            stats[collection_name] = {'error': str(e)}
    
    return stats


# ============================================================
# CLI RUNNER
# ============================================================

async def main():
    """Main entry point for index management"""
    import argparse
    
    parser = argparse.ArgumentParser(description='ThookAI Database Index Management')
    parser.add_argument('action', choices=['create', 'stats', 'drop'],
                       help='Action to perform')
    parser.add_argument('--confirm-drop', action='store_true',
                       help='Confirm dropping all indexes')
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Connect to database
    client = AsyncIOMotorClient(settings.database.mongo_url)
    db = client[settings.database.db_name]
    
    try:
        if args.action == 'create':
            logger.info("Creating indexes...")
            result = await create_indexes(db)
            logger.info("\nIndex Creation Summary:")
            logger.info(f"  Total defined: {result['total_defined']}")
            logger.info(f"  Created: {result['created']}")
            logger.info(f"  Skipped (existing): {result['skipped']}")
            logger.info(f"  Errors: {len(result['errors'])}")
            if result['errors']:
                for error in result['errors']:
                    logger.error(f"  - {error}")
        
        elif args.action == 'stats':
            logger.info("Getting index statistics...")
            stats = await get_index_stats(db)
            for collection, data in stats.items():
                logger.info(f"\n{collection}:")
                if 'error' in data:
                    logger.error(f"  Error: {data['error']}")
                else:
                    logger.info(f"  Documents: {data.get('document_count', 'N/A')}")
                    logger.info(f"  Index count: {data['index_count']}")
                    for idx in data['indexes']:
                        unique = " (unique)" if idx['unique'] else ""
                        sparse = " (sparse)" if idx['sparse'] else ""
                        logger.info(f"    - {idx['name']}: {idx['key']}{unique}{sparse}")
        
        elif args.action == 'drop':
            if not args.confirm_drop:
                logger.error("Must use --confirm-drop flag to drop indexes")
                return
            logger.warning("Dropping all custom indexes...")
            dropped = await drop_all_indexes(db, confirm=True)
            logger.info(f"Dropped indexes for {dropped} collections")
    
    finally:
        client.close()


if __name__ == '__main__':
    asyncio.run(main())
