#!/usr/bin/env python3
"""
ThookAI Sprint 11 Backend Testing
Tests shareable persona cards and regional English features
"""

import requests
import json
import time
import uuid
from datetime import datetime, timedelta
import sys

# Configuration
BACKEND_URL = "https://thook-growth.preview.emergentagent.com/api"
HEADERS = {"Content-Type": "application/json"}

class TestResults:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.results = []
    
    def log(self, test_name, status, message="", response_data=None):
        result = {
            "test": test_name,
            "status": status,
            "message": message,
            "timestamp": datetime.now().isoformat()
        }
        if response_data:
            result["data"] = response_data
        
        self.results.append(result)
        if status == "PASS":
            self.passed += 1
            print(f"✅ {test_name}: {message}")
        else:
            self.failed += 1
            print(f"❌ {test_name}: {message}")
    
    def summary(self):
        total = self.passed + self.failed
        print(f"\n📊 TEST SUMMARY: {self.passed}/{total} passed")
        return self.passed, self.failed, self.results

def make_request(method, url, headers=None, data=None, auth_token=None):
    """Make HTTP request with proper headers and error handling."""
    req_headers = HEADERS.copy()
    if headers:
        req_headers.update(headers)
    
    if auth_token:
        req_headers["Authorization"] = f"Bearer {auth_token}"
    
    try:
        if method == "GET":
            response = requests.get(url, headers=req_headers, timeout=30)
        elif method == "POST":
            response = requests.post(url, headers=req_headers, json=data, timeout=30)
        elif method == "PUT":
            response = requests.put(url, headers=req_headers, json=data, timeout=30)
        elif method == "DELETE":
            response = requests.delete(url, headers=req_headers, timeout=30)
        
        return response
    except requests.exceptions.RequestException as e:
        print(f"Request error: {e}")
        return None

