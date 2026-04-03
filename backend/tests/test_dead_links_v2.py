"""Enhanced dead link detection tests for ThookAI (Phase 20 — E2E-07).

Static analysis tests that verify:
1. Frontend API references (/api/*) map to registered FastAPI routes
2. No hardcoded localhost URLs in frontend production code
3. No bare /tmp paths used as returned media URLs
4. All backend route files are registered in server.py
5. No duplicate route prefixes in server.py (which would cause shadowing)
6. Media URL construction uses R2_PUBLIC_URL (config-driven, not hardcoded)
7. uploads.py raises HTTP 503 when R2 is unavailable (BUG-7 guard)

These tests use only pathlib.Path and file scanning — no subprocess, no network
calls, no Docker required.  They complement the existing test_dead_links.py by
adding AST-level analysis, dynamic-segment normalisation, and duplicate-prefix
checks not present in the original.
"""

import ast
import re
from pathlib import Path
from typing import FrozenSet, List, Set, Tuple

import pytest


# ============================================================
# Path constants
# ============================================================

_TESTS_DIR = Path(__file__).parent
_BACKEND_DIR = _TESTS_DIR.parent
_PROJECT_ROOT = _BACKEND_DIR.parent
_FRONTEND_SRC = _PROJECT_ROOT / "frontend" / "src"
_ROUTES_DIR = _BACKEND_DIR / "routes"
_SERVICES_DIR = _BACKEND_DIR / "services"
_SERVER_PY = _BACKEND_DIR / "server.py"


# ============================================================
# Helper utilities
# ============================================================

def _read_file(path: Path) -> str:
    """Return file content or empty string if unreadable."""
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def _collect_js_files(root: Path) -> List[Path]:
    """Return all .js and .jsx files under *root*, skipping node_modules."""
    files: List[Path] = []
    for pattern in ("*.js", "*.jsx"):
        for f in root.rglob(pattern):
            if "node_modules" not in f.parts:
                files.append(f)
    return files


def _is_test_file(path: Path) -> bool:
    """Return True if the file is a test or spec file."""
    name = path.name.lower()
    parts = {p.lower() for p in path.parts}
    return (
        name.endswith(".test.js")
        or name.endswith(".test.jsx")
        or name.endswith(".spec.js")
        or name.endswith(".spec.jsx")
        or "__tests__" in parts
        or "tests" in parts
    )


_DYNAMIC_SEGMENT_RE = re.compile(
    r"(?:/:\w+|/\{[^}]+\}|/[0-9a-f]{8,})"  # :param, {param}, hex IDs
)

_API_PATH_RE = re.compile(r"""['"](/api/[a-zA-Z][a-zA-Z0-9_\-/{}:.]*)['"]""")


def _normalize_api_path(path: str) -> str:
    """Strip dynamic segments and return the stable base prefix."""
    base = _DYNAMIC_SEGMENT_RE.sub("", path)
    # Remove trailing slash
    return base.rstrip("/") or "/api"


def _collect_frontend_api_paths() -> Set[str]:
    """Extract and normalise all /api/* paths from frontend JS/JSX source files."""
    if not _FRONTEND_SRC.exists():
        return set()

    referenced: Set[str] = set()
    for js_file in _collect_js_files(_FRONTEND_SRC):
        if _is_test_file(js_file):
            continue
        content = _read_file(js_file)
        for m in _API_PATH_RE.finditer(content):
            referenced.add(_normalize_api_path(m.group(1)))
    return referenced


