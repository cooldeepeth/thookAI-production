#!/usr/bin/env python3
"""
Debug script for series list issue.

NOTE: This is a live E2E integration script, not a pytest unit test.
Run directly: python3 debug_series_test.py
"""
import pytest

# This module is a standalone script — mark it so pytest skips it.
collect_ignore = True


def _run_debug():
    import requests
    import sys

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

    # Create test user and get token
    register_data = {
        "email": "debugtest@example.com",
        "password": "test123",
        "name": "Debug Tester"
    }

    try:
        # Register
        response = requests.post(f"{API_BASE}/auth/register", json=register_data, timeout=30)
        if response.status_code == 200:
            token = response.json()["token"]
        else:
            # Try login
            login_data = {"email": "debugtest@example.com", "password": "test123"}
            response = requests.post(f"{API_BASE}/auth/login", json=login_data, timeout=30)
            if response.status_code == 200:
                token = response.json()["token"]
            else:
                print(f"Failed to authenticate: {response.text}")
                sys.exit(1)

        print(f"Got token: {token[:20]}...")

        # Test series list endpoint directly
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{API_BASE}/content/series", headers=headers, timeout=30)

        print(f"Series list response: {response.status_code}")
        if response.status_code != 200:
            print(f"Error response: {response.text}")
        else:
            print(f"Success response: {response.json()}")

    except Exception as e:
        print(f"Error: {e}")


@pytest.mark.skip(reason="Live E2E integration script — run directly, not via pytest")
def test_series_list_debug():
    """Placeholder so pytest can collect this file without errors."""
    pass


if __name__ == "__main__":
    _run_debug()
