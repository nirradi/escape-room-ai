

"""Main game loop skeleton.

Orchestrates: terminal input -> intent -> patch generator (stub or LLM) -> apply_patch -> render

The patch generator can be configured at runtime via mutator_type ("stub" or "llm").
"""
from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict
from typing import Optional

from engine import state as state_mod
from engine.patch import apply_patch, PatchResult

from enum import Enum
from game.narrate import Narration


def get_mutator(mutator_type: str = "llm"):
	"""Return the appropriate patch generator function based on type.

	Args:
		mutator_type: "stub" or "llm" (default).

	Returns:
		A callable with signature: generate_patch(intent, state, level_context) -> dict

	Raises:
		ValueError: If mutator_type is unknown.
	"""
	if mutator_type == "stub-win":
		from game.mutate_stub import generate_confidence as stub_gen
		LOG.info("Using stub (non-LLM) mutator")
		return stub_gen
	elif mutator_type == "stub-lose":
		from game.mutate_stub import generate_confidence as stub_gen
		LOG.info("Using stub (non-LLM) mutator")
		return stub_gen
	elif mutator_type == "llm":
		from llm.mutate import generate_confidence as llm_gen
		LOG.info("Using LLM mutator")
		return llm_gen
	else:
		raise ValueError(f"Unknown mutator_type: {mutator_type}")


def get_narrator(narrator_type: str = "llm"):
	"""Return the appropriate narrator function based on type.

	Args:
		narrator_type: "stub" or "llm" (default).

	Returns:
		A callable with signature: narrate(user_input, state) -> Narration

	Raises:
		ValueError: If narrator_type is unknown.
	"""
	if narrator_type == "stub":
		from game.narrator_stub import narrate as stub_narrate
		LOG.info("Using stub (non-LLM) narrator")
		return stub_narrate
	elif narrator_type == "llm":
		from llm.narrate import narrate as llm_narrate
		LOG.info("Using LLM narrator")
		return llm_narrate
	else:
		raise ValueError(f"Unknown narrator_type: {narrator_type}")


LOG = logging.getLogger(__name__)

# Configure root logger from environment so modules like `llm.mutate`
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


def check_level_conditions(state: state_mod.GameState) -> LevelResult:
	"""Check if the current level's win conditions are met.
	
	Args:
		state: Current game state.
	
	Returns:
		LevelResult: WIN, CONTINUE, or TIMEOUT_FAIL.
	"""

	if state.strict.solutionConfidenceScore >= MAX_CONFIDENCE_SCORE:
		return LevelResult.WIN
	

	if state.strict.gameCounter >= state.strict.maxGameCounter:
		return LevelResult.TIMEOUT_FAIL
	
	return LevelResult.CONTINUE


def render_patch_result(result: PatchResult) -> None:
	"""Print patch application results: success, errors, warnings."""
	LOG.debug("Patch apply result:")
	LOG.debug(f"  success: {result.success}")
	if result.strict_errors:
		LOG.debug("  strict errors:")
		for err in result.strict_errors:
			LOG.debug(f"    - {err.field}: {err.reason} (value={err.attempted_value})")
	if result.warnings:
		LOG.debug("  warnings:")
		for w in result.warnings:
			LOG.debug(f"    - {w}")


def render_strict_state(state: state_mod.GameState) -> None:
    """Print the strict state for debugging."""
    try:
        strict_dict = asdict(state.strict)
    except Exception:
        # Fallback: serialize via state_to_json and extract 'strict'
        doc = json.loads(state_mod.state_to_json(state))
        strict_dict = doc.get('strict', {})
    LOG.debug("Current strict state:")
    LOG.debug(json.dumps(strict_dict, indent=2))


def main(mutator_type: str = "llm", narrator_type: str = "llm") -> None:
	"""Run the main game loop.

	Args:
		mutator_type: "stub-win", "stub-lose", or "llm" (default, uses LLM mutator).
		narrator_type: "stub" or "llm" (default, uses LLM narrator).
	"""

	LOG.info("Starting game loop with mutator_type=%s, narrator_type=%s", mutator_type, narrator_type)
	mutator = get_mutator(mutator_type)
	narrator = get_narrator(narrator_type)
	state = state_mod.create_initial_state()

	while True:
		try:
			user_input = input('> ')
		except (EOFError, KeyboardInterrupt):
			LOG.debug('Exiting.')
			break

		# Increment game counter for this turn
		state.strict.gameCounter += 1

		# Use the selected mutator to generate the patch
		patch = mutator(user_input, state)

		result = None
		if patch:
			LOG.debug("Proposed patch:")
			LOG.debug(json.dumps(patch, indent=2))
			result = apply_patch(state, patch)
			render_patch_result(result)
			if result and result.success:
				state = result.state
		level_result = check_level_conditions(state)
		if level_result == LevelResult.WIN:
			print("WIN CONDITION MET — Level complete.")
			break
		if level_result == LevelResult.TIMEOUT_FAIL:
			print("FAILURE: Maximum game counter reached.")
			break

		# Use the selected narrator to generate narration
		narration = narrator(user_input, state)
		print(narration.text)

		render_strict_state(state)


if __name__ == '__main__':
    main()
