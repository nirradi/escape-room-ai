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
WIN_END_NARRATOR_RULES: str = load_prompt("narrate_win_end")
LOSE_END_NARRATOR_RULES: str = load_prompt("narrate_lose_end")

PROGRESS_FEEDBACK = {
    "COMMITTING_TO_CORRECT_MODEL": "Provide subtle positive reinforcement - the player is making excellent progress toward solving the puzzle.",
    "SOME_UNDERSTANDING": "Offer gentle encouragement - the player is heading in a promising direction.",
    "NEUTRAL_ACTION": "Maintain neutral tension - the player hasn't found a clear path to the solution yet.",
    "COMMITTING_TO_INCORRECT_MODEL": "Introduce subtle friction - the player's current approach is leading away from the solution.",
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


def _get_progress_feedback(classification: str) -> str | None:
    """Get narrator guidance based on player's puzzle-solving progress."""
    if not isinstance(classification, str):
        return None
    normalized = classification.strip().upper()
    if not normalized:
        return None
    return PROGRESS_FEEDBACK.get(normalized)


def _dialogue_history_text(dialogue) -> str:
    lines = []
    for turn in dialogue:
        if not isinstance(turn, dict):
            continue
        role = turn.get("role")
        content = turn.get("content")
        if not isinstance(content, str) or not content.strip():
            continue
        role_name = "player" if role == "player" else "narrator"
        lines.append(f"{role_name}: {content.strip()}")
    return "\n".join(lines)


def narrate(user_input: str, state: GameState, level: Level, phase: str = "turn") -> Narration:
    """
    Generate a terse, in-universe terminal response for the player using LLM.
    Output is plain text, no meta commentary, no emojis, no explanations.
    
    Supports initial, regular turn, and special endgame narration phases.
    
    Args:
        user_input: The player's input.
        state: The current game state.
        level: The current level definition.
        phase: One of "initial", "turn", "win_end", or "lose_end".
        
    Returns:
        Narration: A narration object with text attribute.
    """
    try:
        urgency = state.vibe.urgency
        general_context = level.context or ""
        narration_prompt = level.narration_prompt or ""
        dialogue = state.vibe.dialogue or []
        last_classification = state.vibe.last_evaluator_classification
        normalized_phase = (phase or "turn").strip().lower()

        if normalized_phase not in {"initial", "turn", "win_end", "lose_end"}:
            normalized_phase = "turn"

        is_initial = normalized_phase == "initial" or (normalized_phase == "turn" and len(dialogue) == 0)
        is_end_phase = normalized_phase in {"win_end", "lose_end"}

        # Build system context
        system_parts = []
        if normalized_phase == "win_end":
            system_parts.append(WIN_END_NARRATOR_RULES)
        elif normalized_phase == "lose_end":
            system_parts.append(LOSE_END_NARRATOR_RULES)
        elif is_initial:
            system_parts.append(INITIAL_NARRATOR_RULES)
        else:
            system_parts.append(GENERAL_NARRATOR_RULES)
        
        if general_context:
            system_parts.append("Level context:\n" + general_context)
        
        if narration_prompt:
            system_parts.append("Narration guidelines:\n" + narration_prompt)
        
        if not is_initial and not is_end_phase:
            progress_guidance = _get_progress_feedback(last_classification)
            if progress_guidance:
                system_parts.append(progress_guidance)

        if is_end_phase:
            confidence = state.strict.solutionConfidenceScore
            game_counter = state.strict.gameCounter
            max_turns = level.max_turns
            outcome = "WIN" if normalized_phase == "win_end" else "LOSS"
            history_text = _dialogue_history_text(dialogue)
            system_parts.append("Outcome: " + outcome)
            system_parts.append(f"Current confidence score: {confidence}")
            system_parts.append(f"Current game counter: {game_counter}")
            if max_turns is not None:
                system_parts.append(f"Level max turns: {max_turns}")
            if last_classification:
                system_parts.append("Last evaluator classification: " + str(last_classification))
            if history_text:
                system_parts.append("Player and narrator history:\n" + history_text)
        
        system_parts.append("Current urgency: " + urgency)
        system_message = "\n\n".join(system_parts)

        # Build LLM messages
        lc_messages = [SystemMessage(content=system_message)]
        lc_messages.extend(_dialogue_to_messages(dialogue))
        
        # Add current user input or initial prompt
        if is_initial:
            lc_messages.append(HumanMessage(content="Begin the narration."))
        elif normalized_phase == "win_end":
            lc_messages.append(HumanMessage(content="Deliver the final win narration now."))
        elif normalized_phase == "lose_end":
            lc_messages.append(HumanMessage(content="Deliver the final lose narration now."))
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
