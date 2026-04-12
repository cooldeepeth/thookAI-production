"""Phase 28 — Content Generation Multi-Format tests.

Tests cover CONT-01 through CONT-12. Written in RED state before implementation.
Tests will pass after Plan 02 (backend changes) and Plan 04 (CONT-11/12 fixes).

Run: cd backend && pytest tests/test_content_phase28.py -v
"""
import inspect
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

# Import guard — FORMAT_RULES does not exist until Plan 02 implements it.
# Tests relying on FORMAT_RULES will produce clear FAILED (not ERROR) if not present.
try:
    from agents.writer import FORMAT_RULES
    HAS_FORMAT_RULES = True
except ImportError:
    FORMAT_RULES = {}
    HAS_FORMAT_RULES = False

# Import guard — WORD_COUNT_DEFAULTS does not exist until Plan 02 implements it.
try:
    from agents.commander import WORD_COUNT_DEFAULTS
    HAS_WORD_COUNT_DEFAULTS = True
except ImportError:
    WORD_COUNT_DEFAULTS = {}
    HAS_WORD_COUNT_DEFAULTS = False

# PLATFORM_CONTENT_TYPES — exists now, story_sequence not yet in instagram list
try:
    from routes.content import PLATFORM_CONTENT_TYPES
    HAS_PLATFORM_CONTENT_TYPES = True
except ImportError:
    PLATFORM_CONTENT_TYPES = {}
    HAS_PLATFORM_CONTENT_TYPES = False

# ContentStatusUpdate — already present in routes/content.py
try:
    from routes.content import ContentStatusUpdate
    HAS_STATUS_UPDATE = True
except ImportError:
    ContentStatusUpdate = None
    HAS_STATUS_UPDATE = False

# run_agent_pipeline — already present
try:
    from agents.pipeline import run_agent_pipeline
    HAS_PIPELINE = True
except ImportError:
    run_agent_pipeline = None
    HAS_PIPELINE = False


# ──────────────────────────────────────────────────────────────────────────────
# FORMAT_RULES structure tests  (CONT-09)
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.unit
def test_format_rules_dispatch():
    """CONT-09 — FORMAT_RULES dict must have exactly 8 format-specific keys.

    These 8 keys replace the old 3-key PLATFORM_RULES dict. Each key maps
    to a non-empty string with format-specific writer instructions.
    """
    if not HAS_FORMAT_RULES:
        pytest.fail(
            "FORMAT_RULES not found in agents.writer — must be added in Plan 02. "
            "Expected: from agents.writer import FORMAT_RULES"
        )

    expected_keys = {
        "post",
        "article",
        "carousel_caption",
        "tweet",
        "thread",
        "feed_caption",
        "reel_caption",
        "story_sequence",
    }
    assert isinstance(FORMAT_RULES, dict), "FORMAT_RULES must be a dict"
    assert len(FORMAT_RULES) == 8, (
        f"FORMAT_RULES must have exactly 8 keys. Found {len(FORMAT_RULES)}: {sorted(FORMAT_RULES.keys())}"
    )
    assert set(FORMAT_RULES.keys()) == expected_keys, (
        f"FORMAT_RULES must have exactly these keys: {sorted(expected_keys)}. "
        f"Found: {sorted(FORMAT_RULES.keys())}"
    )
    for key, value in FORMAT_RULES.items():
        assert isinstance(value, str) and len(value) > 0, (
            f"FORMAT_RULES['{key}'] must be a non-empty string"
        )


@pytest.mark.unit
def test_format_rules_content_type_lookup():
    """CONT-09 — FORMAT_RULES values must contain platform-specific markers.

    Verifies that each format rule string contains verifiable output characteristics:
    - tweet: '280' char limit
    - article: '600' or 'words' reference
    - story_sequence: 'Slide' format marker
    - thread: '1/' numbering format
    """
    if not HAS_FORMAT_RULES:
        pytest.fail(
            "FORMAT_RULES not found — will pass after Plan 02 adds it to agents.writer"
        )

    # CONT-04: tweet rule must mention 280-char limit
    assert "280" in FORMAT_RULES["tweet"], (
        "FORMAT_RULES['tweet'] must contain '280' (character limit)"
    )

    # CONT-02: article rule must mention min word count
    article_rule = FORMAT_RULES["article"]
    assert "600" in article_rule or "words" in article_rule.lower(), (
        "FORMAT_RULES['article'] must reference '600' or 'words' (minimum word count guidance)"
    )

    # CONT-08: story_sequence rule must contain slide format marker
    assert "Slide" in FORMAT_RULES["story_sequence"], (
        "FORMAT_RULES['story_sequence'] must contain 'Slide' (slide format marker)"
    )

    # CONT-05: thread rule must contain numbered tweet marker
    assert "1/" in FORMAT_RULES["thread"], (
        "FORMAT_RULES['thread'] must contain '1/' (thread numbering format)"
    )


