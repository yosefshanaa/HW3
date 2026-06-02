"""Guard against a pydantic/matplotlib ``warnings.warn`` clash on Python 3.12.

Why: importing CrewAI makes pydantic replace ``warnings.warn`` with a wrapper
that rejects matplotlib's py3.12-only ``skip_file_prefixes`` keyword. A benign
matplotlib warning then raises ``TypeError`` instead of warning. During figure
rendering we temporarily restore the pristine C implementation (``_warnings.warn``,
which accepts that keyword), then put the wrapper back.
"""

from __future__ import annotations

import _warnings
import functools
import warnings
from collections.abc import Callable
from contextlib import contextmanager
from typing import TypeVar

T = TypeVar("T")


@contextmanager
def restored_warn():
    """Temporarily install the stdlib ``warnings.warn`` (yields, then restores)."""
    saved = warnings.warn
    warnings.warn = _warnings.warn
    try:
        yield
    finally:
        warnings.warn = saved


def warns_safely(func: Callable[..., T]) -> Callable[..., T]:
    """Decorator: run ``func`` with the pristine ``warnings.warn`` restored."""

    @functools.wraps(func)
    def wrapper(*args: object, **kwargs: object) -> T:
        with restored_warn():
            return func(*args, **kwargs)

    return wrapper
