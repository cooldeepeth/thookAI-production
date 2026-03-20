#!/usr/bin/env python3
"""Focused Sprint 9 Analytics Backend Tests

Tests the 8 Sprint 9 analytics endpoints without requiring content creation:
- Analytics overview
- Performance trends  
- AI insights generation
- Pattern Fatigue Shield
- Learning insights
- Persona evolution
- Voice evolution analysis
- Persona suggestions
"""

import sys
import json
import requests
import time
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv("/app/frontend/.env")

# Configuration - Use external URL from frontend .env
BASE_URL = os.getenv('REACT_APP_BACKEND_URL', 'https://thook-growth.preview.emergentagent.com')
API_BASE = f"{BASE_URL}/api"

# Test configuration
TIMEOUT = 30
TEST_USER_EMAIL = f"test_analytics_focused_{int(time.time())}@example.com"
TEST_PASSWORD = "TestPassword123!"

class TestResults:
    """Track test results"""
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.results = []
    
    def log_test(self, name, success, details=""):
        """Log a test result"""
        self.results.append({
            "test": name, 
            "status": "PASS" if success else "FAIL",
            "details": details
        })
        if success:
            self.passed += 1
            print(f"✅ {name}")
        else:
            self.failed += 1
            print(f"❌ {name}: {details}")
    
    def summary(self):
        """Print final summary"""
        total = self.passed + self.failed
        print(f"\n🎯 SPRINT 9 ANALYTICS FOCUSED TEST SUMMARY")
        print(f"Total Tests: {total}")
        print(f"✅ Passed: {self.passed}")
        print(f"❌ Failed: {self.failed}")
        print(f"Success Rate: {(self.passed/total*100):.1f}%" if total > 0 else "No tests run")
        return self.failed == 0

# Global test results tracker
results = TestResults()

def safe_request(method, url, **kwargs):
    """Make HTTP request with timeout and error handling"""
    try:
        kwargs.setdefault('timeout', TIMEOUT)
        response = requests.request(method, url, **kwargs)
        return response
    except requests.exceptions.Timeout:
        print(f"⚠️ Request timeout for {method} {url}")
        return None
    except Exception as e:
        print(f"⚠️ Request error for {method} {url}: {e}")
        return None

def setup_test_user():
    """Register user, create persona, return auth token"""
    print(f"\n🔐 Setting up test user: {TEST_USER_EMAIL}")
    
    # Register user
    register_data = {
        "name": "Analytics Test User", 
        "email": TEST_USER_EMAIL,
        "password": TEST_PASSWORD
    }
    
    response = safe_request("POST", f"{API_BASE}/auth/register", json=register_data)
    if not response or response.status_code != 200:
        results.log_test("User Registration", False, f"Registration failed: {response.status_code if response else 'No response'}")
        return None
    
    # Login to get token
    login_data = {"email": TEST_USER_EMAIL, "password": TEST_PASSWORD}
    response = safe_request("POST", f"{API_BASE}/auth/login", json=login_data)
    
    if not response or response.status_code != 200:
        results.log_test("User Login", False, f"Login failed: {response.status_code if response else 'No response'}")
        return None
    
    data = response.json()
    token = data.get("token")
    
    if not token:
        results.log_test("User Authentication", False, "No token in response")
        return None
    
    # Create persona using interview system
    headers = {"Authorization": f"Bearer {token}"}
    answers = [
        {"question_id": 0, "answer": "I'm a digital marketing strategist helping SaaS companies grow through data-driven content strategies and thought leadership."},
        {"question_id": 1, "answer": "LinkedIn"},
        {"question_id": 2, "answer": "Strategic, Analytical, Actionable"},
        {"question_id": 3, "answer": "Lenny Rachitsky for depth and accessibility in product strategy content. Clear explanations with real examples."},
        {"question_id": 4, "answer": "Crypto speculation, hustle culture, generic motivational quotes"},
        {"question_id": 5, "answer": "Generate leads/clients"},
        {"question_id": 6, "answer": "3-5 hours"}
    ]
    
    # Generate persona directly
    persona_data = {"answers": answers}
    response = safe_request("POST", f"{API_BASE}/onboarding/generate-persona", json=persona_data, headers=headers)
    
    if not response or response.status_code != 200:
        results.log_test("Persona Creation", False, f"Persona generation failed: {response.status_code if response else 'No response'}")
        return None
    
    try:
        data = response.json()
        if data.get("persona_card"):
            results.log_test("Test User Setup", True, "User created with persona")
            return token
        else:
            results.log_test("Persona Creation", False, "No persona card in response")
            return None
    except:
        results.log_test("Persona Creation", False, "Invalid JSON response")
        return None

