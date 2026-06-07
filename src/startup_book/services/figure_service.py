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
from startup_book.shared.safe_warnings import warns_safely  # noqa: E402

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
        return [self.jcurve(), self.unit_economics(), self.funnel(), self.illustration()]

    @warns_safely
    def illustration(self) -> Path:
        """Render a decorative raster (PNG) cover illustration (FR-B3 image).

        A stylised "growth" scene — an upward trajectory with a rocket — drawn
        with matplotlib patches and saved as a raster PNG, distinct from the
        vector data graphs.
        """
        import matplotlib.patches as mpatches

        fig, ax = plt.subplots(figsize=(5.2, 3.0))
        ax.set_xlim(0, 10)
        ax.set_ylim(0, 6)
        ax.axis("off")
        ax.add_patch(mpatches.Rectangle((0, 0), 10, 6, color="#eef2fa"))
        xs = [i * 0.2 for i in range(46)]
        ys = [0.4 + 0.05 * (x**1.9) for x in xs]
        ax.plot(xs, ys, color=_BLUE, lw=3)
        for sx, sy in [(1.5, 5.2), (3.2, 4.6), (7.5, 5.4), (8.8, 3.2)]:
            ax.scatter([sx], [sy], marker="*", s=140, color=_RED, zorder=4)
        rx, ry = xs[-1], ys[-1]
        ax.scatter([rx], [ry], marker="^", s=420, color=_RED, zorder=5)
        ax.text(0.4, 5.4, "Idea", color=_BLUE, fontsize=12, weight="bold")
        ax.text(8.0, 1.8, "Scale", color=_GREEN, fontsize=12, weight="bold")
        path = self.out_dir / "illustration.png"
        fig.savefig(path, format="png", dpi=200, bbox_inches="tight")
        plt.close(fig)
        return path

    @warns_safely
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

    @warns_safely
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

    @warns_safely
    def funnel(self) -> Path:
        """Plot an AARRR acquisition→revenue conversion funnel (centred bars)."""
        stages = ["Acquisition", "Activation", "Retention", "Referral", "Revenue"]
        values = [10000, 3500, 1800, 950, 620]
        palette = [_BLUE, _BLUE, _GREEN, _GREEN, _RED]
        fig, ax = plt.subplots(figsize=(5.6, 3.2))
        for row, (name, value, colour) in enumerate(zip(stages, values, palette, strict=True)):
            y = len(stages) - row
            ax.barh(y, value, height=0.72, left=-value / 2, color=colour)
            ax.text(5400, y, f"{name} · {value:,}", ha="left", va="center", fontsize=9, color="#1A2433")
        ax.set_xlim(-5200, 11200)
        ax.axis("off")
        return self._save(fig, "funnel.pdf")

    def _save(self, fig: plt.Figure, name: str) -> Path:
        """Save ``fig`` as a tight vector PDF and close it; return the path.

        ``bbox_inches="tight"`` handles the layout; we deliberately avoid
        ``tight_layout()`` (its compatibility warning clashes with pydantic's
        global ``warnings.warn`` wrapper once CrewAI is imported).
        """
        path = self.out_dir / name
        fig.savefig(path, format="pdf", bbox_inches="tight")
        plt.close(fig)
        return path
