"""A CrewAI LLM that routes every model call through the API gatekeeper.

Why: the gatekeeper (guidelines §5) is the single choke point for outward
calls. Wrapping CrewAI's :class:`LLM` here means every agent step — sync or
async — is rate-limited, retried and logged, with the gatekeeper kept out of
the serialized pydantic model data via private attributes.
"""

from __future__ import annotations

import asyncio

from crewai import LLM
from crewai.llms.base_llm import BaseLLM
from pydantic import PrivateAttr

from startup_book.shared.gatekeeper import ApiGatekeeper


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

    def get_token_usage_summary(self) -> object:
        """Report the *inner* LLM's accumulated token usage.

        CrewAI reads usage via ``agent.llm.get_token_usage_summary()``. Only the
        inner LLM actually executes litellm calls and records tokens, so the
        wrapper must surface the inner's totals — otherwise usage reads as zero.
        """
        return self._inner.get_token_usage_summary()
