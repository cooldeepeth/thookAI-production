"""
Phase 28: Content Generation Multi-Format Tests
Tests for CONT-01 through CONT-09 — format-specific Writer prompts,
WORD_COUNT_DEFAULTS in Commander, story_sequence in allowlist.
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock


# ===========================================================================
# CONT-09: FORMAT_RULES dict exists and has correct content
# ===========================================================================

class TestFormatRulesDict:
    """FORMAT_RULES in writer.py has exactly 8 keys with correct values."""

    def test_format_rules_exist(self):
        from agents.writer import FORMAT_RULES
        assert FORMAT_RULES is not None, "FORMAT_RULES must exist in writer.py"

    def test_format_rules_has_8_keys(self):
        from agents.writer import FORMAT_RULES
        assert len(FORMAT_RULES) == 8, f"Expected 8 keys, got {len(FORMAT_RULES)}: {list(FORMAT_RULES.keys())}"

    def test_format_rules_has_all_required_keys(self):
        from agents.writer import FORMAT_RULES
        required_keys = {"post", "article", "carousel_caption", "tweet", "thread", "feed_caption", "reel_caption", "story_sequence"}
        missing = required_keys - set(FORMAT_RULES.keys())
        assert not missing, f"FORMAT_RULES is missing keys: {missing}"

    def test_platform_rules_removed(self):
        """PLATFORM_RULES (old 3-key dict) must NOT exist in writer.py."""
        import agents.writer as writer_module
        assert not hasattr(writer_module, "PLATFORM_RULES"), "PLATFORM_RULES still exists — must be replaced by FORMAT_RULES"

    def test_tweet_rule_has_hard_limit_280(self):
        from agents.writer import FORMAT_RULES
        tweet_rule = FORMAT_RULES["tweet"]
        assert "280" in tweet_rule, "Tweet rule must mention 280 char limit"
        assert "HARD LIMIT" in tweet_rule, "Tweet rule must say 'HARD LIMIT'"

    def test_article_rule_has_min_600_words(self):
        from agents.writer import FORMAT_RULES
        article_rule = FORMAT_RULES["article"]
        assert "600" in article_rule, "Article rule must mention min 600 words"

    def test_story_sequence_rule_has_slide_format(self):
        from agents.writer import FORMAT_RULES
        story_rule = FORMAT_RULES["story_sequence"]
        assert "Slide 1:" in story_rule, "story_sequence rule must include 'Slide 1:' format instruction"

    def test_thread_rule_has_numbering_format(self):
        from agents.writer import FORMAT_RULES
        thread_rule = FORMAT_RULES["thread"]
        assert "1/" in thread_rule or "numbered" in thread_rule.lower(), "Thread rule must reference numbered tweet format"


# ===========================================================================
# CONT-09: FORMAT_RULES content_type lookup in run_writer
# ===========================================================================

class TestFormatRulesLookup:
    """The lookup in run_writer uses content_type as primary key."""

    def test_format_rules_content_type_lookup(self):
        """FORMAT_RULES.get(content_type, ...) pattern must be used — not PLATFORM_RULES.get(platform)."""
        from agents.writer import FORMAT_RULES
        # Simulate lookup behavior: tweet content_type on linkedin platform should get tweet rule
        content_type = "tweet"
        platform = "linkedin"
        result = FORMAT_RULES.get(content_type, FORMAT_RULES.get(platform.lower(), ""))
        assert result == FORMAT_RULES["tweet"], "Lookup by content_type must take precedence over platform"

    def test_format_rules_fallback_for_unknown_content_type(self):
        from agents.writer import FORMAT_RULES
        content_type = "unknown_type"
        platform = "linkedin"
        result = FORMAT_RULES.get(content_type, FORMAT_RULES.get(platform.lower(), "FALLBACK"))
        # Unknown content_type and no platform key => empty string fallback
        assert result == "FALLBACK", "Should fallback gracefully for unknown content_type and platform"

    def test_writer_module_uses_content_type_in_lookup(self):
        """Verify that the writer.py source code uses FORMAT_RULES.get(content_type)."""
        import inspect
        from agents import writer
        source = inspect.getsource(writer)
        assert "FORMAT_RULES.get(content_type" in source, (
            "writer.py must use FORMAT_RULES.get(content_type, ...) for the platform_rules lookup"
        )


# ===========================================================================
# CONT-04: X tweet under 280 characters
# ===========================================================================

class TestXTweetFormat:
    """Tweet FORMAT_RULE enforces 280 char limit in prompt."""

    def test_x_tweet_under_280(self):
        """Tweet rule explicitly states 280 char limit and HARD LIMIT."""
        from agents.writer import FORMAT_RULES
        tweet_rule = FORMAT_RULES["tweet"]
        assert "280" in tweet_rule
        assert "HARD LIMIT" in tweet_rule

    def test_x_tweet_rule_is_concise(self):
        """Tweet rule should be present and focused."""
        from agents.writer import FORMAT_RULES
        tweet_rule = FORMAT_RULES["tweet"]
        assert len(tweet_rule) > 50, "Tweet rule should provide meaningful instructions"


# ===========================================================================
# CONT-05: X thread numbered format
# ===========================================================================

class TestXThreadFormat:
    """Thread FORMAT_RULE specifies numbered tweet format."""

    def test_x_thread_numbered(self):
        from agents.writer import FORMAT_RULES
        thread_rule = FORMAT_RULES["thread"]
        # Rule must mention the numbered format (1/ through n/ or similar)
        has_numbering = "1/" in thread_rule or "'1/'" in thread_rule or "numbered" in thread_rule.lower()
        assert has_numbering, "Thread rule must specify numbered tweet format (1/, 2/, etc.)"

    def test_x_thread_per_tweet_limit(self):
        from agents.writer import FORMAT_RULES
        thread_rule = FORMAT_RULES["thread"]
        assert "280" in thread_rule, "Thread rule must specify 280 char limit per tweet"


# ===========================================================================
# CONT-08: Instagram story_sequence
# ===========================================================================

class TestInstagramStorySequence:
    """story_sequence FORMAT_RULE creates slide-based format."""

    def test_instagram_story_sequence(self):
        from agents.writer import FORMAT_RULES
        story_rule = FORMAT_RULES["story_sequence"]
        assert "Slide 1:" in story_rule, "story_sequence rule must include 'Slide 1:' format"

    def test_story_sequence_multi_slide(self):
        from agents.writer import FORMAT_RULES
        story_rule = FORMAT_RULES["story_sequence"]
        # Must mention at least Slide 1 and Slide 3
        assert "Slide 1:" in story_rule, "Must mention Slide 1"
        assert "Slide 3:" in story_rule or "Slide 2:" in story_rule, "Must mention multiple slides"


# ===========================================================================
# Task 2: WORD_COUNT_DEFAULTS in commander.py
# ===========================================================================

class TestWordCountDefaults:
    """WORD_COUNT_DEFAULTS dict in commander.py."""

    def test_word_count_defaults_exist(self):
        from agents.commander import WORD_COUNT_DEFAULTS
        assert WORD_COUNT_DEFAULTS is not None

    def test_word_count_defaults_has_8_keys(self):
        from agents.commander import WORD_COUNT_DEFAULTS
        assert len(WORD_COUNT_DEFAULTS) == 8, f"Expected 8 keys, got {len(WORD_COUNT_DEFAULTS)}"

    def test_word_count_article_min_600(self):
        from agents.commander import WORD_COUNT_DEFAULTS
        assert WORD_COUNT_DEFAULTS["article"] >= 600, "Article word count must be >= 600"

    def test_word_count_tweet_max_60(self):
        from agents.commander import WORD_COUNT_DEFAULTS
        assert WORD_COUNT_DEFAULTS["tweet"] <= 60, "Tweet word count must be <= 60 (approx 280 chars)"

    def test_word_count_has_all_required_keys(self):
        from agents.commander import WORD_COUNT_DEFAULTS
        required_keys = {"post", "article", "carousel_caption", "tweet", "thread", "feed_caption", "reel_caption", "story_sequence"}
        missing = required_keys - set(WORD_COUNT_DEFAULTS.keys())
        assert not missing, f"WORD_COUNT_DEFAULTS is missing keys: {missing}"

    def test_word_count_floor_override_in_commander_source(self):
        """run_commander must apply word count floor after JSON parsing."""
        import inspect
        from agents import commander
        source = inspect.getsource(commander)
        assert "WORD_COUNT_DEFAULTS.get(content_type" in source, (
            "commander.py must use WORD_COUNT_DEFAULTS.get(content_type, ...) for word count override"
        )


# ===========================================================================
# Task 2: story_sequence in backend allowlist
# ===========================================================================

class TestStorySequenceAllowlist:
    """story_sequence must be in PLATFORM_CONTENT_TYPES["instagram"]."""

    def test_story_sequence_in_allowlist(self):
        from routes.content import PLATFORM_CONTENT_TYPES
        assert "story_sequence" in PLATFORM_CONTENT_TYPES["instagram"], (
            "story_sequence must be in PLATFORM_CONTENT_TYPES['instagram']"
        )

    def test_instagram_has_3_content_types(self):
        from routes.content import PLATFORM_CONTENT_TYPES
        assert len(PLATFORM_CONTENT_TYPES["instagram"]) == 3, (
            f"instagram should have 3 content types (feed_caption, reel_caption, story_sequence), "
            f"got {PLATFORM_CONTENT_TYPES['instagram']}"
        )

    def test_instagram_allowlist_contains_all_types(self):
        from routes.content import PLATFORM_CONTENT_TYPES
        expected = {"feed_caption", "reel_caption", "story_sequence"}
        actual = set(PLATFORM_CONTENT_TYPES["instagram"])
        assert actual == expected, f"Expected {expected}, got {actual}"


# ===========================================================================
# Integration: run_writer uses FORMAT_RULES (mock LLM)
# ===========================================================================

class TestRunWriterFormatRulesIntegration:
    """run_writer() correctly passes format-specific rules to the prompt."""

    @pytest.mark.asyncio
    async def test_run_writer_uses_format_rules_for_tweet(self):
        """When content_type='tweet', the Writer prompt should include tweet-specific FORMAT_RULES."""
        from agents.writer import FORMAT_RULES

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
            result = await run_writer(
                platform="x",
                content_type="tweet",
                commander_output={"raw_input": "test", "estimated_word_count": 45, "cta_approach": "question"},
                scout_output={"findings": ""},
                thinker_output={"angle": "test angle", "hook_options": ["hook"], "content_structure": [], "key_insight": "insight"},
                persona_card={"creator_name": "Test User", "writing_voice_descriptor": "direct", "tone": "casual", "hook_style": "bold", "writing_style_notes": ["be concise"]},
            )
        # The prompt should contain the tweet-specific FORMAT_RULES content
        assert "280" in captured_prompt["text"], "Tweet format rule (280 chars) must appear in Writer prompt"
        assert "HARD LIMIT" in captured_prompt["text"], "HARD LIMIT must appear in tweet Writer prompt"

    @pytest.mark.asyncio
    async def test_run_writer_uses_format_rules_for_article(self):
        """When content_type='article', the Writer prompt should include article-specific FORMAT_RULES."""
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
            result = await run_writer(
                platform="linkedin",
                content_type="article",
                commander_output={"raw_input": "test", "estimated_word_count": 800, "cta_approach": "question"},
                scout_output={"findings": ""},
                thinker_output={"angle": "test", "hook_options": ["hook"], "content_structure": [], "key_insight": "insight"},
                persona_card={"creator_name": "Test User", "writing_voice_descriptor": "expert", "tone": "professional", "hook_style": "story", "writing_style_notes": ["be thorough"]},
            )
        assert "600" in captured_prompt["text"], "Article format rule (600 words) must appear in Writer prompt"
