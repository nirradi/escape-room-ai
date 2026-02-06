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


def _build_chain(messages):
    """Build and return the LangChain narrator chain."""
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

    prompt_tpl = ChatPromptTemplate.from_messages(messages)

    llm = ChatOllama(model=model) if model else ChatOllama()
    chain = prompt_tpl | llm | StrOutputParser()

    return chain


def _dialogue_to_messages(dialogue):
    messages = []
    for turn in dialogue:
        if not isinstance(turn, dict):
            continue
        role = turn.get("role")
        content = turn.get("content")
        if not isinstance(content, str):
            continue
        if role == "player":
            messages.append(("user", content))
        elif role == "narrator":
            messages.append(("assistant", content))
    return messages


def _classification_to_system_note(classification: str) -> str | None:
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

        messages = [
            ("system", GENERAL_NARRATOR_RULES),
        ]
        if general_context:
            messages.append(("system", "Level context:\n" + general_context))
        if narration_prompt:
            messages.append(("system", "Narration guidelines:\n" + narration_prompt))
        classification_note = _classification_to_system_note(last_classification)
        if classification_note:
            messages.append(("system", classification_note))
        messages.extend([
            ("system", "Game state:\n" + urgency),
        ])
        messages.extend(_dialogue_to_messages(dialogue))

        chain = _build_chain(messages)
        raw = chain.invoke({})
        
        if raw is None:
            raise RuntimeError("Narrator LLM returned no output")
        text = raw.strip()
        return Narration(text=text)
    except Exception as exc:
        LOG.error("Narrator LLM failed: %s", exc)
        # Fallback: minimal error message
        return Narration(text="[narration unavailable]")
