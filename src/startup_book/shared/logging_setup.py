"""JSON-line logging configuration (guidelines §7.4).

Why: structured, one-object-per-line logs are greppable and machine-parseable.
The configuration is *loaded from* ``config/logging_config.json`` (never
hardcoded — §7.2/§7.3) and every record passes through the
:class:`~startup_book.shared.redaction.RedactionFilter` so secrets cannot leak.
"""

from __future__ import annotations

import json
import logging
import logging.config
from pathlib import Path

import startup_book.constants as c
from startup_book.shared.errors import ConfigError


class JsonLineFormatter(logging.Formatter):
    """Render each log record as a single JSON object (one line, UTF-8)."""

    def format(self, record: logging.LogRecord) -> str:
        """Serialise the record to a compact JSON line (Hebrew kept unescaped)."""
        payload: dict[str, object] = {
            "ts": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(config_path: Path | None = None) -> None:
    """Load the JSON logging config and apply it via :func:`logging.config.dictConfig`.

    Args:
        config_path: Optional override for ``config/logging_config.json``.

    Raises:
        ConfigError: If the file is missing or is not valid JSON.
    """
    path = Path(config_path or c.LOGGING_CONFIG_FILE)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ConfigError(f"Missing logging config: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ConfigError(f"Invalid JSON in {path}: {exc}") from exc
    logging.config.dictConfig(data)
