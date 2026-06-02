"""Shared pytest fixtures (guidelines §6.1).

Provides a temporary, valid config directory, a deterministic fake clock for the
gatekeeper, and a sample :class:`BookContent`, so tests never touch the network,
the real clock, or a real LaTeX engine.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from startup_book.shared.models import BookContent, Chapter, Source

_SETUP = {
    "version": "1.00",
    "book": {
        "title_he": "כותרת",
        "title_en": "Title",
        "author": "tester",
        "course_he": "קורס",
        "lecturer_he": "מרצה",
        "language": "he",
        "chapters": [
            {"id": "intro", "heading_he": "מבוא", "language": "he"},
            {"id": "lean", "heading_he": "רזה", "language": "mixed"},
        ],
    },
    "llm": {
        "model": "gpt-4o-mini",
        "temperature": 0.3,
        "cost_per_1m_input_usd": 0.15,
        "cost_per_1m_output_usd": 0.60,
    },
    "build": {"engine": "lualatex", "passes": 4, "use_biber": True},
}

_LIMITS = {
    "version": "1.00",
    "services": {
        "default": {
            "requests_per_minute": 30,
            "requests_per_hour": 500,
            "concurrent_max": 5,
            "retry_after_seconds": 30,
            "max_retries": 3,
            "max_queue_depth": 100,
        }
    },
}


@pytest.fixture
def config_dir(tmp_path: Path) -> Path:
    """Write a valid setup.json + rate_limits.json to a temp dir and return it."""
    (tmp_path / "setup.json").write_text(json.dumps(_SETUP), encoding="utf-8")
    (tmp_path / "rate_limits.json").write_text(json.dumps(_LIMITS), encoding="utf-8")
    return tmp_path


@pytest.fixture
def sample_content() -> BookContent:
    """A small, valid BookContent payload for rendering/SDK tests."""
    return BookContent(
        title="כותרת",
        chapters=[
            Chapter(id="intro", heading="מבוא", body_markdown="## כותרת\n\nגוף **מודגש**."),
            Chapter(id="lean", heading="רזה", body_markdown="- פריט\n- פריט"),
        ],
        sources=[Source(key="ries2011", title="The Lean Startup", author="Ries", year="2011")],
    )


class FakeClock:
    """A virtual clock: ``sleep`` advances time instead of blocking."""

    def __init__(self) -> None:
        self.t = 0.0
        self.sleeps: list[float] = []

    def now(self) -> float:
        return self.t

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.t += seconds


@pytest.fixture
def fake_clock() -> FakeClock:
    """Return a fresh :class:`FakeClock`."""
    return FakeClock()
