"""
ThookAI Database Connection Module

Features:
- Connection pooling configuration
- Optimized settings for production
- Connection health checking
"""

from motor.motor_asyncio import AsyncIOMotorClient
import logging
from config import settings

logger = logging.getLogger(__name__)

# ==================== CONNECTION CONFIGURATION ====================

# Connection pooling and performance settings
MONGO_OPTIONS = {
    # Connection pooling
    'maxPoolSize': settings.database.max_pool_size,
    'minPoolSize': settings.database.min_pool_size,
    
    # Timeouts (in milliseconds)
    'serverSelectionTimeoutMS': settings.database.server_selection_timeout_ms,
    'connectTimeoutMS': 10000,  # 10 seconds
    'socketTimeoutMS': 30000,   # 30 seconds
    
    # Retry settings
    'retryWrites': True,
    'retryReads': True,
    
    # Compression (optional, can improve performance over network)
    'compressors': ['zstd', 'snappy', 'zlib'],
    
    # Write concern for data durability
    'w': 'majority',
    'journal': True,
    
    # Read preference (can be adjusted based on needs)
    # 'primary' for strong consistency
    # 'secondaryPreferred' for read scaling
    'readPreference': 'primary',
}

# ==================== CLIENT INITIALIZATION ====================

try:
    client = AsyncIOMotorClient(
        settings.database.mongo_url,
        **MONGO_OPTIONS
    )
    db = client[settings.database.db_name]
    logger.info(f"MongoDB client initialized for database: {settings.database.db_name}")
    logger.info(f"Connection pool: min={settings.database.min_pool_size}, max={settings.database.max_pool_size}")
except Exception as e:
    logger.error(f"Failed to initialize MongoDB client: {e}")
    raise


# ==================== UTILITY FUNCTIONS ====================

async def check_connection() -> bool:
    """
    Check if database connection is healthy.
    Returns True if connection is working.
    """
    try:
        await db.command('ping')
        return True
    except Exception as e:
        logger.error(f"Database connection check failed: {e}")
        return False


async def get_connection_stats() -> dict:
    """
    Get database connection statistics.
    Useful for monitoring and debugging.
    """
    try:
        server_info = await client.server_info()
        return {
            'status': 'connected',
            'server_version': server_info.get('version'),
            'database': settings.database.db_name,
            'max_pool_size': settings.database.max_pool_size,
            'min_pool_size': settings.database.min_pool_size,
        }
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e)
        }


async def run_with_timeout(coro, timeout_seconds: float = 10.0):
    """
    Run a database operation with a timeout.
    Useful for preventing long-running queries from blocking.
    
    Usage:
        result = await run_with_timeout(
            db.users.find_one({'email': email}),
            timeout_seconds=5.0
        )
    """
    import asyncio
    try:
        return await asyncio.wait_for(coro, timeout=timeout_seconds)
    except asyncio.TimeoutError:
        logger.warning(f"Database operation timed out after {timeout_seconds}s")
        raise


# ==================== CLEANUP ====================

async def close_connection():
    """Close database connection gracefully"""
    try:
        client.close()
        logger.info("Database connection closed")
    except Exception as e:
        logger.error(f"Error closing database connection: {e}")
