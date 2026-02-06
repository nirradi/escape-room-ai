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
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage


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
    if isinstance(MODEL_CFG, dict):
        model = MODEL_CFG.get("model") or MODEL_CFG.get("name")
    return ChatOllama(model=model) if model else ChatOllama()


def _dialogue_to_messages(dialogue):
    """Convert dialogue history to LangChain message objects."""
    messages = []
    for turn in dialogue:
        if not isinstance(turn, dict):
            continue
        role = turn.get("role")
        content = turn.get("content")
        if not isinstance(content, str):
            continue
        if role == "player":
            messages.append(HumanMessage(content=content))
        elif role == "narrator":
            messages.append(AIMessage(content=content))
    return messages


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
        level_context = level.context or ""
        key_requirement = level.key_player_requirement or ""
        
        # Build system message with context
        system_parts = []
        system_parts.append(SYSTEM_RULES)
        
        if level_context:
            system_parts.append("Level context:\n" + level_context)
        
        if key_requirement:
            system_parts.append("Key player requirement (what they must understand):\n" + key_requirement)
        
        valid_tokens_str = " | ".join(level.value for level in UnderstandingLevel)
        system_parts.append(f"⚠ CRITICAL: You MUST respond with ONLY ONE of these four words, nothing else:\n{valid_tokens_str}")
        system_message = "\n\n".join(system_parts)
        
        # Build LLM messages
        lc_messages = [SystemMessage(content=system_message)]
        lc_messages.extend(_dialogue_to_messages(dialogue))
        
        # Add current user input
        if user_input.strip():
            lc_messages.append(HumanMessage(content=user_input))
        else:
            lc_messages.append(HumanMessage(content=DEFAULT_EVALUATION_PROMPT))

        # Invoke LLM
        llm = _get_llm()
        LOG.debug(f"Invoking evaluator LLM with {len(lc_messages)} messages")
        
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
