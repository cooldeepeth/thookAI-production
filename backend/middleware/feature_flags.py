"""Feature flag dependency for gating non-wedge routes.

All flags live in `Settings.FEATURES_ENABLED` (see backend/config.py).
Attach `Depends(require_feature("flag_name"))` to a route or router; if the
flag is absent or False, the request returns 404.
"""

from fastapi import HTTPException

from config import get_settings


def require_feature(flag_name: str):
    def _check() -> None:
        settings = get_settings()
        if not settings.FEATURES_ENABLED.get(flag_name, False):
            raise HTTPException(status_code=404)
    return _check
