"""Crew service: assemble the CrewAI crew and run it through the gatekeeper.

Why: this is the orchestration seam between the SDK and CrewAI. It builds the
sequential crew, runs ``kickoff`` *through the API gatekeeper* (so the external
operation is rate-limited, retried and logged — guidelines §5), and parses the
structured result into a :class:`BookContent`.
"""

from __future__ import annotations

import asyncio
import logging

from crewai import LLM, Crew, Process
from crewai.llms.base_llm import BaseLLM
from pydantic import PrivateAttr

from startup_book.agents.definitions import build_agents
from startup_book.agents.tasks import build_chapter_tasks
from startup_book.constants import Language
from startup_book.shared.config import ConfigManager
from startup_book.shared.errors import CrewExecutionError
from startup_book.shared.gatekeeper import ApiGatekeeper
from startup_book.shared.models import BookContent, Chapter, Source, TokenUsage

logger = logging.getLogger("startup_book.crew")


class GatekeptLLM(BaseLLM):
    """CrewAI LLM that routes every model call through the API gatekeeper."""

    _gatekeeper: ApiGatekeeper = PrivateAttr()
    _inner: LLM = PrivateAttr()

    def __init__(self, *, gatekeeper: ApiGatekeeper, inner: LLM) -> None:
        """Create the LLM and keep the gatekeeper outside serialized model data."""
        super().__init__(
            model=inner.model,
            temperature=inner.temperature,
            provider=inner.provider,
            stop=inner.stop,
            additional_params=inner.additional_params,
        )
        self._gatekeeper = gatekeeper
        self._inner = inner

    def call(self, *args: object, **kwargs: object) -> object:
        """Execute CrewAI's synchronous LLM call through the gatekeeper."""
        return self._gatekeeper.execute(self._inner.call, *args, **kwargs)

    async def acall(self, *args: object, **kwargs: object) -> object:
        """Execute CrewAI's async LLM call path through the same gatekeeper."""
        return await asyncio.to_thread(self._gatekeeper.execute, self._inner.call, *args, **kwargs)

    def supports_function_calling(self) -> bool:
        """Delegate function-calling capability checks to the provider LLM."""
        return self._inner.supports_function_calling()

    def supports_stop_words(self) -> bool:
        """Delegate stop-word capability checks to the provider LLM."""
        return self._inner.supports_stop_words()

    def get_context_window_size(self) -> int:
        """Delegate context-window lookup to the provider LLM."""
        return self._inner.get_context_window_size()

    def supports_multimodal(self) -> bool:
        """Delegate multimodal capability checks to the provider LLM."""
        return self._inner.supports_multimodal()

    def format_text_content(self, text: str) -> dict[str, object]:
        """Delegate content formatting to the provider LLM."""
        return self._inner.format_text_content(text)

    def to_config_dict(self) -> dict[str, object]:
        """Delegate config serialization to the provider LLM."""
        return self._inner.to_config_dict()


class CrewService:
    """Builds and runs the Researcher -> Writer -> Reviewer -> LaTeX crew."""

    def __init__(self, config: ConfigManager, gatekeeper: ApiGatekeeper) -> None:
        """Store the configuration and the gatekeeper used for every crew run."""
        self._config = config
        self._gatekeeper = gatekeeper

    def _build_llm(self) -> BaseLLM:
        """Construct the shared LLM from configuration (model + temperature)."""
        return GatekeptLLM(
            gatekeeper=self._gatekeeper,
            inner=LLM(
                model=self._config.model(),
                temperature=self._config.temperature(),
                max_tokens=self._config.max_tokens(),
            ),
        )

    def _run_chapter(self, llm: BaseLLM, topic: str, heading: str) -> tuple[object, object]:
        """Run the full Researcher->Writer->Reviewer->LaTeX crew for ONE chapter.

        Running per chapter (rather than all chapters in a single response) gives
        each chapter the model's full output budget, so chapters come out full
        length instead of being rationed into a single capped response.

        Returns ``(crew_output, usage_metrics)``. Token counts live on
        ``crew.usage_metrics`` after ``kickoff`` — the ``CrewOutput`` object has no
        ``token_usage`` attribute, so reading it from there always reported zero.
        """
        agents = build_agents(llm)
        crew = Crew(
            agents=list(agents.values()),
            tasks=build_chapter_tasks(agents, heading),
            process=Process.sequential,
            verbose=True,
        )
        result = crew.kickoff(inputs={"topic": topic})
        return result, crew.usage_metrics

    def generate_content(self, topic: str | None = None) -> BookContent:
        """Author every chapter (one crew run each) and assemble :class:`BookContent`.

        Args:
            topic: Optional topic override; defaults to the configured title.

        Raises:
            CrewExecutionError: If a chapter crew fails or returns unstructured output.
        """
        book = self._config.book()
        topic = topic or book["title_en"]
        llm = self._build_llm()
        chapters: list[Chapter] = []
        sources: dict[str, Source] = {}
        prompt_tokens = completion_tokens = 0

        for spec in self._config.chapter_specs():
            try:
                result, usage_metrics = self._run_chapter(llm, topic, spec.heading_he)
            except Exception as exc:
                raise CrewExecutionError(f"chapter '{spec.id}' failed: {exc}") from exc
            chapter = self._first_chapter(result, spec.id, spec.heading_he, spec.language)
            chapters.append(chapter)
            for src in getattr(getattr(result, "pydantic", None), "sources", []) or []:
                sources[src.key] = src
            usage = self._extract_usage(usage_metrics)
            prompt_tokens += usage.prompt_tokens
            completion_tokens += usage.completion_tokens

        return BookContent(
            title=book["title_he"],
            chapters=chapters,
            sources=list(sources.values()),
            token_usage=TokenUsage(
                prompt_tokens=prompt_tokens, completion_tokens=completion_tokens
            ),
        )

    @staticmethod
    def _first_chapter(result: object, id_: str, heading: str, language: Language) -> Chapter:
        """Pull the single authored chapter from a crew result and normalise it."""
        content = getattr(result, "pydantic", None)
        if not isinstance(content, BookContent) or not content.chapters:
            raise CrewExecutionError("crew did not return a structured chapter")
        chapter = content.chapters[0]
        chapter.id = id_
        chapter.heading = heading
        chapter.language = language
        return chapter

    @staticmethod
    def _extract_usage(usage: object) -> TokenUsage:
        """Normalise a CrewAI ``UsageMetrics`` object into our :class:`TokenUsage`."""
        if usage is None:
            return TokenUsage()
        return TokenUsage(
            prompt_tokens=int(getattr(usage, "prompt_tokens", 0) or 0),
            completion_tokens=int(getattr(usage, "completion_tokens", 0) or 0),
        )
