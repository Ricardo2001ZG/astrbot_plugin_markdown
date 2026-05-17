"""Emoji shortcode detection and conversion.

Converts emoji shortcodes like :smile: to actual emoji characters using
the Python emoji library.
"""

from __future__ import annotations

import re
from typing import Match

# Try to import emoji library, fall back to basic mapping if unavailable
try:
    import emoji
    EMOJI_AVAILABLE = True
except ImportError:
    EMOJI_AVAILABLE = False


# Basic emoji mapping as fallback when emoji library is not available
_BASIC_EMOJI_MAP = {
    # Faces
    ":smile:": "😄", ":grinning:": "😀", ":grin:": "😁", ":joy:": "😂",
    ":wink:": "😉", ":blush:": "😊", ":heart_eyes:": "😍", ":kissing_heart:": "😘",
    ":stuck_out_tongue:": "😛", ":stuck_out_tongue_winking_eye:": "😜",
    ":stuck_out_tongue_closed_eyes:": "😝", ":neutral_face:": "😐", ":expressionless:": "😑",
    ":unamused:": "😒", ":sweat_smile:": "😅", ":cry:": "😢", ":sob:": "😭",
    ":angry:": "😠", ":rage:": "😡", ":thinking:": "🤔", ":confused:": "😕",
    
    # Hand gestures
    ":thumbsup:": "👍", ":thumbsdown:": "👎", ":ok_hand:": "👌", ":v:": "✌️",
    ":clap:": "👏", ":raised_hands:": "🙌", ":wave:": "👋", ":fist:": "✊",
    ":hand:": "✋", ":muscle:": "💪",
    
    # Hearts
    ":heart:": "❤️", ":red_heart:": "❤️", ":orange_heart:": "🧡", ":yellow_heart:": "💛",
    ":green_heart:": "💚", ":blue_heart:": "💙", ":purple_heart:": "💜", ":black_heart:": "🖤",
    ":broken_heart:": "💔", ":heartpulse:": "💗", ":sparkling_heart:": "💖",
    
    # Animals
    ":cat:": "🐱", ":dog:": "🐕", ":mouse:": "🐭", ":rabbit:": "🐰",
    ":bear:": "🐻", ":panda:": "🐼", ":fox:": "🦊", ":fish:": "🐟",
    ":salmon:": "🍣", ":dolphin:": "🐬", ":whale:": "🐋", ":bird:": "🐦",
    
    # Objects
    ":fire:": "🔥", ":star:": "⭐", ":sparkles:": "✨", ":rocket:": "🚀",
    ":check:": "✅", ":white_check_mark:": "✅", ":x:": "❌", ":warning:": "⚠️",
    ":bulb:": "💡", ":book:": "📖", ":pencil:": "✏️", ":memo:": "📝",
    ":computer:": "💻", ":phone:": "📱", ":email:": "📧", ":link:": "🔗",
    
    # Weather
    ":sunny:": "☀️", ":cloud:": "☁️", ":rain:": "🌧️", ":snow:": "❄️",
    ":thunder:": "⛈️", ":rainbow:": "🌈",
    
    # Food & Drink
    ":coffee:": "☕", ":tea:": "🍵", ":beer:": "🍺", ":wine:": "🍷",
    ":pizza:": "🍕", ":burger:": "🍔", ":cake:": "🍰", ":ice_cream:": "🍦",
    
    # Symbols
    ":100:": "💯", ":ok:": "🆗", ":new:": "🆕", ":free:": "🆓",
    ":information_source:": "ℹ️", ":question:": "❓", ":exclamation:": "❗",
    
    # Flags
    ":cn:": "🇨🇳", ":us:": "🇺🇸", ":jp:": "🇯🇵", ":gb:": "🇬🇧",
    ":kr:": "🇰🇷", ":de:": "🇩🇪", ":fr:": "🇫🇷",
}


