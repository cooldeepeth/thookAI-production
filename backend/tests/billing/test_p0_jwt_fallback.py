"""TDD: JWT fallback secret bypass — BILL-06.

BUG: auth_utils.py line 129 uses `or "thook-dev-secret"` fallback.
A token signed with the fallback secret passes verification on any
deployment where JWT_SECRET_KEY is set to a real value.

This test MUST FAIL before the production fix is applied.
"""
import pytest
import jwt as pyjwt
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta, timezone


REAL_SECRET = "production-secret-key-abc123"
FALLBACK_SECRET = "thook-dev-secret"


def _make_token(secret: str, claims: dict = None) -> str:
    payload = claims or {
        "sub": "attacker_user_id",
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
    }
    return pyjwt.encode(payload, secret, algorithm="HS256")


class TestJWTFallbackSecretRejection:
    """Verify that the hardcoded fallback secret is not accepted."""

    def test_token_signed_with_fallback_rejected_when_real_secret_configured(self):
        """CRITICAL: A token signed with 'thook-dev-secret' must NOT pass
        verification when JWT_SECRET_KEY is set to a real production key."""
        from auth_utils import decode_token

        malicious_token = _make_token(FALLBACK_SECRET)

        mock_security = MagicMock()
        mock_security.jwt_secret_key = REAL_SECRET
        mock_security.jwt_algorithm = "HS256"

        with patch("auth_utils.settings.security", mock_security):
            with pytest.raises(Exception):  # JWTError or equivalent
                decode_token(malicious_token)

    def test_token_signed_with_correct_secret_accepted(self):
        """Positive case: token signed with the configured secret works."""
        from auth_utils import decode_token

        valid_token = _make_token(REAL_SECRET, {
            "sub": "legit_user_id",
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        })

        mock_security = MagicMock()
        mock_security.jwt_secret_key = REAL_SECRET
        mock_security.jwt_algorithm = "HS256"

        with patch("auth_utils.settings.security", mock_security):
            payload = decode_token(valid_token)
            assert payload["sub"] == "legit_user_id"

    def test_empty_jwt_secret_raises_error(self):
        """When JWT_SECRET_KEY is empty/None, must raise — not use fallback."""
        from auth_utils import decode_token

        token = _make_token(FALLBACK_SECRET)

        mock_security = MagicMock()
        mock_security.jwt_secret_key = ""
        mock_security.jwt_algorithm = "HS256"

        with patch("auth_utils.settings.security", mock_security):
            with pytest.raises(Exception):  # JWTError
                decode_token(token)

    def test_wrong_secret_rejected(self):
        """Token signed with arbitrary wrong secret is rejected."""
        from auth_utils import decode_token

        wrong_token = _make_token("some-random-wrong-secret")

        mock_security = MagicMock()
        mock_security.jwt_secret_key = REAL_SECRET
        mock_security.jwt_algorithm = "HS256"

        with patch("auth_utils.settings.security", mock_security):
            with pytest.raises(Exception):
                decode_token(wrong_token)
