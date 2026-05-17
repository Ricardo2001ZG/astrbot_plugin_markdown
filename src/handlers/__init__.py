"""Handlers for markdown rendering extensions.

This package contains handlers for various markdown extensions:
- mermaid_handler: Detects and processes Mermaid diagram code blocks
- emoji_handler: Converts emoji shortcodes to emoji characters
"""

from .mermaid_handler import MermaidHandler, MermaidBlock, get_mermaid_handler
from .emoji_handler import EmojiHandler, get_emoji_handler

__all__ = [
    "MermaidHandler",
    "MermaidBlock",
    "get_mermaid_handler",
    "EmojiHandler",
    "get_emoji_handler",
]