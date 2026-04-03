"""Pipeline integration tests for ThookAI content generation pipeline.

Covers PIPE-02 through PIPE-05 requirements:
- PIPE-02: LangGraph orchestrator compilation, quality gate routing, fallback to legacy
- PIPE-03: UOM directive injection into Thinker and Writer prompts
- PIPE-04: Fatigue shield constraint injection into Thinker prompt
- PIPE-05: Vector store retrieval in Writer and embedding storage in Learning

All integration points verified (Task 2 confirmation — all passed without code fixes):
- orchestrator.build_content_pipeline() compiles without errors
- orchestrator.quality_gate() routes correctly (pass/rewrite/accept)
- orchestrator.should_research() reads research_needed correctly with fallback default=True
- pipeline._run_agent_pipeline_inner() falls back to legacy on ImportError and exceptions
- thinker.run_thinker() injects UOM constraints and fatigue shield data into prompts
- thinker._build_fatigue_prompt_section() builds correct constraint text per shield_status
- writer.run_writer() injects UOM adaptive style directives and style examples from vector store
- writer._fetch_style_examples() queries Pinecone with correct parameters, handles empty/errors
- learning.capture_learning_signal() calls upsert_approved_embedding on approval actions
- learning.capture_learning_signal() does NOT call upsert on rejection actions
"""

import sys
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call

# Ensure backend directory is on path for imports
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)


# ============================================================
# PIPE-02: LangGraph Orchestrator Tests
# ============================================================

def _import_orchestrator_module():
    """Import the orchestrator module, mocking langgraph if not installed.

    Returns the module, or raises ImportError if unavailable for non-langgraph reasons.
    """
    import sys
    import types

    if "langgraph" not in sys.modules:
        # Create minimal mock of langgraph so the orchestrator module can be imported
        lg_mock = types.ModuleType("langgraph")
        lg_graph = types.ModuleType("langgraph.graph")

        class _END_sentinel:
            pass

        class _MockStateGraph:
            def __init__(self, state_schema):
                pass

            def add_node(self, *args, **kwargs):
                pass

            def add_edge(self, *args, **kwargs):
                pass

            def add_conditional_edges(self, *args, **kwargs):
                pass

            def set_entry_point(self, *args, **kwargs):
                pass

            def compile(self):
                mock = MagicMock()
                mock.ainvoke = AsyncMock(return_value={})
                return mock

        lg_graph.END = _END_sentinel()
        lg_graph.StateGraph = _MockStateGraph
        lg_mock.graph = lg_graph
        sys.modules.setdefault("langgraph", lg_mock)
        sys.modules.setdefault("langgraph.graph", lg_graph)

    import importlib
    if "agents.orchestrator" in sys.modules:
        return sys.modules["agents.orchestrator"]
    import agents.orchestrator as orch
    return orch


class TestOrchestratorCompilation:
    """PIPE-02: LangGraph orchestrator builds and compiles correctly."""

    def test_build_content_pipeline_compiles(self):
        """build_content_pipeline() returns a compiled graph object (mocking langgraph if needed)."""
        orch = _import_orchestrator_module()
        pipeline = orch.build_content_pipeline()
        # A compiled LangGraph has an ainvoke method
        assert callable(getattr(pipeline, "ainvoke", None)), (
            "Compiled pipeline must have an ainvoke method"
        )

    def test_pipeline_state_has_required_keys(self):
        """PipelineState TypedDict has all required keys for pipeline operation."""
        orch = _import_orchestrator_module()
        PipelineState = orch.PipelineState

        # Verify all required keys exist in the TypedDict annotations
        annotations = PipelineState.__annotations__
        required_keys = [
            "job_id", "user_id", "platform", "content_type", "raw_input",
            "persona_card", "commander_output", "scout_output", "thinker_output",
            "writer_output", "qc_output", "draft", "qc_loop_count",
            "qc_feedback_history", "debate_results", "current_agent",
            "final_content",
        ]
        for key in required_keys:
            assert key in annotations, f"PipelineState missing required key: {key}"


