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
    level: str  # CLEAR_UNDERSTANDING, PARTIAL_UNDERSTANDING, NO_SIGNAL, MISUNDERSTANDING


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
		return Classification(level="CLEAR_UNDERSTANDING")
	elif user_input == "decrease confidence":
		return Classification(level="MISUNDERSTANDING")
	else:
		return Classification(level="NO_SIGNAL")
