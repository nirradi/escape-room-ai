"""Tests for game state management and narrator history."""

import pytest
import json

from engine.state import (
    GameState,
    StrictState,
    VibeState,
    create_initial_state,
    state_to_json,
    state_from_json,
)


class TestNarratorHistory:
    """Test narrator history tracking in game state."""

    def test_initial_state_has_empty_narrator_history(self):
        """Verify that a new game state starts with empty narrator history."""
        state = create_initial_state()
        
        assert state.vibe.narrator_history == []
        assert isinstance(state.vibe.narrator_history, list)

    def test_narrator_history_can_be_appended(self):
        """Verify that narration text can be appended to history."""
        state = create_initial_state()
        
        # Simulate adding narrations
        state.vibe.narrator_history.append("First narration")
        state.vibe.narrator_history.append("Second narration")
        state.vibe.narrator_history.append("Third narration")
        
        assert len(state.vibe.narrator_history) == 3
        assert state.vibe.narrator_history[0] == "First narration"
        assert state.vibe.narrator_history[1] == "Second narration"
        assert state.vibe.narrator_history[2] == "Third narration"

    def test_narrator_history_persists_across_state_operations(self):
        """Verify that narrator history is maintained during state serialization."""
        # Create state with history
        state = create_initial_state()
        state.vibe.narrator_history.append("Welcome to the terminal.")
        state.vibe.narrator_history.append("Access denied.")
        state.vibe.narrator_history.append("Try again.")
        
        # Serialize to JSON
        json_str = state_to_json(state)
        
        # Verify JSON contains the history
        data = json.loads(json_str)
        assert "narrator_history" in data["vibe"]
        assert len(data["vibe"]["narrator_history"]) == 3
        
        # Deserialize back to state
        restored_state = state_from_json(json_str)
        
        # Verify history is preserved
        assert len(restored_state.vibe.narrator_history) == 3
        assert restored_state.vibe.narrator_history[0] == "Welcome to the terminal."
        assert restored_state.vibe.narrator_history[1] == "Access denied."
        assert restored_state.vibe.narrator_history[2] == "Try again."

    def test_narrator_history_handles_empty_list_in_json(self):
        """Verify that empty narrator history is handled correctly during deserialization."""
        json_str = """
        {
          "strict": {
            "gameCounter": 0,
            "level": 1,
            "currentLevelAttempsts": 0
          },
          "vibe": {
            "name": null,
            "narrator_history": []
          }
        }
        """
        
        state = state_from_json(json_str)
        
        assert state.vibe.narrator_history == []
        assert isinstance(state.vibe.narrator_history, list)

    def test_narrator_history_backwards_compatible_with_missing_field(self):
        """Verify that old JSON without narrator_history field is handled gracefully."""
        json_str = """
        {
          "strict": {
            "gameCounter": 5,
            "level": 2,
            "currentLevelAttempsts": 3
          },
          "vibe": {
            "name": "TestPlayer"
          }
        }
        """
        
        state = state_from_json(json_str)
        
        # Should default to empty list when field is missing
        assert state.vibe.narrator_history == []
        assert isinstance(state.vibe.narrator_history, list)

    def test_narrator_history_with_multiline_text(self):
        """Verify that narrator history can store multiline narration text."""
        state = create_initial_state()
        
        multiline_text = """System breach detected.
Security protocols activating.
You have 3 attempts remaining."""
        
        state.vibe.narrator_history.append(multiline_text)
        
        assert len(state.vibe.narrator_history) == 1
        assert state.vibe.narrator_history[0] == multiline_text
        
        # Verify it serializes and deserializes correctly
        json_str = state_to_json(state)
        restored_state = state_from_json(json_str)
        
        assert restored_state.vibe.narrator_history[0] == multiline_text


class TestVibeState:
    """Test the VibeState dataclass."""

    def test_vibe_state_initialization(self):
        """Verify VibeState can be created with default values."""
        vibe = VibeState()
        
        assert vibe.name is None
        assert vibe.narrator_history == []

    def test_vibe_state_with_values(self):
        """Verify VibeState can be created with custom values."""
        vibe = VibeState(
            name="Alice",
            narrator_history=["First", "Second"]
        )
        
        assert vibe.name == "Alice"
        assert len(vibe.narrator_history) == 2
        assert vibe.narrator_history[0] == "First"


class TestGameStateStructure:
    """Test the overall GameState structure."""

    def test_game_state_has_vibe_component(self):
        """Verify GameState includes vibe state with narrator_history."""
        state = create_initial_state()
        
        assert hasattr(state, "vibe")
        assert isinstance(state.vibe, VibeState)
        assert hasattr(state.vibe, "narrator_history")

    def test_game_state_serialization_includes_vibe(self):
        """Verify game state serialization includes VibeState fields."""
        state = create_initial_state()
        state.vibe.name = "Player1"
        state.vibe.narrator_history.append("Test narration")
        
        json_str = state_to_json(state)
        data = json.loads(json_str)
        
        assert "vibe" in data
        assert "name" in data["vibe"]
        assert "narrator_history" in data["vibe"]
        assert data["vibe"]["name"] == "Player1"
        assert data["vibe"]["narrator_history"] == ["Test narration"]
