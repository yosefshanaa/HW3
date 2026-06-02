"""Unit tests for the BookBuilderSDK (services mocked at their modules)."""

from __future__ import annotations

from pathlib import Path

from startup_book.sdk.sdk import BookBuilderSDK
from startup_book.shared.models import BookContent, BuildResult, TokenUsage


def _sdk(config_dir: Path) -> BookBuilderSDK:
    return BookBuilderSDK(config_dir=config_dir)


def test_estimate_cost(config_dir: Path) -> None:
    sdk = _sdk(config_dir)
    usage = TokenUsage(prompt_tokens=1_000_000, completion_tokens=1_000_000)
    assert sdk._estimate_cost(usage) == 0.75  # 1*0.15 + 1*0.60


def test_generate_content_delegates(config_dir: Path, monkeypatch) -> None:
    class FakeCrew:
        def __init__(self, *a: object, **k: object) -> None: ...
        def generate_content(self, topic: str | None) -> BookContent:
            return BookContent(title="delegated")

    monkeypatch.setattr("startup_book.services.crew_service.CrewService", FakeCrew)
    assert _sdk(config_dir).generate_content("x").title == "delegated"


def test_make_figures_delegates(config_dir: Path, monkeypatch) -> None:
    class FakeFig:
        def __init__(self, *a: object, **k: object) -> None: ...
        def generate_all(self) -> list[Path]:
            return [Path("a.pdf"), Path("b.pdf")]

    monkeypatch.setattr("startup_book.services.figure_service.FigureService", FakeFig)
    assert _sdk(config_dir).make_figures() == [Path("a.pdf"), Path("b.pdf")]


def test_render_latex_delegates(config_dir: Path, monkeypatch) -> None:
    seen: dict[str, object] = {}

    class FakeLatex:
        def __init__(self, *a: object, **k: object) -> None: ...
        def render(self, content: BookContent) -> None:
            seen["content"] = content

    monkeypatch.setattr("startup_book.services.latex_service.LatexService", FakeLatex)
    content = BookContent(title="t")
    _sdk(config_dir).render_latex(content)
    assert seen["content"] is content


def test_build_orchestrates_and_carries_usage(config_dir: Path, monkeypatch) -> None:
    content = BookContent(
        title="t", token_usage=TokenUsage(prompt_tokens=1_000_000, completion_tokens=0)
    )

    class FakeCrew:
        def __init__(self, *a: object, **k: object) -> None: ...
        def generate_content(self, topic: str | None) -> BookContent:
            return content

    class FakeFig:
        def __init__(self, *a: object, **k: object) -> None: ...
        def generate_all(self) -> list[Path]:
            return []

    class FakeLatex:
        def __init__(self, *a: object, **k: object) -> None: ...
        def render(self, c: BookContent) -> None: ...

    class FakeCompile:
        def __init__(self, *a: object, **k: object) -> None: ...
        def compile(self) -> BuildResult:
            return BuildResult(pdf_path="/x/book.pdf", pages=14)

    monkeypatch.setattr("startup_book.services.crew_service.CrewService", FakeCrew)
    monkeypatch.setattr("startup_book.services.figure_service.FigureService", FakeFig)
    monkeypatch.setattr("startup_book.services.latex_service.LatexService", FakeLatex)
    monkeypatch.setattr("startup_book.services.compile_service.CompileService", FakeCompile)

    result = _sdk(config_dir).build("topic")
    assert result.pages == 14
    assert result.token_usage.total_tokens == 1_000_000
    assert result.estimated_cost_usd == 0.15
