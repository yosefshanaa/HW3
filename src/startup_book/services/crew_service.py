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
from startup_book.agents.tasks import build_tasks
from startup_book.shared.config import ConfigManager
from startup_book.shared.errors import CrewExecutionError
from startup_book.shared.gatekeeper import ApiGatekeeper
from startup_book.shared.models import BookContent, TokenUsage

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
        """Run the crew and return its output; the LLM itself is gatekept."""
        crew = self._build_crew()
        return crew.kickoff(inputs=inputs)

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
