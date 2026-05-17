"""Tests for Emoji handler."""

import pytest
from src.handlers.emoji_handler import EmojiHandler, get_emoji_handler, EMOJI_AVAILABLE


class TestEmojiHandler:
    """Test EmojiHandler functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.handler = EmojiHandler()

    def test_process_simple_emoji(self):
        """Test converting simple emoji shortcode."""
        text = "Hello :smile: world"
        result = self.handler.process_emoji(text)
        # Should convert :smile: to 😄
        assert "😄" in result
        assert ":smile:" not in result

    def test_process_multiple_emojis(self):
        """Test converting multiple emoji shortcodes."""
        text = "I feel :heart: and :fire: today!"
        result = self.handler.process_emoji(text)
        assert "❤️" in result
        assert "🔥" in result

    def test_no_conversion_in_code_block(self):
        """Test that emoji in code blocks are NOT converted."""
        text = "Check this code: `const emoji = ':smile:'` and this :heart:"
        result = self.handler.process_emoji(text)
        # :smile: in inline code should NOT be converted
        assert ":smile:" in result
        # :heart: outside code should be converted
        assert "❤️" in result

    def test_no_conversion_in_fenced_code_block(self):
        """Test that emoji in fenced code blocks are NOT converted."""
        text = """
```python
emoji = ":smile:"
print(emoji)
```

Outside: :fire:
"""
        result = self.handler.process_emoji(text)
        # :smile: in code block should NOT be converted
        assert ":smile:" in result
        # :fire: outside should be converted
        assert "🔥" in result

    def test_unknown_shortcode_unchanged(self):
        """Test that unknown shortcodes remain unchanged."""
        text = "This is :unknown_emoji: here"
        result = self.handler.process_emoji(text)
        # Unknown shortcode should remain unchanged
        assert ":unknown_emoji:" in result

    def test_empty_text(self):
        """Test processing empty text."""
        assert self.handler.process_emoji("") == ""

    def test_text_without_emojis(self):
        """Test text without any emoji shortcodes."""
        text = "Just plain text without emojis."
        assert self.handler.process_emoji(text) == text

    def test_has_emoji_shortcode_true(self):
        """Test detection of emoji shortcodes."""
        text = "Hello :smile: world"
        assert self.handler.has_emoji_shortcode(text) is True

    def test_has_emoji_shortcode_false(self):
        """Test no emoji shortcodes detected."""
        text = "Just plain text"
        assert self.handler.has_emoji_shortcode(text) is False

    def test_has_emoji_shortcode_in_code_block(self):
        """Test that shortcode in code block is not detected."""
        text = "`:smile:`"
        assert self.handler.has_emoji_shortcode(text) is False

    def test_singleton_get_emoji_handler(self):
        """Test singleton pattern."""
        handler1 = get_emoji_handler()
        handler2 = get_emoji_handler()
        assert handler1 is handler2

    @pytest.mark.skipif(not EMOJI_AVAILABLE, reason="emoji library not installed")
    def test_demojize(self):
        """Test demojize function (requires emoji library)."""
        text = "Hello 😄 world"
        result = self.handler.demojize(text)
        assert ":smile:" in result or "smile" in result.lower()