def test_analytics_overview(token):
    """Test GET /api/analytics/overview"""
    print("\n📊 Testing Analytics Overview")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Test with default parameters (30 days)
    response = safe_request("GET", f"{API_BASE}/analytics/overview", headers=headers)
    if not response:
        results.log_test("Analytics Overview", False, "No response received")
        return False
    
    if response.status_code != 200:
        results.log_test("Analytics Overview", False, f"Status: {response.status_code}")
        return False
    
    try:
        data = response.json()
    except:
        results.log_test("Analytics Overview", False, "Invalid JSON response")
        return False
    
    # Validate structure
    required_fields = ["success", "has_data"]
    for field in required_fields:
        if field not in data:
            results.log_test("Analytics Overview", False, f"Missing {field}")
            return False
    
    if data.get("has_data"):
        # If has_data=true, check for summary and by_platform
        if "summary" not in data or "by_platform" not in data:
            results.log_test("Analytics Overview", False, "Missing summary or by_platform")
            return False
    
    results.log_test("Analytics Overview", True, f"Returned has_data={data.get('has_data')}")
    return True

def test_performance_trends(token):
    """Test GET /api/analytics/trends"""
    print("\n📈 Testing Performance Trends")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Test with parameters
    params = {"days": 30, "granularity": "week"}
    response = safe_request("GET", f"{API_BASE}/analytics/trends", headers=headers, params=params)
    
    if not response:
        results.log_test("Performance Trends", False, "No response received")
        return False
    
    if response.status_code != 200:
        results.log_test("Performance Trends", False, f"Status: {response.status_code}")
        return False
    
    try:
        data = response.json()
    except:
        results.log_test("Performance Trends", False, "Invalid JSON response")
        return False
    
    # Validate structure
    required_fields = ["success", "has_data"]
    for field in required_fields:
        if field not in data:
            results.log_test("Performance Trends", False, f"Missing {field}")
            return False
    
    results.log_test("Performance Trends", True, f"Returned has_data={data.get('has_data')}")
    return True

def test_ai_insights(token):
    """Test GET /api/analytics/insights"""
    print("\n🧠 Testing AI Insights Generation")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    response = safe_request("GET", f"{API_BASE}/analytics/insights", headers=headers)
    
    if not response:
        results.log_test("AI Insights", False, "No response received")
        return False
    
    if response.status_code != 200:
        results.log_test("AI Insights", False, f"Status: {response.status_code}")
        return False
    
    try:
        data = response.json()
    except:
        results.log_test("AI Insights", False, "Invalid JSON response")
        return False
    
    # Validate structure
    required_fields = ["success", "has_insights"]
    for field in required_fields:
        if field not in data:
            results.log_test("AI Insights", False, f"Missing {field}")
            return False
    
    results.log_test("AI Insights", True, f"Returned has_insights={data.get('has_insights')}")
    return True

def test_fatigue_shield(token):
    """Test GET /api/analytics/fatigue-shield"""
    print("\n🛡️ Testing Pattern Fatigue Shield")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    response = safe_request("GET", f"{API_BASE}/analytics/fatigue-shield", headers=headers)
    
    if not response:
        results.log_test("Fatigue Shield", False, "No response received")
        return False
    
    if response.status_code != 200:
        results.log_test("Fatigue Shield", False, f"Status: {response.status_code}")
        return False
    
    try:
        data = response.json()
    except:
        results.log_test("Fatigue Shield", False, "Invalid JSON response")
        return False
    
    # Validate structure
    required_fields = ["success", "shield_status", "shield_message", "fatigue_risk_score"]
    for field in required_fields:
        if field not in data:
            results.log_test("Fatigue Shield", False, f"Missing {field}")
            return False
    
    # Check valid shield status
    shield_status = data.get("shield_status")
    valid_statuses = ["healthy", "caution", "warning", "critical"]
    if shield_status not in valid_statuses:
        results.log_test("Fatigue Shield", False, f"Invalid shield status: {shield_status}")
        return False
    
    results.log_test("Fatigue Shield", True, f"Status: {shield_status}, Risk: {data.get('fatigue_risk_score')}/100")
    return True

def test_learning_insights(token):
    """Test GET /api/analytics/learning"""
    print("\n📚 Testing Learning Insights")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    response = safe_request("GET", f"{API_BASE}/analytics/learning", headers=headers)
    
    if not response:
        results.log_test("Learning Insights", False, "No response received")
        return False
    
    if response.status_code != 200:
        results.log_test("Learning Insights", False, f"Status: {response.status_code}")
        return False
    
    try:
        data = response.json()
    except:
        results.log_test("Learning Insights", False, "Invalid JSON response")
        return False
    
    # Validate structure
    if "has_data" not in data:
        results.log_test("Learning Insights", False, "Missing has_data field")
        return False
    
    results.log_test("Learning Insights", True, f"Returned has_data={data.get('has_data')}")
    return True

