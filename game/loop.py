"""Main game loop skeleton.

Orchestrates: terminal input -> intent -> patch generator (stub or LLM) -> apply_patch -> render

The patch generator can be configured at runtime via evaluator_type ("stub" or "llm").
"""
from __future__ import annotations

import argparse
import json
import logging
import os
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Generator, Optional

from engine import state as state_mod
from engine.patch import PatchResult, apply_patch, classification_to_patch
from game import level as level_mod

# ANSI color codes for narrator output
COLOR_NARRATOR = "\033[36m"  # Cyan
COLOR_RESET = "\033[0m"      # Reset to default


def print_to_player(text: str) -> None:
	"""Print colored text for player-facing narrator output.

	Args:
		text: The text to print in narrator color (cyan).
	"""
	print(f"{COLOR_NARRATOR}{text}{COLOR_RESET}")


def get_evaluator(evaluator_type: str = "llm"):
	"""Return the appropriate evaluator function based on type.

	Args:
		evaluator_type: "stub" or "llm" (default).

	Returns:
		A callable with signature: evaluate(user_input, state, level) -> Classification

	Raises:
		ValueError: If evaluator_type is unknown.
	"""
	if evaluator_type == "stub":
		from game.evaluate_stub import evaluate

		LOG.info("Using stub (non-LLM) evaluator")
		return evaluate
	if evaluator_type == "llm":
		from llm.evaluate import evaluate

		LOG.info("Using LLM evaluator")
		return evaluate
	raise ValueError(f"Unknown evaluator_type: {evaluator_type}")


def get_narrator(narrator_type: str = "llm"):
	"""Return the appropriate narrator function based on type.

	Args:
		narrator_type: "stub" or "llm" (default).

	Returns:
		A callable with signature: narrate(user_input, state, level) -> Narration

	Raises:
		ValueError: If narrator_type is unknown.
	"""
	if narrator_type == "stub":
		from game.narrator_stub import narrate as stub_narrate

		LOG.info("Using stub (non-LLM) narrator")
		return stub_narrate
	if narrator_type == "llm":
		from llm.narrate import narrate as llm_narrate

		LOG.info("Using LLM narrator")
		return llm_narrate
	raise ValueError(f"Unknown narrator_type: {narrator_type}")


LOG = logging.getLogger(__name__)

# Configure root logger from environment so modules like `llm.evaluate`
# emitting DEBUG logs are visible when `LOGLEVEL=DEBUG` is set.
_loglevel = os.getenv("LOGLEVEL", "INFO").upper()
try:
	_level = getattr(logging, _loglevel, logging.INFO)
except Exception:
	_level = logging.INFO
