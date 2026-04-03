"""LangGraph orchestrator node-level unit tests.

Tests each node function in isolation by feeding PipelineState dicts directly,
verifying the returned state delta, and asserting routing logic for quality_gate
and should_research. All agent calls and DB operations are mocked.

Note: quality_gate and should_research basic cases are also covered in
test_pipeline_integration.py (PIPE-02). This file adds NEW edge cases —
missing qc_output, loop counting, hook debate with single option, finalize DB
interaction — that are NOT covered there.

Covers requirements:
- CORE-02: Node-level orchestrator tests including quality gate routing and QC retry loops
"""

import json
import os
import sys
import types
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Ensure backend is on path
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)


# ---------------------------------------------------------------------------
# LangGraph mock + orchestrator import helper
# ---------------------------------------------------------------------------

def _import_orchestrator():
    """Import orchestrator module, installing a minimal langgraph mock if needed.

    The mock satisfies all langgraph.graph imports used by orchestrator.py
    without requiring the actual langgraph package.
    """
    if "langgraph" not in sys.modules:
        lg_mock = types.ModuleType("langgraph")
        lg_graph = types.ModuleType("langgraph.graph")

        class _MockStateGraph:
            def __init__(self, state_schema):
                pass
            def add_node(self, *args, **kwargs): pass
            def add_edge(self, *args, **kwargs): pass
            def add_conditional_edges(self, *args, **kwargs): pass
            def set_entry_point(self, *args, **kwargs): pass
            def compile(self):
                m = MagicMock()
                m.ainvoke = AsyncMock(return_value={})
                return m

        lg_graph.END = object()
        lg_graph.StateGraph = _MockStateGraph
        lg_mock.graph = lg_graph
        sys.modules.setdefault("langgraph", lg_mock)
        sys.modules.setdefault("langgraph.graph", lg_graph)

    if "agents.orchestrator" in sys.modules:
        return sys.modules["agents.orchestrator"]
    import agents.orchestrator as orch
    return orch


# ---------------------------------------------------------------------------
# Shared minimal state builder
# ---------------------------------------------------------------------------

def _base_state(**kwargs) -> dict:
    defaults = {
        "job_id": "job_orch_test",
        "user_id": "user_orch_test",
        "platform": "linkedin",
        "content_type": "post",
        "raw_input": "Why most founders misread PMF signals",
        "persona_card": {
            "writing_voice_descriptor": "Direct SaaS founder",
            "content_niche_signature": "B2B SaaS",
            "inferred_audience_profile": "Startup founders",
            "tone": "Professional",
            "hook_style": "Bold statement",
            "regional_english": "US",
            "content_goal": "Build thought leadership",
        },
        "commander_output": {},
        "scout_output": {},
        "thinker_output": {},
        "writer_output": {},
        "qc_output": {},
        "draft": "",
        "qc_loop_count": 0,
        "qc_feedback_history": [],
        "debate_results": {},
        "consigliere_review": {},
        "current_agent": "initializing",
        "error": None,
        "final_content": "",
        "anti_rep_prompt": "",
        "media_system_suffix": "",
        "image_urls": [],
        "upload_ids": [],
    }
    defaults.update(kwargs)
    return defaults


def _make_mock_db():
    """Build a MagicMock db with async collection stubs."""
    db = MagicMock()
    db.content_jobs.update_one = AsyncMock(return_value=MagicMock(matched_count=1))
    db.content_jobs.find_one = AsyncMock(return_value=None)
    db.persona_engines.find_one = AsyncMock(return_value=None)
    db.users.find_one = AsyncMock(return_value=None)
    return db


# ===========================================================================
# TestCommanderNode
# ===========================================================================

