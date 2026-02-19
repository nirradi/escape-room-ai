"""Top-level game runner that orchestrates multiple levels.

Rules:
- clean state per level attempt
- loss retries the same level
- win advances to next level
- end of level list prints "Game Over"
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Iterable, Optional

import yaml

from engine import state as state_mod
from game import level as level_mod
from game.loop import get_evaluator, get_narrator, print_to_player, run_level


InputFn = Callable[[str], str]
OutputFn = Callable[[str], None]
DEFAULT_CONFIG_PATH = Path("config") / "game.yaml"


def _default_input(prompt: str) -> str:
    return input(prompt)


def _default_output(text: str) -> None:
    print_to_player(text)


def run_game(
    level_names: Iterable[str],
    evaluator_type: str = "llm",
    narrator_type: str = "llm",
    input_fn: InputFn = _default_input,
    output_fn: OutputFn = _default_output,
) -> None:
    """Run a full game from an ordered list of level names."""
    evaluator = get_evaluator(evaluator_type)
    narrator = get_narrator(narrator_type)

    ordered_levels = list(level_names)
    if not ordered_levels:
        output_fn("Game Over")
        return

    level_index = 0
    while level_index < len(ordered_levels):
        level_name = ordered_levels[level_index]
        level = level_mod.load_level(Path("levels") / level_name)
        state = state_mod.create_initial_state()
        level_runner = run_level(
            level=level,
            evaluator=evaluator,
            narrator=narrator,
            input_fn=input_fn,
            output_fn=output_fn,
            state=state,
        )
        level_result: Optional[str] = None

        while True:
            try:
                next(level_runner)
            except StopIteration as stop:
                level_result = stop.value
                break

        if level_result == "win":
            level_index += 1
            continue

        if level_result == "loss":
            continue

        return

    output_fn("Game Over")


def load_game_config(config_path: Path = DEFAULT_CONFIG_PATH) -> dict[str, Any]:
    """Load game runtime config from YAML."""
    try:
        raw = yaml.safe_load(config_path.read_text()) or {}
    except Exception as exc:
        raise RuntimeError(f"Failed to load game config {config_path}: {exc}") from exc

    if not isinstance(raw, dict):
        raise RuntimeError(f"Game config must contain a mapping: {config_path}")

    levels = raw.get("levels")
    if not isinstance(levels, list) or not levels:
        raise RuntimeError("Game config requires non-empty 'levels' list")

    normalized_levels: list[str] = []
    for level_name in levels:
        if isinstance(level_name, str) and level_name.strip():
            normalized_levels.append(level_name.strip())

    if not normalized_levels:
        raise RuntimeError("Game config 'levels' must contain at least one valid level name")

    evaluator_type = str(raw.get("evaluator_type") or "llm").strip().lower()
    narrator_type = str(raw.get("narrator_type") or "llm").strip().lower()

    return {
        "levels": normalized_levels,
        "evaluator_type": evaluator_type,
        "narrator_type": narrator_type,
    }


def run_game_from_config(
    config_path: Path = DEFAULT_CONFIG_PATH,
    input_fn: InputFn = _default_input,
    output_fn: OutputFn = _default_output,
) -> None:
    """Run game using YAML configuration."""
    config = load_game_config(config_path)
    run_game(
        level_names=config["levels"],
        evaluator_type=config["evaluator_type"],
        narrator_type=config["narrator_type"],
        input_fn=input_fn,
        output_fn=output_fn,
    )
