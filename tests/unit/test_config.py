"""Unit tests for the configuration manager."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from startup_book.shared.config import ConfigManager
from startup_book.shared.errors import ConfigError


def test_loads_and_exposes_values(config_dir: Path) -> None:
    cm = ConfigManager(config_dir)
    assert cm.model() == "gpt-4o-mini"
    assert cm.temperature() == pytest.approx(0.3)
    assert cm.cost_rates() == (0.15, 0.60)
    assert cm.rate_limit().requests_per_minute == 30
    assert cm.build_settings()["engine"] == "lualatex"
    assert cm.book()["author"] == "tester"
    specs = cm.chapter_specs()
    assert [s.id for s in specs] == ["intro", "lean"]


def test_env_overrides_model(config_dir: Path, monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_MODEL", "gpt-x")
    assert ConfigManager(config_dir).model() == "gpt-x"


def test_api_key_from_env(config_dir: Path, monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    assert ConfigManager(config_dir).openai_api_key() == "sk-test"


def test_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(ConfigError):
        ConfigManager(tmp_path)


def test_invalid_json_raises(tmp_path: Path) -> None:
    (tmp_path / "setup.json").write_text("{not json", encoding="utf-8")
    (tmp_path / "rate_limits.json").write_text("{}", encoding="utf-8")
    with pytest.raises(ConfigError):
        ConfigManager(tmp_path)


def test_incompatible_version_raises(config_dir: Path) -> None:
    bad = {"version": "2.00", "book": {}, "llm": {}}
    (config_dir / "setup.json").write_text(json.dumps(bad), encoding="utf-8")
    with pytest.raises(ConfigError):
        ConfigManager(config_dir)
