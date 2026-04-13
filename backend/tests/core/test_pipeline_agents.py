"""Isolated unit tests for all 5 content pipeline agents.

Tests Commander, Scout, Thinker, Writer, and QC agents in complete isolation —
no network calls, deterministic LLM mocks, testing I/O contracts, fallback
behavior, and prompt injection of context signals.

Key patching convention: Always patch module-level imports in each agent module
(e.g., 'agents.commander.openai_available', 'agents.commander.LlmChat') rather
than the original source modules. This targets the exact reference used by the
agent at call time.

Covers requirements:
- CORE-01: Each agent testable in isolation with deterministic mock replacing LlmChat
"""

import json
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Ensure backend is on path
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)


# ---------------------------------------------------------------------------
# Helpers — valid return payloads
# ---------------------------------------------------------------------------

def _make_valid_commander_json(content_type="post"):
    return json.dumps({
        "content_type": content_type,
        "primary_angle": "Founders misread product-market fit signals",
        "hook_approach": "bold_claim",
        "key_points": ["Signal 1", "Signal 2", "Signal 3"],
        "research_needed": True,
        "research_query": "product-market fit data 2025",
        "structure": "numbered_list",
        "estimated_word_count": 220,
        "cta_approach": "question",
        "persona_notes": "First-person, conversational, data-backed",
    })


def _make_valid_thinker_json():
    return json.dumps({
        "angle": "The fastest path to PMF is listening not iterating",
        "hook_options": [
            "I killed the feature 3 founders begged for. Revenue doubled.",
            "PMF is not found. It is heard.",
        ],
        "content_structure": [
            {"section": "Hook", "guidance": "Counter-intuitive opening"},
            {"section": "Body", "guidance": "3 concrete lessons"},
            {"section": "Insight", "guidance": "Core truth about PMF"},
            {"section": "CTA", "guidance": "Question to drive comments"},
        ],
        "key_insight": "Customers tell you what to build if you stop and listen",
        "differentiation": "First-person failure with revenue proof points",
    })


def _make_valid_qc_json():
    return json.dumps({
        "personaMatch": 8.5,
        "aiRisk": 18,
        "platformFit": 9.0,
        "overall_pass": True,
        "feedback": ["Add a specific metric to the hook"],
        "suggestions": ["Open with the failure year for impact"],
        "strengths": ["Strong voice", "Clear insight", "Tight CTA"],
    })


def _make_mock_llm_chat(return_value: str):
    """Build a MagicMock LlmChat instance whose send_message returns the given string."""
    mock_instance = MagicMock()
    mock_instance.with_model = MagicMock(return_value=mock_instance)
    mock_instance.send_message = AsyncMock(return_value=return_value)
    return mock_instance


def _make_capturing_llm_chat(container: dict, return_value: str):
    """Build a LlmChat mock that also captures the prompt text sent to send_message."""
    async def _cap_send(user_message):
        container["text"] = user_message.text
        return return_value

    mock_instance = MagicMock()
    mock_instance.with_model = MagicMock(return_value=mock_instance)
    mock_instance.send_message = AsyncMock(side_effect=_cap_send)
    return mock_instance


# ===========================================================================
# TestCommanderAgent
# ===========================================================================

