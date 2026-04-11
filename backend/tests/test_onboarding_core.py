"""
Unit tests for onboarding and persona generation (AUTH-05, AUTH-06).

Tests:
- Onboarding questions endpoint structure
- Model name correctness (AUTH-05): must use claude-sonnet-4-20250514
- Persona generation with LLM mock (AUTH-06)
- Smart fallback persona generation
- DB writes (persona_engines + users)
"""
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import List, Dict, Any


# ---------------------------------------------------------------------------
# Test data
# ---------------------------------------------------------------------------

SAMPLE_ANSWERS = [
    {"question_id": 0, "answer": "I am a SaaS founder sharing lessons on product-market fit"},
    {"question_id": 1, "answer": "LinkedIn"},
    {"question_id": 2, "answer": "Bold, Strategic, Human"},
    {"question_id": 3, "answer": "Paul Graham for razor-sharp clarity"},
    {"question_id": 4, "answer": "Crypto speculation, politics"},
    {"question_id": 5, "answer": "Build personal brand"},
    {"question_id": 6, "answer": "1–3 hours"},
]

MOCK_PERSONA_CARD = {
    "writing_voice_descriptor": "Systems-thinker who narrates the founder journey",
    "content_niche_signature": "B2B SaaS growth for technical founders",
    "inferred_audience_profile": "Series A founders, VPs of Engineering, operators",
    "top_content_format": "Long-form LinkedIn posts with numbered frameworks",
    "personality_archetype": "Builder",
    "tone": "Professional yet conversational",
    "regional_english": "US",
    "hook_style": "Bold statements that challenge common assumptions",
    "focus_platforms": ["LinkedIn"],
    "content_pillars": ["Product strategy", "GTM lessons", "Founder psychology"],
    "content_goal": "Generate leads and build authority",
    "burnout_risk": "medium",
    "risk_tolerance": "balanced",
    "strategy_maturity": 3,
    "writing_style_notes": [
        "Direct and data-driven",
        "Uses personal stories to anchor frameworks",
        "Short paragraphs with strategic white space"
    ]
}


# ---------------------------------------------------------------------------
# TestOnboardingQuestions
# ---------------------------------------------------------------------------

class TestOnboardingQuestions:
    """Tests for GET /onboarding/questions endpoint."""

    def test_questions_module_has_7_questions(self):
        """INTERVIEW_QUESTIONS list must have exactly 7 entries."""
        from routes.onboarding import INTERVIEW_QUESTIONS
        assert len(INTERVIEW_QUESTIONS) == 7

    def test_questions_have_required_fields(self):
        """Each question must have id, type, question, and hint."""
        from routes.onboarding import INTERVIEW_QUESTIONS
        for q in INTERVIEW_QUESTIONS:
            assert "id" in q, f"Question missing 'id': {q}"
            assert "type" in q, f"Question missing 'type': {q}"
            assert "question" in q, f"Question missing 'question': {q}"
            assert "hint" in q, f"Question missing 'hint': {q}"

    def test_questions_include_text_type(self):
        """At least one question must be type 'text'."""
        from routes.onboarding import INTERVIEW_QUESTIONS
        types = [q["type"] for q in INTERVIEW_QUESTIONS]
        assert "text" in types

    def test_questions_include_multi_choice_type(self):
        """At least one question must be type 'multi_choice'."""
        from routes.onboarding import INTERVIEW_QUESTIONS
        types = [q["type"] for q in INTERVIEW_QUESTIONS]
        assert "multi_choice" in types

    def test_question_ids_are_sequential(self):
        """Question IDs must be 0 through 6."""
        from routes.onboarding import INTERVIEW_QUESTIONS
        ids = [q["id"] for q in INTERVIEW_QUESTIONS]
        assert ids == list(range(7))


# ---------------------------------------------------------------------------
# TestModelCorrectness (AUTH-05)
# ---------------------------------------------------------------------------

