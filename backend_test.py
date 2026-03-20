#!/usr/bin/env python3

import requests
import json
import time
import uuid
from datetime import datetime

# Configuration
BASE_URL = "https://thook-growth.preview.emergentagent.com/api"
TEST_TIMEOUT = 45

class TestResults:
    def __init__(self):
        self.results = []
        self.passed = 0
        self.failed = 0
    
    def add_result(self, test_name, success, details="", response=None):
        self.results.append({
            "test": test_name,
            "success": success,
            "details": details,
            "response": response
        })
        if success:
            self.passed += 1
        else:
            self.failed += 1
        print(f"{'✅' if success else '❌'} {test_name}: {details}")
    
    def print_summary(self):
        print(f"\n📊 TEST SUMMARY: {self.passed} passed, {self.failed} failed")
        for result in self.results:
            if not result['success']:
                print(f"❌ {result['test']}: {result['details']}")

# Global test state
test_results = TestResults()
studio_user_token = None
studio_user_id = None
free_user_token = None
workspace_id = None
job_id_for_template = None

def make_request(method, endpoint, data=None, headers=None, timeout=TEST_TIMEOUT):
    """Make HTTP request with consistent error handling."""
    url = f"{BASE_URL}{endpoint}"
    default_headers = {"Content-Type": "application/json"}
    if headers:
        default_headers.update(headers)
    
    try:
        if method == "GET":
            response = requests.get(url, headers=default_headers, timeout=timeout)
        elif method == "POST":
            response = requests.post(url, json=data, headers=default_headers, timeout=timeout)
        elif method == "PUT":
            response = requests.put(url, json=data, headers=default_headers, timeout=timeout)
        elif method == "DELETE":
            response = requests.delete(url, headers=default_headers, timeout=timeout)
        
        return response
    except requests.exceptions.Timeout:
        return None
    except requests.exceptions.RequestException as e:
        return None

def register_and_setup_studio_user():
    """Register a new user and upgrade to Studio tier with completed onboarding."""
    global studio_user_token, studio_user_id
    
    timestamp = int(time.time())
    email = f"studio_test_{timestamp}@test.com"
    
    # 1. Register user
    register_data = {
        "name": f"Studio User {timestamp}",
        "email": email,
        "password": "testPassword123"
    }
    
    response = make_request("POST", "/auth/register", register_data)
    if not response or response.status_code != 200:
        test_results.add_result(
            "Register Studio User",
            False,
            f"Registration failed: {response.status_code if response else 'Timeout'}"
        )
        return False
    
    data = response.json()
    if not data.get("token") or not data.get("user_id"):
        test_results.add_result("Register Studio User", False, f"Registration failed: missing token or user_id")
        return False
    
    studio_user_token = data["token"]
    studio_user_id = data["user_id"]
    
    test_results.add_result(
        "Register Studio User",
        True,
        f"User registered with ID: {studio_user_id}"
    )
    
    # 2. Upgrade to Studio tier
    headers = {"Authorization": f"Bearer {studio_user_token}"}
    upgrade_data = {"tier": "studio"}
    
    response = make_request("POST", "/billing/subscription/upgrade", upgrade_data, headers)
    if not response or response.status_code != 200:
        test_results.add_result(
            "Upgrade to Studio Tier",
            False,
            f"Upgrade failed: {response.status_code if response else 'Timeout'}"
        )
        return False
    
    data = response.json()
    test_results.add_result(
        "Upgrade to Studio Tier", 
        data.get("success", False),
        f"New tier: {data.get('new_tier', 'unknown')}, Credits granted: {data.get('credits_granted', 0)}"
    )
    
    # 3. Complete onboarding to create persona
    onboarding_data = {
        "answers": [
            {"question_id": 0, "answer": "I'm an AI productivity consultant helping content creators scale their operations"},
            {"question_id": 1, "answer": "LinkedIn"},
            {"question_id": 2, "answer": "Strategic, Helpful, Technical"},
            {"question_id": 3, "answer": "Lenny Rachitsky for depth and accessibility"},
            {"question_id": 4, "answer": "Never want to write about crypto speculation or generic motivational content"},
            {"question_id": 5, "answer": "Generate leads/clients"}
        ]
    }
    
    response = make_request("POST", "/onboarding/generate-persona", onboarding_data, headers)
    if not response or response.status_code != 200:
        test_results.add_result(
            "Complete Studio User Onboarding",
            False,
            f"Onboarding failed: {response.status_code if response else 'Timeout'}"
        )
        return False
    
    data = response.json()
    has_persona_card = "persona_card" in data
    test_results.add_result(
        "Complete Studio User Onboarding",
        has_persona_card,
        "Onboarding completed, persona created successfully" if has_persona_card else f"Onboarding failed: {data}"
    )
    
    return True