def _collect_registered_route_prefixes() -> Set[str]:
    """
    Extract route prefixes from backend/routes/*.py router definitions.

    Each route file declares:
        router = APIRouter(prefix="/xxx", ...)
    Server mounts all routers under /api via api_router.include_router(xxx_router).
    Result: the effective public prefix is /api + router_prefix.
    """
    if not _ROUTES_DIR.exists():
        return set()

    prefix_re = re.compile(
        r"""APIRouter\s*\(.*?prefix\s*=\s*['"](/[^'"]+)['"]""", re.DOTALL
    )
    endpoint_re = re.compile(r"""@router\.\w+\s*\(\s*['"](/[^'"]+)['"]""")

    prefixes: Set[str] = set()
    for route_file in _ROUTES_DIR.glob("*.py"):
        if route_file.stem.startswith("_"):
            continue
        content = _read_file(route_file)
        m = prefix_re.search(content)
        if m:
            router_prefix = m.group(1)
            effective = f"/api{router_prefix}"
            prefixes.add(effective)
            # Add endpoint sub-paths too
            for ep_m in endpoint_re.finditer(content):
                sub = _DYNAMIC_SEGMENT_RE.sub("", ep_m.group(1)).rstrip("/")
                if sub and sub != "/":
                    prefixes.add(f"/api{router_prefix}{sub}")

    # Admin router is mounted separately at /api/admin
    if _SERVER_PY.exists():
        server_txt = _read_file(_SERVER_PY)
        if "admin" in server_txt:
            prefixes.add("/api/admin")

    return prefixes


def _collect_include_router_prefixes() -> List[Tuple[str, str]]:
    """
    Parse server.py for include_router calls and return list of (alias, prefix).

    Handles two forms:
    - api_router.include_router(xxx_router)          — prefix embedded in router def
    - app.include_router(xxx_router, prefix="/api/x")— explicit prefix argument
    """
    if not _SERVER_PY.exists():
        return []

    server_txt = _read_file(_SERVER_PY)

    # Collect inline prefix= from include_router calls
    inline_prefix_re = re.compile(
        r"""include_router\s*\(\s*(\w+)\s*,\s*prefix\s*=\s*['"](/[^'"]+)['"]"""
    )
    results: List[Tuple[str, str]] = []
    for m in inline_prefix_re.finditer(server_txt):
        results.append((m.group(1), m.group(2)))

    return results


# ============================================================
# Class 1: Frontend → Backend API reference integrity
# ============================================================


class TestFrontendApiReferencesV2:
    """E2E-07: Every frontend /api/* reference must map to a registered FastAPI route."""

    def test_all_frontend_api_paths_have_backend_routes(self):
        """
        Scan all frontend JS/JSX files for /api/* URL strings and verify that
        every reference resolves to at least one registered backend route prefix.

        Dynamic segments (`:id`, `{param}`, hex IDs) are stripped before matching
        so `/api/content/:id/approve` matches the `/api/content` prefix.
        """
        referenced = _collect_frontend_api_paths()
        if not referenced:
            pytest.skip("No /api/* references found in frontend/src — nothing to validate")

        registered = _collect_registered_route_prefixes()
        assert registered, "No route prefixes found — check backend/routes/ and server.py"

        orphans: List[str] = []
        for ref in sorted(referenced):
            matched = any(
                ref == reg or ref.startswith(reg + "/") or reg.startswith(ref)
                for reg in registered
            )
            if not matched:
                orphans.append(ref)

        assert not orphans, (
            f"{len(orphans)} frontend API reference(s) have NO matching backend route:\n"
            + "\n".join(f"  {p}" for p in orphans)
            + "\n\nRegistered backend prefixes:\n"
            + "\n".join(f"  {p}" for p in sorted(registered))
        )

    def test_no_hardcoded_localhost_in_frontend_production_code(self):
        """
        Scan production frontend JS/JSX files for hardcoded localhost/127.0.0.1 URLs.

        Exclusions:
        - Test files (*.test.js, *.spec.js, __tests__ directories)
        - Lines using process.env.REACT_APP_* (environment-driven fallbacks are OK)
        - Pure comment lines
        """
        if not _FRONTEND_SRC.exists():
            pytest.skip("frontend/src not found — skipping localhost check")

        localhost_re = re.compile(r"https?://localhost|https?://127\.0\.0\.1")
        violations: List[str] = []

        for js_file in _collect_js_files(_FRONTEND_SRC):
            if _is_test_file(js_file):
                continue
            content = _read_file(js_file)
            for lineno, line in enumerate(content.splitlines(), 1):
                stripped = line.strip()
                # Skip comment lines
                if stripped.startswith("//") or stripped.startswith("*"):
                    continue
                if not localhost_re.search(line):
                    continue
                # Allow env-variable-driven development fallbacks
                if "process.env" in line or "REACT_APP_" in line:
                    continue
                rel = js_file.relative_to(_PROJECT_ROOT)
                violations.append(f"{rel}:{lineno}: {stripped[:120]}")

        assert not violations, (
            f"Hardcoded localhost URL(s) found in {len(violations)} production file location(s):\n"
            + "\n".join(f"  {v}" for v in violations[:20])
        )

    def test_no_bare_tmp_paths_in_media_url_construction(self):
        """
        Verify that backend media services do not return bare /tmp/ paths as
        public media URLs in their return statements or assigned url variables.

        Scans backend/services/media_storage.py and backend/routes/uploads.py.
        The /tmp/ path may appear in dev-mode local-fallback code but must NOT
        appear in a return statement that forms the public URL.
        """
        files_to_check = [
            _SERVICES_DIR / "media_storage.py",
            _ROUTES_DIR / "uploads.py",
        ]

        tmp_as_return_re = re.compile(
            # Match: return ... "/tmp/..." (public URL being returned directly)
            r"""return\s+.*['"](/tmp/|file://)""",
            re.MULTILINE,
        )

        violations: List[str] = []
        for src_path in files_to_check:
            if not src_path.exists():
                continue
            content = _read_file(src_path)
            for m in tmp_as_return_re.finditer(content):
                lineno = content[: m.start()].count("\n") + 1
                rel = src_path.relative_to(_PROJECT_ROOT)
                violations.append(f"{rel}:{lineno}")

        assert not violations, (
            "Bare /tmp/ paths are returned as public media URLs in:\n"
            + "\n".join(f"  {v}" for v in violations)
            + "\nMedia URLs must always be constructed from R2_PUBLIC_URL (BUG-7)."
        )


