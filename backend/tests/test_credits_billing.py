"""Tests for ThookAI credit system and starter tier restrictions.

Covers:
- Atomic credit deduction (find_one_and_update)
- Concurrent safety (no negative balance)
- Starter hard caps (video=2, carousel=5)
- Starter platform restriction (LinkedIn only, HTTP 402 for others)
- add_credits utility
- build_plan_preview calculation
"""
import asyncio
import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone


# ---------------------------------------------------------------------------
# Helper: minimal user dict
# ---------------------------------------------------------------------------

def make_user(user_id: str, credits: int = 100, tier: str = "starter") -> dict:
    return {
        "user_id": user_id,
        "email": f"{user_id}@test.com",
        "subscription_tier": tier,
        "credits": credits,
    }


# ---------------------------------------------------------------------------
# Unit tests for deduct_credits (mocked DB)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_deduct_credits_success():
    """Successful deduction returns success=True and correct new_balance."""
    from services.credits import deduct_credits, CreditOperation

    user_id = f"user_{uuid.uuid4().hex[:8]}"
    user = make_user(user_id, credits=100)
    updated_user = {**user, "credits": 90}  # AFTER deduction of 10

    mock_db = MagicMock()
    mock_db.users.find_one = AsyncMock(return_value=user)
    mock_db.users.find_one_and_update = AsyncMock(return_value=updated_user)
    mock_db.credit_transactions.count_documents = AsyncMock(return_value=0)
    mock_db.credit_transactions.insert_one = AsyncMock(return_value=MagicMock())

    # credits.py uses `from database import db` inside functions, so patch database.db
    with patch("database.db", mock_db):
        result = await deduct_credits(user_id, CreditOperation.CONTENT_CREATE)

    assert result["success"] is True
    assert result["new_balance"] == 90
    assert result["credits_used"] == 10
    assert result["operation"] == "CONTENT_CREATE"

    # Verify transaction was recorded
    mock_db.credit_transactions.insert_one.assert_called_once()
    tx = mock_db.credit_transactions.insert_one.call_args[0][0]
    assert tx["type"] == "deduction"
    assert tx["amount"] == 10
    assert tx["balance_after"] == 90


@pytest.mark.asyncio
async def test_deduct_credits_insufficient():
    """Insufficient credits returns success=False with descriptive error."""
    from services.credits import deduct_credits, CreditOperation

    user_id = f"user_{uuid.uuid4().hex[:8]}"
    user = make_user(user_id, credits=5)

    mock_db = MagicMock()
    mock_db.users.find_one = AsyncMock(return_value=user)
    # find_one_and_update returns None when credits < amount (filter not matched)
    mock_db.users.find_one_and_update = AsyncMock(return_value=None)
    mock_db.credit_transactions.count_documents = AsyncMock(return_value=0)

    with patch("database.db", mock_db):
        result = await deduct_credits(user_id, CreditOperation.CONTENT_CREATE)  # costs 10

    assert result["success"] is False
    assert "Not enough credits" in result["error"]
    assert result["available"] == 5
    assert result["required"] == 10


@pytest.mark.asyncio
async def test_deduct_credits_atomic_concurrent():
    """Concurrent deductions on exactly enough credits for ONE operation.

    Only one should succeed; balance must never go negative.
    Uses asyncio.gather to fire both calls simultaneously.
    """
    from services.credits import deduct_credits, CreditOperation

    user_id = f"user_{uuid.uuid4().hex[:8]}"
    # User has exactly 10 credits — enough for exactly one CONTENT_CREATE (costs 10)
    user = make_user(user_id, credits=10)
    updated_user = {**user, "credits": 0}  # AFTER the ONE successful deduction

    # Track call count to simulate atomic DB behavior:
    # First call matches filter (credits=10 >= 10), returns updated doc
    # Second call finds credits=0 < 10, returns None
    call_count = 0

    async def atomic_update_side_effect(filter_doc, update_doc, return_document=None):
        nonlocal call_count
        call_count += 1
        # Only first call "wins" the atomic update
        if call_count == 1:
            return updated_user
        return None  # Simulate second concurrent call losing the race

    mock_db = MagicMock()
    mock_db.users.find_one = AsyncMock(return_value=user)
    mock_db.users.find_one_and_update = AsyncMock(side_effect=atomic_update_side_effect)
    mock_db.credit_transactions.count_documents = AsyncMock(return_value=0)
    mock_db.credit_transactions.insert_one = AsyncMock(return_value=MagicMock())

    with patch("database.db", mock_db):
        results = await asyncio.gather(
            deduct_credits(user_id, CreditOperation.CONTENT_CREATE),
            deduct_credits(user_id, CreditOperation.CONTENT_CREATE),
        )

    successes = [r for r in results if r["success"]]
    failures = [r for r in results if not r["success"]]

    assert len(successes) == 1, f"Expected exactly 1 success, got {len(successes)}: {results}"
    assert len(failures) == 1, f"Expected exactly 1 failure, got {len(failures)}: {results}"

    # Winning result shows balance = 0, never negative
    winning_balance = successes[0]["new_balance"]
    assert winning_balance >= 0, f"Balance went negative: {winning_balance}"