class TestCommanderAgent:
    """Isolated tests for commander.run_commander()."""

    @pytest.mark.asyncio
    async def test_commander_returns_valid_json_keys(self, make_persona_card):
        """Commander returns dict with all required keys when LLM is available."""
        from agents.commander import run_commander

        mock_chat = _make_mock_llm_chat(_make_valid_commander_json())

        with patch("agents.commander.LlmChat", return_value=mock_chat), \
             patch("agents.commander.chat_constructor_key", return_value="test-key"), \
             patch("agents.commander.openai_available", return_value=True):
            result = await run_commander(
                raw_input="AI trends in B2B SaaS",
                platform="linkedin",
                content_type="post",
                persona_card=make_persona_card(),
            )

        required_keys = {
            "content_type", "primary_angle", "hook_approach", "key_points",
            "research_needed", "structure",
        }
        assert required_keys.issubset(result.keys()), (
            f"Missing keys: {required_keys - result.keys()}"
        )
        assert isinstance(result["key_points"], list)
        assert isinstance(result["research_needed"], bool)

    @pytest.mark.asyncio
    async def test_commander_fallback_to_mock_when_no_llm(self, make_persona_card):
        """Commander returns mock output when no LLM provider is available."""
        from agents.commander import run_commander

        with patch("agents.commander.openai_available", return_value=False):
            result = await run_commander(
                raw_input="AI trends",
                platform="linkedin",
                content_type="post",
                persona_card=make_persona_card(),
            )

        required_keys = {
            "content_type", "primary_angle", "hook_approach", "key_points",
            "research_needed", "structure",
        }
        assert required_keys.issubset(result.keys()), (
            f"Mock fallback missing keys: {required_keys - result.keys()}"
        )

    @pytest.mark.asyncio
    async def test_commander_cleans_json_markdown_fencing(self, make_persona_card):
        """Commander strips markdown code fencing from LLM response."""
        from agents.commander import run_commander

        raw = "```json\n" + _make_valid_commander_json() + "\n```"
        mock_chat = _make_mock_llm_chat(raw)

        with patch("agents.commander.LlmChat", return_value=mock_chat), \
             patch("agents.commander.chat_constructor_key", return_value="test-key"), \
             patch("agents.commander.openai_available", return_value=True):
            result = await run_commander(
                raw_input="test topic",
                platform="linkedin",
                content_type="post",
                persona_card=make_persona_card(),
            )

        assert isinstance(result, dict), "Should return parsed dict, not raw string"
        assert "primary_angle" in result

    @pytest.mark.asyncio
    async def test_commander_handles_invalid_json_gracefully(self, make_persona_card):
        """Commander falls back to mock when LLM returns non-JSON garbage."""
        from agents.commander import run_commander

        mock_chat = _make_mock_llm_chat("not json at all, sorry about that")

        with patch("agents.commander.LlmChat", return_value=mock_chat), \
             patch("agents.commander.chat_constructor_key", return_value="test-key"), \
             patch("agents.commander.openai_available", return_value=True):
            result = await run_commander(
                raw_input="test topic",
                platform="linkedin",
                content_type="post",
                persona_card=make_persona_card(),
            )

        assert isinstance(result, dict)
        assert "primary_angle" in result

    @pytest.mark.asyncio
    async def test_commander_includes_anti_rep_prompt_in_message(self, make_persona_card):
        """Anti-repetition prompt is injected into the message sent to LLM."""
        from agents.commander import run_commander

        captured = {}
        mock_chat = _make_capturing_llm_chat(captured, _make_valid_commander_json())

        with patch("agents.commander.LlmChat", return_value=mock_chat), \
             patch("agents.commander.chat_constructor_key", return_value="test-key"), \
             patch("agents.commander.openai_available", return_value=True):
            await run_commander(
                raw_input="test topic",
                platform="linkedin",
                content_type="post",
                persona_card=make_persona_card(),
                anti_rep_prompt="AVOID: question hooks about AI trends",
            )

        assert "AVOID: question hooks about AI trends" in captured.get("text", ""), (
            "Anti-rep prompt should be appended to the commander prompt"
        )


# ===========================================================================
# TestScoutAgent
# ===========================================================================