class TestFallbackToLegacy:
    """PIPE-02: Orchestrator ImportError triggers fallback to legacy pipeline."""

    @pytest.mark.asyncio
    async def test_import_error_falls_back_to_legacy(self):
        """_run_agent_pipeline_inner catches ImportError and calls legacy pipeline."""
        with patch("database.db", MagicMock()):
            with patch("agents.pipeline.run_agent_pipeline_legacy", new_callable=AsyncMock) as mock_legacy:
                mock_legacy.return_value = None

                # Simulate ImportError from orchestrator import
                import builtins
                original_import = builtins.__import__

                def mock_import(name, *args, **kwargs):
                    if name == "agents.orchestrator":
                        raise ImportError("langgraph not available")
                    return original_import(name, *args, **kwargs)

                with patch("builtins.__import__", side_effect=mock_import):
                    from agents.pipeline import _run_agent_pipeline_inner
                    await _run_agent_pipeline_inner(
                        job_id="job_test",
                        user_id="user_test",
                        platform="linkedin",
                        content_type="post",
                        raw_input="test input",
                    )

                mock_legacy.assert_called_once()

    @pytest.mark.asyncio
    async def test_general_exception_falls_back_to_legacy(self):
        """_run_agent_pipeline_inner catches general exceptions and falls back to legacy."""
        with patch("database.db", MagicMock()):
            with patch("agents.pipeline.run_agent_pipeline_legacy", new_callable=AsyncMock) as mock_legacy:
                mock_legacy.return_value = None

                # Ensure orchestrator module is available (mock langgraph if needed)
                orch = _import_orchestrator_module()

                # Patch run_orchestrated_pipeline on the loaded module
                with patch.object(orch, "run_orchestrated_pipeline", new_callable=AsyncMock) as mock_orch:
                    mock_orch.side_effect = RuntimeError("Orchestrator failure")

                    # Import agents.orchestrator first so the pipeline can find it
                    import sys
                    sys.modules.setdefault("agents.orchestrator", orch)

                    from agents.pipeline import _run_agent_pipeline_inner
                    await _run_agent_pipeline_inner(
                        job_id="job_test2",
                        user_id="user_test2",
                        platform="x",
                        content_type="post",
                        raw_input="test fallback",
                    )

                mock_legacy.assert_called_once()


class TestQualityGate:
    """PIPE-02: quality_gate() routes QC results correctly."""

    def test_quality_gate_returns_pass_when_overall_pass_true(self):
        """quality_gate returns 'pass' when overall_pass=True regardless of loop count."""
        orch = _import_orchestrator_module()
        quality_gate = orch.quality_gate

        state = {
            "job_id": "job_1",
            "user_id": "user_1",
            "qc_output": {"overall_pass": True, "personaMatch": 9.0},
            "qc_loop_count": 1,
        }
        result = quality_gate(state)
        assert result == "pass", f"Expected 'pass' but got '{result}'"

    def test_quality_gate_returns_rewrite_when_loops_not_exhausted(self):
        """quality_gate returns 'rewrite' when overall_pass=False and loop_count < MAX_QC_LOOPS."""
        orch = _import_orchestrator_module()
        quality_gate = orch.quality_gate
        MAX_QC_LOOPS = orch.MAX_QC_LOOPS

        state = {
            "job_id": "job_2",
            "user_id": "user_2",
            "qc_output": {"overall_pass": False},
            "qc_loop_count": 1,  # less than MAX_QC_LOOPS (3)
        }
        result = quality_gate(state)
        assert result == "rewrite", f"Expected 'rewrite' but got '{result}'"

    def test_quality_gate_returns_accept_when_loops_exhausted(self):
        """quality_gate returns 'accept' when loops are exhausted (loop_count >= MAX_QC_LOOPS)."""
        orch = _import_orchestrator_module()
        quality_gate = orch.quality_gate
        MAX_QC_LOOPS = orch.MAX_QC_LOOPS

        state = {
            "job_id": "job_3",
            "user_id": "user_3",
            "qc_output": {"overall_pass": False},
            "qc_loop_count": MAX_QC_LOOPS,  # exactly at budget limit
        }
        result = quality_gate(state)
        assert result == "accept", f"Expected 'accept' but got '{result}'"

    def test_quality_gate_accepts_when_loops_exceed_max(self):
        """quality_gate returns 'accept' when loop_count > MAX_QC_LOOPS."""
        orch = _import_orchestrator_module()
        quality_gate = orch.quality_gate
        MAX_QC_LOOPS = orch.MAX_QC_LOOPS

        state = {
            "job_id": "job_4",
            "user_id": "user_4",
            "qc_output": {"overall_pass": False},
            "qc_loop_count": MAX_QC_LOOPS + 5,
        }
        result = quality_gate(state)
        assert result == "accept"