class TestCommanderNode:
    """Node 1: commander_node updates state with output dict."""

    @pytest.mark.asyncio
    async def test_commander_node_updates_state_with_output(self):
        """commander_node returns dict with commander_output and current_agent=commander."""
        orch = _import_orchestrator()
        mock_db = _make_mock_db()

        commander_result = {
            "content_type": "post",
            "primary_angle": "Founders misread PMF",
            "hook_approach": "bold_claim",
            "key_points": ["k1", "k2"],
            "research_needed": True,
            "research_query": "pmf stats",
            "structure": "numbered_list",
            "estimated_word_count": 220,
            "cta_approach": "question",
            "persona_notes": "Use first-person",
        }

        with patch("agents.orchestrator.db", mock_db), \
             patch("agents.orchestrator.db.content_jobs.update_one", AsyncMock()), \
             patch("agents.commander.run_commander", new_callable=AsyncMock) as mock_cmd:
            mock_cmd.return_value = commander_result

            # Patch the lazy import inside commander_node
            with patch("agents.orchestrator.db", mock_db):
                mock_db.persona_engines.find_one = AsyncMock(return_value={"card": {}})
                mock_db.users.find_one = AsyncMock(return_value={"name": "Test User"})

                state = _base_state()
                result = await orch.commander_node(state)

        assert "commander_output" in result
        assert result["current_agent"] == "commander"
        assert result["commander_output"].get("primary_angle") == "Founders misread PMF"

    @pytest.mark.asyncio
    async def test_commander_node_loads_persona_from_db(self):
        """commander_node uses persona_card already in state (loaded by run_orchestrated_pipeline)."""
        orch = _import_orchestrator()
        mock_db = _make_mock_db()

        persona_in_state = {
            "writing_voice_descriptor": "Startup CTO voice",
            "content_niche_signature": "Engineering leadership",
            "inferred_audience_profile": "Engineering managers",
            "tone": "Direct",
            "hook_style": "Bold claim",
            "regional_english": "US",
            "content_goal": "Build brand",
        }

        captured = {}

        async def capture_commander(raw_input, platform, content_type, persona_card,
                                    anti_rep_prompt="", media_system_suffix="",
                                    image_urls=None, **kwargs):
            captured["persona_card"] = persona_card
            return {
                "content_type": content_type,
                "primary_angle": "test angle",
                "hook_approach": "bold_claim",
                "key_points": [],
                "research_needed": False,
                "structure": "list",
                "estimated_word_count": 200,
                "cta_approach": "question",
                "persona_notes": "",
                "research_query": "test",
            }

        with patch("agents.orchestrator.db", mock_db), \
             patch("agents.commander.run_commander", side_effect=capture_commander):
            state = _base_state(persona_card=persona_in_state)
            result = await orch.commander_node(state)

        assert captured.get("persona_card") == persona_in_state, (
            "commander_node should pass the persona_card from state to run_commander"
        )

    @pytest.mark.asyncio
    async def test_commander_node_sets_error_on_exception(self):
        """commander_node raises when run_commander raises (error propagates up)."""
        orch = _import_orchestrator()
        mock_db = _make_mock_db()

        with patch("agents.orchestrator.db", mock_db), \
             patch("agents.commander.run_commander",
                   new_callable=AsyncMock) as mock_cmd:
            mock_cmd.side_effect = RuntimeError("Commander exploded")

            state = _base_state()
            with pytest.raises(RuntimeError, match="Commander exploded"):
                await orch.commander_node(state)


# ===========================================================================
# TestScoutNode
# ===========================================================================

