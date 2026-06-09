"""Crew service: the orchestration seam between the SDK and CrewAI.

Builds a sequential crew per chapter, runs ``kickoff`` through the API gatekeeper
(rate-limited, retried, logged — §5), and parses the result into a
:class:`BookContent`. Chapters run concurrently (§15); see PLAN.md §8.
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor

from crewai import LLM, Crew, Process
from crewai.llms.base_llm import BaseLLM

from startup_book.agents.definitions import build_agents
from startup_book.agents.tasks import build_chapter_tasks
from startup_book.constants import Language
from startup_book.services.gatekept_llm import GatekeptLLM
from startup_book.shared.config import ConfigManager
from startup_book.shared.errors import CrewExecutionError
from startup_book.shared.gatekeeper import ApiGatekeeper
from startup_book.shared.models import BookContent, Chapter, ChapterSpec, Source, TokenUsage

logger = logging.getLogger("startup_book.crew")


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

    def _run_chapter(self, topic: str, heading: str) -> tuple[object, object]:
        """Run the full Researcher->Writer->Reviewer->LaTeX crew for ONE chapter.

        Running per chapter gives each chapter the model's full output budget. A
        **fresh** LLM is built per chapter so its token counter measures only this
        chapter (read straight from the LLM — ``crew.usage_metrics`` over-counts a
        shared wrapper) and concurrent chapters never share a usage accumulator.
        """
        llm = self._build_llm()
        agents = build_agents(llm)
        crew = Crew(
            agents=list(agents.values()),
            tasks=build_chapter_tasks(agents, heading),
            process=Process.sequential,
            verbose=True,
        )
        result = crew.kickoff(inputs={"topic": topic})
        return result, llm.get_token_usage_summary()

    def generate_content(self, topic: str | None = None) -> BookContent:
        """Author every chapter (one crew run each) and assemble :class:`BookContent`.

        Chapters are generated concurrently (§15) and reassembled in outline
        order; token usage is summed across all runs.

        Args:
            topic: Optional topic override; defaults to the configured title.

        Raises:
            CrewExecutionError: If a chapter crew fails or returns unstructured output.
        """
        book = self._config.book()
        topic = topic or book["title_en"]
        specs = self._config.chapter_specs()
        results = self._run_chapters(topic, specs)

        chapters: list[Chapter] = []
        sources: dict[str, Source] = {}
        prompt_tokens = completion_tokens = 0
        for spec, (result, usage_metrics) in zip(specs, results, strict=True):
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

    def _run_chapters(
        self, topic: str, specs: list[ChapterSpec]
    ) -> list[tuple[object, object]]:
        """Run every chapter crew concurrently and return results in outline order.

        Chapter generation is I/O-bound, so threads fit (§15.1). The pool is
        capped at ``concurrent_max`` so chapter parallelism never exceeds the
        configured budget; the gatekeeper independently throttles each LLM call,
        so no thread holds a gatekeeper slot while idle (no deadlock). Full
        rationale + thread-safety note: PLAN.md §8.
        """
        max_workers = max(1, min(len(specs), self._config.rate_limit().concurrent_max))
        results: list[tuple[object, object]] = [(None, None)] * len(specs)
        with ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="chapter") as pool:
            futures = {
                pool.submit(self._run_chapter, topic, spec.heading_he): i
                for i, spec in enumerate(specs)
            }
            for future, i in futures.items():
                try:
                    results[i] = future.result()
                except Exception as exc:
                    raise CrewExecutionError(f"chapter '{specs[i].id}' failed: {exc}") from exc
        return results

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
