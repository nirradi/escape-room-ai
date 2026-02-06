#!/usr/bin/env python3
"""
Benchmark script for evaluate() function.

Loads test cases from CSV and level from YAML to run a structured test suite.
Tests all 4 classification outcomes with 15 test cases (including 5 enhanced PARTIAL_UNDERSTANDING cases).
"""

import sys
import csv
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

# Add parent directory to path so we can import from the project
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from engine.state import GameState, StrictState, VibeState
from game.level import load_level
from llm.evaluate import evaluate


@dataclass
class TestCase:
    """Represents a single test case for the evaluator."""
    case_id: int
    description: str
    dialogue_history: list
    player_input: str
    expected_classification: str


# Dialogue history templates for each test case
DIALOGUE_TEMPLATES = {
    1: [
        {"role": "narrator", "content": "You find a locked door on the wall."},
        {"role": "player", "content": "I see a locked door"},
        {"role": "narrator", "content": "Yes, it appears to require a key."},
    ],
    2: [
        {"role": "narrator", "content": "The door has a keyhole. A rusty key is on the floor."},
        {"role": "player", "content": "Where's the lock?"},
        {"role": "narrator", "content": "The lock is on the door, in the keyhole."},
    ],
    3: [
        {"role": "narrator", "content": "A heavy wooden door blocks your path. You find an ornate key."},
        {"role": "player", "content": "Is this door locked?"},
        {"role": "narrator", "content": "Yes, sealed tight. The key might work."},
        {"role": "player", "content": "I'll take the key and try it"},
    ],
    4: [
        {"role": "narrator", "content": "A locked door stands before you."},
        {"role": "player", "content": "I see a locked door"},
    ],
    5: [
        {"role": "narrator", "content": "You find a key on the table."},
        {"role": "player", "content": "A key! That's useful."},
        {"role": "narrator", "content": "Yes, it's ornate and heavy."},
    ],
    6: [
        {"role": "narrator", "content": "The door is wooden with a large lock. A key rests on a shelf."},
        {"role": "player", "content": "I pick up the key"},
        {"role": "narrator", "content": "You now hold the brass key."},
    ],
    7: [
        {"role": "narrator", "content": "You see an ornate door and hold a golden key."},
        {"role": "player", "content": "What do I do with this key?"},
        {"role": "narrator", "content": "You could try using it on locks you find."},
    ],
    8: [
        {"role": "narrator", "content": "Before you stands a locked wooden door and in your hand is a key."},
        {"role": "player", "content": "I have this key but I'm not sure what it opens"},
        {"role": "narrator", "content": "Perhaps explore and see."},
    ],
    9: [
        {"role": "narrator", "content": "The room has a locked metal door. On the ground lies an ornate key."},
        {"role": "player", "content": "There's a key here and a locked door there"},
        {"role": "narrator", "content": "Indeed."},
    ],
    10: [
        {"role": "narrator", "content": "You're in a room with a locked door. You pick up a silver key."},
        {"role": "player", "content": "I found this key"},
        {"role": "narrator", "content": "What will you do with it?"},
    ],
    11: [
        {"role": "narrator", "content": "A sturdy door with a keyhole blocks your exit. A key rests nearby."},
        {"role": "player", "content": "I examine the key closely"},
        {"role": "narrator", "content": "It appears old but well-crafted."},
    ],
    12: [
        {"role": "narrator", "content": "You're trapped in a room with a locked door."},
        {"role": "player", "content": "What's in here?"},
    ],
    13: [
        {"role": "narrator", "content": "A locked door blocks your exit. You see a key nearby."},
        {"role": "player", "content": "What time is it?"},
        {"role": "narrator", "content": "You don't have a watch."},
    ],
    14: [
        {"role": "narrator", "content": "You stand before a locked wooden door. A key is on the ground."},
        {"role": "player", "content": "I'll break down the door with my bare hands"},
        {"role": "narrator", "content": "The door is too strong, your hands hurt."},
    ],
    15: [
        {"role": "narrator", "content": "A locked door with a keyhole. A key sits on the table."},
        {"role": "player", "content": "I need to find the key to unlock this door"},
        {"role": "narrator", "content": "Correct, and you have found it."},
        {"role": "player", "content": "Now I'll use it"},
    ],
}


def load_test_cases_from_csv(csv_path: Path) -> list[TestCase]:
    """Load test cases from CSV file."""
    test_cases = []
    
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            case_id = int(row['case_id'])
            test_cases.append(TestCase(
                case_id=case_id,
                description=row['description'],
                dialogue_history=DIALOGUE_TEMPLATES.get(case_id, []),
                player_input=row['player_input'],
                expected_classification=row['expected_classification'],
            ))
    
    return test_cases


