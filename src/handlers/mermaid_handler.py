"""Mermaid diagram detection and processing.

Detects mermaid code blocks in markdown text and prepares them for
front-end rendering via Mermaid.js.
"""

from __future__ import annotations

import re
from typing import NamedTuple


class MermaidBlock(NamedTuple):
    """Represents a detected mermaid code block."""

    language: str  # 'mermaid'
    content: str  # The diagram code
    start: int  # Start position in text
    end: int  # End position in text


class MermaidHandler:
    """Handles Mermaid diagram code blocks.

    This handler detects mermaid code blocks in markdown and prepares
    them for front-end rendering. The actual rendering happens in the
    browser via Mermaid.js CDN.
    """

    # Pattern to match ```mermaid ... ``` code blocks
    MERMAID_PATTERN = re.compile(
        r"```mermaid\s*\n(.*?)```",
        re.DOTALL | re.IGNORECASE
    )

    # Supported mermaid diagram types for validation
    SUPPORTED_DIAGRAMS = {
        "flowchart", "graph", "sequencediagram", "classdiagram",
        "statediagram", "erdiagram", "journey", "gantt", "pie",
        "mindmap", "timeline", "quadrantchart", "requirementdiagram",
        "gitgraph", "c4diagram", "blockchart"
    }

    def detect_mermaid_blocks(self, text: str) -> list[MermaidBlock]:
        """Detect all mermaid code blocks in the text.

        Args:
            text: Raw markdown text

        Returns:
            List of MermaidBlock objects with positions and content
        """
        blocks = []
        for match in self.MERMAID_PATTERN.finditer(text):
            content = match.group(1).strip()
            if content:
                blocks.append(MermaidBlock(
                    language="mermaid",
                    content=content,
                    start=match.start(),
                    end=match.end()
                ))
        return blocks

    def has_mermaid(self, text: str) -> bool:
        """Check if text contains mermaid code blocks.

        Args:
            text: Raw markdown text

        Returns:
            True if at least one mermaid block is found
        """
        return bool(self.MERMAID_PATTERN.search(text))

    def validate_mermaid_syntax(self, content: str) -> tuple[bool, str | None]:
        """Basic validation of mermaid diagram syntax.

        Checks if the content starts with a known diagram type keyword.

        Args:
            content: Mermaid diagram code

        Returns:
            Tuple of (is_valid, error_message)
        """
        lines = content.strip().split("\n")
        if not lines:
            return False, "Empty mermaid block"

        first_line = lines[0].strip().lower()

        # Check for known diagram types
        for diagram_type in self.SUPPORTED_DIAGRAMS:
            if first_line.startswith(diagram_type):
                return True, None

        # Some diagrams have specific first lines
        if first_line.startswith("%%{"):  # Mermaid directives
            return True, None

        return True, None  # Allow unknown types, let mermaid.js handle errors

    def get_diagram_type(self, content: str) -> str | None:
        """Extract the diagram type from mermaid content.

        Args:
            content: Mermaid diagram code

        Returns:
            Diagram type string or None if not detectable
        """
        lines = content.strip().split("\n")
        if not lines:
            return None

        first_line = lines[0].strip().lower()

        for diagram_type in self.SUPPORTED_DIAGRAMS:
            if first_line.startswith(diagram_type):
                return diagram_type

        return None


# Module-level singleton instance
_handler_instance: MermaidHandler | None = None


def get_mermaid_handler() -> MermaidHandler:
    """Get the singleton MermaidHandler instance."""
    global _handler_instance
    if _handler_instance is None:
        _handler_instance = MermaidHandler()
    return _handler_instance