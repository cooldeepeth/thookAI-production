#!/usr/bin/env python3
"""
Sprint 7 Backend Testing Suite for ThookAI
Tests Platform Integrations, Planner, and Publisher functionality

NOTE: This is a live E2E integration script. Run directly against a running server.
Run: python3 backend_test_sprint7.py
It is also collectable by pytest (all test_* methods are marked skip for pytest).

Focus Areas:
1. Platform Status Endpoint
2. Planner - Optimal Times
3. Planner - Weekly Schedule
4. Content Scheduling Flow
5. Upcoming Scheduled Content
6. Cancel Scheduled Content
"""

import asyncio
import requests
import json
import time
import sys
import os
from datetime import datetime, timezone, timedelta

# Get backend URL from frontend env — only at runtime (not import time)
def _get_backend_url():
    FRONTEND_ENV_PATH = "/app/frontend/.env"
    backend_url = None
    try:
        with open(FRONTEND_ENV_PATH, "r") as f:
            for line in f:
                if line.startswith("REACT_APP_BACKEND_URL="):
                    backend_url = line.split("=", 1)[1].strip()
                    break
    except Exception:
        pass
    # Fallback to environment variable
    if not backend_url:
        backend_url = os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8000")
    return backend_url


API_BASE = None  # Resolved at runtime only

