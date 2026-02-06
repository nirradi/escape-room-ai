"""Tests for the game loop.

Tests the main game loop with user input simulation using stubbed mutator and narrator.
"""

import pytest
from unittest.mock import patch
from io import StringIO

from game.loop import main


class TestGameLoopWin:
    """Test the game loop win condition by driving it with simulated user input."""

    def test_win_with_stub_mutator(self):
        """WIN test: Execute the full loop and reach win condition."""
        # Simulate user inputs that increase confidence to win
        # The stub mutator increases confidence by 0.1 per "increase confidence" command
        # We need 5 inputs to reach 0.5 (the threshold)
        user_inputs = ["increase confidence"] * 5
        
        with patch("builtins.input", side_effect=user_inputs):
            # Should not raise an exception, just exit normally on win
            main(mutator_type="stub-win", narrator_type="stub")


class TestGameLoopTimeout:
    """Test the game loop timeout condition by driving it with simulated user input."""

    def test_timeout_with_max_iterations(self):
        """TIMEOUT test: Execute the loop until max counter is reached."""
        # level max_turns is 10, so we need 10 unhandled inputs to hit timeout
        # Each unhandled input increments the counter but doesn't change confidence
        user_inputs = ["unhandled command"] * 10
        
        with patch("builtins.input", side_effect=user_inputs):
            # Should exit normally on timeout
            main(mutator_type="stub-lose", narrator_type="stub")


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
                main(mutator_type="stub-lose", narrator_type="stub")
                
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
            assert "[urgency=DIRE]" in str(urgency_outputs[-1])

    def test_urgency_reflects_game_state(self):
        """Test that urgency is correctly set in game state through apply_patch."""
        # Test with enough inputs to reach conclusion (10 for timeout)
        user_inputs = ["cmd"] * 10
        
        with patch("builtins.input", side_effect=user_inputs):
            with patch("builtins.print") as mock_print:
                main(mutator_type="stub-lose", narrator_type="stub")
                
                # Capture printed outputs
                outputs = [call[0][0] for call in mock_print.call_args_list if call[0]]
        
        # Verify stub narrator output contains urgency
        urgency_outputs = [o for o in outputs if "[urgency=" in str(o)]
        assert len(urgency_outputs) >= 3, "Should have urgency output for each turn"
        
        # First few should be SOME URGENCY (turns 1-2 are < 25% of 10)
        for output in urgency_outputs[:2]:
            assert "[urgency=SOME URGENCY]" in str(output)

