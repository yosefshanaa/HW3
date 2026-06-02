"""Central API gatekeeper: every external call funnels through here (§5).

Why: a production agent must control and observe its outward actions. This class
enforces sliding-window rate limits, applies FIFO backpressure when overloaded,
retries transient failures, and logs every attempt — so no agent step can hit
the network unmetered.
"""

from __future__ import annotations

import logging
from collections import deque
from collections.abc import Callable
from typing import TypeVar

from startup_book.shared.clock import Clock, SystemClock
from startup_book.shared.errors import GatekeeperError, RateLimitExceeded
from startup_book.shared.models import QueueStatus, RateLimitConfig

T = TypeVar("T")
logger = logging.getLogger("startup_book.gatekeeper")

_MINUTE = 60.0
_HOUR = 3600.0


class ApiGatekeeper:
    """Rate-limited, retrying, observable wrapper around external calls."""

    def __init__(self, config: RateLimitConfig, clock: Clock | None = None) -> None:
        """Create a gatekeeper.

        Args:
            config: The rate-limit policy (from ``rate_limits.json``).
            clock: Time source; defaults to the real :class:`SystemClock`.
        """
        self._cfg = config
        self._clock = clock or SystemClock()
        self._minute_calls: deque[float] = deque()
        self._hour_calls: deque[float] = deque()
        self._pending = 0
        self._status = QueueStatus()

    def get_queue_status(self) -> QueueStatus:
        """Return a copy of the current queue/counter snapshot."""
        return self._status.model_copy()

    def execute(self, fn: Callable[..., T], *args: object, **kwargs: object) -> T:
        """Run ``fn`` through admission control and retry handling.

        Raises:
            RateLimitExceeded: If the pending queue is full (backpressure).
            GatekeeperError: If the call still fails after ``max_retries``.
        """
        self._admit()
        return self._run_with_retry(fn, *args, **kwargs)

    # --- admission / sliding-window rate limiting ---------------------------
    def _prune(self, now: float) -> None:
        """Drop call timestamps that have left the minute/hour windows."""
        while self._minute_calls and now - self._minute_calls[0] >= _MINUTE:
            self._minute_calls.popleft()
        while self._hour_calls and now - self._hour_calls[0] >= _HOUR:
            self._hour_calls.popleft()

    def _wait_seconds(self, now: float) -> float:
        """Return seconds until a slot frees (0.0 if a call may proceed now)."""
        waits = [0.0]
        if len(self._minute_calls) >= self._cfg.requests_per_minute:
            waits.append(_MINUTE - (now - self._minute_calls[0]))
        if len(self._hour_calls) >= self._cfg.requests_per_hour:
            waits.append(_HOUR - (now - self._hour_calls[0]))
        return max(waits)

    def _admit(self) -> None:
        """Block (via the clock) until the rate limit allows one more call."""
        if self._pending >= self._cfg.max_queue_depth:
            raise RateLimitExceeded("gatekeeper queue is full (backpressure)")
        self._pending += 1
        self._status.queued = self._pending
        try:
            while True:
                now = self._clock.now()
                self._prune(now)
                wait = self._wait_seconds(now)
                if wait <= 0:
                    break
                self._clock.sleep(wait)
            stamp = self._clock.now()
            self._minute_calls.append(stamp)
            self._hour_calls.append(stamp)
        finally:
            self._pending -= 1
            self._status.queued = self._pending

    # --- execution / retry ---------------------------------------------------
    def _run_with_retry(self, fn: Callable[..., T], *args: object, **kwargs: object) -> T:
        """Execute ``fn`` with bounded retries on transient failures."""
        attempt = 0
        while True:
            try:
                result = fn(*args, **kwargs)
                self._status.served += 1
                logger.info("api call ok (attempt %d)", attempt + 1)
                return result
            except Exception as exc:
                if attempt >= self._cfg.max_retries:
                    logger.error("api call failed permanently: %s", exc)
                    raise GatekeeperError(
                        f"call failed after {attempt + 1} attempts: {exc}"
                    ) from exc
                attempt += 1
                self._status.retried += 1
                logger.warning("api call failed, retrying (%d): %s", attempt, exc)
                self._clock.sleep(self._cfg.retry_after_seconds)