class EmojiHandler:
    """Handles emoji shortcode conversion.

    Converts emoji shortcodes like :smile: to actual emoji characters.
    Uses the emoji library when available, falls back to a basic mapping.
    """

    # Pattern to match :shortcode: format
    # Does NOT match shortcodes inside code blocks (handled separately)
    SHORTCODE_PATTERN = re.compile(r":[a-zA-Z0-9_+-]+:")

    def __init__(self, use_alias: bool = True):
        """Initialize the emoji handler.

        Args:
            use_alias: Use alias format (:smile:) when True, else Unicode format
        """
        self.use_alias = use_alias
        self._code_block_ranges: list[tuple[int, int]] = []

    def _find_code_blocks(self, text: str) -> None:
        """Find all code block positions to exclude from emoji processing.

        Args:
            text: The markdown text to analyze
        """
        self._code_block_ranges = []
        
        # Match fenced code blocks (```)
        fence_pattern = re.compile(r"```[\s\S]*?```", re.MULTILINE)
        for match in fence_pattern.finditer(text):
            self._code_block_ranges.append((match.start(), match.end()))
        
        # Match inline code (`code`)
        inline_code_pattern = re.compile(r"`[^`]+`")
        for match in inline_code_pattern.finditer(text):
            self._code_block_ranges.append((match.start(), match.end()))

    def _is_in_code_block(self, pos: int) -> bool:
        """Check if a position is inside a code block.

        Args:
            pos: Position in the text

        Returns:
            True if position is inside a code block
        """
        for start, end in self._code_block_ranges:
            if start <= pos < end:
                return True
        return False

    def process_emoji(self, text: str) -> str:
        """Convert emoji shortcodes to emoji characters.

        Does NOT convert shortcodes inside code blocks.

        Args:
            text: Markdown text with potential emoji shortcodes

        Returns:
            Text with shortcodes converted to emoji
        """
        if not text:
            return text

        # Find code blocks to exclude
        self._find_code_blocks(text)

        if EMOJI_AVAILABLE:
            return self._process_with_library(text)
        else:
            return self._process_with_mapping(text)

    def _process_with_library(self, text: str) -> str:
        """Process using the emoji library."""
        # Use the emoji library's emojize function with alias support
        # language='alias' means :smile: → 😄 (as opposed to Unicode aliases)
        result = []
        last_end = 0

        for match in self.SHORTCODE_PATTERN.finditer(text):
            start, end = match.start(), match.end()
            
            # Add text before this match
            result.append(text[last_end:start])
            
            # Check if in code block
            if self._is_in_code_block(start):
                result.append(match.group())
            else:
                # Try to convert
                shortcode = match.group()
                converted = emoji.emojize(shortcode, language='alias')
                result.append(converted)
            
            last_end = end

        result.append(text[last_end:])
        return ''.join(result)

    def _process_with_mapping(self, text: str) -> str:
        """Process using the fallback mapping."""
        result = []
        last_end = 0

        for match in self.SHORTCODE_PATTERN.finditer(text):
            start, end = match.start(), match.end()
            
            # Add text before this match
            result.append(text[last_end:start])
            
            # Check if in code block
            if self._is_in_code_block(start):
                result.append(match.group())
            else:
                # Use fallback mapping
                shortcode = match.group().lower()
                result.append(_BASIC_EMOJI_MAP.get(shortcode, match.group()))
            
            last_end = end

        result.append(text[last_end:])
        return ''.join(result)

    def demojize(self, text: str) -> str:
        """Convert emoji characters to shortcodes (reverse operation).

        Args:
            text: Text with emoji characters

        Returns:
            Text with emojis converted to shortcodes
        """
        if not EMOJI_AVAILABLE:
            # Can't demojize without the library
            return text
        
        return emoji.demojize(text, language='alias')

    def has_emoji_shortcode(self, text: str) -> bool:
        """Check if text contains any emoji shortcodes.

        Args:
            text: Text to check

        Returns:
            True if any :shortcode: pattern is found outside code blocks
        """
        if not text:
            return False

        self._find_code_blocks(text)
        
        for match in self.SHORTCODE_PATTERN.finditer(text):
            if not self._is_in_code_block(match.start()):
                return True
        
        return False


# Module-level singleton instance
_handler_instance: EmojiHandler | None = None


def get_emoji_handler() -> EmojiHandler:
    """Get the singleton EmojiHandler instance."""
    global _handler_instance
    if _handler_instance is None:
        _handler_instance = EmojiHandler()
    return _handler_instance