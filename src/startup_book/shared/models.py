"""Typed data contracts shared across the SDK and services.

Why: pydantic models give the pipeline validated, self-documenting boundaries
(guidelines §16 "building blocks": explicit input/output/setup data). Every
service consumes and returns one of these instead of loose dicts.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from startup_book.constants import Language


class RateLimitConfig(BaseModel):
    """Rate-limit policy for the API gatekeeper (from ``rate_limits.json``)."""

    requests_per_minute: int = Field(gt=0)
    requests_per_hour: int = Field(gt=0)
    concurrent_max: int = Field(gt=0)
    retry_after_seconds: float = Field(ge=0)
    max_retries: int = Field(ge=0)
    max_queue_depth: int = Field(gt=0)


class QueueStatus(BaseModel):
    """A snapshot of the gatekeeper's queue and counters."""

    queued: int = 0
    served: int = 0
    retried: int = 0


class ChapterSpec(BaseModel):
    """The outline entry for one chapter (from ``setup.json``)."""

    id: str
    heading_he: str
    language: Language = Language.HEBREW


class TokenUsage(BaseModel):
    """Token counts and derived cost for a generation run."""

    prompt_tokens: int = 0
    completion_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        """Total tokens (prompt + completion)."""
        return self.prompt_tokens + self.completion_tokens


class Source(BaseModel):
    """A bibliography entry referenced by the book."""

    key: str  # BibTeX citation key, e.g. "ries2011lean"
    title: str
    author: str = ""
    year: str = ""


class Chapter(BaseModel):
    """One generated chapter: heading + body (Markdown) + language mode."""

    id: str
    heading: str
    body_markdown: str = ""
    language: Language = Language.HEBREW


class BookContent(BaseModel):
    """The full content payload produced by the crew."""

    title: str
    chapters: list[Chapter] = Field(default_factory=list)
    sources: list[Source] = Field(default_factory=list)
    token_usage: TokenUsage = Field(default_factory=TokenUsage)


class BuildResult(BaseModel):
    """The outcome of a full ``build`` run."""

    pdf_path: str
    pages: int = 0
    token_usage: TokenUsage = Field(default_factory=TokenUsage)
    estimated_cost_usd: float = 0.0
