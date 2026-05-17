"""AstrBot Markdown Renderer Plugin.

Intercepts LLM text replies and renders them as high-quality images
using VS Code's markdown-it ecosystem (markdown-it + KaTeX + highlight.js)
powered by Playwright headless Chromium.

Features:
- Mermaid diagram rendering (via CDN-loaded Mermaid.js)
- Emoji shortcode conversion (:smile: → 😄)
- Math formulas (KaTeX)
- Syntax highlighting (highlight.js)
"""

from __future__ import annotations

import os
import time
import uuid

from astrbot.api import logger, star
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.message_components import Image, Plain

from .markdown_detect import should_render
from .renderer import CHROMIUM_ARGS, MarkdownRenderer
from .src.handlers import get_emoji_handler, get_mermaid_handler

# Default configuration values (mirrored in _conf_schema.json)
_DEFAULTS = {
    "enabled": True,
    "char_threshold": 100,
    "score_threshold": 2,
    "force_render_char_threshold": 500,
    "width": 800,
    "theme": "light",
    "font_size": 16,
    "render_timeout": 10,
    "footer": "Powered by AstrBot",
    "llm_only": True,
    # Engine: markdown-it
    "md_html": False,
    "md_linkify": True,
    "md_typographer": True,
    "md_quotes": "\"\"''",
    # Engine: KaTeX
    "katex_throw_on_error": False,
    "katex_output": "htmlAndMathml",
    "katex_trust": False,
    "katex_escaped_delimiters": True,
    # Engine: highlight.js
    "hljs_ignore_illegals": True,
    # Extension: Mermaid
    "mermaid_enabled": True,
    "mermaid_timeout": 5,
    # Extension: Emoji
    "emoji_enabled": True,
}


def _get_temp_dir() -> str:
    """Get AstrBot temp directory, creating it if needed."""
    from astrbot.core.utils.astrbot_path import get_astrbot_temp_path

    d = get_astrbot_temp_path()
    os.makedirs(d, exist_ok=True)
    return d


def _save_temp_png(png_bytes: bytes) -> str:
    """Save PNG bytes to a temp file and return the path.

    Note: Temp files are NOT cleaned up here. AstrBot's built-in
    ``TempDirCleaner`` automatically purges the temp directory on a
    periodic schedule (every 10 min, oldest-first when size limit is
    exceeded), so explicit per-file deletion is unnecessary.
    """
    temp_dir = _get_temp_dir()
    timestamp = f"{int(time.time())}_{uuid.uuid4().hex[:8]}"
    path = os.path.join(temp_dir, f"md_render_{timestamp}.png")
    with open(path, "wb") as f:
        f.write(png_bytes)
    return path


def _cfg_val(config, key: str):
    """Read a config value with fallback to defaults.

    Note: AstrBot deserialises ``_conf_schema.json`` via ``json.loads``,
    so boolean fields are returned as native Python ``bool`` (not strings).
    A bare ``bool(val)`` is therefore safe and will never hit the
    ``bool("false") == True`` trap.
    """
    try:
        val = config.get(key, _DEFAULTS.get(key))
    except Exception:
        val = _DEFAULTS.get(key)
    return val if val is not None else _DEFAULTS.get(key)


