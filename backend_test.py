#!/usr/bin/env python3
"""
Backend Test Suite for Celery Async Dispatch Implementation
Tests the content routes with Redis/Celery fallback behavior
"""

import asyncio
import httpx
import json
import uuid
from datetime import datetime

# Backend URL from environment
BACKEND_URL = "https://celery-dispatch-fix.preview.emergentagent.com/api"

class BackendTester:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=60.0)
        self.auth_token = None
        self.user_data = None
        self.job_id = None
        
    async def cleanup(self):
        await self.client.aclose()
    
    def log(self, message, level="INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")
    
    async def test_user_registration(self):
        """Test user registration API"""
        self.log("Testing user registration...")
        
        # Generate unique test data
        test_email = f"test_{uuid.uuid4().hex[:8]}@example.com"
        test_data = {
            "email": test_email,
            "password": "TestPassword123!",
            "name": "Test User"
        }
        
        try:
            response = await self.client.post(f"{BACKEND_URL}/auth/register", json=test_data)
            
            if response.status_code == 200:
                data = response.json()
                self.auth_token = data.get("token")
                self.user_data = data
                self.log(f"✅ User registration successful - User ID: {data.get('user_id')}")
                return True
            else:
                self.log(f"❌ User registration failed - Status: {response.status_code}, Response: {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ User registration error: {str(e)}", "ERROR")
            return False
    
    async def test_onboarding_completion(self):
        """Test onboarding completion to create persona"""
        self.log("Testing onboarding completion...")
        
        if not self.auth_token:
            self.log("❌ No auth token available for onboarding", "ERROR")
            return False
        
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        # Sample onboarding answers
        onboarding_data = {
            "answers": [
                {"id": 0, "answer": "I'm a tech entrepreneur sharing insights on building SaaS products from idea to scale."},
                {"id": 1, "answer": "LinkedIn + X"},
                {"id": 2, "answer": "Strategic, Authentic, Actionable"},
                {"id": 3, "answer": "Paul Graham for clarity and depth in technical writing."},
                {"id": 4, "answer": "Crypto speculation, get-rich-quick schemes, political debates"},
                {"id": 5, "answer": "Build personal brand"},
                {"id": 6, "answer": "3–5 hours"}
            ]
        }
        
        try:
            response = await self.client.post(
                f"{BACKEND_URL}/onboarding/generate-persona", 
                json=onboarding_data,
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                self.log("✅ Onboarding completion successful")
                return True
            else:
                self.log(f"❌ Onboarding failed - Status: {response.status_code}, Response: {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Onboarding error: {str(e)}", "ERROR")
            return False
    
    async def test_content_job_creation(self):
        """Test content job creation"""
        self.log("Testing content job creation...")
        
        if not self.auth_token:
            self.log("❌ No auth token available for content creation", "ERROR")
            return False
        
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        content_data = {
            "platform": "linkedin",
            "content_type": "post",
            "raw_input": "I want to share insights about building resilient software architecture that can scale from startup to enterprise. Focus on practical lessons learned from real-world implementations."
        }
        
        try:
            response = await self.client.post(
                f"{BACKEND_URL}/content/create",
                json=content_data,
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                self.job_id = data.get("job_id")
                self.log(f"✅ Content job created successfully - Job ID: {self.job_id}")
                
                # Wait a moment for job to process
                await asyncio.sleep(3)
                return True
            else:
                self.log(f"❌ Content job creation failed - Status: {response.status_code}, Response: {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Content job creation error: {str(e)}", "ERROR")
            return False
    
    async def test_celery_image_generation(self):
        """Test Celery async image generation with fallback"""
        self.log("Testing Celery async image generation...")
        
        if not self.auth_token or not self.job_id:
            self.log("❌ Missing auth token or job ID for image generation", "ERROR")
            return False
        
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        image_data = {
            "job_id": self.job_id,
            "style": "minimal",
            "provider": "openai"
        }
        
        try:
            response = await self.client.post(
                f"{BACKEND_URL}/content/generate-image",
                json=image_data,
                headers=headers
            )
            
            if response.status_code == 202:
                # Async mode - task queued
                data = response.json()
                self.log(f"✅ Image generation queued (async mode) - Task ID: {data.get('task_id')}")
                return True
            elif response.status_code == 200:
                # Sync mode - immediate response
                data = response.json()
                if data.get("generated"):
                    self.log("✅ Image generation completed (sync fallback mode)")
                    return True
                else:
                    self.log(f"⚠️ Image generation failed in sync mode: {data.get('error', 'Unknown error')}")
                    return False
            else:
                self.log(f"❌ Image generation failed - Status: {response.status_code}, Response: {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Image generation error: {str(e)}", "ERROR")
            return False
    
    async def test_celery_voice_narration(self):
        """Test Celery async voice narration with fallback"""
        self.log("Testing Celery async voice narration...")
        
        if not self.auth_token or not self.job_id:
            self.log("❌ Missing auth token or job ID for voice narration", "ERROR")
            return False
        
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        voice_data = {
            "job_id": self.job_id,
            "provider": "elevenlabs"
        }
        
        try:
            response = await self.client.post(
                f"{BACKEND_URL}/content/narrate",
                json=voice_data,
                headers=headers
            )
            
            if response.status_code == 202:
                # Async mode - task queued
                data = response.json()
                self.log(f"✅ Voice narration queued (async mode) - Task ID: {data.get('task_id')}")
                return True
            elif response.status_code == 200:
                # Sync mode - immediate response
                data = response.json()
                if data.get("generated"):
                    self.log("✅ Voice narration completed (sync fallback mode)")
                    return True
                else:
                    self.log(f"⚠️ Voice narration failed in sync mode: {data.get('error', 'Unknown error')}")
                    return False
            else:
                self.log(f"❌ Voice narration failed - Status: {response.status_code}, Response: {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Voice narration error: {str(e)}", "ERROR")
            return False
    
    async def test_celery_video_generation(self):
        """Test Celery async video generation with fallback"""
        self.log("Testing Celery async video generation...")
        
        if not self.auth_token or not self.job_id:
            self.log("❌ Missing auth token or job ID for video generation", "ERROR")
            return False
        
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        video_data = {
            "job_id": self.job_id,
            "duration": 5,
            "provider": "runway"
        }
        
        try:
            response = await self.client.post(
                f"{BACKEND_URL}/content/generate-video",
                json=video_data,
                headers=headers
            )
            
            if response.status_code == 202:
                # Async mode - task queued
                data = response.json()
                self.log(f"✅ Video generation queued (async mode) - Task ID: {data.get('task_id')}")
                return True
            elif response.status_code == 200:
                # Sync mode - immediate response
                data = response.json()
                if data.get("generated"):
                    self.log("✅ Video generation completed (sync fallback mode)")
                    return True
                else:
                    self.log(f"⚠️ Video generation failed in sync mode: {data.get('error', 'Unknown error')}")
                    return False
            else:
                self.log(f"❌ Video generation failed - Status: {response.status_code}, Response: {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Video generation error: {str(e)}", "ERROR")
            return False
    
    async def test_job_task_status(self):
        """Test job task status endpoint"""
        self.log("Testing job task status endpoint...")
        
        if not self.auth_token or not self.job_id:
            self.log("❌ Missing auth token or job ID for task status check", "ERROR")
            return False
        
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        try:
            response = await self.client.get(
                f"{BACKEND_URL}/content/jobs/{self.job_id}/task-status",
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                mode = data.get("mode", "unknown")
                status = data.get("status", "unknown")
                self.log(f"✅ Task status endpoint working - Mode: {mode}, Status: {status}")
                return True
            else:
                self.log(f"❌ Task status check failed - Status: {response.status_code}, Response: {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Task status check error: {str(e)}", "ERROR")
            return False
    
    async def run_all_tests(self):
        """Run all tests in sequence"""
        self.log("🚀 Starting Celery Async Dispatch Backend Tests")
        self.log(f"Backend URL: {BACKEND_URL}")
        
        results = {}
        
        # Test sequence
        tests = [
            ("User Registration", self.test_user_registration),
            ("Onboarding Completion", self.test_onboarding_completion),
            ("Content Job Creation", self.test_content_job_creation),
            ("Celery Image Generation", self.test_celery_image_generation),
            ("Celery Voice Narration", self.test_celery_voice_narration),
            ("Celery Video Generation", self.test_celery_video_generation),
            ("Job Task Status", self.test_job_task_status)
        ]
        
        for test_name, test_func in tests:
            self.log(f"\n--- Running {test_name} ---")
            try:
                result = await test_func()
                results[test_name] = result
                if not result:
                    self.log(f"❌ {test_name} failed - continuing with remaining tests", "WARNING")
            except Exception as e:
                self.log(f"❌ {test_name} crashed: {str(e)}", "ERROR")
                results[test_name] = False
        
        # Summary
        self.log("\n" + "="*50)
        self.log("TEST SUMMARY")
        self.log("="*50)
        
        passed = sum(1 for r in results.values() if r)
        total = len(results)
        
        for test_name, result in results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            self.log(f"{status} {test_name}")
        
        self.log(f"\nOverall: {passed}/{total} tests passed")
        
        if passed == total:
            self.log("🎉 All tests passed! Celery async dispatch implementation is working correctly.")
        else:
            self.log("⚠️ Some tests failed. Check the logs above for details.")
        
        return results

async def main():
    tester = BackendTester()
    try:
        results = await tester.run_all_tests()
        return results
    finally:
        await tester.cleanup()

if __name__ == "__main__":
    asyncio.run(main())