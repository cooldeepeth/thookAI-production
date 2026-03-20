#!/usr/bin/env python3
"""
Sprint 10 Backend Testing for ThookAI Platform

Tests:
- Credit System (balance, usage, costs)
- Subscription Tiers (details, tiers, limits, upgrade)
- Viral Hook Predictor (predict, improve, batch, patterns)

All tests use the external production URL and real authentication.
"""
import requests
import json
import time
from datetime import datetime
from typing import Dict, Any

# Production configuration - DO NOT CHANGE
BASE_URL = "https://thook-growth.preview.emergentagent.com/api"
session = requests.Session()

def log_test(test_name: str, success: bool, details: str = ""):
    """Log test results with timestamp."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"[{timestamp}] {status} - {test_name}")
    if details:
        print(f"    Details: {details}")
    print()

def register_and_auth() -> Dict[str, Any]:
    """Register a new test user and get authentication token."""
    timestamp = int(time.time() * 1000)
    test_user = {
        "email": f"sprint10test{timestamp}@example.com",
        "password": "TestPass123!",
        "name": f"Sprint10 Test User {timestamp}"
    }
    
    print(f"🔐 Registering test user: {test_user['email']}")
    
    # Register user
    register_response = session.post(f"{BASE_URL}/auth/register", json=test_user)
    if register_response.status_code != 200:
        raise Exception(f"Registration failed: {register_response.text}")
    
    # Login to get token
    login_response = session.post(f"{BASE_URL}/auth/login", json={
        "email": test_user["email"],
        "password": test_user["password"]
    })
    
    if login_response.status_code != 200:
        raise Exception(f"Login failed: {login_response.text}")
    
    login_data = login_response.json()
    token = login_data.get("token")
    
    if not token:
        raise Exception("No token received")
    
    # Set auth header for all future requests
    session.headers.update({"Authorization": f"Bearer {token}"})
    
    print(f"✅ Authentication successful for {test_user['email']}")
    print(f"🪙 Token: {token[:20]}...")
    print()
    
    return {
        "user": test_user,
        "token": token,
        "user_id": login_data.get("user_id")
    }

# ============ CREDIT SYSTEM TESTS ============

def test_get_credit_balance():
    """Test GET /api/billing/credits - Credit balance endpoint"""
    try:
        response = session.get(f"{BASE_URL}/billing/credits")
        
        if response.status_code != 200:
            log_test("Credit Balance Endpoint", False, f"Status: {response.status_code}, Response: {response.text}")
            return False
        
        data = response.json()
        
        # Validate response structure
        required_fields = ["success", "credits", "monthly_allowance", "used_this_period", "tier", "is_low_balance"]
        missing_fields = [f for f in required_fields if f not in data]
        
        if missing_fields:
            log_test("Credit Balance Endpoint", False, f"Missing fields: {missing_fields}")
            return False
        
        if not data.get("success"):
            log_test("Credit Balance Endpoint", False, f"API returned success=false: {data}")
            return False
        
        # Validate data types and ranges
        if not isinstance(data["credits"], int) or data["credits"] < 0:
            log_test("Credit Balance Endpoint", False, f"Invalid credits value: {data['credits']}")
            return False
        
        if not isinstance(data["monthly_allowance"], int) or data["monthly_allowance"] <= 0:
            log_test("Credit Balance Endpoint", False, f"Invalid monthly_allowance: {data['monthly_allowance']}")
            return False
        
        log_test("Credit Balance Endpoint", True, f"Credits: {data['credits']}, Tier: {data['tier']}, Monthly: {data['monthly_allowance']}")
        return True
        
    except Exception as e:
        log_test("Credit Balance Endpoint", False, f"Exception: {str(e)}")
        return False

def test_get_credit_usage():
    """Test GET /api/billing/credits/usage - Credit usage history"""
    try:
        response = session.get(f"{BASE_URL}/billing/credits/usage?days=30&limit=50")
        
        if response.status_code != 200:
            log_test("Credit Usage History", False, f"Status: {response.status_code}, Response: {response.text}")
            return False
        
        data = response.json()
        
        # Validate response structure
        required_fields = ["success", "transactions", "summary"]
        missing_fields = [f for f in required_fields if f not in data]
        
        if missing_fields:
            log_test("Credit Usage History", False, f"Missing fields: {missing_fields}")
            return False
        
        if not data.get("success"):
            log_test("Credit Usage History", False, f"API returned success=false: {data}")
            return False
        
        # Validate summary structure
        summary = data.get("summary", {})
        summary_fields = ["total_deducted", "total_added", "net_change", "by_operation"]
        missing_summary = [f for f in summary_fields if f not in summary]
        
        if missing_summary:
            log_test("Credit Usage History", False, f"Missing summary fields: {missing_summary}")
            return False
        
        transaction_count = len(data.get("transactions", []))
        log_test("Credit Usage History", True, f"Retrieved {transaction_count} transactions, Net change: {summary['net_change']}")
        return True
        
    except Exception as e:
        log_test("Credit Usage History", False, f"Exception: {str(e)}")
        return False

def test_get_operation_costs():
    """Test GET /api/billing/credits/costs - Operation costs"""
    try:
        response = session.get(f"{BASE_URL}/billing/credits/costs")
        
        if response.status_code != 200:
            log_test("Operation Costs", False, f"Status: {response.status_code}, Response: {response.text}")
            return False
        
        data = response.json()
        
        if "costs" not in data:
            log_test("Operation Costs", False, f"Missing 'costs' field in response: {data}")
            return False
        
        costs = data["costs"]
        
        # Check for expected operations
        expected_operations = ["content_create", "viral_predict", "repurpose", "ai_insights"]
        found_operations = []
        
        for op_name, op_data in costs.items():
            found_operations.append(op_name)
            if not isinstance(op_data, dict) or "credits" not in op_data or "name" not in op_data:
                log_test("Operation Costs", False, f"Invalid operation data for {op_name}: {op_data}")
                return False
        
        log_test("Operation Costs", True, f"Found {len(costs)} operations: {', '.join(found_operations[:5])}")
        return True
        
    except Exception as e:
        log_test("Operation Costs", False, f"Exception: {str(e)}")
        return False

# ============ SUBSCRIPTION TESTS ============

def test_get_subscription_details():
    """Test GET /api/billing/subscription - Current subscription details"""
    try:
        response = session.get(f"{BASE_URL}/billing/subscription")
        
        if response.status_code != 200:
            log_test("Subscription Details", False, f"Status: {response.status_code}, Response: {response.text}")
            return False
        
        data = response.json()
        
        # Validate response structure
        required_fields = ["success", "tier", "tier_name", "is_active", "features"]
        missing_fields = [f for f in required_fields if f not in data]
        
        if missing_fields:
            log_test("Subscription Details", False, f"Missing fields: {missing_fields}")
            return False
        
        if not data.get("success"):
            log_test("Subscription Details", False, f"API returned success=false: {data}")
            return False
        
        # Validate features structure
        features = data.get("features", {})
        expected_features = ["max_personas", "platforms", "content_per_day", "series_enabled"]
        
        missing_features = [f for f in expected_features if f not in features]
        if missing_features:
            log_test("Subscription Details", False, f"Missing feature fields: {missing_features}")
            return False
        
        log_test("Subscription Details", True, f"Tier: {data['tier_name']}, Active: {data['is_active']}, Platforms: {len(features.get('platforms', []))}")
        return True
        
    except Exception as e:
        log_test("Subscription Details", False, f"Exception: {str(e)}")
        return False

def test_get_available_tiers():
    """Test GET /api/billing/subscription/tiers - Available subscription tiers"""
    try:
        response = session.get(f"{BASE_URL}/billing/subscription/tiers")
        
        if response.status_code != 200:
            log_test("Available Tiers", False, f"Status: {response.status_code}, Response: {response.text}")
            return False
        
        data = response.json()
        
        # Validate response structure
        required_fields = ["success", "tiers", "current_tier"]
        missing_fields = [f for f in required_fields if f not in data]
        
        if missing_fields:
            log_test("Available Tiers", False, f"Missing fields: {missing_fields}")
            return False
        
        if not data.get("success"):
            log_test("Available Tiers", False, f"API returned success=false: {data}")
            return False
        
        tiers = data.get("tiers", [])
        
        if len(tiers) != 4:
            log_test("Available Tiers", False, f"Expected 4 tiers, got {len(tiers)}")
            return False
        
        # Check for expected tiers
        expected_tier_ids = {"free", "pro", "studio", "agency"}
        found_tier_ids = {tier.get("id") for tier in tiers}
        
        if expected_tier_ids != found_tier_ids:
            log_test("Available Tiers", False, f"Expected tiers {expected_tier_ids}, got {found_tier_ids}")
            return False
        
        # Validate tier structure
        for tier in tiers:
            required_tier_fields = ["id", "name", "price_monthly", "monthly_credits", "features"]
            missing_tier_fields = [f for f in required_tier_fields if f not in tier]
            if missing_tier_fields:
                log_test("Available Tiers", False, f"Missing tier fields in {tier.get('id')}: {missing_tier_fields}")
                return False
        
        tier_names = [tier["name"] for tier in tiers]
        log_test("Available Tiers", True, f"Found all 4 tiers: {', '.join(tier_names)}, Current: {data['current_tier']}")
        return True
        
    except Exception as e:
        log_test("Available Tiers", False, f"Exception: {str(e)}")
        return False

def test_get_feature_limits():
    """Test GET /api/billing/subscription/limits - Feature limits"""
    try:
        response = session.get(f"{BASE_URL}/billing/subscription/limits")
        
        if response.status_code != 200:
            log_test("Feature Limits", False, f"Status: {response.status_code}, Response: {response.text}")
            return False
        
        data = response.json()
        
        # Validate response structure
        required_fields = ["success", "tier", "limits", "feature_access"]
        missing_fields = [f for f in required_fields if f not in data]
        
        if missing_fields:
            log_test("Feature Limits", False, f"Missing fields: {missing_fields}")
            return False
        
        if not data.get("success"):
            log_test("Feature Limits", False, f"API returned success=false: {data}")
            return False
        
        limits = data.get("limits", {})
        expected_limits = ["max_personas", "content_per_day", "team_members"]
        
        missing_limits = [l for l in expected_limits if l not in limits]
        if missing_limits:
            log_test("Feature Limits", False, f"Missing limit fields: {missing_limits}")
            return False
        
        # Validate limit structure (each should have limit, used, remaining)
        for limit_name, limit_data in limits.items():
            if isinstance(limit_data, dict):
                if "limit" not in limit_data:
                    log_test("Feature Limits", False, f"Missing 'limit' in {limit_name}")
                    return False
        
        feature_access = data.get("feature_access", {})
        expected_features = ["platforms", "series_enabled", "repurpose_enabled"]
        
        missing_features = [f for f in expected_features if f not in feature_access]
        if missing_features:
            log_test("Feature Limits", False, f"Missing feature access fields: {missing_features}")
            return False
        
        log_test("Feature Limits", True, f"Limits for {data['tier']} tier, Platforms: {len(feature_access.get('platforms', []))}")
        return True
        
    except Exception as e:
        log_test("Feature Limits", False, f"Exception: {str(e)}")
        return False

def test_upgrade_subscription():
    """Test POST /api/billing/subscription/upgrade - Tier upgrade"""
    try:
        # Try upgrading to pro
        upgrade_data = {
            "tier": "pro",
            "billing_period": "monthly"
        }
        
        response = session.post(f"{BASE_URL}/billing/subscription/upgrade", json=upgrade_data)
        
        if response.status_code != 200:
            log_test("Upgrade Subscription", False, f"Status: {response.status_code}, Response: {response.text}")
            return False
        
        data = response.json()
        
        # Validate response structure
        required_fields = ["success", "new_tier", "credits_granted"]
        missing_fields = [f for f in required_fields if f not in data]
        
        if missing_fields:
            log_test("Upgrade Subscription", False, f"Missing fields: {missing_fields}")
            return False
        
        if not data.get("success"):
            log_test("Upgrade Subscription", False, f"API returned success=false: {data}")
            return False
        
        if data.get("new_tier") != "pro":
            log_test("Upgrade Subscription", False, f"Expected new_tier 'pro', got {data.get('new_tier')}")
            return False
        
        credits_granted = data.get("credits_granted", 0)
        if credits_granted <= 0:
            log_test("Upgrade Subscription", False, f"Expected credits > 0, got {credits_granted}")
            return False
        
        log_test("Upgrade Subscription", True, f"Upgraded to {data['new_tier']}, Credits granted: {credits_granted}")
        return True
        
    except Exception as e:
        log_test("Upgrade Subscription", False, f"Exception: {str(e)}")
        return False

# ============ VIRAL HOOK PREDICTOR TESTS ============

def test_viral_predict():
    """Test POST /api/viral/predict - Viral hook prediction"""
    try:
        predict_data = {
            "content": "Stop doing this one thing that's killing your productivity. I spent 10 years figuring this out.",
            "platform": "linkedin"
        }
        
        response = session.post(f"{BASE_URL}/viral/predict", json=predict_data)
        
        if response.status_code != 200:
            log_test("Viral Hook Prediction", False, f"Status: {response.status_code}, Response: {response.text}")
            return False
        
        data = response.json()
        
        # Validate response structure
        required_fields = ["success", "virality_score", "virality_level", "pattern_analysis", "improvements"]
        missing_fields = [f for f in required_fields if f not in data]
        
        if missing_fields:
            log_test("Viral Hook Prediction", False, f"Missing fields: {missing_fields}")
            return False
        
        if not data.get("success"):
            log_test("Viral Hook Prediction", False, f"API returned success=false: {data}")
            return False
        
        virality_score = data.get("virality_score", 0)
        if not isinstance(virality_score, int) or virality_score < 0 or virality_score > 100:
            log_test("Viral Hook Prediction", False, f"Invalid virality_score: {virality_score}")
            return False
        
        virality_level = data.get("virality_level", "")
        valid_levels = ["high", "moderate", "low", "poor"]
        if virality_level not in valid_levels:
            log_test("Viral Hook Prediction", False, f"Invalid virality_level: {virality_level}")
            return False
        
        pattern_analysis = data.get("pattern_analysis", {})
        if "hook" not in pattern_analysis or "final_score" not in pattern_analysis:
            log_test("Viral Hook Prediction", False, f"Invalid pattern_analysis structure: {pattern_analysis}")
            return False
        
        log_test("Viral Hook Prediction", True, f"Score: {virality_score}/100, Level: {virality_level}, Improvements: {len(data.get('improvements', []))}")
        return True
        
    except Exception as e:
        log_test("Viral Hook Prediction", False, f"Exception: {str(e)}")
        return False

def test_viral_improve():
    """Test POST /api/viral/improve - Hook improvement"""
    try:
        improve_data = {
            "hook": "Here's my tip for better content",
            "platform": "linkedin",
            "style": "curiosity"
        }
        
        response = session.post(f"{BASE_URL}/viral/improve", json=improve_data)
        
        if response.status_code != 200:
            log_test("Hook Improvement", False, f"Status: {response.status_code}, Response: {response.text}")
            return False
        
        data = response.json()
        
        # Validate response structure
        required_fields = ["success", "improved_hooks"]
        missing_fields = [f for f in required_fields if f not in data]
        
        if missing_fields:
            log_test("Hook Improvement", False, f"Missing fields: {missing_fields}")
            return False
        
        if not data.get("success"):
            log_test("Hook Improvement", False, f"API returned success=false: {data}")
            return False
        
        improved_hooks = data.get("improved_hooks", [])
        if not isinstance(improved_hooks, list) or len(improved_hooks) == 0:
            log_test("Hook Improvement", False, f"Expected non-empty list of improved_hooks, got: {improved_hooks}")
            return False
        
        # Validate hook structure
        for hook in improved_hooks[:3]:  # Check first 3
            if not isinstance(hook, dict) or "text" not in hook:
                log_test("Hook Improvement", False, f"Invalid hook structure: {hook}")
                return False
        
        log_test("Hook Improvement", True, f"Generated {len(improved_hooks)} improved hooks using {data.get('style', 'unknown')} style")
        return True
        
    except Exception as e:
        log_test("Hook Improvement", False, f"Exception: {str(e)}")
        return False

def test_viral_batch_predict():
    """Test POST /api/viral/batch-predict - Batch prediction"""
    try:
        batch_data = {
            "hooks": [
                "Stop doing this mistake in your content strategy",
                "3 content tips that actually work",
                "Here's what I learned after 1000 posts"
            ],
            "platform": "linkedin"
        }
        
        response = session.post(f"{BASE_URL}/viral/batch-predict", json=batch_data)
        
        if response.status_code != 200:
            log_test("Batch Prediction", False, f"Status: {response.status_code}, Response: {response.text}")
            return False
        
        data = response.json()
        
        # Validate response structure
        required_fields = ["success", "predictions", "recommended"]
        missing_fields = [f for f in required_fields if f not in data]
        
        if missing_fields:
            log_test("Batch Prediction", False, f"Missing fields: {missing_fields}")
            return False
        
        if not data.get("success"):
            log_test("Batch Prediction", False, f"API returned success=false: {data}")
            return False
        
        predictions = data.get("predictions", [])
        if len(predictions) != 3:
            log_test("Batch Prediction", False, f"Expected 3 predictions, got {len(predictions)}")
            return False
        
        # Check that hooks are ranked (first should have highest score)
        scores = [p.get("score", 0) for p in predictions]
        if scores != sorted(scores, reverse=True):
            log_test("Batch Prediction", False, f"Hooks not ranked by score: {scores}")
            return False
        
        recommended = data.get("recommended", {})
        if "hook" not in recommended or "score" not in recommended:
            log_test("Batch Prediction", False, f"Invalid recommended structure: {recommended}")
            return False
        
        log_test("Batch Prediction", True, f"Ranked 3 hooks, Best score: {scores[0]}, Recommended: '{recommended['hook'][:40]}...'")
        return True
        
    except Exception as e:
        log_test("Batch Prediction", False, f"Exception: {str(e)}")
        return False

def test_viral_patterns():
    """Test GET /api/viral/patterns - Viral patterns info"""
    try:
        response = session.get(f"{BASE_URL}/viral/patterns")
        
        if response.status_code != 200:
            log_test("Viral Patterns", False, f"Status: {response.status_code}, Response: {response.text}")
            return False
        
        data = response.json()
        
        # Validate response structure
        required_fields = ["positive_patterns", "negative_patterns", "tips"]
        missing_fields = [f for f in required_fields if f not in data]
        
        if missing_fields:
            log_test("Viral Patterns", False, f"Missing fields: {missing_fields}")
            return False
        
        positive_patterns = data.get("positive_patterns", [])
        if not isinstance(positive_patterns, list) or len(positive_patterns) == 0:
            log_test("Viral Patterns", False, f"Expected non-empty positive_patterns list, got: {positive_patterns}")
            return False
        
        negative_patterns = data.get("negative_patterns", [])
        if not isinstance(negative_patterns, list) or len(negative_patterns) == 0:
            log_test("Viral Patterns", False, f"Expected non-empty negative_patterns list, got: {negative_patterns}")
            return False
        
        tips = data.get("tips", [])
        if not isinstance(tips, list) or len(tips) == 0:
            log_test("Viral Patterns", False, f"Expected non-empty tips list, got: {tips}")
            return False
        
        # Validate pattern structure
        for pattern in positive_patterns[:2]:
            if not isinstance(pattern, dict) or "name" not in pattern or "description" not in pattern:
                log_test("Viral Patterns", False, f"Invalid positive pattern structure: {pattern}")
                return False
        
        for pattern in negative_patterns[:2]:
            if not isinstance(pattern, dict) or "name" not in pattern or "reason" not in pattern:
                log_test("Viral Patterns", False, f"Invalid negative pattern structure: {pattern}")
                return False
        
        log_test("Viral Patterns", True, f"Positive: {len(positive_patterns)}, Negative: {len(negative_patterns)}, Tips: {len(tips)}")
        return True
        
    except Exception as e:
        log_test("Viral Patterns", False, f"Exception: {str(e)}")
        return False

def run_all_tests():
    """Run all Sprint 10 backend tests."""
    print("🚀 SPRINT 10 BACKEND TESTING - THOOKAI PLATFORM")
    print("=" * 60)
    print()
    
    # Setup authentication
    try:
        auth_info = register_and_auth()
        print(f"🎯 Testing with user: {auth_info['user']['email']}")
        print()
    except Exception as e:
        print(f"❌ Authentication setup failed: {e}")
        return
    
    # Track test results
    tests = []
    
    print("📊 CREDIT SYSTEM TESTS")
    print("-" * 30)
    tests.append(("Credit Balance Endpoint", test_get_credit_balance()))
    tests.append(("Credit Usage History", test_get_credit_usage()))  
    tests.append(("Operation Costs", test_get_operation_costs()))
    
    print("💳 SUBSCRIPTION TESTS")
    print("-" * 30)
    tests.append(("Subscription Details", test_get_subscription_details()))
    tests.append(("Available Tiers", test_get_available_tiers()))
    tests.append(("Feature Limits", test_get_feature_limits()))
    tests.append(("Upgrade Subscription", test_upgrade_subscription()))
    
    print("🔥 VIRAL HOOK PREDICTOR TESTS")  
    print("-" * 30)
    tests.append(("Viral Hook Prediction", test_viral_predict()))
    tests.append(("Hook Improvement", test_viral_improve()))
    tests.append(("Batch Prediction", test_viral_batch_predict()))
    tests.append(("Viral Patterns", test_viral_patterns()))
    
    # Summary
    print("=" * 60)
    print("🏁 SPRINT 10 TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for name, result in tests if result)
    total = len(tests)
    
    print(f"✅ PASSED: {passed}/{total} tests")
    print(f"❌ FAILED: {total - passed}/{total} tests")
    print()
    
    # Details
    for test_name, result in tests:
        status = "✅" if result else "❌"
        print(f"{status} {test_name}")
    
    print()
    print("🎯 CRITICAL ENDPOINTS STATUS:")
    
    # Group by category
    credit_tests = [(n, r) for n, r in tests[:3]]
    subscription_tests = [(n, r) for n, r in tests[3:7]]
    viral_tests = [(n, r) for n, r in tests[7:]]
    
    credit_pass = sum(1 for _, r in credit_tests if r)
    sub_pass = sum(1 for _, r in subscription_tests if r)  
    viral_pass = sum(1 for _, r in viral_tests if r)
    
    print(f"📊 Credit System: {credit_pass}/{len(credit_tests)} working")
    print(f"💳 Subscription Tiers: {sub_pass}/{len(subscription_tests)} working") 
    print(f"🔥 Viral Hook Predictor: {viral_pass}/{len(viral_tests)} working")
    
    if passed == total:
        print()
        print("🎉 ALL SPRINT 10 FEATURES WORKING CORRECTLY!")
        print("🚀 READY FOR PRODUCTION")
    else:
        print()
        print("⚠️  SOME FEATURES NEED ATTENTION")
        failed_tests = [name for name, result in tests if not result]
        print(f"🔧 Failed: {', '.join(failed_tests)}")

if __name__ == "__main__":
    run_all_tests()