class Sprint7TestRunner:
    def __init__(self):
        global API_BASE
        if API_BASE is None:
            API_BASE = f"{_get_backend_url()}/api"
        self.token = None
        self.user_id = None
        self.job_ids = []
        self.scheduled_job_ids = []
        # Use timestamp to ensure unique email
        import time
        timestamp = int(time.time())
        self.test_email = f"sprint7test{timestamp}@example.com"
        self.test_password = "test123"
        self.test_name = "Sprint 7 Tester"
        
    def log(self, message, level="INFO"):
        print(f"[{level}] {message}")
        
    def test_api_call(self, method, endpoint, data=None, headers=None, timeout=30, params=None):
        """Make API call and return response with error handling."""
        try:
            url = f"{API_BASE}{endpoint}"
            default_headers = {"Content-Type": "application/json"}
            if self.token:
                default_headers["Authorization"] = f"Bearer {self.token}"
            if headers:
                default_headers.update(headers)
                
            self.log(f"{method} {url}" + (f" with params: {params}" if params else ""))
            
            if method == "GET":
                response = requests.get(url, headers=default_headers, timeout=timeout, params=params)
            elif method == "POST":
                response = requests.post(url, json=data, headers=default_headers, timeout=timeout, params=params)
            elif method == "PATCH":
                response = requests.patch(url, json=data, headers=default_headers, timeout=timeout, params=params)
            elif method == "DELETE":
                response = requests.delete(url, headers=default_headers, timeout=timeout, params=params)
            else:
                raise ValueError(f"Unsupported method: {method}")
                
            self.log(f"Response: {response.status_code}")
            
            if response.headers.get('content-type', '').startswith('application/json'):
                return response.status_code, response.json()
            else:
                return response.status_code, response.text
                
        except Exception as e:
            self.log(f"API call failed: {e}", "ERROR")
            return None, str(e)
    
    async def test_auth_flow(self):
        """Test user registration and authentication."""
        self.log("=== Testing Authentication Flow ===")
        
        # Register new user
        register_data = {
            "email": self.test_email,
            "password": self.test_password,
            "name": self.test_name
        }
        
        status, response = self.test_api_call("POST", "/auth/register", register_data)
        
        if status == 200:
            if isinstance(response, dict) and "token" in response:
                self.token = response["token"]
                self.user_id = response.get("user_id")
                self.log("✅ User registration successful")
                return True
            else:
                self.log("❌ Registration response missing token", "ERROR")
                return False
        elif status == 400 and "already exists" in str(response):
            # Try logging in instead
            self.log("User already exists, trying login...")
            login_data = {
                "email": self.test_email,
                "password": self.test_password
            }
            status, response = self.test_api_call("POST", "/auth/login", login_data)
            
            if status == 200 and isinstance(response, dict) and "token" in response:
                self.token = response["token"]
                self.user_id = response.get("user_id")
                self.log("✅ User login successful")
                return True
            else:
                self.log("❌ Login failed after registration conflict", "ERROR")
                return False
        else:
            self.log(f"❌ Registration failed: {response}", "ERROR")
            return False

    # ============ SPRINT 7 TESTS ============
    
    async def test_platform_status_endpoint(self):
        """Test GET /api/platforms/status - platform connection status."""
        self.log("=== Testing Platform Status Endpoint ===")
        
        status, response = self.test_api_call("GET", "/platforms/status")
        
        if status != 200:
            self.log(f"❌ Platform status endpoint failed: {response}", "ERROR")
            return False
        
        if not isinstance(response, dict):
            self.log("❌ Response should be a dict", "ERROR")
            return False
        
        # Check required fields
        required_fields = ["platforms", "total_connected"]
        missing_fields = [field for field in required_fields if field not in response]
        if missing_fields:
            self.log(f"❌ Missing fields in response: {missing_fields}", "ERROR")
            return False
        
        platforms = response.get("platforms", {})
        expected_platforms = ["linkedin", "x", "instagram"]
        
        for platform in expected_platforms:
            if platform not in platforms:
                self.log(f"❌ Missing platform: {platform}", "ERROR")
                return False
            
            platform_data = platforms[platform]
            required_platform_fields = ["connected", "configured"]
            missing_platform_fields = [field for field in required_platform_fields if field not in platform_data]
            if missing_platform_fields:
                self.log(f"❌ Missing fields for {platform}: {missing_platform_fields}", "ERROR")
                return False
        
        total_connected = response.get("total_connected", 0)
        if not isinstance(total_connected, int) or total_connected < 0:
            self.log("❌ total_connected should be a non-negative integer", "ERROR")
            return False
        
        self.log("✅ Platform status endpoint working correctly")
        self.log(f"Platforms status: {platforms}")
        self.log(f"Total connected: {total_connected}")
        return True
    
    async def test_planner_optimal_times(self):
        """Test GET /api/dashboard/schedule/optimal-times."""
        self.log("=== Testing Planner Optimal Times ===")
        
        # Test with different platforms
        platforms_to_test = ["linkedin", "x", "instagram"]
        
        for platform in platforms_to_test:
            self.log(f"Testing optimal times for {platform}")
            
            params = {
                "platform": platform,
                "count": 3
            }
            
            status, response = self.test_api_call("GET", "/dashboard/schedule/optimal-times", params=params)
            
            if status != 200:
                self.log(f"❌ Optimal times failed for {platform}: {response}", "ERROR")
                return False
            
            if not isinstance(response, dict):
                self.log(f"❌ Response for {platform} should be a dict", "ERROR")
                return False
            
            # Check required fields
            required_fields = ["best_times", "reasoning", "platform"]
            missing_fields = [field for field in required_fields if field not in response]
            if missing_fields:
                self.log(f"❌ Missing fields in {platform} response: {missing_fields}", "ERROR")
                return False
            
            if response.get("platform") != platform:
                self.log(f"❌ Platform mismatch for {platform}: got {response.get('platform')}", "ERROR")
                return False
            
            best_times = response.get("best_times", [])
            if not isinstance(best_times, list):
                self.log(f"❌ best_times should be a list for {platform}", "ERROR")
                return False
            
            if len(best_times) == 0:
                self.log(f"❌ Should have at least one optimal time for {platform}", "ERROR")
                return False
            
            # Check structure of time slots
            for time_slot in best_times[:2]:  # Check first 2 slots
                required_time_fields = ["datetime", "display_time", "reason"]
                missing_time_fields = [field for field in required_time_fields if field not in time_slot]
                if missing_time_fields:
                    self.log(f"❌ Time slot missing fields for {platform}: {missing_time_fields}", "ERROR")
                    return False
            
            reasoning = response.get("reasoning", "")
            if not isinstance(reasoning, str) or len(reasoning) == 0:
                self.log(f"❌ Reasoning should be a non-empty string for {platform}", "ERROR")
                return False
            
            self.log(f"✅ Optimal times working for {platform} - {len(best_times)} slots returned")
        
        self.log("✅ Planner optimal times working for all platforms")
        return True
    
    async def test_planner_weekly_schedule(self):
        """Test GET /api/dashboard/schedule/weekly."""
        self.log("=== Testing Planner Weekly Schedule ===")
        
        params = {
            "posts_per_week": 5
        }
        
        status, response = self.test_api_call("GET", "/dashboard/schedule/weekly", params=params)
        
        if status != 200:
            self.log(f"❌ Weekly schedule failed: {response}", "ERROR")
            return False
        
        if not isinstance(response, dict):
            self.log("❌ Response should be a dict", "ERROR")
            return False
        
        # Check required fields
        required_fields = ["schedule", "total_posts", "platforms"]
        missing_fields = [field for field in required_fields if field not in response]
        if missing_fields:
            self.log(f"❌ Missing fields in response: {missing_fields}", "ERROR")
            return False
        
        schedule = response.get("schedule", [])
        if not isinstance(schedule, list):
            self.log("❌ Schedule should be a list", "ERROR")
            return False
        
        if len(schedule) == 0:
            self.log("❌ Schedule should have at least one time slot", "ERROR")
            return False
        
        total_posts = response.get("total_posts", 0)
        if total_posts != len(schedule):
            self.log(f"❌ total_posts ({total_posts}) should match schedule length ({len(schedule)})", "ERROR")
            return False
        
        platforms = response.get("platforms", [])
        if not isinstance(platforms, list) or len(platforms) == 0:
            self.log("❌ Platforms should be a non-empty list", "ERROR")
            return False
        
        # Check schedule item structure
        for item in schedule[:2]:  # Check first 2 items
            required_item_fields = ["platform", "suggested_time", "display_time", "reason"]
            missing_item_fields = [field for field in required_item_fields if field not in item]
            if missing_item_fields:
                self.log(f"❌ Schedule item missing fields: {missing_item_fields}", "ERROR")
                return False
        
        self.log("✅ Weekly schedule generation working correctly")
        self.log(f"Generated {total_posts} posts across platforms: {platforms}")
        return True
    
    async def create_content_for_scheduling(self):
        """Create and approve content for scheduling tests."""
        self.log("=== Creating Content for Scheduling Tests ===")
        
        content_data = {
            "platform": "linkedin",
            "content_type": "post",
            "raw_input": "Exploring the future of sustainable technology and innovation in 2025."
        }
        
        status, response = self.test_api_call("POST", "/content/create", content_data)
        
        if status != 200 or "job_id" not in response:
            self.log("❌ Failed to create content for scheduling test", "ERROR")
            return None
        
        job_id = response["job_id"]
        self.job_ids.append(job_id)
        self.log(f"Content creation started: {job_id}")
        
        # Poll until ready
        if not await self.poll_job_until_ready(job_id):
            self.log("❌ Content creation failed to complete", "ERROR")
            return None
        
        # Approve the content
        approval_data = {"status": "approved"}
        status, response = self.test_api_call("PATCH", f"/content/job/{job_id}/status", approval_data)
        
        if status != 200:
            self.log(f"❌ Failed to approve content: {response}", "ERROR")
            return None
        
        self.log(f"✅ Content approved: {job_id}")
        return job_id
    
    async def poll_job_until_ready(self, job_id, max_wait=60):
        """Poll job until it's ready for review."""
        self.log(f"Polling job {job_id} until ready...")
        
        start_time = time.time()
        while time.time() - start_time < max_wait:
            status, response = self.test_api_call("GET", f"/content/job/{job_id}")
            
            if status == 200:
                job_status = response.get("status", "unknown")
                current_agent = response.get("current_agent", "unknown")
                
                if job_status in ("reviewing", "completed"):
                    self.log("✅ Job ready for review")
                    return True
                elif job_status == "error":
                    self.log(f"❌ Job failed with error: {response.get('error', 'Unknown error')}", "ERROR")
                    return False
            else:
                self.log(f"❌ Failed to poll job: {response}", "ERROR")
                return False
            
            await asyncio.sleep(3)
        
        self.log("❌ Job polling timed out", "ERROR")
        return False
    
    async def test_schedule_content_endpoint(self):
        """Test POST /api/dashboard/schedule/content."""
        self.log("=== Testing Schedule Content Endpoint ===")
        
        # First create and approve content
        job_id = await self.create_content_for_scheduling()
        if not job_id:
            return False
        
        # Schedule for 2 hours from now
        future_time = datetime.now(timezone.utc) + timedelta(hours=2)
        
        schedule_data = {
            "job_id": job_id,
            "scheduled_at": future_time.isoformat(),
            "platforms": ["linkedin"]
        }
        
        status, response = self.test_api_call("POST", "/dashboard/schedule/content", schedule_data)
        
        if status != 200:
            self.log(f"❌ Schedule content failed: {response}", "ERROR")
            return False
        
        if not isinstance(response, dict):
            self.log("❌ Schedule response should be a dict", "ERROR")
            return False
        
        # Check required fields
        required_fields = ["scheduled", "job_id", "scheduled_at", "platforms"]
        missing_fields = [field for field in required_fields if field not in response]
        if missing_fields:
            self.log(f"❌ Missing fields in schedule response: {missing_fields}", "ERROR")
            return False
        
        if response.get("scheduled") != True:
            self.log("❌ Scheduled field should be True", "ERROR")
            return False
        
        if response.get("job_id") != job_id:
            self.log(f"❌ Job ID mismatch: expected {job_id}, got {response.get('job_id')}", "ERROR")
            return False
        
        platforms = response.get("platforms", [])
        if platforms != ["linkedin"]:
            self.log(f"❌ Platform mismatch: expected ['linkedin'], got {platforms}", "ERROR")
            return False
        
        self.scheduled_job_ids.append(job_id)
        self.log(f"✅ Content scheduled successfully: {job_id}")
        return True
    
    async def test_upcoming_scheduled_endpoint(self):
        """Test GET /api/dashboard/schedule/upcoming."""
        self.log("=== Testing Upcoming Scheduled Endpoint ===")
        
        status, response = self.test_api_call("GET", "/dashboard/schedule/upcoming")
        
        if status != 200:
            self.log(f"❌ Upcoming scheduled failed: {response}", "ERROR")
            return False
        
        if not isinstance(response, dict):
            self.log("❌ Response should be a dict", "ERROR")
            return False
        
        # Check required fields
        required_fields = ["scheduled", "total"]
        missing_fields = [field for field in required_fields if field not in response]
        if missing_fields:
            self.log(f"❌ Missing fields in response: {missing_fields}", "ERROR")
            return False
        
        scheduled = response.get("scheduled", [])
        if not isinstance(scheduled, list):
            self.log("❌ Scheduled should be a list", "ERROR")
            return False
        
        total = response.get("total", 0)
        if total != len(scheduled):
            self.log(f"❌ Total ({total}) should match scheduled length ({len(scheduled)})", "ERROR")
            return False
        
        # If we have scheduled content, check structure
        if len(scheduled) > 0:
            for item in scheduled[:1]:  # Check first item
                required_item_fields = ["job_id", "platform", "scheduled_at"]
                missing_item_fields = [field for field in required_item_fields if field not in item]
                if missing_item_fields:
                    self.log(f"❌ Scheduled item missing fields: {missing_item_fields}", "ERROR")
                    return False
            
            # Check if our scheduled content appears
            scheduled_job_ids_in_response = [item.get("job_id") for item in scheduled]
            found_our_job = any(job_id in scheduled_job_ids_in_response for job_id in self.scheduled_job_ids)
            
            if not found_our_job and len(self.scheduled_job_ids) > 0:
                self.log("❌ Our scheduled content should appear in upcoming list", "ERROR")
                return False
            
            self.log(f"✅ Upcoming scheduled working - found {total} scheduled items")
        else:
            self.log("✅ Upcoming scheduled working - no scheduled content (expected if none created)")
        
        return True
    
    async def test_cancel_scheduled_endpoint(self):
        """Test DELETE /api/dashboard/schedule/{job_id}."""
        self.log("=== Testing Cancel Scheduled Endpoint ===")
        
        if not self.scheduled_job_ids:
            self.log("❌ No scheduled content available for cancellation test", "ERROR")
            return False
        
        job_id_to_cancel = self.scheduled_job_ids[0]
        
        status, response = self.test_api_call("DELETE", f"/dashboard/schedule/{job_id_to_cancel}")
        
        if status != 200:
            self.log(f"❌ Cancel scheduled failed: {response}", "ERROR")
            return False
        
        if not isinstance(response, dict):
            self.log("❌ Cancel response should be a dict", "ERROR")
            return False
        
        # Check required fields
        required_fields = ["message", "job_id"]
        missing_fields = [field for field in required_fields if field not in response]
        if missing_fields:
            self.log(f"❌ Missing fields in cancel response: {missing_fields}", "ERROR")
            return False
        
        if response.get("job_id") != job_id_to_cancel:
            self.log(f"❌ Job ID mismatch in cancel: expected {job_id_to_cancel}, got {response.get('job_id')}", "ERROR")
            return False
        
        message = response.get("message", "")
        if "cancelled" not in message.lower():
            self.log(f"❌ Cancel message should mention cancellation: {message}", "ERROR")
            return False
        
        # Verify it's removed from upcoming
        await asyncio.sleep(1)  # Brief pause
        status, upcoming_response = self.test_api_call("GET", "/dashboard/schedule/upcoming")
        
        if status == 200:
            scheduled = upcoming_response.get("scheduled", [])
            cancelled_job_found = any(item.get("job_id") == job_id_to_cancel for item in scheduled)
            
            if cancelled_job_found:
                self.log("❌ Cancelled job should not appear in upcoming list", "ERROR")
                return False
        
        self.log(f"✅ Schedule cancellation working correctly: {job_id_to_cancel}")
        return True
    
    async def test_full_scheduling_flow(self):
        """Test the complete scheduling workflow."""
        self.log("=== Testing Full Scheduling Flow ===")
        
        # Step 1: Register and authenticate (already done)
        self.log("✓ User authenticated")
        
        # Step 2: Create content
        self.log("Step 2: Creating content...")
        content_data = {
            "platform": "linkedin", 
            "content_type": "post",
            "raw_input": "Complete workflow test for content scheduling and publishing."
        }
        
        status, response = self.test_api_call("POST", "/content/create", content_data)
        
        if status != 200 or "job_id" not in response:
            self.log("❌ Failed to create content in full flow", "ERROR")
            return False
        
        job_id = response["job_id"]
        self.job_ids.append(job_id)
        self.log(f"✓ Content created: {job_id}")
        
        # Step 3: Poll until reviewing
        self.log("Step 3: Waiting for content generation...")
        if not await self.poll_job_until_ready(job_id):
            self.log("❌ Content generation failed in full flow", "ERROR")
            return False
        
        self.log("✓ Content ready for review")
        
        # Step 4: Approve content
        self.log("Step 4: Approving content...")
        approval_data = {"status": "approved"}
        status, response = self.test_api_call("PATCH", f"/content/job/{job_id}/status", approval_data)
        
        if status != 200:
            self.log(f"❌ Failed to approve content in full flow: {response}", "ERROR")
            return False
        
        self.log("✓ Content approved")
        
        # Step 5: Schedule content
        self.log("Step 5: Scheduling content...")
        future_time = datetime.now(timezone.utc) + timedelta(hours=1)
        
        schedule_data = {
            "job_id": job_id,
            "scheduled_at": future_time.isoformat(),
            "platforms": ["linkedin"]
        }
        
        status, response = self.test_api_call("POST", "/dashboard/schedule/content", schedule_data)
        
        if status != 200:
            self.log(f"❌ Failed to schedule content in full flow: {response}", "ERROR")
            return False
        
        self.log("✓ Content scheduled")
        
        # Step 6: Verify in upcoming
        self.log("Step 6: Verifying in upcoming list...")
        status, response = self.test_api_call("GET", "/dashboard/schedule/upcoming")
        
        if status != 200:
            self.log("❌ Failed to get upcoming in full flow", "ERROR")
            return False
        
        scheduled = response.get("scheduled", [])
        found = any(item.get("job_id") == job_id for item in scheduled)
        
        if not found:
            self.log("❌ Scheduled content not found in upcoming list", "ERROR")
            return False
        
        self.log("✓ Content appears in upcoming scheduled")
        
        # Step 7: Cancel scheduled content
        self.log("Step 7: Cancelling scheduled content...")
        status, response = self.test_api_call("DELETE", f"/dashboard/schedule/{job_id}")
        
        if status != 200:
            self.log(f"❌ Failed to cancel in full flow: {response}", "ERROR")
            return False
        
        self.log("✓ Content cancelled")
        
        # Step 8: Verify removal from upcoming
        self.log("Step 8: Verifying removal from upcoming...")
        await asyncio.sleep(1)
        status, response = self.test_api_call("GET", "/dashboard/schedule/upcoming")
        
        if status == 200:
            scheduled = response.get("scheduled", [])
            still_found = any(item.get("job_id") == job_id for item in scheduled)
            
            if still_found:
                self.log("❌ Cancelled content still appears in upcoming list", "ERROR")
                return False
        
        self.log("✓ Content removed from upcoming list")
        self.log("✅ Full scheduling flow completed successfully!")
        return True

    async def run_all_tests(self):
        """Run all Sprint 7 backend tests in sequence."""
        print(f"\n🚀 Starting ThookAI Sprint 7 Backend Tests")
        print(f"Backend URL: {API_BASE}")
        print("=" * 60)
        
        test_results = {}
        
        # Authentication
        test_results["auth"] = await self.test_auth_flow()
        if not test_results["auth"]:
            print("❌ Authentication failed - stopping tests")
            return test_results
        
        # SPRINT 7 PRIORITY TESTS
        
        # 1. Platform Status Endpoint
        test_results["platform_status"] = await self.test_platform_status_endpoint()
        
        # 2. Planner - Optimal Times
        test_results["planner_optimal_times"] = await self.test_planner_optimal_times()
        
        # 3. Planner - Weekly Schedule
        test_results["planner_weekly_schedule"] = await self.test_planner_weekly_schedule()
        
        # 4. Schedule Content (creates content for testing)
        test_results["schedule_content"] = await self.test_schedule_content_endpoint()
        
        # 5. Upcoming Scheduled
        test_results["upcoming_scheduled"] = await self.test_upcoming_scheduled_endpoint()
        
        # 6. Cancel Scheduled
        test_results["cancel_scheduled"] = await self.test_cancel_scheduled_endpoint()
        
        # 7. Full Scheduling Flow (comprehensive test)
        test_results["full_scheduling_flow"] = await self.test_full_scheduling_flow()
        
        return test_results