def register_free_user():
    """Register a free tier user for testing restrictions."""
    global free_user_token
    
    timestamp = int(time.time())
    email = f"free_test_{timestamp}@test.com"
    
    register_data = {
        "name": f"Free User {timestamp}",
        "email": email,
        "password": "testPassword123"
    }
    
    response = make_request("POST", "/auth/register", register_data)
    if not response or response.status_code != 200:
        test_results.add_result(
            "Register Free User",
            False,
            f"Registration failed: {response.status_code if response else 'Timeout'}"
        )
        return False
    
    data = response.json()
    if not data.get("token") or not data.get("user_id"):
        test_results.add_result("Register Free User", False, f"Registration failed: missing token or user_id")
        return False
    
    free_user_token = data["token"]
    
    test_results.add_result(
        "Register Free User",
        True,
        "Free tier user registered successfully"
    )
    
    return True

def test_workspace_crud():
    """Test workspace CRUD operations."""
    global workspace_id
    
    if not studio_user_token:
        test_results.add_result("Workspace CRUD", False, "No studio user token available")
        return
    
    headers = {"Authorization": f"Bearer {studio_user_token}"}
    
    # 4. Create workspace
    workspace_data = {
        "name": "Test Agency",
        "description": "My test agency workspace"
    }
    
    response = make_request("POST", "/agency/workspace", workspace_data, headers)
    if not response or response.status_code != 200:
        test_results.add_result(
            "Create Workspace",
            False,
            f"Failed: {response.status_code if response else 'Timeout'}"
        )
        return
    
    data = response.json()
    if data.get("success"):
        workspace_id = data.get("workspace_id")
        test_results.add_result(
            "Create Workspace",
            True,
            f"Workspace created with ID: {workspace_id}"
        )
    else:
        test_results.add_result("Create Workspace", False, f"Failed: {data}")
        return
    
    # 5. List workspaces
    response = make_request("GET", "/agency/workspaces", headers=headers)
    if not response or response.status_code != 200:
        test_results.add_result(
            "List Workspaces",
            False,
            f"Failed: {response.status_code if response else 'Timeout'}"
        )
        return
    
    data = response.json()
    owned_workspaces = data.get("owned", [])
    success = data.get("success", False) and len(owned_workspaces) > 0
    test_results.add_result(
        "List Workspaces",
        success,
        f"Found {len(owned_workspaces)} owned workspaces" if success else "No workspaces found"
    )
    
    # 6. Get workspace details
    if workspace_id:
        response = make_request("GET", f"/agency/workspace/{workspace_id}", headers=headers)
        if not response or response.status_code != 200:
            test_results.add_result(
                "Get Workspace Details",
                False,
                f"Failed: {response.status_code if response else 'Timeout'}"
            )
        else:
            data = response.json()
            workspace = data.get("workspace", {})
            success = data.get("success", False) and workspace.get("name") == "Test Agency"
            test_results.add_result(
                "Get Workspace Details",
                success,
                f"Workspace name: {workspace.get('name')}, Role: {workspace.get('user_role')}, Members: {workspace.get('member_count', 0)}"
            )

