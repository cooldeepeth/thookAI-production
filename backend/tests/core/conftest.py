"""Shared fixtures for tests/core/ — isolated pipeline agent and orchestrator tests.

Provides deterministic LLM mocking, persona card factory, pipeline state factory,
and mock DB collections. All tests in this package use these fixtures to avoid
any real network calls.
"""

import json
import os
import sys
from contextlib import contextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Ensure backend directory is on the Python path for imports.
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)


# ---------------------------------------------------------------------------
# Default return values
# ---------------------------------------------------------------------------

_DEFAULT_COMMANDER_JSON = json.dumps({
    "content_type": "post",
    "primary_angle": "Why most founders get product-market fit backwards",
    "hook_approach": "bold_claim",
    "key_points": ["Listen before building", "Revenue before features", "Data beats opinion"],
    "research_needed": True,
    "research_query": "product-market fit statistics 2025",
    "structure": "numbered_list",
    "estimated_word_count": 220,
    "cta_approach": "question",
    "persona_notes": "Use first-person, start bold, end with a question.",
})

_DEFAULT_THINKER_JSON = json.dumps({
    "angle": "Most founders waste years chasing features instead of listening to customers",
    "hook_options": [
        "I killed a feature 3 founders begged me to build. Revenue doubled.",
        "Product-market fit isn't found. It's heard.",
    ],
    "content_structure": [
        {"section": "Hook", "guidance": "Open with counter-intuitive statement"},
        {"section": "Body", "guidance": "3 lessons from listening over building"},
        {"section": "Insight", "guidance": "The core truth: customers tell you what to build"},
        {"section": "CTA", "guidance": "Ask readers what signal told them they had PMF"},
    ],
    "key_insight": "The fastest path to PMF is listening, not iterating on assumptions",
    "differentiation": "First-person failure story combined with concrete revenue data",
})

_DEFAULT_QC_JSON = json.dumps({
    "personaMatch": 8.5,
    "aiRisk": 18,
    "platformFit": 9.0,
    "overall_pass": True,
    "feedback": ["Good hook, could add a specific metric"],
    "suggestions": ["Consider opening with the failure year for more impact"],
    "strengths": ["Strong first-person voice", "Clear key insight", "Tight CTA"],
})


# ---------------------------------------------------------------------------
# LLM mock factory
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_llm_generate():
    """Factory: patches LlmChat.send_message to return a deterministic AsyncMock.

    Usage::

        def test_something(mock_llm_generate):
            with mock_llm_generate(_DEFAULT_COMMANDER_JSON) as mock:
                result = await run_commander(...)
                mock.assert_awaited()
    """
    @contextmanager
    def _factory(return_value: str = _DEFAULT_COMMANDER_JSON):
        with patch("services.llm_client.LlmChat.send_message", new_callable=AsyncMock) as m:
            m.return_value = return_value
            yield m
    return _factory


# ---------------------------------------------------------------------------
# Persona card factory
# ---------------------------------------------------------------------------

@pytest.fixture
def make_persona_card():
    """Factory fixture returning a complete, realistic persona dict.

    Call with keyword overrides to customise specific fields::

        card = make_persona_card(tone="casual", regional_english="IN")
    """
    def _factory(**kwargs) -> dict:
        defaults = {
            "writing_voice_descriptor": "Direct, data-backed founder with earned opinions",
            "content_niche_signature": "B2B SaaS growth and product strategy",
            "inferred_audience_profile": "Startup founders and product managers",
            "tone": "Professional yet conversational",
            "hook_style": "Bold statement",
            "regional_english": "US",
            "content_goal": "Build thought leadership and drive inbound",
            "creator_name": "Alex Chen",
            "writing_style_notes": [
                "Write with authenticity and directness",
                "Use first-person throughout",
                "Back claims with specific numbers or examples",
            ],
        }
        defaults.update(kwargs)
        return defaults
    return _factory


# ---------------------------------------------------------------------------
# Pipeline state factory
# ---------------------------------------------------------------------------

@pytest.fixture
def make_pipeline_state(make_persona_card):
    """Factory returning a minimal PipelineState dict with sensible defaults.

    Usage::

        state = make_pipeline_state(platform="x", qc_loop_count=2)
    """
    def _factory(**kwargs) -> dict:
        defaults = {
            "job_id": "job_test_001",
            "user_id": "user_test_001",
            "platform": "linkedin",
            "content_type": "post",
            "raw_input": "Why most founders get product-market fit backwards",
            "persona_card": make_persona_card(),
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
    return _factory


# ---------------------------------------------------------------------------
# Mock DB collections
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_db_collections():
    """Patches database.db with an AsyncMock providing all standard collections.

    Each collection exposes find_one, update_one, insert_one, find, count_documents
    as AsyncMocks so tests can configure return values without a real DB.
    """
    def _make_collection():
        col = MagicMock()
        col.find_one = AsyncMock(return_value=None)
        col.update_one = AsyncMock(return_value=MagicMock(matched_count=1))
        col.insert_one = AsyncMock(return_value=MagicMock(inserted_id="mock_id"))
        col.find = MagicMock(return_value=MagicMock(
            to_list=AsyncMock(return_value=[]),
            __aiter__=MagicMock(return_value=iter([])),
        ))
        col.count_documents = AsyncMock(return_value=0)
        return col

    mock = MagicMock()
    mock.persona_engines = _make_collection()
    mock.content_jobs = _make_collection()
    mock.users = _make_collection()
    mock.platform_tokens = _make_collection()
    mock.scheduled_posts = _make_collection()
    mock.workspace_members = _make_collection()

    with patch("database.db", mock):
        yield mock
