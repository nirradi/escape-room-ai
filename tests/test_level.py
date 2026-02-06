"""Tests for level loading."""

from pathlib import Path

import pytest

from game.level import Level, load_level


def test_load_level_parses_fields(tmp_path: Path) -> None:
    level_path = tmp_path / "level.yaml"
    level_path.write_text(
        """
level_id: 2
title: "Test Level"
context: |
  General context.
narration_prompt: |
  Line one.
  Line two.
key_player_requirement: |
  Understand the concept.
max_turns: 7
""".lstrip()
    )

    level = load_level(level_path)

    assert isinstance(level, Level)
    assert level.level_id == 2
    assert level.title == "Test Level"
    assert level.context == "General context."
    assert level.narration_prompt == "Line one.\nLine two."
    assert level.key_player_requirement == "Understand the concept."
    assert level.max_turns == 7
    assert level.raw.get("level_id") == 2


def test_load_level_rejects_non_mapping(tmp_path: Path) -> None:
    level_path = tmp_path / "level.yaml"
    level_path.write_text("- not a mapping\n")

    with pytest.raises(RuntimeError):
        load_level(level_path)
