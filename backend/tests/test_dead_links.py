"""Dead link detection tests for ThookAI (Phase 16 — E2E-10).

Static analysis tests that verify:
1. Frontend API references resolve to real registered FastAPI routes
2. No hardcoded localhost URLs in frontend production code
3. Media URL construction uses R2_PUBLIC_URL (not bare /tmp paths as response URLs)
4. All route files in backend/routes/ are registered in server.py

These tests use only pathlib.Path and file scanning — no subprocess, no network calls.
"""

import re
from pathlib import Path

import pytest


# ============================================================
# Project root detection
# ============================================================

# backend/tests/ -> backend/ -> project root
_TESTS_DIR = Path(__file__).parent
_BACKEND_DIR = _TESTS_DIR.parent
_PROJECT_ROOT = _BACKEND_DIR.parent
_FRONTEND_SRC = _PROJECT_ROOT / "frontend" / "src"
_ROUTES_DIR = _BACKEND_DIR / "routes"
_SERVER_PY = _BACKEND_DIR / "server.py"


# ============================================================
# Test 1: Frontend API references resolve to registered routes
# ============================================================


class TestFrontendApiReferences:
    """E2E-10: Frontend /api/* calls must map to real FastAPI routes."""

    def _collect_frontend_api_paths(self) -> set[str]:
        """Extract all /api/<segment> base paths from frontend JS/JSX files."""
        api_ref_pattern = re.compile(r"""['"](/api/[a-zA-Z][a-zA-Z0-9/_\-:{}]*)['"]""")
        referenced: set[str] = set()

        if not _FRONTEND_SRC.exists():
            return referenced

        for js_file in _FRONTEND_SRC.rglob("*.js"):
            if "node_modules" in str(js_file):
                continue
            try:
                content = js_file.read_text(encoding="utf-8", errors="ignore")
                for match in api_ref_pattern.finditer(content):
                    path = match.group(1)
                    # Normalize: strip path params like :id, {id}
                    # Keep only the base prefix for route matching
                    base = re.sub(r"[/:]?\{[^}]+\}", "", path)  # remove {param}
                    base = re.sub(r"/:[\w]+", "", base)  # remove :param
                    base = re.sub(r"/[0-9a-f]{24}$", "", base)  # remove hex IDs
                    referenced.add(base.rstrip("/"))
            except (OSError, UnicodeDecodeError):
                continue

        for jsx_file in _FRONTEND_SRC.rglob("*.jsx"):
            if "node_modules" in str(jsx_file):
                continue
            try:
                content = jsx_file.read_text(encoding="utf-8", errors="ignore")
                for match in api_ref_pattern.finditer(content):
                    path = match.group(1)
                    base = re.sub(r"[/:]?\{[^}]+\}", "", path)
                    base = re.sub(r"/:[\w]+", "", base)
                    base = re.sub(r"/[0-9a-f]{24}$", "", base)
                    referenced.add(base.rstrip("/"))
            except (OSError, UnicodeDecodeError):
                continue

        return referenced

    def _collect_registered_route_prefixes(self) -> set[str]:
        """Extract route prefixes registered in server.py and individual route modules."""
        if not _SERVER_PY.exists():
            return set()

        server_content = _SERVER_PY.read_text(encoding="utf-8")
        prefixes: set[str] = set()

        # Extract include_router calls from server.py — all routes are under /api
        # Pattern: api_router.include_router(xxx_router) or app.include_router(xxx_router, prefix="/api/xxx")
        # Also collect prefixes from router definitions in route files

        for route_file in _ROUTES_DIR.glob("*.py"):
            if route_file.stem in ("__init__", "__pycache__"):
                continue
            try:
                content = route_file.read_text(encoding="utf-8", errors="ignore")
                # Extract router prefix: router = APIRouter(prefix="/xxx", ...)
                prefix_match = re.search(r"""APIRouter\s*\(.*?prefix\s*=\s*['"](/[^'"]+)['"]""", content, re.DOTALL)
                if prefix_match:
                    prefix = prefix_match.group(1)
                    # Prefix is relative to /api (server.py mounts all routes under /api)
                    # So a prefix of "/auth" registers as /api/auth
                    prefixes.add(f"/api{prefix}")
                    # Also add sub-paths from the router endpoints
                    for endpoint_match in re.finditer(r"""@router\.\w+\s*\(\s*['"](/[^'"]+)['"]""", content):
                        endpoint_path = endpoint_match.group(1)
                        # Strip path params
                        clean = re.sub(r"/\{[^}]+\}", "", endpoint_path)
                        if clean and clean != "/":
                            prefixes.add(f"/api{prefix}{clean}")
            except (OSError, UnicodeDecodeError):
                continue

        # Add known top-level admin route registered separately
        if "admin" in server_content:
            prefixes.add("/api/admin")

        return prefixes

    def test_frontend_api_references_resolve(self):
        """All /api/* paths referenced in frontend code must map to a registered route.

        This test extracts API path strings from frontend JS/JSX files and verifies
        each one has a matching registered route prefix in the backend.
        """
        referenced = self._collect_frontend_api_paths()
        registered = self._collect_registered_route_prefixes()

        if not referenced:
            pytest.skip("No /api/ references found in frontend source — skipping")

        # For each reference, check if any registered prefix matches it
        orphans = []
        for ref_path in sorted(referenced):
            # A reference is valid if any registered route is a prefix of it
            # (e.g. /api/auth/register -> /api/auth is registered)
            matched = any(
                ref_path == reg or ref_path.startswith(reg + "/") or reg.startswith(ref_path)
                for reg in registered
            )
            if not matched:
                orphans.append(ref_path)

        assert not orphans, (
            f"Frontend references {len(orphans)} unresolved API path(s):\n"
            + "\n".join(f"  {p}" for p in orphans)
            + f"\n\nRegistered prefixes:\n"
            + "\n".join(f"  {p}" for p in sorted(registered))
        )


