"""Output generator for Narrator LLM renderer.

Produces terse, in-universe terminal text for player-facing output.
"""

from dataclasses import dataclass
from typing import Dict, Any
import logging

from engine.state import GameState
from .tools import call_llm, load_model_config, load_prompt

# TODO: Prompt tuning per level
# TODO: Injecting story context later


LOG = logging.getLogger(__name__)

MODEL_CFG: Dict[str, Any] = load_model_config(key="narrator")
PROMPT_TPL: str = load_prompt("narrate")


@dataclass
class Narration:
    """Represents a narration output."""
    text: str


def narrate(user_input: str, state: GameState) -> Narration:
    """
    Generate a terse, in-universe terminal response for the player using LLM.
    Output is plain text, no meta commentary, no emojis, no explanations.
    
    Args:
        user_input: The user's input.
        state: The current game state.
        
    Returns:
        Narration: A narration object with text attribute.
    """
    try:
        raw = call_llm(PROMPT_TPL, MODEL_CFG)
        if raw is None:
            raise RuntimeError("Narrator LLM returned no output")
        text = raw.strip()
        return Narration(text=text)
    except Exception as exc:
        LOG.error("Narrator LLM failed: %s", exc)
        # Fallback: minimal error message
        return Narration(text="[narration unavailable]")
