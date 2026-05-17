"""Handlers for markdown rendering extensions.

This package contains handlers for various markdown extensions:
- mermaid_handler: Detects and processes Mermaid diagram code blocks
"""

from .mermaid_handler import MermaidHandler, MermaidBlock, get_mermaid_handler

__all__ = [
    "MermaidHandler",
    "MermaidBlock",
    "get_mermaid_handler",
]