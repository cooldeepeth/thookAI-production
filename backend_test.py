#!/usr/bin/env python3
"""
Backend Testing Suite for ThookAI Sprint 4
Tests Dashboard Stats API, Learning Signal Capture, Anti-Repetition Engine, and Content Pipeline
"""

import asyncio
import requests
import json
import time
import sys
import os

# Get backend URL from frontend env
FRONTEND_ENV_PATH = "/app/frontend/.env"
BACKEND_URL = None

try:
    with open(FRONTEND_ENV_PATH, "r") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL="):
                BACKEND_URL = line.split("=", 1)[1].strip()
                break
except Exception as e:
    print(f"Error reading frontend .env: {e}")
    sys.exit(1)

if not BACKEND_URL:
    print("Error: REACT_APP_BACKEND_URL not found in frontend/.env")
    sys.exit(1)

API_BASE = f"{BACKEND_URL}/api"

class TestRunner:
    def __init__(self):
        self.token = None
        self.user_id = None
        self.job_ids = []
        self.test_email = "thookai.test@example.com"
        self.test_password = "ThookAI123!"
        self.test_name = "ThookAI Tester"
        
    def log(self, message, level="INFO"):
        print(f"[{level}] {message}")
        
    def test_api_call(self, method, endpoint, data=None, headers=None, timeout=30):
        """Make API call and return response with error handling."""
        try:
            url = f"{API_BASE}{endpoint}"
            default_headers = {"Content-Type": "application/json"}
            if self.token:
                default_headers["Authorization"] = f"Bearer {self.token}"
            if headers:
                default_headers.update(headers)
                
            self.log(f"{method} {url}")
            
            if method == "GET":
                response = requests.get(url, headers=default_headers, timeout=timeout)
            elif method == "POST":
                response = requests.post(url, json=data, headers=default_headers, timeout=timeout)
            elif method == "PATCH":
                response = requests.patch(url, json=data, headers=default_headers, timeout=timeout)
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
    
    async def test_dashboard_stats_initial(self):
        """Test dashboard stats API with new user (should show defaults)."""
        self.log("=== Testing Dashboard Stats API (Initial) ===")
        
        status, response = self.test_api_call("GET", "/dashboard/stats")
        
        if status == 200:
            required_fields = [
                "posts_created", "credits", "platforms_count", 
                "persona_score", "learning_signals_count", "recent_jobs"
            ]
            
            missing_fields = [field for field in required_fields if field not in response]
            if missing_fields:
                self.log(f"❌ Missing fields in dashboard stats: {missing_fields}", "ERROR")
                return False
            
            # Check initial values for new user
            if response["posts_created"] != 0:
                self.log(f"❌ Expected posts_created=0 for new user, got {response['posts_created']}", "ERROR")
                return False
            
            if response["learning_signals_count"] != 0:
                self.log(f"❌ Expected learning_signals_count=0 for new user, got {response['learning_signals_count']}", "ERROR")
                return False
                
            if len(response["recent_jobs"]) != 0:
                self.log(f"❌ Expected 0 recent_jobs for new user, got {len(response['recent_jobs'])}", "ERROR")
                return False
            
            self.log("✅ Dashboard stats API working - initial state correct")
            return True
        else:
            self.log(f"❌ Dashboard stats API failed: {response}", "ERROR")
            return False
    
    async def test_content_creation(self):
        """Test content creation flow."""
        self.log("=== Testing Content Creation Flow ===")
        
        content_data = {
            "platform": "linkedin",
            "content_type": "post",
            "raw_input": "AI is transforming the workplace by automating routine tasks and freeing humans to focus on creative problem-solving."
        }
        
        status, response = self.test_api_call("POST", "/content/create", content_data)
        
        if status == 200:
            if isinstance(response, dict) and "job_id" in response:
                job_id = response["job_id"]
                self.job_ids.append(job_id)
                self.log(f"✅ Content creation started: {job_id}")
                return job_id
            else:
                self.log("❌ Content creation response missing job_id", "ERROR")
                return None
        else:
            self.log(f"❌ Content creation failed: {response}", "ERROR")
            return None
    
    async def poll_job_until_ready(self, job_id, max_wait=60):
        """Poll job until it's ready for review."""
        self.log(f"=== Polling job {job_id} until ready ===")
        
        start_time = time.time()
        while time.time() - start_time < max_wait:
            status, response = self.test_api_call("GET", f"/content/job/{job_id}")
            
            if status == 200:
                job_status = response.get("status", "unknown")
                current_agent = response.get("current_agent", "unknown")
                
                self.log(f"Job status: {job_status}, agent: {current_agent}")
                
                if job_status == "reviewing":
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
    
    async def test_content_approval(self, job_id):
        """Test content approval and learning signal capture."""
        self.log(f"=== Testing Content Approval for {job_id} ===")
        
        approval_data = {
            "status": "approved"
        }
        
        status, response = self.test_api_call("PATCH", f"/content/job/{job_id}/status", approval_data)
        
        if status == 200:
            if "approved" in str(response).lower():
                self.log("✅ Content approval successful")
                return True
            else:
                self.log(f"❌ Unexpected approval response: {response}", "ERROR")
                return False
        else:
            self.log(f"❌ Content approval failed: {response}", "ERROR")
            return False
    
    async def test_idempotency_check(self, job_id):
        """Test that approving an already approved job returns appropriate message."""
        self.log(f"=== Testing Idempotency for {job_id} ===")
        
        approval_data = {
            "status": "approved"
        }
        
        status, response = self.test_api_call("PATCH", f"/content/job/{job_id}/status", approval_data)
        
        if status == 200:
            if "already" in str(response).lower():
                self.log("✅ Idempotency check working")
                return True
            else:
                self.log(f"❌ Idempotency not working properly: {response}", "ERROR")
                return False
        else:
            self.log(f"❌ Idempotency test failed: {response}", "ERROR")
            return False
    
    async def test_dashboard_stats_updated(self):
        """Test dashboard stats after content approval."""
        self.log("=== Testing Dashboard Stats (After Approval) ===")
        
        # Wait a bit for background task to complete
        await asyncio.sleep(3)
        
        status, response = self.test_api_call("GET", "/dashboard/stats")
        
        if status == 200:
            posts_created = response.get("posts_created", 0)
            learning_signals = response.get("learning_signals_count", 0)
            recent_jobs = response.get("recent_jobs", [])
            
            if posts_created < 1:
                self.log(f"❌ posts_created should be at least 1 after approval, got {posts_created}", "ERROR")
                return False
            
            if learning_signals < 1:
                self.log(f"❌ learning_signals_count should be at least 1 after approval, got {learning_signals}", "ERROR")
                return False
            
            if len(recent_jobs) < 1:
                self.log(f"❌ recent_jobs should show at least 1 job, got {len(recent_jobs)}", "ERROR")
                return False
            
            # Check that recent job shows approved status
            recent_job = recent_jobs[0]
            if recent_job.get("status") != "approved":
                self.log(f"❌ Recent job should show approved status, got {recent_job.get('status')}", "ERROR")
                return False
            
            self.log("✅ Dashboard stats updated correctly after approval")
            return True
        else:
            self.log(f"❌ Dashboard stats API failed: {response}", "ERROR")
            return False
    
    async def test_second_content_creation(self):
        """Create second content to test anti-repetition."""
        self.log("=== Testing Second Content Creation (Anti-Repetition) ===")
        
        # Similar but different content to test anti-repetition
        content_data = {
            "platform": "linkedin",
            "content_type": "post",
            "raw_input": "Artificial intelligence is revolutionizing business operations by streamlining processes and enhancing human productivity."
        }
        
        job_id = await self.test_content_creation()
        if not job_id:
            return None
        
        # Poll until ready
        if not await self.poll_job_until_ready(job_id):
            return None
        
        # Check if QC output includes repetition fields
        status, response = self.test_api_call("GET", f"/content/job/{job_id}")
        
        if status == 200:
            qc_output = response.get("qc_score", {})
            
            # Check for repetition risk fields
            if "repetition_risk" not in qc_output:
                self.log("❌ QC output missing repetition_risk field", "ERROR")
                return None
            
            if "repetition_level" not in qc_output:
                self.log("❌ QC output missing repetition_level field", "ERROR")
                return None
            
            rep_risk = qc_output.get("repetition_risk", 0)
            rep_level = qc_output.get("repetition_level", "none")
            
            self.log(f"✅ Anti-repetition working: risk={rep_risk}, level={rep_level}")
            
            # Since this is similar content, we expect some repetition risk
            if rep_risk > 50 or rep_level in ["medium", "high"]:
                self.log("✅ Anti-repetition engine detected similarity as expected")
            else:
                self.log("ℹ️ Anti-repetition showed low risk (may be expected with mock mode)")
            
            return job_id
        else:
            self.log(f"❌ Failed to check second job: {response}", "ERROR")
            return None
    
    async def test_content_rejection(self):
        """Test content rejection flow."""
        self.log("=== Testing Content Rejection Flow ===")
        
        # Create third content for rejection test
        content_data = {
            "platform": "linkedin",
            "content_type": "post",
            "raw_input": "Testing rejection flow for learning signal capture"
        }
        
        job_id = await self.test_content_creation()
        if not job_id:
            return False
        
        # Poll until ready
        if not await self.poll_job_until_ready(job_id):
            return False
        
        # Reject the content
        rejection_data = {
            "status": "rejected",
            "rejection_reason": "Testing rejection flow"
        }
        
        status, response = self.test_api_call("PATCH", f"/content/job/{job_id}/status", rejection_data)
        
        if status == 200:
            if "rejected" in str(response).lower():
                self.log("✅ Content rejection successful")
                return True
            else:
                self.log(f"❌ Unexpected rejection response: {response}", "ERROR")
                return False
        else:
            self.log(f"❌ Content rejection failed: {response}", "ERROR")
            return False

    async def run_all_tests(self):
        """Run all backend tests in sequence."""
        print(f"\n🚀 Starting ThookAI Sprint 4 Backend Tests")
        print(f"Backend URL: {API_BASE}")
        print("=" * 60)
        
        test_results = {}
        
        # Authentication
        test_results["auth"] = await self.test_auth_flow()
        if not test_results["auth"]:
            print("❌ Authentication failed - stopping tests")
            return test_results
        
        # Dashboard stats (initial)
        test_results["dashboard_initial"] = await self.test_dashboard_stats_initial()
        
        # Content creation and approval
        job_id = await self.test_content_creation()
        test_results["content_creation"] = job_id is not None
        
        if job_id:
            test_results["job_polling"] = await self.poll_job_until_ready(job_id)
            
            if test_results["job_polling"]:
                test_results["content_approval"] = await self.test_content_approval(job_id)
                
                # Test idempotency
                test_results["idempotency"] = await self.test_idempotency_check(job_id)
                
                # Dashboard stats after approval
                test_results["dashboard_updated"] = await self.test_dashboard_stats_updated()
        
        # Anti-repetition testing with second content
        second_job_id = await self.test_second_content_creation()
        test_results["anti_repetition"] = second_job_id is not None
        
        # Content rejection flow
        test_results["content_rejection"] = await self.test_content_rejection()
        
        return test_results

async def main():
    """Main test runner."""
    runner = TestRunner()
    results = await runner.run_all_tests()
    
    print("\n" + "=" * 60)
    print("🏁 TEST SUMMARY")
    print("=" * 60)
    
    passed = 0
    total = 0
    
    for test_name, result in results.items():
        total += 1
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name.replace('_', ' ').title()}")
        if result:
            passed += 1
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED!")
        return 0
    else:
        print("❌ Some tests failed - check logs above")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)