class TestShouldResearch:
    """PIPE-02: should_research() correctly interprets commander output."""

    def test_should_research_returns_true_when_research_needed(self):
        """should_research returns True when commander_output has research_needed=True."""
        orch = _import_orchestrator_module()
        should_research = orch.should_research

        state = {
            "commander_output": {"research_needed": True, "primary_angle": "test"},
        }
        assert should_research(state) is True

    def test_should_research_returns_false_when_research_not_needed(self):
        """should_research returns False when commander_output has research_needed=False."""
        orch = _import_orchestrator_module()
        should_research = orch.should_research

        state = {
            "commander_output": {"research_needed": False},
        }
        assert should_research(state) is False

    def test_should_research_defaults_to_true_when_key_missing(self):
        """should_research defaults to True when research_needed key is absent."""
        orch = _import_orchestrator_module()
        should_research = orch.should_research

        state = {
            "commander_output": {},
        }
        # Default is True (research unless explicitly skipped)
        assert should_research(state) is True


# ============================================================
# PIPE-03: UOM Directive Injection Tests
# ============================================================

THINKER_UOM_DIRECTIVES = {
    "risk_level": "low",
    "hook_complexity": "advanced",
    "max_options": 3,
}

WRITER_UOM_DIRECTIVES = {
    "tone_intensity": "bold",
    "vocabulary_depth": "advanced",
    "content_length": "long",
    "emotional_energy": "high",
    "cta_aggressiveness": "strong",
}


class TestThinkerUOMInjection:
    """PIPE-03: UOM directives are fetched and injected into Thinker prompt."""

    @pytest.mark.asyncio
    async def test_thinker_injects_uom_constraints_into_prompt(self):
        """run_thinker() injects UOM CONSTRAINTS section when directives are returned."""
        captured_prompts = []

        class MockChat:
            def __init__(self, *args, **kwargs):
                pass

            def with_model(self, *args, **kwargs):
                return self

            async def send_message(self, msg):
                captured_prompts.append(msg.text)
                return '{"angle": "test", "hook_options": ["hook1"], "content_structure": [], "key_insight": "insight", "differentiation": "diff"}'

        with patch("agents.thinker.LlmChat", MockChat):
            with patch("agents.thinker.chat_constructor_key", return_value="fake-key"):
                with patch("agents.thinker.openai_available", return_value=True):
                    with patch("services.uom_service.get_agent_directives", new_callable=AsyncMock) as mock_uom:
                        mock_uom.return_value = THINKER_UOM_DIRECTIVES

                        from agents.thinker import run_thinker
                        await run_thinker(
                            raw_input="content about leadership",
                            commander_output={"primary_angle": "leadership"},
                            scout_output={"findings": "some research"},
                            persona_card={"content_niche_signature": "leadership"},
                            user_id="user_uom_test",
                        )

        assert len(captured_prompts) > 0, "No prompts were captured"
        prompt = captured_prompts[0]
        assert "UOM CONSTRAINTS" in prompt, (
            f"UOM CONSTRAINTS not found in thinker prompt. Prompt was:\n{prompt[:500]}"
        )
        assert "low" in prompt or "advanced" in prompt, (
            "UOM directive values not found in prompt"
        )

    @pytest.mark.asyncio
    async def test_thinker_continues_without_uom_on_exception(self):
        """run_thinker() continues without UOM when get_agent_directives raises an exception."""
        captured_prompts = []

        class MockChat:
            def __init__(self, *args, **kwargs):
                pass

            def with_model(self, *args, **kwargs):
                return self

            async def send_message(self, msg):
                captured_prompts.append(msg.text)
                return '{"angle": "test", "hook_options": ["hook1"], "content_structure": [], "key_insight": "insight", "differentiation": "diff"}'

        with patch("agents.thinker.LlmChat", MockChat):
            with patch("agents.thinker.chat_constructor_key", return_value="fake-key"):
                with patch("agents.thinker.openai_available", return_value=True):
                    with patch("services.uom_service.get_agent_directives", new_callable=AsyncMock) as mock_uom:
                        mock_uom.side_effect = ConnectionError("Pinecone down")

                        from agents.thinker import run_thinker
                        result = await run_thinker(
                            raw_input="test input",
                            commander_output={"primary_angle": "test"},
                            scout_output={},
                            persona_card={},
                            user_id="user_fail_test",
                        )

        # Should return a valid thinker dict even though UOM failed
        assert isinstance(result, dict)
        assert "angle" in result