logging.basicConfig(level=_level, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
# Silence overly noisy httpcore/httpx loggers which clutter output
for _n in ("httpcore.http11", "httpcore.connection", "httpx"):
	logging.getLogger(_n).setLevel(logging.WARNING)


MAX_CONFIDENCE_SCORE = 0.5


class LevelResult(Enum):
	WIN = "win"
	CONTINUE = "continue"
	TIMEOUT_FAIL = "timeout_fail"


def _calculate_urgency(game_counter: int, max_turns: Optional[int]) -> str:
	if max_turns is None or max_turns <= 0:
		return "SOME URGENCY"
	progress = game_counter / max_turns
	if progress < 0.25:
		return "SOME URGENCY"
	if progress < 0.50:
		return "MODERATE URGENCY"
	if progress < 0.75:
		return "VERY URGENT"
	return "DIRE"


def check_level_conditions(state: state_mod.GameState, level: level_mod.Level) -> LevelResult:
	"""Check if the current level's win conditions are met.

	Args:
		state: Current game state.
		level: Current level definition.

	Returns:
		LevelResult: WIN, CONTINUE, or TIMEOUT_FAIL.
	"""
	if state.strict.solutionConfidenceScore >= MAX_CONFIDENCE_SCORE:
		return LevelResult.WIN

	max_turns = level.max_turns or 0
	if max_turns and state.strict.gameCounter >= max_turns:
		return LevelResult.TIMEOUT_FAIL

	return LevelResult.CONTINUE


def render_patch_result(result: PatchResult) -> None:
	"""Print patch application results: success, errors, warnings."""
	LOG.debug("Patch apply result:")
	LOG.debug("  success: %s", result.success)
	if result.strict_errors:
		LOG.debug("  strict errors:")
		for err in result.strict_errors:
			LOG.debug("    - %s: %s (value=%s)", err.field, err.reason, err.attempted_value)
	if result.warnings:
		LOG.debug("  warnings:")
		for warning in result.warnings:
			LOG.debug("    - %s", warning)


def run_level(
	level: level_mod.Level,
	evaluator: Callable[[str, state_mod.GameState, level_mod.Level], Any],
	narrator: Callable[[str, state_mod.GameState, level_mod.Level, str], Any],
	input_fn: Callable[[str], str],
	output_fn: Callable[[str], None],
	state: Optional[state_mod.GameState] = None,
) -> Generator[None, None, str]:
	"""Run a single level as a step-wise generator.

	Input/output are injected via ``input_fn`` and ``output_fn``.
	The generator yields control points and returns the final outcome:
	``"win"``, ``"loss"``, ``"error"``, or ``"aborted"``.
	"""
	state = state or state_mod.create_initial_state()

	initial_narration = narrator("", state, level, phase="initial")
	output_fn(initial_narration.text)

	initial_dialogue = [{"role": "narrator", "content": initial_narration.text}]
	state = apply_patch(state, {"vibe": {"dialogue": initial_dialogue}}).state
	yield None

	while True:
		try:
			user_input = input_fn("> ")
		except (EOFError, KeyboardInterrupt):
			return "aborted"

		try:
			classification = evaluator(user_input, state, level)
		except Exception as exc:
			LOG.error("Evaluator failed, aborting level: %s", exc)
			output_fn("FATAL ERROR: Evaluator failed. Level aborted.")
			return "error"

		new_game_counter = state.strict.gameCounter
		if classification.level != "INVALID":
			new_game_counter += 1

		urgency = _calculate_urgency(new_game_counter, level.max_turns)
		patch = classification_to_patch(classification.level, state.strict.solutionConfidenceScore) or {}
		strict_patch = patch.get("strict") or {}
		strict_patch["gameCounter"] = new_game_counter
		patch["strict"] = strict_patch
		patch["vibe"] = {
			"last_evaluator_classification": classification.level,
			"urgency": urgency,
		}

		if patch:
			LOG.debug("Proposed patch:")
			LOG.debug(json.dumps(patch, indent=2))
		result = apply_patch(state, patch)
		if patch:
			render_patch_result(result)
		state = result.state

		level_result = check_level_conditions(state, level)
		if level_result == LevelResult.WIN:
			end_narration = narrator(user_input, state, level, phase="win_end")
			output_fn(end_narration.text)
			return "win"
		if level_result == LevelResult.TIMEOUT_FAIL:
			end_narration = narrator(user_input, state, level, phase="lose_end")
			output_fn(end_narration.text)
			return "loss"

		narration = narrator(user_input, state, level, phase="turn")
		output_fn(narration.text)

		base_dialogue = state.vibe.dialogue or []
		user_turn = {"role": "player", "content": user_input}
		narrator_turn = {"role": "narrator", "content": narration.text}
		updated_dialogue = base_dialogue + [user_turn, narrator_turn]
		dialogue_patch = {
			"vibe": {"dialogue": updated_dialogue, "urgency": state.vibe.urgency},
		}
		state = apply_patch(state, dialogue_patch).state
		yield None


def main(evaluator_type: str = "llm", narrator_type: str = "llm", level_name: str = "bobs-plan.yaml") -> None:
	"""Run one level with terminal I/O (compatibility adapter)."""
	LOG.info(
		"Starting game loop with evaluator_type=%s, narrator_type=%s, level_name=%s",
		evaluator_type,
		narrator_type,
		level_name,
	)
	evaluator = get_evaluator(evaluator_type)
	narrator = get_narrator(narrator_type)
	level = level_mod.load_level(Path("levels") / level_name)

	level_runner = run_level(
		level=level,
		evaluator=evaluator,
		narrator=narrator,
		input_fn=input,
		output_fn=print_to_player,
	)

	while True:
		try:
			next(level_runner)
		except StopIteration as stop:
			if stop.value == "error":
				raise SystemExit(1)
			break


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