class TestModelCorrectness:
    """
    AUTH-05: Verify generate-persona uses the correct Claude model name.

    The bug documented in CLAUDE.md was using "claude-4-sonnet-20250514"
    instead of "claude-sonnet-4-20250514". These tests verify the correct
    model name is used everywhere in onboarding.py.
    """

    def test_correct_model_name_in_generate_persona_source(self):
        """
        Inspect onboarding module source to confirm correct model name.
        This is AUTH-05: the model must be 'claude-sonnet-4-20250514'.
        """
        import inspect
        import routes.onboarding as onboarding_module
        source = inspect.getsource(onboarding_module)
        # Must NOT contain the wrong model name
        assert "claude-4-sonnet-20250514" not in source, (
            "BUG AUTH-05: Wrong model name 'claude-4-sonnet-20250514' found in onboarding.py. "
            "Must be 'claude-sonnet-4-20250514'."
        )

    def test_correct_model_name_present_in_source(self):
        """Source must contain the correct model name at least twice (analyze-posts + generate-persona)."""
        import inspect
        import routes.onboarding as onboarding_module
        source = inspect.getsource(onboarding_module)
        count = source.count("claude-sonnet-4-20250514")
        assert count >= 2, (
            f"Expected at least 2 occurrences of 'claude-sonnet-4-20250514' in onboarding.py, "
            f"found {count}. Both analyze-posts and generate-persona must use the correct model."
        )

    def test_with_model_called_with_correct_args(self):
        """
        Mock LlmChat to capture with_model() arguments.
        Verifies .with_model("anthropic", "claude-sonnet-4-20250514") is called.
        """
        mock_chat_instance = MagicMock()
        mock_chat_instance.with_model.return_value = mock_chat_instance
        mock_chat_instance.send_message = AsyncMock(return_value=json.dumps(MOCK_PERSONA_CARD))

        mock_db = MagicMock()
        mock_db.persona_engines.update_one = AsyncMock()
        mock_db.users.update_one = AsyncMock()

        with patch("routes.onboarding.anthropic_available", return_value=True), \
             patch("routes.onboarding.LlmChat", return_value=mock_chat_instance) as MockLlmChat, \
             patch("routes.onboarding.db", mock_db):

            import asyncio
            from routes.onboarding import generate_persona
            from pydantic import BaseModel
            from typing import List, Dict, Any, Optional

            class FakeRequest(BaseModel):
                answers: List[Dict[str, Any]]
                posts_analysis: Optional[str] = None
                voice_sample_url: Optional[str] = None
                visual_preference: Optional[str] = None
                writing_samples: Optional[List[str]] = None

            request = FakeRequest(answers=SAMPLE_ANSWERS)
            current_user = {"user_id": "test-user-123"}

            asyncio.run(generate_persona(request, current_user))

            # with_model must be called with exactly these arguments
            mock_chat_instance.with_model.assert_called_once_with("anthropic", "claude-sonnet-4-20250514")


# ---------------------------------------------------------------------------
# TestPersonaGeneration (AUTH-06)
# ---------------------------------------------------------------------------

