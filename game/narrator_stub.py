"""Stub (non-LLM) narrator for the game loop.

This is a deterministic, hard-coded narrator for testing and
quick iteration without requiring an LLM.
"""

from __future__ import annotations

from dataclasses import dataclass
from engine.state import GameState


@dataclass
class Narration:
    """Represents a narration output."""
    text: str


def narrate(user_input: str, state: GameState) -> Narration:
    """Generate stub narration for the current game state.
    
    Args:
        user_input: The user's input.
        state: The current game state.
        
    Returns:
        Narration: A narration object with text attribute.
    """
    return Narration(text="whats next")
	
