"""Unit tests for the matplotlib figure service."""

from __future__ import annotations

from pathlib import Path

from startup_book.services.figure_service import FigureService


def test_generate_all_writes_three_assets(tmp_path: Path) -> None:
    paths = FigureService(out_dir=tmp_path).generate_all()
    names = {p.name for p in paths}
    assert names == {"jcurve.pdf", "unit_economics.pdf", "illustration.png"}
    for path in paths:
        assert path.exists() and path.stat().st_size > 0


def test_jcurve_is_a_pdf(tmp_path: Path) -> None:
    path = FigureService(out_dir=tmp_path).jcurve()
    assert path.suffix == ".pdf"
    assert path.read_bytes().startswith(b"%PDF")


def test_illustration_is_a_png(tmp_path: Path) -> None:
    path = FigureService(out_dir=tmp_path).illustration()
    assert path.suffix == ".png"
    assert path.read_bytes().startswith(b"\x89PNG")


def test_out_dir_is_created(tmp_path: Path) -> None:
    target = tmp_path / "nested" / "figs"
    FigureService(out_dir=target).unit_economics()
    assert (target / "unit_economics.pdf").exists()