class TestPersonaGeneration:
    """
    AUTH-06: Persona Engine document has personalized fields from LLM.
    Verifies voice_fingerprint, content_identity, uom, and learning_signals
    are populated in the DB document.
    """

    def _run_generate_persona(self, mock_llm_response: str):
        """Helper: run generate_persona with mocked LLM and DB, return db update args."""
        mock_chat_instance = MagicMock()
        mock_chat_instance.with_model.return_value = mock_chat_instance
        mock_chat_instance.send_message = AsyncMock(return_value=mock_llm_response)

        mock_db = MagicMock()
        captured_docs = []

        async def capture_update(filter_, update, **kwargs):
            captured_docs.append(update.get("$set", {}))
            return MagicMock()

        mock_db.persona_engines.update_one = capture_update
        mock_db.users.update_one = AsyncMock()

        import asyncio
        from routes.onboarding import generate_persona
        from pydantic import BaseModel
        from typing import List, Dict, Any, Optional

        class FakeRequest(BaseModel):
            answers: List[Dict[str, Any]]
            posts_analysis: Optional[str] = None
            voice_sample_url: Optional[str] = None
            visual_preference: Optional[str] = None
            writing_samples: Optional[List[str]] = None

        request = FakeRequest(answers=SAMPLE_ANSWERS)
        current_user = {"user_id": "test-user-456"}

        with patch("routes.onboarding.anthropic_available", return_value=True), \
             patch("routes.onboarding.LlmChat", return_value=mock_chat_instance), \
             patch("routes.onboarding.db", mock_db):
            asyncio.run(generate_persona(request, current_user))

        return captured_docs, mock_db

    def test_persona_doc_has_voice_fingerprint(self):
        """Stored persona_engines doc must have voice_fingerprint field."""
        docs, _ = self._run_generate_persona(json.dumps(MOCK_PERSONA_CARD))
        assert len(docs) > 0, "persona_engines.update_one was never called"
        doc = docs[0]
        assert "voice_fingerprint" in doc, "voice_fingerprint missing from persona doc"

    def test_voice_fingerprint_has_sentence_length_distribution(self):
        """voice_fingerprint must contain sentence_length_distribution."""
        docs, _ = self._run_generate_persona(json.dumps(MOCK_PERSONA_CARD))
        vf = docs[0]["voice_fingerprint"]
        assert "sentence_length_distribution" in vf

    def test_voice_fingerprint_has_vocabulary_complexity(self):
        """voice_fingerprint must contain vocabulary_complexity."""
        docs, _ = self._run_generate_persona(json.dumps(MOCK_PERSONA_CARD))
        vf = docs[0]["voice_fingerprint"]
        assert "vocabulary_complexity" in vf

    def test_persona_doc_has_content_identity(self):
        """Stored persona doc must have content_identity field."""
        docs, _ = self._run_generate_persona(json.dumps(MOCK_PERSONA_CARD))
        doc = docs[0]
        assert "content_identity" in doc, "content_identity missing from persona doc"

    def test_content_identity_has_required_fields(self):
        """content_identity must have topic_clusters, tone, regional_english."""
        docs, _ = self._run_generate_persona(json.dumps(MOCK_PERSONA_CARD))
        ci = docs[0]["content_identity"]
        assert "topic_clusters" in ci
        assert "tone" in ci
        assert "regional_english" in ci

    def test_persona_doc_has_uom(self):
        """Stored persona doc must have uom field."""
        docs, _ = self._run_generate_persona(json.dumps(MOCK_PERSONA_CARD))
        assert "uom" in docs[0], "uom missing from persona doc"

    def test_uom_has_burnout_risk(self):
        """uom must contain burnout_risk."""
        docs, _ = self._run_generate_persona(json.dumps(MOCK_PERSONA_CARD))
        uom = docs[0]["uom"]
        assert "burnout_risk" in uom

    def test_uom_has_risk_tolerance(self):
        """uom must contain risk_tolerance."""
        docs, _ = self._run_generate_persona(json.dumps(MOCK_PERSONA_CARD))
        uom = docs[0]["uom"]
        assert "risk_tolerance" in uom

    def test_uom_has_strategy_maturity(self):
        """uom must contain strategy_maturity."""
        docs, _ = self._run_generate_persona(json.dumps(MOCK_PERSONA_CARD))
        uom = docs[0]["uom"]
        assert "strategy_maturity" in uom

    def test_persona_doc_has_learning_signals(self):
        """Stored persona doc must have learning_signals with empty lists."""
        docs, _ = self._run_generate_persona(json.dumps(MOCK_PERSONA_CARD))
        assert "learning_signals" in docs[0]
        ls = docs[0]["learning_signals"]
        assert isinstance(ls.get("edit_deltas"), list)
        assert isinstance(ls.get("approved_embeddings"), list)
        assert isinstance(ls.get("rejected_patterns"), list)

    def test_onboarding_completed_flag_set_to_true(self):
        """users.update_one must set onboarding_completed to True."""
        mock_chat_instance = MagicMock()
        mock_chat_instance.with_model.return_value = mock_chat_instance
        mock_chat_instance.send_message = AsyncMock(return_value=json.dumps(MOCK_PERSONA_CARD))

        user_updates = []

        async def capture_user_update(filter_, update, **kwargs):
            user_updates.append(update)
            return MagicMock()

        mock_db = MagicMock()
        mock_db.persona_engines.update_one = AsyncMock()
        mock_db.users.update_one = capture_user_update

        import asyncio
        from routes.onboarding import generate_persona
        from pydantic import BaseModel
        from typing import List, Dict, Any, Optional

        class FakeRequest(BaseModel):
            answers: List[Dict[str, Any]]
            posts_analysis: Optional[str] = None
            voice_sample_url: Optional[str] = None
            visual_preference: Optional[str] = None
            writing_samples: Optional[List[str]] = None

        request = FakeRequest(answers=SAMPLE_ANSWERS)
        current_user = {"user_id": "test-user-789"}

        with patch("routes.onboarding.anthropic_available", return_value=True), \
             patch("routes.onboarding.LlmChat", return_value=mock_chat_instance), \
             patch("routes.onboarding.db", mock_db):
            asyncio.run(generate_persona(request, current_user))

        assert len(user_updates) > 0, "users.update_one was never called"
        assert user_updates[0].get("$set", {}).get("onboarding_completed") is True

    def test_generate_persona_requires_authentication(self):
        """
        The endpoint uses Depends(get_current_user) — without auth the route
        dependency would reject the request. We verify get_current_user is
        imported and used via inspection.
        """
        import inspect
        import routes.onboarding as onboarding_module
        source = inspect.getsource(onboarding_module)
        assert "get_current_user" in source, "get_current_user dependency must be in onboarding.py"
        assert "Depends(get_current_user)" in source, "generate_persona must require auth via Depends"

    def test_llm_response_with_markdown_wrapper_is_cleaned(self):
        """Persona card JSON wrapped in markdown code block must be parsed correctly."""
        wrapped_response = f"```json\n{json.dumps(MOCK_PERSONA_CARD)}\n```"
        docs, _ = self._run_generate_persona(wrapped_response)
        assert "card" in docs[0]
        assert docs[0]["card"]["personality_archetype"] == "Builder"

    def test_fallback_used_when_llm_raises(self):
        """When LLM raises an exception, _generate_smart_persona fallback is used."""
        mock_chat_instance = MagicMock()
        mock_chat_instance.with_model.return_value = mock_chat_instance
        mock_chat_instance.send_message = AsyncMock(side_effect=Exception("API timeout"))

        mock_db = MagicMock()
        mock_db.persona_engines.update_one = AsyncMock()
        mock_db.users.update_one = AsyncMock()

        import asyncio
        from routes.onboarding import generate_persona
        from pydantic import BaseModel
        from typing import List, Dict, Any, Optional

        class FakeRequest(BaseModel):
            answers: List[Dict[str, Any]]
            posts_analysis: Optional[str] = None
            voice_sample_url: Optional[str] = None
            visual_preference: Optional[str] = None
            writing_samples: Optional[List[str]] = None

        request = FakeRequest(answers=SAMPLE_ANSWERS)
        current_user = {"user_id": "test-user-fallback"}

        with patch("routes.onboarding.anthropic_available", return_value=True), \
             patch("routes.onboarding.LlmChat", return_value=mock_chat_instance), \
             patch("routes.onboarding.db", mock_db), \
             patch("routes.onboarding._generate_smart_persona", wraps=__import__(
                 "routes.onboarding", fromlist=["_generate_smart_persona"]
             )._generate_smart_persona) as mock_fallback:
            result = asyncio.run(generate_persona(request, current_user))

        # Fallback should have been called
        mock_fallback.assert_called_once()


