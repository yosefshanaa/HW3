"""Immutable project-wide constants (guidelines §7.3).

Why: values that are intrinsic to the project (paths, filenames, enum-like
labels) live here as named constants instead of being scattered as magic
literals. Tunable values that an operator might change (model, rate limits) do
NOT belong here — those are read from ``config/`` files via the config manager.
"""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path

# --- Repository layout -------------------------------------------------------
# constants.py lives at src/startup_book/constants.py, so the repo root is three
# parents up. All other locations are derived relative to it (never absolute).
PACKAGE_ROOT: Path = Path(__file__).resolve().parent
REPO_ROOT: Path = PACKAGE_ROOT.parents[1]

CONFIG_DIR: Path = REPO_ROOT / "config"
ASSETS_DIR: Path = REPO_ROOT / "assets"
FIGURES_DIR: Path = ASSETS_DIR / "figures"
LATEX_DIR: Path = REPO_ROOT / "latex"
RESULTS_DIR: Path = REPO_ROOT / "results"

# --- Config filenames --------------------------------------------------------
SETUP_CONFIG_FILE: str = "setup.json"
RATE_LIMITS_FILE: str = "rate_limits.json"

# Logging config follows Python's dictConfig schema (its own ``version: 1``), so
# it is loaded directly rather than through the versioned ConfigManager.
LOGGING_CONFIG_FILE: Path = CONFIG_DIR / "logging_config.json"

# --- Environment variable names ----------------------------------------------
ENV_OPENAI_API_KEY: str = "OPENAI_API_KEY"
ENV_OPENAI_BASE_URL: str = "OPENAI_BASE_URL"
ENV_OPENAI_MODEL: str = "OPENAI_MODEL"

# --- Output artefacts --------------------------------------------------------
BOOK_PDF_NAME: str = "book.pdf"
MAIN_TEX_NAME: str = "main.tex"


class Language(StrEnum):
    """Chapter language mode used to drive BiDi handling in LaTeX."""

    HEBREW = "he"
    MIXED = "mixed"  # Hebrew prose with embedded English/code (BiDi chapter)