def test_persona_evolution(token):
    """Test GET /api/analytics/persona/evolution"""
    print("\n🧬 Testing Persona Evolution Timeline")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    response = safe_request("GET", f"{API_BASE}/analytics/persona/evolution", headers=headers)
    
    if not response:
        results.log_test("Persona Evolution", False, "No response received")
        return False
    
    if response.status_code != 200:
        results.log_test("Persona Evolution", False, f"Status: {response.status_code}")
        return False
    
    try:
        data = response.json()
    except:
        results.log_test("Persona Evolution", False, "Invalid JSON response")
        return False
    
    # Validate structure
    required_fields = ["success", "current_card_summary", "timeline", "total_refinements"]
    for field in required_fields:
        if field not in data:
            results.log_test("Persona Evolution", False, f"Missing {field}")
            return False
    
    timeline = data.get("timeline", [])
    refinements = data.get("total_refinements", 0)
    results.log_test("Persona Evolution", True, f"Timeline: {len(timeline)} events, Refinements: {refinements}")
    return True

def test_voice_evolution(token):
    """Test GET /api/analytics/persona/voice-evolution"""
    print("\n🎙️ Testing Voice Evolution Analysis")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    response = safe_request("GET", f"{API_BASE}/analytics/persona/voice-evolution", headers=headers)
    
    if not response:
        results.log_test("Voice Evolution", False, "No response received")
        return False
    
    if response.status_code != 200:
        results.log_test("Voice Evolution", False, f"Status: {response.status_code}")
        return False
    
    try:
        data = response.json()
    except:
        results.log_test("Voice Evolution", False, "Invalid JSON response")
        return False
    
    # Validate structure
    if "has_data" not in data:
        results.log_test("Voice Evolution", False, "Missing has_data field")
        return False
    
    results.log_test("Voice Evolution", True, f"Returned has_data={data.get('has_data')}")
    return True

def test_persona_suggestions(token):
    """Test GET /api/analytics/persona/suggestions"""
    print("\n💡 Testing Persona Update Suggestions")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    response = safe_request("GET", f"{API_BASE}/analytics/persona/suggestions", headers=headers)
    
    if not response:
        results.log_test("Persona Suggestions", False, "No response received")
        return False
    
    if response.status_code != 200:
        results.log_test("Persona Suggestions", False, f"Status: {response.status_code}")
        return False
    
    try:
        data = response.json()
    except:
        results.log_test("Persona Suggestions", False, "Invalid JSON response")
        return False
    
    # Validate structure
    required_fields = ["success", "should_update"]
    for field in required_fields:
        if field not in data:
            results.log_test("Persona Suggestions", False, f"Missing {field}")
            return False
    
    should_update = data.get("should_update", False)
    confidence = data.get("confidence", 0)
    results.log_test("Persona Suggestions", True, f"Should update: {should_update}, Confidence: {confidence}%")
    return True

def main():
    """Run all Sprint 9 analytics backend tests"""
    print("🚀 THOOKAI SPRINT 9 ANALYTICS FOCUSED BACKEND TESTS")
    print(f"Target: {API_BASE}")
    print("=" * 60)
    
    # Step 1: Setup test user with persona
    token = setup_test_user()
    if not token:
        print("\n❌ Cannot proceed without authentication and persona")
        return False
    
    # Step 2: Test all 8 analytics endpoints
    print("\n" + "=" * 60)
    print("🧪 RUNNING SPRINT 9 ANALYTICS ENDPOINT TESTS")
    print("=" * 60)
    
    test_analytics_overview(token)
    test_performance_trends(token)
    test_ai_insights(token)
    test_fatigue_shield(token)
    test_learning_insights(token)
    test_persona_evolution(token) 
    test_voice_evolution(token)
    test_persona_suggestions(token)
    
    # Final results
    print("\n" + "=" * 60)
    success = results.summary()
    print("=" * 60)
    
    if success:
        print("🎉 ALL ANALYTICS ENDPOINTS WORKING! Sprint 9 Analytics Backend is ready.")
        print("\nNOTE: Endpoints return 'no data' states as expected for new users.")
        print("In production, these will populate as users create and approve content.")
    else:
        print("⚠️ Some tests failed. Check the results above.")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)