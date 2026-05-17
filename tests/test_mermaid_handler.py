"""Tests for Mermaid handler."""

import pytest
from src.handlers.mermaid_handler import MermaidHandler, get_mermaid_handler


class TestMermaidHandler:
    """Test MermaidHandler functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.handler = MermaidHandler()

    def test_detect_simple_flowchart(self):
        """Test detecting a simple flowchart."""
        text = """
```mermaid
flowchart TD
    A --> B
```
"""
        blocks = self.handler.detect_mermaid_blocks(text)
        assert len(blocks) == 1
        assert blocks[0].language == "mermaid"
        assert "flowchart TD" in blocks[0].content

    def test_detect_sequence_diagram(self):
        """Test detecting a sequence diagram."""
        text = """
```mermaid
sequenceDiagram
    Alice->>Bob: Hello
```
"""
        blocks = self.handler.detect_mermaid_blocks(text)
        assert len(blocks) == 1
        assert "sequenceDiagram" in blocks[0].content

    def test_detect_multiple_blocks(self):
        """Test detecting multiple mermaid blocks."""
        text = """
```mermaid
flowchart TD
    A --> B
```

Some text here.

```mermaid
graph LR
    X --> Y
```
"""
        blocks = self.handler.detect_mermaid_blocks(text)
        assert len(blocks) == 2

    def test_no_mermaid_blocks(self):
        """Test text without mermaid blocks."""
        text = "This is just plain text with ```python\nprint('hello')\n``` code."
        blocks = self.handler.detect_mermaid_blocks(text)
        assert len(blocks) == 0

    def test_has_mermaid_true(self):
        """Test has_mermaid returns True when mermaid exists."""
        text = "```mermaid\nflowchart TD\n    A --> B\n```"
        assert self.handler.has_mermaid(text) is True

    def test_has_mermaid_false(self):
        """Test has_mermaid returns False when no mermaid."""
        text = "Just plain text without mermaid."
        assert self.handler.has_mermaid(text) is False

    def test_validate_flowchart(self):
        """Test validation of flowchart syntax."""
        content = "flowchart TD\n    A --> B"
        is_valid, error = self.handler.validate_mermaid_syntax(content)
        assert is_valid is True
        assert error is None

    def test_validate_sequence_diagram(self):
        """Test validation of sequence diagram."""
        content = "sequenceDiagram\n    Alice->>Bob: Hello"
        is_valid, error = self.handler.validate_mermaid_syntax(content)
        assert is_valid is True

    def test_get_diagram_type_flowchart(self):
        """Test extracting flowchart type."""
        content = "flowchart TD\n    A --> B"
        assert self.handler.get_diagram_type(content) == "flowchart"

    def test_get_diagram_type_sequence(self):
        """Test extracting sequence diagram type."""
        content = "sequenceDiagram\n    Alice->>Bob"
        assert self.handler.get_diagram_type(content) == "sequencediagram"

    def test_singleton_get_mermaid_handler(self):
        """Test singleton pattern."""
        handler1 = get_mermaid_handler()
        handler2 = get_mermaid_handler()
        assert handler1 is handler2