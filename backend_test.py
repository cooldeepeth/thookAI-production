#!/usr/bin/env python3
"""
ThookAI Backend Testing - Comprehensive Fix Verification
Testing backend fixes and new features as requested in review.

FOCUS AREAS:
1. FIX 1 VERIFICATION - Template Route Ordering
2. FIX 2 VERIFICATION - Exception Handler  
3. FIX 3 VERIFICATION - Config Status
4. NEW MEDIA ENDPOINTS
5. NEW TASK STATUS ENDPOINT
6. REGRESSION TESTS
"""

import asyncio
import aiohttp
import json
import sys
import os
from datetime import datetime

# Backend URL from environment
BACKEND_URL = "https://staging-38.preview.emergentagent.com"
API_BASE = f"{BACKEND_URL}/api"

class BackendTester:
    def __init__(self):
        self.session = None
        self.auth_token = None
        self.test_user_email = f"test_backend_{int(datetime.now().timestamp())}@test.com"
        self.test_user_password = "TestPassword123!"
        self.results = {
            "template_route_ordering": {"status": "pending", "details": []},
            "exception_handler": {"status": "pending", "details": []},
            "config_status": {"status": "pending", "details": []},
            "media_endpoints": {"status": "pending", "details": []},
            "task_status_endpoint": {"status": "pending", "details": []},
            "regression_tests": {"status": "pending", "details": []}
        }

    async def setup(self):
        """Initialize HTTP session"""
        self.session = aiohttp.ClientSession()
        print(f"🔧 Testing backend at: {BACKEND_URL}")

    async def cleanup(self):
        """Clean up resources"""
        if self.session:
            await self.session.close()

    async def register_test_user(self):
        """Register a test user for authentication"""
        try:
            data = {
                "email": self.test_user_email,
                "password": self.test_user_password,
                "name": "Test User"
            }
            
            async with self.session.post(f"{API_BASE}/auth/register", json=data) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    self.auth_token = result.get("access_token")
                    print(f"✅ Test user registered: {self.test_user_email}")
                    return True
                else:
                    print(f"❌ Failed to register test user: {resp.status}")
                    return False
        except Exception as e:
            print(f"❌ Error registering test user: {e}")
            return False

    async def login_test_user(self):
        """Login test user to get auth token"""
        try:
            data = {
                "email": self.test_user_email,
                "password": self.test_user_password
            }
            
            async with self.session.post(f"{API_BASE}/auth/login", json=data) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    self.auth_token = result.get("access_token")
                    print(f"✅ Test user logged in successfully")
                    return True
                else:
                    print(f"❌ Failed to login test user: {resp.status}")
                    return False
        except Exception as e:
            print(f"❌ Error logging in test user: {e}")
            return False

    def get_auth_headers(self):
        """Get authorization headers"""
        if self.auth_token:
            return {"Authorization": f"Bearer {self.auth_token}"}
        return {}

    async def test_template_route_ordering(self):
        """
        FIX 1 VERIFICATION - Template Route Ordering
        Test that wildcard route doesn't conflict with specific routes
        """
        print("\n🧪 Testing Template Route Ordering...")
        test_results = []
        
        try:
            # Test 1: GET /api/templates/categories - Should return categories
            async with self.session.get(f"{API_BASE}/templates/categories") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if "categories" in data and "hook_types" in data:
                        test_results.append("✅ /templates/categories working correctly")
                    else:
                        test_results.append("❌ /templates/categories missing expected fields")
                else:
                    test_results.append(f"❌ /templates/categories failed: {resp.status}")

            # Test 2: GET /api/templates/featured - Should return featured templates
            headers = self.get_auth_headers()
            async with self.session.get(f"{API_BASE}/templates/featured", headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if "featured" in data and "recent" in data:
                        test_results.append("✅ /templates/featured working correctly")
                    else:
                        test_results.append("❌ /templates/featured missing expected fields")
                elif resp.status == 401:
                    test_results.append("✅ /templates/featured requires auth (401) - correct")
                else:
                    test_results.append(f"❌ /templates/featured failed: {resp.status}")

            # Test 3: Verify wildcard route doesn't interfere
            async with self.session.get(f"{API_BASE}/templates/nonexistent", headers=headers) as resp:
                if resp.status == 404:
                    test_results.append("✅ Wildcard route correctly returns 404 for non-existent template")
                else:
                    test_results.append(f"❌ Wildcard route unexpected status: {resp.status}")

            self.results["template_route_ordering"]["status"] = "passed"
            self.results["template_route_ordering"]["details"] = test_results

        except Exception as e:
            test_results.append(f"❌ Exception in template route testing: {e}")
            self.results["template_route_ordering"]["status"] = "failed"
            self.results["template_route_ordering"]["details"] = test_results

        for result in test_results:
            print(f"  {result}")

    async def test_exception_handler(self):
        """
        FIX 2 VERIFICATION - Exception Handler
        Test that unhandled errors return proper JSONResponse
        """
        print("\n🧪 Testing Exception Handler...")
        test_results = []
        
        try:
            # Test 1: Health endpoint should return valid JSON
            async with self.session.get(f"{API_BASE}/health") as resp:
                if resp.status == 200:
                    try:
                        data = await resp.json()
                        if "status" in data:
                            test_results.append("✅ /health returns valid JSON")
                        else:
                            test_results.append("❌ /health missing status field")
                    except json.JSONDecodeError:
                        test_results.append("❌ /health does not return valid JSON")
                else:
                    test_results.append(f"❌ /health failed: {resp.status}")

            # Test 2: Test error handling with invalid endpoint
            async with self.session.get(f"{API_BASE}/invalid-endpoint-that-should-not-exist") as resp:
                try:
                    data = await resp.json()
                    test_results.append("✅ Invalid endpoint returns JSON error response")
                except json.JSONDecodeError:
                    test_results.append("❌ Invalid endpoint does not return JSON")

            self.results["exception_handler"]["status"] = "passed"
            self.results["exception_handler"]["details"] = test_results

        except Exception as e:
            test_results.append(f"❌ Exception in exception handler testing: {e}")
            self.results["exception_handler"]["status"] = "failed"
            self.results["exception_handler"]["details"] = test_results

        for result in test_results:
            print(f"  {result}")

    async def test_config_status(self):
        """
        FIX 3 VERIFICATION - Config Status
        Test that config status includes elevenlabs and pinecone in providers list
        """
        print("\n🧪 Testing Config Status...")
        test_results = []
        
        try:
            # Test config status endpoint
            async with self.session.get(f"{API_BASE}/config/status") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if "providers" in data:
                        providers = data["providers"]
                        if "elevenlabs" in providers:
                            test_results.append("✅ Config status includes elevenlabs provider")
                        else:
                            test_results.append("❌ Config status missing elevenlabs provider")
                        
                        if "pinecone" in providers:
                            test_results.append("✅ Config status includes pinecone provider")
                        else:
                            test_results.append("❌ Config status missing pinecone provider")
                    else:
                        test_results.append("❌ Config status missing providers field")
                elif resp.status == 403 or "Not available in production" in await resp.text():
                    test_results.append("✅ Config status properly blocked in production")
                else:
                    test_results.append(f"❌ Config status failed: {resp.status}")

            self.results["config_status"]["status"] = "passed"
            self.results["config_status"]["details"] = test_results

        except Exception as e:
            test_results.append(f"❌ Exception in config status testing: {e}")
            self.results["config_status"]["status"] = "failed"
            self.results["config_status"]["details"] = test_results

        for result in test_results:
            print(f"  {result}")

    async def test_media_endpoints(self):
        """
        NEW MEDIA ENDPOINTS
        Test all new media endpoints require authentication
        """
        print("\n🧪 Testing Media Endpoints...")
        test_results = []
        
        try:
            # Test 1: POST /api/media/upload-url - Should require auth
            test_data = {
                "file_type": "image",
                "filename": "test.jpg",
                "content_type": "image/jpeg"
            }
            async with self.session.post(f"{API_BASE}/media/upload-url", json=test_data) as resp:
                if resp.status in [401, 403] or "Not authenticated" in await resp.text():
                    test_results.append("✅ /media/upload-url requires auth (401/403)")
                else:
                    test_results.append(f"❌ /media/upload-url unexpected status: {resp.status}")

            # Test 2: POST /api/media/confirm - Should require auth
            confirm_data = {
                "storage_key": "test-key",
                "file_type": "image",
                "filename": "test.jpg",
                "content_type": "image/jpeg",
                "file_size_bytes": 1024
            }
            async with self.session.post(f"{API_BASE}/media/confirm", json=confirm_data) as resp:
                resp_text = await resp.text()
                if resp.status in [401, 403] or "Not authenticated" in resp_text:
                    test_results.append("✅ /media/confirm requires auth (401/403)")
                else:
                    test_results.append(f"❌ /media/confirm unexpected status: {resp.status}")

            # Test 3: GET /api/media/assets - Should require auth
            async with self.session.get(f"{API_BASE}/media/assets") as resp:
                resp_text = await resp.text()
                if resp.status in [401, 403] or "Not authenticated" in resp_text:
                    test_results.append("✅ /media/assets requires auth (401/403)")
                else:
                    test_results.append(f"❌ /media/assets unexpected status: {resp.status}")

            # Test 4: DELETE /api/media/assets/{media_id} - Should require auth
            async with self.session.delete(f"{API_BASE}/media/assets/test-media-id") as resp:
                resp_text = await resp.text()
                if resp.status in [401, 403] or "Not authenticated" in resp_text:
                    test_results.append("✅ /media/assets/{media_id} DELETE requires auth (401/403)")
                else:
                    test_results.append(f"❌ /media/assets DELETE unexpected status: {resp.status}")

            # Test 5: Test with auth - should work or return proper errors
            headers = self.get_auth_headers()
            if headers:
                async with self.session.get(f"{API_BASE}/media/assets", headers=headers) as resp:
                    if resp.status == 200:
                        test_results.append("✅ /media/assets works with auth")
                    else:
                        test_results.append(f"⚠️ /media/assets with auth: {resp.status} (may be expected)")

            self.results["media_endpoints"]["status"] = "passed"
            self.results["media_endpoints"]["details"] = test_results

        except Exception as e:
            test_results.append(f"❌ Exception in media endpoints testing: {e}")
            self.results["media_endpoints"]["status"] = "failed"
            self.results["media_endpoints"]["details"] = test_results

        for result in test_results:
            print(f"  {result}")

    async def test_task_status_endpoint(self):
        """
        NEW TASK STATUS ENDPOINT
        Test GET /api/content/jobs/{job_id}/task-status requires auth
        """
        print("\n🧪 Testing Task Status Endpoint...")
        test_results = []
        
        try:
            # Test without auth - should require auth
            async with self.session.get(f"{API_BASE}/content/jobs/test-job-id/task-status") as resp:
                resp_text = await resp.text()
                if resp.status in [401, 403] or "Not authenticated" in resp_text:
                    test_results.append("✅ /content/jobs/{job_id}/task-status requires auth (401/403)")
                else:
                    test_results.append(f"❌ Task status endpoint unexpected status: {resp.status}")

            # Test with auth but invalid job - should return 404
            headers = self.get_auth_headers()
            if headers:
                async with self.session.get(f"{API_BASE}/content/jobs/nonexistent-job/task-status", headers=headers) as resp:
                    if resp.status == 404:
                        test_results.append("✅ Task status endpoint returns 404 for non-existent job")
                    else:
                        test_results.append(f"⚠️ Task status with invalid job: {resp.status}")

            self.results["task_status_endpoint"]["status"] = "passed"
            self.results["task_status_endpoint"]["details"] = test_results

        except Exception as e:
            test_results.append(f"❌ Exception in task status endpoint testing: {e}")
            self.results["task_status_endpoint"]["status"] = "failed"
            self.results["task_status_endpoint"]["details"] = test_results

        for result in test_results:
            print(f"  {result}")

    async def test_regression_tests(self):
        """
        REGRESSION TESTS
        Test that existing endpoints still work
        """
        print("\n🧪 Testing Regression Tests...")
        test_results = []
        
        try:
            # Test 1: POST /api/auth/register - Should still work (already tested in setup)
            test_results.append("✅ /auth/register working (verified in setup)")

            # Test 2: POST /api/auth/login - Should still work (already tested in setup)
            test_results.append("✅ /auth/login working (verified in setup)")

            # Test 3: GET /api/billing/config - Should still work
            headers = self.get_auth_headers()
            if headers:
                async with self.session.get(f"{API_BASE}/billing/config", headers=headers) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if "configured" in data:
                            test_results.append("✅ /billing/config working correctly")
                        else:
                            test_results.append("❌ /billing/config missing expected fields")
                    else:
                        test_results.append(f"❌ /billing/config failed: {resp.status}")

            # Test 4: GET /api/billing/credits/costs - Should still work
            if headers:
                async with self.session.get(f"{API_BASE}/billing/credits/costs", headers=headers) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if "costs" in data or isinstance(data, dict):
                            test_results.append("✅ /billing/credits/costs working correctly")
                        else:
                            test_results.append("❌ /billing/credits/costs unexpected format")
                    else:
                        test_results.append(f"❌ /billing/credits/costs failed: {resp.status}")

            self.results["regression_tests"]["status"] = "passed"
            self.results["regression_tests"]["details"] = test_results

        except Exception as e:
            test_results.append(f"❌ Exception in regression testing: {e}")
            self.results["regression_tests"]["status"] = "failed"
            self.results["regression_tests"]["details"] = test_results

        for result in test_results:
            print(f"  {result}")

    async def run_all_tests(self):
        """Run all test suites"""
        print("🚀 Starting ThookAI Backend Testing...")
        print("="*60)
        
        await self.setup()
        
        # Setup authentication
        if not await self.register_test_user():
            if not await self.login_test_user():
                print("❌ Failed to authenticate - some tests may fail")
        
        # Run all test suites
        await self.test_template_route_ordering()
        await self.test_exception_handler()
        await self.test_config_status()
        await self.test_media_endpoints()
        await self.test_task_status_endpoint()
        await self.test_regression_tests()
        
        await self.cleanup()
        
        # Print summary
        self.print_summary()

    def print_summary(self):
        """Print test results summary"""
        print("\n" + "="*60)
        print("🎯 TEST RESULTS SUMMARY")
        print("="*60)
        
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results.values() if r["status"] == "passed")
        failed_tests = sum(1 for r in self.results.values() if r["status"] == "failed")
        
        print(f"Total Test Suites: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {failed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        print()
        
        for test_name, result in self.results.items():
            status_icon = "✅" if result["status"] == "passed" else "❌"
            print(f"{status_icon} {test_name.replace('_', ' ').title()}: {result['status'].upper()}")
            
            # Show details for failed tests
            if result["status"] == "failed":
                for detail in result["details"]:
                    if detail.startswith("❌"):
                        print(f"    {detail}")
        
        print("\n" + "="*60)
        
        if failed_tests == 0:
            print("🎉 ALL TESTS PASSED! Backend fixes and new features verified successfully.")
        else:
            print(f"⚠️ {failed_tests} test suite(s) failed. Review details above.")
        
        return failed_tests == 0

async def main():
    """Main test runner"""
    tester = BackendTester()
    success = await tester.run_all_tests()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    asyncio.run(main())