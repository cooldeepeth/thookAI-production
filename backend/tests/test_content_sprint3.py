"""
Sprint 3 Content Studio API Tests
Tests: POST /create, GET /job/{id}, PATCH /job/{id}/status, GET /jobs, GET /platform-types
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
SESSION_TOKEN = "test_session_sprint2_1773805008345"

HEADERS = {
    "Content-Type": "application/json",
    "Cookie": f"session_token={SESSION_TOKEN}"
}


def auth_headers():
    return HEADERS


# ── Platform Types ──────────────────────────────────────────────────────────

class TestPlatformTypes:
    """GET /api/content/platform-types"""

    def test_get_platform_types(self):
        r = requests.get(f"{BASE_URL}/api/content/platform-types", headers=auth_headers())
        assert r.status_code == 200
        data = r.json()
        assert "linkedin" in data
        assert "x" in data
        assert "instagram" in data
        assert "post" in data["linkedin"]
        assert "tweet" in data["x"]
        print("PASS: platform-types returns correct mapping")


# ── Create Content Job ───────────────────────────────────────────────────────

class TestCreateContentJob:
    """POST /api/content/create"""

    def test_create_valid_linkedin_post(self):
        r = requests.post(f"{BASE_URL}/api/content/create", json={
            "platform": "linkedin",
            "content_type": "post",
            "raw_input": "5 lessons I learned scaling to $1M ARR"
        }, headers=auth_headers())
        assert r.status_code == 200
        data = r.json()
        assert "job_id" in data
        assert data["status"] == "running"
        print(f"PASS: Created job {data['job_id']}")
        return data["job_id"]

    def test_create_returns_400_for_short_input(self):
        r = requests.post(f"{BASE_URL}/api/content/create", json={
            "platform": "linkedin",
            "content_type": "post",
            "raw_input": "hi"
        }, headers=auth_headers())
        assert r.status_code == 400
        print("PASS: 400 for short input")

    def test_create_returns_400_for_invalid_content_type(self):
        r = requests.post(f"{BASE_URL}/api/content/create", json={
            "platform": "linkedin",
            "content_type": "tweet",  # tweet is not valid for linkedin
            "raw_input": "Valid input text here"
        }, headers=auth_headers())
        assert r.status_code == 400
        print("PASS: 400 for invalid content_type for platform")

    def test_create_x_tweet(self):
        r = requests.post(f"{BASE_URL}/api/content/create", json={
            "platform": "x",
            "content_type": "tweet",
            "raw_input": "Why remote teams outperform in-office teams"
        }, headers=auth_headers())
        assert r.status_code == 200
        data = r.json()
        assert "job_id" in data
        print(f"PASS: Created X tweet job {data['job_id']}")


# ── Get Job Status ───────────────────────────────────────────────────────────

class TestGetJob:
    """GET /api/content/job/{job_id}"""

    JOB_ID = "job_307f39714a52"  # pre-created reference job

    def test_get_reference_job(self):
        r = requests.get(f"{BASE_URL}/api/content/job/{self.JOB_ID}", headers=auth_headers())
        assert r.status_code == 200
        data = r.json()
        assert data["job_id"] == self.JOB_ID
        assert data["status"] == "reviewing"
        assert data["platform"] == "linkedin"
        print(f"PASS: Reference job {self.JOB_ID} has status=reviewing")

    def test_reference_job_has_final_content(self):
        r = requests.get(f"{BASE_URL}/api/content/job/{self.JOB_ID}", headers=auth_headers())
        assert r.status_code == 200
        data = r.json()
        assert data.get("final_content") is not None
        assert len(data["final_content"]) > 0
        print(f"PASS: final_content present, length={len(data['final_content'])}")

    def test_reference_job_has_qc_scores(self):
        r = requests.get(f"{BASE_URL}/api/content/job/{self.JOB_ID}", headers=auth_headers())
        assert r.status_code == 200
        data = r.json()
        qc = data.get("qc_score")
        assert qc is not None
        assert "personaMatch" in qc
        assert "aiRisk" in qc
        assert "platformFit" in qc
        print(f"PASS: QC scores: personaMatch={qc.get('personaMatch')}, aiRisk={qc.get('aiRisk')}, platformFit={qc.get('platformFit')}")

    def test_reference_job_has_agent_summaries(self):
        r = requests.get(f"{BASE_URL}/api/content/job/{self.JOB_ID}", headers=auth_headers())
        assert r.status_code == 200
        data = r.json()
        summaries = data.get("agent_summaries", {})
        for agent in ["commander", "scout", "thinker", "writer", "qc"]:
            assert agent in summaries, f"Missing summary for {agent}"
        print("PASS: All agent_summaries present")

    def test_get_nonexistent_job_returns_404(self):
        r = requests.get(f"{BASE_URL}/api/content/job/job_nonexistent999", headers=auth_headers())
        assert r.status_code == 404
        print("PASS: 404 for nonexistent job")


# ── Patch Job Status ─────────────────────────────────────────────────────────

class TestPatchJobStatus:
    """PATCH /api/content/job/{job_id}/status"""

    def test_approve_reference_job(self):
        r = requests.patch(f"{BASE_URL}/api/content/job/job_307f39714a52/status", json={
            "status": "approved"
        }, headers=auth_headers())
        assert r.status_code == 200
        data = r.json()
        assert "approved" in data.get("message", "").lower()
        print("PASS: approved reference job")

    def test_approve_with_edited_content(self):
        r = requests.patch(f"{BASE_URL}/api/content/job/job_307f39714a52/status", json={
            "status": "approved",
            "edited_content": "My edited content for testing purposes"
        }, headers=auth_headers())
        assert r.status_code == 200
        print("PASS: approved with edited_content")

        # verify the content was updated
        r2 = requests.get(f"{BASE_URL}/api/content/job/job_307f39714a52", headers=auth_headers())
        assert r2.status_code == 200
        data = r2.json()
        assert data["final_content"] == "My edited content for testing purposes"
        assert data["status"] == "approved"
        print("PASS: Verified edited_content persisted")


# ── List Jobs ────────────────────────────────────────────────────────────────

class TestListJobs:
    """GET /api/content/jobs"""

    def test_list_jobs_returns_array(self):
        r = requests.get(f"{BASE_URL}/api/content/jobs", headers=auth_headers())
        assert r.status_code == 200
        data = r.json()
        assert "jobs" in data
        assert isinstance(data["jobs"], list)
        print(f"PASS: jobs list returned, count={len(data['jobs'])}")

    def test_jobs_do_not_include_agent_outputs(self):
        r = requests.get(f"{BASE_URL}/api/content/jobs", headers=auth_headers())
        assert r.status_code == 200
        jobs = r.json()["jobs"]
        if jobs:
            for job in jobs[:3]:
                assert "agent_outputs" not in job, "agent_outputs should be excluded from list"
        print("PASS: agent_outputs excluded from list")


# ── Full Pipeline Test (creates job and waits up to 90s) ─────────────────────

class TestFullPipeline:
    """Tests that the full pipeline completes within 90 seconds"""

    def test_full_pipeline_completes(self):
        # Create a new job
        r = requests.post(f"{BASE_URL}/api/content/create", json={
            "platform": "linkedin",
            "content_type": "post",
            "raw_input": "The future of AI in content creation is here"
        }, headers=auth_headers())
        assert r.status_code == 200
        job_id = r.json()["job_id"]
        print(f"Created job: {job_id}, waiting for pipeline to complete...")

        # Poll for up to 90 seconds
        start = time.time()
        final_job = None
        while time.time() - start < 90:
            time.sleep(5)
            r2 = requests.get(f"{BASE_URL}/api/content/job/{job_id}", headers=auth_headers())
            if r2.status_code == 200:
                job = r2.json()
                print(f"  [{int(time.time()-start)}s] status={job.get('status')}, agent={job.get('current_agent')}")
                if job["status"] in ("reviewing", "error", "approved"):
                    final_job = job
                    break

        assert final_job is not None, "Pipeline did not complete within 90 seconds"
        assert final_job["status"] == "reviewing", f"Pipeline ended with status={final_job['status']}, error={final_job.get('error')}"
        assert final_job.get("final_content") and len(final_job["final_content"]) > 0
        qc = final_job.get("qc_score", {})
        assert "personaMatch" in qc
        assert "aiRisk" in qc
        assert "platformFit" in qc
        print(f"PASS: Full pipeline completed in {int(time.time()-start)}s. QC={qc}")
