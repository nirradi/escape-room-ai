"""Benchmark-style harness for the LLM mutator.

This script is exploratory and observational — it is NOT a unit test.
Run it directly with Python. It will call the real `llm.mutate.generate_patch`
and `engine.patch.apply_patch` repeatedly and print a human-readable
summary of outcomes.

Usage:
    python scripts/bench_mutator.py --intent set_clock --runs 20 --dump out.json

Important: this script does not mock the LLM. It may be slow or require
an LLM client to be configured (see `llm.client`).
"""

from __future__ import annotations

import argparse
import json
import time
from copy import deepcopy
from dataclasses import asdict
from pathlib import Path
from statistics import mean
from typing import Any, Dict, List

from engine.state import create_initial_state, state_to_json, copy_state
from engine.patch import apply_patch
from llm.mutate import generate_patch
from game.commands import Intent, IntentType

# these should build proper intents using Intent


def build_intent_set_clock(time_str: str = "09:00", timezone: str = "UTC") -> Intent:
    return Intent(type=IntentType.SET_CLOCK, params={"time": time_str, "timezone": timezone}, confidence=0.9)

def build_intent_send_email(recipient: str = "alice@example.com", sent_at: str = "08:30") -> Intent:
    return Intent(type=IntentType.SEND_EMAIL, params={"recipient": recipient, "sent_at": sent_at}, confidence=0.9)

def summarize_runs(results: List[Dict[str, Any]], expected_strict_fields: List[str]) -> None:
    total = len(results)
    valid_json_count = sum(1 for r in results if r["raw_patch"])
    applied_success = sum(1 for r in results if r["apply_result"] and r["apply_result"].success)
    strict_valid_count = sum(1 for r in results if r["apply_result"] and len(r["apply_result"].strict_errors) == 0)
    mutated_expected = 0
    unexpected_fields_counts = 0
    warnings_counts = [len(r["apply_result"].warnings) if r["apply_result"] else 0 for r in results]

    for r in results:
        patch = r["raw_patch"] or {}
        if not patch:
            continue
        strict = patch.get("strict", {}) if isinstance(patch.get("strict", {}), dict) else {}
        if any(f in strict for f in expected_strict_fields):
            # consider mutated if apply_result reports success and the strict field present
            if r["apply_result"] and r["apply_result"].success:
                mutated_expected += 1
        # unexpected: any strict key not in expected_strict_fields
        unexpected = [k for k in strict.keys() if k not in expected_strict_fields]
        if unexpected:
            unexpected_fields_counts += 1

    print("\nBench Mutator Summary")
    print("---------------------")
    print(f"Total runs: {total}")
    print(f"Valid JSON (non-empty patch): {valid_json_count} ({valid_json_count/total*100:.1f}%)")
    print(f"Apply success (no strict validation errors): {applied_success} ({applied_success/total*100:.1f}%)")
    print(f"Strict-valid runs (no strict errors reported): {strict_valid_count} ({strict_valid_count/total*100:.1f}%)")
    print(f"Mutated expected strict fields: {mutated_expected} ({mutated_expected/total*100:.1f}%)")
    print(f"Runs with unexpected strict fields: {unexpected_fields_counts} ({unexpected_fields_counts/total*100:.1f}%)")
    print(f"Average warnings per run: {mean(warnings_counts) if warnings_counts else 0:.2f}")

    print("\nSample outputs (first 5):")
    for i, r in enumerate(results[:5], 1):
        print(f"--- Run {i} ---")
        print("Raw patch:")
        print(json.dumps(r["raw_patch"], indent=2))
        ar = r["apply_result"]
        if ar:
            print("Apply success:", ar.success)
            if ar.strict_errors:
                print("Strict errors:")
                for e in ar.strict_errors:
                    print(f" - {e.field}: {e.reason} (value={e.attempted_value})")
            if ar.warnings:
                print("Warnings:")
                for w in ar.warnings:
                    print(f" - {w}")
        else:
            print("No apply result (empty or invalid patch)")


def run_benchmark(intent_name: str, runs: int, dump: Path | None) -> None:
    base_state = create_initial_state()
    results: List[Dict[str, Any]] = []

    if intent_name == "set_clock":
        intent = build_intent_set_clock()
        expected = ["clock"]
    elif intent_name == "send_email":
        intent = build_intent_send_email()
        expected = ["emails"]
    else:
        # default: use set_clock
        intent = build_intent_set_clock()
        expected = ["clock"]

    print(f"Running mutator benchmark: intent={intent_name}, runs={runs}")
    for i in range(1, runs + 1):
        state = deepcopy(base_state)
        start_time = time.time()
        patch = generate_patch(intent, state, level_context={})
        duration = time.time() - start_time

        apply_result = None
        try:
            if patch:
                apply_result = apply_patch(state, patch)
        except Exception as exc:  # defensive: never crash the harness
            print(f"Warning: apply_patch raised exception on run {i}: {exc}")

        results.append({
            "index": i,
            "duration": duration,
            "raw_patch": patch,
            "apply_result": apply_result,
        })

        print(f"Run {i}/{runs}: duration={duration:.2f}s, patch_keys={list(patch.keys()) if patch else []}")

    summarize_runs(results, expected_strict_fields=expected)

    if dump:
        serializable = []
        for r in results:
            ar = r["apply_result"]
            serializable.append({
                "index": r["index"],
                "duration": r["duration"],
                "raw_patch": r["raw_patch"],
                "apply_result": {
                    "success": ar.success if ar else None,
                    "strict_errors": [asdict(e) for e in ar.strict_errors] if ar and ar.strict_errors else [],
                    "warnings": ar.warnings if ar else [],
                } if ar else None,
            })
        dump.write_text(json.dumps(serializable, indent=2))
        print(f"Raw results dumped to {dump}")


def main():
    p = argparse.ArgumentParser(description="LLM Mutator benchmark harness")
    p.add_argument("--intent", choices=["set_clock", "send_email"], default="set_clock")
    p.add_argument("--runs", type=int, default=10)
    p.add_argument("--dump", type=Path, default=None)
    args = p.parse_args()

    run_benchmark(args.intent, args.runs, args.dump)


if __name__ == "__main__":
    main()
