#!/usr/bin/env python3
"""
Test authentication isolation - ensure no cookies are interfering.

NOTE: This is a live E2E integration script requiring a running server.
Run directly: python3 auth_isolation_test.py
"""
import pytest


def _run_auth_isolation():
    import asyncio
    import httpx

    BASE_URL = "https://celery-dispatch-fix.preview.emergentagent.com/api"

    async def test_auth_isolation():
        async with httpx.AsyncClient() as session:
            print("Testing auth without any tokens...")

            # Test 1: No auth headers or cookies
            response = await session.get(f"{BASE_URL}/persona/me")
            status1 = response.status_code
            try:
                data1 = response.json()
            except Exception:
                data1 = response.text
            print(f"No auth: Status {status1}, Response: {str(data1)[:100]}")

            # Test 2: Invalid Bearer token
            headers = {"Authorization": "Bearer invalid-token-xyz"}
            response = await session.get(f"{BASE_URL}/persona/me", headers=headers)
            status2 = response.status_code
            try:
                data2 = response.json()
            except Exception:
                data2 = response.text
            print(f"Invalid token: Status {status2}, Response: {str(data2)[:100]}")

            # Test 3: Valid endpoint that should work without auth
            response = await session.get(f"{BASE_URL}/")
            status3 = response.status_code
            try:
                data3 = response.json()
            except Exception:
                data3 = response.text
            print(f"Public endpoint: Status {status3}, Response: {str(data3)[:100]}")

    asyncio.run(test_auth_isolation())


@pytest.mark.skip(reason="Live E2E integration script — run directly against a server, not via pytest")
def test_auth_isolation_placeholder():
    """Placeholder so pytest can collect this file without errors."""
    pass


if __name__ == "__main__":
    _run_auth_isolation()
