"""Compile service: run the multi-pass LaTeX build and report the result.

Why: a correct bibliography + cross-references need several passes
(lualatex -> biber -> lualatex -> lualatex, assignment §13.2). This service runs
them as subprocesses, fails loudly with the tail of the log on error
(guidelines §6.3), and returns a :class:`BuildResult` with the PDF page count.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from startup_book.constants import BOOK_PDF_NAME, LATEX_DIR, MAIN_TEX_NAME
from startup_book.shared.config import ConfigManager
from startup_book.shared.errors import LatexCompileError
from startup_book.shared.models import BuildResult


class CompileService:
    """Compiles ``main.tex`` into ``book.pdf`` via the multi-pass sequence."""

    def __init__(self, config: ConfigManager, latex_dir: Path | None = None) -> None:
        """Store config and the LaTeX project directory."""
        self._config = config
        self._dir = latex_dir or LATEX_DIR

    def compile(self) -> BuildResult:
        """Run the full build and return the resulting :class:`BuildResult`.

        Raises:
            LatexCompileError: If the engine is missing or any pass fails.
        """
        settings = self._config.build_settings()
        engine = settings.get("engine", "lualatex")
        if shutil.which(engine) is None:
            raise LatexCompileError(
                f"'{engine}' not found on PATH — install MiKTeX or TeX Live first"
            )
        job = MAIN_TEX_NAME.removesuffix(".tex")
        self._run([engine, "-interaction=nonstopmode", "-halt-on-error", MAIN_TEX_NAME])
        if settings.get("use_biber", True) and shutil.which("biber"):
            self._run(["biber", job])
        self._run([engine, "-interaction=nonstopmode", "-halt-on-error", MAIN_TEX_NAME])
        self._run([engine, "-interaction=nonstopmode", "-halt-on-error", MAIN_TEX_NAME])

        pdf = self._dir / f"{job}.pdf"
        book = self._dir / BOOK_PDF_NAME
        shutil.copyfile(pdf, book)
        return BuildResult(pdf_path=str(book), pages=self._page_count(book))

    def _run(self, cmd: list[str]) -> None:
        """Run one build command in the LaTeX directory; raise on failure."""
        proc = subprocess.run(cmd, cwd=self._dir, capture_output=True, text=True, check=False)
        if proc.returncode != 0:
            tail = (proc.stdout + proc.stderr)[-1500:]
            raise LatexCompileError(f"{cmd[0]} failed (exit {proc.returncode})", tail)

    @staticmethod
    def _page_count(pdf: Path) -> int:
        """Return the PDF page count (0 if it cannot be read)."""
        try:
            from pypdf import PdfReader

            return len(PdfReader(str(pdf)).pages)
        except Exception:
            return 0
