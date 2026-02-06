"""Benchmark utility for Narrator LLM renderer.

This script benchmarks the LLM-based narration output for various outcomes.
Run directly with Python. It will call llm.narrate.generate_narration repeatedly and print a summary.

Usage:
    python scripts/bench_narrator.py --intent set_clock --runs 10 --dump out.json

Note: This script does not mock the LLM. It may be slow or require an LLM client to be configured.
"""

import argparse
import json
import time
from pathlib import Path
from typing import Any, Dict, List
from dataclasses import asdict

from llm.narrate import NarrationInput, generate_narration

# Example input scenarios for benchmarking
def build_narration_input(intent_type: str = "SET_CLOCK", success: bool = True, errors=None, patch=None) -> NarrationInput:
    return NarrationInput(
        intent_type=intent_type,
        success=success,
        errors=errors or [],
        patch=patch or None,
    )

def run_benchmark(intent_type: str, runs: int, dump: Path | None) -> None:
    results: List[Dict[str, Any]] = []
    print(f"Running narrator benchmark: intent={intent_type}, runs={runs}")
    for i in range(1, runs + 1):
        # Alternate between success and failure for diversity
        success = (i % 2 == 1)
        errors = [] if success else ["Permission denied", "Malformed request"]
        patch = {"clock": "09:00"} if intent_type == "SET_CLOCK" and success else None
        input_obj = build_narration_input(intent_type=intent_type, success=success, errors=errors, patch=patch)
        start_time = time.time()
        narration = generate_narration(input_obj)
        duration = time.time() - start_time
        results.append({
            "index": i,
            "duration": duration,
            "input": asdict(input_obj),
            "narration": narration,
        })
        print(f"Run {i}/{runs}: duration={duration:.2f}s\nInput: {input_obj}\nNarration: {narration}\n")
    print("\nSample outputs (first 5):")
    for r in results[:5]:
        print(f"--- Run {r['index']} ---")
        print("Input:", r["input"])
        print("Narration:", r["narration"])
    if dump:
        dump.write_text(json.dumps(results, indent=2))
        print(f"Raw results dumped to {dump}")

def main():
    p = argparse.ArgumentParser(description="LLM Narrator benchmark harness")
    p.add_argument("--intent", default="SET_CLOCK")
    p.add_argument("--runs", type=int, default=10)
    p.add_argument("--dump", type=Path, default=None)
    args = p.parse_args()
    run_benchmark(args.intent, args.runs, args.dump)

if __name__ == "__main__":
    main()
