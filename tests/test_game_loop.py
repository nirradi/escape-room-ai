"""Tests for the game loop.

Tests the main game loop with user input simulation using stubbed mutator and narrator.
"""

import pytest
from unittest.mock import patch

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
        # maxGameCounter is 10, so we need 10 unhandled inputs to hit timeout
        # Each unhandled input increments the counter but doesn't change confidence
        user_inputs = ["unhandled command"] * 10
        
        with patch("builtins.input", side_effect=user_inputs):
            # Should exit normally on timeout
            main(mutator_type="stub-lose", narrator_type="stub")