class TestScoutAgent:
    """Isolated tests for scout.run_scout()."""

    @pytest.mark.asyncio
    async def test_scout_returns_findings_with_valid_perplexity_key(self):
        """Scout returns 'findings' key when Perplexity returns a successful response."""
        import httpx
        import respx
        from agents.scout import run_scout

        mock_response_data = {
            "choices": [{"message": {"content": "• AI adoption up 40%\n• 3x engagement with data claims"}}],
            "citations": ["https://example.com/source1"],
        }

        with patch("agents.scout.settings") as mock_settings:
            mock_settings.llm.perplexity_key = "pplx-realkey123456"

            with respx.mock() as mock_rx:
                mock_rx.post("https://api.perplexity.ai/chat/completions").mock(
                    return_value=httpx.Response(200, json=mock_response_data)
                )
                result = await run_scout(
                    topic="AI trends",
                    research_query="AI adoption statistics 2025",
                    platform="linkedin",
                )

        assert "findings" in result
        assert len(result["findings"]) > 0

    @pytest.mark.asyncio
    async def test_scout_falls_back_to_mock_with_placeholder_key(self):
        """Scout uses _mock_research when Perplexity key is a placeholder."""
        from agents.scout import run_scout

        with patch("agents.scout.settings") as mock_settings:
            mock_settings.llm.perplexity_key = "pplx-placeholder"

            result = await run_scout(
                topic="AI trends",
                research_query="AI adoption statistics 2025",
                platform="linkedin",
            )

        assert "findings" in result
        # Mock research contains bullet points
        assert "•" in result["findings"]

    @pytest.mark.asyncio
    async def test_scout_handles_perplexity_timeout(self):
        """Scout returns mock fallback gracefully when HTTP call raises TimeoutException."""
        import httpx
        from agents.scout import run_scout

        with patch("agents.scout.settings") as mock_settings:
            mock_settings.llm.perplexity_key = "pplx-realkey123456"

            with patch("httpx.AsyncClient") as mock_client_cls:
                mock_client = AsyncMock()
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=False)
                mock_client.post = AsyncMock(side_effect=httpx.TimeoutException("timeout"))
                mock_client_cls.return_value = mock_client

                result = await run_scout(
                    topic="AI trends",
                    research_query="AI adoption statistics 2025",
                    platform="linkedin",
                )

        assert "findings" in result
        assert isinstance(result["findings"], str)

    @pytest.mark.asyncio
    async def test_scout_enriches_with_obsidian_when_configured(self):
        """Scout appends vault notes to findings when Obsidian search returns results."""
        from agents.scout import run_scout

        vault_result = {
            "sources_found": 2,
            "findings": "AI as a co-pilot model is the dominant pattern",
            "vault_sources": ["note1.md", "note2.md"],
        }

        with patch("agents.scout.settings") as mock_settings:
            mock_settings.llm.perplexity_key = "pplx-placeholder"

            with patch("services.obsidian_service.search_vault", new_callable=AsyncMock) as mock_vault:
                mock_vault.return_value = vault_result

                result = await run_scout(
                    topic="AI trends",
                    research_query="AI adoption statistics 2025",
                    platform="linkedin",
                    user_id="user_123",
                )

        mock_vault.assert_awaited_once()
        assert "From your research vault:" in result["findings"]

    @pytest.mark.asyncio
    async def test_scout_skips_obsidian_when_not_configured(self):
        """Scout does NOT call obsidian_service.search_vault when no user_id is provided."""
        from agents.scout import run_scout

        with patch("agents.scout.settings") as mock_settings:
            mock_settings.llm.perplexity_key = "pplx-placeholder"

            with patch("services.obsidian_service.search_vault", new_callable=AsyncMock) as mock_vault:
                result = await run_scout(
                    topic="AI trends",
                    research_query="AI adoption statistics 2025",
                    platform="linkedin",
                    user_id=None,  # No user_id — skip Obsidian
                )

        mock_vault.assert_not_called()
        assert "findings" in result


# ===========================================================================
# TestThinkerAgent
# ===========================================================================

