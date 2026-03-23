#!/usr/bin/env python3
"""
Debug the public persona endpoint specifically
"""
import requests
import json
import time

BACKEND_URL = "https://celery-dispatch-fix.preview.emergentagent.com/api"
HEADERS = {"Content-Type": "application/json"}

# Test with existing user from previous test
auth_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyXzZiYzliODczYzNhZiIsImVtYWlsIjoidGVzdF9zcHJpbnQxMV8xNzc0MDA5NjMwQGV4YW1wbGUuY29tIiwiZXhwIjoxNzc0NjE0NDMwfQ.Ug7OTNGIQizW5Sujrd14fMyCsQAcsrEJ5C7qQji0Wnc"

print("🔍 Debugging public persona endpoint...")

# 1. First create a new share link (since we revoked the previous one)
print("Creating new share link...")
share_data = {"expiry_days": 30}
headers_with_auth = HEADERS.copy()
headers_with_auth["Authorization"] = f"Bearer {auth_token}"

try:
    response = requests.post(f"{BACKEND_URL}/persona/share", headers=headers_with_auth, json=share_data, timeout=30)
    print(f"Share creation status: {response.status_code}")
    if response.status_code == 200:
        share_result = response.json()
        share_token = share_result.get("share_token")
        print(f"Share token: {share_token}")
        print(f"Full response: {json.dumps(share_result, indent=2)}")
    else:
        print(f"Error: {response.text}")
        exit(1)
except Exception as e:
    print(f"Exception during share creation: {e}")
    exit(1)

# 2. Test public persona endpoint with detailed debugging
print(f"\nTesting public persona endpoint...")
public_url = f"{BACKEND_URL}/persona/public/{share_token}"
print(f"URL: {public_url}")

try:
    print("Making request to public endpoint...")
    response = requests.get(public_url, timeout=60)  # Increased timeout
    print(f"Response status: {response.status_code}")
    print(f"Response headers: {dict(response.headers)}")
    
    if response.status_code == 200:
        public_data = response.json()
        print("✅ Public persona endpoint working!")
        print(f"Response data keys: {list(public_data.keys())}")
        print(f"Creator: {public_data.get('creator', {})}")
        print(f"View count: {public_data.get('share_info', {}).get('view_count', 'N/A')}")
    else:
        print(f"❌ Error response: {response.text}")
        
except requests.exceptions.Timeout:
    print("❌ Timeout error - endpoint took too long to respond")
except requests.exceptions.ConnectionError:
    print("❌ Connection error - could not connect to endpoint")  
except Exception as e:
    print(f"❌ Unexpected error: {e}")

print("\n🔍 Debug complete")