class Main(star.Star):
    """Markdown-to-image rendering plugin for AstrBot."""

    def __init__(self, context: star.Context, config=None) -> None:
        super().__init__(context, config)
        self.config = config
        self.renderer = MarkdownRenderer()
        self._playwright_available: bool | None = None
        self._security_warned: set[str] = set()
        # Handlers for extensions
        self._emoji_handler = get_emoji_handler()
        self._mermaid_handler = get_mermaid_handler()

    def _get_plugin_config(self):
        """Return the plugin config injected by StarManager.

        AstrBot passes plugin settings as the optional ``config`` constructor
        argument. ``context.get_config()`` returns the core AstrBot config, not
        the plugin-specific config file, so use the injected config when
        available.
        """
        if self.config is not None:
            return self.config
        return self.context.get_config()

    async def initialize(self) -> None:
        """Check Playwright availability on startup."""
        try:
            import playwright  # noqa: F401

            self._playwright_available = True
            logger.info("Markdown plugin: Playwright is available.")
        except ImportError:
            self._playwright_available = False
            logger.error(
                "Markdown plugin: 'playwright' package not found. "
                "Please install it with: pip install playwright && playwright install chromium"
            )
            return

        # Verify browser is installed (non-blocking)
        try:
            from playwright.async_api import async_playwright

            pw = await async_playwright().start()
            try:
                browser = await pw.chromium.launch(headless=True, args=CHROMIUM_ARGS)
                await browser.close()
                logger.info("Markdown plugin: Chromium browser verified.")
            finally:
                await pw.stop()
        except Exception as e:
            logger.warning(
                f"Markdown plugin: Chromium browser not ready — {e}. "
                "Run 'playwright install chromium' to install it."
            )

    @filter.on_decorating_result(priority=10)
    async def on_decorating_result(self, event: AstrMessageEvent) -> None:
        """Intercept replies and render markdown as images when conditions are met."""
        config = self._get_plugin_config()

        if not _cfg_val(config, "enabled"):
            return

        if not self._playwright_available:
            return

        result = event.get_result()
        if result is None or not result.chain:
            return

        # Skip non-LLM results (e.g. /help commands) when llm_only is enabled
        if _cfg_val(config, "llm_only") and not result.is_llm_result():
            return

        # Collect all leading Plain text components
        plain_parts: list[str] = []
        for comp in result.chain:
            if isinstance(comp, Plain):
                plain_parts.append(comp.text)
            else:
                break

        if not plain_parts:
            return

        plain_text = "".join(plain_parts)

        # Process emoji shortcodes if enabled
        emoji_enabled = bool(_cfg_val(config, "emoji_enabled"))
        if emoji_enabled:
            plain_text = self._emoji_handler.process_emoji(plain_text)

        # Check rendering conditions: markdown detected + length threshold
        char_threshold = int(_cfg_val(config, "char_threshold"))
        score_threshold = int(_cfg_val(config, "score_threshold"))
        force_render_char_threshold = int(
            _cfg_val(config, "force_render_char_threshold")
        )
        katex_escaped_delimiters = bool(_cfg_val(config, "katex_escaped_delimiters"))

        if not should_render(
            plain_text,
            char_threshold=char_threshold,
            score_threshold=score_threshold,
            force_render_char_threshold=force_render_char_threshold,
            enable_escaped_math_delimiters=katex_escaped_delimiters,
        ):
            return

        # Render markdown to image
        try:
            width = int(_cfg_val(config, "width"))
            theme = str(_cfg_val(config, "theme"))
            font_size = int(_cfg_val(config, "font_size"))
            render_timeout = int(_cfg_val(config, "render_timeout"))
            footer = str(_cfg_val(config, "footer"))

            engine = self._build_engine_config(config)

            png_bytes = await self.renderer.render(
                plain_text,
                width=width,
                theme=theme,
                font_size=font_size,
                footer=footer,
                timeout=render_timeout,
                engine=engine,
            )

            img_path = _save_temp_png(png_bytes)

            # Replace the leading Plain components with the rendered image
            remaining = result.chain[len(plain_parts) :]
            result.chain = [Image.fromFileSystem(img_path)] + remaining

            # Prevent built-in t2i from also converting
            result.use_t2i_ = False

            logger.debug(
                f"Markdown plugin: rendered {len(plain_text)} chars → {img_path}"
            )

        except Exception as e:
            logger.error(f"Markdown plugin: render failed — {e}", exc_info=True)
            # On failure, leave the original text untouched;
            # built-in t2i may still convert it if enabled.

    async def terminate(self) -> None:
        """Release browser resources on plugin unload or AstrBot shutdown."""
        await self.renderer.terminate()

    def _build_engine_config(self, config) -> dict:
        """Build engine options dict from plugin configuration."""
        md_html = bool(_cfg_val(config, "md_html"))
        katex_trust = bool(_cfg_val(config, "katex_trust"))

        if md_html and "md_html" not in self._security_warned:
            logger.info(
                "Markdown plugin: md_html is enabled — raw HTML in "
                "markdown will be rendered. Output is sanitized by DOMPurify."
            )
            self._security_warned.add("md_html")
        if katex_trust and "katex_trust" not in self._security_warned:
            logger.info(
                "Markdown plugin: katex_trust is enabled — KaTeX can "
                "use extended commands. Output is sanitized by DOMPurify."
            )
            self._security_warned.add("katex_trust")

        return {
            "markdownIt": {
                "html": md_html,
                "linkify": bool(_cfg_val(config, "md_linkify")),
                "typographer": bool(_cfg_val(config, "md_typographer")),
                "quotes": str(_cfg_val(config, "md_quotes")),
            },
            "katex": {
                "throwOnError": bool(_cfg_val(config, "katex_throw_on_error")),
                "output": str(_cfg_val(config, "katex_output")),
                "trust": katex_trust,
                "enableEscapedDelimiters": bool(
                    _cfg_val(config, "katex_escaped_delimiters")
                ),
            },
            "highlight": {
                "ignoreIllegals": bool(_cfg_val(config, "hljs_ignore_illegals")),
            },
        }

    @filter.command("md_theme")
    async def cmd_theme(self, event: AstrMessageEvent, theme: str = "") -> None:
        """Switch markdown rendering theme (light/dark)."""
        theme = theme.strip().lower()
        if theme not in ("light", "dark"):
            yield event.plain_result("Usage: /md_theme <light|dark>")
            return

        config = self._get_plugin_config()
        config["theme"] = theme
        config.save_config()
        yield event.plain_result(f"Markdown theme set to: {theme}")

