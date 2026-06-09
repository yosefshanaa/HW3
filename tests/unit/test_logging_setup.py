"""Unit tests for JSON-line logging setup (guidelines §7.4)."""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

import pytest

from startup_book.shared.errors import ConfigError
from startup_book.shared.logging_setup import JsonLineFormatter, configure_logging
from startup_book.shared.redaction import RedactionFilter


def _record(msg: str, *args: object, exc_info: object = None) -> logging.LogRecord:
    return logging.LogRecord(
        name="startup_book.x",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg=msg,
        args=args,
        exc_info=exc_info,
    )


def test_json_line_formatter_emits_single_json_object() -> None:
    payload = json.loads(JsonLineFormatter().format(_record("hello %s", "world")))
    assert payload["level"] == "INFO"
    assert payload["logger"] == "startup_book.x"
    assert payload["msg"] == "hello world"
    assert "ts" in payload


def test_json_line_formatter_includes_exception() -> None:
    try:
        raise ValueError("boom")
    except ValueError:
        rec = _record("failed", exc_info=sys.exc_info())
    payload = json.loads(JsonLineFormatter().format(rec))
    assert "boom" in payload["exc"]


def test_json_line_formatter_keeps_hebrew_unescaped() -> None:
    payload_line = JsonLineFormatter().format(_record("פרק נכתב"))
    assert "פרק נכתב" in payload_line


def test_configure_logging_installs_redaction_and_json() -> None:
    """The shipped config/logging_config.json must load and wire redaction+JSON."""
    root = logging.getLogger()
    sb = logging.getLogger("startup_book")
    saved = [(lg, lg.handlers[:], lg.level, lg.propagate) for lg in (root, sb)]
    try:
        configure_logging()
        handlers = sb.handlers
        assert handlers, "configure_logging should install at least one handler"
        assert any(isinstance(f, RedactionFilter) for h in handlers for f in h.filters)
        assert any(isinstance(h.formatter, JsonLineFormatter) for h in handlers)
    finally:
        for lg, hs, lvl, prop in saved:
            lg.handlers = hs
            lg.setLevel(lvl)
            lg.propagate = prop


def test_configure_logging_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(ConfigError):
        configure_logging(tmp_path / "nope.json")


def test_configure_logging_invalid_json_raises(tmp_path: Path) -> None:
    bad = tmp_path / "logging_config.json"
    bad.write_text("{ not json", encoding="utf-8")
    with pytest.raises(ConfigError):
        configure_logging(bad)
