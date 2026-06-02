"""Unit tests for the SystemClock."""

from __future__ import annotations

from startup_book.shared.clock import SystemClock


def test_now_is_monotonic() -> None:
    clock = SystemClock()
    first = clock.now()
    second = clock.now()
    assert second >= first


def test_sleep_zero_is_noop(monkeypatch) -> None:
    called: list[float] = []
    monkeypatch.setattr("time.sleep", lambda s: called.append(s))
    SystemClock().sleep(0)
    assert called == []  # non-positive sleeps are skipped


def test_sleep_positive_calls_time_sleep(monkeypatch) -> None:
    called: list[float] = []
    monkeypatch.setattr("time.sleep", lambda s: called.append(s))
    SystemClock().sleep(0.01)
    assert called == [0.01]