class TestWriterUOMInjection:
    """PIPE-03: UOM directives are fetched and injected into Writer prompt."""

    @pytest.mark.asyncio
    async def test_writer_injects_adaptive_style_directives(self):
        """run_writer() injects ADAPTIVE STYLE DIRECTIVES section when directives are returned."""
        captured_prompts = []

        class MockChat:
            def __init__(self, *args, **kwargs):
                pass

            def with_model(self, *args, **kwargs):
                return self

            async def send_message(self, msg):
                captured_prompts.append(msg.text)
                return "Great leadership post content here."

        with patch("agents.writer.LlmChat", MockChat):
            with patch("agents.writer.chat_constructor_key", return_value="fake-key"):
                with patch("agents.writer.anthropic_available", return_value=True):
                    with patch("services.uom_service.get_agent_directives", new_callable=AsyncMock) as mock_uom:
                        mock_uom.return_value = WRITER_UOM_DIRECTIVES
                        with patch("agents.writer._fetch_style_examples", new_callable=AsyncMock) as mock_style:
                            mock_style.return_value = ""

                            from agents.writer import run_writer
                            await run_writer(
                                platform="linkedin",
                                content_type="post",
                                commander_output={"primary_angle": "leadership", "cta_approach": "question", "estimated_word_count": 200},
                                scout_output={"findings": "research data"},
                                thinker_output={
                                    "angle": "leadership angle",
                                    "hook_options": ["Bold leadership hook"],
                                    "content_structure": [{"section": "Hook", "guidance": "start strong"}],
                                    "key_insight": "the key insight",
                                },
                                persona_card={
                                    "writing_voice_descriptor": "Authentic leader",
                                    "tone": "Confident",
                                    "hook_style": "Bold statement",
                                    "regional_english": "US",
                                    "creator_name": "Test Creator",
                                },
                                user_id="user_writer_uom",
                            )

        assert len(captured_prompts) > 0, "No prompts were captured"
        prompt = captured_prompts[0]
        assert "ADAPTIVE STYLE DIRECTIVES" in prompt, (
            f"ADAPTIVE STYLE DIRECTIVES not found in writer prompt. Prompt was:\n{prompt[:500]}"
        )
        assert "bold" in prompt.lower() or "strong" in prompt.lower(), (
            "UOM directive values not found in prompt"
        )

    @pytest.mark.asyncio
    async def test_writer_continues_without_uom_on_exception(self):
        """run_writer() continues gracefully when get_agent_directives raises an exception."""
        class MockChat:
            def __init__(self, *args, **kwargs):
                pass

            def with_model(self, *args, **kwargs):
                return self

            async def send_message(self, msg):
                return "Content without UOM directives."

        with patch("agents.writer.LlmChat", MockChat):
            with patch("agents.writer.chat_constructor_key", return_value="fake-key"):
                with patch("agents.writer.anthropic_available", return_value=True):
                    with patch("services.uom_service.get_agent_directives", new_callable=AsyncMock) as mock_uom:
                        mock_uom.side_effect = RuntimeError("UOM service down")
                        with patch("agents.writer._fetch_style_examples", new_callable=AsyncMock) as mock_style:
                            mock_style.return_value = ""

                            from agents.writer import run_writer
                            result = await run_writer(
                                platform="linkedin",
                                content_type="post",
                                commander_output={"primary_angle": "test", "cta_approach": "question", "estimated_word_count": 200},
                                scout_output={},
                                thinker_output={
                                    "angle": "test angle",
                                    "hook_options": ["test hook"],
                                    "content_structure": [],
                                    "key_insight": "insight",
                                },
                                persona_card={
                                    "writing_voice_descriptor": "Test",
                                    "tone": "Professional",
                                    "hook_style": "Bold",
                                    "regional_english": "US",
                                    "creator_name": "Test",
                                },
                                user_id="user_no_uom",
                            )

        assert isinstance(result, dict)
        assert "draft" in result


