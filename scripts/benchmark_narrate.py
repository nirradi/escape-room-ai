#!/usr/bin/env python3
"""
Benchmark script for narrate() function.

Tests the narrate entry point with basic game state and user input
to verify it's not broken logically. Tests both initial narration
(empty dialogue) and dialogue scenarios.
"""

import sys
from pathlib import Path

# Add parent directory to path so we can import from the project
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from engine.state import GameState, StrictState, VibeState
from game.level import Level
from llm.narrate import narrate


def benchmark_narrate():
    """Run benchmark test for narrate function."""
    
    print("=" * 70)
    print("NARRATE BENCHMARK")
    print("=" * 70)
    
    # Create a basic game state
    state = GameState(
        strict=StrictState(
            gameCounter=1,
            level=1,
            currentLevelAttempsts=1,
            solutionConfidenceScore=0.5,
        ),
        vibe=VibeState(
            name="player",
            dialogue=[],
            urgency="MODERATE",
            last_evaluator_classification=None,
        )
    )
    
    # Create a basic level definition
    level = Level(
        level_id=1,
        title="Test Level",
        context="You are in a mysterious escape room. Find a way out.",
        narration_prompt="Be terse. Describe only what the player observes.",
        key_player_requirement=None,
        max_turns=10,
    )
    
    # Test 1: Initial narration (empty dialogue)
    print("\n[TEST 1] Initial Narration (empty dialogue)")
    print("-" * 70)
    try:
        narration_1 = narrate("", state, level)
        output_1 = narration_1.text
        
        if output_1 and output_1 != "[narration unavailable]":
            print(f"✓ Initial narration generated successfully")
            print(f"  Output ({len(output_1)} chars): {output_1[:100]}...")
        else:
            print(f"✗ Initial narration failed or returned fallback")
            return False
    except Exception as e:
        print(f"✗ Initial narration raised exception: {e}")
        return False
    
    # Test 2: Narration with dialogue history
    print("\n[TEST 2] Narration with dialogue history")
    print("-" * 70)
    
    # Update state to include dialogue history
    state.vibe.dialogue = [
        {"role": "narrator", "content": output_1},
        {"role": "player", "content": "Look around carefully"},
    ]
    state.vibe.last_evaluator_classification = "PARTIAL_UNDERSTANDING"
    
    try:
        narration_2 = narrate("What do I see?", state, level)
        output_2 = narration_2.text
        
        if output_2 and output_2 != "[narration unavailable]":
            print(f"✓ Follow-up narration generated successfully")
            print(f"  Output ({len(output_2)} chars): {output_2[:100]}...")
        else:
            print(f"✗ Follow-up narration failed or returned fallback")
            return False
    except Exception as e:
        print(f"✗ Follow-up narration raised exception: {e}")
        return False
    
    # Summary
    print("\n" + "=" * 70)
    print("BENCHMARK COMPLETE - ALL TESTS PASSED ✓")
    print("=" * 70)
    print(f"\n✓ Test 1: Initial narration works")
    print(f"✓ Test 2: Follow-up narration works")
    print(f"\nBoth narrations generated valid output without errors.")
    
    return True


if __name__ == "__main__":
    success = benchmark_narrate()
    sys.exit(0 if success else 1)
