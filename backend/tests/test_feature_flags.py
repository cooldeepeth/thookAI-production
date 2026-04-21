"""Feature flag guard tests.

Verifies that every route file listed in the wedge spec returns HTTP 404
when its feature flag is False (the default). One endpoint per flagged file.

The lru_cache on get_settings() returns a fresh Settings instance whose
FEATURES_ENABLED defaults match `.planning/WEDGE.md`, so these tests run
against the production default state without any mocking.
"""
from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from config import get_settings

pytestmark = pytest.mark.asyncio


# One endpoint per flagged route file. Keep this list aligned with the
# guards added in backend/routes/ and the flag names in config.py.
FLAGGED_ENDPOINTS: list[tuple[str, str, str, str]] = [
    # (route_file, flag_name, http_method, url)
    ("agency.py", "feature_agency_workspace", "GET", "/api/agency/workspaces"),
    ("analytics.py", "feature_strategy_dashboard", "GET", "/api/analytics/overview"),
    ("auth_social.py", "platform_x", "GET", "/api/auth/x"),
    ("campaigns.py", "feature_campaigns", "GET", "/api/campaigns"),
    ("n8n_bridge.py", "feature_repurpose", "POST", "/api/n8n/trigger/noop"),
    ("obsidian.py", "feature_repurpose", "GET", "/api/obsidian/config"),
    ("repurpose.py", "feature_repurpose", "GET", "/api/content/repurpose/suggestions"),
    ("strategy.py", "feature_strategy_dashboard", "GET", "/api/strategy"),
    ("templates.py", "feature_templates", "GET", "/api/templates"),
    ("viral.py", "feature_viral_card", "POST", "/api/viral/predict"),
    ("viral_card.py", "feature_viral_card", "GET", "/api/viral-card/does-not-exist"),
    ("admin.py", "feature_admin_panel", "GET", "/api/admin/stats/overview"),
    ("notifications.py", "feature_admin_panel", "GET", "/api/notifications"),
]


@pytest.fixture(scope="module")
def app():
    """Import the FastAPI app once per module (heavy to construct)."""
    from server import app as fastapi_app
    return fastapi_app


def test_all_target_flags_default_to_false():
    """Sanity: every flag used by a guard is False in default settings.

    If this fails, the test assertions below are meaningless.
    """
    settings = get_settings()
    for _file, flag, _method, _url in FLAGGED_ENDPOINTS:
        assert settings.FEATURES_ENABLED.get(flag) is False, (
            f"Flag {flag!r} is not False by default — cannot verify 404 guard "
            f"for {_file}"
        )


@pytest.mark.parametrize(
    "route_file, flag_name, method, url",
    FLAGGED_ENDPOINTS,
    ids=[f"{f}:{url}" for f, _flag, _m, url in FLAGGED_ENDPOINTS],
)
async def test_flagged_route_returns_404_when_disabled(
    app, route_file, flag_name, method, url
):
    """Each flagged endpoint must 404 when its feature flag is False."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        if method == "GET":
            resp = await client.get(url)
        elif method == "POST":
            resp = await client.post(url, json={})
        else:
            pytest.fail(f"Unsupported method {method}")

    assert resp.status_code == 404, (
        f"{route_file} {method} {url} (flag={flag_name}) "
        f"returned {resp.status_code} instead of 404: {resp.text[:200]}"
    )
