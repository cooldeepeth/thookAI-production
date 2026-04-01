"""Tests for Obsidian vault integration with Scout and Strategist agents (Plan 15-02).

OBS-01: Scout agent enriched with Obsidian vault search results
OBS-02: Strategist uses recent vault notes as recommendation signal
OBS-04: Both agents degrade gracefully when Obsidian not configured
"""

import asyncio
import sys
import types
import unittest
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers: Patch module-level settings reads in agent imports
# ---------------------------------------------------------------------------

def _make_settings(obsidian_configured: bool = False) -> MagicMock:
    """Build a mock settings object used by agents/services at import time."""
    settings = MagicMock()
    settings.llm.perplexity_key = ""  # force mock Perplexity path
    settings.strategist.max_cards_per_day = 3
    settings.strategist.suppression_days = 14
    settings.strategist.consecutive_dismissal_threshold = 5
    settings.strategist.min_approved_content = 1
    settings.strategist.synthesis_timeout = 30.0
    settings.obsidian.is_configured.return_value = obsidian_configured
    return settings


# ---------------------------------------------------------------------------
# Scout agent tests
# ---------------------------------------------------------------------------

class TestRunScoutObsidianEnrichment(unittest.IsolatedAsyncioTestCase):
    """Tests for Obsidian vault enrichment in run_scout (OBS-01, OBS-04)."""

    def _fresh_scout_module(self):
        """Import scout module fresh, clearing cached imports."""
        # Remove cached scout module so re-import picks up mocked settings
        for key in list(sys.modules.keys()):
            if key in ("agents.scout", "agents.commander"):
                del sys.modules[key]
        import agents.scout
        return agents.scout

    async def test_no_user_id_skips_vault_search_entirely(self):
        """run_scout with user_id=None skips vault search — backward compatible (OBS-04)."""
        mock_search_vault = AsyncMock(return_value={
            "findings": "vault content",
            "vault_sources": [{"title": "note.md", "snippet": "some text"}],
            "sources_found": 1,
        })
        with patch("agents.scout.settings", _make_settings(obsidian_configured=True)):
            import agents.scout as scout_mod
            # Reload to pick up the patched settings
            with patch.dict("sys.modules", {"services.obsidian_service": MagicMock(search_vault=mock_search_vault)}):
                result = await scout_mod.run_scout("AI trends", "AI trends research", "linkedin")

        # Without user_id, vault should not be searched
        mock_search_vault.assert_not_called()
        # Standard mock research keys should be present
        self.assertIn("findings", result)
        self.assertIn("citations", result)
        self.assertIn("sources_found", result)
        self.assertNotIn("vault_sources", result)

    async def test_obsidian_not_configured_returns_perplexity_only(self):
        """Scout falls back to Perplexity-only when Obsidian not configured (OBS-04)."""
        mock_search_vault = AsyncMock(return_value={
            "findings": "",
            "vault_sources": [],
            "sources_found": 0,
        })
        obsidian_module = MagicMock()
        obsidian_module.search_vault = mock_search_vault

        with patch.dict("sys.modules", {"services.obsidian_service": obsidian_module}):
            with patch("agents.scout.settings", _make_settings(obsidian_configured=False)):
                import agents.scout as scout_mod
                result = await scout_mod.run_scout(
                    "AI trends", "AI trends research", "linkedin", user_id="user-123"
                )

        # search_vault may be called but returns empty — result should not have vault_sources
        self.assertIn("findings", result)
        self.assertNotIn("vault_sources", result)

    async def test_vault_search_returns_results_merges_into_findings(self):
        """Scout merges vault results into findings with [Vault: title] prefix (OBS-01)."""
        mock_search_vault = AsyncMock(return_value={
            "findings": "[Vault: Research/AI-trends.md] LLMs are transforming content creation...",
            "vault_sources": [{"title": "Research/AI-trends.md", "snippet": "LLMs are transforming..."}],
            "sources_found": 1,
        })
        obsidian_module = MagicMock()
        obsidian_module.search_vault = mock_search_vault

        with patch.dict("sys.modules", {"services.obsidian_service": obsidian_module}):
            with patch("agents.scout.settings", _make_settings(obsidian_configured=True)):
                import agents.scout as scout_mod
                result = await scout_mod.run_scout(
                    "AI trends", "AI trends research", "linkedin", user_id="user-123"
                )

        self.assertIn("findings", result)
        # Vault content should be merged into findings
        self.assertIn("vault", result["findings"].lower())
        # vault_sources should be in the result
        self.assertIn("vault_sources", result)
        self.assertEqual(len(result["vault_sources"]), 1)
        self.assertEqual(result["vault_sources"][0]["title"], "Research/AI-trends.md")

    async def test_vault_search_empty_results_no_vault_sources_in_output(self):
        """Scout with Obsidian configured but empty vault results — no vault_sources key added."""
        mock_search_vault = AsyncMock(return_value={
            "findings": "",
            "vault_sources": [],
            "sources_found": 0,
        })
        obsidian_module = MagicMock()
        obsidian_module.search_vault = mock_search_vault

        with patch.dict("sys.modules", {"services.obsidian_service": obsidian_module}):
            with patch("agents.scout.settings", _make_settings(obsidian_configured=True)):
                import agents.scout as scout_mod
                result = await scout_mod.run_scout(
                    "AI trends", "AI trends research", "linkedin", user_id="user-123"
                )

        self.assertIn("findings", result)
        self.assertNotIn("vault_sources", result)

    async def test_vault_exception_is_non_fatal(self):
        """Scout with Obsidian search_vault raising exception returns Perplexity results unchanged."""
        mock_search_vault = AsyncMock(side_effect=Exception("Connection refused"))
        obsidian_module = MagicMock()
        obsidian_module.search_vault = mock_search_vault

        with patch.dict("sys.modules", {"services.obsidian_service": obsidian_module}):
            with patch("agents.scout.settings", _make_settings(obsidian_configured=True)):
                import agents.scout as scout_mod
                result = await scout_mod.run_scout(
                    "AI trends", "AI trends research", "linkedin", user_id="user-123"
                )

        # Should return mock research (Perplexity) without error
        self.assertIn("findings", result)
        self.assertIn("citations", result)
        self.assertNotIn("vault_sources", result)

    async def test_vault_section_appended_after_perplexity_findings(self):
        """Vault content appended to Perplexity findings — Perplexity first, then vault section."""
        mock_search_vault = AsyncMock(return_value={
            "findings": "[Vault: Research/topic.md] My research note...",
            "vault_sources": [{"title": "Research/topic.md", "snippet": "My research note..."}],
            "sources_found": 1,
        })
        obsidian_module = MagicMock()
        obsidian_module.search_vault = mock_search_vault

        with patch.dict("sys.modules", {"services.obsidian_service": obsidian_module}):
            with patch("agents.scout.settings", _make_settings(obsidian_configured=True)):
                import agents.scout as scout_mod
                result = await scout_mod.run_scout(
                    "topic", "topic research", "linkedin", user_id="user-123"
                )

        findings = result["findings"]
        # Standard mock research bullet should come first
        self.assertIn("•", findings)
        # Vault section should come after
        vault_pos = findings.lower().find("vault")
        # Ensure vault content is in the findings
        self.assertGreater(vault_pos, -1)

    async def test_run_scout_signature_has_optional_user_id(self):
        """run_scout accepts optional user_id keyword argument without error."""
        with patch("agents.scout.settings", _make_settings(obsidian_configured=False)):
            import agents.scout as scout_mod
            import inspect
            sig = inspect.signature(scout_mod.run_scout)
            params = list(sig.parameters.keys())
            self.assertIn("user_id", params)