# ---------------------------------------------------------------------------
# TestSmartFallback
# ---------------------------------------------------------------------------

class TestSmartFallback:
    """Tests for _generate_smart_persona fallback function."""

    def _answers(self, about="", platform="LinkedIn", style="Bold, Clear, Strategic",
                 goal="Build personal brand", time_avail="1–3 hours") -> list:
        return [
            {"question_id": 0, "answer": about},
            {"question_id": 1, "answer": platform},
            {"question_id": 2, "answer": style},
            {"question_id": 5, "answer": goal},
            {"question_id": 6, "answer": time_avail},
        ]

    def test_founder_in_about_gives_builder_archetype(self):
        """'founder' in about answer should produce personality_archetype='Builder' (no bold/provocative in style)."""
        from routes.onboarding import _generate_smart_persona
        # Use a neutral style that doesn't trigger Provocateur (no "bold", "provocative", etc.)
        answers = self._answers(about="I am a SaaS founder building developer tools", style="Clear, Strategic, Analytical")
        result = _generate_smart_persona(answers)
        assert result["personality_archetype"] == "Builder"

    def test_startup_in_about_gives_builder_archetype(self):
        """'startup' keyword should also trigger Builder archetype (no bold/provocative style)."""
        from routes.onboarding import _generate_smart_persona
        # Use a neutral style that doesn't trigger Provocateur
        answers = self._answers(about="Running a startup in fintech", style="Direct, Practical, Data-driven")
        result = _generate_smart_persona(answers)
        assert result["personality_archetype"] == "Builder"

    def test_story_in_about_gives_storyteller_archetype(self):
        """'story' in about should produce personality_archetype='Storyteller'."""
        from routes.onboarding import _generate_smart_persona
        answers = self._answers(about="I share stories about my entrepreneurial journey")
        result = _generate_smart_persona(answers)
        assert result["personality_archetype"] == "Storyteller"

    def test_bold_style_gives_provocateur_archetype(self):
        """'bold' in style words should produce personality_archetype='Provocateur'."""
        from routes.onboarding import _generate_smart_persona
        answers = self._answers(about="Marketing consultant", style="Bold, provocative, disruptive")
        result = _generate_smart_persona(answers)
        assert result["personality_archetype"] == "Provocateur"

    def test_default_archetype_is_educator(self):
        """Without specific keywords, archetype should default to 'Educator'."""
        from routes.onboarding import _generate_smart_persona
        answers = self._answers(about="I share knowledge about software", style="Clear, Concise, Helpful")
        result = _generate_smart_persona(answers)
        assert result["personality_archetype"] == "Educator"

    def test_under_1_hour_gives_high_burnout_risk(self):
        """'Under 1 hour' time availability should produce burnout_risk='high'."""
        from routes.onboarding import _generate_smart_persona
        answers = self._answers(time_avail="Under 1 hour")
        result = _generate_smart_persona(answers)
        assert result["burnout_risk"] == "high"

    def test_1_3_hours_gives_medium_burnout_risk(self):
        """'1–3 hours' time availability should produce burnout_risk='medium'."""
        from routes.onboarding import _generate_smart_persona
        answers = self._answers(time_avail="1–3 hours")
        result = _generate_smart_persona(answers)
        assert result["burnout_risk"] == "medium"

    def test_5_plus_hours_gives_low_burnout_risk(self):
        """'5+ hours' time availability should produce burnout_risk='low'."""
        from routes.onboarding import _generate_smart_persona
        answers = self._answers(time_avail="5+ hours")
        result = _generate_smart_persona(answers)
        assert result["burnout_risk"] == "low"

    def test_all_three_platforms_expands_to_list(self):
        """'All three' platform selection should expand to LinkedIn, X (Twitter), Instagram."""
        from routes.onboarding import _generate_smart_persona
        answers = self._answers(platform="All three")
        result = _generate_smart_persona(answers)
        assert "LinkedIn" in result["focus_platforms"]
        assert "X (Twitter)" in result["focus_platforms"]
        assert "Instagram" in result["focus_platforms"]
        assert len(result["focus_platforms"]) == 3

    def test_linkedin_plus_x_platform_splits_correctly(self):
        """'LinkedIn + X' should split to [LinkedIn, X] list."""
        from routes.onboarding import _generate_smart_persona
        answers = self._answers(platform="LinkedIn + X")
        result = _generate_smart_persona(answers)
        assert len(result["focus_platforms"]) == 2

    def test_single_platform_stays_single(self):
        """Single platform selection should be a list with one element."""
        from routes.onboarding import _generate_smart_persona
        answers = self._answers(platform="LinkedIn")
        result = _generate_smart_persona(answers)
        assert result["focus_platforms"] == ["LinkedIn"]

    def test_empty_answers_returns_valid_persona(self):
        """Empty answers list should still produce a valid persona without exceptions."""
        from routes.onboarding import _generate_smart_persona
        result = _generate_smart_persona([])
        # Must return a dict with all required fields
        required_fields = [
            "writing_voice_descriptor", "personality_archetype", "tone",
            "focus_platforms", "content_pillars", "burnout_risk", "risk_tolerance"
        ]
        for field in required_fields:
            assert field in result, f"Field '{field}' missing from smart fallback result"

    def test_fallback_result_has_all_required_fields(self):
        """Smart fallback must return all fields needed for persona_doc construction."""
        from routes.onboarding import _generate_smart_persona
        answers = self._answers(about="I am a SaaS founder")
        result = _generate_smart_persona(answers)
        required = [
            "writing_voice_descriptor", "content_niche_signature", "inferred_audience_profile",
            "top_content_format", "personality_archetype", "tone", "regional_english",
            "hook_style", "focus_platforms", "content_pillars", "content_goal",
            "burnout_risk", "risk_tolerance", "strategy_maturity", "writing_style_notes"
        ]
        for field in required:
            assert field in result, f"Field '{field}' missing from smart fallback result"


