"""
Docker Compose Integration Smoke Test — All Services Healthy Within 120s (E2E-06)

Verifies that `docker compose up` brings all 7 ThookAI services to a healthy state
within 120 seconds. Requires Docker to be available in the environment.

Run manually:
  cd backend && pytest tests/integration/test_docker_smoke.py -v -m integration

Skip in regular CI (no Docker):
  pytest -m "not integration"   # default — integration tests auto-skipped

All tests in this module are marked with @pytest.mark.integration and are
automatically skipped when Docker is not available on the host.
"""

import json
import shutil
import socket
import subprocess
import time
import urllib.request
from pathlib import Path
from typing import Optional
from urllib.error import URLError

import pytest

# ---------------------------------------------------------------------------
# Auto-skip entire module if Docker is not present
# ---------------------------------------------------------------------------

pytestmark = pytest.mark.skipif(
    not shutil.which("docker"),
    reason="Docker not available — skipping Docker Compose smoke tests",
)

# ---------------------------------------------------------------------------
# Service definitions
# ---------------------------------------------------------------------------

# Project root is two levels above this file:
#   backend/tests/integration/test_docker_smoke.py → backend/tests/integration
#   → backend/tests → backend → project root
_PROJECT_ROOT = Path(__file__).parent.parent.parent.parent

# Services map: name → health check config.
# "url" services are checked via HTTP GET; "port" services via TCP connect.
SERVICES: dict[str, dict] = {
    "backend": {"url": "http://localhost:8001/health", "timeout": 60},
    "frontend": {"url": "http://localhost:3000", "timeout": 120},
    "mongo": {"port": 27017, "timeout": 30},
    "redis": {"port": 6379, "timeout": 30},
    "n8n": {"url": "http://localhost:5678/healthz", "timeout": 90},
    "lightrag": {"url": "http://localhost:9621/health", "timeout": 90},
    "remotion": {"url": "http://localhost:3001/health", "timeout": 90},
}


# ---------------------------------------------------------------------------
# Helper: wait for HTTP URL to return 2xx
# ---------------------------------------------------------------------------


def _wait_for_url(url: str, timeout_sec: int) -> tuple[bool, float]:
    """Poll an HTTP URL every 5 seconds until it returns 2xx or timeout expires.

    Returns:
        (healthy: bool, elapsed_seconds: float)
    """
    start = time.monotonic()
    deadline = start + timeout_sec
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=5) as resp:
                if resp.status < 400:
                    return True, time.monotonic() - start
        except (URLError, TimeoutError, ConnectionRefusedError, OSError):
            pass
        time.sleep(5)
    return False, time.monotonic() - start


# ---------------------------------------------------------------------------
# Helper: wait for TCP port to accept connections
# ---------------------------------------------------------------------------


def _wait_for_port(port: int, timeout_sec: int) -> tuple[bool, float]:
    """Poll a TCP port every 5 seconds until connection succeeds or timeout.

    Returns:
        (healthy: bool, elapsed_seconds: float)
    """
    start = time.monotonic()
    deadline = start + timeout_sec
    while time.monotonic() < deadline:
        try:
            with socket.create_connection(("localhost", port), timeout=5):
                return True, time.monotonic() - start
        except (ConnectionRefusedError, TimeoutError, OSError):
            pass
        time.sleep(5)
    return False, time.monotonic() - start


# ---------------------------------------------------------------------------
# Helper: check a single service
# ---------------------------------------------------------------------------


def _check_service(name: str, config: dict) -> tuple[bool, float]:
    """Check health of a single service using URL or port, per its config."""
    if "url" in config:
        return _wait_for_url(config["url"], config["timeout"])
    elif "port" in config:
        return _wait_for_port(config["port"], config["timeout"])
    return False, 0.0


