"""Crew service: assemble the CrewAI crew and run it through the gatekeeper.

Why: this is the orchestration seam between the SDK and CrewAI. It builds the
sequential crew, runs ``kickoff`` *through the API gatekeeper* (so the external
operation is rate-limited, retried and logged — guidelines §5), and parses the
structured result into a :class:`BookContent`.
"""

from __future__ import annotations

import logging

from crewai import LLM, Crew, Process

from startup_book.agents.definitions import build_agents
from startup_book.agents.tasks import build_tasks
from startup_book.shared.config import ConfigManager
from startup_book.shared.errors import CrewExecutionError
from startup_book.shared.gatekeeper import ApiGatekeeper
from startup_book.shared.models import BookContent, TokenUsage

logger = logging.getLogger("startup_book.crew")


class CrewService:
    """Builds and runs the Researcher -> Writer -> Reviewer -> LaTeX crew."""

    def __init__(self, config: ConfigManager, gatekeeper: ApiGatekeeper) -> None:
        """Store the configuration and the gatekeeper used for every crew run."""
        self._config = config
        self._gatekeeper = gatekeeper

    def _build_llm(self) -> LLM:
        """Construct the shared LLM from configuration (model + temperature)."""
        return LLM(model=self._config.model(), temperature=self._config.temperature())

    def _build_crew(self) -> Crew:
        """Assemble the sequential crew from the agent and task factories."""
        agents = build_agents(self._build_llm())
        tasks = build_tasks(agents)
        return Crew(
            agents=list(agents.values()),
            tasks=tasks,
            process=Process.sequential,
            verbose=True,
        )

    def _run_crew(self, inputs: dict[str, str]) -> object:
        """Run the crew's ``kickoff`` through the gatekeeper and return its output."""
        crew = self._build_crew()
        return self._gatekeeper.execute(crew.kickoff, inputs=inputs)

    def generate_content(self, topic: str | None = None) -> BookContent:
        """Run the pipeline and return the assembled :class:`BookContent`.

        Args:
            topic: Optional topic override; defaults to the configured title.

        Raises:
            CrewExecutionError: If the crew fails or returns unstructured output.
        """
        book = self._config.book()
        topic = topic or book["title_en"]
        outline = "\n".join(
            f"- {spec.id}: {spec.heading_he}" for spec in self._config.chapter_specs()
        )
        try:
            result = self._run_crew({"topic": topic, "outline": outline})
        except Exception as exc:
            raise CrewExecutionError(f"crew execution failed: {exc}") from exc
        return self._to_book_content(result, book["title_he"])

    def _to_book_content(self, result: object, default_title: str) -> BookContent:
        """Validate the crew output and enrich it with title and token usage."""
        content = getattr(result, "pydantic", None)
        if not isinstance(content, BookContent):
            raise CrewExecutionError("crew did not return a structured BookContent")
        if not content.title:
            content.title = default_title
        content.token_usage = self._extract_usage(result)
        return content

    @staticmethod
    def _extract_usage(result: object) -> TokenUsage:
        """Best-effort extraction of token counts from the crew output."""
        usage = getattr(result, "token_usage", None)
        if usage is None:
            return TokenUsage()
        return TokenUsage(
            prompt_tokens=int(getattr(usage, "prompt_tokens", 0) or 0),
            completion_tokens=int(getattr(usage, "completion_tokens", 0) or 0),
        )
