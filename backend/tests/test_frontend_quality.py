"""
Frontend quality static analysis tests.

These tests use Python's pathlib to read frontend source files and assert
that quality patterns exist. No browser or JS runtime is needed — pure
file-level grep-style assertions.

UI-01  Mobile sidebar responsive props and Tailwind classes
UI-02  Error boundary catches errors and shows recovery UI
UI-03  Empty states with CTAs in ContentLibrary, Campaigns, Templates
UI-04  401 redirect via ProtectedRoute and AuthContext logout
UI-05  Frontend pages have valid imports and no hardcoded URLs
"""
import re
from pathlib import Path

import pytest

# Resolve frontend source root relative to this test file:
# tests/ -> backend/ -> project_root/ -> frontend/src/
FRONTEND_ROOT = Path(__file__).parent.parent.parent / "frontend" / "src"
DASHBOARD_DIR = FRONTEND_ROOT / "pages" / "Dashboard"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _read(rel_path: str) -> str:
    """Read a file relative to FRONTEND_ROOT and return its contents."""
    path = FRONTEND_ROOT / rel_path
    assert path.exists(), f"Expected file not found: {path}"
    return path.read_text(encoding="utf-8")


def _contains_ci(content: str, *patterns: str) -> bool:
    """Return True if the content contains ANY of the patterns (case-insensitive)."""
    lower = content.lower()
    return any(p.lower() in lower for p in patterns)


# ===========================================================================
# UI-01  Mobile Sidebar
# ===========================================================================


class TestMobileSidebar:
    """UI-01: Sidebar.jsx must accept isOpen/onClose props and use responsive Tailwind classes."""

    @pytest.fixture(autouse=True)
    def sidebar_content(self):
        self.content = _read("pages/Dashboard/Sidebar.jsx")

    def test_accepts_is_open_prop(self):
        """Sidebar component signature must include isOpen prop."""
        assert "isOpen" in self.content, (
            "Sidebar.jsx must accept an 'isOpen' prop for mobile toggle support"
        )

    def test_accepts_on_close_prop(self):
        """Sidebar component signature must include onClose prop."""
        assert "onClose" in self.content, (
            "Sidebar.jsx must accept an 'onClose' prop to close the sidebar"
        )

    def test_has_responsive_tailwind_class(self):
        """Sidebar must use responsive Tailwind breakpoint classes (md:, lg:, xl:, etc.)."""
        has_responsive = bool(re.search(r"\b(md:|lg:|xl:|sm:)", self.content))
        assert has_responsive, (
            "Sidebar.jsx must contain responsive Tailwind breakpoint classes "
            "(e.g. 'md:hidden', 'md:translate-x-0', 'lg:block')"
        )

    def test_has_fixed_or_absolute_positioning(self):
        """Sidebar must use fixed or absolute positioning for mobile overlay."""
        has_position = "fixed" in self.content or "absolute" in self.content
        assert has_position, (
            "Sidebar.jsx must use 'fixed' or 'absolute' positioning for mobile overlay layout"
        )

    def test_has_click_handler_for_overlay(self):
        """Sidebar must have an onClick handler (for backdrop/overlay close action)."""
        assert "onClick" in self.content, (
            "Sidebar.jsx must have an onClick handler for the mobile overlay dismiss action"
        )


# ===========================================================================
# UI-02  Error Boundary
# ===========================================================================


class TestErrorBoundary:
    """UI-02: ErrorBoundary.jsx must be a class component with proper error catching and recovery UI."""

    @pytest.fixture(autouse=True)
    def boundary_content(self):
        self.content = _read("components/ErrorBoundary.jsx")

    def test_has_get_derived_state_from_error(self):
        """ErrorBoundary must implement getDerivedStateFromError lifecycle method."""
        assert "getDerivedStateFromError" in self.content, (
            "ErrorBoundary.jsx must define 'getDerivedStateFromError' static method"
        )

    def test_has_component_did_catch(self):
        """ErrorBoundary must implement componentDidCatch for error logging."""
        assert "componentDidCatch" in self.content, (
            "ErrorBoundary.jsx must define 'componentDidCatch' for error logging"
        )

    def test_has_has_error_state_flag(self):
        """ErrorBoundary must track error state via hasError flag."""
        assert "hasError" in self.content, (
            "ErrorBoundary.jsx must use a 'hasError' state property to track error state"
        )

    def test_has_window_location_reload_recovery(self):
        """ErrorBoundary must provide a reload-based recovery action."""
        assert "window.location.reload" in self.content, (
            "ErrorBoundary.jsx must call window.location.reload() for user-triggered recovery"
        )

    def test_error_boundary_imported_in_app(self):
        """App.js must import and use ErrorBoundary to wrap the application."""
        app_content = _read("App.js")
        assert "ErrorBoundary" in app_content, (
            "App.js must import and use ErrorBoundary to wrap the top-level application"
        )

        # Also verify it is used in JSX (not just imported)
        assert "<ErrorBoundary" in app_content, (
            "App.js must use <ErrorBoundary> as a JSX wrapper, not just import it"
        )