# ============================================================
# PIPE-04: Fatigue Shield Tests
# ============================================================

class TestFatigueShieldPromptSection:
    """PIPE-04: _build_fatigue_prompt_section() builds correct constraint text."""

    def test_returns_empty_string_for_healthy_status(self):
        """_build_fatigue_prompt_section returns empty string when shield_status='healthy'."""
        from agents.thinker import _build_fatigue_prompt_section

        fatigue_context = {
            "shield_status": "healthy",
            "risk_factors": [],
            "recommendations": [],
        }
        result = _build_fatigue_prompt_section(fatigue_context)
        assert result == "", f"Expected empty string for healthy status, got: {repr(result)}"

    def test_returns_empty_string_for_none_context(self):
        """_build_fatigue_prompt_section returns empty string when context is None."""
        from agents.thinker import _build_fatigue_prompt_section

        result = _build_fatigue_prompt_section(None)
        assert result == "", f"Expected empty string for None context, got: {repr(result)}"

    def test_returns_constraint_text_for_warning_status(self):
        """_build_fatigue_prompt_section returns constraint text when status='warning' with risk_factors."""
        from agents.thinker import _build_fatigue_prompt_section

        fatigue_context = {
            "shield_status": "warning",
            "risk_factors": [
                {"factor": "hook_repetition", "detail": "Using bold claims too frequently"},
                {"factor": "topic_overuse", "detail": "Leadership content repeated 5x this week"},
            ],
            "recommendations": ["Try a storytelling format", "Explore contrarian angles"],
        }
        result = _build_fatigue_prompt_section(fatigue_context)

        assert result != "", "Expected non-empty string for warning status"
        assert "CONTENT DIVERSITY CONSTRAINTS" in result, (
            "Expected constraint header in result"
        )
        assert "Using bold claims too frequently" in result, (
            "Expected risk factor detail in result"
        )
        assert "MUST be avoided" in result or "avoid" in result.lower(), (
            "Expected avoidance instruction in result"
        )

    def test_returns_constraint_text_for_critical_status(self):
        """_build_fatigue_prompt_section handles 'critical' shield status."""
        from agents.thinker import _build_fatigue_prompt_section

        fatigue_context = {
            "shield_status": "critical",
            "risk_factors": [
                {"factor": "high_repetition", "detail": "Same hook pattern used 10x"},
            ],
            "recommendations": ["Use a completely different format"],
        }
        result = _build_fatigue_prompt_section(fatigue_context)
        assert result != "", "Expected constraint text for critical status"
        assert "Same hook pattern used 10x" in result

    def test_returns_empty_when_no_overused_patterns_or_recommendations(self):
        """_build_fatigue_prompt_section returns empty when risk_factors have no detail and no recommendations."""
        from agents.thinker import _build_fatigue_prompt_section

        fatigue_context = {
            "shield_status": "warning",
            "risk_factors": [{"factor": "hook_repetition"}],  # No "detail" key
            "recommendations": [],
        }
        result = _build_fatigue_prompt_section(fatigue_context)
        # No detail + no recommendations = nothing to inject
        assert result == "", f"Expected empty string, got: {repr(result)}"


