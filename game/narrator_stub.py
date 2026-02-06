"""Stub (non-LLM) narrator for the game loop.

This is a deterministic, hard-coded narrator for testing and
quick iteration without requiring an LLM.
"""

from __future__ import annotations

from dataclasses import dataclass
from engine.state import GameState
from game.level import Level


@dataclass
class Narration:
    """Represents a narration output."""
    text: str


def narrate(user_input: str, state: GameState, level: Level) -> Narration:
    """Generate stub narration for the current game state.
    
    Echoes the urgency level for testing purposes.
    
    Args:
        user_input: The user's input.
        state: The current game state.
        level: The current level definition.
        
    Returns:
        Narration: A narration object with text attribute.
    """
    urgency = state.vibe.urgency
    return Narration(text=f"[urgency={urgency}]")
	
