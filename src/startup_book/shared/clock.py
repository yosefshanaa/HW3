"""A tiny clock abstraction so time-dependent code is deterministically testable.

Why: the gatekeeper enforces rate limits over time. Tests must not sleep for real
seconds, so time is injected. Production uses :class:`SystemClock`; tests use a
fake clock that advances virtual time on ``sleep`` (see ``tests/``).
"""

from __future__ import annotations

import time
from typing import Protocol


class Clock(Protocol):
    """Monotonic time source with a sleep primitive."""

    def now(self) -> float:
        """Return a monotonically increasing time in seconds."""
        ...

    def sleep(self, seconds: float) -> None:
        """Advance time by ``seconds`` (really sleeping in production)."""
        ...


class SystemClock:
    """The real clock: monotonic time and a real sleep."""

    def now(self) -> float:
        """Return the process monotonic clock in seconds."""
        return time.monotonic()

    def sleep(self, seconds: float) -> None:
        """Sleep for ``seconds`` (no-op for non-positive values)."""
        if seconds > 0:
            time.sleep(seconds)