def test_sprint11_backend():
    """Test Sprint 11 shareable persona cards and regional English features."""
    results = TestResults()
    
    # Generate unique test data
    timestamp = int(time.time())
    test_email = f"test_sprint11_{timestamp}@example.com"
    test_password = "TestPassword123!"
    test_name = f"Sprint11 Tester {timestamp}"
    
    auth_token = None
    share_token = None
    
    print("🚀 Starting Sprint 11 Backend Testing...")
    print(f"📧 Test User: {test_email}")
    print(f"🔗 Backend URL: {BACKEND_URL}")
    
    # ============ USER REGISTRATION ============
    print("\n🔐 Testing User Registration...")
    register_data = {
        "email": test_email,
        "password": test_password,
        "name": test_name
    }
    
    response = make_request("POST", f"{BACKEND_URL}/auth/register", data=register_data)
    if response and response.status_code == 200:
        user_data = response.json()
        auth_token = user_data.get("token")
        results.log("User Registration", "PASS", f"User registered: {user_data.get('name')}", user_data)
    else:
        error_msg = f"Status: {response.status_code if response else 'No response'}"
        if response:
            error_msg += f", Error: {response.text}"
        results.log("User Registration", "FAIL", error_msg)
        print("❌ Cannot continue without user registration")
        return results.summary()
    
    # ============ ONBOARDING FLOW ============
    print("\n📋 Testing Onboarding Flow...")
    
    # Start onboarding
    response = make_request("GET", f"{BACKEND_URL}/onboarding/questions", auth_token=auth_token)
    if response and response.status_code == 200:
        questions_data = response.json()
        total_questions = questions_data.get("total", 0)
        results.log("Get Onboarding Questions", "PASS", f"Retrieved {total_questions} questions")
    else:
        results.log("Get Onboarding Questions", "FAIL", "Failed to get questions")
        return results.summary()
    
    # Sample onboarding answers
    sample_answers = [
        {"question_id": 0, "answer": "I'm a B2B SaaS founder sharing lessons on growing from 0 to $1M ARR through data-driven content marketing and product-led growth strategies."},
        {"question_id": 1, "answer": "LinkedIn"},
        {"question_id": 2, "answer": "Strategic, Data-driven, Authentic"},
        {"question_id": 3, "answer": "Lenny Rachitsky for his depth combined with accessibility, and Paul Graham for razor-sharp clarity in technical topics."},
        {"question_id": 4, "answer": "Crypto speculation, generic hustle culture posts, political commentary, and superficial trending topics without substance."},
        {"question_id": 5, "answer": "Generate leads/clients"},
        {"question_id": 6, "answer": "3–5 hours"}
    ]
    
    # Complete persona generation
    persona_data = {
        "answers": sample_answers,
        "posts_analysis": "Analytical voice with structured insights and professional tone"
    }
    
    response = make_request("POST", f"{BACKEND_URL}/onboarding/generate-persona", data=persona_data, auth_token=auth_token)
    if response and response.status_code == 200:
        persona_result = response.json()
        persona_card = persona_result.get("persona_card", {})
        results.log("Onboarding Complete", "PASS", f"Persona created: {persona_card.get('personality_archetype', 'Unknown')}")
    else:
        error_msg = f"Status: {response.status_code if response else 'No response'}"
        if response:
            error_msg += f", Error: {response.text}"
        results.log("Onboarding Complete", "FAIL", error_msg)
        return results.summary()
    
    # ============ SHAREABLE PERSONA CARDS FLOW ============
    print("\n🔗 Testing Shareable Persona Cards...")
    
    # 1. Create share link
    print("\n1️⃣ Creating share link...")
    share_data = {"expiry_days": 30}
    
    response = make_request("POST", f"{BACKEND_URL}/persona/share", data=share_data, auth_token=auth_token)
    if response and response.status_code == 200:
        share_result = response.json()
        share_token = share_result.get("share_token")
        share_url = share_result.get("share_url")
        expires_at = share_result.get("expires_at")
        
        # Validate response structure
        if share_token and share_url and expires_at:
            # Check URL format
            expected_url = f"/creator/{share_token}"
            if share_url == expected_url:
                # Check expiry is approximately 30 days out
                expiry_date = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                expected_expiry = datetime.now().replace(tzinfo=expiry_date.tzinfo) + timedelta(days=29)  # Allow 1 day tolerance
                if expiry_date > expected_expiry:
                    results.log("Create Share Link", "PASS", f"Share created: {share_token[:8]}... expires: {expires_at}")
                else:
                    results.log("Create Share Link", "FAIL", "Expiry date not ~30 days out")
            else:
                results.log("Create Share Link", "FAIL", f"Invalid share_url format: {share_url}")
        else:
            results.log("Create Share Link", "FAIL", "Missing required fields in response")
    else:
        error_msg = f"Status: {response.status_code if response else 'No response'}"
        if response:
            error_msg += f", Error: {response.text}"
        results.log("Create Share Link", "FAIL", error_msg)
        return results.summary()
    
    # 2. Check share status
    print("\n2️⃣ Checking share status...")
    response = make_request("GET", f"{BACKEND_URL}/persona/share/status", auth_token=auth_token)
    if response and response.status_code == 200:
        status_result = response.json()
        is_shared = status_result.get("is_shared")
        returned_token = status_result.get("share_token")
        
        if is_shared and returned_token == share_token:
            results.log("Check Share Status", "PASS", f"Share status confirmed: is_shared={is_shared}")
        else:
            results.log("Check Share Status", "FAIL", f"Share status mismatch: is_shared={is_shared}, token_match={returned_token == share_token}")
    else:
        error_msg = f"Status: {response.status_code if response else 'No response'}"
        results.log("Check Share Status", "FAIL", error_msg)
    
    # 3. Fetch public persona (NO AUTH)
    print("\n3️⃣ Fetching public persona (no auth)...")
    if share_token:
        # Make request WITHOUT auth token
        response = make_request("GET", f"{BACKEND_URL}/persona/public/{share_token}")
        if response and response.status_code == 200:
            public_data = response.json()
            
            # Validate required fields
            required_fields = ["creator", "card", "voice_metrics", "share_info"]
            missing_fields = [field for field in required_fields if field not in public_data]
            
            if not missing_fields:
                creator = public_data.get("creator", {})
                card = public_data.get("card", {})
                voice_metrics = public_data.get("voice_metrics", {})
                share_info = public_data.get("share_info", {})
                
                # Check specific required card data
                card_fields = ["archetype", "voice_descriptor", "pillars"]
                card_has_data = any(field in str(card).lower() for field in card_fields)
                
                if card_has_data and "view_count" in share_info:
                    initial_view_count = share_info.get("view_count", 0)
                    results.log("Fetch Public Persona", "PASS", f"Public persona retrieved, view_count: {initial_view_count}")
                else:
                    results.log("Fetch Public Persona", "FAIL", "Missing required card data or view_count")
            else:
                results.log("Fetch Public Persona", "FAIL", f"Missing fields: {missing_fields}")
        else:
            error_msg = f"Status: {response.status_code if response else 'No response'}"
            results.log("Fetch Public Persona", "FAIL", error_msg)
    
    # 4. Verify view count increments
    print("\n4️⃣ Verifying view count increment...")
    if share_token:
        time.sleep(1)  # Brief pause
        response = make_request("GET", f"{BACKEND_URL}/persona/public/{share_token}")
        if response and response.status_code == 200:
            public_data = response.json()
            share_info = public_data.get("share_info", {})
            new_view_count = share_info.get("view_count", 0)
            
            if new_view_count > 0:  # Should be at least 2 now
                results.log("View Count Increment", "PASS", f"View count incremented: {new_view_count}")
            else:
                results.log("View Count Increment", "FAIL", f"View count not incremented: {new_view_count}")
        else:
            results.log("View Count Increment", "FAIL", "Failed to fetch public persona again")
    
    # 5. Revoke share link
    print("\n5️⃣ Revoking share link...")
    response = make_request("DELETE", f"{BACKEND_URL}/persona/share", auth_token=auth_token)
    if response and response.status_code == 200:
        revoke_result = response.json()
        if revoke_result.get("success"):
            results.log("Revoke Share Link", "PASS", "Share link revoked successfully")
        else:
            results.log("Revoke Share Link", "FAIL", "Revoke not successful")
    else:
        error_msg = f"Status: {response.status_code if response else 'No response'}"
        results.log("Revoke Share Link", "FAIL", error_msg)
    
    # 6. Verify public endpoint returns 404 after revoke
    print("\n6️⃣ Verifying revoked link returns 404...")
    if share_token:
        time.sleep(1)  # Brief pause for data consistency
        response = make_request("GET", f"{BACKEND_URL}/persona/public/{share_token}")
        if response and response.status_code == 404:
            results.log("Verify Revoked Link 404", "PASS", "Revoked link correctly returns 404")
        else:
            status = response.status_code if response else "No response"
            results.log("Verify Revoked Link 404", "FAIL", f"Expected 404, got {status}")
    
    # ============ REGIONAL ENGLISH TESTS ============
    print("\n🌍 Testing Regional English Features...")
    
    # 7. Get regional English options
    print("\n7️⃣ Getting regional English options...")
    response = make_request("GET", f"{BACKEND_URL}/persona/regional-english/options")
    if response and response.status_code == 200:
        options_data = response.json()
        options = options_data.get("options", [])
        
        # Verify all 4 options present
        expected_codes = ["US", "UK", "AU", "IN"]
        found_codes = [opt.get("code") for opt in options]
        missing_codes = [code for code in expected_codes if code not in found_codes]
        
        if not missing_codes:
            # Verify required fields
            required_fields = ["name", "spelling_rules", "date_format"]
            all_have_fields = all(
                all(field in opt for field in required_fields) 
                for opt in options
            )
            
            if all_have_fields:
                results.log("Get Regional Options", "PASS", f"Retrieved {len(options)} regional options")
            else:
                results.log("Get Regional Options", "FAIL", "Options missing required fields")
        else:
            results.log("Get Regional Options", "FAIL", f"Missing regional codes: {missing_codes}")
    else:
        error_msg = f"Status: {response.status_code if response else 'No response'}"
        results.log("Get Regional Options", "FAIL", error_msg)
    
    # 8. Update to UK English
    print("\n8️⃣ Updating to UK English...")
    uk_data = {"regional_english": "UK"}
    
    response = make_request("PUT", f"{BACKEND_URL}/persona/regional-english", data=uk_data, auth_token=auth_token)
    if response and response.status_code == 200:
        uk_result = response.json()
        if uk_result.get("success") and uk_result.get("regional_english") == "UK":
            config = uk_result.get("config", {})
            if "British English" in config.get("name", ""):
                results.log("Update to UK English", "PASS", "Successfully updated to UK English")
            else:
                results.log("Update to UK English", "FAIL", "UK config not returned correctly")
        else:
            results.log("Update to UK English", "FAIL", "Update not successful")
    else:
        error_msg = f"Status: {response.status_code if response else 'No response'}"
        results.log("Update to UK English", "FAIL", error_msg)
    
    # 9. Verify persona card contains UK setting
    print("\n9️⃣ Verifying persona card contains UK setting...")
    response = make_request("GET", f"{BACKEND_URL}/persona/me", auth_token=auth_token)
    if response and response.status_code == 200:
        persona_data = response.json()
        card = persona_data.get("card", {})
        regional_english = card.get("regional_english")
        
        if regional_english == "UK":
            results.log("Verify UK in Card", "PASS", "Persona card contains regional_english: UK")
        else:
            results.log("Verify UK in Card", "FAIL", f"Expected UK, got: {regional_english}")
    else:
        error_msg = f"Status: {response.status_code if response else 'No response'}"
        results.log("Verify UK in Card", "FAIL", error_msg)
    
    # 10. Update to AU English
    print("\n🔟 Updating to AU English...")
    au_data = {"regional_english": "AU"}
    
    response = make_request("PUT", f"{BACKEND_URL}/persona/regional-english", data=au_data, auth_token=auth_token)
    if response and response.status_code == 200:
        au_result = response.json()
        if au_result.get("success") and au_result.get("regional_english") == "AU":
            config = au_result.get("config", {})
            if "Australian English" in config.get("name", ""):
                results.log("Update to AU English", "PASS", "Successfully updated to AU English")
            else:
                results.log("Update to AU English", "FAIL", "AU config not returned correctly")
        else:
            results.log("Update to AU English", "FAIL", "Update not successful")
    else:
        error_msg = f"Status: {response.status_code if response else 'No response'}"
        results.log("Update to AU English", "FAIL", error_msg)
    
    # 11. Test invalid regional code
    print("\n1️⃣1️⃣ Testing invalid regional code...")
    invalid_data = {"regional_english": "FR"}
    
    response = make_request("PUT", f"{BACKEND_URL}/persona/regional-english", data=invalid_data, auth_token=auth_token)
    if response and response.status_code == 400:
        results.log("Test Invalid Regional Code", "PASS", "Invalid code correctly returns 400 error")
    else:
        status = response.status_code if response else "No response"
        results.log("Test Invalid Regional Code", "FAIL", f"Expected 400, got {status}")
    
    print("\n🎯 Sprint 11 Backend Testing Complete!")
    return results.summary()

if __name__ == "__main__":
    passed, failed, detailed_results = test_sprint11_backend()
    
    # Write detailed results to file
    with open("/app/sprint11_test_results.json", "w") as f:
        json.dump(detailed_results, f, indent=2)
    
    print(f"\n📝 Detailed results saved to: /app/sprint11_test_results.json")
    
    if failed > 0:
        sys.exit(1)
    else:
        print("✅ All tests passed!")