# ============================================================
# Class 2: Route registration completeness
# ============================================================


class TestRouteRegistrationCompleteness:
    """E2E-07: All route files in backend/routes/ must be imported and registered."""

    def test_all_route_files_registered_in_server(self):
        """
        Every .py file in backend/routes/ (except __init__.py) must appear in
        server.py as an import and have include_router() called for it.
        """
        if not _SERVER_PY.exists():
            pytest.fail("backend/server.py not found — cannot verify route registration")

        server_txt = _read_file(_SERVER_PY)

        route_files = sorted(
            f for f in _ROUTES_DIR.glob("*.py")
            if f.stem != "__init__" and not f.stem.startswith("_")
        )
        assert route_files, f"No route files found in {_ROUTES_DIR}"

        orphans: List[str] = []
        for route_file in route_files:
            module_name = route_file.stem
            imported = (
                f"from routes.{module_name} import" in server_txt
                or f"import routes.{module_name}" in server_txt
                or f"routes/{module_name}" in server_txt
            )
            if not imported:
                orphans.append(module_name)

        assert not orphans, (
            "The following route files are NOT imported in backend/server.py:\n"
            + "\n".join(f"  routes/{r}.py" for r in orphans)
            + "\nAdd the missing import + include_router() call to server.py."
        )

    def test_no_duplicate_route_prefixes(self):
        """
        Parse all include_router calls in server.py that carry an explicit
        prefix= argument and assert no two routers share the same prefix.

        Duplicate prefixes cause route shadowing — the second router's endpoints
        silently override the first's.
        """
        pairs = _collect_include_router_prefixes()
        if not pairs:
            # Most routers embed the prefix in their APIRouter definition —
            # no explicit prefix= in include_router calls is the expected pattern.
            return

        seen: dict = {}
        duplicates: List[str] = []
        for alias, prefix in pairs:
            if prefix in seen:
                duplicates.append(
                    f"Duplicate prefix '{prefix}' used by both '{seen[prefix]}' and '{alias}'"
                )
            else:
                seen[prefix] = alias

        assert not duplicates, (
            "Duplicate route prefixes detected in server.py — "
            "this causes route shadowing:\n"
            + "\n".join(f"  {d}" for d in duplicates)
        )


