#!/usr/bin/env python3
"""
Test authentication isolation - ensure no cookies are interfering
"""

import asyncio
import aiohttp

BASE_URL = "https://thook-growth.preview.emergentagent.com/api"

async def test_auth_isolation():
    # Create completely separate session for auth testing
    async with aiohttp.ClientSession() as session:
        print("Testing auth without any tokens...")
        
        # Test 1: No auth headers or cookies
        async with session.get(f"{BASE_URL}/persona/me") as response:
            status1 = response.status
            data1 = await response.json() if response.content_type == 'application/json' else await response.text()
            print(f"No auth: Status {status1}, Response: {str(data1)[:100]}")
        
        # Test 2: Invalid Bearer token
        headers = {"Authorization": "Bearer invalid-token-xyz"}
        async with session.get(f"{BASE_URL}/persona/me", headers=headers) as response:
            status2 = response.status
            data2 = await response.json() if response.content_type == 'application/json' else await response.text()
            print(f"Invalid token: Status {status2}, Response: {str(data2)[:100]}")
        
        # Test 3: Valid endpoint that should work without auth
        async with session.get(f"{BASE_URL}/") as response:
            status3 = response.status
            data3 = await response.json() if response.content_type == 'application/json' else await response.text()
            print(f"Public endpoint: Status {status3}, Response: {str(data3)[:100]}")

if __name__ == "__main__":
    asyncio.run(test_auth_isolation())