def run_test_case(test_case: TestCase, level) -> tuple[bool, Optional[str]]:
    """Run a single test case. 
    
    Returns:
        (is_correct, actual_classification): 
        - is_correct: True if result matches expected classification
        - actual_classification: The classification returned, or None if error/invalid
    """
    
    state = GameState(
        strict=StrictState(
            gameCounter=len(test_case.dialogue_history),
            level=1,
            currentLevelAttempsts=1,
            solutionConfidenceScore=0.0,
        ),
        vibe=VibeState(
            name="player",
            dialogue=test_case.dialogue_history,
            urgency="MODERATE",
            last_evaluator_classification=None,
        )
    )
    
    try:
        classification = evaluate(test_case.player_input, state, level)
        actual = classification.level
        is_correct = actual == test_case.expected_classification
        return (is_correct, actual)
    except Exception as e:
        print(f"      ✗ Exception raised: {str(e)[:60]}")
        return (False, None)


def benchmark_evaluate():
    """Run all test cases from CSV and report statistics."""
    
    print("=" * 80)
    print("EVALUATE BENCHMARK - STRUCTURED TEST SUITE (CSV + YAML)")
    print("=" * 80)
    print()
    
    # Load level from YAML
    level_path = Path(project_root) / "levels" / "test-evaluator.yaml"
    level = load_level(level_path)
    print(f"Loaded level: {level.title}")
    print()
    
    # Load test cases from CSV
    csv_path = Path(__file__).parent / "benchmark_evaluate_testcases.csv"
    test_cases = load_test_cases_from_csv(csv_path)
    print(f"Loaded {len(test_cases)} test cases from CSV")
    print("=" * 80)
    print()
    
    # Valid tokens for format compliance checking
    VALID_TOKENS = {"CLEAR_UNDERSTANDING", "PARTIAL_UNDERSTANDING", "NO_SIGNAL", "MISUNDERSTANDING"}
    
    # Track results by classification
    results = {
        "CLEAR_UNDERSTANDING": {"passed": 0, "total": 0},
        "PARTIAL_UNDERSTANDING": {"passed": 0, "total": 0},
        "NO_SIGNAL": {"passed": 0, "total": 0},
        "MISUNDERSTANDING": {"passed": 0, "total": 0},
    }
    
    total_passed = 0
    total_valid_format = 0  # Count of valid token responses
    total_tests = len(test_cases)
    
    # Run each test case
    for test_case in test_cases:
        is_correct, actual = run_test_case(test_case, level)
        results[test_case.expected_classification]["total"] += 1
        
        # Check format compliance
        is_valid_format = actual in VALID_TOKENS
        if is_valid_format:
            total_valid_format += 1
        
        if is_correct:
            status = "✓ PASS"
            results[test_case.expected_classification]["passed"] += 1
            total_passed += 1
        else:
            if is_valid_format:
                status = f"✗ FAIL (got {actual})"
            else:
                status = f"✗ FAIL (invalid: {actual})"
        
        print(f"[TEST {test_case.case_id:2d}] {status:30s}  {test_case.expected_classification:20s}  {test_case.description}")
        print(f"         Input: \"{test_case.player_input[:60]}...\"")
        print()
    
    # Print summary
    print("=" * 80)
    print("BENCHMARK SUMMARY")
    print("=" * 80)
    
    # Format compliance metrics
    format_compliance = (total_valid_format / total_tests) * 100
    print(f"\n{'INSTRUCTION-FOLLOWING (Format Compliance)':<50}")
    print(f"  Valid token responses: {total_valid_format}/{total_tests} ({format_compliance:.1f}%)")
    print(f"  Invalid responses:     {total_tests - total_valid_format}/{total_tests} ({100 - format_compliance:.1f}%)")
    
    # Classification accuracy (only among valid responses)
    print(f"\n{'CLASSIFICATION ACCURACY (Semantic Correctness)':<50}")
    if total_valid_format > 0:
        semantic_accuracy = (total_passed / total_valid_format) * 100
        print(f"  Correct classifications: {total_passed}/{total_valid_format} ({semantic_accuracy:.1f}%)")
        print(f"  Wrong classifications:   {total_valid_format - total_passed}/{total_valid_format} ({100 - semantic_accuracy:.1f}%)")
    else:
        print(f"  No valid responses to evaluate")
    
    # Overall accuracy
    overall_accuracy = (total_passed / total_tests) * 100
    print(f"\n{'OVERALL ACCURACY':<50}")
    print(f"  Total correct:  {total_passed}/{total_tests} ({overall_accuracy:.1f}%)")
    
    # Per-classification breakdown
    print(f"\n{'BREAKDOWN BY EXPECTED CLASSIFICATION':<50}")
    print("-" * 80)
    print(f"{'Classification':<25} {'Passed':<10} {'Total':<10} {'Rate':<10}")
    print("-" * 80)
    
    for classification in ["CLEAR_UNDERSTANDING", "PARTIAL_UNDERSTANDING", "NO_SIGNAL", "MISUNDERSTANDING"]:
        passed = results[classification]["passed"]
        total = results[classification]["total"]
        rate = f"{passed}/{total}" if total > 0 else "0/0"
        pct = f"{(passed/total)*100:.0f}%" if total > 0 else "N/A"
        print(f"{classification:<25} {passed:<10} {total:<10} {pct:<10}")
    
    print("=" * 80)
    
    # Success if at least 60% pass (9 out of 15)
    required_passes = int(total_tests * 0.6)
    return total_passed >= required_passes


if __name__ == "__main__":
    success = benchmark_evaluate()
    sys.exit(0 if success else 1)