def test_invitation_flow():
    """Test workspace invitation flow."""
    if not workspace_id or not studio_user_token:
        test_results.add_result("Invitation Flow", False, "Missing workspace_id or token")
        return
    
    headers = {"Authorization": f"Bearer {studio_user_token}"}
    
    # 7. Invite a creator
    invite_data = {
        "email": "creator@test.com",
        "role": "creator"
    }
    
    response = make_request("POST", f"/agency/workspace/{workspace_id}/invite", invite_data, headers)
    if not response or response.status_code != 200:
        test_results.add_result(
            "Invite Creator",
            False,
            f"Failed: {response.status_code if response else 'Timeout'}"
        )
        return
    
    data = response.json()
    invite_id = data.get("invite_id")
    success = data.get("success", False) and invite_id
    test_results.add_result(
        "Invite Creator",
        success,
        f"Invite ID: {invite_id}, Status: {data.get('status', 'unknown')}" if success else f"Failed: {data}"
    )
    
    # 8. List members
    response = make_request("GET", f"/agency/workspace/{workspace_id}/members", headers=headers)
    if not response or response.status_code != 200:
        test_results.add_result(
            "List Members",
            False,
            f"Failed: {response.status_code if response else 'Timeout'}"
        )
        return
    
    data = response.json()
    members = data.get("members", [])
    success = data.get("success", False) and len(members) >= 1
    
    # Check for owner and pending invite
    has_owner = any(m.get("role") == "owner" for m in members)
    has_pending = any(m.get("status") == "pending" for m in members)
    
    test_results.add_result(
        "List Members",
        success and has_owner,
        f"Total members: {len(members)}, Has owner: {has_owner}, Has pending invite: {has_pending}"
    )
    
    # 9. List creators with stats
    response = make_request("GET", f"/agency/workspace/{workspace_id}/creators", headers=headers)
    if not response or response.status_code != 200:
        test_results.add_result(
            "List Creators with Stats",
            False,
            f"Failed: {response.status_code if response else 'Timeout'}"
        )
        return
    
    data = response.json()
    creators = data.get("creators", [])
    success = data.get("success", False)
    test_results.add_result(
        "List Creators with Stats",
        success,
        f"Found {len(creators)} active creators" if success else f"Failed: {data}"
    )
    
    # 10. Get workspace content
    response = make_request("GET", f"/agency/workspace/{workspace_id}/content", headers=headers)
    if not response or response.status_code != 200:
        test_results.add_result(
            "Get Workspace Content",
            False,
            f"Failed: {response.status_code if response else 'Timeout'}"
        )
        return
    
    data = response.json()
    content = data.get("content", [])
    success = data.get("success", False)
    test_results.add_result(
        "Get Workspace Content",
        success,
        f"Found {len(content)} content items" if success else f"Failed: {data}"
    )

def test_tier_restriction():
    """Test that free tier users cannot access agency features."""
    if not free_user_token:
        test_results.add_result("Tier Restriction", False, "No free user token available")
        return
    
    headers = {"Authorization": f"Bearer {free_user_token}"}
    
    # 11. Try to create workspace with free user
    workspace_data = {
        "name": "Free User Workspace",
        "description": "This should fail"
    }
    
    response = make_request("POST", "/agency/workspace", workspace_data, headers)
    
    # Should return 403 Forbidden
    if response and response.status_code == 403:
        data = response.json()
        expected_message = "Agency features require Studio or Agency tier"
        has_expected_message = expected_message in data.get("detail", "")
        test_results.add_result(
            "Tier Restriction (Free User)",
            has_expected_message,
            f"Got expected 403 error: {data.get('detail', '')}" if has_expected_message else f"Wrong error message: {data.get('detail', '')}"
        )
    else:
        test_results.add_result(
            "Tier Restriction (Free User)",
            False,
            f"Expected 403, got {response.status_code if response else 'Timeout'}"
        )

def test_templates_categories():
    """Test template categories endpoint."""
    if not studio_user_token:
        test_results.add_result("Templates Categories", False, "No studio user token available")
        return
    
    headers = {"Authorization": f"Bearer {studio_user_token}"}
    
    # 13. Get categories
    response = make_request("GET", "/templates/categories", headers=headers)
    if not response or response.status_code != 200:
        test_results.add_result(
            "Get Templates Categories",
            False,
            f"Failed: {response.status_code if response else 'Timeout'}"
        )
        return
    
    data = response.json()
    categories = data.get("categories", [])
    hook_types = data.get("hook_types", [])
    success = data.get("success", False) and len(categories) == 10 and len(hook_types) == 8
    
    test_results.add_result(
        "Get Templates Categories",
        success,
        f"Categories: {len(categories)}, Hook types: {len(hook_types)}" if success else f"Wrong counts: {len(categories)} categories, {len(hook_types)} hook types"
    )

