"""Unit tests for secret redaction in log output (guidelines §2.4 + §7.4)."""

from __future__ import annotations

import io
import logging

from startup_book.shared.logging_setup import JsonLineFormatter
from startup_book.shared.redaction import RedactionFilter, redact


def _logger_with_redaction(name: str) -> tuple[logging.Logger, io.StringIO]:
    """Build an isolated logger whose single handler redacts + JSON-formats."""
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonLineFormatter())
    handler.addFilter(RedactionFilter())
    logger = logging.getLogger(name)
    logger.handlers = [handler]
    logger.setLevel(logging.INFO)
    logger.propagate = False
    return logger, stream


def test_redact_masks_sk_style_key() -> None:
    masked = redact("authorization: Bearer sk-ABCD1234efgh5678IJKL")
    assert "sk-ABCD1234" not in masked
    assert "REDACTED" in masked


def test_redact_masks_env_api_key_value(monkeypatch) -> None:
    # A custom (non sk-) key value must still be scrubbed via the env lookup.
    monkeypatch.setenv("OPENAI_API_KEY", "totally-custom-not-sk-value")
    masked = redact("key=totally-custom-not-sk-value done")
    assert "totally-custom-not-sk-value" not in masked
    assert "REDACTED" in masked


def test_redact_passthrough_when_no_secret(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert redact("nothing secret here") == "nothing secret here"


def test_api_key_never_reaches_logs() -> None:
    """The required test: a key in a log message never reaches handler output."""
    logger, stream = _logger_with_redaction("startup_book.tests.redaction")

    logger.info("calling OpenAI with sk-SECRETKEY1234567890abcdef now")

    out = stream.getvalue()
    assert "sk-SECRETKEY" not in out
    assert "REDACTED" in out


def test_redaction_filter_redacts_percent_args() -> None:
    """%-style args are merged into the message and redacted too."""
    logger, stream = _logger_with_redaction("startup_book.tests.redaction.args")

    logger.info("key=%s", "sk-ABCDEFGH12345678")

    assert "sk-ABCDEF" not in stream.getvalue()
