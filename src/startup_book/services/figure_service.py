"""Figure service: generate the book's Python-made graphs (assignment FR-B4).

Why: the book must contain at least one graph produced by Python code. This
service renders vector PDFs with matplotlib (Agg backend, no display) into
``assets/figures/`` so LaTeX can ``\\includegraphics`` them. Figure labels are
intentionally English (LTR) for clean technical readability inside an RTL book.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # headless backend; must precede pyplot import
import matplotlib.pyplot as plt  # noqa: E402  (backend set above on purpose)

from startup_book.constants import FIGURES_DIR  # noqa: E402

_BLUE = "#1f3b73"
_RED = "#c0392b"
_GREEN = "#2e7d57"


class FigureService:
    """Renders the startup book's figures as vector PDFs."""

    def __init__(self, out_dir: Path | None = None) -> None:
        """Create the service.

        Args:
            out_dir: Output directory for the PDFs (defaults to ``assets/figures``).
        """
        self.out_dir = out_dir or FIGURES_DIR
        self.out_dir.mkdir(parents=True, exist_ok=True)

    def generate_all(self) -> list[Path]:
        """Render every figure and return the list of written paths."""
        return [self.jcurve(), self.unit_economics()]

    def jcurve(self) -> Path:
        """Plot the classic startup cash-flow J-curve over 24 months."""
        months = list(range(25))
        revenue = [2.0 * (1.25**t) for t in months]  # $K, compounding
        burn = 30.0  # fixed monthly burn, $K
        cumulative, running = [], 0.0
        for r in revenue:
            running += r - burn
            cumulative.append(running)

        fig, ax = plt.subplots(figsize=(5.4, 3.2))
        ax.plot(months, cumulative, color=_BLUE, lw=2.2, label="Cumulative cash")
        ax.axhline(0, color="grey", lw=0.8, ls="--")
        trough = min(range(len(cumulative)), key=lambda i: cumulative[i])
        ax.scatter([trough], [cumulative[trough]], color=_RED, zorder=5)
        ax.annotate(
            "cash trough",
            (trough, cumulative[trough]),
            textcoords="offset points",
            xytext=(8, -14),
            color=_RED,
            fontsize=9,
        )
        ax.set_xlabel("Month")
        ax.set_ylabel("Cumulative cash flow ($K)")
        ax.set_title("Startup Cash-Flow J-Curve")
        ax.legend(frameon=False, fontsize=9)
        ax.grid(True, alpha=0.25)
        return self._save(fig, "jcurve.pdf")

    def unit_economics(self) -> Path:
        """Bar chart comparing LTV and CAC per acquisition channel."""
        channels = ["Organic", "Paid search", "Referral"]
        ltv = [900, 720, 1100]
        cac = [120, 360, 200]
        x = range(len(channels))
        width = 0.38

        fig, ax = plt.subplots(figsize=(5.4, 3.2))
        ax.bar([i - width / 2 for i in x], ltv, width, color=_GREEN, label="LTV")
        ax.bar([i + width / 2 for i in x], cac, width, color=_RED, label="CAC")
        for i, (lv, cv) in enumerate(zip(ltv, cac, strict=True)):
            ax.text(i, max(lv, cv) + 25, f"{lv / cv:.1f}:1", ha="center", fontsize=9, color=_BLUE)
        ax.set_xticks(list(x))
        ax.set_xticklabels(channels)
        ax.set_ylabel("USD per customer")
        ax.set_title("Unit Economics — LTV vs CAC (ratio on top)")
        ax.legend(frameon=False, fontsize=9)
        ax.grid(True, axis="y", alpha=0.25)
        return self._save(fig, "unit_economics.pdf")

    def _save(self, fig: plt.Figure, name: str) -> Path:
        """Save ``fig`` as a tight vector PDF and close it; return the path."""
        path = self.out_dir / name
        fig.tight_layout()
        fig.savefig(path, format="pdf", bbox_inches="tight")
        plt.close(fig)
        return path
