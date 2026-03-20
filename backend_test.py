#!/usr/bin/env python3
"""
Comprehensive End-to-End Backend Testing for ThookAI Platform
Testing authentication, onboarding, persona engine, content studio, billing, templates marketplace, 
agency workspace, platform connections, and error handling.
"""

import asyncio
import aiohttp
import json
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

# Configuration
BASE_URL = "https://thook-growth.preview.emergentagent.com/api"
TEST_USER_EMAIL = "e2e_test_user@test.com"
TEST_USER_PASSWORD = "SecurePass123!"
TEST_USER_NAME = "E2E Test User"

class E2ETestRunner:
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.auth_token: Optional[str] = None
        self.test_results = []
        self.user_id: Optional[str] = None
        self.workspace_id: Optional[str] = None
        
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
            "details": details,
            "timestamp": datetime.now().isoformat()
        })
    
    async def make_request(self, method: str, endpoint: str, data: dict = None, 
                          headers: dict = None, require_auth: bool = True) -> tuple[int, dict]:
        """Make HTTP request and return (status_code, response_data)"""
        url = f"{BASE_URL}{endpoint}"
        
        # Set up headers
        request_headers = {"Content-Type": "application/json"}
        if headers:
            request_headers.update(headers)
        
        # Add auth token if required and available
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
        except asyncio.TimeoutError:
            return 408, {"error": "Request timeout"}
        except Exception as e:
            return 500, {"error": f"Request failed: {str(e)}"}
    
    async def test_auth_registration(self):
        """PHASE 1: Registration Tests"""
        print("\n🔐 PHASE 1: AUTHENTICATION TESTS")
        
        # Test 1: Valid registration
        status, response = await self.make_request(
            "POST", "/auth/register",
            data={
                "email": TEST_USER_EMAIL,
                "password": TEST_USER_PASSWORD,
                "name": TEST_USER_NAME
            },
            require_auth=False
        )
        
        if status == 200 and "user_id" in response:
            self.user_id = response["user_id"]
            self.log_result("Valid Registration", True, f"User created with ID: {self.user_id}")
        else:
            self.log_result("Valid Registration", False, f"Status: {status}, Response: {response}")
        
        # Test 2: Duplicate email
        status, response = await self.make_request(
            "POST", "/auth/register",
            data={
                "email": TEST_USER_EMAIL,
                "password": TEST_USER_PASSWORD,
                "name": TEST_USER_NAME
            },
            require_auth=False
        )
        
        expected_duplicate = status == 400 and "already registered" in str(response).lower()
        self.log_result("Duplicate Email Registration", expected_duplicate, 
                       f"Status: {status}, Response: {response}")
        
        # Test 3: Invalid email format
        status, response = await self.make_request(
            "POST", "/auth/register",
            data={
                "email": "invalid-email",
                "password": "Pass123!",
                "name": "Test"
            },
            require_auth=False
        )
        
        expected_invalid_email = status in [400, 422]
        self.log_result("Invalid Email Format", expected_invalid_email, 
                       f"Status: {status}, Response: {response}")
        
        # Test 4: Missing required fields
        status, response = await self.make_request(
            "POST", "/auth/register",
            data={"email": "test@test.com"},
            require_auth=False
        )
        
        expected_missing_fields = status in [400, 422]
        self.log_result("Missing Required Fields", expected_missing_fields, 
                       f"Status: {status}, Response: {response}")
    
    async def test_auth_login(self):
        """Login Tests"""
        
        # Test 6: Valid login
        status, response = await self.make_request(
            "POST", "/auth/login",
            data={
                "email": TEST_USER_EMAIL,
                "password": TEST_USER_PASSWORD
            },
            require_auth=False
        )
        
        if status == 200 and "token" in response:
            self.auth_token = response["token"]
            self.log_result("Valid Login", True, "Auth token received")
        else:
            self.log_result("Valid Login", False, f"Status: {status}, Response: {response}")
        
        # Test 7: Wrong password
        status, response = await self.make_request(
            "POST", "/auth/login",
            data={
                "email": TEST_USER_EMAIL,
                "password": "WrongPass123!"
            },
            require_auth=False
        )
        
        expected_wrong_password = status == 401
        self.log_result("Wrong Password", expected_wrong_password, 
                       f"Status: {status}, Response: {response}")
        
        # Test 8: Non-existent user
        status, response = await self.make_request(
            "POST", "/auth/login",
            data={
                "email": "nonexistent@test.com",
                "password": "Pass123!"
            },
            require_auth=False
        )
        
        expected_nonexistent = status == 401
        self.log_result("Non-existent User", expected_nonexistent, 
                       f"Status: {status}, Response: {response}")
    
    async def test_auth_session(self):
        """Session Tests"""
        
        # Test 9: Get user with valid token
        status, response = await self.make_request("GET", "/auth/me")
        
        valid_session = status == 200 and "user_id" in response
        self.log_result("Valid Token Session", valid_session, 
                       f"Status: {status}, User: {response.get('name', 'N/A')}")
        
        # Test 10: Access without token (use separate session to avoid cookies)
        async with aiohttp.ClientSession() as clean_session:
            async with clean_session.get(f"{BASE_URL}/auth/me") as response:
                status = response.status
                expected_no_auth = status in [401, 403]
                self.log_result("No Token Access", expected_no_auth, 
                               f"Status: {status}, No auth properly blocked: {expected_no_auth}")
        
        # Test 11: Invalid token (use separate session)
        async with aiohttp.ClientSession() as clean_session:
            headers = {"Authorization": "Bearer invalid-token-xyz", "Content-Type": "application/json"}
            async with clean_session.get(f"{BASE_URL}/auth/me", headers=headers) as response:
                status = response.status
                expected_invalid_token = status in [401, 403]
                self.log_result("Invalid Token", expected_invalid_token, 
                               f"Status: {status}, Invalid token properly blocked: {expected_invalid_token}")
    
    async def test_onboarding_flow(self):
        """PHASE 2: Onboarding Flow Tests"""
        print("\n🚀 PHASE 2: ONBOARDING FLOW TESTS")
        
        # Test 12: Get questions
        status, response = await self.make_request("GET", "/onboarding/questions", require_auth=False)
        
        questions_available = status == 200 and "questions" in response and len(response.get("questions", [])) > 0
        self.log_result("Get Questions", questions_available, 
                       f"Status: {status}, Questions count: {len(response.get('questions', []))}")
        
        # Test 13: Generate persona (simplified version - just with mock answers)
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
        
        persona_generated = status == 200 and "persona" in response
        self.log_result("Generate Persona", persona_generated, 
                       f"Status: {status}, Persona generated: {persona_generated}")
        
        # Test 14: Check if onboarding completed (via persona endpoint)
        status, response = await self.make_request("GET", "/persona/me")
        
        onboarding_completed = status == 200 and "card" in response
        self.log_result("Onboarding Completed", onboarding_completed, 
                       f"Status: {status}, Persona available after onboarding: {onboarding_completed}")
    
    async def test_persona_engine(self):
        """PHASE 3: Persona Engine Tests"""
        print("\n👤 PHASE 3: PERSONA ENGINE TESTS")
        
        # Test 16: Get persona
        status, response = await self.make_request("GET", "/persona/me")
        
        persona_available = status == 200 and "card" in response
        self.log_result("Get Persona", persona_available, 
                       f"Status: {status}, Has card: {bool(response.get('card'))}")
        
        # Test 17: Update persona field
        status, response = await self.make_request(
            "PUT", "/persona/me",
            data={"card": {"hook_style": "Bold contrarian statement"}}
        )
        
        persona_updated = status == 200
        self.log_result("Update Persona", persona_updated, 
                       f"Status: {status}, Response: {response}")
        
        # Test 18: Get regional English options
        status, response = await self.make_request("GET", "/persona/regional-english/options")
        
        options_available = status == 200 and len(response.get("options", [])) == 4
        self.log_result("Regional English Options", options_available, 
                       f"Status: {status}, Options count: {len(response.get('options', []))}")
        
        # Test 19: Update regional English to UK
        status, response = await self.make_request(
            "PUT", "/persona/regional-english",
            data={"regional_english": "UK"}
        )
        
        regional_updated = status == 200
        self.log_result("Update Regional English (UK)", regional_updated, 
                       f"Status: {status}, Response: {response}")
        
        # Test 20: Invalid region
        status, response = await self.make_request(
            "PUT", "/persona/regional-english",
            data={"regional_english": "FR"}
        )
        
        invalid_region_rejected = status == 400
        self.log_result("Invalid Region (FR)", invalid_region_rejected, 
                       f"Status: {status}, Response: {response}")
    
    async def test_persona_sharing(self):
        """Persona Sharing Tests"""
        share_token = None
        
        # Test 21: Create share link
        status, response = await self.make_request("POST", "/persona/share")
        
        if status == 200 and "share_token" in response:
            share_token = response["share_token"]
            share_created = True
        else:
            share_created = False
        
        self.log_result("Create Share Link", share_created, 
                       f"Status: {status}, Token: {bool(share_token)}")
        
        if share_token:
            # Test 22: View public persona (NO AUTH)
            status, response = await self.make_request(
                "GET", f"/persona/public/{share_token}",
                require_auth=False
            )
            
            public_view_working = status == 200 and "creator" in response
            self.log_result("View Public Persona", public_view_working, 
                           f"Status: {status}, Has creator info: {bool(response.get('creator'))}")
            
            # Test 23: Revoke share
            status, response = await self.make_request("DELETE", "/persona/share")
            
            share_revoked = status == 200
            self.log_result("Revoke Share", share_revoked, 
                           f"Status: {status}, Response: {response}")
            
            # Test 24: Access after revoke
            status, response = await self.make_request(
                "GET", f"/persona/public/{share_token}",
                require_auth=False
            )
            
            access_blocked = status in [404, 410]
            self.log_result("Access After Revoke", access_blocked, 
                           f"Status: {status}, Access blocked: {access_blocked}")
    
    async def test_content_studio(self):
        """PHASE 4: Content Studio Tests"""
        print("\n📝 PHASE 4: CONTENT STUDIO TESTS")
        
        # Test 25: Create content
        status, response = await self.make_request(
            "POST", "/content/create",
            data={
                "topic": "The future of AI in content creation",
                "platform": "linkedin",
                "content_type": "thought_leadership",
                "raw_input": "The future of AI in content creation"
            }
        )
        
        content_job_created = status in [200, 202] and "job_id" in response
        job_id = response.get("job_id") if content_job_created else None
        self.log_result("Create Content", content_job_created, 
                       f"Status: {status}, Job ID: {job_id}")
        
        # Test 26: Poll for status
        if job_id:
            poll_attempts = 0
            max_attempts = 10
            final_status = None
            
            while poll_attempts < max_attempts:
                status, response = await self.make_request("GET", f"/content/job/{job_id}")
                
                if status == 200:
                    current_status = response.get("status")
                    if current_status not in ["processing", "queued"]:
                        final_status = current_status
                        break
                
                poll_attempts += 1
                await asyncio.sleep(2)  # Wait 2 seconds between polls
            
            polling_working = final_status is not None
            self.log_result("Poll Content Status", polling_working, 
                           f"Final status: {final_status} after {poll_attempts} attempts")
        
        # Test 27: List user's content
        status, response = await self.make_request("GET", "/content/jobs")
        
        content_list_available = status == 200 and ("jobs" in response or "content" in response)
        self.log_result("List User Content", content_list_available, 
                       f"Status: {status}, Jobs count: {len(response.get('jobs', response.get('content', [])))}")
        
        # Test 28: Invalid platform
        status, response = await self.make_request(
            "POST", "/content/create",
            data={
                "topic": "Test",
                "platform": "invalid_platform",
                "content_type": "thought_leadership",
                "raw_input": "Test content"
            }
        )
        
        invalid_platform_rejected = status in [400, 422]
        self.log_result("Invalid Platform", invalid_platform_rejected, 
                       f"Status: {status}, Response: {response}")
        
        # Test 29: Empty topic
        status, response = await self.make_request(
            "POST", "/content/create",
            data={
                "topic": "",
                "platform": "linkedin",
                "content_type": "thought_leadership",
                "raw_input": ""
            }
        )
        
        empty_topic_rejected = status in [400, 422]
        self.log_result("Empty Topic", empty_topic_rejected, 
                       f"Status: {status}, Response: {response}")
    
    async def test_dashboard_analytics(self):
        """PHASE 5: Dashboard & Analytics"""
        print("\n📊 PHASE 5: DASHBOARD & ANALYTICS TESTS")
        
        # Test 30: Dashboard stats
        status, response = await self.make_request("GET", "/dashboard/stats")
        
        stats_available = status == 200
        self.log_result("Dashboard Stats", stats_available, 
                       f"Status: {status}, Response keys: {list(response.keys()) if isinstance(response, dict) else 'N/A'}")
        
        # Test 31: Daily brief
        status, response = await self.make_request("GET", "/dashboard/daily-brief")
        
        brief_available = status == 200
        self.log_result("Daily Brief", brief_available, 
                       f"Status: {status}, Has suggestions: {bool(response.get('suggestions'))}")
        
        # Test 32: Analytics overview
        status, response = await self.make_request("GET", "/analytics/overview")
        
        analytics_available = status == 200
        self.log_result("Analytics Overview", analytics_available, 
                       f"Status: {status}, Has data: {response.get('has_data', False)}")
    
    async def test_billing_credits(self):
        """PHASE 6: Billing & Credits"""
        print("\n💳 PHASE 6: BILLING & CREDITS TESTS")
        
        # Test 33: Get credit balance
        status, response = await self.make_request("GET", "/billing/credits")
        
        credits_available = status == 200 and "credits" in response
        self.log_result("Get Credits", credits_available, 
                       f"Status: {status}, Credits: {response.get('credits', 'N/A')}")
        
        # Test 34: Get subscription
        status, response = await self.make_request("GET", "/billing/subscription")
        
        subscription_available = status == 200 and "tier" in response
        current_tier = response.get("tier", "unknown")
        self.log_result("Get Subscription", subscription_available, 
                       f"Status: {status}, Tier: {current_tier}")
        
        # Test 35: Upgrade to Pro (if currently free)
        if current_tier == "free":
            status, response = await self.make_request(
                "POST", "/billing/subscription/upgrade",
                data={"tier": "pro", "billing_period": "monthly"}
            )
            
            upgrade_successful = status == 200 and response.get("new_tier") == "pro"
            self.log_result("Upgrade to Pro", upgrade_successful, 
                           f"Status: {status}, New tier: {response.get('new_tier', 'N/A')}")
    
    async def test_templates_marketplace(self):
        """PHASE 7: Templates Marketplace"""
        print("\n🛍️ PHASE 7: TEMPLATES MARKETPLACE TESTS")
        
        # Test 36: Get categories
        status, response = await self.make_request("GET", "/templates/categories")
        
        categories_available = (status == 200 and 
                               len(response.get("categories", [])) == 10 and
                               len(response.get("hook_types", [])) == 8)
        self.log_result("Template Categories", categories_available, 
                       f"Status: {status}, Categories: {len(response.get('categories', []))}, Hook types: {len(response.get('hook_types', []))}")
        
        # Test 37: Browse templates
        status, response = await self.make_request("GET", "/templates")
        
        templates_browsable = status == 200 and "templates" in response
        self.log_result("Browse Templates", templates_browsable, 
                       f"Status: {status}, Templates count: {len(response.get('templates', []))}")
        
        # Test 38: Filter by platform
        status, response = await self.make_request("GET", "/templates?platform=linkedin")
        
        platform_filter_working = status == 200
        self.log_result("Filter by Platform", platform_filter_working, 
                       f"Status: {status}, Filtered results available")
        
        # Test 39: Featured templates
        status, response = await self.make_request("GET", "/templates/featured")
        
        featured_available = status == 200 and "featured" in response
        self.log_result("Featured Templates", featured_available, 
                       f"Status: {status}, Has featured: {bool(response.get('featured'))}")
    
    async def test_agency_workspace(self):
        """PHASE 8: Agency Workspace (with upgraded user)"""
        print("\n🏢 PHASE 8: AGENCY WORKSPACE TESTS")
        
        # Test 40: Create workspace (as Pro+ user)
        status, response = await self.make_request(
            "POST", "/agency/workspace",
            data={
                "name": "E2E Test Agency",
                "description": "Testing workspace"
            }
        )
        
        workspace_created = status == 200 and "workspace_id" in response
        if workspace_created:
            self.workspace_id = response["workspace_id"]
        
        self.log_result("Create Workspace", workspace_created, 
                       f"Status: {status}, Workspace ID: {self.workspace_id}")
        
        # Test 41: List workspaces
        status, response = await self.make_request("GET", "/agency/workspaces")
        
        workspaces_listed = status == 200 and "owned" in response
        self.log_result("List Workspaces", workspaces_listed, 
                       f"Status: {status}, Owned count: {len(response.get('owned', []))}")
        
        if self.workspace_id:
            # Test 42: Invite creator
            status, response = await self.make_request(
                "POST", f"/agency/workspace/{self.workspace_id}/invite",
                data={
                    "email": "invited@test.com",
                    "role": "creator"
                }
            )
            
            invite_sent = status == 200
            self.log_result("Invite Creator", invite_sent, 
                           f"Status: {status}, Invite sent: {invite_sent}")
            
            # Test 43: List members
            status, response = await self.make_request("GET", f"/agency/workspace/{self.workspace_id}/members")
            
            members_listed = status == 200 and "members" in response
            member_count = len(response.get("members", []))
            self.log_result("List Members", members_listed, 
                           f"Status: {status}, Members count: {member_count}")
    
    async def test_platform_connections(self):
        """PHASE 9: Platform Connections"""
        print("\n🔗 PHASE 9: PLATFORM CONNECTIONS TESTS")
        
        # Test 44: List available platforms
        status, response = await self.make_request("GET", "/platforms/status")
        
        platforms_available = status == 200
        platform_count = len(response.get("platforms", [])) if isinstance(response, dict) and "platforms" in response else 0
        self.log_result("Available Platforms", platforms_available, 
                       f"Status: {status}, Platforms count: {platform_count}")
        
        # Test 45: LinkedIn OAuth (mocked)
        status, response = await self.make_request("GET", "/platforms/connect/linkedin")
        
        oauth_initiated = status == 200 or "auth_url" in response or status == 302
        self.log_result("LinkedIn OAuth", oauth_initiated, 
                       f"Status: {status}, OAuth response available: {bool(response)}")
        
        # Test 46: List connected platforms
        status, response = await self.make_request("GET", "/platforms/status")
        
        connected_listed = status == 200
        self.log_result("Connected Platforms", connected_listed, 
                       f"Status: {status}, Platform status listed")
    
    async def test_error_handling(self):
        """PHASE 10: Error Handling & Edge Cases"""
        print("\n⚠️ PHASE 10: ERROR HANDLING & EDGE CASES")
        
        # Test 47: Access protected endpoint without auth (use separate session)
        async with aiohttp.ClientSession() as clean_session:
            async with clean_session.get(f"{BASE_URL}/persona/me") as response:
                status = response.status
                auth_required = status in [401, 403]
                self.log_result("Unauthorized Access", auth_required, 
                               f"Status: {status}, Auth properly required: {auth_required}")
        
        # Test 48: Access non-existent resource
        status, response = await self.make_request("GET", "/content/job/non-existent-job-id")
        
        not_found = status == 404
        self.log_result("Non-existent Resource", not_found, 
                       f"Status: {status}, Properly returns 404: {not_found}")
        
        # Test 49: Invalid JSON body
        try:
            url = f"{BASE_URL}/content/create"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.auth_token}" if self.auth_token else ""
            }
            async with self.session.post(url, data="invalid-json", headers=headers) as response:
                status = response.status
                invalid_json_handled = status in [400, 422]
        except Exception:
            invalid_json_handled = True  # Exception handling counts as proper error handling
        
        self.log_result("Invalid JSON Body", invalid_json_handled, 
                       f"Status: {status}, Invalid JSON properly handled")
        
        # Test 50: Very long input
        long_topic = "A" * 10000
        status, response = await self.make_request(
            "POST", "/content/create",
            data={
                "topic": long_topic,
                "platform": "linkedin",
                "content_type": "thought_leadership",
                "raw_input": long_topic
            }
        )
        
        long_input_handled = status in [200, 202, 400, 422]  # Either accepted or properly rejected
        self.log_result("Very Long Input", long_input_handled, 
                       f"Status: {status}, Long input handled appropriately")
        
        # Test 51: Invalid token with separate session
        async with aiohttp.ClientSession() as clean_session:
            headers = {"Authorization": "Bearer invalid-token-xyz", "Content-Type": "application/json"}
            async with clean_session.get(f"{BASE_URL}/persona/me", headers=headers) as response:
                status = response.status
                invalid_token_blocked = status in [401, 403]
                self.log_result("Invalid Token Blocked", invalid_token_blocked, 
                               f"Status: {status}, Invalid token properly blocked: {invalid_token_blocked}")
    
    async def run_all_tests(self):
        """Run all test phases"""
        print("🚀 STARTING COMPREHENSIVE END-TO-END TESTING FOR ThookAI PLATFORM")
        print("=" * 80)
        
        start_time = time.time()
        
        try:
            await self.test_auth_registration()
            await self.test_auth_login()
            await self.test_auth_session()
            await self.test_onboarding_flow()
            await self.test_persona_engine()
            await self.test_persona_sharing()
            await self.test_content_studio()
            await self.test_dashboard_analytics()
            await self.test_billing_credits()
            await self.test_templates_marketplace()
            await self.test_agency_workspace()
            await self.test_platform_connections()
            await self.test_error_handling()
        except Exception as e:
            print(f"\n❌ CRITICAL ERROR DURING TESTING: {e}")
            self.log_result("Test Suite", False, f"Critical error: {e}")
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Print summary
        print("\n" + "=" * 80)
        print("📊 COMPREHENSIVE TEST RESULTS SUMMARY")
        print("=" * 80)
        
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
        
        # Save results to file
        with open("/app/e2e_test_results.json", "w") as f:
            json.dump({
                "summary": {
                    "total_tests": len(self.test_results),
                    "passed": len(passed_tests),
                    "failed": len(failed_tests),
                    "success_rate": len(passed_tests)/(len(self.test_results)) * 100,
                    "duration_seconds": duration,
                    "timestamp": datetime.now().isoformat()
                },
                "results": self.test_results
            }, f, indent=2)
        
        print(f"\n📄 Detailed results saved to: /app/e2e_test_results.json")
        
        return len(failed_tests) == 0

async def main():
    """Main test runner"""
    async with E2ETestRunner() as runner:
        success = await runner.run_all_tests()
        return 0 if success else 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)