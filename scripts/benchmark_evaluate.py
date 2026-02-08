#!/usr/bin/env python3
"""
Benchmark script for evaluate() function.

Loads test cases from CSV and level from YAML to run a structured test suite.
Tests all 4 classification outcomes with various test cases.
"""

import sys
import csv
import argparse
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
    player_input: str
    expected_classification: str


def load_test_cases_from_csv(csv_path: Path) -> list[TestCase]:
    """Load test cases from CSV file."""
    test_cases = []
    
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            test_cases.append(TestCase(
                case_id=int(row['case_id']),
                description=row['description'],
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
            gameCounter=1,
            level=1,
            currentLevelAttempsts=1,
            solutionConfidenceScore=0.0,
        ),
        vibe=VibeState(
            name="player",
            dialogue=[],  # Empty dialogue history - focusing on current input only
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


def benchmark_evaluate(csv_path: Path, level_path: Path, benchmark_name: str = "EVALUATE BENCHMARK"):
    """Run all test cases from CSV and report statistics.
    
    Args:
        csv_path: Path to CSV file with test cases
        level_path: Path to level YAML file
        benchmark_name: Name of the benchmark for display
    """
    
    print("=" * 80)
    print(f"{benchmark_name}")
    print("=" * 80)
    print()
    
    # Load level from YAML
    level = load_level(level_path)
    print(f"Loaded level: {level.title}")
    print(f"Level path: {level_path}")
    print()
    
    # Load test cases from CSV
    test_cases = load_test_cases_from_csv(csv_path)
    print(f"Loaded {len(test_cases)} test cases from CSV")
    print(f"CSV path: {csv_path}")
    print("=" * 80)
    print()
    
    # Valid tokens for format compliance checking
    VALID_TOKENS = {"COMMITTING_TO_CORRECT_MODEL", "SOME_UNDERSTANDING", "NEUTRAL_ACTION", "COMMITTING_TO_INCORRECT_MODEL"}
    
    # Track results by classification
    results = {
        "COMMITTING_TO_CORRECT_MODEL": {"passed": 0, "total": 0},
        "SOME_UNDERSTANDING": {"passed": 0, "total": 0},
        "NEUTRAL_ACTION": {"passed": 0, "total": 0},
        "COMMITTING_TO_INCORRECT_MODEL": {"passed": 0, "total": 0},
    }
    
    total_passed = 0
    total_valid_format = 0  # Count of valid token responses
    total_tests = len(test_cases)
    narrative_failures = []  # Track any narrative-style outputs
    determinism_failures = []  # Track determinism issues
    
    # Run each test case
    for test_case in test_cases:
        is_correct, actual = run_test_case(test_case, level)
        results[test_case.expected_classification]["total"] += 1
        
        # Check format compliance (must be valid token, not narrative)
        is_valid_format = actual in VALID_TOKENS
        if is_valid_format:
            total_valid_format += 1
        else:
            # Check if output looks like narrative (contains spaces, punctuation, multiple words)
            if actual and (len(actual.split()) > 1 or any(c in actual for c in ".,!?;:")):
                narrative_failures.append((test_case.case_id, actual))
        
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
    
    # Test determinism on a subset of test cases
    print("=" * 80)
    print("DETERMINISM CHECK (running same inputs twice)")
    print("=" * 80)
    for test_id in [1, 5, 12, 24, 27]:  # Sample from different categories
        test_case = next((tc for tc in test_cases if tc.case_id == test_id), None)
        if not test_case:
            continue
        _, result1 = run_test_case(test_case, level)
        _, result2 = run_test_case(test_case, level)
        is_deterministic = result1 == result2
        if is_deterministic:
            print(f"[TEST {test_id:2d}] ✓ Deterministic: {result1}")
        else:
            print(f"[TEST {test_id:2d}] ✗ NOT DETERMINISTIC: {result1} vs {result2}")
            determinism_failures.append((test_id, result1, result2))
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
    
    if narrative_failures:
        print(f"\n  ⚠ NARRATIVE OUTPUT DETECTED ({len(narrative_failures)} cases):")
        for case_id, output in narrative_failures[:3]:  # Show first 3
            print(f"    - Test {case_id}: {output[:60]}...")
    
    # Determinism check
    if determinism_failures:
        print(f"\n  ⚠ DETERMINISM FAILURES: {len(determinism_failures)} cases")
        for test_id, r1, r2 in determinism_failures:
            print(f"    - Test {test_id}: {r1} vs {r2}")
    else:
        print(f"\n  ✓ DETERMINISM: All sampled tests produced consistent results")
    
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
    
    for classification in ["COMMITTING_TO_CORRECT_MODEL", "SOME_UNDERSTANDING", "NEUTRAL_ACTION", "COMMITTING_TO_INCORRECT_MODEL"]:
        passed = results[classification]["passed"]
        total = results[classification]["total"]
        rate = f"{passed}/{total}" if total > 0 else "0/0"
        pct = f"{(passed/total)*100:.0f}%" if total > 0 else "N/A"
        print(f"{classification:<25} {passed:<10} {total:<10} {pct:<10}")
    
    print("=" * 80)
    
    # Success if at least 70% pass (higher bar for refactored version)
    required_passes = int(total_tests * 0.7)
    success = (total_passed >= required_passes and 
               format_compliance >= 100 and  # All must be valid tokens
               len(narrative_failures) == 0 and  # No narrative outputs
               len(determinism_failures) == 0)  # Must be deterministic
    
    # Return stats for aggregation
    return {
        "success": success,
        "total_tests": total_tests,
        "total_passed": total_passed,
        "format_compliance": format_compliance,
        "narrative_failures": len(narrative_failures),
        "determinism_failures": len(determinism_failures),
        "results": results,
    }


def print_combined_summary(all_stats: list):
    """Print a combined summary of all benchmark runs."""
    print("=" * 80)
    print("COMBINED SUMMARY - ALL BENCHMARKS")
    print("=" * 80)
    print()
    
    # Calculate totals
    total_tests_all = sum(s["total_tests"] for s in all_stats)
    total_passed_all = sum(s["total_passed"] for s in all_stats)
    overall_accuracy = (total_passed_all / total_tests_all * 100) if total_tests_all > 0 else 0
    
    # Per-benchmark summary
    print(f"{'Benchmark':<35} {'Passed':<12} {'Total':<12} {'Accuracy':<12} {'Status':<10}")
    print("-" * 80)
    for stats in all_stats:
        name = stats["benchmark_name"].replace(" BENCHMARK", "")
        passed = stats["total_passed"]
        total = stats["total_tests"]
        accuracy = (passed / total * 100) if total > 0 else 0
        status = "✓ PASS" if stats["success"] else "✗ FAIL"
        print(f"{name:<35} {passed:<12} {total:<12} {accuracy:<11.1f}% {status:<10}")
    
    print("-" * 80)
    print(f"{'TOTAL':<35} {total_passed_all:<12} {total_tests_all:<12} {overall_accuracy:<11.1f}%")
    print()
    
    # Quality metrics
    total_format_issues = sum(s["total_tests"] for s in all_stats) - sum(s["total_tests"] * s["format_compliance"] / 100 for s in all_stats)
    total_narrative_failures = sum(s["narrative_failures"] for s in all_stats)
    total_determinism_failures = sum(s["determinism_failures"] for s in all_stats)
    
    print(f"{'QUALITY METRICS':<35}")
    print(f"  Format compliance issues:  {int(total_format_issues)}")
    print(f"  Narrative output failures: {total_narrative_failures}")
    print(f"  Determinism failures:      {total_determinism_failures}")
    print()
    
    # Aggregate by classification type
    print(f"{'AGGREGATE BY CLASSIFICATION TYPE':<35}")
    print("-" * 80)
    print(f"{'Classification':<30} {'Passed':<12} {'Total':<12} {'Rate':<12}")
    print("-" * 80)
    
    for classification in ["COMMITTING_TO_CORRECT_MODEL", "SOME_UNDERSTANDING", "NEUTRAL_ACTION", "COMMITTING_TO_INCORRECT_MODEL"]:
        total_passed_class = sum(s["results"][classification]["passed"] for s in all_stats)
        total_tests_class = sum(s["results"][classification]["total"] for s in all_stats)
        rate = f"{(total_passed_class/total_tests_class)*100:.0f}%" if total_tests_class > 0 else "N/A"
        print(f"{classification:<30} {total_passed_class:<12} {total_tests_class:<12} {rate:<12}")
    
    print("=" * 80)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run evaluate() benchmark tests")
    parser.add_argument(
        "--csv",
        type=Path,
        help="Path to CSV file with test cases (default: benchmark_evaluate_testcases.csv)"
    )
    parser.add_argument(
        "--level",
        type=Path,
        help="Path to level YAML file (default: levels/test-evaluator.yaml)"
    )
    parser.add_argument(
        "--name",
        type=str,
        default="EVALUATE BENCHMARK",
        help="Name of the benchmark for display"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run all available benchmarks"
    )
    
    args = parser.parse_args()
    
    if args.all:
        # Run all benchmarks
        benchmarks = [
            {
                "csv": Path(__file__).parent / "benchmark_evaluate_testcases.csv",
                "level": project_root / "levels" / "test-evaluator.yaml",
                "name": "TEST-EVALUATOR BENCHMARK"
            },
            {
                "csv": Path(__file__).parent / "benchmark_between_floors.csv",
                "level": project_root / "levels" / "between-floors.yaml",
                "name": "BETWEEN-FLOORS BENCHMARK"
            },
            {
                "csv": Path(__file__).parent / "benchmark_ice_cream.csv",
                "level": project_root / "levels" / "ice-cream.yaml",
                "name": "ICE-CREAM BENCHMARK"
            },
        ]
        
        all_stats = []
        for i, benchmark in enumerate(benchmarks):
            if i > 0:
                print("\n\n")  # Space between benchmarks
            stats = benchmark_evaluate(
                benchmark["csv"],
                benchmark["level"],
                benchmark["name"]
            )
            stats["benchmark_name"] = benchmark["name"]
            all_stats.append(stats)
        
        # Print combined summary
        print("\n\n")
        print_combined_summary(all_stats)
        
        all_success = all(s["success"] for s in all_stats)
        sys.exit(0 if all_success else 1)
    else:
        # Run single benchmark with specified or default paths
        csv_path = args.csv if args.csv else Path(__file__).parent / "benchmark_evaluate_testcases.csv"
        level_path = args.level if args.level else project_root / "levels" / "test-evaluator.yaml"
        
        stats = benchmark_evaluate(csv_path, level_path, args.name)
        sys.exit(0 if stats["success"] else 1)


