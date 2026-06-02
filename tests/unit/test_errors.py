"""Unit tests for the typed error hierarchy."""

from __future__ import annotations

from startup_book.shared.errors import (
    ConfigError,
    CrewExecutionError,
    GatekeeperError,
    LatexCompileError,
    RateLimitExceededError,
    StartupBookError,
)


def test_all_errors_subclass_base() -> None:
    for err in (ConfigError, GatekeeperError, CrewExecutionError, LatexCompileError):
        assert issubclass(err, StartupBookError)


def test_rate_limit_is_a_gatekeeper_error() -> None:
    assert issubclass(RateLimitExceededError, GatekeeperError)


def test_latex_error_carries_log_tail() -> None:
    err = LatexCompileError("boom", log_tail="...last lines...")
    assert str(err) == "boom"
    assert err.log_tail == "...last lines..."


def test_latex_error_log_tail_defaults_empty() -> None:
    assert LatexCompileError("boom").log_tail == ""
