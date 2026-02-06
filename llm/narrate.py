"""Output generator for Narrator LLM renderer.

Produces terse, in-universe terminal text for player-facing output.
"""

from dataclasses import dataclass
from typing import Dict, Any
import logging

from engine.state import GameState
from game.level import Level
from .tools import load_model_config, load_prompt
from langchain_ollama import ChatOllama  # type: ignore
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

# TODO: Prompt tuning per level
# TODO: Injecting story context later


LOG = logging.getLogger(__name__)

# === Initialization (runs once at module load) ===
MODEL_CFG: Dict[str, Any] = load_model_config(key="narrator")
GENERAL_NARRATOR_RULES: str = load_prompt("narrate")
INITIAL_NARRATOR_RULES: str = load_prompt("narrate_initial")

CLASSIFICATION_NOTES = {
    "CLEAR_UNDERSTANDING": "The player is on the right track.",
    "PARTIAL_UNDERSTANDING": "The player is picking up on some of the idea.",
    "NO_SIGNAL": "The player is currently without proper direction.",
    "MISUNDERSTANDING": "The player has missed the idea completely.",
}


@dataclass
class Narration:
    """Represents a narration output."""
    text: str


# === Helpers (runtime utilities) ===

def _get_llm() -> ChatOllama:
    """Create and return a ChatOllama instance configured for narration."""
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


def _classification_to_system_note(classification: str) -> str | None:
    """Get system note for player's progress classification."""
    if not isinstance(classification, str):
        return None
    normalized = classification.strip().upper()
    if not normalized:
        return None
    return CLASSIFICATION_NOTES.get(normalized)


def narrate(user_input: str, state: GameState, level: Level) -> Narration:
    """
    Generate a terse, in-universe terminal response for the player using LLM.
    Output is plain text, no meta commentary, no emojis, no explanations.
    
    For the initial narration (when dialogue is empty), uses a special opening prompt
    to set the scene before any player interaction.
    
    Args:
        user_input: The player's input.
        state: The current game state.
        level: The current level definition.
        
    Returns:
        Narration: A narration object with text attribute.
    """
    try:
        urgency = state.vibe.urgency
        general_context = level.context or ""
        narration_prompt = level.narration_prompt or ""
        dialogue = state.vibe.dialogue or []
        last_classification = state.vibe.last_evaluator_classification
        
        is_initial = len(dialogue) == 0

        # Build system context
        system_parts = []
        system_parts.append(INITIAL_NARRATOR_RULES if is_initial else GENERAL_NARRATOR_RULES)
        
        if general_context:
            system_parts.append("Level context:\n" + general_context)
        
        if narration_prompt:
            system_parts.append("Narration guidelines:\n" + narration_prompt)
        
        if not is_initial:
            classification_note = _classification_to_system_note(last_classification)
            if classification_note:
                system_parts.append(classification_note)
        
        system_parts.append("Current urgency: " + urgency)
        system_message = "\n\n".join(system_parts)

        # Build LLM messages
        lc_messages = [SystemMessage(content=system_message)]
        lc_messages.extend(_dialogue_to_messages(dialogue))
        
        # Add current user input or initial prompt
        if is_initial:
            lc_messages.append(HumanMessage(content="Begin the narration."))
        elif user_input.strip():
            lc_messages.append(HumanMessage(content=user_input))
        else:
            lc_messages.append(HumanMessage(content="Continue narrating."))

        # Invoke LLM
        llm = _get_llm()
        LOG.debug(f"Invoking narrator LLM with {len(lc_messages)} messages")
        
        result = llm.invoke(lc_messages)
        raw = result.content if hasattr(result, 'content') else str(result)
        LOG.debug(f"Narrator LLM returned: {repr(raw)}")
        
        if raw is None or (isinstance(raw, str) and not raw.strip()):
            raise RuntimeError("Narrator LLM returned no output")
        
        return Narration(text=raw.strip())
    except Exception as exc:
        LOG.error("Narrator LLM failed: %s", exc)
        return Narration(text="[narration unavailable]")