class TestThinkerFatigueInjection:
    """PIPE-04: run_thinker() injects fatigue section into prompt when fatigue is detected."""

    @pytest.mark.asyncio
    async def test_thinker_injects_fatigue_constraints_when_non_healthy(self):
        """run_thinker() injects fatigue shield section into prompt when status is 'warning'."""
        captured_prompts = []

        class MockChat:
            def __init__(self, *args, **kwargs):
                pass

            def with_model(self, *args, **kwargs):
                return self

            async def send_message(self, msg):
                captured_prompts.append(msg.text)
                return '{"angle": "test", "hook_options": ["hook1"], "content_structure": [], "key_insight": "insight", "differentiation": "diff"}'

        warning_fatigue = {
            "shield_status": "warning",
            "risk_factors": [
                {"factor": "hook_repetition", "detail": "Bold claims overused this week"},
            ],
            "recommendations": ["Try storytelling"],
        }

        with patch("agents.thinker.LlmChat", MockChat):
            with patch("agents.thinker.chat_constructor_key", return_value="fake-key"):
                with patch("agents.thinker.openai_available", return_value=True):
                    with patch("services.uom_service.get_agent_directives", new_callable=AsyncMock) as mock_uom:
                        mock_uom.return_value = {}

                        from agents.thinker import run_thinker
                        await run_thinker(
                            raw_input="leadership content",
                            commander_output={"primary_angle": "leadership"},
                            scout_output={},
                            persona_card={},
                            fatigue_context=warning_fatigue,
                            user_id="user_fatigue_test",
                        )

        assert len(captured_prompts) > 0, "No prompts were captured"
        prompt = captured_prompts[0]
        assert "CONTENT DIVERSITY CONSTRAINTS" in prompt, (
            f"Fatigue constraints not injected into prompt. Prompt:\n{prompt[:500]}"
        )
        assert "Bold claims overused this week" in prompt, (
            "Risk factor detail not found in thinker prompt"
        )

    @pytest.mark.asyncio
    async def test_legacy_pipeline_calls_fatigue_shield_before_thinker(self):
        """In legacy pipeline, get_pattern_fatigue_shield is called and result passed to run_thinker."""
        mock_persona = {
            "card": {"content_niche_signature": "leadership"},
        }
        mock_user = {"name": "Test User"}

        with patch("agents.pipeline.db") as mock_db:
            mock_db.persona_engines.find_one = AsyncMock(return_value=mock_persona)
            mock_db.users.find_one = AsyncMock(return_value=mock_user)
            mock_db.content_jobs.update_one = AsyncMock()
            mock_db.content_jobs.find_one = AsyncMock(return_value={"final_content": None})

            with patch("agents.pipeline.get_anti_repetition_context", new_callable=AsyncMock) as mock_anti:
                mock_anti.return_value = {"has_patterns": False}

                with patch("agents.pipeline._build_upload_media_context", new_callable=AsyncMock) as mock_media:
                    mock_media.return_value = ("", [])

                    with patch("agents.pipeline.get_pattern_fatigue_shield", new_callable=AsyncMock) as mock_fatigue:
                        mock_fatigue.return_value = {
                            "shield_status": "warning",
                            "risk_factors": [{"factor": "hook_repetition", "detail": "overused"}],
                            "recommendations": [],
                        }

                        with patch("agents.pipeline.run_commander", new_callable=AsyncMock) as mock_cmd:
                            mock_cmd.return_value = {"primary_angle": "test", "research_needed": False}

                            with patch("agents.pipeline.run_thinker", new_callable=AsyncMock) as mock_thinker:
                                mock_thinker.return_value = {"angle": "test", "hook_options": ["hook"]}

                                with patch("agents.pipeline.run_writer", new_callable=AsyncMock) as mock_writer:
                                    mock_writer.return_value = {"draft": "test content"}

                                    with patch("agents.pipeline.run_qc", new_callable=AsyncMock) as mock_qc:
                                        mock_qc.return_value = {"overall_pass": True, "personaMatch": 8}

                                        from agents.pipeline import run_agent_pipeline_legacy
                                        await run_agent_pipeline_legacy(
                                            job_id="job_fatigue_legacy",
                                            user_id="user_legacy",
                                            platform="linkedin",
                                            content_type="post",
                                            raw_input="test input",
                                        )

            # Verify get_pattern_fatigue_shield was called
            mock_fatigue.assert_called_once_with("user_legacy")

            # Verify run_thinker was called with fatigue_context
            thinker_call_kwargs = mock_thinker.call_args
            fatigue_passed = thinker_call_kwargs.kwargs.get("fatigue_context") or (
                thinker_call_kwargs.args[4] if len(thinker_call_kwargs.args) > 4 else None
            )
            assert fatigue_passed is not None, "fatigue_context not passed to run_thinker"
            assert fatigue_passed.get("shield_status") == "warning"


# ============================================================
# PIPE-05: Vector Store / Pinecone Tests
# ============================================================

