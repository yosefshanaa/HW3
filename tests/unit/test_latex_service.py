"""Unit tests for the LaTeX rendering service."""

from __future__ import annotations

from pathlib import Path

from startup_book.services.latex_service import LatexService
from startup_book.shared.config import ConfigManager
from startup_book.shared.models import BookContent


def test_render_writes_chapters_index_and_bib(
    config_dir: Path, tmp_path: Path, sample_content: BookContent
) -> None:
    service = LatexService(ConfigManager(config_dir), latex_dir=tmp_path)
    index = service.render(sample_content)

    gen = tmp_path / "generated"
    assert index == gen / "chapters.tex"
    # Chapters are named by position (not crew id) so they match main_generated.tex.
    assert (gen / "01-1.tex").exists()
    assert (gen / "02-2.tex").exists()
    assert (gen / "references.bib").exists()


def test_chapter_fragment_has_chapter_and_converted_body(
    config_dir: Path, tmp_path: Path, sample_content: BookContent
) -> None:
    service = LatexService(ConfigManager(config_dir), latex_dir=tmp_path)
    service.render(sample_content)
    text = (tmp_path / "generated" / "01-1.tex").read_text(encoding="utf-8")
    assert r"\chapter{מבוא}" in text
    assert r"\section{כותרת}" in text  # '## כותרת' converted
    assert r"\textbf{מודגש}" in text  # '**מודגש**' converted


def test_index_inputs_every_chapter(
    config_dir: Path, tmp_path: Path, sample_content: BookContent
) -> None:
    service = LatexService(ConfigManager(config_dir), latex_dir=tmp_path)
    service.render(sample_content)
    index = (tmp_path / "generated" / "chapters.tex").read_text(encoding="utf-8")
    assert r"\input{generated/01-1}" in index
    assert r"\input{generated/02-2}" in index


def test_bib_contains_source_key(
    config_dir: Path, tmp_path: Path, sample_content: BookContent
) -> None:
    service = LatexService(ConfigManager(config_dir), latex_dir=tmp_path)
    service.render(sample_content)
    bib = (tmp_path / "generated" / "references.bib").read_text(encoding="utf-8")
    assert "@misc{ries2011," in bib
    assert "The Lean Startup" in bib


def test_bib_escapes_ampersand_in_author(
    config_dir: Path, tmp_path: Path
) -> None:
    # A raw "&" in a crew-collected author is a fatal biber error; it must be
    # escaped. The key is also reduced to biber-safe characters.
    from startup_book.shared.models import BookContent, Chapter, Source

    content = BookContent(
        title="t",
        chapters=[Chapter(id="x", heading="h", body_markdown="body")],
        sources=[Source(key="mck&2020", title="Report 50% up", author="McKinsey & Co", year="2020")],
    )
    service = LatexService(ConfigManager(config_dir), latex_dir=tmp_path)
    service.render(content)
    bib = (tmp_path / "generated" / "references.bib").read_text(encoding="utf-8")
    assert r"McKinsey \& Co" in bib
    assert r"Report 50\% up" in bib
    assert "@misc{mck2020," in bib  # "&" stripped from the key
    assert "McKinsey & Co" not in bib  # no raw ampersand survives