@pytest.mark.asyncio
async def test_starter_hard_cap_video():
    """Starter user who has hit 2 video generations is blocked with HTTP 402-style error."""
    from services.credits import deduct_credits, CreditOperation

    user_id = f"user_{uuid.uuid4().hex[:8]}"
    user = make_user(user_id, credits=500, tier="starter")

    mock_db = MagicMock()
    mock_db.users.find_one = AsyncMock(return_value=user)
    # Simulate 2 existing VIDEO_GENERATE transactions (hard cap = 2)
    mock_db.credit_transactions.count_documents = AsyncMock(return_value=2)

    with patch("database.db", mock_db):
        result = await deduct_credits(user_id, CreditOperation.VIDEO_GENERATE)

    assert result["success"] is False
    assert "limited to 2 video" in result["error"].lower()
    assert result.get("upgrade_required") is True


@pytest.mark.asyncio
async def test_starter_hard_cap_carousel():
    """Starter user who has hit 5 carousel generations is blocked."""
    from services.credits import deduct_credits, CreditOperation

    user_id = f"user_{uuid.uuid4().hex[:8]}"
    user = make_user(user_id, credits=500, tier="starter")

    mock_db = MagicMock()
    mock_db.users.find_one = AsyncMock(return_value=user)
    # count_documents returns 5 (carousel cap = 5)
    mock_db.credit_transactions.count_documents = AsyncMock(return_value=5)

    with patch("database.db", mock_db):
        result = await deduct_credits(user_id, CreditOperation.CAROUSEL_GENERATE)

    assert result["success"] is False
    assert "limited to 5 carousel" in result["error"].lower()
    assert result.get("upgrade_required") is True


# ---------------------------------------------------------------------------
# Platform restriction tests via FastAPI test client
# ---------------------------------------------------------------------------


def _make_app_with_user(current_user_dict: dict):
    """Build a FastAPI app with content routes and overridden auth dependency.

    The content router has prefix="/content" internally, so mounting under ""
    gives routes at /content/create etc.
    """
    from fastapi import FastAPI
    from routes.content import router as content_router
    from auth_utils import get_current_user

    app = FastAPI()
    app.include_router(content_router)  # routes like /content/create

    # Override the auth dependency so tests don't need a real JWT
    async def override_get_current_user():
        return current_user_dict

    app.dependency_overrides[get_current_user] = override_get_current_user
    return app


def _make_starter_user(user_id: str = None) -> dict:
    uid = user_id or f"user_{uuid.uuid4().hex[:8]}"
    return {
        "user_id": uid,
        "email": f"{uid}@test.com",
        "subscription_tier": "starter",
        "credits": 200,
    }


def _make_custom_user(user_id: str = None) -> dict:
    uid = user_id or f"user_{uuid.uuid4().hex[:8]}"
    return {
        "user_id": uid,
        "email": f"{uid}@test.com",
        "subscription_tier": "custom",
        "credits": 1000,
    }


@pytest.mark.asyncio
async def test_starter_platform_restriction_blocks_x():
    """Starter user gets HTTP 402 when trying to create content for platform 'x'."""
    from httpx import AsyncClient, ASGITransport

    starter_user = _make_starter_user()
    app = _make_app_with_user(starter_user)

    with patch("routes.content.db") as mock_db:
        mock_db.campaigns.find_one = AsyncMock(return_value=None)
        mock_db.content_jobs.insert_one = AsyncMock(return_value=MagicMock())

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/content/create",
                json={
                    "platform": "x",
                    "content_type": "tweet",
                    "raw_input": "This is a test post about productivity",
                },
            )

    assert response.status_code == 402, f"Expected 402, got {response.status_code}: {response.json()}"
    detail = response.json().get("detail", "")
    assert "linkedin" in detail.lower() or "LinkedIn" in detail, f"Expected LinkedIn mention in: {detail}"


@pytest.mark.asyncio
async def test_starter_platform_restriction_allows_linkedin():
    """Starter user is NOT blocked on platform 'linkedin' for platform restriction.

    The request may fail for other reasons (credits, pipeline) but NOT with the
    platform restriction 402.
    """
    from httpx import AsyncClient, ASGITransport

    starter_user = _make_starter_user()
    updated_user = {**starter_user, "credits": 190}
    app = _make_app_with_user(starter_user)

    # Patch both routes.content.db (used in route handler) and database.db (used in credits service)
    with patch("routes.content.db") as mock_route_db, \
         patch("database.db") as mock_credits_db:
        mock_route_db.campaigns.find_one = AsyncMock(return_value=None)
        mock_route_db.content_jobs.insert_one = AsyncMock(return_value=MagicMock())
        mock_route_db.campaigns.update_one = AsyncMock(return_value=MagicMock())

        mock_credits_db.users.find_one = AsyncMock(return_value=starter_user)
        mock_credits_db.users.find_one_and_update = AsyncMock(return_value=updated_user)
        mock_credits_db.credit_transactions.count_documents = AsyncMock(return_value=0)
        mock_credits_db.credit_transactions.insert_one = AsyncMock(return_value=MagicMock())

        with patch("routes.content.run_agent_pipeline"):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post(
                    "/content/create",
                    json={
                        "platform": "linkedin",
                        "content_type": "post",
                        "raw_input": "This is a test post about productivity",
                    },
                )

    # Should NOT be a platform restriction 402
    # If it's 402, the error must NOT mention LinkedIn restriction
    if response.status_code == 402:
        detail = response.json().get("detail", "")
        assert "Starter accounts can only create content for LinkedIn" not in detail, (
            f"Got platform restriction 402 for linkedin — should be allowed. Response: {response.json()}"
        )


