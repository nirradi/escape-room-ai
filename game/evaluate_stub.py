"""Stub (non-LLM) evaluator for the game loop.

This is a deterministic, hard-coded evaluator for testing and
quick iteration without requiring an LLM.
"""

from __future__ import annotations

from dataclasses import dataclass

from engine.state import GameState
from game.level import Level


@dataclass
class Classification:
	"""Represents a player understanding classification."""
	level: str  # COMMITTING_TO_CORRECT_MODEL, SOME_UNDERSTANDING, NEUTRAL_ACTION, COMMITTING_TO_INCORRECT_MODEL


def evaluate(user_input: str, state: GameState, level: Level) -> Classification:
	"""Evaluate player understanding based on input.
	
	Args:
		user_input: The player's input.
		state: The current game state.
		level: The current level definition.
		
	Returns:
		Classification: A classification object with level attribute.
	"""
	if user_input == "increase confidence":
		return Classification(level="COMMITTING_TO_CORRECT_MODEL")
	elif user_input == "decrease confidence":
		return Classification(level="COMMITTING_TO_INCORRECT_MODEL")
	else:
		return Classification(level="NEUTRAL_ACTION")