# ---------------------------------------------------------------------------
# Extended test fixtures
# ---------------------------------------------------------------------------

MOCK_PERSONA_CARD_EXTENDED = {
    **MOCK_PERSONA_CARD,
    "personality_traits": ["Analytical", "Strategic", "Authentic"],
    "voice_style": "Direct professional voice with numbered frameworks and data-backed insights",
}


# ---------------------------------------------------------------------------
# TestGeneratePersonaExtendedRequest (ONBD-05)
# ---------------------------------------------------------------------------

class TestGeneratePersonaExtendedRequest:
    """Tests that generate_persona accepts the three new optional request fields."""

    def _run_with_request(self, extra_fields: dict):
        """Run generate_persona with given extra fields and return without exception."""
        mock_chat_instance = MagicMock()
        mock_chat_instance.with_model.return_value = mock_chat_instance
        mock_chat_instance.send_message = AsyncMock(return_value=json.dumps(MOCK_PERSONA_CARD_EXTENDED))

        mock_db = MagicMock()
        mock_db.persona_engines.update_one = AsyncMock()
        mock_db.users.update_one = AsyncMock()

        import asyncio
        from routes.onboarding import generate_persona
        from pydantic import BaseModel
        from typing import List, Dict, Any, Optional

        class FakeExtendedRequest(BaseModel):
            answers: List[Dict[str, Any]]
            posts_analysis: Optional[str] = None
            voice_sample_url: Optional[str] = None
            visual_preference: Optional[str] = None
            writing_samples: Optional[List[str]] = None

        request = FakeExtendedRequest(answers=SAMPLE_ANSWERS, **extra_fields)
        current_user = {"user_id": "test-user-ext"}

        with patch("routes.onboarding.anthropic_available", return_value=True), \
             patch("routes.onboarding.LlmChat", return_value=mock_chat_instance), \
             patch("routes.onboarding.db", mock_db):
            asyncio.run(generate_persona(request, current_user))

    def test_generate_persona_accepts_voice_sample_url(self):
        """generate_persona must accept voice_sample_url field without error."""
        self._run_with_request({"voice_sample_url": "https://r2.example.com/voice.webm"})

    def test_generate_persona_accepts_visual_preference(self):
        """generate_persona must accept visual_preference field without error."""
        self._run_with_request({"visual_preference": "bold"})

    def test_generate_persona_accepts_writing_samples(self):
        """generate_persona must accept writing_samples field without error."""
        self._run_with_request({"writing_samples": ["post1 text", "post2 text"]})

    def test_generate_persona_accepts_all_new_fields_together(self):
        """generate_persona must accept all three new fields simultaneously without error."""
        self._run_with_request({
            "voice_sample_url": "https://r2.example.com/voice.webm",
            "visual_preference": "creative",
            "writing_samples": ["post1", "post2", "post3"],
        })


