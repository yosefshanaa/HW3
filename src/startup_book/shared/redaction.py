"""Secret redaction for log records (guidelines §2.4 security, §7.4 logging).

Why: a production agent's logs must never leak credentials. :func:`redact`
masks OpenAI-style API keys (``sk-…``) and the live value of ``OPENAI_API_KEY``
from any text, and :class:`RedactionFilter` applies it to every log record
before a handler can emit it — so a key can never be written to disk or stdout.
"""

from __future__ import annotations

import logging
import os
import re

from startup_book.constants import ENV_OPENAI_API_KEY

# OpenAI keys look like ``sk-...`` / ``sk-proj-...`` (long base62 with hyphens).
_SK_PATTERN = re.compile(r"sk-[A-Za-z0-9_\-]{6,}")
_REDACTED = "***REDACTED***"


def redact(text: str) -> str:
    """Return ``text`` with API keys and the live ``OPENAI_API_KEY`` value masked.

    Two layers: a pattern match for the canonical ``sk-…`` shape, plus a literal
    replacement of whatever the environment currently holds (covers custom keys
    that do not match the pattern).
    """
    masked = _SK_PATTERN.sub(_REDACTED, text)
    secret = os.environ.get(ENV_OPENAI_API_KEY)
    if secret:
        masked = masked.replace(secret, _REDACTED)
    return masked


class RedactionFilter(logging.Filter):
    """A logging filter that scrubs secrets from each record before emission."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Render the record's message, redact it in place, and keep the record."""
        record.msg = redact(record.getMessage())
        record.args = None  # args are already merged into the redacted message
        return True