_TEST_MARKDOWN = (
        "# Markdown Rendering Test\n\n"
        "## Text Formatting\n\n"
        "**Bold**, *italic*, ~~strikethrough~~, `inline code`, "
        "==highlighted==, H~2~O (subscript), x^2^ (superscript).\n\n"
        'Typographic: (tm) (c) (r) "quotes" -- and --- dashes.\n\n'
        "## Emoji Support\n\n"
        "Emoji shortcodes are automatically converted: "
        ":smile: :heart: :fire: :thumbsup: :cat: :rocket: :check: :x:\n\n"
        "Common emojis: :coffee: :pizza: :cake: :star: :sparkles: :bulb:\n\n"
        "## Code Block\n\n"
        "```python\n"
        "def fibonacci(n: int) -> list[int]:\n"
        '    """Generate Fibonacci sequence."""\n'
        "    a, b = 0, 1\n"
        "    seq = []\n"
        "    for _ in range(n):\n"
        "        seq.append(a)\n"
        "        a, b = b, a + b\n"
        "    return seq\n"
        "```\n\n"
        "## Mermaid Diagram\n\n"
        "```mermaid\n"
        "flowchart TD\n"
        "    A[Start] --> B{Is it working?}\n"
        "    B -->|Yes| C[Great! :smile:]\n"
        "    B -->|No| D[Debug]\n"
        "    D --> B\n"
        "```\n\n"
        "## Sequence Diagram\n\n"
        "```mermaid\n"
        "sequenceDiagram\n"
        "    participant User\n"
        "    participant Plugin\n"
        "    participant Renderer\n"
        "    User->>Plugin: Send message\n"
        "    Plugin->>Renderer: Render markdown\n"
        "    Renderer-->>Plugin: Return image\n"
        "    Plugin-->>User: Display image\n"
        "```\n\n"
        "## Table\n\n"
        "| Feature | Syntax | Renders As |\n"
        "|---------|--------|------------|\n"
        "| Bold | `**text**` | **text** |\n"
        "| Italic | `*text*` | *text* |\n"
        "| Code | `` `code` `` | `code` |\n"
        "| Emoji | `:smile:` | :smile: |\n\n"
        "## Lists\n\n"
        "1. First ordered item\n"
        "   - Nested unordered\n"
        "   - Another nested\n"
        "2. Second ordered item\n"
        "3. Third ordered item\n\n"
        "## Blockquote\n\n"
        '> "Mathematics is the queen of the sciences."\n'
        "> — Carl Friedrich Gauss\n\n"
        "## Inline Math\n\n"
        "Einstein's equation $E = mc^2$, Euler's identity "
        "$e^{i\\pi} + 1 = 0$, and a summation "
        "$\\sum_{k=1}^{n} k = \\frac{n(n+1)}{2}$.\n\n"
        "## Display Math\n\n"
        "$$\n"
        "\\int_0^\\infty e^{-x^2} \\, dx = \\frac{\\sqrt{\\pi}}{2}\n"
        "$$\n\n"
        "$$\n"
        "\\mathbf{A} = \\begin{bmatrix} a_{11} & a_{12} \\\\\\\\ "
        "a_{21} & a_{22} \\end{bmatrix}, \\quad "
        "\\det(\\mathbf{A}) = a_{11}a_{22} - a_{12}a_{21}\n"
        "$$\n\n"
        "$$\n"
        "\\begin{aligned}\n"
        "\\nabla \\cdot \\mathbf{E} &= \\frac{\\rho}{\\varepsilon_0} \\\\\\\\\n"
        "\\nabla \\times \\mathbf{B} &= \\mu_0 \\mathbf{J} + "
        "\\mu_0 \\varepsilon_0 \\frac{\\partial \\mathbf{E}}"
        "{\\partial t}\n"
        "\\end{aligned}\n"
        "$$\n\n"
        "## Footnotes\n\n"
        "Markdown rendering is powered by markdown-it[^1] "
        "with KaTeX[^2] for math support.\n\n"
        "[^1]: A fast, spec-compliant CommonMark parser.\n"
        "[^2]: The fastest math typesetting library for the web.\n\n"
        "---\n\n"
        "*Test complete — all extensions rendered successfully.* :rocket:\n"
    )

    @filter.command("md_test")
    async def cmd_test(self, event: AstrMessageEvent) -> None:
        """Render a comprehensive test document covering all supported syntax."""
        if not self._playwright_available:
            yield event.plain_result(
                "Playwright is not available. "
                "Install with: pip install playwright && playwright install chromium"
            )
            return

        config = self._get_plugin_config()
        try:
            width = int(_cfg_val(config, "width"))
            theme = str(_cfg_val(config, "theme"))
            font_size = int(_cfg_val(config, "font_size"))
            render_timeout = int(_cfg_val(config, "render_timeout"))

            engine = self._build_engine_config(config)

            png_bytes = await self.renderer.render(
                self._TEST_MARKDOWN,
                width=width,
                theme=theme,
                font_size=font_size,
                footer="Markdown Rendering Test",
                timeout=render_timeout,
                engine=engine,
            )

            img_path = _save_temp_png(png_bytes)
            yield event.image_result(img_path)

        except Exception as e:
            logger.error(f"Markdown plugin: test render failed — {e}", exc_info=True)
            yield event.plain_result(f"Test render failed: {e}")
