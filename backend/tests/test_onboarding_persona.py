"""Backend tests for Onboarding and Persona Engine APIs - Sprint 2"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

TEST_CREDENTIALS = {"email": "test@thook.ai", "password": "TestPass123!"}
FRESH_CREDENTIALS = {"email": "fresh@thook.ai", "password": "FreshPass123!"}

SAMPLE_ANSWERS = [
    {"question_id": 0, "answer": "I am a SaaS founder sharing lessons on product-market fit"},
    {"question_id": 1, "answer": "LinkedIn"},
    {"question_id": 2, "answer": "Bold, Strategic, Human"},
    {"question_id": 3, "answer": "Paul Graham for razor-sharp clarity"},
    {"question_id": 4, "answer": "Crypto speculation, politics"},
    {"question_id": 5, "answer": "Build personal brand"},
    {"question_id": 6, "answer": "1–3 hours"},
]


@pytest.fixture(scope="module")
def test_token():
    r = requests.post(f"{BASE_URL}/api/auth/login", json=TEST_CREDENTIALS)
    assert r.status_code == 200
    return r.json()["token"]


@pytest.fixture(scope="module")
def fresh_token():
    r = requests.post(f"{BASE_URL}/api/auth/login", json=FRESH_CREDENTIALS)
    assert r.status_code == 200
    return r.json()["token"]


def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


# Onboarding Questions
def test_get_questions_returns_7():
    r = requests.get(f"{BASE_URL}/api/onboarding/questions")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 7
    assert len(data["questions"]) == 7


def test_questions_have_correct_structure():
    r = requests.get(f"{BASE_URL}/api/onboarding/questions")
    data = r.json()
    for q in data["questions"]:
        assert "id" in q
        assert "type" in q
        assert "question" in q
        assert "hint" in q
    # Check types
    types = [q["type"] for q in data["questions"]]
    assert "text" in types
    assert "multi_choice" in types


# Analyze Posts
def test_analyze_posts_returns_analysis(test_token):
    r = requests.post(
        f"{BASE_URL}/api/onboarding/analyze-posts",
        json={"posts_text": "I build SaaS tools. Here are my lessons from shipping fast.", "platform": "LinkedIn"},
        headers=auth_headers(test_token)
    )
    assert r.status_code == 200
    data = r.json()
    assert "analysis" in data
    assert len(data["analysis"]) > 10


def test_analyze_posts_requires_auth():
    r = requests.post(
        f"{BASE_URL}/api/onboarding/analyze-posts",
        json={"posts_text": "test"}
    )
    assert r.status_code == 401


# Generate Persona
def test_generate_persona_with_full_answers(fresh_token):
    r = requests.post(
        f"{BASE_URL}/api/onboarding/generate-persona",
        json={"answers": SAMPLE_ANSWERS},
        headers=auth_headers(fresh_token)
    )
    assert r.status_code == 200
    data = r.json()
    assert "persona_card" in data
    card = data["persona_card"]
    required = ["writing_voice_descriptor", "content_niche_signature", "personality_archetype",
                "content_pillars", "tone", "hook_style", "focus_platforms", "burnout_risk", "risk_tolerance"]
    for field in required:
        assert field in card, f"Missing field: {field}"


def test_generate_persona_updates_onboarding_flag(fresh_token):
    # Generate persona
    requests.post(
        f"{BASE_URL}/api/onboarding/generate-persona",
        json={"answers": SAMPLE_ANSWERS},
        headers=auth_headers(fresh_token)
    )
    # Check user flag
    r = requests.get(f"{BASE_URL}/api/auth/me", headers=auth_headers(fresh_token))
    assert r.status_code == 200
    assert r.json()["onboarding_completed"] == True


# Persona CRUD
def test_get_persona_me(test_token):
    r = requests.get(f"{BASE_URL}/api/persona/me", headers=auth_headers(test_token))
    assert r.status_code == 200
    data = r.json()
    assert "card" in data
    assert "uom" in data
    assert "voice_fingerprint" in data


def test_update_persona_me(test_token):
    r = requests.put(
        f"{BASE_URL}/api/persona/me",
        json={"card": {"writing_voice_descriptor": "TEST_Updated voice descriptor"}},
        headers=auth_headers(test_token)
    )
    assert r.status_code == 200
    assert r.json()["message"] == "Persona updated successfully"
    # Verify persisted
    r2 = requests.get(f"{BASE_URL}/api/persona/me", headers=auth_headers(test_token))
    assert r2.json()["card"]["writing_voice_descriptor"] == "TEST_Updated voice descriptor"


def test_delete_persona_resets_flag(fresh_token):
    # Ensure persona exists
    requests.post(
        f"{BASE_URL}/api/onboarding/generate-persona",
        json={"answers": SAMPLE_ANSWERS},
        headers=auth_headers(fresh_token)
    )
    # Delete
    r = requests.delete(f"{BASE_URL}/api/persona/me", headers=auth_headers(fresh_token))
    assert r.status_code == 200
    # Check flag reset
    r2 = requests.get(f"{BASE_URL}/api/auth/me", headers=auth_headers(fresh_token))
    assert r2.json()["onboarding_completed"] == False
    # Persona should be gone
    r3 = requests.get(f"{BASE_URL}/api/persona/me", headers=auth_headers(fresh_token))
    assert r3.status_code == 404
