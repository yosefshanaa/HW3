"""Single source of truth for the project version and version-compatibility.

Why: the submission guidelines (§8.1) require explicit, centralised version
tracking for both code and configuration, starting at ``1.00``. The application
validates, at startup, that the configuration files it loads were written for a
compatible code version so that a stale config fails loudly instead of silently
misbehaving.
"""

from __future__ import annotations

# Code version. Bump the minor part on meaningful changes (guidelines §8.1).
__version__ = "1.50"


def _major(version: str) -> str:
    """Return the major component of a ``"MAJOR.MINOR"`` version string.

    Args:
        version: A version string such as ``"1.00"``.

    Returns:
        The text before the first dot (``"1"`` for ``"1.00"``); the whole string
        if there is no dot.
    """
    return version.split(".", 1)[0]


def is_config_compatible(config_version: str) -> bool:
    """Check whether a configuration version is compatible with this code.

    Compatibility is defined by a shared major version: ``"1.xx"`` configs work
    with ``"1.xx"`` code. This keeps the rule simple and predictable while still
    catching genuinely breaking config changes.

    Args:
        config_version: The ``"version"`` value read from a config file.

    Returns:
        ``True`` when the major versions match, otherwise ``False``.
    """
    return _major(config_version) == _major(__version__)
