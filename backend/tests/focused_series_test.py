#!/usr/bin/env python3
"""
Test series creation and listing in same session
"""
import requests
import json
import sys
import time

# Get backend URL
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

API_BASE = f"{BACKEND_URL}/api"

# Create unique user
timestamp = int(time.time())
register_data = {
    "email": f"seriestest{timestamp}@example.com",
    "password": "test123",
    "name": "Series Tester"
}

try:
    # Register
    response = requests.post(f"{API_BASE}/auth/register", json=register_data, timeout=30)
    if response.status_code != 200:
        print(f"Registration failed: {response.text}")
        sys.exit(1)
    
    token = response.json()["token"]
    print(f"Registered user, got token")

    headers = {"Authorization": f"Bearer {token}"}
    
    # 1. Create series plan
    print("1. Creating series plan...")
    plan_data = {
        "topic": "productivity tips",
        "template_type": "numbered_tips",
        "num_posts": 3,
        "platform": "linkedin"
    }
    
    response = requests.post(f"{API_BASE}/content/series/plan", json=plan_data, headers=headers, timeout=60)
    if response.status_code != 200:
        print(f"Plan creation failed: {response.text}")
        sys.exit(1)
    
    plan_result = response.json()
    print(f"✅ Plan created: {plan_result['plan']['series_title']}")
    
    # 2. Save series
    print("2. Saving series...")
    save_data = {"plan": plan_result["plan"]}
    
    response = requests.post(f"{API_BASE}/content/series/save", json=save_data, headers=headers, timeout=30)
    if response.status_code != 200:
        print(f"Save failed: {response.text}")
        sys.exit(1)
    
    save_result = response.json()
    series_id = save_result["series_id"]
    print(f"✅ Series saved: {series_id}")
    
    # 3. List series
    print("3. Listing series...")
    response = requests.get(f"{API_BASE}/content/series", headers=headers, timeout=30)
    print(f"Series list response: {response.status_code}")
    
    if response.status_code != 200:
        print(f"❌ List failed: {response.text}")
    else:
        result = response.json()
        print(f"✅ Found {result['total']} series")
        if result['series']:
            series = result['series'][0]
            print(f"First series: {series['title']} (ID: {series['series_id']})")

except Exception as e:
    print(f"Error: {e}")