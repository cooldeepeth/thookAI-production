"""Backend API tests for ThookAI - Auth endpoints"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

TIMESTAMP = int(time.time())
TEST_EMAIL = f"TEST_user_{TIMESTAMP}@thook.ai"
TEST_PASSWORD = "TestPass123!"
TEST_NAME = "Test User Sprint1"

EXISTING_EMAIL = "test@thook.ai"
EXISTING_PASSWORD = "TestPass123!"


class TestHealthCheck:
    """Health and root endpoint tests"""

    def test_root_api(self):
        r = requests.get(f"{BASE_URL}/api/")
        assert r.status_code == 200
        data = r.json()
        assert data.get("status") == "running"

    def test_health_endpoint(self):
        r = requests.get(f"{BASE_URL}/api/health")
        assert r.status_code == 200


class TestRegister:
    """Registration endpoint tests"""

    def test_register_new_user(self):
        r = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD,
            "name": TEST_NAME
        })
        assert r.status_code == 200
        data = r.json()
        assert "token" in data
        assert data["email"] == TEST_EMAIL
        assert "user_id" in data
        assert "hashed_password" not in data
        assert "_id" not in data

    def test_register_duplicate_email(self):
        # Register twice with same email
        requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": TEST_EMAIL + ".dup",
            "password": TEST_PASSWORD,
            "name": TEST_NAME
        })
        r = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": TEST_EMAIL + ".dup",
            "password": TEST_PASSWORD,
            "name": TEST_NAME
        })
        assert r.status_code == 400


class TestLogin:
    """Login endpoint tests"""

    def test_login_existing_user(self):
        r = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": EXISTING_EMAIL,
            "password": EXISTING_PASSWORD
        })
        assert r.status_code == 200
        data = r.json()
        assert "token" in data
        assert data["email"] == EXISTING_EMAIL
        assert "hashed_password" not in data

    def test_login_wrong_password(self):
        r = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": EXISTING_EMAIL,
            "password": "WrongPassword!"
        })
        assert r.status_code == 401

    def test_login_nonexistent_user(self):
        r = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "nonexistent@thook.ai",
            "password": "Pass123!"
        })
        assert r.status_code == 401


class TestAuthMe:
    """GET /api/auth/me endpoint tests"""

    def test_me_with_valid_token(self):
        # Login first to get token
        login_r = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": EXISTING_EMAIL,
            "password": EXISTING_PASSWORD
        })
        assert login_r.status_code == 200
        token = login_r.json()["token"]

        r = requests.get(f"{BASE_URL}/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        data = r.json()
        assert data["email"] == EXISTING_EMAIL
        assert "hashed_password" not in data
        assert "_id" not in data

    def test_me_without_token(self):
        r = requests.get(f"{BASE_URL}/api/auth/me")
        assert r.status_code == 401

    def test_me_with_invalid_token(self):
        r = requests.get(f"{BASE_URL}/api/auth/me", headers={"Authorization": "Bearer invalidtoken"})
        assert r.status_code == 401


class TestLogout:
    """Logout endpoint tests"""

    def test_logout(self):
        # Login first
        session = requests.Session()
        login_r = session.post(f"{BASE_URL}/api/auth/login", json={
            "email": EXISTING_EMAIL,
            "password": EXISTING_PASSWORD
        })
        assert login_r.status_code == 200

        r = session.post(f"{BASE_URL}/api/auth/logout")
        assert r.status_code == 200
        data = r.json()
        assert "message" in data
