"""Tests for patch application and urgency calculation."""

import pytest

from engine.patch import (
    apply_patch,
    _calculate_urgency,
    PatchResult,
)
from engine.state import create_initial_state, GameState, StrictState, VibeState


class TestUrgencyCalculation:
    """Test the urgency calculation function."""

    def test_urgency_at_start(self):
        """Test urgency at the beginning (0-25% progress)."""
        assert _calculate_urgency(0, 10) == "SOME URGENCY"
        assert _calculate_urgency(1, 10) == "SOME URGENCY"
        assert _calculate_urgency(2, 10) == "SOME URGENCY"

    def test_urgency_at_quarter(self):
        """Test urgency at 25-50% progress."""
        assert _calculate_urgency(3, 10) == "MODERATE URGENCY"
        assert _calculate_urgency(4, 10) == "MODERATE URGENCY"

    def test_urgency_at_half(self):
        """Test urgency at 50-75% progress."""
        assert _calculate_urgency(5, 10) == "VERY URGENT"
        assert _calculate_urgency(6, 10) == "VERY URGENT"
        assert _calculate_urgency(7, 10) == "VERY URGENT"

    def test_urgency_at_three_quarters(self):
        """Test urgency at 75%+ progress."""
        assert _calculate_urgency(8, 10) == "DIRE"
        assert _calculate_urgency(9, 10) == "DIRE"
        assert _calculate_urgency(10, 10) == "DIRE"

    def test_urgency_with_no_max_turns(self):
        """Test urgency defaults to SOME URGENCY when max_turns is None."""
        assert _calculate_urgency(5, None) == "SOME URGENCY"
        assert _calculate_urgency(100, None) == "SOME URGENCY"

    def test_urgency_with_zero_max_turns(self):
        """Test urgency defaults to SOME URGENCY when max_turns is 0."""
        assert _calculate_urgency(5, 0) == "SOME URGENCY"

    def test_urgency_progression_full_sequence(self):
        """Test complete urgency progression through all stages."""
        max_turns = 20
        
        # 0-4 turns (0-25%): SOME URGENCY
        for turn in range(0, 5):
            assert _calculate_urgency(turn, max_turns) == "SOME URGENCY"
        
        # 5-9 turns (25-50%): MODERATE URGENCY
        for turn in range(5, 10):
            assert _calculate_urgency(turn, max_turns) == "MODERATE URGENCY"
        
        # 10-14 turns (50-75%): VERY URGENT
        for turn in range(10, 15):
            assert _calculate_urgency(turn, max_turns) == "VERY URGENT"
        
        # 15-20 turns (75-100%): DIRE
        for turn in range(15, 21):
            assert _calculate_urgency(turn, max_turns) == "DIRE"


class TestApplyPatchWithUrgency:
    """Test that apply_patch correctly sets urgency in state."""

    def test_apply_patch_sets_urgency_initially(self):
        """Test that apply_patch sets urgency on first call."""
        state = create_initial_state()
        patch = {}
        
        result = apply_patch(state, patch, level_max_turns=10)
        
        assert result.success
        # After first turn (gameCounter = 1), urgency should be SOME URGENCY
        assert result.state.vibe.urgency == "SOME URGENCY"
        assert result.state.strict.gameCounter == 1

    def test_apply_patch_updates_urgency_progressively(self):
        """Test that urgency updates as game progresses."""
        state = create_initial_state()
        max_turns = 10
        
        # Apply patches repeatedly to simulate game progression
        for turn in range(10):
            result = apply_patch(state, {}, level_max_turns=max_turns)
            state = result.state
        
        # After 10 turns (100% progress), should be DIRE
        assert state.vibe.urgency == "DIRE"
        assert state.strict.gameCounter == 10

    def test_apply_patch_urgency_transitions(self):
        """Test urgency transitions through all levels."""
        state = create_initial_state()
        max_turns = 12
        
        urgency_history = []
        
        for _ in range(12):
            result = apply_patch(state, {}, level_max_turns=max_turns)
            state = result.state
            urgency_history.append(state.vibe.urgency)
        
        # Verify we see all urgency levels in order
        assert "SOME URGENCY" in urgency_history
        assert "MODERATE URGENCY" in urgency_history
        assert "VERY URGENT" in urgency_history
        assert "DIRE" in urgency_history
        
        # Verify ordering: urgency should only increase or stay same
        urgency_levels = ["SOME URGENCY", "MODERATE URGENCY", "VERY URGENT", "DIRE"]
        urgency_indices = [urgency_levels.index(u) for u in urgency_history]
        
        for i in range(len(urgency_indices) - 1):
            assert urgency_indices[i] <= urgency_indices[i + 1], \
                "Urgency should never decrease"

    def test_apply_patch_without_max_turns(self):
        """Test that urgency defaults to SOME URGENCY without max_turns."""
        state = create_initial_state()
        
        for _ in range(5):
            result = apply_patch(state, {})  # No level_max_turns
            state = result.state
        
        # Without max_turns, urgency should always be SOME URGENCY
        assert state.vibe.urgency == "SOME URGENCY"

    def test_apply_patch_preserves_other_vibe_state(self):
        """Test that urgency updates don't affect other vibe state."""
        state = create_initial_state()
        state.vibe.name = "Player1"
        state.vibe.narrator_history = ["First", "Second"]
        
        result = apply_patch(state, {}, level_max_turns=10)
        
        # Verify other vibe state is preserved
        assert result.state.vibe.name == "Player1"
        assert result.state.vibe.narrator_history == ["First", "Second"]
        # But urgency should be updated
        assert result.state.vibe.urgency == "SOME URGENCY"

    def test_apply_patch_with_strict_patch(self):
        """Test that urgency is still calculated when applying strict patches."""
        state = create_initial_state()
        
        # Apply a patch that changes confidence
        patch = {
            "strict": {
                "solutionConfidenceScore": 0.5
            }
        }
        
        result = apply_patch(state, patch, level_max_turns=10)
        
        assert result.success
        assert result.state.strict.solutionConfidenceScore == 0.5
        assert result.state.vibe.urgency == "SOME URGENCY"
        assert result.state.strict.gameCounter == 1