class TestFetchStyleExamples:
    """PIPE-05: _fetch_style_examples() queries vector store for similar content."""

    @pytest.mark.asyncio
    async def test_fetch_style_examples_calls_query_with_correct_params(self):
        """_fetch_style_examples calls query_similar_content with correct user_id, raw_input, top_k, threshold."""
        mock_results = [
            {
                "id": "user1_job123",
                "score": 0.88,
                "metadata": {
                    "content_preview": "Leadership is about serving others first...",
                    "platform": "linkedin",
                },
            },
        ]

        with patch("services.vector_store.query_similar_content", new_callable=AsyncMock) as mock_query:
            mock_query.return_value = mock_results

            from agents.writer import _fetch_style_examples
            result = await _fetch_style_examples(
                user_id="user_style_test",
                raw_input="write about leadership",
                platform="linkedin",
            )

        mock_query.assert_called_once_with(
            user_id="user_style_test",
            query_text="write about leadership",
            top_k=3,
            similarity_threshold=0.65,
        )
        assert "PREVIOUSLY APPROVED CONTENT" in result, (
            f"Expected style examples header in result. Got: {repr(result)}"
        )
        assert "Leadership is about serving others first" in result

    @pytest.mark.asyncio
    async def test_fetch_style_examples_returns_empty_when_no_results(self):
        """_fetch_style_examples returns empty string when vector store returns no results."""
        with patch("services.vector_store.query_similar_content", new_callable=AsyncMock) as mock_query:
            mock_query.return_value = []

            from agents.writer import _fetch_style_examples
            result = await _fetch_style_examples(
                user_id="user_no_results",
                raw_input="test query",
                platform="x",
            )

        assert result == "", f"Expected empty string, got: {repr(result)}"

    @pytest.mark.asyncio
    async def test_fetch_style_examples_returns_empty_on_exception(self):
        """_fetch_style_examples returns empty string and logs warning when vector store raises exception."""
        with patch("services.vector_store.query_similar_content", new_callable=AsyncMock) as mock_query:
            mock_query.side_effect = ConnectionError("Pinecone connection failed")

            from agents.writer import _fetch_style_examples
            result = await _fetch_style_examples(
                user_id="user_error_test",
                raw_input="test input",
                platform="linkedin",
            )

        assert result == "", (
            f"Expected empty string on exception, got: {repr(result)}"
        )

    @pytest.mark.asyncio
    async def test_fetch_style_examples_returns_empty_for_no_user_id(self):
        """_fetch_style_examples returns empty string immediately when user_id is empty."""
        with patch("services.vector_store.query_similar_content", new_callable=AsyncMock) as mock_query:
            from agents.writer import _fetch_style_examples
            result = await _fetch_style_examples(
                user_id="",
                raw_input="test input",
                platform="linkedin",
            )

        mock_query.assert_not_called()
        assert result == ""


class TestWriterStyleExamplesInPrompt:
    """PIPE-05: run_writer() includes style examples in prompt when vector store returns results."""

    @pytest.mark.asyncio
    async def test_writer_includes_style_examples_in_prompt(self):
        """run_writer() includes fetched style examples in the writer prompt."""
        captured_prompts = []
        style_examples = (
            "PREVIOUSLY APPROVED CONTENT IN THIS VOICE (match this style closely):\n"
            "Example 1:\nLeadership is about empowering others first.\n"
        )

        class MockChat:
            def __init__(self, *args, **kwargs):
                pass

            def with_model(self, *args, **kwargs):
                return self

            async def send_message(self, msg):
                captured_prompts.append(msg.text)
                return "Well-crafted leadership content."

        with patch("agents.writer.LlmChat", MockChat):
            with patch("agents.writer.chat_constructor_key", return_value="fake-key"):
                with patch("agents.writer.anthropic_available", return_value=True):
                    with patch("agents.writer._fetch_style_examples", new_callable=AsyncMock) as mock_style:
                        mock_style.return_value = style_examples
                        with patch("services.uom_service.get_agent_directives", new_callable=AsyncMock) as mock_uom:
                            mock_uom.return_value = {}

                            from agents.writer import run_writer
                            await run_writer(
                                platform="linkedin",
                                content_type="post",
                                commander_output={"primary_angle": "leadership", "cta_approach": "question", "estimated_word_count": 200},
                                scout_output={"findings": ""},
                                thinker_output={
                                    "angle": "leadership angle",
                                    "hook_options": ["leadership hook"],
                                    "content_structure": [{"section": "Hook", "guidance": "start strong"}],
                                    "key_insight": "insight",
                                },
                                persona_card={
                                    "writing_voice_descriptor": "Authentic leader",
                                    "tone": "Confident",
                                    "hook_style": "Bold statement",
                                    "regional_english": "US",
                                    "creator_name": "Test Creator",
                                },
                                user_id="user_style_prompt_test",
                            )

        assert len(captured_prompts) > 0, "No prompts were captured"
        prompt = captured_prompts[0]
        assert "PREVIOUSLY APPROVED CONTENT" in prompt, (
            f"Style examples not found in writer prompt. Prompt:\n{prompt[:600]}"
        )
        assert "Leadership is about empowering others first" in prompt