@pytest.mark.asyncio
async def test_custom_tier_no_platform_restriction():
    """Custom tier user can create content for platform 'x' — no platform restriction."""
    from httpx import AsyncClient, ASGITransport

    custom_user = _make_custom_user()
    updated_user = {**custom_user, "credits": 990}
    app = _make_app_with_user(custom_user)

    # Patch both routes.content.db (used in route handler) and database.db (used in credits service)
    with patch("routes.content.db") as mock_route_db, \
         patch("database.db") as mock_credits_db:
        mock_route_db.campaigns.find_one = AsyncMock(return_value=None)
        mock_route_db.content_jobs.insert_one = AsyncMock(return_value=MagicMock())
        mock_route_db.campaigns.update_one = AsyncMock(return_value=MagicMock())

        mock_credits_db.users.find_one = AsyncMock(return_value=custom_user)
        mock_credits_db.users.find_one_and_update = AsyncMock(return_value=updated_user)
        mock_credits_db.credit_transactions.count_documents = AsyncMock(return_value=0)
        mock_credits_db.credit_transactions.insert_one = AsyncMock(return_value=MagicMock())

        with patch("routes.content.run_agent_pipeline"):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post(
                    "/content/create",
                    json={
                        "platform": "x",
                        "content_type": "tweet",
                        "raw_input": "This is a test post about productivity",
                    },
                )

    # Must NOT get a platform restriction 402
    assert response.status_code != 402 or (
        "Starter accounts can only create content for LinkedIn" not in response.json().get("detail", "")
    ), f"Custom tier user got platform restriction. Response: {response.json()}"


# ---------------------------------------------------------------------------
# add_credits tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_add_credits_success():
    """add_credits correctly increases user balance."""
    from services.credits import add_credits

    user_id = f"user_{uuid.uuid4().hex[:8]}"
    user = make_user(user_id, credits=50)
    updated_user = {**user, "credits": 150}

    mock_db = MagicMock()
    mock_db.users.find_one = AsyncMock(return_value=user)
    mock_db.users.update_one = AsyncMock(return_value=MagicMock())
    mock_db.credit_transactions.insert_one = AsyncMock(return_value=MagicMock())

    with patch("database.db", mock_db):
        result = await add_credits(user_id, 100, "purchase", "Test credit purchase")

    assert result["success"] is True
    assert result["new_balance"] == 150
    assert result["credits_added"] == 100

    # Verify update_one called with correct new balance
    call_args = mock_db.users.update_one.call_args
    assert call_args[0][1]["$set"]["credits"] == 150


# ---------------------------------------------------------------------------
# build_plan_preview tests
# ---------------------------------------------------------------------------


def test_build_plan_preview_calculates_correctly():
    """build_plan_preview returns correct total_credits and monthly_price_usd."""
    from services.credits import build_plan_preview, CreditOperation

    # 10 text posts (10 credits each) + 5 images (8 credits each) = 100 + 40 = 140 credits
    result = build_plan_preview(text_posts=10, images=5)

    assert result["total_credits"] == 140
    assert result["monthly_price_usd"] > 0
    assert "features" in result
    assert isinstance(result["features"], dict)
    assert "breakdown" in result

    # Verify operation costs match enums
    assert result["breakdown"]["text_posts"]["credits_each"] == CreditOperation.CONTENT_CREATE.value
    assert result["breakdown"]["images"]["credits_each"] == CreditOperation.IMAGE_GENERATE.value


def test_build_plan_preview_volume_discount():
    """Higher credit volumes get lower per-credit pricing."""
    from services.credits import build_plan_preview

    # Small plan: 500 credits -> $0.06/credit -> $30
    small = build_plan_preview(text_posts=50)  # 50 * 10 = 500 credits
    assert small["total_credits"] == 500
    assert small["price_per_credit"] == 0.06

    # Large plan: 2000 credits -> $0.035/credit
    large = build_plan_preview(text_posts=200)  # 200 * 10 = 2000 credits
    assert large["total_credits"] == 2000
    assert large["price_per_credit"] == 0.035
    assert large["monthly_price_usd"] > small["monthly_price_usd"]