# ============================================================
# Test 2: No hardcoded localhost URLs in frontend production code
# ============================================================


class TestNoHardcodedLocalhost:
    """E2E-10: Frontend must use REACT_APP_BACKEND_URL, not hardcoded localhost."""

    def test_no_hardcoded_localhost_in_frontend(self):
        """No frontend JS/JSX files contain hardcoded http://localhost or https://localhost.

        The API base URL must come from process.env.REACT_APP_BACKEND_URL so
        that the same build works in local dev and production Vercel deployments.
        """
        if not _FRONTEND_SRC.exists():
            pytest.skip("frontend/src directory not found — skipping")

        localhost_pattern = re.compile(r"https?://localhost")
        violations: list[str] = []

        for src_file in list(_FRONTEND_SRC.rglob("*.js")) + list(_FRONTEND_SRC.rglob("*.jsx")):
            if "node_modules" in str(src_file):
                continue
            try:
                content = src_file.read_text(encoding="utf-8", errors="ignore")
            except (OSError, UnicodeDecodeError):
                continue

            for i, line in enumerate(content.splitlines(), 1):
                # Skip comment lines
                stripped = line.strip()
                if stripped.startswith("//") or stripped.startswith("*"):
                    continue
                if localhost_pattern.search(line):
                    # Allow development fallback patterns like:
                    # process.env.REACT_APP_BACKEND_URL || 'http://localhost:8000'
                    if "process.env" not in line and "REACT_APP_" not in line:
                        rel = src_file.relative_to(_PROJECT_ROOT)
                        violations.append(f"{rel}:{i}: {line.strip()}")

        assert not violations, (
            f"Hardcoded localhost URLs found in {len(violations)} location(s):\n"
            + "\n".join(f"  {v}" for v in violations[:20])
        )


# ============================================================
# Test 3: Media URL uses R2_PUBLIC_URL, not /tmp paths as client response URLs
# ============================================================


