"""Player understanding evaluator LLM.

Classifies player input to determine understanding level based on game context.
Uses LangChain to structure prompts and invoke LLM classification.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict
import logging

from engine.state import GameState
from game.level import Level
from .tools import load_model_config, load_prompt


LOG = logging.getLogger(__name__)

MODEL_CFG: Dict[str, Any] = load_model_config(key="evaluator")
SYSTEM_RULES: str = load_prompt("evaluate")


@dataclass
class Classification:
    """Represents a player understanding classification."""
    level: str  # CLEAR_UNDERSTANDING, PARTIAL_UNDERSTANDING, NO_SIGNAL, MISUNDERSTANDING


def _build_chain():
    """Build and return the LangChain evaluator classification chain.
    
    Returns:
        A chain that accepts a dict with:
        - system_rules: General classification rules
        - level_context: Background and setting information
        - key_requirement: The main question/concept the player should understand
        - dialog: History of dialog exchanges
        - latest_input: The current player input
        - instructions: Output format instructions
        
    Raises:
        RuntimeError: If langchain_ollama/langchain_core are missing.
    """
    try:
        from langchain_ollama import ChatOllama  # type: ignore
        from langchain_core.prompts import ChatPromptTemplate  # type: ignore
        from langchain_core.output_parsers import StrOutputParser  # type: ignore
    except Exception as exc:
        raise RuntimeError("langchain_ollama or langchain_core not available") from exc

    # Extract model name from config
    model = None
    if isinstance(MODEL_CFG, dict):
        model = MODEL_CFG.get("model") or MODEL_CFG.get("name")

    # Build chat template with multiple structured inputs
    prompt_tpl = ChatPromptTemplate.from_messages([
        ("system", "{system_rules}"),
        ("system", "Level context:\n{level_context}"),
        ("system", "Key player requirement (what they must understand):\n{key_requirement}"),
        ("system", "Dialog:\n{dialog}"),
        ("system", "{instructions}"),
        ("player", "{latest_input}"),
    ])

    llm = ChatOllama(model=model) if model else ChatOllama()
    chain = prompt_tpl | llm | StrOutputParser()

    return chain


# Build chain once at module initialization
_EVALUATOR_CHAIN = _build_chain()


def evaluate(user_input: str, state: GameState, level: Level) -> Classification:
    """Evaluate player understanding from player input.
    
    Args:
        user_input: The player's input.
        state: The current game state.
        level: The current level definition.
        
    Returns:
        Classification: A classification object with level attribute.
    """
    try:
        # Build dialog from player history
        dialog = "\n".join(state.player_history) if state.player_history else ""
        level_context = level.context or ""
        key_requirement = level.key_player_requirement or ""
        
        # Invoke chain with structured inputs
        classification = _EVALUATOR_CHAIN.invoke({
            "system_rules": SYSTEM_RULES,
            "level_context": level_context,
            "key_requirement": key_requirement,
            "dialog": dialog,
            "latest_input": user_input,
            "instructions": "Return only one of the following: CLEAR_UNDERSTANDING, PARTIAL_UNDERSTANDING, NO_SIGNAL, MISUNDERSTANDING."
        })
        
        if classification is None:
            raise RuntimeError("Evaluator LLM returned no output")
        
        # Clean and validate output
        result = classification.strip().upper()
        valid_levels = {"CLEAR_UNDERSTANDING", "PARTIAL_UNDERSTANDING", "NO_SIGNAL", "MISUNDERSTANDING"}
        
        if result not in valid_levels:
            LOG.warning("Invalid classification '%s', defaulting to NO_SIGNAL", result)
            result = "NO_SIGNAL"
        
        return Classification(level=result)
    except Exception as exc:
        LOG.error("Evaluator LLM failed: %s", exc)
        # Fallback: assume no signal on error
        return Classification(level="NO_SIGNAL")