class TestScoutNode:
    """Node 2: scout_node updates state with research output."""

    @pytest.mark.asyncio
    async def test_scout_node_returns_research_output(self):
        """scout_node returns dict with scout_output when run_scout succeeds."""
        orch = _import_orchestrator()
        mock_db = _make_mock_db()

        scout_result = {
            "findings": "• PMF found by < 20% of startups on first attempt",
            "citations": ["https://example.com"],
            "sources_found": 1,
        }

        with patch("agents.orchestrator.db", mock_db), \
             patch("agents.scout.run_scout", new_callable=AsyncMock) as mock_scout:
            mock_scout.return_value = scout_result

            state = _base_state(
                commander_output={
                    "research_needed": True,
                    "research_query": "PMF stats 2025",
                    "primary_angle": "test",
                }
            )
            result = await orch.scout_node(state)

        assert "scout_output" in result
        assert result["scout_output"]["findings"] == scout_result["findings"]
        assert result["current_agent"] == "scout"

    @pytest.mark.asyncio
    async def test_scout_node_skips_gracefully_when_scout_unavailable(self):
        """scout_node returns empty-ish scout_output when run_scout raises."""
        orch = _import_orchestrator()
        mock_db = _make_mock_db()

        with patch("agents.orchestrator.db", mock_db), \
             patch("agents.scout.run_scout",
                   new_callable=AsyncMock) as mock_scout:
            mock_scout.side_effect = Exception("Perplexity unreachable")

            state = _base_state(
                commander_output={"research_needed": True, "research_query": "test"}
            )
            result = await orch.scout_node(state)

        # Node should not raise — returns graceful fallback
        assert "scout_output" in result
        assert "findings" in result["scout_output"]

    @pytest.mark.asyncio
    async def test_scout_node_handles_timeout_gracefully(self):
        """scout_node returns fallback scout_output when run_scout times out."""
        import asyncio
        orch = _import_orchestrator()
        mock_db = _make_mock_db()

        with patch("agents.orchestrator.db", mock_db), \
             patch("agents.scout.run_scout",
                   new_callable=AsyncMock) as mock_scout:
            mock_scout.side_effect = asyncio.TimeoutError()

            state = _base_state(
                commander_output={"research_needed": True, "research_query": "test"}
            )
            result = await orch.scout_node(state)

        assert "scout_output" in result
        assert "findings" in result["scout_output"]


# ===========================================================================
# TestThinkerNode
# ===========================================================================

class TestThinkerNode:
    """Node 4: thinker_node updates state with strategy output."""

    @pytest.mark.asyncio
    async def test_thinker_node_updates_state(self):
        """thinker_node returns dict with thinker_output when run_thinker succeeds."""
        orch = _import_orchestrator()
        mock_db = _make_mock_db()

        thinker_result = {
            "angle": "Listen before building",
            "hook_options": ["Most founders build the wrong thing first."],
            "content_structure": [{"section": "Hook", "guidance": "Bold claim"}],
            "key_insight": "PMF is heard not found",
            "differentiation": "First-person with data",
        }

        with patch("agents.orchestrator.db", mock_db), \
             patch("agents.thinker.run_thinker", new_callable=AsyncMock) as mock_thinker:
            mock_thinker.return_value = thinker_result

            state = _base_state(
                commander_output={
                    "primary_angle": "test",
                    "_fatigue_data": {},  # pre-populated by identity_check_node
                },
                scout_output={"findings": "test findings", "citations": [], "sources_found": 0},
            )
            result = await orch.thinker_node(state)

        assert "thinker_output" in result
        assert result["thinker_output"]["angle"] == "Listen before building"
        assert result["current_agent"] == "thinker"

    @pytest.mark.asyncio
    async def test_thinker_node_passes_fatigue_context(self):
        """thinker_node extracts _fatigue_data from commander_output and passes to run_thinker."""
        orch = _import_orchestrator()
        mock_db = _make_mock_db()

        fatigue_data = {
            "shield_status": "warning",
            "risk_factors": [{"detail": "question hooks overused"}],
            "recommendations": ["Use story format"],
        }

        captured = {}

        async def cap_thinker(raw_input, commander_output, scout_output, persona_card,
                               fatigue_context=None, user_id=""):
            captured["fatigue_context"] = fatigue_context
            return {
                "angle": "test", "hook_options": ["hook"],
                "content_structure": [], "key_insight": "insight", "differentiation": "diff",
            }

        with patch("agents.orchestrator.db", mock_db), \
             patch("agents.thinker.run_thinker", side_effect=cap_thinker):
            state = _base_state(
                commander_output={
                    "primary_angle": "test",
                    "_fatigue_data": fatigue_data,
                },
                scout_output={"findings": "test", "citations": [], "sources_found": 0},
            )
            await orch.thinker_node(state)

        assert captured.get("fatigue_context") == fatigue_data, (
            "thinker_node should extract _fatigue_data and pass as fatigue_context"
        )


# ===========================================================================
# TestWriterNode
# ===========================================================================