# ──────────────────────────────────────────────────────────────────────────────
# WORD_COUNT_DEFAULTS tests  (CONT-02, CONT-04, CONT-08)
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.unit
def test_word_count_defaults_exist():
    """CONT-02/04/08 — WORD_COUNT_DEFAULTS dict must guide per-format word count.

    Commander uses these defaults to set estimated_word_count per content_type,
    preventing articles from being too short and tweets from being too long.
    """
    if not HAS_WORD_COUNT_DEFAULTS:
        pytest.fail(
            "WORD_COUNT_DEFAULTS not found in agents.commander — must be added in Plan 02."
        )

    assert isinstance(WORD_COUNT_DEFAULTS, dict), "WORD_COUNT_DEFAULTS must be a dict"
    assert len(WORD_COUNT_DEFAULTS) >= 8, (
        f"WORD_COUNT_DEFAULTS must have at least 8 content_type keys, got {len(WORD_COUNT_DEFAULTS)}"
    )

    # CONT-02: articles must be longer than posts
    assert WORD_COUNT_DEFAULTS.get("article", 0) >= 600, (
        "WORD_COUNT_DEFAULTS['article'] must be >= 600 (articles need substantial length)"
    )

    # CONT-04: tweets must be short — ~280 chars ≈ 40-60 words
    assert WORD_COUNT_DEFAULTS.get("tweet", 999) <= 60, (
        "WORD_COUNT_DEFAULTS['tweet'] must be <= 60 (tweets are short, ~280 chars)"
    )

    # CONT-08: story sequences are brief — 3-5 slides × 15-25 words each
    assert WORD_COUNT_DEFAULTS.get("story_sequence", 999) <= 120, (
        "WORD_COUNT_DEFAULTS['story_sequence'] must be <= 120 (3-5 slides, ~15-25 words each)"
    )


# ──────────────────────────────────────────────────────────────────────────────
# PLATFORM_CONTENT_TYPES allowlist tests  (CONT-08)
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.unit
def test_story_sequence_in_allowlist():
    """CONT-08 — Instagram must allow story_sequence content_type.

    Currently PLATFORM_CONTENT_TYPES['instagram'] only has feed_caption and
    reel_caption. Adding story_sequence is required for CONT-08.
    """
    if not HAS_PLATFORM_CONTENT_TYPES:
        pytest.fail("PLATFORM_CONTENT_TYPES not found in routes.content")

    assert "story_sequence" in PLATFORM_CONTENT_TYPES.get("instagram", []), (
        "PLATFORM_CONTENT_TYPES['instagram'] must include 'story_sequence'"
    )
    assert len(PLATFORM_CONTENT_TYPES.get("instagram", [])) == 3, (
        "PLATFORM_CONTENT_TYPES['instagram'] must have exactly 3 types: "
        "feed_caption, reel_caption, story_sequence"
    )


# ──────────────────────────────────────────────────────────────────────────────
# LinkedIn format tests  (CONT-01, CONT-02, CONT-03)
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.unit
def test_linkedin_post_format():
    """CONT-01 — LinkedIn post FORMAT_RULE must specify character limit and hashtag guidance."""
    if not HAS_FORMAT_RULES:
        pytest.fail("FORMAT_RULES not yet implemented — will pass after Plan 02")

    post_rule = FORMAT_RULES["post"]
    assert (
        "3,000" in post_rule or "3000" in post_rule
    ), "FORMAT_RULES['post'] must reference the 3,000-char LinkedIn post limit"
    assert "hashtag" in post_rule.lower(), (
        "FORMAT_RULES['post'] must contain hashtag guidance"
    )


@pytest.mark.unit
def test_linkedin_article_format():
    """CONT-02 — LinkedIn article FORMAT_RULE must specify min word count and article structure."""
    if not HAS_FORMAT_RULES:
        pytest.fail("FORMAT_RULES not yet implemented — will pass after Plan 02")

    article_rule = FORMAT_RULES["article"]
    assert "600" in article_rule, (
        "FORMAT_RULES['article'] must reference '600' (minimum word count)"
    )
    assert (
        "header" in article_rule.lower() or "headline" in article_rule.lower()
    ), "FORMAT_RULES['article'] must mention header or headline (article structure)"


