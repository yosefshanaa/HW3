"""startup-book — a CrewAI system that writes and typesets a startup mini-book.

Public API: import :class:`BookBuilderSDK` (the single business entry point per
guidelines §4) and read :data:`__version__`. Nothing else in the package is part
of the supported surface.
"""

from __future__ import annotations

from startup_book.shared.version import __version__

__all__ = ["BookBuilderSDK", "__version__"]


def __getattr__(name: str) -> object:
    """Lazily expose :class:`BookBuilderSDK` without importing heavy deps eagerly.

    Importing the SDK pulls in CrewAI (and its large dependency tree). Doing that
    lazily keeps ``import startup_book`` (e.g. just to read ``__version__``) cheap
    and avoids import errors in environments where only the metadata is needed.
    """
    if name == "BookBuilderSDK":
        from startup_book.sdk.sdk import BookBuilderSDK

        return BookBuilderSDK
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