class TestLearningEmbeddingStorage:
    """PIPE-05: learning.py calls upsert_approved_embedding on content approval."""

    @pytest.mark.asyncio
    async def test_capture_learning_signal_calls_upsert_approved_embedding(self):
        """record_approval (capture_learning_signal with action='approved') calls upsert_approved_embedding."""
        mock_job_doc = {
            "job_id": "job_learn_1",
            "platform": "linkedin",
            "content_type": "post",
            "was_edited": False,
        }

        with patch("agents.learning.db") as mock_db:
            mock_db.content_jobs.find_one = AsyncMock(return_value=mock_job_doc)
            mock_db.persona_engines.update_one = AsyncMock(
                return_value=MagicMock(modified_count=1)
            )

            with patch("services.vector_store.upsert_approved_embedding", new_callable=AsyncMock) as mock_upsert:
                mock_upsert.return_value = "user_learn_1_job_learn_1"

                with patch("agents.learning.update_uom_after_interaction", new_callable=AsyncMock):
                    with patch("agents.learning.analyze_edit_delta", new_callable=AsyncMock) as mock_analyze:
                        mock_analyze.return_value = {}

                        from agents.learning import capture_learning_signal
                        result = await capture_learning_signal(
                            user_id="user_learn_1",
                            job_id="job_learn_1",
                            original_content="Original AI content here",
                            final_content="Final approved content here",
                            action="approved",
                        )

            # Verify upsert_approved_embedding was called
            mock_upsert.assert_called_once()
            call_kwargs = mock_upsert.call_args

            # Check correct user_id
            assert call_kwargs.kwargs.get("user_id") == "user_learn_1" or (
                len(call_kwargs.args) > 0 and call_kwargs.args[0] == "user_learn_1"
            ), "upsert_approved_embedding called with wrong user_id"

            # Check correct content
            content_arg = call_kwargs.kwargs.get("content_text") or (
                call_kwargs.args[1] if len(call_kwargs.args) > 1 else None
            )
            assert content_arg == "Final approved content here", (
                f"upsert_approved_embedding called with wrong content: {content_arg}"
            )

            # Check correct content_id
            content_id_arg = call_kwargs.kwargs.get("content_id") or (
                call_kwargs.args[2] if len(call_kwargs.args) > 2 else None
            )
            assert content_id_arg == "job_learn_1", (
                f"upsert_approved_embedding called with wrong content_id: {content_id_arg}"
            )

        assert result is True

    @pytest.mark.asyncio
    async def test_capture_learning_signal_does_not_call_upsert_on_rejection(self):
        """capture_learning_signal with action='rejected' does NOT call upsert_approved_embedding."""
        mock_job_doc = {
            "job_id": "job_reject_1",
            "platform": "linkedin",
            "content_type": "post",
            "was_edited": False,
        }

        with patch("agents.learning.db") as mock_db:
            mock_db.content_jobs.find_one = AsyncMock(return_value=mock_job_doc)
            mock_db.persona_engines.update_one = AsyncMock(
                return_value=MagicMock(modified_count=1)
            )

            with patch("services.vector_store.upsert_approved_embedding", new_callable=AsyncMock) as mock_upsert:
                with patch("agents.learning.update_uom_after_interaction", new_callable=AsyncMock):
                    from agents.learning import capture_learning_signal
                    await capture_learning_signal(
                        user_id="user_reject_1",
                        job_id="job_reject_1",
                        original_content="Content that was rejected",
                        final_content="Content that was rejected",
                        action="rejected",
                    )

            mock_upsert.assert_not_called()
