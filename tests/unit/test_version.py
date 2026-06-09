"""Unit tests for version-compatibility logic."""

from __future__ import annotations

from startup_book.shared import version


def test_version_is_current() -> None:
    assert version.__version__ == "1.50"


def test_same_major_is_compatible() -> None:
    assert version.is_config_compatible("1.00") is True
    assert version.is_config_compatible("1.99") is True


def test_different_major_is_incompatible() -> None:
    assert version.is_config_compatible("2.00") is False
    assert version.is_config_compatible("0.9") is False


def test_major_without_dot() -> None:
    assert version._major("1") == "1"
