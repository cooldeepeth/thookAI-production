#!/usr/bin/env python3
"""
ThookAI Backend Testing - Production Launch Preparation
Testing billing configuration, credit costs, subscription endpoints, and checkout flows.
"""

import asyncio
import aiohttp
import json
import time
from datetime import datetime
from typing import Dict, Any, Optional

# Configuration
BASE_URL = "https://staging-38.preview.emergentagent.com/api"
TEST_USER_EMAIL = f"billing_test_{int(time.time())}@test.com"
TEST_USER_PASSWORD = "SecurePass123!"
TEST_USER_NAME = "Billing Test User"

class BillingTestRunner:
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.auth_token: Optional[str] = None
        self.test_results = []
        self.user_id: Optional[str] = None
        
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
    
    async def setup_test_user(self):
        """Register and login test user"""
        print("\n🔐 SETTING UP TEST USER")
        
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
        
        if status == 200 and "user_id" in response:
            self.user_id = response["user_id"]
            self.log_result("User Registration", True, f"User created with ID: {self.user_id}")
        else:
            self.log_result("User Registration", False, f"Status: {status}, Response: {response}")
            return False
        
        # Login to get token
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
            self.log_result("User Login", True, "Auth token received")
            return True
        else:
            self.log_result("User Login", False, f"Status: {status}, Response: {response}")
            return False
    
    async def test_billing_config_endpoint(self):
        """Test 1: BILLING CONFIG ENDPOINT"""
        print("\n💳 TEST 1: BILLING CONFIG ENDPOINT")
        
        status, response = await self.make_request("GET", "/billing/config", require_auth=False)
        
        # Check basic response structure
        config_valid = (
            status == 200 and
            "configured" in response and
            "publishable_key" in response and
            "prices" in response and
            "credit_packages" in response
        )
        
        if config_valid:
            # Verify early bird pricing
            prices = response.get("prices", {})
            expected_prices = {
                "pro": 1900,    # $19.00
                "studio": 4900, # $49.00
                "agency": 12900 # $129.00
            }
            
            pricing_correct = True
            pricing_details = []
            
            for tier, expected_cents in expected_prices.items():
                if tier in prices:
                    actual_monthly = prices[tier].get("monthly", 0)
                    if actual_monthly == expected_cents:
                        pricing_details.append(f"{tier}: ${expected_cents/100:.0f} ✓")
                    else:
                        pricing_details.append(f"{tier}: expected ${expected_cents/100:.0f}, got ${actual_monthly/100:.2f} ✗")
                        pricing_correct = False
                else:
                    pricing_details.append(f"{tier}: missing ✗")
                    pricing_correct = False
            
            self.log_result("Billing Config Structure", True, f"configured={response.get('configured')}, publishable_key={response.get('publishable_key')}")
            self.log_result("Early Bird Pricing", pricing_correct, "; ".join(pricing_details))
        else:
            self.log_result("Billing Config Structure", False, f"Status: {status}, Response: {response}")
    
    async def test_credit_costs_endpoint(self):
        """Test 2: CREDIT COSTS ENDPOINT"""
        print("\n🪙 TEST 2: CREDIT COSTS ENDPOINT")
        
        status, response = await self.make_request("GET", "/billing/credits/costs", require_auth=False)
        
        if status == 200 and "costs" in response:
            costs = response["costs"]
            
            # Expected operations with unique values
            expected_operations = {
                "content_create": 10,
                "content_regenerate": 4,
                "image_generate": 8,
                "carousel_generate": 15,
                "voice_narration": 12,
                "video_generate": 50,
                "repurpose": 3,
                "series_plan": 6,
                "ai_insights": 2,
                "viral_predict": 1
            }
            
            # Check if all 10 operations are present
            operations_present = len(costs) >= 10
            self.log_result("Credit Costs Count", operations_present, f"Found {len(costs)} operations (expected 10+)")
            
            # Check specific operations and their costs
            operations_correct = True
            operation_details = []
            
            for op_name, expected_cost in expected_operations.items():
                if op_name in costs:
                    actual_cost = costs[op_name].get("credits", 0)
                    if actual_cost == expected_cost:
                        operation_details.append(f"{op_name}: {actual_cost} ✓")
                    else:
                        operation_details.append(f"{op_name}: expected {expected_cost}, got {actual_cost} ✗")
                        operations_correct = False
                else:
                    operation_details.append(f"{op_name}: missing ✗")
                    operations_correct = False
            
            self.log_result("Credit Costs Values", operations_correct, "; ".join(operation_details))
            
            # Check for unique values
            credit_values = [costs[op].get("credits", 0) for op in costs]
            unique_values = len(set(credit_values)) == len(credit_values)
            self.log_result("Credit Costs Uniqueness", unique_values, f"All values unique: {unique_values}")
            
        else:
            self.log_result("Credit Costs Endpoint", False, f"Status: {status}, Response: {response}")
    
    async def test_subscription_endpoints(self):
        """Test 3: SUBSCRIPTION ENDPOINTS (authenticated)"""
        print("\n📋 TEST 3: SUBSCRIPTION ENDPOINTS")
        
        # Test 3a: Current subscription
        status, response = await self.make_request("GET", "/billing/subscription")
        
        subscription_valid = (
            status == 200 and
            "tier" in response and
            "tier_name" in response and
            "is_active" in response and
            "features" in response
        )
        
        current_tier = response.get("tier", "unknown")
        self.log_result("Current Subscription", subscription_valid, 
                       f"Status: {status}, Tier: {current_tier}")
        
        # Test 3b: Available tiers with pricing
        status, response = await self.make_request("GET", "/billing/subscription/tiers")
        
        tiers_valid = (
            status == 200 and
            "tiers" in response and
            "current_tier" in response
        )
        
        if tiers_valid:
            tiers = response.get("tiers", [])
            tier_count = len(tiers)
            tier_names = [tier.get("id", "unknown") for tier in tiers]
            self.log_result("Available Tiers", True, 
                           f"Found {tier_count} tiers: {', '.join(tier_names)}")
        else:
            self.log_result("Available Tiers", False, f"Status: {status}, Response: {response}")
        
        # Test 3c: Feature limits
        status, response = await self.make_request("GET", "/billing/subscription/limits")
        
        limits_valid = (
            status == 200 and
            "tier" in response and
            "limits" in response and
            "feature_access" in response
        )
        
        self.log_result("Feature Limits", limits_valid, 
                       f"Status: {status}, Has limits structure: {limits_valid}")
        
        # Test 3d: Daily content limit
        status, response = await self.make_request("GET", "/billing/subscription/daily-limit")
        
        daily_limit_valid = status == 200
        self.log_result("Daily Content Limit", daily_limit_valid, 
                       f"Status: {status}, Response available: {daily_limit_valid}")
    
    async def test_checkout_endpoints(self):
        """Test 4: CHECKOUT ENDPOINTS (authenticated)"""
        print("\n🛒 TEST 4: CHECKOUT ENDPOINTS")
        
        # Test 4a: Subscription checkout
        status, response = await self.make_request(
            "POST", "/billing/subscription/checkout",
            data={"tier": "pro", "billing_period": "monthly"}
        )
        
        subscription_checkout_valid = (
            status == 200 and
            ("checkout_url" in response or "simulated" in response)
        )
        
        checkout_details = ""
        if "simulated" in response and response["simulated"]:
            checkout_details = "Simulated checkout (Stripe not configured)"
        elif "checkout_url" in response:
            checkout_details = f"Checkout URL: {response['checkout_url'][:50]}..."
        
        self.log_result("Subscription Checkout", subscription_checkout_valid, 
                       f"Status: {status}, {checkout_details}")
        
        # Test 4b: Credit checkout
        status, response = await self.make_request(
            "POST", "/billing/credits/checkout",
            data={"package": "small"}
        )
        
        credit_checkout_valid = (
            status == 200 and
            ("checkout_url" in response or "simulated" in response)
        )
        
        credit_details = ""
        if "simulated" in response and response["simulated"]:
            credit_details = f"Simulated: {response.get('credits', 0)} credits"
        elif "checkout_url" in response:
            credit_details = f"Checkout URL: {response['checkout_url'][:50]}..."
        
        self.log_result("Credit Checkout", credit_checkout_valid, 
                       f"Status: {status}, {credit_details}")
    
    async def test_simulate_endpoints(self):
        """Test 5: SIMULATE ENDPOINTS (dev only)"""
        print("\n🧪 TEST 5: SIMULATE ENDPOINTS")
        
        # Test 5a: Simulate upgrade
        status, response = await self.make_request(
            "POST", "/billing/simulate/upgrade",
            data={"tier": "pro"}
        )
        
        if status == 200:
            simulate_upgrade_valid = (
                "success" in response and
                response.get("success") and
                "new_tier" in response and
                response.get("new_tier") == "pro"
            )
            
            credits_granted = response.get("credits", 0)
            self.log_result("Simulate Upgrade", simulate_upgrade_valid, 
                           f"Upgraded to {response.get('new_tier')}, Credits: {credits_granted}")
        elif status == 403:
            self.log_result("Simulate Upgrade", True, 
                           "Correctly disabled in production environment")
        else:
            self.log_result("Simulate Upgrade", False, 
                           f"Status: {status}, Response: {response}")
    
    async def test_regression_endpoints(self):
        """Test 6: REGRESSION TEST - Existing Endpoints"""
        print("\n🔄 TEST 6: REGRESSION TEST")
        
        # Test 6a: Health check
        status, response = await self.make_request("GET", "/health", require_auth=False)
        
        health_valid = status == 200 and "status" in response
        self.log_result("Health Check", health_valid, 
                       f"Status: {status}, Health: {response.get('status', 'unknown')}")
        
        # Test 6b: Template categories
        status, response = await self.make_request("GET", "/templates/categories", require_auth=False)
        
        categories_valid = (
            status == 200 and
            "categories" in response and
            len(response.get("categories", [])) > 0
        )
        
        category_count = len(response.get("categories", []))
        self.log_result("Template Categories", categories_valid, 
                       f"Status: {status}, Categories: {category_count}")
        
        # Test 6c: Current credits (after potential upgrade)
        status, response = await self.make_request("GET", "/billing/credits")
        
        credits_valid = (
            status == 200 and
            "credits" in response and
            "tier" in response
        )
        
        current_credits = response.get("credits", 0)
        current_tier = response.get("tier", "unknown")
        self.log_result("Current Credits", credits_valid, 
                       f"Credits: {current_credits}, Tier: {current_tier}")
    
    async def run_all_tests(self):
        """Run all billing tests"""
        print("🚀 STARTING THOOKAI BILLING BACKEND TESTING")
        print("=" * 80)
        
        start_time = time.time()
        
        try:
            # Setup
            if not await self.setup_test_user():
                print("❌ Failed to setup test user, aborting tests")
                return False
            
            # Run tests
            await self.test_billing_config_endpoint()
            await self.test_credit_costs_endpoint()
            await self.test_subscription_endpoints()
            await self.test_checkout_endpoints()
            await self.test_simulate_endpoints()
            await self.test_regression_endpoints()
            
        except Exception as e:
            print(f"\n❌ CRITICAL ERROR DURING TESTING: {e}")
            self.log_result("Test Suite", False, f"Critical error: {e}")
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Print summary
        print("\n" + "=" * 80)
        print("📊 BILLING TEST RESULTS SUMMARY")
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
        with open("/app/billing_test_results.json", "w") as f:
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
        
        print(f"\n📄 Detailed results saved to: /app/billing_test_results.json")
        
        return len(failed_tests) == 0

async def main():
    """Main test runner"""
    async with BillingTestRunner() as runner:
        success = await runner.run_all_tests()
        return 0 if success else 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)