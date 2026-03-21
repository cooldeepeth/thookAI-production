#!/usr/bin/env python3
"""
Targeted E2E Backend Testing for specific failing areas
"""

import asyncio
import aiohttp
import json
import time
from datetime import datetime

# Configuration  
BASE_URL = "https://staging-38.preview.emergentagent.com/api"
TEST_USER_EMAIL = f"targeted_test_{int(time.time())}@test.com"
TEST_USER_PASSWORD = "SecurePass123!"
TEST_USER_NAME = "Targeted Test User"

class TargetedTestRunner:
    def __init__(self):
        self.session = None
        self.auth_token = None
        self.test_results = []
        self.user_id = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    def log_result(self, test_name: str, passed: bool, details: str = ""):
        status = "✅ PASS" if passed else "❌ FAIL"
        result = f"{status}: {test_name}"
        if details:
            result += f" - {details}"
        print(result)
        self.test_results.append({
            "test": test_name,
            "passed": passed,
            "details": details
        })
    
    async def make_request(self, method: str, endpoint: str, data: dict = None, 
                          headers: dict = None, require_auth: bool = True) -> tuple[int, dict]:
        """Make HTTP request and return (status_code, response_data)"""
        url = f"{BASE_URL}{endpoint}"
        
        request_headers = {"Content-Type": "application/json"}
        if headers:
            request_headers.update(headers)
        
        if require_auth and self.auth_token:
            request_headers["Authorization"] = f"Bearer {self.auth_token}"
        
        try:
            async with self.session.request(
                method, url, json=data, headers=request_headers, timeout=30
            ) as response:
                try:
                    response_data = await response.json()
                except Exception:
                    response_data = {"error": "Invalid JSON response", "text": await response.text()}
                return response.status, response_data
        except Exception as e:
            return 500, {"error": f"Request failed: {str(e)}"}
    
    async def setup_user_with_persona(self):
        """Create user and set up persona for content testing"""
        print("🔧 SETUP: Creating user with persona")
        
        # Register user
        status, response = await self.make_request(
            "POST", "/auth/register",
            data={
                "email": TEST_USER_EMAIL,
                "password": TEST_USER_PASSWORD,
                "name": TEST_USER_NAME
            },
            require_auth=False
        )
        
        if status == 200 and "token" in response:
            self.auth_token = response["token"]
            self.user_id = response["user_id"]
            print(f"✅ User created: {self.user_id}")
        else:
            print(f"❌ User creation failed: {status}, {response}")
            return False
        
        # Generate persona using onboarding
        mock_answers = [
            {"question_id": 0, "answer": "I create content about AI and technology for developers and entrepreneurs"},
            {"question_id": 1, "answer": "LinkedIn"},
            {"question_id": 2, "answer": "Bold Strategic Human"},
            {"question_id": 3, "answer": "Lenny Rachitsky - depth + accessibility"},
            {"question_id": 4, "answer": "Crypto speculation, hustle culture"},
            {"question_id": 5, "answer": "Build personal brand"}
        ]
        
        status, response = await self.make_request(
            "POST", "/onboarding/generate-persona",
            data={
                "answers": mock_answers,
                "posts_analysis": "Analytical voice with professional tone"
            }
        )
        
        if status == 200:
            print(f"✅ Persona generated successfully")
            return True
        else:
            print(f"❌ Persona generation failed: {status}, {response}")
            return False
    
    async def test_billing_endpoints(self):
        """Test billing endpoints that were failing"""
        print("\n💳 TESTING: Billing Endpoints")
        
        # Test credits
        status, response = await self.make_request("GET", "/billing/credits")
        credits_working = status == 200 and "credits" in response
        self.log_result("Get Credits", credits_working, 
                       f"Status: {status}, Credits: {response.get('credits', 'N/A')}")
        
        # Test subscription
        status, response = await self.make_request("GET", "/billing/subscription")
        subscription_working = status == 200 and "tier" in response
        self.log_result("Get Subscription", subscription_working, 
                       f"Status: {status}, Tier: {response.get('tier', 'N/A')}")
        
        # Test tier upgrade
        if subscription_working and response.get("tier") == "free":
            status, response = await self.make_request(
                "POST", "/billing/subscription/upgrade",
                data={"tier": "pro", "billing_period": "monthly"}
            )
            upgrade_working = status == 200
            self.log_result("Tier Upgrade", upgrade_working, 
                           f"Status: {status}, Response: {response}")
    
    async def test_content_creation(self):
        """Test content creation workflow"""
        print("\n📝 TESTING: Content Creation")
        
        # Test content creation with proper persona
        status, response = await self.make_request(
            "POST", "/content/create",
            data={
                "platform": "linkedin",
                "content_type": "post",
                "raw_input": "The future of AI in content creation is here"
            }
        )
        
        content_created = status in [200, 201] and "job_id" in response
        job_id = response.get("job_id") if content_created else None
        self.log_result("Create Content", content_created, 
                       f"Status: {status}, Job ID: {job_id}")
        
        # Test job status
        if job_id:
            status, response = await self.make_request("GET", f"/content/job/{job_id}")
            job_status_working = status == 200
            self.log_result("Get Job Status", job_status_working, 
                           f"Status: {status}, Job status: {response.get('status', 'N/A')}")
        
        # Test list content
        status, response = await self.make_request("GET", "/content/jobs")
        list_working = status == 200
        job_count = len(response.get("jobs", [])) if isinstance(response, dict) else 0
        self.log_result("List Content Jobs", list_working, 
                       f"Status: {status}, Jobs count: {job_count}")
    
    async def test_auth_validation(self):
        """Test authentication validation"""
        print("\n🔐 TESTING: Authentication Validation")
        
        # Test protected endpoint without auth
        status, response = await self.make_request("GET", "/persona/me", require_auth=False)
        auth_required = status in [401, 403]
        self.log_result("Protected Endpoint Without Auth", auth_required, 
                       f"Status: {status}, Properly blocked: {auth_required}")
        
        # Test with invalid token
        status, response = await self.make_request(
            "GET", "/persona/me", 
            headers={"Authorization": "Bearer invalid-token-xyz"},
            require_auth=False
        )
        invalid_token_blocked = status in [401, 403]
        self.log_result("Invalid Token Blocked", invalid_token_blocked, 
                       f"Status: {status}, Invalid token properly blocked: {invalid_token_blocked}")
    
    async def test_agency_workspace(self):
        """Test agency workspace functionality"""
        print("\n🏢 TESTING: Agency Workspace")
        
        # First upgrade to pro tier if not already
        await self.make_request(
            "POST", "/billing/subscription/upgrade",
            data={"tier": "pro", "billing_period": "monthly"}
        )
        
        # Test workspace creation (should still fail with Pro, need Studio+)
        status, response = await self.make_request(
            "POST", "/agency/workspace",
            data={
                "name": "Test Agency Workspace",
                "description": "Testing workspace creation"
            }
        )
        
        workspace_blocked_pro = status == 403
        self.log_result("Pro Tier Workspace Block", workspace_blocked_pro, 
                       f"Status: {status}, Pro tier properly blocked from agency: {workspace_blocked_pro}")
        
        # Upgrade to Studio tier
        status, response = await self.make_request(
            "POST", "/billing/subscription/upgrade",
            data={"tier": "studio", "billing_period": "monthly"}
        )
        
        # Try workspace creation again
        status, response = await self.make_request(
            "POST", "/agency/workspace",
            data={
                "name": "Test Agency Workspace",
                "description": "Testing workspace creation"
            }
        )
        
        workspace_created = status == 200 and "workspace_id" in response
        workspace_id = response.get("workspace_id") if workspace_created else None
        self.log_result("Studio Tier Workspace Creation", workspace_created, 
                       f"Status: {status}, Workspace ID: {workspace_id}")
        
        # Test listing workspaces
        status, response = await self.make_request("GET", "/agency/workspaces")
        workspaces_listed = status == 200
        owned_count = len(response.get("owned", [])) if isinstance(response, dict) else 0
        self.log_result("List Workspaces", workspaces_listed, 
                       f"Status: {status}, Owned workspaces: {owned_count}")
    
    async def run_targeted_tests(self):
        """Run targeted tests on specific failing areas"""
        print("🚀 STARTING TARGETED BACKEND TESTING")
        print("=" * 60)
        
        start_time = time.time()
        
        try:
            # Setup
            if not await self.setup_user_with_persona():
                return False
            
            # Run targeted tests
            await self.test_billing_endpoints()
            await self.test_content_creation()
            await self.test_auth_validation()
            await self.test_agency_workspace()
            
        except Exception as e:
            print(f"\n❌ CRITICAL ERROR: {e}")
            self.log_result("Test Suite", False, f"Critical error: {e}")
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Print summary
        print("\n" + "=" * 60)
        print("📊 TARGETED TEST RESULTS SUMMARY")
        print("=" * 60)
        
        passed_tests = [r for r in self.test_results if r["passed"]]
        failed_tests = [r for r in self.test_results if not r["passed"]]
        
        print(f"✅ PASSED: {len(passed_tests)}")
        print(f"❌ FAILED: {len(failed_tests)}")
        print(f"⏱️ DURATION: {duration:.2f} seconds")
        print(f"📈 SUCCESS RATE: {len(passed_tests)/(len(self.test_results)) * 100:.1f}%")
        
        if failed_tests:
            print("\n❌ FAILED TESTS:")
            for test in failed_tests:
                print(f"  - {test['test']}: {test['details']}")
        
        return len(failed_tests) == 0

async def main():
    """Main test runner"""
    async with TargetedTestRunner() as runner:
        success = await runner.run_targeted_tests()
        return 0 if success else 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)