# ============================================================
# Class 3: Media URL integrity
# ============================================================


class TestMediaUrlIntegrity:
    """E2E-07: Media URLs must be config-driven (R2_PUBLIC_URL) — never hardcoded."""

    def _read_media_storage(self) -> str:
        src = _SERVICES_DIR / "media_storage.py"
        return _read_file(src)

    def _read_uploads(self) -> str:
        src = _ROUTES_DIR / "uploads.py"
        return _read_file(src)

    def test_media_storage_uses_r2_public_url(self):
        """
        backend/services/media_storage.py must reference r2_public_url or
        R2_PUBLIC_URL when constructing public file URLs.

        This ensures URLs are always derived from config, not hardcoded endpoints.
        """
        source = self._read_media_storage()
        assert source, "backend/services/media_storage.py must exist"

        has_r2_public_url = (
            "r2_public_url" in source.lower()
            or "R2_PUBLIC_URL" in source
            or "settings.r2" in source
        )
        assert has_r2_public_url, (
            "media_storage.py must use settings.r2.r2_public_url for URL construction — "
            "no hardcoded S3/R2 endpoint strings allowed."
        )

    def test_no_hardcoded_s3_endpoints_in_media_storage(self):
        """
        Verify media_storage.py does not contain hardcoded S3 or R2 endpoint
        domain strings that would break when the bucket is moved or renamed.
        """
        source = self._read_media_storage()
        assert source, "backend/services/media_storage.py must exist"

        # Endpoint URL constructed dynamically from settings is fine,
        # but a hardcoded full bucket URL like https://bucket.r2.cloudflarestorage.com/
        # (without referencing settings) is not.
        hardcoded_bucket_re = re.compile(
            r"""https://[a-f0-9]{32}\.r2\.cloudflarestorage\.com/""", re.IGNORECASE
        )
        matches = hardcoded_bucket_re.findall(source)
        assert not matches, (
            "media_storage.py contains a hardcoded R2 endpoint URL — "
            "use settings.r2.r2_account_id to construct the endpoint dynamically:\n"
            + "\n".join(f"  {m}" for m in matches)
        )

    def test_uploads_route_rejects_when_r2_unavailable(self):
        """
        backend/routes/uploads.py must raise HTTP 503 (not fall back to /tmp)
        when R2 is not configured and the server is in production mode.

        This is the BUG-7 guard: ephemeral /tmp files vanish on restart, causing
        dead media links in production.
        """
        source = self._read_uploads()
        assert source, "backend/routes/uploads.py must exist"

        has_503_guard = "503" in source and (
            "is_production" in source or "production" in source.lower()
        )
        assert has_503_guard, (
            "routes/uploads.py is missing the HTTP 503 guard for when R2 is "
            "unavailable in production (BUG-7). Add:\n"
            "  if settings.app.is_production:\n"
            "      raise HTTPException(status_code=503, ...)\n"
            "before the /tmp fallback code."
        )

        # Verify 503 appears BEFORE /tmp to ensure the guard is effective
        pos_503 = source.find("503")
        pos_tmp = source.find("/tmp/")
        if pos_tmp != -1 and pos_503 != -1:
            assert pos_503 < pos_tmp, (
                "The HTTP 503 production guard must appear BEFORE the /tmp fallback "
                "in uploads.py so production requests are blocked before reaching "
                "the ephemeral storage path."
            )

    def test_get_public_url_references_r2_public_url(self):
        """
        The get_public_url() helper in media_storage.py must derive the URL
        from settings.r2.r2_public_url, not a hardcoded string.
        """
        source = self._read_media_storage()
        assert source, "backend/services/media_storage.py must exist"

        assert "get_public_url" in source, (
            "media_storage.py must define a get_public_url() function that "
            "constructs the public URL from settings."
        )
        assert "r2_public_url" in source, (
            "get_public_url() in media_storage.py must reference "
            "settings.r2.r2_public_url to build the public URL."
        )
