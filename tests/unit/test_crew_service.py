"""Unit tests for the crew service (crew run mocked — no network)."""

from __future__ import annotations

from pathlib import Path

import pytest

from startup_book.services.crew_service import CrewService, GatekeptLLM
from startup_book.shared.config import ConfigManager
from startup_book.shared.errors import CrewExecutionError
from startup_book.shared.gatekeeper import ApiGatekeeper
from startup_book.shared.models import BookContent, Chapter, RateLimitConfig


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


def test_generate_content_fills_title_and_usage(config_dir: Path, monkeypatch) -> None:
    svc = _service(config_dir)
    content = BookContent(title="", chapters=[Chapter(id="intro", heading="מבוא")])
    monkeypatch.setattr(svc, "_run_crew", lambda inputs: _Result(content))

    result = svc.generate_content("My Topic")
    assert result.title == "כותרת"  # default from config (was empty)
    assert result.token_usage.prompt_tokens == 120
    assert result.token_usage.completion_tokens == 80


def test_generate_content_builds_topic_and_outline(config_dir: Path, monkeypatch) -> None:
    captured: dict[str, str] = {}

    def fake_run(inputs: dict[str, str]) -> _Result:
        captured.update(inputs)
        return _Result(BookContent(title="t"))

    svc = _service(config_dir)
    monkeypatch.setattr(svc, "_run_crew", fake_run)
    svc.generate_content("My Topic")
    assert captured["topic"] == "My Topic"
    assert "intro" in captured["outline"]


def test_unstructured_output_raises(config_dir: Path, monkeypatch) -> None:
    svc = _service(config_dir)
    monkeypatch.setattr(svc, "_run_crew", lambda inputs: _Result(pydantic=None))
    with pytest.raises(CrewExecutionError):
        svc.generate_content("t")


def test_crew_failure_is_wrapped(config_dir: Path, monkeypatch) -> None:
    svc = _service(config_dir)

    def boom(inputs: dict[str, str]) -> None:
        raise RuntimeError("llm down")

    monkeypatch.setattr(svc, "_run_crew", boom)
    with pytest.raises(CrewExecutionError):
        svc.generate_content("t")


def test_extract_usage_handles_missing() -> None:
    assert CrewService._extract_usage(_Result(None, usage=None)).total_tokens == 0


def test_gatekept_llm_routes_call_through_gatekeeper(fake_clock, monkeypatch) -> None:
    gk = ApiGatekeeper(_service_config(), fake_clock)
    calls = {"gatekeeper": 0, "llm": 0}

    class FakeInnerLLM:
        model = "gpt-4o-mini"
        temperature = 0.0
        provider = "openai"
        stop: list[str] = []
        additional_params: dict[str, object] = {}

        def call(self, *args: object, **kwargs: object) -> str:
            calls["llm"] += 1
            return "ok"

    def fake_execute(fn, *args: object, **kwargs: object) -> object:
        calls["gatekeeper"] += 1
        return fn(*args, **kwargs)

    monkeypatch.setattr(gk, "execute", fake_execute)

    llm = GatekeptLLM(gatekeeper=gk, inner=FakeInnerLLM())
    assert llm.call("hello") == "ok"
    assert calls == {"gatekeeper": 1, "llm": 1}
