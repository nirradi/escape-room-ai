"""Stub (non-LLM) patch generator for the game loop.

This is a deterministic, hard-coded patch generator for testing and
quick iteration without requiring an LLM.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from engine.state import GameState


def generate_confidence(userInput: str, state: GameState) -> Dict[str, Any]:
	
	if userInput == "increase confidence":
		return {
			"strict": {
				"solutionConfidenceScore": min(
					state.strict.solutionConfidenceScore + 0.1,
					1.0
				)
			}
		}
	# Unknown or unhandled intents produce no patch
	return {}