# ===========================================================================
# UI-03  Empty States
# ===========================================================================


class TestEmptyStates:
    """UI-03: ContentLibrary, Campaigns, and Templates must show friendly empty states."""

    def _assert_has_empty_state_text(self, filename: str):
        content = _read(f"pages/Dashboard/{filename}")
        has_empty_text = _contains_ci(
            content,
            "empty",
            "no content",
            "no templates",
            "no campaigns",
            "get started",
            "create your first",
            "nothing here",
            "not yet",
            "yet",
        )
        assert has_empty_text, (
            f"{filename} must display friendly empty state text when there is no data "
            "(e.g. 'No content yet', 'Create your first post', 'No campaigns yet')"
        )

    def _assert_has_cta(self, filename: str):
        content = _read(f"pages/Dashboard/{filename}")
        has_cta = (
            "button" in content.lower()
            or "Button" in content
            or "onClick" in content
            or "<Link" in content
            or 'href' in content
        )
        assert has_cta, (
            f"{filename} must contain a CTA element (Button, button, onClick handler, or Link) "
            "so users can take action from the empty state"
        )

    def test_content_library_has_empty_state_text(self):
        """ContentLibrary.jsx must display empty state text when no content exists."""
        self._assert_has_empty_state_text("ContentLibrary.jsx")

    def test_content_library_has_cta(self):
        """ContentLibrary.jsx must have a CTA element for users to create content."""
        self._assert_has_cta("ContentLibrary.jsx")

    def test_campaigns_has_empty_state_text(self):
        """Campaigns.jsx must display empty state text when no campaigns exist."""
        self._assert_has_empty_state_text("Campaigns.jsx")

    def test_campaigns_has_cta(self):
        """Campaigns.jsx must have a CTA element for users to create a campaign."""
        self._assert_has_cta("Campaigns.jsx")

    def test_templates_has_empty_state_text(self):
        """Templates.jsx must display empty state text when no templates exist."""
        self._assert_has_empty_state_text("Templates.jsx")

    def test_templates_has_cta(self):
        """Templates.jsx must have a CTA element for users to find or create templates."""
        self._assert_has_cta("Templates.jsx")


# ===========================================================================
# UI-04  Auth Redirect (401 handling)
# ===========================================================================


class TestAuthRedirect:
    """UI-04: AuthContext.jsx must manage tokens and App.js must guard routes with ProtectedRoute."""

    @pytest.fixture(autouse=True)
    def read_files(self):
        self.auth_content = _read("context/AuthContext.jsx")
        self.app_content = _read("App.js")

    def test_auth_context_uses_cookie_auth(self):
        """AuthContext must use cookie-based auth via apiFetch (session_token cookie)."""
        assert "apiFetch" in self.auth_content, (
            "AuthContext.jsx must use apiFetch (which sends session_token cookie via credentials: 'include')"
        )

    def test_auth_context_has_logout_function(self):
        """AuthContext must expose a logout function."""
        assert "logout" in self.auth_content, (
            "AuthContext.jsx must define a 'logout' function to clear auth state"
        )

    def test_auth_context_clears_session_on_logout(self):
        """AuthContext logout must call the backend logout endpoint to clear cookies."""
        assert "/api/auth/logout" in self.auth_content, (
            "AuthContext.jsx must call POST /api/auth/logout to clear session cookies"
        )

    def test_app_has_protected_route(self):
        """App.js must define or use a ProtectedRoute component."""
        assert "ProtectedRoute" in self.app_content, (
            "App.js must define or import a 'ProtectedRoute' component to guard dashboard routes"
        )

    def test_app_redirects_to_auth(self):
        """App.js must redirect unauthenticated users to /auth."""
        assert "/auth" in self.app_content, (
            "App.js must redirect unauthenticated users to the '/auth' route"
        )

    def test_app_uses_navigate_or_redirect(self):
        """App.js must use React Router's Navigate for redirects."""
        has_redirect = "Navigate" in self.app_content or "Redirect" in self.app_content
        assert has_redirect, (
            "App.js must use React Router's 'Navigate' (or 'Redirect') component "
            "to redirect unauthenticated users"
        )


# ===========================================================================
# UI-05  Frontend Page Integrity
# ===========================================================================