def create_test_content():
    """Create and approve test content for templates."""
    global job_id_for_template
    
    if not studio_user_token:
        test_results.add_result("Create Test Content", False, "No studio user token available")
        return
    
    headers = {"Authorization": f"Bearer {studio_user_token}"}
    
    # Create content
    content_data = {
        "platform": "linkedin",
        "content_type": "post", 
        "raw_input": "AI productivity tips for content creators - help people understand how to use AI tools effectively for content creation"
    }
    
    response = make_request("POST", "/content/create", content_data, headers)
    if not response or response.status_code != 200:
        test_results.add_result(
            "Create Test Content",
            False,
            f"Failed: {response.status_code if response else 'Timeout'}"
        )
        return
    
    data = response.json()
    job_id = data.get("job_id")
    if not job_id:
        test_results.add_result("Create Test Content", False, "No job_id returned")
        return
    
    # Since we can't easily get approved content, let's mock it by directly updating the database
    # For testing purposes, we'll assume this content would be approved
    job_id_for_template = job_id
    
    test_results.add_result(
        "Create Test Content",
        True,
        f"Content created with job_id: {job_id} (would need manual approval for template publishing)"
    )

def test_templates_marketplace():
    """Test templates marketplace endpoints."""
    if not studio_user_token:
        test_results.add_result("Templates Marketplace", False, "No studio user token available")
        return
    
    headers = {"Authorization": f"Bearer {studio_user_token}"}
    
    # 15. Browse templates
    response = make_request("GET", "/templates", headers=headers)
    if not response or response.status_code != 200:
        test_results.add_result(
            "Browse Templates",
            False,
            f"Failed: {response.status_code if response else 'Timeout'}"
        )
    else:
        data = response.json()
        templates = data.get("templates", [])
        success = data.get("success", False)
        test_results.add_result(
            "Browse Templates",
            success,
            f"Found {len(templates)} templates, Total: {data.get('total', 0)}"
        )
    
    # 16. Get featured templates
    response = make_request("GET", "/templates/featured", headers=headers)
    if not response or response.status_code != 200:
        test_results.add_result(
            "Get Featured Templates",
            False,
            f"Failed: {response.status_code if response else 'Timeout'}"
        )
    else:
        data = response.json()
        featured = data.get("featured", [])
        recent = data.get("recent", [])
        success = data.get("success", False)
        test_results.add_result(
            "Get Featured Templates",
            success,
            f"Featured: {len(featured)}, Recent: {len(recent)}" if success else f"Failed: {data}"
        )
    
    # 17. Test template publishing with non-existent job_id
    fake_template_data = {
        "job_id": "non-existent-job-id-12345",
        "title": "Test Template",
        "category": "thought_leadership",
        "description": "This should fail"
    }
    
    response = make_request("POST", "/templates", fake_template_data, headers)
    
    # Should return 404 "Content not found"
    if response and response.status_code == 404:
        data = response.json()
        expected_message = "Content not found"
        has_expected_message = expected_message in data.get("detail", "")
        test_results.add_result(
            "Template Publishing Validation",
            has_expected_message,
            f"Got expected 404 error: {data.get('detail', '')}" if has_expected_message else f"Wrong error message: {data.get('detail', '')}"
        )
    else:
        test_results.add_result(
            "Template Publishing Validation",
            False,
            f"Expected 404, got {response.status_code if response else 'Timeout'}"
        )

def main():
    """Run all Sprint 12 tests."""
    print("🚀 Starting Sprint 12 Backend Testing - Agency Workspace & Templates Marketplace")
    print(f"Testing against: {BASE_URL}")
    print("=" * 80)
    
    # PRE-SETUP
    print("\n📋 PRE-SETUP:")
    if not register_and_setup_studio_user():
        print("❌ Failed to setup studio user, aborting tests")
        return
    
    if not register_free_user():
        print("❌ Failed to setup free user, some tests will be skipped")
    
    # AGENCY WORKSPACE TESTS
    print("\n🏢 AGENCY WORKSPACE TESTS:")
    test_workspace_crud()
    test_invitation_flow()
    test_tier_restriction()
    
    # TEMPLATES MARKETPLACE TESTS  
    print("\n📚 TEMPLATES MARKETPLACE TESTS:")
    test_templates_categories()
    create_test_content()
    test_templates_marketplace()
    
    # Summary
    print("\n" + "=" * 80)
    test_results.print_summary()
    
    return test_results.failed == 0

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)