"""Integration test: the SDK build pipeline with real figure + LaTeX rendering.

Only the external boundaries are stubbed — the crew (LLM/network) and the LaTeX
compile (subprocess) — so this exercises ConfigManager, FigureService,
LatexService and the SDK orchestration working together for real.
"""

from __future__ import annotations

from pathlib import Path

from startup_book.sdk.sdk import BookBuilderSDK
from startup_book.shared.models import BookContent, BuildResult


def test_build_produces_real_figures_and_latex(
    config_dir: Path, tmp_path: Path, sample_content: BookContent, monkeypatch
) -> None:
    fig_dir = tmp_path / "figs"
    tex_dir = tmp_path / "latex"
    monkeypatch.setattr("startup_book.services.figure_service.FIGURES_DIR", fig_dir)
    monkeypatch.setattr("startup_book.services.latex_service.LATEX_DIR", tex_dir)

    class FakeCrew:
        def __init__(self, *a: object, **k: object) -> None: ...
        def generate_content(self, topic: str | None) -> BookContent:
            return sample_content

    class FakeCompile:
        def __init__(self, *a: object, **k: object) -> None: ...
        def compile(self) -> BuildResult:
            tex_dir.mkdir(parents=True, exist_ok=True)
            (tex_dir / "book.pdf").write_bytes(b"%PDF-1.4")
            return BuildResult(pdf_path=str(tex_dir / "book.pdf"), pages=15)

    monkeypatch.setattr("startup_book.services.crew_service.CrewService", FakeCrew)
    monkeypatch.setattr("startup_book.services.compile_service.CompileService", FakeCompile)

    result = BookBuilderSDK(config_dir=config_dir).build("Topic")

    assert result.pages == 15
    # real figures rendered
    assert (fig_dir / "jcurve.pdf").exists()
    assert (fig_dir / "unit_economics.pdf").exists()
    assert (fig_dir / "illustration.png").exists()
    # real LaTeX fragments rendered from the sample content
    assert (tex_dir / "generated" / "01-intro.tex").exists()
    assert (tex_dir / "generated" / "chapters.tex").exists()
    assert (tex_dir / "generated" / "references.bib").exists()
