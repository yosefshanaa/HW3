"""Audit service: parse a LaTeX compiler log into a build-health report.

Why: a grader (or CI) needs a one-glance health check — page count plus proof
of zero overfull boxes, missing glyphs and undefined citations — without
scrolling a 2000-line ``.log`` by hand. This service turns the log into a typed
:class:`~startup_book.shared.models.AuditReport`.
"""

from __future__ import annotations

import re
from pathlib import Path

from startup_book.constants import LATEX_DIR, MAIN_TEX_NAME
from startup_book.shared.errors import AuditError
from startup_book.shared.models import AuditReport

_PAGES = re.compile(r"Output written on \S+ \((\d+) pages?")
_OVERFULL = re.compile(r"Overfull \\[hv]box")
_UNDERFULL = re.compile(r"Underfull \\[hv]box")
_MISSING_GLYPH = re.compile(r"Missing character")
_UNDEFINED_CITATION = re.compile(r"Citation\b.*?undefined")


class AuditService:
    """Parses a LaTeX ``.log`` into an :class:`AuditReport`."""

    def __init__(self, log_path: Path | None = None) -> None:
        """Store the log path (defaults to the canonical build log ``latex/main.log``)."""
        default = LATEX_DIR / f"{MAIN_TEX_NAME.removesuffix('.tex')}.log"
        self._log_path = Path(log_path) if log_path else default

    def audit(self) -> AuditReport:
        """Read the log and return a build-health report.

        Raises:
            AuditError: If the log file does not exist.
        """
        try:
            text = self._log_path.read_text(encoding="utf-8", errors="ignore")
        except FileNotFoundError as exc:
            raise AuditError(f"no LaTeX log to audit: {self._log_path}") from exc
        pages = _PAGES.search(text)
        return AuditReport(
            log_path=str(self._log_path),
            pages=int(pages.group(1)) if pages else 0,
            overfull=len(_OVERFULL.findall(text)),
            underfull=len(_UNDERFULL.findall(text)),
            missing_glyphs=len(_MISSING_GLYPH.findall(text)),
            undefined_citations=len(_UNDEFINED_CITATION.findall(text)),
        )
