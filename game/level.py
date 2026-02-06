"""Level loading and data model."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

import yaml


@dataclass(frozen=True)
class Level:
    """Represents a loaded game level."""
    level_id: int
    title: str
    narration_prompt: Optional[str] = None
    mutation_prompt: Optional[str] = None
    max_turns: Optional[int] = None
    raw: Dict[str, Any] = field(default_factory=dict)


def load_level(level_path: Path) -> Level:
    """Load a level definition from YAML.

    Args:
        level_path: Path to the level YAML file.

    Returns:
        Parsed Level instance.
    """
    try:
        data = yaml.safe_load(level_path.read_text()) or {}
    except Exception as exc:
        raise RuntimeError(f"Failed to load level {level_path}: {exc}") from exc

    if not isinstance(data, dict):
        raise RuntimeError(f"Level file must contain a mapping: {level_path}")

    return Level(
        level_id=int(data.get("level_id") or 0),
        title=str(data.get("title") or ""),
        narration_prompt=_safe_str(data.get("narration_prompt")),
        mutation_prompt=_safe_str(data.get("mutation_prompt")),
        max_turns=_safe_int(data.get("max_turns")),
        raw=data,
    )


def _safe_str(value: Any) -> Optional[str]:
    if isinstance(value, str):
        return value.strip() or None
    return None


def _safe_int(value: Any) -> Optional[int]:
    try:
        if value is None:
            return None
        return int(value)
    except Exception:
        return None
