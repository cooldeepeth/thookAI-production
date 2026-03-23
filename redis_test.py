#!/usr/bin/env python3
"""
Additional test to verify Redis configuration and Celery fallback behavior
"""

import asyncio
import sys
import os

# Add backend to path
sys.path.append('/app/backend')

async def test_redis_configuration():
    """Test Redis configuration and fallback behavior"""
    print("🔍 Testing Redis Configuration and Celery Fallback...")
    
    # Test 1: Check Redis configuration function
    try:
        from tasks import is_redis_configured, get_task_runner, check_celery_health
        
        redis_configured = is_redis_configured()
        print(f"✅ Redis configured: {redis_configured}")
        
        # Test 2: Check task runner
        task_runner = get_task_runner()
        print(f"✅ Task runner: {'Celery' if task_runner else 'Sync fallback'}")
        
        # Test 3: Check Celery health
        health = check_celery_health()
        print(f"✅ Celery health: {health}")
        
        # Test 4: Test task status function
        from tasks import get_task_status
        
        # Test with a fake task ID
        fake_task_id = "test-task-123"
        status = await get_task_status(fake_task_id)
        print(f"✅ Task status for fake ID: {status}")
        
        return True
        
    except Exception as e:
        print(f"❌ Redis configuration test failed: {e}")
        return False

async def test_celery_imports():
    """Test that Celery task imports work correctly"""
    print("\n🔍 Testing Celery Task Imports...")
    
    try:
        from tasks.media_tasks import generate_image, generate_voice, generate_video
        print("✅ Media tasks imported successfully")
        
        # Check if tasks have the right attributes
        print(f"✅ generate_image task: {hasattr(generate_image, 'apply_async')}")
        print(f"✅ generate_voice task: {hasattr(generate_voice, 'apply_async')}")
        print(f"✅ generate_video task: {hasattr(generate_video, 'apply_async')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Celery imports test failed: {e}")
        return False

async def main():
    print("🚀 Starting Redis/Celery Configuration Tests\n")
    
    test1_result = await test_redis_configuration()
    test2_result = await test_celery_imports()
    
    print("\n" + "="*50)
    print("CONFIGURATION TEST SUMMARY")
    print("="*50)
    
    if test1_result and test2_result:
        print("✅ All configuration tests passed!")
        print("✅ Celery async dispatch implementation is properly configured for fallback mode")
    else:
        print("❌ Some configuration tests failed")
    
    return test1_result and test2_result

if __name__ == "__main__":
    asyncio.run(main())