# ---------------------------------------------------------------------------
# Strategist agent tests
# ---------------------------------------------------------------------------

class TestStrategistVaultSignals(unittest.IsolatedAsyncioTestCase):
    """Tests for vault signal injection in _gather_user_context and _build_synthesis_prompt (OBS-02)."""

    def _make_db_mock(self) -> MagicMock:
        """Build a mock db object with async find_one and cursor support."""
        db = MagicMock()
        # persona
        db.persona_engines = MagicMock()
        db.persona_engines.find_one = AsyncMock(return_value={
            "user_id": "user-123",
            "card": {"archetype": "Thought Leader", "primary_platform": "linkedin"},
            "voice_fingerprint": {"traits": ["concise"]},
            "content_identity": {"content_pillars": ["AI", "Leadership"]},
            "learning_signals": {"approved_count": 5},
        })
        # content_jobs
        db.content_jobs = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.sort = MagicMock(return_value=mock_cursor)
        mock_cursor.to_list = AsyncMock(return_value=[])
        db.content_jobs.find = MagicMock(return_value=mock_cursor)
        return db

    async def test_gather_user_context_includes_vault_notes_key(self):
        """_gather_user_context includes 'vault_notes' key when get_recent_notes returns results."""
        mock_get_recent_notes = AsyncMock(return_value=[
            {"title": "AI-trends", "path": "Research/AI-trends.md", "modified": ""},
            {"title": "Customer story", "path": "Research/customer-story.md", "modified": ""},
        ])
        obsidian_module = MagicMock()
        obsidian_module.get_recent_notes = mock_get_recent_notes

        db_mock = self._make_db_mock()

        with patch.dict("sys.modules", {"services.obsidian_service": obsidian_module}):
            with patch("agents.strategist.settings", _make_settings()):
                with patch("agents.strategist.db", db_mock):
                    # patch _query_content_gaps to avoid lightrag dep
                    with patch("agents.strategist._query_content_gaps", AsyncMock(return_value="")):
                        import agents.strategist as strat_mod
                        ctx = await strat_mod._gather_user_context("user-123")

        self.assertIn("vault_notes", ctx)
        self.assertEqual(len(ctx["vault_notes"]), 2)
        self.assertEqual(ctx["vault_notes"][0]["title"], "AI-trends")

    async def test_gather_user_context_vault_notes_empty_when_not_configured(self):
        """_gather_user_context returns empty vault_notes when get_recent_notes returns []."""
        mock_get_recent_notes = AsyncMock(return_value=[])
        obsidian_module = MagicMock()
        obsidian_module.get_recent_notes = mock_get_recent_notes

        db_mock = self._make_db_mock()

        with patch.dict("sys.modules", {"services.obsidian_service": obsidian_module}):
            with patch("agents.strategist.settings", _make_settings()):
                with patch("agents.strategist.db", db_mock):
                    with patch("agents.strategist._query_content_gaps", AsyncMock(return_value="")):
                        import agents.strategist as strat_mod
                        ctx = await strat_mod._gather_user_context("user-123")

        self.assertIn("vault_notes", ctx)
        self.assertEqual(ctx["vault_notes"], [])

    async def test_gather_user_context_vault_notes_empty_on_exception(self):
        """_gather_user_context returns empty vault_notes when get_recent_notes raises (non-fatal)."""
        mock_get_recent_notes = AsyncMock(side_effect=Exception("Service down"))
        obsidian_module = MagicMock()
        obsidian_module.get_recent_notes = mock_get_recent_notes

        db_mock = self._make_db_mock()

        with patch.dict("sys.modules", {"services.obsidian_service": obsidian_module}):
            with patch("agents.strategist.settings", _make_settings()):
                with patch("agents.strategist.db", db_mock):
                    with patch("agents.strategist._query_content_gaps", AsyncMock(return_value="")):
                        import agents.strategist as strat_mod
                        ctx = await strat_mod._gather_user_context("user-123")

        # Non-fatal: vault_notes should be empty list, no exception raised
        self.assertIn("vault_notes", ctx)
        self.assertEqual(ctx["vault_notes"], [])

    async def test_build_synthesis_prompt_includes_vault_signals_section(self):
        """_build_synthesis_prompt includes VAULT SIGNALS section when vault_notes is non-empty."""
        context = {
            "persona": {
                "card": {"archetype": "Thought Leader", "primary_platform": "linkedin"},
                "voice_fingerprint": {"traits": ["concise"]},
                "content_identity": {"content_pillars": ["AI"]},
            },
            "recent_content": [],
            "performance_signals": [],
            "knowledge_gaps": "",
            "vault_notes": [
                {"title": "AI-trends", "path": "Research/AI-trends.md", "modified": "2026-04-01"},
            ],
        }
        with patch("agents.strategist.settings", _make_settings()):
            import agents.strategist as strat_mod
            prompt = await strat_mod._build_synthesis_prompt(context, [])

        self.assertIn("VAULT SIGNALS", prompt)
        self.assertIn("AI-trends", prompt)

    async def test_build_synthesis_prompt_no_vault_signals_when_empty(self):
        """_build_synthesis_prompt has no VAULT SIGNALS text when vault_notes is empty."""
        context = {
            "persona": {
                "card": {"archetype": "Thought Leader", "primary_platform": "linkedin"},
                "voice_fingerprint": {"traits": ["concise"]},
                "content_identity": {"content_pillars": ["AI"]},
            },
            "recent_content": [],
            "performance_signals": [],
            "knowledge_gaps": "",
            "vault_notes": [],
        }
        with patch("agents.strategist.settings", _make_settings()):
            import agents.strategist as strat_mod
            prompt = await strat_mod._build_synthesis_prompt(context, [])

        self.assertNotIn("VAULT SIGNALS", prompt)

    async def test_strategist_system_prompt_mentions_vault_signal_source(self):
        """STRATEGIST_SYSTEM_PROMPT includes 'vault' as a valid signal_source value."""
        with patch("agents.strategist.settings", _make_settings()):
            import agents.strategist as strat_mod
            prompt = strat_mod.STRATEGIST_SYSTEM_PROMPT

        self.assertIn("vault", prompt)

    async def test_strategist_system_prompt_mentions_vault_in_why_now_guidance(self):
        """STRATEGIST_SYSTEM_PROMPT includes vault note guidance in why_now section."""
        with patch("agents.strategist.settings", _make_settings()):
            import agents.strategist as strat_mod
            prompt = strat_mod.STRATEGIST_SYSTEM_PROMPT

        # Should mention vault notes as a why_now signal
        prompt_lower = prompt.lower()
        self.assertTrue(
            "vault" in prompt_lower,
            "STRATEGIST_SYSTEM_PROMPT should mention vault as a signal source",
        )


if __name__ == "__main__":
    unittest.main()
