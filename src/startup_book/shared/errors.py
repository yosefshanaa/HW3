"""Typed exception hierarchy for the project.

Why: the guidelines (§6.3) require clear error messages and graceful failure.
A small, explicit hierarchy lets callers distinguish *what* failed (config, the
gatekeeper, the crew, the LaTeX build) and handle each appropriately, instead of
catching bare ``Exception``.
"""

from __future__ import annotations


class StartupBookError(Exception):
    """Base class for every error raised by this package."""


class ConfigError(StartupBookError):
    """A configuration file is missing, malformed, or version-incompatible."""


class GatekeeperError(StartupBookError):
    """An external call failed permanently after passing through the gatekeeper."""


class RateLimitExceededError(GatekeeperError):
    """The request could not be served because the queue is full (backpressure)."""


class CrewExecutionError(StartupBookError):
    """The CrewAI pipeline failed to produce content."""


class LatexCompileError(StartupBookError):
    """The LaTeX build returned a non-zero exit code.

    Attributes:
        log_tail: The last lines of the compiler log, to aid debugging.
    """

    def __init__(self, message: str, log_tail: str = "") -> None:
        super().__init__(message)
        self.log_tail = log_tail
