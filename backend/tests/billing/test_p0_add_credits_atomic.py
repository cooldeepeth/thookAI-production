"""TDD: Non-atomic add_credits race condition — BILL-07.

BUG: services/credits.py lines 460-471 use find_one + update_one($set)
instead of atomic find_one_and_update($inc). Concurrent calls can lose credits.

NOTE per PITFALLS.md Pitfall 4: mongomock serializes operations, so the
asyncio.gather test verifies CORRECT behavior after the fix, not the bug itself.
The bug is verified by code inspection (non-atomic pattern confirmed in research).
"""
import asyncio
import pytest
from unittest.mock import patch


@pytest.mark.asyncio
class TestAddCreditsAtomicity:

    async def test_single_add_credits_returns_correct_balance(self, mongomock_db):
        """Basic add_credits adds amount and returns new balance."""
        await mongomock_db.users.insert_one({
            "user_id": "user_single", "credits": 50, "email": "a@b.com"
        })
        # credits.py uses lazy `from database import db` inside each function,
        # so we patch database.db (the source), not services.credits.db.
        with patch("database.db", mongomock_db):
            from services.credits import add_credits
            result = await add_credits("user_single", 100, "purchase")
        assert result["success"] is True
        assert result["new_balance"] == 150
        assert result["credits_added"] == 100

        user = await mongomock_db.users.find_one({"user_id": "user_single"})
        assert user["credits"] == 150

    async def test_concurrent_add_credits_no_lost_updates(self, mongomock_db):
        """Two concurrent add_credits(100) on a 0-credit user must yield 200."""
        await mongomock_db.users.insert_one({
            "user_id": "user_race", "credits": 0, "email": "race@test.com"
        })
        with patch("database.db", mongomock_db):
            from services.credits import add_credits
            await asyncio.gather(
                add_credits("user_race", 100, "purchase"),
                add_credits("user_race", 100, "purchase"),
            )
        user = await mongomock_db.users.find_one({"user_id": "user_race"})
        assert user["credits"] == 200, (
            f"Expected 200 credits after two +100 adds, got {user['credits']}"
        )

    async def test_add_credits_nonexistent_user_returns_error(self, mongomock_db):
        """add_credits for non-existent user returns error dict."""
        with patch("database.db", mongomock_db):
            from services.credits import add_credits
            result = await add_credits("nonexistent_user", 100, "purchase")
        assert result["success"] is False
        assert "not found" in result.get("error", "").lower()

    async def test_add_credits_records_transaction(self, mongomock_db):
        """add_credits writes a credit_transaction document."""
        await mongomock_db.users.insert_one({
            "user_id": "user_txn", "credits": 0, "email": "txn@test.com"
        })
        with patch("database.db", mongomock_db):
            from services.credits import add_credits
            await add_credits("user_txn", 50, "webhook", "Test credit add")

        txn = await mongomock_db.credit_transactions.find_one({"user_id": "user_txn"})
        assert txn is not None
        assert txn["amount"] == 50
        assert txn["type"] == "addition"
        assert txn["source"] == "webhook"
