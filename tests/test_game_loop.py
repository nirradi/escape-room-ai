"""Tests for the game loop.

Tests the main game loop with player input simulation using stubbed evaluator and narrator.
"""

import pytest
from unittest.mock import patch, MagicMock
from io import StringIO

from game.loop import main
from engine import state as state_mod
from engine.patch import apply_patch


class TestGameLoopWin:
    """Test the game loop win condition by driving it with simulated player input."""

    def test_win_with_stub_evaluator(self):
        """WIN test: Execute the full loop and reach win condition."""
        # Simulate player inputs that increase confidence to win
        # The stub evaluator increases confidence by 0.25 per "increase confidence" command
        # We need 2 inputs to reach 0.5 (the threshold)
        user_inputs = ["increase confidence"] * 2
        
        with patch("builtins.input", side_effect=user_inputs):
            with patch("builtins.print") as mock_print:
                # Should not raise an exception, just exit normally on win
                main(evaluator_type="stub", narrator_type="stub")

                outputs = [call[0][0] for call in mock_print.call_args_list if call[0]]
                assert any("[end=win]" in str(o) for o in outputs), "Should emit win end narration"


class TestGameLoopTimeout:
    """Test the game loop timeout condition by driving it with simulated player input."""

    def test_timeout_with_max_iterations(self):
        """TIMEOUT test: Execute the loop until max counter is reached."""
        # level max_turns is 10, so we need 10 unhandled inputs to hit timeout
        # Each unhandled input increments the counter but doesn't change confidence
        user_inputs = ["unhandled command"] * 10
        
        with patch("builtins.input", side_effect=user_inputs):
            with patch("builtins.print") as mock_print:
                # Should exit normally on timeout
                main(evaluator_type="stub", narrator_type="stub")

                outputs = [call[0][0] for call in mock_print.call_args_list if call[0]]
                assert any("[end=lose]" in str(o) for o in outputs), "Should emit lose end narration"


class TestUrgencyProgression:
    """Test that urgency increases as the game progresses."""

    def test_urgency_increases_over_turns(self):
        """Test that urgency level increases as turns progress."""
        # Level max_turns is 10
        # Turn 1-2: SOME URGENCY (< 25%)
        # Turn 3-5: MODERATE URGENCY (25-50%)
        # Turn 6-7: VERY URGENT (50-75%)
        # Turn 8-10: DIRE (>= 75%)
        
        user_inputs = ["test"] * 10
        outputs = []
        
        with patch("builtins.input", side_effect=user_inputs):
            with patch("builtins.print") as mock_print:
                main(evaluator_type="stub", narrator_type="stub")
                
                # Capture all print outputs
                for call in mock_print.call_args_list:
                    if call[0]:  # if there are positional arguments
                        outputs.append(call[0][0])
        
        # Filter for urgency messages from the stub narrator
        urgency_outputs = [o for o in outputs if "[urgency=" in str(o)]
        
        # Verify we have urgency outputs
        assert len(urgency_outputs) > 0, "Should have urgency outputs from stub narrator"
        
        # Verify progression of urgency levels
        # First few should be SOME URGENCY
        assert "[urgency=SOME URGENCY]" in str(urgency_outputs[0])
        
        # Middle ones should show increased urgency
        if len(urgency_outputs) >= 5:
            assert any("MODERATE URGENCY" in str(o) or "VERY URGENT" in str(o) or "DIRE" in str(o) 
                      for o in urgency_outputs[3:])
        
        # Last ones should be DIRE
        if len(urgency_outputs) >= 8:
            assert "DIRE" in str(urgency_outputs[-1])

    def test_urgency_reflects_game_state(self):
        """Test that urgency is correctly set in game state through apply_patch."""
        # Test with enough inputs to reach conclusion (10 for timeout)
        user_inputs = ["cmd"] * 10
        
        with patch("builtins.input", side_effect=user_inputs):
            with patch("builtins.print") as mock_print:
                main(evaluator_type="stub", narrator_type="stub")
                
                # Capture printed outputs
                outputs = [call[0][0] for call in mock_print.call_args_list if call[0]]
        
        # Verify stub narrator output contains urgency
        urgency_outputs = [o for o in outputs if "[urgency=" in str(o)]
        assert len(urgency_outputs) >= 3, "Should have urgency output for each turn"
        
        # First few should be SOME URGENCY (turns 1-2 are < 25% of 10)
        for output in urgency_outputs[:2]:
            assert "[urgency=SOME URGENCY]" in str(output)


