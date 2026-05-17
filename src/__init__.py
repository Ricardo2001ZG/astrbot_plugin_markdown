"""Source package for astrbot_plugin_markdown.

This package contains:
- handlers: Mermaid and Emoji processing modules
- entry.js: Browser-side JavaScript entry point (built via npm)
"""

from .handlers import get_emoji_handler, get_mermaid_handler

__all__ = ["get_emoji_handler", "get_mermaid_handler"]