class TestWriterNode:
    """Node 6: writer_node updates state with draft content."""

    @pytest.mark.asyncio
    async def test_writer_node_sets_draft(self):
        """writer_node returns dict with draft key populated from run_writer."""
        orch = _import_orchestrator()
        mock_db = _make_mock_db()

        writer_result = {
            "draft": "Most founders build what they imagine, not what customers need.",
            "word_count": 12,
            "character_count": 70,
            "platform": "linkedin",
            "regional_english": "US",
        }

        with patch("agents.orchestrator.db", mock_db), \
             patch("agents.writer.run_writer", new_callable=AsyncMock) as mock_writer:
            mock_writer.return_value = writer_result

            state = _base_state(
                commander_output={"primary_angle": "test", "cta_approach": "question",
                                  "estimated_word_count": 200},
                thinker_output={
                    "angle": "Listen first",
                    "hook_options": ["Hook"],
                    "content_structure": [],
                    "key_insight": "insight",
                    "differentiation": "diff",
                },
                scout_output={"findings": "test"},
            )
            result = await orch.writer_node(state)

        assert result.get("draft") == writer_result["draft"]
        assert result["current_agent"] == "writer"

    @pytest.mark.asyncio
    async def test_writer_node_handles_empty_response(self):
        """writer_node handles empty dict response from run_writer without raising."""
        orch = _import_orchestrator()
        mock_db = _make_mock_db()

        with patch("agents.orchestrator.db", mock_db), \
             patch("agents.writer.run_writer",
                   new_callable=AsyncMock) as mock_writer:
            mock_writer.return_value = {"draft": "", "word_count": 0}

            state = _base_state(
                commander_output={"primary_angle": "test", "cta_approach": "q",
                                  "estimated_word_count": 200},
                thinker_output={
                    "angle": "test", "hook_options": [],
                    "content_structure": [], "key_insight": "", "differentiation": "",
                },
                scout_output={"findings": ""},
            )
            result = await orch.writer_node(state)

        # Node should not raise — empty draft is a valid (though poor) result
        assert "draft" in result
        assert result["draft"] == ""


# ===========================================================================
# TestQCNode
# ===========================================================================

class TestQCNode:
    """Node 7: qc_node updates state with QC scores and loop count."""

    @pytest.mark.asyncio
    async def test_qc_node_updates_state_with_scores(self):
        """qc_node returns dict with qc_output containing score keys."""
        orch = _import_orchestrator()
        mock_db = _make_mock_db()

        qc_result = {
            "personaMatch": 8.5,
            "aiRisk": 18,
            "platformFit": 9.0,
            "overall_pass": True,
            "feedback": ["Good hook"],
            "suggestions": ["Add a stat"],
            "strengths": ["Strong voice"],
        }

        with patch("agents.orchestrator.db", mock_db), \
             patch("agents.qc.run_qc", new_callable=AsyncMock) as mock_qc:
            mock_qc.return_value = qc_result

            state = _base_state(draft="Some draft content about PMF")
            result = await orch.qc_node(state)

        assert "qc_output" in result
        assert result["qc_output"]["overall_pass"] is True
        assert result["qc_output"]["personaMatch"] == 8.5
        assert result["current_agent"] == "qc"

    @pytest.mark.asyncio
    async def test_qc_node_increments_qc_loop_count(self):
        """qc_node increments qc_loop_count by 1 on each call."""
        orch = _import_orchestrator()
        mock_db = _make_mock_db()

        qc_result = {
            "personaMatch": 6.0, "aiRisk": 40, "platformFit": 7.0,
            "overall_pass": False, "feedback": ["Needs work"], "suggestions": [], "strengths": [],
        }

        with patch("agents.orchestrator.db", mock_db), \
             patch("agents.qc.run_qc", new_callable=AsyncMock) as mock_qc:
            mock_qc.return_value = qc_result

            state = _base_state(draft="Draft", qc_loop_count=1)
            result = await orch.qc_node(state)

        assert result["qc_loop_count"] == 2, (
            f"qc_loop_count should be 2 (was 1), got {result.get('qc_loop_count')}"
        )

    @pytest.mark.asyncio
    async def test_qc_node_appends_feedback_to_history(self):
        """qc_node accumulates QC feedback across loops into qc_feedback_history."""
        orch = _import_orchestrator()
        mock_db = _make_mock_db()

        qc_result = {
            "personaMatch": 6.0, "aiRisk": 40, "platformFit": 7.0,
            "overall_pass": False,
            "feedback": ["Hook is weak"],
            "suggestions": ["Open with a stat"],
            "strengths": [],
        }

        with patch("agents.orchestrator.db", mock_db), \
             patch("agents.qc.run_qc", new_callable=AsyncMock) as mock_qc:
            mock_qc.return_value = qc_result

            # Simulate second loop — history already has entries from loop 1
            state = _base_state(
                draft="Draft",
                qc_loop_count=1,
                qc_feedback_history=["[Loop 1] Previous feedback item"],
            )
            result = await orch.qc_node(state)

        history = result.get("qc_feedback_history", [])
        assert len(history) > 1, "qc_feedback_history should grow after each QC loop"
        # New items should be tagged with current loop number
        new_items = [item for item in history if "Loop 2" in item]
        assert len(new_items) >= 1, "New feedback items should be tagged [Loop 2]"


