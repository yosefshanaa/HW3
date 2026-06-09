"""Unit tests for the crew service (crew run mocked — no network)."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from startup_book.services.crew_service import CrewService, GatekeptLLM
from startup_book.shared.config import ConfigManager
from startup_book.shared.errors import CrewExecutionError
from startup_book.shared.gatekeeper import ApiGatekeeper
from startup_book.shared.models import BookContent, Chapter, RateLimitConfig


class FakeInnerLLM:
    """A minimal crewai-LLM stand-in that records calls and answers capabilities."""

    model = "gpt-4o-mini"
    temperature = 0.0
    provider = "openai"
    stop: list[str] = []
    additional_params: dict[str, object] = {}

    def __init__(self) -> None:
        self.calls = 0

    def call(self, *args: object, **kwargs: object) -> str:
        self.calls += 1
        return "ok"

    def supports_function_calling(self) -> bool:
        return True

    def supports_stop_words(self) -> bool:
        return False

    def get_context_window_size(self) -> int:
        return 4096

    def supports_multimodal(self) -> bool:
        return True

    def format_text_content(self, text: str) -> dict[str, object]:
        return {"type": "text", "text": text}

    def to_config_dict(self) -> dict[str, object]:
        return {"model": self.model}


class _Usage:
    prompt_tokens = 120
    completion_tokens = 80


class _Result:
    def __init__(self, pydantic: object, usage: object = _Usage()) -> None:
        self.pydantic = pydantic
        self.token_usage = usage


def _service(config_dir: Path) -> CrewService:
    cm = ConfigManager(config_dir)
    return CrewService(cm, ApiGatekeeper(cm.rate_limit()))


def _service_config() -> RateLimitConfig:
    """Build a permissive gatekeeper config for LLM wrapper tests."""
    return RateLimitConfig(
        requests_per_minute=100,
        requests_per_hour=1000,
        concurrent_max=2,
        retry_after_seconds=0,
        max_retries=0,
        max_queue_depth=10,
    )


def test_generate_content_aggregates_chapters_title_and_usage(
    config_dir: Path, monkeypatch
) -> None:
    # The test config has 2 chapters -> 2 crew runs -> usage is summed. A fresh
    # result per call (production returns a new crew result each run).
    svc = _service(config_dir)
    monkeypatch.setattr(
        svc,
        "_run_chapter",
        lambda llm, topic, heading: _Result(
            BookContent(title="", chapters=[Chapter(id="x", heading="h")])
        ),
    )

    result = svc.generate_content("My Topic")
    assert result.title == "כותרת"  # from config
    assert [c.heading for c in result.chapters] == ["מבוא", "רזה"]  # per-spec headings
    assert result.token_usage.prompt_tokens == 240  # 120 * 2 chapters
    assert result.token_usage.completion_tokens == 160  # 80 * 2 chapters


def test_generate_content_runs_each_chapter_with_topic(config_dir: Path, monkeypatch) -> None:
    seen: list[tuple[str, str]] = []

    def fake_run(llm: object, topic: str, heading: str) -> _Result:
        seen.append((topic, heading))
        return _Result(BookContent(title="t", chapters=[Chapter(id="x", heading=heading)]))

    svc = _service(config_dir)
    monkeypatch.setattr(svc, "_run_chapter", fake_run)
    svc.generate_content("My Topic")
    assert [t for t, _ in seen] == ["My Topic", "My Topic"]  # topic passed each run
    assert [h for _, h in seen] == ["מבוא", "רזה"]  # one run per chapter heading


def test_unstructured_output_raises(config_dir: Path, monkeypatch) -> None:
    svc = _service(config_dir)
    monkeypatch.setattr(svc, "_run_chapter", lambda llm, topic, heading: _Result(pydantic=None))
    with pytest.raises(CrewExecutionError):
        svc.generate_content("t")


def test_crew_failure_is_wrapped(config_dir: Path, monkeypatch) -> None:
    svc = _service(config_dir)

    def boom(llm: object, topic: str, heading: str) -> None:
        raise RuntimeError("llm down")

    monkeypatch.setattr(svc, "_run_chapter", boom)
    with pytest.raises(CrewExecutionError):
        svc.generate_content("t")


def test_extract_usage_handles_missing() -> None:
    assert CrewService._extract_usage(_Result(None, usage=None)).total_tokens == 0


def test_gatekept_llm_routes_call_through_gatekeeper(fake_clock, monkeypatch) -> None:
    gk = ApiGatekeeper(_service_config(), fake_clock)
    seen = {"gatekeeper": 0}
    inner = FakeInnerLLM()

    def fake_execute(fn, *args: object, **kwargs: object) -> object:
        seen["gatekeeper"] += 1
        return fn(*args, **kwargs)

    monkeypatch.setattr(gk, "execute", fake_execute)

    llm = GatekeptLLM(gatekeeper=gk, inner=inner)
    assert llm.call("hello") == "ok"
    assert (seen["gatekeeper"], inner.calls) == (1, 1)


def test_gatekept_llm_async_call_routes_through_gatekeeper(fake_clock) -> None:
    gk = ApiGatekeeper(_service_config(), fake_clock)
    inner = FakeInnerLLM()
    llm = GatekeptLLM(gatekeeper=gk, inner=inner)

    assert asyncio.run(llm.acall("hello")) == "ok"
    assert inner.calls == 1


def test_gatekept_llm_delegates_capabilities(fake_clock) -> None:
    gk = ApiGatekeeper(_service_config(), fake_clock)
    inner = FakeInnerLLM()
    llm = GatekeptLLM(gatekeeper=gk, inner=inner)

    assert llm.supports_function_calling() is True
    assert llm.supports_stop_words() is False
    assert llm.supports_multimodal() is True
    assert llm.get_context_window_size() == 4096
    assert llm.format_text_content("hi") == {"type": "text", "text": "hi"}
    assert llm.to_config_dict() == {"model": "gpt-4o-mini"}
