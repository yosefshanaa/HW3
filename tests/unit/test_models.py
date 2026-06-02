"""Unit tests for the pydantic domain models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from startup_book.constants import Language
from startup_book.shared.models import (
    BookContent,
    Chapter,
    RateLimitConfig,
    TokenUsage,
)


def test_token_usage_total() -> None:
    usage = TokenUsage(prompt_tokens=100, completion_tokens=40)
    assert usage.total_tokens == 140


def test_chapter_defaults_to_hebrew() -> None:
    chapter = Chapter(id="x", heading="כותרת")
    assert chapter.language is Language.HEBREW
    assert chapter.body_markdown == ""


def test_book_content_defaults() -> None:
    book = BookContent(title="t")
    assert book.chapters == []
    assert book.sources == []
    assert book.token_usage.total_tokens == 0


def test_rate_limit_rejects_non_positive_rpm() -> None:
    with pytest.raises(ValidationError):
        RateLimitConfig(
            requests_per_minute=0,
            requests_per_hour=10,
            concurrent_max=1,
            retry_after_seconds=1,
            max_retries=1,
            max_queue_depth=1,
        )
