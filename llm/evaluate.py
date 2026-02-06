"""Player understanding evaluator LLM.

Classifies player input to determine understanding level based on game context.
Uses LangChain to structure prompts and invoke LLM classification.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict
import logging

from engine.state import GameState
from game.level import Level
from .tools import load_model_config, load_prompt
from langchain_ollama import ChatOllama  # type: ignore
from langchain_core.messages import SystemMessage, HumanMessage


LOG = logging.getLogger(__name__)


class UnderstandingLevel(str, Enum):
    """Valid classification levels for player understanding."""
    CLEAR_UNDERSTANDING = "CLEAR_UNDERSTANDING"
    PARTIAL_UNDERSTANDING = "PARTIAL_UNDERSTANDING"
    NO_SIGNAL = "NO_SIGNAL"
    MISUNDERSTANDING = "MISUNDERSTANDING"
    INVALID = "INVALID"  # Internal only: not shown to LLM, used when output format is invalid


MODEL_CFG: Dict[str, Any] = load_model_config(key="evaluator")
SYSTEM_RULES: str = load_prompt("evaluate")

# Generate evaluation prompt from enum values (exclude INVALID - internal only)
_VALID_TOKENS = "\n".join(level.value for level in UnderstandingLevel if level != UnderstandingLevel.INVALID)
DEFAULT_EVALUATION_PROMPT: str = f"""Evaluate the player's current understanding.
Output must be exactly one of the following tokens and nothing else:

{_VALID_TOKENS}

Any additional text is invalid."""


@dataclass
class Classification:
    """Represents a player understanding classification."""
    level: str  # One of UnderstandingLevel enum values


def _get_llm() -> ChatOllama:
    """Create and return a ChatOllama instance configured for evaluation."""
    model = None
    temperature = 0.0  # Default to 0 for deterministic classification
    
    if isinstance(MODEL_CFG, dict):
        model = MODEL_CFG.get("model") or MODEL_CFG.get("name")
        temperature = MODEL_CFG.get("temperature", 0.0)
    
    return ChatOllama(model=model, temperature=temperature) if model else ChatOllama(temperature=0.0)


def _collapse_player_inputs(dialogue, current_input: str) -> str:
    """Collapse all player inputs into a single numbered evidence list.
    
    Args:
        dialogue: List of dialogue turns with role and content.
        current_input: The current player input to append to the history.
        
    Returns:
        A formatted string with numbered player inputs in chronological order.
    """
    player_inputs = []
    
    # Extract all player inputs from dialogue history
    if dialogue:
        for turn in dialogue:
            if not isinstance(turn, dict):
                continue
            role = turn.get("role")
            content = turn.get("content")
            if role == "player" and isinstance(content, str) and content.strip():
                player_inputs.append(content.strip())
    
    # Add current input
    if current_input.strip():
        player_inputs.append(current_input.strip())
    
    # Format as numbered evidence list
    if not player_inputs:
        return "PLAYER INPUT HISTORY (evidence):\n(no player inputs yet)"
    
    lines = ["PLAYER INPUT HISTORY (evidence):"]
    for i, player_input in enumerate(player_inputs, start=1):
        lines.append(f"{i}. {player_input}")
    
    return "\n".join(lines)


def evaluate(user_input: str, state: GameState, level: Level) -> Classification:
    """Evaluate player understanding from player input.
    
    Args:
        user_input: The player's input.
        state: The current game state.
        level: The current level definition.
        
    Returns:
        Classification: A classification object with level attribute.
        
    Raises:
        Exception: Re-raises any exception to abort the game on evaluator failure.
    """
    try:
        dialogue = state.vibe.dialogue or []
        key_requirement = level.key_player_requirement or ""
        
        # Build system messages:
        # 1. Evaluator rules system message
        lc_messages = [SystemMessage(content=SYSTEM_RULES)]
        
        # 2. Key requirement system message
        if key_requirement:
            key_req_message = f"Key player requirement (what they must understand):\n{key_requirement}"
            lc_messages.append(SystemMessage(content=key_req_message))
        
        # 3. Collapsed player input history as single HumanMessage
        collapsed_history = _collapse_player_inputs(dialogue, user_input)
        lc_messages.append(HumanMessage(content=collapsed_history))

        # Invoke LLM
        llm = _get_llm()
        LOG.debug(f"Invoking evaluator LLM with {len(lc_messages)} messages")
        LOG.debug(f"Collapsed player history:\n{collapsed_history}")
        
        result = llm.invoke(lc_messages)
        raw = result.content if hasattr(result, 'content') else str(result)
        LOG.debug(f"Evaluator LLM returned: {repr(raw)}")
        
        if raw is None:
            raise RuntimeError("Evaluator LLM returned no output")
        
        # Clean and validate output
        raw_str = raw.strip().upper()
        # Exclude INVALID from valid LLM outputs (it's internal only)
        valid_levels = {level.value for level in UnderstandingLevel if level != UnderstandingLevel.INVALID}
        
        # Try exact match first
        if raw_str in valid_levels:
            return Classification(level=raw_str)
        
        # If not an exact match, search for any valid keyword in the response
        for keyword in valid_levels:
            if keyword in raw_str:
                LOG.debug(f"Found '{keyword}' within response, using it")
                return Classification(level=keyword)
        
        # If no valid keyword found, return INVALID (LLM format error)
        LOG.warning("No valid classification found in '%s', returning INVALID", raw_str[:100])
        return Classification(level=UnderstandingLevel.INVALID.value)
    except Exception as exc:
        LOG.error("Evaluator LLM failed: %s", exc)
        # Re-raise to abort game on evaluator failure
        raise
