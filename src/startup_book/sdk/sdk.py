"""BookBuilderSDK — the single entry point for all business logic (§4).

Why: every consumer (CLI, tests, a future GUI/REST) goes through this class, not
through the services directly. It composes the configuration and the API
gatekeeper once, then orchestrates the four services (crew, figure, latex,
compile). Services are imported lazily so that constructing the SDK — or merely
importing the package — does not pull in CrewAI unless content is generated.
"""

from __future__ import annotations

from pathlib import Path

from startup_book.shared.config import ConfigManager
from startup_book.shared.gatekeeper import ApiGatekeeper
from startup_book.shared.models import AuditReport, BookContent, BuildResult, TokenUsage


class BookBuilderSDK:
    """Orchestrates research → write → review → typeset → compile."""

    def __init__(self, config_dir: Path | None = None) -> None:
        """Compose configuration and the API gatekeeper.

        Args:
            config_dir: Optional override for the ``config/`` directory (tests).
        """
        self.config = ConfigManager(config_dir)
        self.gatekeeper = ApiGatekeeper(self.config.rate_limit())

    def generate_content(self, topic: str | None = None) -> BookContent:
        """Run the CrewAI pipeline and return the assembled book content.

        Args:
            topic: Optional topic override; defaults to the book title in config.
        """
        from startup_book.services.crew_service import CrewService

        service = CrewService(self.config, self.gatekeeper)
        return service.generate_content(topic)

    def make_figures(self) -> list[Path]:
        """Generate the Python figures and return their output paths."""
        from startup_book.services.figure_service import FigureService

        return FigureService().generate_all()

    def render_latex(self, content: BookContent) -> None:
        """Render ``content`` into LaTeX chapter fragments and the .bib file."""
        from startup_book.services.latex_service import LatexService

        LatexService(self.config).render(content)

    def compile_pdf(self) -> BuildResult:
        """Compile the LaTeX project to a PDF and return the build result."""
        from startup_book.services.compile_service import CompileService

        return CompileService(self.config).compile()

    def audit(self, log_path: Path | None = None) -> AuditReport:
        """Parse a LaTeX build log into a health report (pages + zero-defect checks)."""
        from startup_book.services.audit_service import AuditService

        return AuditService(log_path).audit()

    def build(self, topic: str | None = None) -> BuildResult:
        """Run the full pipeline end to end and return the build result.

        Steps: generate content → make figures → render LaTeX → compile PDF.
        The token usage from generation is carried into the final result, and an
        estimated USD cost is computed from the configured price rates.
        """
        content = self.generate_content(topic)
        self.make_figures()
        self.render_latex(content)
        result = self.compile_pdf()
        result.token_usage = content.token_usage
        result.estimated_cost_usd = self._estimate_cost(content.token_usage)
        return result

    def _estimate_cost(self, usage: TokenUsage) -> float:
        """Estimate USD cost from token counts and configured price rates."""
        in_rate, out_rate = self.config.cost_rates()
        cost = usage.prompt_tokens / 1e6 * in_rate
        cost += usage.completion_tokens / 1e6 * out_rate
        return round(cost, 6)