# ---------------------------------------------------------------------------
# TestNewPersonaFields (ONBD-06)
# ---------------------------------------------------------------------------

class TestNewPersonaFields:
    """Tests that persona_doc written to DB includes the four new fields."""

    def _run_extended(self, visual_preference="bold", writing_samples=None, voice_sample_url=None):
        """Same pattern as TestPersonaGeneration._run_generate_persona but with new fields."""
        mock_chat_instance = MagicMock()
        mock_chat_instance.with_model.return_value = mock_chat_instance
        mock_chat_instance.send_message = AsyncMock(return_value=json.dumps(MOCK_PERSONA_CARD_EXTENDED))

        mock_db = MagicMock()
        captured_docs = []

        async def capture_update(filter_, update, **kwargs):
            captured_docs.append(update.get("$set", {}))
            return MagicMock()

        mock_db.persona_engines.update_one = capture_update
        mock_db.users.update_one = AsyncMock()

        import asyncio
        from routes.onboarding import generate_persona
        from pydantic import BaseModel
        from typing import List, Dict, Any, Optional

        class FakeExtendedRequest(BaseModel):
            answers: List[Dict[str, Any]]
            posts_analysis: Optional[str] = None
            voice_sample_url: Optional[str] = None
            visual_preference: Optional[str] = None
            writing_samples: Optional[List[str]] = None

        request = FakeExtendedRequest(
            answers=SAMPLE_ANSWERS,
            visual_preference=visual_preference,
            writing_samples=writing_samples,
            voice_sample_url=voice_sample_url,
        )
        current_user = {"user_id": "test-user-newfields"}

        with patch("routes.onboarding.anthropic_available", return_value=True), \
             patch("routes.onboarding.LlmChat", return_value=mock_chat_instance), \
             patch("routes.onboarding.db", mock_db):
            asyncio.run(generate_persona(request, current_user))

        assert len(captured_docs) > 0, "persona_engines.update_one was never called"
        return captured_docs[0]

    def test_persona_doc_has_voice_style(self):
        """persona_doc must have voice_style field as a non-empty str."""
        doc = self._run_extended()
        assert "voice_style" in doc, "voice_style missing from persona_doc"
        assert isinstance(doc["voice_style"], str), "voice_style must be a str"

    def test_persona_doc_has_visual_preferences(self):
        """persona_doc must have visual_preferences equal to the visual_preference passed in."""
        doc = self._run_extended(visual_preference="bold")
        assert "visual_preferences" in doc, "visual_preferences missing from persona_doc"
        assert doc["visual_preferences"] == "bold"

    def test_persona_doc_has_writing_samples(self):
        """persona_doc must have writing_samples equal to the list passed in."""
        samples = ["sample post 1", "sample post 2"]
        doc = self._run_extended(writing_samples=samples)
        assert "writing_samples" in doc, "writing_samples missing from persona_doc"
        assert doc["writing_samples"] == samples

    def test_persona_doc_has_personality_traits(self):
        """persona_doc must have personality_traits as a list."""
        doc = self._run_extended()
        assert "personality_traits" in doc, "personality_traits missing from persona_doc"
        assert isinstance(doc["personality_traits"], list)

    def test_visual_preferences_defaults_to_minimal_when_none(self):
        """When visual_preference is None, persona_doc visual_preferences must default to 'minimal'."""
        doc = self._run_extended(visual_preference=None)
        assert doc.get("visual_preferences") == "minimal"

    def test_writing_samples_defaults_to_empty_list_when_none(self):
        """When writing_samples is None, persona_doc writing_samples must default to []."""
        doc = self._run_extended(writing_samples=None)
        assert doc.get("writing_samples") == []