@pytest.mark.unit
def test_linkedin_carousel_format():
    """CONT-03 — LinkedIn carousel caption FORMAT_RULE must specify char limit and slide tease."""
    if not HAS_FORMAT_RULES:
        pytest.fail("FORMAT_RULES not yet implemented — will pass after Plan 02")

    carousel_rule = FORMAT_RULES["carousel_caption"]
    assert (
        "1,500" in carousel_rule or "1500" in carousel_rule
    ), "FORMAT_RULES['carousel_caption'] must reference the 1,500-char carousel limit"
    assert (
        "Swipe" in carousel_rule
        or "carousel" in carousel_rule.lower()
        or "slides" in carousel_rule.lower()
    ), "FORMAT_RULES['carousel_caption'] must reference carousel/slides/swipe behavior"


# ──────────────────────────────────────────────────────────────────────────────
# X (Twitter) format tests  (CONT-04, CONT-05)
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.unit
def test_x_tweet_under_280():
    """CONT-04 — X tweet FORMAT_RULE must enforce 280-char HARD LIMIT explicitly."""
    if not HAS_FORMAT_RULES:
        pytest.fail("FORMAT_RULES not yet implemented — will pass after Plan 02")

    tweet_rule = FORMAT_RULES["tweet"]
    assert "280" in tweet_rule, (
        "FORMAT_RULES['tweet'] must contain '280' (character limit)"
    )
    assert (
        "HARD" in tweet_rule.upper() and "LIMIT" in tweet_rule.upper()
    ), "FORMAT_RULES['tweet'] must contain 'HARD LIMIT' (case insensitive) to prevent LLM overrun"


@pytest.mark.unit
def test_x_thread_numbered():
    """CONT-05 — X thread FORMAT_RULE must specify numbered tweet format and per-tweet limit."""
    if not HAS_FORMAT_RULES:
        pytest.fail("FORMAT_RULES not yet implemented — will pass after Plan 02")

    thread_rule = FORMAT_RULES["thread"]
    assert "1/" in thread_rule, (
        "FORMAT_RULES['thread'] must contain '1/' (numbered tweet format marker)"
    )
    assert "280" in thread_rule, (
        "FORMAT_RULES['thread'] must contain '280' (per-tweet character limit)"
    )


# ──────────────────────────────────────────────────────────────────────────────
# Instagram format tests  (CONT-06, CONT-07, CONT-08)
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.unit
def test_instagram_feed_hashtags():
    """CONT-06 — Instagram feed caption FORMAT_RULE must specify hashtag count guidance."""
    if not HAS_FORMAT_RULES:
        pytest.fail("FORMAT_RULES not yet implemented — will pass after Plan 02")

    feed_rule = FORMAT_RULES["feed_caption"]
    assert "10" in feed_rule, (
        "FORMAT_RULES['feed_caption'] must contain '10' (hashtag count)"
    )
    assert "hashtag" in feed_rule.lower(), (
        "FORMAT_RULES['feed_caption'] must mention hashtags"
    )


@pytest.mark.unit
def test_instagram_reel_format():
    """CONT-07 — Instagram reel FORMAT_RULE must be reel/script-specific."""
    if not HAS_FORMAT_RULES:
        pytest.fail("FORMAT_RULES not yet implemented — will pass after Plan 02")

    reel_rule = FORMAT_RULES["reel_caption"]
    assert (
        "script" in reel_rule.lower()
        or "talking point" in reel_rule.lower()
        or "Reel" in reel_rule
    ), (
        "FORMAT_RULES['reel_caption'] must contain 'script', 'talking point', or 'Reel' "
        "(reel-specific content type indicator)"
    )


@pytest.mark.unit
def test_instagram_story_sequence():
    """CONT-08 — Instagram story FORMAT_RULE must specify slide format and count."""
    if not HAS_FORMAT_RULES:
        pytest.fail("FORMAT_RULES not yet implemented — will pass after Plan 02")

    story_rule = FORMAT_RULES["story_sequence"]
    assert "Slide 1:" in story_rule, (
        "FORMAT_RULES['story_sequence'] must contain 'Slide 1:' (slide format marker)"
    )
    assert (
        "3" in story_rule or "5" in story_rule
    ), "FORMAT_RULES['story_sequence'] must reference slide count (3 or 5)"


# ──────────────────────────────────────────────────────────────────────────────
# Approve + schedule tests  (CONT-11)
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.unit
def test_approve_and_schedule():
    """CONT-11 — ContentStatusUpdate Pydantic model must accept 'approved' and reject invalid values."""
    if not HAS_STATUS_UPDATE:
        pytest.fail("ContentStatusUpdate not found in routes.content")

    # Must accept 'approved'
    model = ContentStatusUpdate(status="approved")
    assert model.status == "approved", "ContentStatusUpdate must accept status='approved'"

    # Must accept 'rejected'
    model2 = ContentStatusUpdate(status="rejected")
    assert model2.status == "rejected", "ContentStatusUpdate must accept status='rejected'"

    # Must reject invalid status values
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        ContentStatusUpdate(status="invalid_status")

    with pytest.raises(ValidationError):
        ContentStatusUpdate(status="pending")


