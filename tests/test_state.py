"""Tests for game state management and dialogue history."""

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


class TestDialogue:
    """Test dialogue tracking in game state."""

    def test_initial_state_has_empty_dialogue(self):
        """Verify that a new game state starts with empty dialogue."""
        state = create_initial_state()
        
        assert state.vibe.dialogue == []
        assert isinstance(state.vibe.dialogue, list)

    def test_dialogue_can_be_appended(self):
        """Verify that player and narrator turns can be appended to dialogue."""
        state = create_initial_state()
        
        # Simulate adding dialogue turns
        state.vibe.dialogue.append({"role": "player", "content": "What is this place?"})
        state.vibe.dialogue.append({"role": "narrator", "content": "A mysterious room."})
        state.vibe.dialogue.append({"role": "player", "content": "Where do I go?"})
        
        assert len(state.vibe.dialogue) == 3
        assert state.vibe.dialogue[0]["role"] == "player"
        assert state.vibe.dialogue[1]["role"] == "narrator"
        assert state.vibe.dialogue[2]["role"] == "player"

    def test_dialogue_persists_across_state_operations(self):
        """Verify that dialogue is maintained during state serialization."""
        # Create state with dialogue
        state = create_initial_state()
        state.vibe.dialogue.append({"role": "player", "content": "Hello"})
        state.vibe.dialogue.append({"role": "narrator", "content": "Welcome."})
        
        # Serialize to JSON
        json_str = state_to_json(state)
        
        # Verify JSON contains the dialogue
        data = json.loads(json_str)
        assert "dialogue" in data["vibe"]
        assert len(data["vibe"]["dialogue"]) == 2
        
        # Deserialize back to state
        restored_state = state_from_json(json_str)
        
        # Verify dialogue is preserved
        assert len(restored_state.vibe.dialogue) == 2
        assert restored_state.vibe.dialogue[0]["role"] == "player"
        assert restored_state.vibe.dialogue[1]["role"] == "narrator"

    def test_dialogue_handles_empty_list_in_json(self):
        """Verify that empty dialogue is handled correctly during deserialization."""
        json_str = """
        {
          "strict": {
            "gameCounter": 0,
            "level": 1,
            "currentLevelAttempsts": 0
          },
          "vibe": {
            "name": null,
            "dialogue": []
          }
        }
        """
        
        state = state_from_json(json_str)
        
        assert state.vibe.dialogue == []
        assert isinstance(state.vibe.dialogue, list)

    def test_dialogue_backwards_compatible_with_missing_field(self):
        """Verify that old JSON without dialogue field is handled gracefully."""
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
        assert state.vibe.dialogue == []
        assert isinstance(state.vibe.dialogue, list)

    def test_dialogue_with_multiline_content(self):
        """Verify that dialogue can store multiline content."""
        state = create_initial_state()
        
        multiline_content = """System breach detected.
Security protocols activating.
You have 3 attempts remaining."""
        
        state.vibe.dialogue.append({"role": "narrator", "content": multiline_content})
        
        assert len(state.vibe.dialogue) == 1
        assert state.vibe.dialogue[0]["content"] == multiline_content
        
        # Verify it serializes and deserializes correctly
        json_str = state_to_json(state)
        restored_state = state_from_json(json_str)
        
        assert restored_state.vibe.dialogue[0]["content"] == multiline_content


class TestVibeState:
    """Test the VibeState dataclass."""

    def test_vibe_state_initialization(self):
        """Verify VibeState can be created with default values."""
        vibe = VibeState()
        
        assert vibe.name is None
        assert vibe.dialogue == []

    def test_vibe_state_with_values(self):
        """Verify VibeState can be created with custom values."""
        vibe = VibeState(
            name="Alice",
            dialogue=[{"role": "player", "content": "Hello"}]
        )
        
        assert vibe.name == "Alice"
        assert len(vibe.dialogue) == 1
        assert vibe.dialogue[0]["role"] == "player"


class TestGameStateStructure:
    """Test the overall GameState structure."""

    def test_game_state_has_vibe_component(self):
        """Verify GameState includes vibe state with dialogue."""
        state = create_initial_state()
        
        assert hasattr(state, "vibe")
        assert isinstance(state.vibe, VibeState)
        assert hasattr(state.vibe, "dialogue")

    def test_game_state_serialization_includes_vibe(self):
        """Verify game state serialization includes VibeState fields."""
        state = create_initial_state()
        state.vibe.name = "Player1"
        state.vibe.dialogue.append({"role": "player", "content": "Test input"})
        
        json_str = state_to_json(state)
        data = json.loads(json_str)
        
        assert "vibe" in data
        assert "name" in data["vibe"]
        assert "dialogue" in data["vibe"]
        assert data["vibe"]["name"] == "Player1"
        assert len(data["vibe"]["dialogue"]) == 1