# ===========================================================================
# TestQualityGate — additional edge cases
# ===========================================================================

class TestQualityGate:
    """quality_gate routing: pass / rewrite / accept transitions."""

    def test_quality_gate_pass_when_overall_pass_true(self):
        """quality_gate returns 'pass' when overall_pass=True."""
        orch = _import_orchestrator()
        state = _base_state(
            qc_output={"overall_pass": True, "personaMatch": 9.0},
            qc_loop_count=0,
        )
        assert orch.quality_gate(state) == "pass"

    def test_quality_gate_rewrite_when_fail_and_loops_remain(self):
        """quality_gate returns 'rewrite' when fail and loops < MAX."""
        orch = _import_orchestrator()
        state = _base_state(
            qc_output={"overall_pass": False},
            qc_loop_count=1,  # MAX is 3
        )
        assert orch.quality_gate(state) == "rewrite"

    def test_quality_gate_accept_when_loops_exhausted(self):
        """quality_gate returns 'accept' when qc_loop_count == MAX_QC_LOOPS."""
        orch = _import_orchestrator()
        max_loops = orch.MAX_QC_LOOPS
        state = _base_state(
            qc_output={"overall_pass": False},
            qc_loop_count=max_loops,
        )
        assert orch.quality_gate(state) == "accept"

    def test_quality_gate_accept_when_loops_exceed_max(self):
        """quality_gate returns 'accept' when qc_loop_count > MAX_QC_LOOPS."""
        orch = _import_orchestrator()
        max_loops = orch.MAX_QC_LOOPS
        state = _base_state(
            qc_output={"overall_pass": False},
            qc_loop_count=max_loops + 5,
        )
        assert orch.quality_gate(state) == "accept"

    def test_quality_gate_handles_missing_qc_output(self):
        """quality_gate handles state with no qc_output gracefully (treats as fail)."""
        orch = _import_orchestrator()
        state = _base_state(qc_output={}, qc_loop_count=0)
        # overall_pass defaults to False when missing — should rewrite or accept
        result = orch.quality_gate(state)
        assert result in ("rewrite", "accept"), (
            f"Expected rewrite or accept for missing qc_output, got '{result}'"
        )


# ===========================================================================
# TestShouldResearch — edge cases not in test_pipeline_integration.py
# ===========================================================================

class TestShouldResearch:
    """should_research routing: True/False/missing key."""

    def test_should_research_true_when_research_needed_true(self):
        """should_research returns True when commander_output.research_needed=True."""
        orch = _import_orchestrator()
        state = _base_state(commander_output={"research_needed": True})
        assert orch.should_research(state) is True

    def test_should_research_false_when_research_needed_false(self):
        """should_research returns False when commander_output.research_needed=False."""
        orch = _import_orchestrator()
        state = _base_state(commander_output={"research_needed": False})
        assert orch.should_research(state) is False

    def test_should_research_true_when_commander_output_missing(self):
        """should_research defaults to True when commander_output is absent."""
        orch = _import_orchestrator()
        # State with no commander_output at all
        state = _base_state()
        state.pop("commander_output", None)
        assert orch.should_research(state) is True, (
            "Safe default: research when we do not know if it is needed"
        )


# ===========================================================================
# TestHookDebateNode
# ===========================================================================

