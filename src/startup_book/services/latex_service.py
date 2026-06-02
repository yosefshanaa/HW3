"""LaTeX service: write the crew's BookContent into generated LaTeX artifacts.

Why: the structural LaTeX (preamble, cover, required elements) is hand-authored
and stable (ADR-6); the crew fills *prose*. This service converts the crew's
:class:`BookContent` into additive artifacts under ``latex/generated/`` — one
``.tex`` fragment per chapter, an index that inputs them, and a ``references.bib``
— without ever touching the curated authored chapters.
"""

from __future__ import annotations

from pathlib import Path

from startup_book.constants import LATEX_DIR
from startup_book.shared.config import ConfigManager
from startup_book.shared.latex_text import escape_latex, markdown_to_latex
from startup_book.shared.models import BookContent, Source


class LatexService:
    """Renders :class:`BookContent` into ``latex/generated/`` artifacts."""

    def __init__(self, config: ConfigManager, latex_dir: Path | None = None) -> None:
        """Create the service and ensure the output directory exists."""
        self._config = config
        self._out = (latex_dir or LATEX_DIR) / "generated"
        self._out.mkdir(parents=True, exist_ok=True)

    def render(self, content: BookContent) -> Path:
        """Write all generated artifacts and return the chapter-index path."""
        inputs: list[str] = []
        for index, chapter in enumerate(content.chapters, start=1):
            name = f"{index:02d}-{chapter.id}"
            self._write_chapter(name, chapter.heading, chapter.body_markdown)
            inputs.append(name)
        self._write_index(inputs)
        self._write_bib(content.sources)
        return self._out / "chapters.tex"

    def _write_chapter(self, name: str, heading: str, body_markdown: str) -> None:
        """Write one chapter fragment (``\\chapter`` + converted body)."""
        body = markdown_to_latex(body_markdown)
        text = f"\\chapter{{{escape_latex(heading)}}}\n\n{body}"
        (self._out / f"{name}.tex").write_text(text, encoding="utf-8")

    def _write_index(self, names: list[str]) -> None:
        """Write ``chapters.tex`` that ``\\input``s every generated chapter."""
        lines = [rf"\input{{generated/{name}}}" for name in names]
        (self._out / "chapters.tex").write_text("\n".join(lines) + "\n", encoding="utf-8")

    def _write_bib(self, sources: list[Source]) -> None:
        """Write a ``references.bib`` from the crew-collected sources."""
        entries = [self._bib_entry(src) for src in sources]
        (self._out / "references.bib").write_text("\n".join(entries), encoding="utf-8")

    @staticmethod
    def _bib_entry(src: Source) -> str:
        """Format a single ``@misc`` BibTeX entry from a :class:`Source`."""
        return (
            f"@misc{{{src.key},\n"
            f"  title  = {{{src.title}}},\n"
            f"  author = {{{src.author}}},\n"
            f"  year   = {{{src.year}}}\n"
            f"}}\n"
        )
