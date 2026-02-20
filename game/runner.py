"""Top-level game runner that orchestrates multiple levels.

Rules:
- clean state per level attempt
- loss retries the same level
- win advances to next level
- end of level list prints "Game Over"
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from dataclasses import asdict
from typing import Any, Callable, Generator, Iterable, Optional

import yaml

from engine import state as state_mod
from game import level as level_mod
import os

from game.loop import OutputEvent, get_evaluator, get_narrator, run_level


InputFn = Callable[[str], str]
OutputFn = Callable[[OutputEvent], None]
DEFAULT_CONFIG_PATH = Path("config") / "game.yaml"

# ANSI color codes for narrator output
COLOR_NARRATOR = "\033[36m"  # Cyan
COLOR_WIN = "\033[32m"       # Green
COLOR_LOSE = "\033[31m"      # Red
COLOR_DEBUG = "\033[33m"     # Yellow
COLOR_RESET = "\033[0m"      # Reset to default


def _default_input(prompt: str) -> str:
    return input(prompt)


def colorize_text(text: str, color: str = COLOR_NARRATOR) -> str:
    """Return text wrapped in ANSI color codes."""
    return f"{color}{text}{COLOR_RESET}"


def print_to_player(text: str, color: str = COLOR_NARRATOR) -> None:
    """Print colored text for player-facing narrator output.

    Args:
        text: The text to print.
        color: ANSI color to apply when text is not already colorized.
    """
    if text.startswith("\033["):
        print(text)
        return
    print(colorize_text(text, color=color))


def default_output(event: OutputEvent) -> None:
    """Default output formatter for terminal output."""
    color = COLOR_NARRATOR
    if event.phase == "win_end":
        color = COLOR_WIN
    elif event.phase == "lose_end":
        color = COLOR_LOSE
    elif event.phase == "debug":
        color = COLOR_DEBUG
    print_to_player(event.text, color=color)


def _default_output(event: OutputEvent) -> None:
    default_output(event)


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
        output_fn(OutputEvent(text="Game Over", phase="game_over", state=None, level=None))
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
            state=state,
        )
        level_result: Optional[str] = drive_level(
            level_runner=level_runner,
            input_fn=input_fn,
            output_fn=output_fn,
        )

        if level_result == "win":
            level_index += 1
            continue

        if level_result == "loss":
            continue

        return

    output_fn(OutputEvent(text="Game Over", phase="game_over", state=None, level=None))


def drive_level(
    level_runner: Generator[OutputEvent, Optional[str], str],
    input_fn: Callable[[str], str],
    output_fn: Callable[[OutputEvent], None],
) -> str:
    """Run a level generator using the provided input/output functions."""
    try:
        event = next(level_runner)
    except StopIteration as stop:
        return stop.value

    while True:
        if event.phase == "prompt":
            try:
                user_input = input_fn("> ")
            except (EOFError, KeyboardInterrupt):
                user_input = None
            if user_input == "quitquitquit":
                return "aborted"
            if user_input == "debugdebug":
                if event.state is None:
                    debug_text = "<no state>"
                else:
                    debug_data = asdict(event.state)
                    if isinstance(debug_data.get("vibe"), dict):
                        debug_data["vibe"].pop("dialogue", None)
                    debug_text = json.dumps(debug_data, indent=2, sort_keys=True)
                output_fn(OutputEvent(text=debug_text, phase="debug", state=event.state, level=event.level))
                continue
            try:
                event = level_runner.send(user_input)
            except StopIteration as stop:
                return stop.value
            continue

        output_fn(event)
        try:
            event = next(level_runner)
        except StopIteration as stop:
            return stop.value


def main(
    evaluator_type: str = "llm",
    narrator_type: str = "llm",
    level_name: str = "bobs-plan.yaml",
) -> None:
    """Run one level with terminal I/O (compatibility adapter)."""
    evaluator = get_evaluator(evaluator_type)
    narrator = get_narrator(narrator_type)
    level = level_mod.load_level(Path("levels") / level_name)
    level_runner = run_level(level=level, evaluator=evaluator, narrator=narrator)
    result = drive_level(level_runner=level_runner, input_fn=input, output_fn=default_output)
    if result == "error":
        raise SystemExit(1)


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


def _parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Escape room game loop")
    parser.add_argument(
        "--evaluator-type",
        default=os.getenv("EVALUATOR_TYPE", "llm"),
        choices=["stub", "llm"],
        help="Evaluator type",
    )
    parser.add_argument(
        "--narrator-type",
        default=os.getenv("NARRATOR_TYPE", "llm"),
        choices=["stub", "llm"],
        help="Narrator type",
    )
    parser.add_argument(
        "--level",
        default=os.getenv("LEVEL_NAME", "bobs-plan.yaml"),
        help="Name of the level file to load (default: bobs-plan.yaml)",
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    args = _parse_args()
    main(evaluator_type=args.evaluator_type, narrator_type=args.narrator_type, level_name=args.level)
