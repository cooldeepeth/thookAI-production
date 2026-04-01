"""
Tests verifying n8n security configuration in docker-compose files.

Covers:
- E2E-02: n8n not publicly accessible in production (ports removed, basic auth, internal network)
- E2E-09: Execution history pruning configured at 336h max age and 10000 max count
"""

import pathlib

import pytest
import yaml

# Resolve project root relative to this test file (backend/tests/test_n8n_security.py -> project root)
PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]
BASE_COMPOSE_PATH = PROJECT_ROOT / "docker-compose.yml"
PROD_COMPOSE_PATH = PROJECT_ROOT / "docker-compose.prod.yml"


def _load_yaml(path: pathlib.Path) -> dict:
    """Load and parse a YAML file, returning its content as a dict."""
    with open(path, "r") as f:
        return yaml.safe_load(f)


def _get_env_list(service: dict) -> list[str]:
    """Extract the environment list from a service definition.

    Docker Compose environment can be a list of 'KEY=VALUE' strings
    or a dict mapping KEY -> VALUE. This helper normalises to a list
    of 'KEY=VALUE' strings regardless of form.
    """
    env = service.get("environment", [])
    if isinstance(env, dict):
        return [f"{k}={v}" for k, v in env.items()]
    return env or []


class TestN8nSecurityConfig:
    """Verify n8n security hardening configuration in Docker Compose files."""

    # ------------------------------------------------------------------ #
    # Base docker-compose.yml tests (dev + prod shared config)            #
    # ------------------------------------------------------------------ #

    def test_n8n_block_env_access_in_node(self):
        """N8N_BLOCK_ENV_ACCESS_IN_NODE=true must be set in base n8n service.

        This prevents n8n workflows from reading arbitrary environment variables
        from the host, which could leak secrets.
        """
        compose = _load_yaml(BASE_COMPOSE_PATH)
        n8n_env = _get_env_list(compose["services"]["n8n"])
        assert "N8N_BLOCK_ENV_ACCESS_IN_NODE=true" in n8n_env, (
            "N8N_BLOCK_ENV_ACCESS_IN_NODE=true must be set in docker-compose.yml n8n service"
        )

    def test_n8n_execution_pruning_max_age(self):
        """EXECUTIONS_DATA_MAX_AGE=336 must be set to prevent unbounded execution log growth.

        336 hours (14 days) is the configured maximum age for execution history.
        """
        compose = _load_yaml(BASE_COMPOSE_PATH)
        n8n_env = _get_env_list(compose["services"]["n8n"])
        assert "EXECUTIONS_DATA_MAX_AGE=336" in n8n_env, (
            "EXECUTIONS_DATA_MAX_AGE=336 must be set in docker-compose.yml n8n service "
            "(E2E-09: execution history pruning)"
        )

    def test_n8n_execution_pruning_max_count(self):
        """EXECUTIONS_DATA_PRUNE_MAX_COUNT=10000 must be set.

        Caps total stored execution records regardless of age.
        """
        compose = _load_yaml(BASE_COMPOSE_PATH)
        n8n_env = _get_env_list(compose["services"]["n8n"])
        assert "EXECUTIONS_DATA_PRUNE_MAX_COUNT=10000" in n8n_env, (
            "EXECUTIONS_DATA_PRUNE_MAX_COUNT=10000 must be set in docker-compose.yml n8n service "
            "(E2E-09: execution history pruning)"
        )

    def test_n8n_worker_block_env_access(self):
        """n8n-worker must also have N8N_BLOCK_ENV_ACCESS_IN_NODE=true.

        Worker processes execute workflow code, so they need the same
        env-access restriction as the main n8n node.
        """
        compose = _load_yaml(BASE_COMPOSE_PATH)
        worker_env = _get_env_list(compose["services"]["n8n-worker"])
        assert "N8N_BLOCK_ENV_ACCESS_IN_NODE=true" in worker_env, (
            "N8N_BLOCK_ENV_ACCESS_IN_NODE=true must be set in docker-compose.yml n8n-worker service"
        )

    # ------------------------------------------------------------------ #
    # Production docker-compose.prod.yml tests                            #
    # ------------------------------------------------------------------ #

    def test_prod_n8n_no_public_ports(self):
        """In production, n8n must NOT publish any port to the host.

        Port 5678 must NOT appear in the merged ports list. The service
        should use expose: ["5678"] so backend can still reach it over
        the internal Docker network, but no external access is possible.
        """
        compose = _load_yaml(PROD_COMPOSE_PATH)
        n8n_service = compose["services"]["n8n"]
        ports = n8n_service.get("ports", [])
        assert ports == [] or ports is None, (
            f"docker-compose.prod.yml n8n must have no published ports, "
            f"but found: {ports} (E2E-02: n8n not publicly accessible)"
        )
        # Also confirm expose is set so internal access still works
        expose = n8n_service.get("expose", [])
        assert "5678" in [str(e) for e in expose], (
            "docker-compose.prod.yml n8n must expose port 5678 for internal Docker network access"
        )

    def test_prod_n8n_basic_auth_active(self):
        """In production, n8n basic auth must be enabled.

        N8N_BASIC_AUTH_ACTIVE=true adds a credential layer even within
        the internal network — defence in depth.
        """
        compose = _load_yaml(PROD_COMPOSE_PATH)
        n8n_env = _get_env_list(compose["services"]["n8n"])
        assert "N8N_BASIC_AUTH_ACTIVE=true" in n8n_env, (
            "N8N_BASIC_AUTH_ACTIVE=true must be set in docker-compose.prod.yml n8n service "
            "(E2E-02: n8n basic auth)"
        )

    def test_prod_internal_network_defined(self):
        """Production compose must define thookai-internal as an internal network.

        internal: true on a Docker bridge network means the Docker daemon
        will block all external routing, enforcing network isolation at the
        infrastructure level rather than only at the application level.
        """
        compose = _load_yaml(PROD_COMPOSE_PATH)
        networks = compose.get("networks", {})
        assert "thookai-internal" in networks, (
            "docker-compose.prod.yml must define a 'thookai-internal' network (E2E-02)"
        )
        internal_network = networks["thookai-internal"]
        assert internal_network.get("internal") is True, (
            "docker-compose.prod.yml thookai-internal network must have internal: true "
            "to block external routing (E2E-02: network isolation)"
        )
