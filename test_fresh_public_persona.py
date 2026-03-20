#!/usr/bin/env python3
"""
Test with a completely fresh user to verify public persona endpoint
"""
import requests
import json
import time
import uuid

BACKEND_URL = "https://thook-growth.preview.emergentagent.com/api"
HEADERS = {"Content-Type": "application/json"}

def test_fresh_user_public_persona():
    """Test public persona with a fresh user to avoid cached share issues."""
    
    # Generate unique test data
    timestamp = int(time.time())
    test_email = f"fresh_test_{timestamp}@example.com"
    test_password = "TestPassword123!"
    test_name = f"Fresh User {timestamp}"
    
    print(f"🆕 Testing with fresh user: {test_email}")
    
    # 1. Register new user
    register_data = {
        "email": test_email,
        "password": test_password,
        "name": test_name
    }
    
    response = requests.post(f"{BACKEND_URL}/auth/register", headers=HEADERS, json=register_data, timeout=30)
    if response.status_code != 200:
        print(f"❌ Registration failed: {response.status_code} - {response.text}")
        return
    
    user_data = response.json()
    auth_token = user_data.get("token")
    print(f"✅ User registered: {user_data.get('name')}")
    
    # 2. Complete onboarding
    sample_answers = [
        {"question_id": 0, "answer": "I'm a startup founder sharing product development insights."},
        {"question_id": 1, "answer": "LinkedIn"},
        {"question_id": 2, "answer": "Direct, Strategic, Technical"},
        {"question_id": 3, "answer": "Paul Graham for clear technical writing."},
        {"question_id": 4, "answer": "Generic motivational content."},
        {"question_id": 5, "answer": "Build personal brand"},
        {"question_id": 6, "answer": "3–5 hours"}
    ]
    
    persona_data = {
        "answers": sample_answers,
        "posts_analysis": "Technical voice with practical insights"
    }
    
    headers_with_auth = HEADERS.copy()
    headers_with_auth["Authorization"] = f"Bearer {auth_token}"
    
    response = requests.post(f"{BACKEND_URL}/onboarding/generate-persona", headers=headers_with_auth, json=persona_data, timeout=30)
    if response.status_code != 200:
        print(f"❌ Onboarding failed: {response.status_code} - {response.text}")
        return
    
    persona_result = response.json()
    print(f"✅ Persona created: {persona_result.get('persona_card', {}).get('personality_archetype', 'Unknown')}")
    
    # 3. Create share link
    share_data = {"expiry_days": 30}
    response = requests.post(f"{BACKEND_URL}/persona/share", headers=headers_with_auth, json=share_data, timeout=30)
    if response.status_code != 200:
        print(f"❌ Share creation failed: {response.status_code} - {response.text}")
        return
    
    share_result = response.json()
    share_token = share_result.get("share_token")
    print(f"✅ Share created: {share_token[:8]}...")
    
    # 4. Test public persona endpoint
    public_url = f"{BACKEND_URL}/persona/public/{share_token}"
    print(f"🔍 Testing public URL: {public_url}")
    
    response = requests.get(public_url, timeout=60)
    print(f"📊 Response status: {response.status_code}")
    
    if response.status_code == 200:
        public_data = response.json()
        print("✅ Public persona endpoint working!")
        
        # Validate response structure
        required_fields = ["creator", "card", "voice_metrics", "share_info"]
        missing_fields = [field for field in required_fields if field not in public_data]
        
        if not missing_fields:
            view_count = public_data.get("share_info", {}).get("view_count", 0)
            creator_name = public_data.get("creator", {}).get("name", "Unknown")
            card_archetype = public_data.get("card", {}).get("personality_archetype", "Unknown")
            
            print(f"  📋 Creator: {creator_name}")
            print(f"  🎭 Archetype: {card_archetype}")
            print(f"  👀 View count: {view_count}")
            print(f"  🔑 Response keys: {list(public_data.keys())}")
        else:
            print(f"❌ Missing required fields: {missing_fields}")
    
    elif response.status_code == 404:
        print(f"❌ Share token not found: {response.text}")
    else:
        print(f"❌ Unexpected error: {response.status_code} - {response.text}")

if __name__ == "__main__":
    test_fresh_user_public_persona()