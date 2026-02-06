"""State model and helpers."""
import json
from dataclasses import dataclass, field, asdict
from typing import Optional, Union
from copy import deepcopy

from dataclasses_jsonschema import JsonSchemaMixin


@dataclass
class StrictState(JsonSchemaMixin):
    """
    Closed-schema state used for win conditions and validation.
    
    No dynamic keys allowed. Structure is fixed and enforced.
    """
    gameCounter: int = 0
    maxGameCounter: int = 10
    level: int = 1
    currentLevelAttempsts: int = 0
    solutionConfidenceScore: float = 0.0


@dataclass
class VibeState:
    """
    Free-form, realism-only state.
    
    Not used for win conditions or validation.
    Can be extended with narrative details.
    """
    name: Optional[str] = None


@dataclass
class GameState:
    """Top-level game state with strict and vibe components."""
    strict: StrictState
    vibe: VibeState


def create_initial_state() -> GameState:
    """
    Create an initial game state with default values.
    
    Returns:
        GameState: Fresh game state ready for play.
    """
    return GameState(
        strict=StrictState(
            gameCounter=0,
            level=1,
            currentLevelAttempsts=0,
        ),
        vibe=VibeState(
            
        )
    )



def state_to_json(state: GameState) -> str:
    """
    Serialize game state to JSON string.
    
    Args:
        state: GameState to serialize.
        
    Returns:
        str: JSON representation of the state.
    """
    return json.dumps(asdict(state), indent=2)


def state_from_json(json_str: str) -> GameState:
    """
    Deserialize game state from JSON string.
    
    Args:
        json_str: JSON string containing serialized state.
        
    Returns:
        GameState: Reconstructed state object.
        
    Raises:
        json.JSONDecodeError: If JSON is invalid.
        KeyError: If required fields are missing.
        TypeError: If field types don't match.
    """
    data = json.loads(json_str)
    
    strict = StrictState(
        gameCounter=data["strict"]["gameCounter"],
        level=data["strict"]["level"],
        currentLevelAttempsts=data["strict"]["currentLevelAttempsts"]
    )
    
    vibe = VibeState(
        name=data["vibe"].get("name")
    )
    
    return GameState(strict=strict, vibe=vibe)


def strict_state_schema() -> dict:
    """
    Return a JSON schema for StrictState.
    Useful for LLM prompt context and validation.
    """
    return StrictState.json_schema()