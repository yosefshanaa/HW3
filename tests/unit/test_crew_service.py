"""Unit tests for the crew service (crew run mocked — no network)."""

from __future__ import annotations

import asyncio
import json
import threading
import time
from pathlib import Path

import pytest

from startup_book.services.crew_service import CrewService
from startup_book.services.gatekept_llm import GatekeptLLM
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
    """Stand-in for CrewAI's ``crew.usage_metrics`` (where token counts live)."""

    prompt_tokens = 120
    completion_tokens = 80


class _Result:
    """Stand-in for ``CrewOutput`` — it carries ``pydantic`` but NO token_usage."""

    def __init__(self, pydantic: object) -> None:
        self.pydantic = pydantic


def _ok(heading: str = "h") -> tuple[_Result, _Usage]:
    """A fake ``_run_chapter`` return value: ``(crew result, usage metrics)``."""
    return _Result(BookContent(title="", chapters=[Chapter(id="x", heading=heading)])), _Usage()


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
    monkeypatch.setattr(svc, "_run_chapter", lambda llm, topic, heading: _ok())

    result = svc.generate_content("My Topic")
    assert result.title == "כותרת"  # from config
    assert [c.heading for c in result.chapters] == ["מבוא", "רזה"]  # per-spec headings
    assert result.token_usage.prompt_tokens == 240  # 120 * 2 chapters
    assert result.token_usage.completion_tokens == 160  # 80 * 2 chapters


def test_generate_content_runs_each_chapter_with_topic(config_dir: Path, monkeypatch) -> None:
    seen: list[tuple[str, str]] = []

    def fake_run(llm: object, topic: str, heading: str) -> tuple[_Result, _Usage]:
        seen.append((topic, heading))
        return _ok(heading)

    svc = _service(config_dir)
    monkeypatch.setattr(svc, "_run_chapter", fake_run)
    svc.generate_content("My Topic")
    # Chapters run concurrently, so completion order is not deterministic; assert
    # on membership instead: the topic reaches every run, once per heading.
    assert {t for t, _ in seen} == {"My Topic"}
    assert sorted(h for _, h in seen) == sorted(["מבוא", "רזה"])


def test_unstructured_output_raises(config_dir: Path, monkeypatch) -> None:
    svc = _service(config_dir)
    monkeypatch.setattr(
        svc, "_run_chapter", lambda llm, topic, heading: (_Result(None), _Usage())
    )
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
    assert CrewService._extract_usage(None).total_tokens == 0


def test_run_chapter_reads_usage_from_crew_metrics(config_dir: Path, monkeypatch) -> None:
    """Token usage must come from ``crew.usage_metrics`` (the real CrewAI location),
    not from a non-existent ``result.token_usage`` — the §11 cost-reporting bug."""
    svc = _service(config_dir)

    class FakeCrew:
        usage_metrics = _Usage()

        def __init__(self, **kwargs: object) -> None:
            pass

        def kickoff(self, inputs: dict[str, object]) -> _Result:
            return _Result(BookContent(title="", chapters=[Chapter(id="x", heading="h")]))

    monkeypatch.setattr("startup_book.services.crew_service.build_agents", lambda llm: {})
    monkeypatch.setattr(
        "startup_book.services.crew_service.build_chapter_tasks",
        lambda agents, heading: [],
    )
    monkeypatch.setattr("startup_book.services.crew_service.Crew", FakeCrew)

    result, usage = svc._run_chapter(object(), "topic", "מבוא")
    assert isinstance(result, _Result)
    assert (usage.prompt_tokens, usage.completion_tokens) == (120, 80)


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


def _write_config(config_dir: Path, *, n_chapters: int, concurrent_max: int) -> None:
    """Write a setup.json with N chapters and a rate_limits.json with the cap."""
    setup = {
        "version": "1.00",
        "book": {
            "title_he": "כותרת", "title_en": "Title", "author": "t",
            "course_he": "ק", "lecturer_he": "מ", "language": "he",
            "chapters": [
                {"id": f"c{i}", "heading_he": f"פרק {i}", "language": "he"}
                for i in range(n_chapters)
            ],
        },
        "llm": {
            "model": "gpt-4o-mini", "temperature": 0.3,
            "cost_per_1m_input_usd": 0.15, "cost_per_1m_output_usd": 0.60,
        },
        "build": {"engine": "lualatex", "passes": 4, "use_biber": True},
    }
    limits = {
        "version": "1.00",
        "services": {"default": {
            "requests_per_minute": 100, "requests_per_hour": 1000,
            "concurrent_max": concurrent_max, "retry_after_seconds": 0,
            "max_retries": 0, "max_queue_depth": 100,
        }},
    }
    (config_dir / "setup.json").write_text(json.dumps(setup), encoding="utf-8")
    (config_dir / "rate_limits.json").write_text(json.dumps(limits), encoding="utf-8")


def test_chapters_run_concurrently_bounded_by_concurrent_max(tmp_path: Path, monkeypatch) -> None:
    """Chapters run in parallel but never exceed concurrent_max, and come back
    in outline order with usage summed across all runs (§15)."""
    _write_config(tmp_path, n_chapters=6, concurrent_max=2)
    svc = _service(tmp_path)

    state = {"active": 0, "peak": 0}
    lock = threading.Lock()

    def fake_run(llm: object, topic: str, heading: str) -> tuple[_Result, _Usage]:
        with lock:
            state["active"] += 1
            state["peak"] = max(state["peak"], state["active"])
        time.sleep(0.03)  # hold the slot so overlap is observable
        with lock:
            state["active"] -= 1
        return _ok(heading)

    monkeypatch.setattr(svc, "_run_chapter", fake_run)
    result = svc.generate_content("t")

    assert state["peak"] <= 2  # never exceeded concurrent_max (the §15 invariant)
    assert state["peak"] == 2  # but it DID run in parallel, not sequentially
    assert [c.heading for c in result.chapters] == [f"פרק {i}" for i in range(6)]  # ordered
    assert result.token_usage.prompt_tokens == 720  # 120 * 6
    assert result.token_usage.completion_tokens == 480  # 80 * 6