async def main():
    """Main test runner."""
    runner = Sprint7TestRunner()
    results = await runner.run_all_tests()
    
    print("\n" + "=" * 60)
    print("🏁 SPRINT 7 TEST SUMMARY")
    print("=" * 60)
    
    passed = 0
    total = 0
    
    priority_tests = [
        "auth", "platform_status", "planner_optimal_times", 
        "planner_weekly_schedule", "schedule_content", 
        "upcoming_scheduled", "cancel_scheduled"
    ]
    
    comprehensive_tests = ["full_scheduling_flow"]
    
    print("PRIORITY TESTS:")
    for test_name in priority_tests:
        if test_name in results:
            total += 1
            result = results[test_name]
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"  {status} {test_name.replace('_', ' ').title()}")
            if result:
                passed += 1
    
    print("\nCOMPREHENSIVE TESTS:")
    for test_name in comprehensive_tests:
        if test_name in results:
            total += 1
            result = results[test_name]
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"  {status} {test_name.replace('_', ' ').title()}")
            if result:
                passed += 1
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL SPRINT 7 TESTS PASSED!")
        return 0
    else:
        print("❌ Some tests failed - check logs above")
        return 1

import pytest


@pytest.mark.skip(reason="Live E2E integration script — run directly against a server, not via pytest")
def test_sprint7_e2e_placeholder():
    """Placeholder so pytest can collect this file without errors."""
    pass


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)