class TestThinkerAgent:
    """Isolated tests for thinker.run_thinker()."""

    @pytest.mark.asyncio
    async def test_thinker_returns_valid_strategy_json(self, make_persona_card):
        """Thinker returns dict with required strategy keys when LLM is available."""
        from agents.thinker import run_thinker

        commander_output = {
            "primary_angle": "Founders misread PMF signals",
            "content_type": "post",
            "hook_approach": "bold_claim",
        }
        scout_output = {"findings": "• PMF success rate < 20% for first-time founders"}

        mock_chat = _make_mock_llm_chat(_make_valid_thinker_json())

        with patch("agents.thinker.LlmChat", return_value=mock_chat), \
             patch("agents.thinker.chat_constructor_key", return_value="test-key"), \
             patch("agents.thinker.openai_available", return_value=True):
            result = await run_thinker(
                raw_input="Product-market fit",
                commander_output=commander_output,
                scout_output=scout_output,
                persona_card=make_persona_card(),
            )

        required_keys = {"angle", "hook_options", "content_structure", "key_insight", "differentiation"}
        assert required_keys.issubset(result.keys()), f"Missing: {required_keys - result.keys()}"
        assert isinstance(result["hook_options"], list)
        assert len(result["hook_options"]) >= 1
        assert isinstance(result["content_structure"], list)

    @pytest.mark.asyncio
    async def test_thinker_fallback_to_mock_when_no_llm(self, make_persona_card):
        """Thinker returns _mock_thinker output when no LLM is available."""
        from agents.thinker import run_thinker

        commander_output = {"primary_angle": "Test angle", "content_type": "post"}

        with patch("agents.thinker.openai_available", return_value=False):
            result = await run_thinker(
                raw_input="test topic",
                commander_output=commander_output,
                scout_output={},
                persona_card=make_persona_card(),
            )

        required_keys = {"angle", "hook_options", "content_structure", "key_insight", "differentiation"}
        assert required_keys.issubset(result.keys()), f"Mock fallback missing: {required_keys - result.keys()}"

    @pytest.mark.asyncio
    async def test_thinker_injects_fatigue_context_when_non_healthy(self, make_persona_card):
        """Thinker prompt contains overused patterns when shield_status is warning."""
        from agents.thinker import run_thinker

        captured = {}
        mock_chat = _make_capturing_llm_chat(captured, _make_valid_thinker_json())

        fatigue_context = {
            "shield_status": "warning",
            "risk_factors": [
                {"detail": "question hooks used 8 times in last 10 posts"},
                {"detail": "AI trends topic overused 5 times"},
            ],
            "recommendations": ["Try contrast hooks", "Use personal story format"],
        }

        with patch("agents.thinker.LlmChat", return_value=mock_chat), \
             patch("agents.thinker.chat_constructor_key", return_value="test-key"), \
             patch("agents.thinker.openai_available", return_value=True):
            await run_thinker(
                raw_input="AI productivity",
                commander_output={"primary_angle": "angle", "content_type": "post"},
                scout_output={},
                persona_card=make_persona_card(),
                fatigue_context=fatigue_context,
            )

        prompt_text = captured.get("text", "")
        assert "question hooks" in prompt_text or "DIVERSITY CONSTRAINTS" in prompt_text, (
            "Fatigue context constraints should appear in the Thinker prompt"
        )

    @pytest.mark.asyncio
    async def test_thinker_skips_fatigue_for_healthy_status(self, make_persona_card):
        """_build_fatigue_prompt_section returns empty string when status is healthy."""
        from agents.thinker import _build_fatigue_prompt_section

        result = _build_fatigue_prompt_section({"shield_status": "healthy"})
        assert result == "", "Healthy status should yield empty string"

        result_none = _build_fatigue_prompt_section(None)
        assert result_none == "", "None input should yield empty string"

    @pytest.mark.asyncio
    async def test_thinker_queries_lightrag_when_configured(self, make_persona_card):
        """Thinker prompt includes knowledge graph context when LightRAG returns data."""
        from agents.thinker import run_thinker

        captured = {}
        mock_chat = _make_capturing_llm_chat(captured, _make_valid_thinker_json())

        with patch("agents.thinker.LlmChat", return_value=mock_chat), \
             patch("agents.thinker.chat_constructor_key", return_value="test-key"), \
             patch("agents.thinker.openai_available", return_value=True), \
             patch("services.lightrag_service.query_knowledge_graph",
                   new_callable=AsyncMock) as mock_kg:
            mock_kg.return_value = "Previously used angle: AI productivity hacks (3x)"

            await run_thinker(
                raw_input="AI productivity",
                commander_output={"primary_angle": "angle", "content_type": "post"},
                scout_output={},
                persona_card=make_persona_card(),
                user_id="user_123",
            )

        mock_kg.assert_awaited_once()
        assert "Previously used angle" in captured.get("text", ""), (
            "Knowledge graph context should appear in the Thinker prompt"
        )


