"""Main game loop skeleton.

Orchestrates: terminal input -> intent -> patch generator (stub or LLM) -> apply_patch -> render

The patch generator can be configured at runtime via evaluator_type ("stub" or "llm").
"""
from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Generator, Optional

from engine import state as state_mod
from engine.patch import PatchResult, apply_patch, classification_to_patch
from game import level as level_mod

@dataclass(frozen=True)
class OutputEvent:
	"""Output payload emitted by the game loop."""
	text: str
	phase: str
	state: Optional[state_mod.GameState]
	level: Optional[level_mod.Level]


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
	state: Optional[state_mod.GameState] = None,
) -> Generator[OutputEvent, Optional[str], str]:
	"""Run a single level as a step-wise generator.

	The generator yields output events and expects user input via ``send``.
	It returns the final outcome: ``"win"``, ``"loss"``, ``"error"``,
	or ``"aborted"``.
	"""
	state = state or state_mod.create_initial_state()

	initial_narration = narrator("", state, level, phase="initial")
	yield OutputEvent(
		text=initial_narration.text,
		phase="initial",
		state=state,
		level=level,
	)

	initial_dialogue = [{"role": "narrator", "content": initial_narration.text}]
	state = apply_patch(state, {"vibe": {"dialogue": initial_dialogue}}).state

	while True:
		user_input = yield OutputEvent(
			text="",
			phase="prompt",
			state=state,
			level=level,
		)
		if user_input is None:
			return "aborted"

		try:
			classification = evaluator(user_input, state, level)
		except Exception as exc:
			LOG.error("Evaluator failed, aborting level: %s", exc)
			yield OutputEvent(
				text="FATAL ERROR: Evaluator failed. Level aborted.",
				phase="error",
				state=state,
				level=level,
			)
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
			yield OutputEvent(
				text=end_narration.text,
				phase="win_end",
				state=state,
				level=level,
			)
			return "win"
		if level_result == LevelResult.TIMEOUT_FAIL:
			end_narration = narrator(user_input, state, level, phase="lose_end")
			yield OutputEvent(
				text=end_narration.text,
				phase="lose_end",
				state=state,
				level=level,
			)
			return "loss"

		narration = narrator(user_input, state, level, phase="turn")
		yield OutputEvent(
			text=narration.text,
			phase="turn",
			state=state,
			level=level,
		)

		base_dialogue = state.vibe.dialogue or []
		user_turn = {"role": "player", "content": user_input}
		narrator_turn = {"role": "narrator", "content": narration.text}
		updated_dialogue = base_dialogue + [user_turn, narrator_turn]
		dialogue_patch = {
			"vibe": {"dialogue": updated_dialogue, "urgency": state.vibe.urgency},
		}
		state = apply_patch(state, dialogue_patch).state


