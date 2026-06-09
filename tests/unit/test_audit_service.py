"""Unit tests for the LaTeX build-health audit (grader-convenience command)."""

from __future__ import annotations

from pathlib import Path

import pytest

from startup_book.services.audit_service import AuditService
from startup_book.shared.errors import AuditError
from startup_book.shared.models import AuditReport

_CLEAN_LOG = """
This is LuaHBTeX, Version 1.18 ...
[16] [17]
Output written on main.pdf (17 pages, 204640 bytes).
Transcript written on main.log.
"""

_DIRTY_LOG = r"""
Missing character: There is no ﬁ in font [lmroman10-regular]!
Overfull \hbox (4.8933pt too wide) in paragraph at lines 23--24
Underfull \vbox (badness 3000) has occurred while \output is active
LaTeX Warning: Citation 'ries2011' on page 3 undefined on input line 50.
Output written on main_generated.pdf (21 pages, 220360 bytes).
LaTeX Warning: There were undefined references.
"""


def _write(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def test_audit_clean_log_is_healthy(tmp_path: Path) -> None:
    log = _write(tmp_path / "main.log", _CLEAN_LOG)
    report = AuditService(log).audit()
    assert report.pages == 17
    assert (report.overfull, report.missing_glyphs, report.undefined_citations) == (0, 0, 0)
    assert report.healthy is True
    assert report.log_path == str(log)


def test_audit_dirty_log_counts_each_defect(tmp_path: Path) -> None:
    log = _write(tmp_path / "main_generated.log", _DIRTY_LOG)
    report = AuditService(log).audit()
    assert report.pages == 21
    assert report.overfull == 1
    assert report.underfull == 1
    assert report.missing_glyphs == 1
    assert report.undefined_citations == 1
    assert report.healthy is False


def test_audit_missing_log_raises(tmp_path: Path) -> None:
    with pytest.raises(AuditError):
        AuditService(tmp_path / "nope.log").audit()


def test_audit_report_healthy_property() -> None:
    assert AuditReport(log_path="x", pages=10).healthy is True
    assert AuditReport(log_path="x", overfull=2).healthy is False
    assert AuditReport(log_path="x", missing_glyphs=1).healthy is False
    assert AuditReport(log_path="x", undefined_citations=1).healthy is False


def test_audit_default_log_path_is_main_log() -> None:
    # No explicit path -> defaults to the canonical build log (latex/main.log).
    assert AuditService()._log_path.name == "main.log"


def test_sdk_audit_delegates(config_dir: Path, tmp_path: Path) -> None:
    from startup_book import BookBuilderSDK

    log = _write(tmp_path / "main.log", _CLEAN_LOG)
    report = BookBuilderSDK(config_dir).audit(log)
    assert isinstance(report, AuditReport)
    assert report.pages == 17 and report.healthy