class TestHookDebateNode:
    """Node 5: hook_debate_node scores multiple hooks and selects the winner."""

    @pytest.mark.asyncio
    async def test_hook_debate_scores_multiple_hooks(self):
        """hook_debate_node returns debate_results with selected_hook when LLM is available."""
        orch = _import_orchestrator()
        mock_db = _make_mock_db()

        debate_response = json.dumps({
            "evaluations": [
                {"hook_index": 0, "engagement_potential": 8, "persona_fit": 9,
                 "originality": 7, "total": 24, "reasoning": "Strong bold claim"},
                {"hook_index": 1, "engagement_potential": 7, "persona_fit": 8,
                 "originality": 6, "total": 21, "reasoning": "Good but generic"},
            ],
            "winner_index": 0,
            "winner_hook": "I killed a feature 3 founders begged for. Revenue doubled.",
        })

        mock_chat = MagicMock()
        mock_chat.with_model = MagicMock(return_value=mock_chat)
        mock_chat.send_message = AsyncMock(return_value=debate_response)

        with patch("agents.orchestrator.db", mock_db), \
             patch("agents.orchestrator.LlmChat", return_value=mock_chat), \
             patch("agents.orchestrator.chat_constructor_key", return_value="test-key"), \
             patch("agents.orchestrator.openai_available", return_value=True):
            state = _base_state(
                thinker_output={
                    "angle": "Listen first",
                    "hook_options": [
                        "I killed a feature 3 founders begged for. Revenue doubled.",
                        "PMF is not found. It is heard.",
                    ],
                    "content_structure": [],
                    "key_insight": "insight",
                    "differentiation": "diff",
                }
            )
            result = await orch.hook_debate_node(state)

        assert "debate_results" in result
        debate = result["debate_results"]
        assert "selected_hook" in debate
        assert len(debate["selected_hook"]) > 0

    @pytest.mark.asyncio
    async def test_hook_debate_handles_single_hook(self):
        """hook_debate_node skips debate and returns the single hook directly."""
        orch = _import_orchestrator()
        mock_db = _make_mock_db()

        single_hook = "There is only one path to PMF: listening."

        state = _base_state(
            thinker_output={
                "angle": "Listen first",
                "hook_options": [single_hook],  # only 1 hook
                "content_structure": [],
                "key_insight": "insight",
                "differentiation": "diff",
            }
        )
        result = await orch.hook_debate_node(state)

        assert "debate_results" in result
        debate = result["debate_results"]
        assert debate.get("selected_hook") == single_hook
        assert debate.get("skipped") is True


# ===========================================================================
# TestFinalizeNode
# ===========================================================================

class TestFinalizeNode:
    """Node 10: finalize_node persists final content and updates job status."""

    @pytest.mark.asyncio
    async def test_finalize_sets_final_content_from_draft(self):
        """finalize_node returns final_content equal to state draft."""
        orch = _import_orchestrator()
        mock_db = _make_mock_db()

        draft_text = "Most founders misread PMF signals. I did too. Here is what I learned."

        with patch("agents.orchestrator.db", mock_db):
            state = _base_state(draft=draft_text)
            result = await orch.finalize_node(state)

        assert result.get("final_content") == draft_text
        assert result.get("current_agent") == "done"

    @pytest.mark.asyncio
    async def test_finalize_updates_job_in_db(self):
        """finalize_node calls db.content_jobs.update_one with final status."""
        orch = _import_orchestrator()
        mock_db = _make_mock_db()
        update_spy = AsyncMock(return_value=MagicMock(matched_count=1))
        mock_db.content_jobs.update_one = update_spy

        draft_text = "Most founders misread PMF signals."

        with patch("agents.orchestrator.db", mock_db):
            state = _base_state(draft=draft_text)
            await orch.finalize_node(state)

        update_spy.assert_awaited()
        # Verify the call included the job_id and a "completed" status
        call_args = update_spy.call_args
        filter_arg = call_args[0][0] if call_args[0] else call_args.args[0]
        update_arg = call_args[0][1] if len(call_args[0]) > 1 else call_args.args[1]
        assert filter_arg.get("job_id") == "job_orch_test"
        assert update_arg.get("$set", {}).get("status") == "completed"
