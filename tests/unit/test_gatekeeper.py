"""Unit tests for the API gatekeeper (PRD_api_gatekeeper scenarios)."""

from __future__ import annotations

import threading
import time
from concurrent.futures import ThreadPoolExecutor

import pytest

from startup_book.shared.errors import GatekeeperError, RateLimitExceededError
from startup_book.shared.gatekeeper import ApiGatekeeper
from startup_book.shared.models import RateLimitConfig


def cfg(**over: object) -> RateLimitConfig:
    """Build a RateLimitConfig with small, test-friendly defaults."""
    base = {
        "requests_per_minute": 10,
        "requests_per_hour": 100,
        "concurrent_max": 5,
        "retry_after_seconds": 30,
        "max_retries": 3,
        "max_queue_depth": 2,
    }
    base.update(over)
    return RateLimitConfig(**base)


class Flaky:
    """A callable that fails ``fails`` times before succeeding."""

    def __init__(self, fails: int) -> None:
        self.fails = fails
        self.calls = 0

    def __call__(self) -> str:
        self.calls += 1
        if self.calls <= self.fails:
            raise RuntimeError("transient")
        return "ok"


def wait_until(predicate) -> None:
    """Wait briefly for a condition that depends on another test thread."""
    deadline = time.monotonic() + 2
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.01)
    raise AssertionError("condition was not reached before timeout")


def test_under_limit_passes_through(fake_clock) -> None:
    gk = ApiGatekeeper(cfg(), fake_clock)
    assert [gk.execute(lambda v=i: v) for i in range(3)] == [0, 1, 2]
    assert fake_clock.sleeps == []
    assert gk.get_queue_status().served == 3


def test_over_minute_limit_waits_then_proceeds(fake_clock) -> None:
    gk = ApiGatekeeper(cfg(requests_per_minute=2), fake_clock)
    gk.execute(lambda: "a")
    gk.execute(lambda: "b")
    assert gk.execute(lambda: "c") == "c"  # third call must wait one window
    assert fake_clock.sleeps == [60.0]


def test_retry_then_success(fake_clock) -> None:
    gk = ApiGatekeeper(cfg(max_retries=3, retry_after_seconds=5), fake_clock)
    flaky = Flaky(fails=2)
    assert gk.execute(flaky) == "ok"
    assert flaky.calls == 3
    assert gk.get_queue_status().retried == 2
    assert fake_clock.sleeps == [5.0, 5.0]


def test_retry_exhausted_raises(fake_clock) -> None:
    gk = ApiGatekeeper(cfg(max_retries=2), fake_clock)
    flaky = Flaky(fails=5)
    with pytest.raises(GatekeeperError):
        gk.execute(flaky)
    assert flaky.calls == 3  # initial + 2 retries
    assert gk.get_queue_status().retried == 2


def test_concurrent_limit_queues_until_active_call_finishes(fake_clock) -> None:
    gk = ApiGatekeeper(cfg(concurrent_max=1, max_queue_depth=2), fake_clock)
    first_started = threading.Event()
    release_first = threading.Event()
    second_started = threading.Event()

    def first_call() -> str:
        first_started.set()
        release_first.wait(timeout=2)
        return "first"

    def second_call() -> str:
        second_started.set()
        return "second"

    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(gk.execute, first_call)
        assert first_started.wait(timeout=1)
        second = pool.submit(gk.execute, second_call)
        wait_until(lambda: gk.get_queue_status().queued == 1)
        assert not second_started.is_set()

        release_first.set()
        assert first.result(timeout=2) == "first"
        assert second.result(timeout=2) == "second"


def test_full_queue_raises_backpressure(fake_clock) -> None:
    gk = ApiGatekeeper(cfg(concurrent_max=1, max_queue_depth=1), fake_clock)
    first_started = threading.Event()
    release_first = threading.Event()

    def first_call() -> str:
        first_started.set()
        release_first.wait(timeout=2)
        return "first"

    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(gk.execute, first_call)
        assert first_started.wait(timeout=1)
        queued = pool.submit(gk.execute, lambda: "queued")
        wait_until(lambda: gk.get_queue_status().queued == 1)

        with pytest.raises(RateLimitExceededError):
            gk.execute(lambda: "third")

        release_first.set()
        assert first.result(timeout=2) == "first"
        assert queued.result(timeout=2) == "queued"