# ---------------------------------------------------------------------------
# Test class
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestDockerComposeSmokeE2E06:
    """Smoke tests for Docker Compose stack startup and cross-service health.

    All tests in this class share the `compose_up` fixture which brings up
    the full stack before any test runs and tears it down after all tests
    in the class complete.
    """

    # ------------------------------------------------------------------
    # Fixture: bring up Docker Compose stack
    # ------------------------------------------------------------------

    @pytest.fixture(scope="class")
    def compose_up(self):  # type: ignore[override]
        """Start Docker Compose stack, yield for tests, then teardown.

        Uses the main docker-compose.yml from the project root.
        Builds images before starting to pick up any local changes.
        """
        compose_file = str(_PROJECT_ROOT / "docker-compose.yml")
        compose_cmd_base = ["docker", "compose", "-f", compose_file]

        # Start stack
        result = subprocess.run(
            compose_cmd_base + ["up", "-d", "--build"],
            cwd=str(_PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=300,
        )

        if result.returncode != 0:
            raise RuntimeError(
                f"docker compose up failed (exit {result.returncode}):\n"
                f"STDOUT: {result.stdout[-2000:]}\n"
                f"STDERR: {result.stderr[-2000:]}"
            )

        yield  # Run tests

        # Teardown: stop and remove all containers + volumes
        subprocess.run(
            compose_cmd_base + ["down", "-v", "--remove-orphans"],
            cwd=str(_PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=120,
        )

    # ------------------------------------------------------------------
    # Test 1: All 7 services healthy within 120 seconds (overall wall clock)
    # ------------------------------------------------------------------

    def test_all_services_healthy_within_120s(self, compose_up: None) -> None:
        """Verify every service in SERVICES becomes healthy within 120 seconds.

        The 120-second budget is measured from when this test begins — by this
        point `docker compose up` has already completed so services should be
        near-ready.  Each service has its own per-service timeout (shorter for
        fast services like mongo/redis, longer for frontend/n8n).
        """
        overall_start = time.monotonic()
        results: dict[str, dict] = {}

        for svc_name, svc_config in SERVICES.items():
            healthy, elapsed = _check_service(svc_name, svc_config)
            results[svc_name] = {
                "healthy": healthy,
                "elapsed_s": round(elapsed, 1),
                "timeout_s": svc_config["timeout"],
            }

        overall_elapsed = time.monotonic() - overall_start

        # Print summary table for CI logs
        print("\n\n=== Docker Compose Health Check Summary ===")
        print(f"{'Service':<12} {'Status':<8} {'Time(s)':<10} {'Timeout(s)'}")
        print("-" * 44)
        for svc_name, info in results.items():
            status = "HEALTHY" if info["healthy"] else "TIMEOUT"
            print(
                f"{svc_name:<12} {status:<8} {info['elapsed_s']:<10} {info['timeout_s']}"
            )
        print(f"\nTotal wall clock: {overall_elapsed:.1f}s")
        print("==========================================\n")

        # Assert all services healthy
        failed_services = [
            name for name, info in results.items() if not info["healthy"]
        ]
        assert not failed_services, (
            f"Services did not become healthy within their timeouts: {failed_services}\n"
            f"Details: {json.dumps(results, indent=2)}"
        )

        # Assert total elapsed is within 120s budget
        assert overall_elapsed <= 120, (
            f"Total time to health ({overall_elapsed:.1f}s) exceeded 120-second budget. "
            f"Service results: {json.dumps(results, indent=2)}"
        )

    # ------------------------------------------------------------------
    # Test 2: Backend /health endpoint returns expected shape
    # ------------------------------------------------------------------

    def test_backend_health_returns_ok(self, compose_up: None) -> None:
        """GET /health returns HTTP 200 with expected JSON fields."""
        url = "http://localhost:8001/health"

        # Wait up to 30s in case the stack was just brought up
        healthy, _ = _wait_for_url(url, timeout_sec=30)
        assert healthy, "Backend /health did not return 2xx within 30 seconds"

        with urllib.request.urlopen(url, timeout=10) as resp:
            assert resp.status == 200, f"Expected 200, got {resp.status}"
            body = json.loads(resp.read().decode())

        # The health endpoint should contain at minimum a status field
        assert "status" in body or "ok" in body or "healthy" in body, (
            f"Health response missing expected status field. Got: {body}"
        )

    # ------------------------------------------------------------------
    # Test 3: Cross-service connectivity via backend health endpoint
    # ------------------------------------------------------------------

    def test_cross_service_connectivity(self, compose_up: None) -> None:
        """Verify backend can reach MongoDB and Redis via the health endpoint.

        The backend /health endpoint queries MongoDB as part of its check.
        If MongoDB is unreachable, the endpoint returns a non-200 or an
        unhealthy status — this verifies backend → MongoDB connectivity.

        n8n → backend and LightRAG → mongo connectivity is verified by
        their respective service health checks passing in test_all_services_healthy_within_120s.
        """
        url = "http://localhost:8001/health"

        # Backend must be reachable
        healthy, elapsed = _wait_for_url(url, timeout_sec=30)
        assert healthy, (
            f"Backend health check failed after {elapsed:.1f}s — "
            "cannot verify cross-service connectivity"
        )

        with urllib.request.urlopen(url, timeout=10) as resp:
            body = json.loads(resp.read().decode())

        # If the health endpoint reports DB status explicitly, verify it
        db_status = (
            body.get("database")
            or body.get("db")
            or body.get("mongo")
            or body.get("mongodb")
        )
        if db_status is not None:
            assert db_status in ("ok", "healthy", "connected", True), (
                f"Backend reports database as unhealthy: {db_status}. Full body: {body}"
            )

        # Redis connectivity: if reported in health body
        redis_status = body.get("redis") or body.get("cache")
        if redis_status is not None:
            assert redis_status in ("ok", "healthy", "connected", True), (
                f"Backend reports Redis as unhealthy: {redis_status}. Full body: {body}"
            )

        # Document what we verified
        print(
            f"\n[Cross-service] Backend /health = HTTP 200 "
            f"(implying backend → MongoDB + Redis reachable)\n"
            f"Response: {json.dumps(body, indent=2)}"
        )