# ---------------------------------------------------------------------------
# TestSmartFallbackNewFields (ONBD-05 / ONBD-06)
# ---------------------------------------------------------------------------

class TestSmartFallbackNewFields:
    """Tests that _generate_smart_persona fallback includes personality_traits and voice_style."""

    def test_smart_fallback_includes_personality_traits(self):
        """_generate_smart_persona must return personality_traits key with at least one element."""
        from routes.onboarding import _generate_smart_persona
        result = _generate_smart_persona(SAMPLE_ANSWERS)
        assert "personality_traits" in result, "personality_traits missing from smart fallback"
        assert isinstance(result["personality_traits"], list)
        assert len(result["personality_traits"]) >= 1

    def test_smart_fallback_includes_voice_style(self):
        """_generate_smart_persona must return voice_style key as a non-empty str."""
        from routes.onboarding import _generate_smart_persona
        result = _generate_smart_persona(SAMPLE_ANSWERS)
        assert "voice_style" in result, "voice_style missing from smart fallback"
        assert isinstance(result["voice_style"], str)
        assert len(result["voice_style"]) > 0

    def test_smart_fallback_personality_traits_are_strings(self):
        """Each element of personality_traits in smart fallback must be a str."""
        from routes.onboarding import _generate_smart_persona
        result = _generate_smart_persona(SAMPLE_ANSWERS)
        for trait in result["personality_traits"]:
            assert isinstance(trait, str), f"personality_traits element must be str, got {type(trait)}"