class TestFrontendPageIntegrity:
    """UI-05: Dashboard pages must have valid local imports and no hardcoded localhost URLs."""

    def _resolve_import_path(self, import_path: str, source_file: Path) -> Path | None:
        """
        Resolve a relative import path from a source file.
        Returns Path if resolvable to a local file, None otherwise.
        """
        if import_path.startswith("./") or import_path.startswith("../"):
            base = source_file.parent
            candidate = (base / import_path).resolve()
            # Try as-is, then with common extensions
            for suffix in ("", ".jsx", ".js", ".tsx", ".ts"):
                p = Path(str(candidate) + suffix)
                if p.exists():
                    return p
            # Try as directory with index file
            for index in ("index.jsx", "index.js", "index.tsx", "index.ts"):
                p = candidate / index
                if p.exists():
                    return p
        elif import_path.startswith("@/"):
            # @/ maps to frontend/src/
            rel = import_path[2:]  # strip "@/"
            candidate = (FRONTEND_ROOT / rel).resolve()
            for suffix in ("", ".jsx", ".js", ".tsx", ".ts"):
                p = Path(str(candidate) + suffix)
                if p.exists():
                    return p
            for index in ("index.jsx", "index.js", "index.tsx", "index.ts"):
                p = candidate / index
                if p.exists():
                    return p
        return None

    def test_dashboard_index_local_imports_resolve(self):
        """
        All local imports (relative or @/) in Dashboard/index.jsx must resolve
        to existing files on disk.
        """
        index_file = DASHBOARD_DIR / "index.jsx"
        assert index_file.exists(), f"Dashboard index.jsx not found at {index_file}"
        content = index_file.read_text(encoding="utf-8")

        # Extract import paths from: import X from "..."  or  import { X } from "..."
        import_paths = re.findall(r'from\s+["\']([^"\']+)["\']', content)
        unresolved = []

        for path_str in import_paths:
            if not (path_str.startswith("./") or path_str.startswith("../") or path_str.startswith("@/")):
                # Skip third-party packages (e.g. "react", "react-router-dom")
                continue
            resolved = self._resolve_import_path(path_str, index_file)
            if resolved is None:
                unresolved.append(path_str)

        assert unresolved == [], (
            f"Dashboard/index.jsx has unresolvable local imports: {unresolved}. "
            "These imports will cause runtime errors."
        )

    def test_app_js_local_imports_resolve(self):
        """
        All local imports in App.js must resolve to existing files on disk.
        """
        app_file = FRONTEND_ROOT / "App.js"
        assert app_file.exists(), f"App.js not found at {app_file}"
        content = app_file.read_text(encoding="utf-8")

        import_paths = re.findall(r'from\s+["\']([^"\']+)["\']', content)
        unresolved = []

        for path_str in import_paths:
            if not (path_str.startswith("./") or path_str.startswith("../") or path_str.startswith("@/")):
                continue
            resolved = self._resolve_import_path(path_str, app_file)
            if resolved is None:
                unresolved.append(path_str)

        assert unresolved == [], (
            f"App.js has unresolvable local imports: {unresolved}. "
            "These imports will cause runtime errors."
        )

    def test_no_hardcoded_localhost_in_dashboard_pages(self):
        """
        Dashboard page files must not contain raw hardcoded 'http://localhost' URLs.
        Fallback patterns like `|| 'http://localhost:8000'` in env var declarations are allowed.
        """
        jsx_files = list(DASHBOARD_DIR.glob("*.jsx"))
        assert jsx_files, f"No .jsx files found in {DASHBOARD_DIR}"

        violations = []
        for jsx_file in jsx_files:
            content = jsx_file.read_text(encoding="utf-8")
            # Find raw hardcoded localhost URLs NOT inside a fallback pattern
            # Allow:  process.env.X || "http://localhost..."
            # Allow:  import.meta.env.X || "http://localhost..."
            # Disallow: fetch("http://localhost:8000/api/...")
            lines = content.splitlines()
            for i, line in enumerate(lines, 1):
                if "http://localhost" in line:
                    # Check if it's a fallback pattern
                    is_fallback = bool(
                        re.search(
                            r'(?:process\.env\.|import\.meta\.env\.)\w+\s*\|\|\s*["\']http://localhost',
                            line,
                        )
                    )
                    if not is_fallback:
                        violations.append(f"{jsx_file.name}:{i}: {line.strip()}")

        assert violations == [], (
            "Hardcoded 'http://localhost' URLs found in Dashboard pages (not in env fallback patterns). "
            "Use process.env.REACT_APP_BACKEND_URL instead:\n"
            + "\n".join(violations)
        )

    def test_react_app_backend_url_usage_consistent(self):
        """
        Dashboard pages and key files must reference REACT_APP_BACKEND_URL or BACKEND_URL
        for API calls rather than inline URL strings.
        """
        key_files = [
            FRONTEND_ROOT / "context" / "AuthContext.jsx",
            FRONTEND_ROOT / "App.js",
        ]
        for f in key_files:
            if not f.exists():
                continue
            content = f.read_text(encoding="utf-8")
            # These files may not make API calls, so just verify no raw localhost
            lines = content.splitlines()
            for i, line in enumerate(lines, 1):
                if "http://localhost" in line:
                    is_fallback = bool(
                        re.search(
                            r'(?:process\.env\.|import\.meta\.env\.)\w+\s*\|\|\s*["\']http://localhost',
                            line,
                        )
                    )
                    assert is_fallback, (
                        f"{f.name} line {i} contains a hardcoded localhost URL outside a fallback pattern: "
                        f"{line.strip()}"
                    )