class TestStateProgression:
    """Test that game state progresses correctly through the loop."""

    def test_dialogue_accumulates_over_turns(self):
        """Test that user and narrator dialogue is accumulated in state."""
        user_inputs = ["hello", "test", "another", EOFError()]
        captured_states = []

        # Capture state after each apply_patch call
        original_apply_patch = apply_patch
        
        def capturing_apply_patch(state, patch_dict):
            result = original_apply_patch(state, patch_dict)
            captured_states.append(result.state)
            return result

        with patch("builtins.input", side_effect=user_inputs):
            with patch("game.loop.apply_patch", side_effect=capturing_apply_patch):
                # Use stub evaluator and narrator
                main(evaluator_type="stub", narrator_type="stub")

        # Should have captured multiple states
        assert len(captured_states) > 0, "Should have captured state snapshots"
        
        # Final state should have dialogue entries
        final_state = captured_states[-1]
        assert final_state.vibe.dialogue is not None
        assert len(final_state.vibe.dialogue) > 0, "Dialogue should not be empty"
        
        # Dialogue should contain both user and narrator roles
        roles = [turn.get("role") for turn in final_state.vibe.dialogue]
        assert "player" in roles, "Dialogue should contain player turns"
        assert "narrator" in roles, "Dialogue should contain narrator turns"

    def test_classification_stored_in_state(self):
        """Test that the last evaluator classification is stored in vibe state."""
        user_inputs = ["increase confidence", "test", EOFError()]
        captured_states = []

        original_apply_patch = apply_patch
        
        def capturing_apply_patch(state, patch_dict):
            result = original_apply_patch(state, patch_dict)
            captured_states.append(result.state)
            return result

        with patch("builtins.input", side_effect=user_inputs):
            with patch("game.loop.apply_patch", side_effect=capturing_apply_patch):
                main(evaluator_type="stub", narrator_type="stub")

        # Should have at least one state with classification set
        states_with_classification = [
            s for s in captured_states 
            if s.vibe.last_evaluator_classification is not None
        ]
        assert len(states_with_classification) > 0, "Should have states with classification"
        
        # Classification should be one of the expected values
        valid_classifications = {
            "COMMITTING_TO_CORRECT_MODEL",
            "SOME_UNDERSTANDING", 
            "NEUTRAL_ACTION",
            "COMMITTING_TO_INCORRECT_MODEL"
        }
        for state in states_with_classification:
            assert state.vibe.last_evaluator_classification in valid_classifications

    def test_confidence_score_changes_with_classification(self):
        """Test that confidence score updates based on classification."""
        # Use inputs that will generate different classifications
        user_inputs = ["increase confidence", "increase confidence", EOFError()]  # Both CLEAR
        captured_states = []

        original_apply_patch = apply_patch
        
        def capturing_apply_patch(state, patch_dict):
            result = original_apply_patch(state, patch_dict)
            captured_states.append(result.state)
            return result

        with patch("builtins.input", side_effect=user_inputs):
            with patch("game.loop.apply_patch", side_effect=capturing_apply_patch):
                main(evaluator_type="stub", narrator_type="stub")

        # Confidence should increase from initial 0.0
        initial_confidence = 0.0
        final_confidence = captured_states[-1].strict.solutionConfidenceScore
        assert final_confidence > initial_confidence, "Confidence should increase on COMMITTING_TO_CORRECT_MODEL"
        # Should reach win condition (0.5)
        assert final_confidence >= 0.5, "Should reach win condition after 2 CLEAR inputs"

    def test_game_counter_increments_each_turn(self):
        """Test that gameCounter increments with each user input."""
        user_inputs = ["test"] * 5 + [EOFError()]
        captured_states = []

        original_apply_patch = apply_patch
        
        def capturing_apply_patch(state, patch_dict):
            result = original_apply_patch(state, patch_dict)
            captured_states.append(result.state)
            return result

        with patch("builtins.input", side_effect=user_inputs):
            with patch("game.loop.apply_patch", side_effect=capturing_apply_patch):
                main(evaluator_type="stub", narrator_type="stub")

        # Game counter should increment monotonically (but may repeat within a turn)
        counters = [s.strict.gameCounter for s in captured_states]
        assert counters == sorted(counters), "Game counter should increment monotonically"
        # Should have at least as many turns as inputs provided
        unique_counters = len(set(counters))
        assert unique_counters >= 5, f"Should have at least 5 unique turns, got {unique_counters}"

    def test_urgency_updates_in_state(self):
        """Test that urgency is updated in vibe state."""
        user_inputs = ["test"] * 10 + [EOFError()]
        captured_states = []

        original_apply_patch = apply_patch
        
        def capturing_apply_patch(state, patch_dict):
            result = original_apply_patch(state, patch_dict)
            captured_states.append(result.state)
            return result

        with patch("builtins.input", side_effect=user_inputs):
            with patch("game.loop.apply_patch", side_effect=capturing_apply_patch):
                main(evaluator_type="stub", narrator_type="stub")

        # Should have multiple urgency values
        urgencies = [s.vibe.urgency for s in captured_states]
        unique_urgencies = set(urgencies)
        assert len(unique_urgencies) >= 1, "Should have at least one urgency value"
        
        # All urgencies should be valid
        valid_urgencies = {"SOME URGENCY", "MODERATE URGENCY", "VERY URGENT", "DIRE"}
        for urgency in unique_urgencies:
            assert urgency in valid_urgencies, f"Invalid urgency: {urgency}"


