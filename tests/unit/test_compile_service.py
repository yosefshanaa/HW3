"""Unit tests for the LaTeX compile service (subprocess mocked)."""

from __future__ import annotations

from pathlib import Path

import pytest

from startup_book.services.compile_service import CompileService
from startup_book.services.figure_service import FigureService
from startup_book.shared.config import ConfigManager
from startup_book.shared.errors import LatexCompileError


class _Proc:
    """Minimal stand-in for a completed subprocess."""

    def __init__(self, returncode: int) -> None:
        self.returncode = returncode
        self.stdout = "out"
        self.stderr = "err"


def test_missing_engine_raises(config_dir: Path, tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("shutil.which", lambda name: None)
    svc = CompileService(ConfigManager(config_dir), latex_dir=tmp_path)
    with pytest.raises(LatexCompileError):
        svc.compile()


def test_run_nonzero_raises_with_log_tail(config_dir: Path, tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("subprocess.run", lambda *a, **k: _Proc(1))
    svc = CompileService(ConfigManager(config_dir), latex_dir=tmp_path)
    with pytest.raises(LatexCompileError) as info:
        svc._run(["lualatex", "main.tex"])
    assert info.value.log_tail


def test_compile_success_runs_four_passes(config_dir: Path, tmp_path: Path, monkeypatch) -> None:
    runs: list[list[str]] = []
    monkeypatch.setattr("shutil.which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr("subprocess.run", lambda cmd, **k: runs.append(cmd) or _Proc(0))
    monkeypatch.setattr(CompileService, "_page_count", staticmethod(lambda pdf: 15))
    (tmp_path / "main.pdf").write_bytes(b"%PDF-1.4 fake")

    result = CompileService(ConfigManager(config_dir), latex_dir=tmp_path).compile()

    assert result.pages == 15
    assert result.pdf_path.endswith("book.pdf")
    assert (tmp_path / "book.pdf").exists()
    assert len(runs) == 4  # lualatex, biber, lualatex, lualatex


def test_page_count_reads_real_pdf(tmp_path: Path) -> None:
    pdf = FigureService(out_dir=tmp_path).jcurve()
    assert CompileService._page_count(pdf) == 1


def test_page_count_bad_pdf_returns_zero(tmp_path: Path) -> None:
    bad = tmp_path / "x.pdf"
    bad.write_bytes(b"not a pdf")
    assert CompileService._page_count(bad) == 0
