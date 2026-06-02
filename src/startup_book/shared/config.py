"""Configuration manager: the single place that reads config files and secrets.

Why: the guidelines forbid hardcoded tunables (§7.2) and require a clear config
hierarchy (§7.3) plus version checks (§8.1). Everything tunable (model, limits,
book metadata) is read here from ``config/*.json``; secrets come only from the
environment (``.env`` via python-dotenv), never from source.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from startup_book import constants as c
from startup_book.shared.errors import ConfigError
from startup_book.shared.models import ChapterSpec, RateLimitConfig
from startup_book.shared.version import is_config_compatible


class ConfigManager:
    """Loads and exposes validated configuration and secrets."""

    def __init__(self, config_dir: Path | None = None) -> None:
        """Load ``setup.json`` and ``rate_limits.json`` and the ``.env`` file.

        Args:
            config_dir: Directory holding the JSON config files. Defaults to the
                repository ``config/`` directory.

        Raises:
            ConfigError: If a file is missing, invalid JSON, or version-incompatible.
        """
        load_dotenv(c.REPO_ROOT / ".env")
        self._dir = config_dir or c.CONFIG_DIR
        self._setup = self._load_checked(c.SETUP_CONFIG_FILE)
        self._limits = self._load_checked(c.RATE_LIMITS_FILE)

    def _load_checked(self, filename: str) -> dict[str, Any]:
        """Read a JSON config file and verify its version is compatible."""
        path = self._dir / filename
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise ConfigError(f"Missing config file: {path}") from exc
        except json.JSONDecodeError as exc:
            raise ConfigError(f"Invalid JSON in {path}: {exc}") from exc
        version = str(data.get("version", ""))
        if not is_config_compatible(version):
            raise ConfigError(f"{filename} version {version!r} is incompatible")
        return data

    # --- secrets (environment only) -----------------------------------------
    def openai_api_key(self) -> str | None:
        """Return the OpenAI API key from the environment, if set."""
        return os.environ.get(c.ENV_OPENAI_API_KEY)

    # --- LLM settings --------------------------------------------------------
    def model(self) -> str:
        """Resolve the model name (env override wins over ``setup.json``)."""
        return os.environ.get(c.ENV_OPENAI_MODEL) or self._setup["llm"]["model"]

    def temperature(self) -> float:
        """Sampling temperature for the agents."""
        return float(self._setup["llm"].get("temperature", 0.4))

    def cost_rates(self) -> tuple[float, float]:
        """Return (input, output) USD cost per 1M tokens for cost reporting."""
        llm = self._setup["llm"]
        return (
            float(llm.get("cost_per_1m_input_usd", 0.0)),
            float(llm.get("cost_per_1m_output_usd", 0.0)),
        )

    # --- book metadata -------------------------------------------------------
    def book(self) -> dict[str, Any]:
        """Return the raw ``book`` config block (title, author, course, …)."""
        return self._setup["book"]

    def chapter_specs(self) -> list[ChapterSpec]:
        """Return the chapter outline as validated :class:`ChapterSpec` objects."""
        return [ChapterSpec(**ch) for ch in self._setup["book"]["chapters"]]

    def build_settings(self) -> dict[str, Any]:
        """Return the ``build`` config block (engine, passes, use_biber)."""
        return self._setup.get("build", {})

    # --- rate limits ---------------------------------------------------------
    def rate_limit(self, service: str = "default") -> RateLimitConfig:
        """Return the :class:`RateLimitConfig` for a named service."""
        services = self._limits["services"]
        block = services.get(service, services["default"])
        return RateLimitConfig(**block)