# ===========================================================================
# TestWriterAgent
# ===========================================================================

class TestWriterAgent:
    """Isolated tests for writer.run_writer()."""

    def _make_thinker_output(self):
        return {
            "angle": "The fastest path to PMF is listening not iterating",
            "hook_options": ["I killed a feature 3 founders begged for. Revenue doubled."],
            "content_structure": [
                {"section": "Hook", "guidance": "Counter-intuitive opening"},
                {"section": "Body", "guidance": "3 concrete lessons"},
            ],
            "key_insight": "Customers tell you what to build if you stop and listen",
            "differentiation": "First-person failure with proof",
        }

    def _make_commander_output(self):
        return {
            "primary_angle": "Founders misread PMF signals",
            "cta_approach": "question",
            "estimated_word_count": 220,
        }

    @pytest.mark.asyncio
    async def test_writer_returns_content_string(self, make_persona_card):
        """Writer returns a dict with non-empty 'draft' key when LLM is available."""
        from agents.writer import run_writer

        draft_text = (
            "Most founders are chasing the wrong signal for product-market fit.\n\n"
            "After 3 failed products, I learned this the hard way.\n\n"
            "What's your biggest PMF indicator?"
        )
        mock_chat = _make_mock_llm_chat(draft_text)

        with patch("agents.writer.LlmChat", return_value=mock_chat), \
             patch("agents.writer.chat_constructor_key", return_value="test-key"), \
             patch("agents.writer.anthropic_available", return_value=True):
            result = await run_writer(
                platform="linkedin",
                content_type="post",
                commander_output=self._make_commander_output(),
                scout_output={"findings": "• 80% of startups fail due to poor PMF"},
                thinker_output=self._make_thinker_output(),
                persona_card=make_persona_card(),
            )

        assert isinstance(result, dict), "Writer should return a dict"
        draft = result.get("draft", "")
        assert len(draft) > 0, "draft should be non-empty"

    @pytest.mark.asyncio
    async def test_writer_fallback_to_mock_when_no_llm(self, make_persona_card):
        """Writer returns _mock_writer output when Anthropic is unavailable."""
        from agents.writer import run_writer

        with patch("agents.writer.anthropic_available", return_value=False):
            result = await run_writer(
                platform="linkedin",
                content_type="post",
                commander_output=self._make_commander_output(),
                scout_output={},
                thinker_output=self._make_thinker_output(),
                persona_card=make_persona_card(),
            )

        assert isinstance(result, dict), "Mock fallback should return dict"
        assert "draft" in result
        assert len(result["draft"]) > 0

    @pytest.mark.asyncio
    async def test_writer_applies_regional_english_rules(self, make_persona_card):
        """Writer prompt contains Indian English rules when regional_english=IN."""
        from agents.writer import run_writer

        captured = {}
        mock_chat = _make_capturing_llm_chat(
            captured, "Draft content for Indian market using crore and lakh properly."
        )
        indian_persona = make_persona_card(regional_english="IN")

        with patch("agents.writer.LlmChat", return_value=mock_chat), \
             patch("agents.writer.chat_constructor_key", return_value="test-key"), \
             patch("agents.writer.anthropic_available", return_value=True):
            await run_writer(
                platform="linkedin",
                content_type="post",
                commander_output=self._make_commander_output(),
                scout_output={},
                thinker_output=self._make_thinker_output(),
                persona_card=indian_persona,
            )

        prompt_text = captured.get("text", "")
        assert "Indian English" in prompt_text or "lakh" in prompt_text or "crore" in prompt_text, (
            "Writer prompt should include Indian English rules for IN regional setting"
        )

    @pytest.mark.asyncio
    async def test_writer_injects_style_examples_from_vector_store(self, make_persona_card):
        """Writer prompt includes style examples retrieved from vector store."""
        from agents.writer import run_writer

        captured = {}
        style_example = (
            "PREVIOUSLY APPROVED CONTENT IN THIS VOICE (match this style closely):\n"
            "Example 1:\nBuilt a $1M ARR product with 0 marketing. Here is how."
        )
        mock_chat = _make_capturing_llm_chat(
            captured, "Great LinkedIn content matching the style examples above."
        )

        with patch("agents.writer.LlmChat", return_value=mock_chat), \
             patch("agents.writer.chat_constructor_key", return_value="test-key"), \
             patch("agents.writer.anthropic_available", return_value=True), \
             patch("agents.writer._fetch_style_examples",
                   new_callable=AsyncMock) as mock_examples:
            mock_examples.return_value = style_example

            await run_writer(
                platform="linkedin",
                content_type="post",
                commander_output=self._make_commander_output(),
                scout_output={},
                thinker_output=self._make_thinker_output(),
                persona_card=make_persona_card(),
                user_id="user_123",
            )

        mock_examples.assert_awaited_once()
        prompt_text = captured.get("text", "")
        assert "PREVIOUSLY APPROVED CONTENT" in prompt_text, (
            "Style examples should be injected into the writer prompt"
        )

    @pytest.mark.asyncio
    async def test_writer_respects_platform_rules(self, make_persona_card):
        """Writer prompt contains X/Twitter 280-char rule when platform=x.

        PLATFORM_RULES was renamed to FORMAT_RULES in Phase 28 — rules are
        now keyed by content_type (e.g. 'tweet', 'post') not platform.
        """
        from agents.writer import run_writer, FORMAT_RULES

        captured = {}
        mock_chat = _make_capturing_llm_chat(captured, "Short punchy X content.")

        with patch("agents.writer.LlmChat", return_value=mock_chat), \
             patch("agents.writer.chat_constructor_key", return_value="test-key"), \
             patch("agents.writer.anthropic_available", return_value=True):
            await run_writer(
                platform="x",
                content_type="tweet",
                commander_output=self._make_commander_output(),
                scout_output={},
                thinker_output=self._make_thinker_output(),
                persona_card=make_persona_card(),
            )

        prompt_text = captured.get("text", "")
        tweet_rules = FORMAT_RULES.get("tweet", "")
        assert "280" in prompt_text or "X (Twitter)" in prompt_text or tweet_rules[:30] in prompt_text, (
            "Writer prompt should include format-specific rules for tweet (280-char limit)"
        )