# ──────────────────────────────────────────────────────────────────────────────
# Pipeline stage progression tests  (CONT-12)
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.unit
def test_pipeline_stage_progression():
    """CONT-12 — run_agent_pipeline must accept all required pipeline parameters.

    Verifies the function signature without executing the pipeline (no LLM calls).
    The signature must include job_id, platform, content_type, raw_input, user_id.
    """
    if not HAS_PIPELINE:
        pytest.fail("run_agent_pipeline not found in agents.pipeline")

    sig = inspect.signature(run_agent_pipeline)
    params = set(sig.parameters.keys())

    required_params = {"job_id", "user_id", "platform", "content_type", "raw_input"}
    missing = required_params - params
    assert not missing, (
        f"run_agent_pipeline is missing required parameters: {sorted(missing)}. "
        f"Found parameters: {sorted(params)}"
    )


# ──────────────────────────────────────────────────────────────────────────────
# Integration: run_writer uses FORMAT_RULES (mock LLM)  (CONT-09)
# ──────────────────────────────────────────────────────────────────────────────

class TestRunWriterFormatRulesIntegration:
    """run_writer() correctly passes format-specific rules to the LLM prompt."""

    @pytest.mark.asyncio
    async def test_run_writer_uses_format_rules_for_tweet(self):
        """CONT-09 — When content_type='tweet', the Writer prompt must include tweet FORMAT_RULES."""
        if not HAS_FORMAT_RULES:
            pytest.fail("FORMAT_RULES not yet implemented — will pass after Plan 02")

        captured_prompt = {}

        async def mock_send_message(message):
            captured_prompt["text"] = message.text
            return "This is a short tweet."

        mock_chat = MagicMock()
        mock_chat.send_message = mock_send_message
        mock_chat.with_model = MagicMock(return_value=mock_chat)

        with patch("agents.writer.anthropic_available", return_value=True), \
             patch("agents.writer.LlmChat", return_value=mock_chat), \
             patch("agents.writer._fetch_style_examples", new_callable=AsyncMock, return_value=""):
            from agents.writer import run_writer
            await run_writer(
                platform="x",
                content_type="tweet",
                commander_output={
                    "raw_input": "test",
                    "estimated_word_count": 45,
                    "cta_approach": "question",
                },
                scout_output={"findings": ""},
                thinker_output={
                    "angle": "test angle",
                    "hook_options": ["hook"],
                    "content_structure": [],
                    "key_insight": "insight",
                },
                persona_card={
                    "creator_name": "Test User",
                    "writing_voice_descriptor": "direct",
                    "tone": "casual",
                    "hook_style": "bold",
                    "writing_style_notes": ["be concise"],
                },
            )
        assert "280" in captured_prompt.get("text", ""), (
            "Tweet format rule (280 chars) must appear in Writer LLM prompt"
        )
        assert "HARD LIMIT" in captured_prompt.get("text", ""), (
            "HARD LIMIT must appear in tweet Writer LLM prompt"
        )

    @pytest.mark.asyncio
    async def test_run_writer_uses_format_rules_for_article(self):
        """CONT-09 — When content_type='article', the Writer prompt must include article FORMAT_RULES."""
        if not HAS_FORMAT_RULES:
            pytest.fail("FORMAT_RULES not yet implemented — will pass after Plan 02")

        captured_prompt = {}

        async def mock_send_message(message):
            captured_prompt["text"] = message.text
            return "# My Article\n\n## Section 1\n\nContent here...\n" * 10

        mock_chat = MagicMock()
        mock_chat.send_message = mock_send_message
        mock_chat.with_model = MagicMock(return_value=mock_chat)

        with patch("agents.writer.anthropic_available", return_value=True), \
             patch("agents.writer.LlmChat", return_value=mock_chat), \
             patch("agents.writer._fetch_style_examples", new_callable=AsyncMock, return_value=""):
            from agents.writer import run_writer
            await run_writer(
                platform="linkedin",
                content_type="article",
                commander_output={
                    "raw_input": "test",
                    "estimated_word_count": 800,
                    "cta_approach": "question",
                },
                scout_output={"findings": ""},
                thinker_output={
                    "angle": "test",
                    "hook_options": ["hook"],
                    "content_structure": [],
                    "key_insight": "insight",
                },
                persona_card={
                    "creator_name": "Test User",
                    "writing_voice_descriptor": "expert",
                    "tone": "professional",
                    "hook_style": "story",
                    "writing_style_notes": ["be thorough"],
                },
            )
        assert "600" in captured_prompt.get("text", ""), (
            "Article format rule (600 words) must appear in Writer LLM prompt"
        )