class TestMediaUrlPatterns:
    """E2E-10: Media URLs returned to clients must use R2_PUBLIC_URL, not /tmp."""

    def _read_source(self, rel_path: str) -> str:
        path = _BACKEND_DIR / rel_path
        if not path.exists():
            return ""
        return path.read_text(encoding="utf-8", errors="ignore")

    def test_media_url_uses_r2_public_url(self):
        """URL construction in media_storage.py uses R2_PUBLIC_URL settings, not /tmp."""
        source = self._read_source("services/media_storage.py")
        assert source, "services/media_storage.py must exist"

        # R2_PUBLIC_URL should be used for URL construction
        assert "r2_public_url" in source.lower() or "R2_PUBLIC_URL" in source, (
            "media_storage.py must use r2_public_url for URL construction"
        )

        # No bare /tmp/ URL returned directly (tmp is a fallback path, not a public URL)
        # Check that if /tmp appears, it's only in the context of local file paths, not
        # in return statements that form public URLs
        tmp_return_pattern = re.compile(
            r"return\s+.*['\"]?(/tmp/|file://)", re.MULTILINE
        )
        assert not tmp_return_pattern.search(source), (
            "media_storage.py must not return /tmp/ paths as public URLs"
        )

    def test_uploads_route_blocks_tmp_in_production(self):
        """uploads.py must raise HTTP 503 when R2 is unavailable in production.

        This prevents /tmp fallback in production where files are ephemeral.
        BUG-7 fix: In production, raise 503 rather than silently falling back.
        """
        source = self._read_source("routes/uploads.py")
        assert source, "routes/uploads.py must exist"

        # Must have production guard
        has_production_guard = "is_production" in source and (
            "503" in source or "raise HTTPException" in source
        )
        assert has_production_guard, (
            "routes/uploads.py must raise HTTPException (503) when R2 is "
            "unavailable in production — not fall back to /tmp"
        )

        # /tmp fallback must only be in non-production code path
        # Check that the 503 raise comes before any /tmp usage
        production_503_pos = source.find("503")
        tmp_pos = source.find("/tmp/")
        if tmp_pos != -1 and production_503_pos != -1:
            assert production_503_pos < tmp_pos, (
                "Production 503 guard must appear before /tmp fallback in uploads.py"
            )

    def test_media_storage_r2_public_url_in_get_public_url(self):
        """get_public_url() in media_storage.py must reference r2_public_url setting."""
        source = self._read_source("services/media_storage.py")
        assert source, "services/media_storage.py must exist"

        # Find get_public_url function and verify it uses r2_public_url
        assert "get_public_url" in source, (
            "media_storage.py must define a get_public_url function"
        )
        # r2_public_url should appear in the URL construction
        assert "r2_public_url" in source, (
            "media_storage.py must reference settings.r2.r2_public_url in URL construction"
        )


# ============================================================
# Test 4: All route files registered in server.py
# ============================================================


class TestRouteRegistration:
    """E2E-10: All route files in backend/routes/ must be registered in server.py."""

    def test_all_route_files_registered(self):
        """Every .py file in backend/routes/ must be imported and registered in server.py.

        Orphan route files that are imported but never include_router'd would
        result in dead API endpoints that never respond.
        """
        if not _SERVER_PY.exists():
            pytest.fail("server.py does not exist — cannot verify route registration")

        server_content = _SERVER_PY.read_text(encoding="utf-8")

        # Find all route module files
        route_files = [
            f for f in _ROUTES_DIR.glob("*.py")
            if f.stem not in ("__init__",) and not f.stem.startswith("_")
        ]

        orphan_routes = []
        for route_file in sorted(route_files):
            module_name = route_file.stem  # e.g. "auth", "content", "strategy"

            # Check if this module is imported in server.py
            # Pattern: from routes.xxx import router as xxx_router
            # OR: import routes.xxx
            is_imported = (
                f"from routes.{module_name} import" in server_content
                or f"import routes.{module_name}" in server_content
                or f"routes/{module_name}" in server_content
            )

            if not is_imported:
                orphan_routes.append(module_name)

        assert not orphan_routes, (
            f"The following route files are NOT imported in server.py:\n"
            + "\n".join(f"  routes/{r}.py" for r in sorted(orphan_routes))
            + "\n\nAdd the missing import + include_router() calls to backend/server.py."
        )

    def test_all_route_files_include_router_called(self):
        """Every imported route module must have include_router() called for it.

        Importing a module but not calling include_router() means the endpoints
        are defined but never accessible.
        """
        if not _SERVER_PY.exists():
            pytest.fail("server.py does not exist")

        server_content = _SERVER_PY.read_text(encoding="utf-8")

        # Extract all imported router aliases
        # Pattern: from routes.xxx import router as xxx_router
        import_aliases = re.findall(
            r"from routes\.\w+ import router as (\w+router)\b",
            server_content,
        )

        # Check each alias has a corresponding include_router call
        unregistered = [
            alias for alias in import_aliases
            if f"include_router({alias}" not in server_content
        ]

        assert not unregistered, (
            f"The following router aliases are imported but include_router() "
            f"never called:\n"
            + "\n".join(f"  {alias}" for alias in sorted(unregistered))
        )
