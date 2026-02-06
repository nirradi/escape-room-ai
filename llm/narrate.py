"""Output generator for Narrator LLM renderer.

Produces terse, in-universe terminal text for player-facing output.
"""

from dataclasses import dataclass
from typing import Dict, Any
import logging

from engine.state import GameState
from game.level import Level
from .tools import load_model_config, load_prompt

# TODO: Prompt tuning per level
# TODO: Injecting story context later


LOG = logging.getLogger(__name__)

MODEL_CFG: Dict[str, Any] = load_model_config(key="narrator")
GENERAL_NARRATOR_RULES: str = load_prompt("narrate")


@dataclass
class Narration:
    """Represents a narration output."""
    text: str


def _build_chain():
    """Build and return the LangChain narrator chain.
    
    Returns:
        A chain that accepts a dict with:
        - system_rules: General narrator rules
        - level_context: Level-specific context
        - game_state: Current game state info
        - past_narration: History of previous narrations
        - latest_input: The current user input
        
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
        ("system", "Game state:\n{game_state}"),
        ("system", "Past narration:\n{past_narration}"),
        ("user", "{latest_input}"),
    ])

    llm = ChatOllama(model=model) if model else ChatOllama()
    chain = prompt_tpl | llm | StrOutputParser()

    return chain


# Build chain once at module initialization
_NARRATOR_CHAIN = _build_chain()


def narrate(user_input: str, state: GameState, level: Level) -> Narration:
    """
    Generate a terse, in-universe terminal response for the player using LLM.
    Output is plain text, no meta commentary, no emojis, no explanations.
    
    Args:
        user_input: The user's input.
        state: The current game state.
        level: The current level definition.
        
    Returns:
        Narration: A narration object with text attribute.
    """
    try:
        # Read urgency from game state (calculated in apply_patch)
        urgency = state.vibe.urgency
        
        # Build structured inputs in deterministic order
        past_narration = "\n".join(state.vibe.narrator_history) if state.vibe.narrator_history else ""
        level_context = level.narration_prompt or ""
        
        # Invoke chain with structured inputs
        raw = _NARRATOR_CHAIN.invoke({
            "system_rules": GENERAL_NARRATOR_RULES,
            "level_context": level_context,
            "game_state": urgency,
            "past_narration": past_narration,
            "latest_input": user_input,
        })
        
        if raw is None:
            raise RuntimeError("Narrator LLM returned no output")
        text = raw.strip()
        return Narration(text=text)
    except Exception as exc:
        LOG.error("Narrator LLM failed: %s", exc)
        # Fallback: minimal error message
        return Narration(text="[narration unavailable]")