# ===========================================================================
# TestQCAgent
# ===========================================================================

class TestQCAgent:
    """Isolated tests for qc.run_qc()."""

    _DRAFT = (
        "Most founders are solving the wrong problem.\n\n"
        "I spent 18 months building features nobody asked for.\n\n"
        "The fix? Stop building. Start listening.\n\n"
        "What has a customer told you that changed your roadmap entirely?"
    )

    @pytest.mark.asyncio
    async def test_qc_returns_score_dict(self, make_persona_card):
        """QC returns dict with all required score keys when LLM is available."""
        from agents.qc import run_qc

        mock_chat = _make_mock_llm_chat(_make_valid_qc_json())

        with patch("agents.qc.LlmChat", return_value=mock_chat), \
             patch("agents.qc.chat_constructor_key", return_value="test-key"), \
             patch("agents.qc.openai_available", return_value=True):
            result = await run_qc(
                draft=self._DRAFT,
                persona_card=make_persona_card(),
                platform="linkedin",
                content_type="post",
            )

        required_keys = {
            "personaMatch", "aiRisk", "platformFit", "overall_pass",
            "feedback", "suggestions", "strengths",
        }
        assert required_keys.issubset(result.keys()), f"Missing QC keys: {required_keys - result.keys()}"
        assert isinstance(result["overall_pass"], bool)
        assert isinstance(result["feedback"], list)
        assert isinstance(result["strengths"], list)

    @pytest.mark.asyncio
    async def test_qc_fallback_to_mock(self, make_persona_card):
        """QC returns _mock_qc output when OpenAI is unavailable."""
        from agents.qc import run_qc

        with patch("agents.qc.openai_available", return_value=False):
            result = await run_qc(
                draft=self._DRAFT,
                persona_card=make_persona_card(),
                platform="linkedin",
                content_type="post",
            )

        required_keys = {
            "personaMatch", "aiRisk", "platformFit", "overall_pass",
            "feedback", "suggestions", "strengths",
        }
        assert required_keys.issubset(result.keys())
        # Long-enough draft should pass mock QC (word count raises persona_match above 7)
        assert isinstance(result["overall_pass"], bool)

    @pytest.mark.asyncio
    async def test_qc_handles_invalid_json_from_llm(self, make_persona_card):
        """QC falls back to mock dict when LLM returns garbled text."""
        from agents.qc import run_qc

        mock_chat = _make_mock_llm_chat("garbled not json ::: {broken")

        with patch("agents.qc.LlmChat", return_value=mock_chat), \
             patch("agents.qc.chat_constructor_key", return_value="test-key"), \
             patch("agents.qc.openai_available", return_value=True):
            result = await run_qc(
                draft=self._DRAFT,
                persona_card=make_persona_card(),
                platform="linkedin",
                content_type="post",
            )

        # Should not raise — must return a fallback dict
        assert isinstance(result, dict)
        assert "personaMatch" in result

    @pytest.mark.asyncio
    async def test_qc_checks_anti_repetition_when_user_id_provided(self, make_persona_card):
        """QC calls anti_repetition.score_repetition_risk when user_id is provided."""
        from agents.qc import run_qc

        rep_result = {
            "repetition_risk_score": 30,
            "risk_level": "low",
            "feedback": "Diversity is healthy",
        }

        with patch("agents.qc.openai_available", return_value=False), \
             patch("agents.anti_repetition.score_repetition_risk",
                   new_callable=AsyncMock) as mock_rep:
            mock_rep.return_value = rep_result

            result = await run_qc(
                draft=self._DRAFT,
                persona_card=make_persona_card(),
                platform="linkedin",
                content_type="post",
                user_id="user_123",
            )

        mock_rep.assert_awaited_once_with("user_123", self._DRAFT)
        assert "repetition_risk" in result
        assert "repetition_level" in result

    @pytest.mark.asyncio
    async def test_qc_skips_anti_repetition_when_no_user_id(self, make_persona_card):
        """QC does NOT call anti_repetition when user_id is None."""
        from agents.qc import run_qc

        with patch("agents.qc.openai_available", return_value=False), \
             patch("agents.anti_repetition.score_repetition_risk",
                   new_callable=AsyncMock) as mock_rep:
            result = await run_qc(
                draft=self._DRAFT,
                persona_card=make_persona_card(),
                platform="linkedin",
                content_type="post",
                user_id=None,
            )

        mock_rep.assert_not_called()
        assert "repetition_risk" not in result
