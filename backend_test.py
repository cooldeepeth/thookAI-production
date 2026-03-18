#!/usr/bin/env python3
"""Backend Testing Suite for ThookAI Sprint 9 Analytics Features

Tests all analytics endpoints including:
- Analytics overview  
- Performance trends
- AI insights generation
- Pattern Fatigue Shield
- Learning insights
- Persona evolution
- Voice evolution analysis
- Persona suggestions

Requires: python3 -m pip install requests python-dotenv
"""

import sys
import json
import time
import requests
from datetime import datetime, timezone, timedelta
import uuid
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv("/app/frontend/.env")

# Configuration - Use external URL from frontend .env
BASE_URL = os.getenv('REACT_APP_BACKEND_URL', 'https://social-scheduler-87.preview.emergentagent.com')
API_BASE = f"{BASE_URL}/api"

# Test configuration
TIMEOUT = 90  # Increased timeout for content generation
TEST_USER_EMAIL = f"test_analytics_{int(time.time())}@example.com"
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
        print(f"\n🎯 SPRINT 9 ANALYTICS BACKEND TEST SUMMARY")
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

def register_test_user():
    """Register a new test user and return auth token"""
    print(f"\n🔐 Registering test user: {TEST_USER_EMAIL}")
    
    # Register user
    register_data = {
        "name": "Test Analytics User", 
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
    
    results.log_test("User Authentication Setup", True, f"Token obtained for {TEST_USER_EMAIL}")
    return token

def complete_onboarding(token):
    """Complete onboarding to create persona using new interview system"""
    print("\n📝 Completing onboarding to create persona")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Use the new onboarding system with interview questions
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
        results.log_test("Persona Generation", False, f"Persona generation failed: {response.status_code if response else 'No response'}")
        return False
    
    try:
        data = response.json()
        if data.get("persona_card"):
            results.log_test("Onboarding Process", True, "Persona created successfully")
            return True
        else:
            results.log_test("Persona Generation", False, "No persona card in response")
            return False
    except:
        results.log_test("Persona Generation", False, "Invalid JSON response")
        return False

def create_test_content(token):
    """Create and approve test content for analytics"""
    print("\n📄 Creating test content for analytics data")
    
    headers = {"Authorization": f"Bearer {token}"}
    content_jobs = []
    
    # Create 3 pieces of content
    test_topics = [
        "5 productivity tips for remote workers",
        "How to build a personal brand on LinkedIn", 
        "The future of AI in marketing"
    ]
    
    for i, topic in enumerate(test_topics):
        content_data = {
            "platform": "linkedin",
            "content_type": "post",
            "raw_input": topic
        }
        
        # Create content
        response = safe_request("POST", f"{API_BASE}/content/create", json=content_data, headers=headers)
        if not response or response.status_code != 200:
            results.log_test(f"Content Creation {i+1}", False, f"Failed: {response.status_code if response else 'No response'}")
            continue
        
        data = response.json()
        job_id = data.get("job_id")
        if not job_id:
            results.log_test(f"Content Creation {i+1}", False, "No job_id returned")
            continue
        
        # Poll until reviewing (max 90 seconds)
        for attempt in range(18):  # 18 * 5 = 90 seconds
            time.sleep(5)
            response = safe_request("GET", f"{API_BASE}/content/job/{job_id}", headers=headers)
            if response and response.status_code == 200:
                job_data = response.json()
                if job_data.get("status") == "reviewing":
                    break
                elif job_data.get("status") == "failed":
                    results.log_test(f"Content Generation {i+1}", False, f"Content generation failed")
                    break
        else:
            results.log_test(f"Content Generation {i+1}", False, f"Timeout waiting for content to reach reviewing status")
            continue
        
        # Approve content
        response = safe_request("POST", f"{API_BASE}/content/approve/{job_id}", headers=headers)
        if response and response.status_code == 200:
            content_jobs.append(job_id)
            results.log_test(f"Content Approval {i+1}", True, f"Job {job_id} approved")
        else:
            results.log_test(f"Content Approval {i+1}", False, f"Approval failed: {response.status_code if response else 'No response'}")
    
    print(f"Created and approved {len(content_jobs)} content pieces")
    return content_jobs

def test_analytics_overview(token):
    """Test GET /api/analytics/overview"""
    print("\n📊 Testing Analytics Overview")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Test with default parameters (30 days)
    response = safe_request("GET", f"{API_BASE}/analytics/overview", headers=headers)
    if not response:
        results.log_test("Analytics Overview - Request", False, "No response received")
        return False
    
    if response.status_code != 200:
        results.log_test("Analytics Overview - Status", False, f"Status: {response.status_code}")
        return False
    
    try:
        data = response.json()
    except:
        results.log_test("Analytics Overview - JSON", False, "Invalid JSON response")
        return False
    
    # Validate structure
    required_fields = ["success", "has_data"]
    for field in required_fields:
        if field not in data:
            results.log_test("Analytics Overview - Structure", False, f"Missing {field}")
            return False
    
    if data.get("has_data"):
        # If has_data=true, check for summary and by_platform
        if "summary" not in data or "by_platform" not in data:
            results.log_test("Analytics Overview - Data Fields", False, "Missing summary or by_platform")
            return False
        
        # Check summary structure
        summary = data.get("summary", {})
        summary_fields = ["total_posts", "total_impressions", "total_engagements"]
        for field in summary_fields:
            if field not in summary:
                results.log_test("Analytics Overview - Summary", False, f"Missing {field} in summary")
                return False
        
        results.log_test("Analytics Overview", True, f"Data available: {summary.get('total_posts', 0)} posts analyzed")
    else:
        results.log_test("Analytics Overview", True, "No data available (expected for new user)")
    
    return True

def test_performance_trends(token):
    """Test GET /api/analytics/trends"""
    print("\n📈 Testing Performance Trends")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Test with parameters
    params = {"days": 30, "granularity": "week"}
    response = safe_request("GET", f"{API_BASE}/analytics/trends", headers=headers, params=params)
    
    if not response:
        results.log_test("Performance Trends - Request", False, "No response received")
        return False
    
    if response.status_code != 200:
        results.log_test("Performance Trends - Status", False, f"Status: {response.status_code}")
        return False
    
    try:
        data = response.json()
    except:
        results.log_test("Performance Trends - JSON", False, "Invalid JSON response")
        return False
    
    # Validate structure - handle both cases with and without data
    required_fields = ["success", "has_data"]
    for field in required_fields:
        if field not in data:
            results.log_test("Performance Trends - Structure", False, f"Missing {field}")
            return False
    
    # Check trend field - only required when has_data=true
    if data.get("has_data"):
        if "trend" not in data:
            results.log_test("Performance Trends - Trend Missing", False, "Missing trend field when has_data=true")
            return False
        
        trend_value = data.get("trend")
        valid_trends = ["improving", "stable", "declining", "insufficient_data"]
        if trend_value not in valid_trends:
            results.log_test("Performance Trends - Trend Value", False, f"Invalid trend: {trend_value}")
            return False
        
        if "periods" not in data:
            results.log_test("Performance Trends - Periods", False, "Missing periods array")
            return False
        
        results.log_test("Performance Trends", True, f"Trend: {trend_value}, {len(data.get('periods', []))} periods")
    else:
        # No data case
        results.log_test("Performance Trends", True, "No data available (expected for new user)")
    
    return True

def test_ai_insights(token):
    """Test GET /api/analytics/insights"""
    print("\n🧠 Testing AI Insights Generation")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    response = safe_request("GET", f"{API_BASE}/analytics/insights", headers=headers)
    
    if not response:
        results.log_test("AI Insights - Request", False, "No response received")
        return False
    
    if response.status_code != 200:
        results.log_test("AI Insights - Status", False, f"Status: {response.status_code}")
        return False
    
    try:
        data = response.json()
    except:
        results.log_test("AI Insights - JSON", False, "Invalid JSON response")
        return False
    
    # Validate structure
    required_fields = ["success", "has_insights"]
    for field in required_fields:
        if field not in data:
            results.log_test("AI Insights - Structure", False, f"Missing {field}")
            return False
    
    if data.get("has_insights"):
        # Check for insights fields
        insights_fields = ["summary", "key_insights", "recommendations"]
        for field in insights_fields:
            if field not in data:
                results.log_test("AI Insights - Content", False, f"Missing {field}")
                return False
        
        results.log_test("AI Insights", True, f"Generated insights with {len(data.get('key_insights', []))} insights")
    else:
        results.log_test("AI Insights", True, "No insights available (expected for limited content)")
    
    return True

def test_fatigue_shield(token):
    """Test GET /api/analytics/fatigue-shield"""
    print("\n🛡️ Testing Pattern Fatigue Shield")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    response = safe_request("GET", f"{API_BASE}/analytics/fatigue-shield", headers=headers)
    
    if not response:
        results.log_test("Fatigue Shield - Request", False, "No response received")
        return False
    
    if response.status_code != 200:
        results.log_test("Fatigue Shield - Status", False, f"Status: {response.status_code}")
        return False
    
    try:
        data = response.json()
    except:
        results.log_test("Fatigue Shield - JSON", False, "Invalid JSON response")
        return False
    
    # Validate structure
    required_fields = ["success", "shield_status", "shield_message", "fatigue_risk_score"]
    for field in required_fields:
        if field not in data:
            results.log_test("Fatigue Shield - Structure", False, f"Missing {field}")
            return False
    
    # Check valid shield status
    shield_status = data.get("shield_status")
    valid_statuses = ["healthy", "caution", "warning", "critical"]
    if shield_status not in valid_statuses:
        results.log_test("Fatigue Shield - Status Value", False, f"Invalid shield status: {shield_status}")
        return False
    
    # Check risk score range
    risk_score = data.get("fatigue_risk_score")
    if not isinstance(risk_score, (int, float)) or risk_score < 0 or risk_score > 100:
        results.log_test("Fatigue Shield - Risk Score", False, f"Invalid risk score: {risk_score}")
        return False
    
    results.log_test("Fatigue Shield", True, f"Status: {shield_status}, Risk: {risk_score}/100")
    return True

def test_learning_insights(token):
    """Test GET /api/analytics/learning"""
    print("\n📚 Testing Learning Insights")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    response = safe_request("GET", f"{API_BASE}/analytics/learning", headers=headers)
    
    if not response:
        results.log_test("Learning Insights - Request", False, "No response received")
        return False
    
    if response.status_code != 200:
        results.log_test("Learning Insights - Status", False, f"Status: {response.status_code}")
        return False
    
    try:
        data = response.json()
    except:
        results.log_test("Learning Insights - JSON", False, "Invalid JSON response")
        return False
    
    # Validate structure
    if "has_data" not in data:
        results.log_test("Learning Insights - Structure", False, "Missing has_data field")
        return False
    
    if data.get("has_data"):
        # Check for learning data fields
        learning_fields = ["approved_count", "rejected_count"]
        for field in learning_fields:
            if field not in data:
                results.log_test("Learning Insights - Data", False, f"Missing {field}")
                return False
        
        approved = data.get("approved_count", 0)
        rejected = data.get("rejected_count", 0)
        results.log_test("Learning Insights", True, f"Approved: {approved}, Rejected: {rejected}")
    else:
        results.log_test("Learning Insights", True, "No learning data yet (expected for new user)")
    
    return True

def test_persona_evolution(token):
    """Test GET /api/analytics/persona/evolution"""
    print("\n🧬 Testing Persona Evolution Timeline")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    response = safe_request("GET", f"{API_BASE}/analytics/persona/evolution", headers=headers)
    
    if not response:
        results.log_test("Persona Evolution - Request", False, "No response received")
        return False
    
    if response.status_code != 200:
        results.log_test("Persona Evolution - Status", False, f"Status: {response.status_code}")
        return False
    
    try:
        data = response.json()
    except:
        results.log_test("Persona Evolution - JSON", False, "Invalid JSON response")
        return False
    
    # Validate structure
    required_fields = ["success", "current_card_summary", "timeline", "total_refinements"]
    for field in required_fields:
        if field not in data:
            results.log_test("Persona Evolution - Structure", False, f"Missing {field}")
            return False
    
    timeline = data.get("timeline", [])
    refinements = data.get("total_refinements", 0)
    results.log_test("Persona Evolution", True, f"Timeline has {len(timeline)} events, {refinements} refinements")
    return True

def test_voice_evolution(token):
    """Test GET /api/analytics/persona/voice-evolution"""
    print("\n🎙️ Testing Voice Evolution Analysis")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    response = safe_request("GET", f"{API_BASE}/analytics/persona/voice-evolution", headers=headers)
    
    if not response:
        results.log_test("Voice Evolution - Request", False, "No response received")
        return False
    
    if response.status_code != 200:
        results.log_test("Voice Evolution - Status", False, f"Status: {response.status_code}")
        return False
    
    try:
        data = response.json()
    except:
        results.log_test("Voice Evolution - JSON", False, "Invalid JSON response")
        return False
    
    # Validate structure
    if "has_data" not in data:
        results.log_test("Voice Evolution - Structure", False, "Missing has_data field")
        return False
    
    if data.get("has_data"):
        # Check for analysis fields
        analysis_fields = ["evolution_detected", "evolution_summary"]
        for field in analysis_fields:
            if field not in data:
                results.log_test("Voice Evolution - Analysis", False, f"Missing {field}")
                return False
        
        evolution_detected = data.get("evolution_detected", False)
        total_posts = data.get("total_posts_analyzed", 0)
        results.log_test("Voice Evolution", True, f"Analyzed {total_posts} posts, evolution detected: {evolution_detected}")
    else:
        results.log_test("Voice Evolution", True, "Insufficient data for voice evolution analysis")
    
    return True

def test_persona_suggestions(token):
    """Test GET /api/analytics/persona/suggestions"""
    print("\n💡 Testing Persona Update Suggestions")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    response = safe_request("GET", f"{API_BASE}/analytics/persona/suggestions", headers=headers)
    
    if not response:
        results.log_test("Persona Suggestions - Request", False, "No response received")
        return False
    
    if response.status_code != 200:
        results.log_test("Persona Suggestions - Status", False, f"Status: {response.status_code}")
        return False
    
    try:
        data = response.json()
    except:
        results.log_test("Persona Suggestions - JSON", False, "Invalid JSON response")
        return False
    
    # Validate structure
    required_fields = ["success", "should_update"]
    for field in required_fields:
        if field not in data:
            results.log_test("Persona Suggestions - Structure", False, f"Missing {field}")
            return False
    
    should_update = data.get("should_update", False)
    suggested_updates = data.get("suggested_updates", [])
    confidence = data.get("confidence", 0)
    
    results.log_test("Persona Suggestions", True, f"Should update: {should_update}, Suggestions: {len(suggested_updates)}, Confidence: {confidence}%")
    return True

def main():
    """Run all Sprint 9 analytics backend tests"""
    print("🚀 THOOKAI SPRINT 9 ANALYTICS BACKEND TESTS")
    print(f"Target: {API_BASE}")
    print("=" * 60)
    
    # Step 1: Register test user and get token
    token = register_test_user()
    if not token:
        print("\n❌ Cannot proceed without authentication")
        return False
    
    # Step 2: Complete onboarding
    if not complete_onboarding(token):
        print("\n❌ Cannot proceed without persona")
        return False
    
    # Step 3: Create test content
    content_jobs = create_test_content(token)
    print(f"\nCreated {len(content_jobs)} content pieces for testing")
    
    # Small delay to let content settle
    time.sleep(2)
    
    # Step 4: Test all analytics endpoints
    print("\n" + "=" * 60)
    print("🧪 RUNNING ANALYTICS ENDPOINT TESTS")
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
        print("🎉 ALL TESTS PASSED! Sprint 9 Analytics Backend is working correctly.")
    else:
        print("⚠️ Some tests failed. Check the results above.")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)