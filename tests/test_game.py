"""Tests for top-level game orchestrator."""

from pathlib import Path

from game.runner import run_game
from game.runner import run_game_from_config


class TestGameOrchestrator:
    """Validate multi-level orchestration and retry behavior."""

    def test_win_advances_and_finishes_with_game_over(self):
        inputs = iter([
            "increase confidence",
            "increase confidence",  # level 1 win
            "increase confidence",
            "increase confidence",  # level 2 win
        ])
        outputs = []

        def input_fn(prompt: str) -> str:
            return next(inputs)

        def output_fn(event) -> None:
            outputs.append(event.text)

        run_game(
            level_names=["bobs-plan.yaml", "between-floors.yaml"],
            evaluator_type="stub",
            narrator_type="stub",
            input_fn=input_fn,
            output_fn=output_fn,
        )

        assert any("[end=win]" in output for output in outputs)
        assert outputs[-1] == "Game Over"

    def test_loss_retries_same_level_then_win(self):
        inputs = iter([
            *(["unhandled command"] * 10),  # lose first attempt
            "increase confidence",
            "increase confidence",  # win retry attempt
        ])
        outputs = []

        def input_fn(prompt: str) -> str:
            return next(inputs)

        def output_fn(event) -> None:
            outputs.append(event.text)

        run_game(
            level_names=["bobs-plan.yaml"],
            evaluator_type="stub",
            narrator_type="stub",
            input_fn=input_fn,
            output_fn=output_fn,
        )

        assert any("[end=lose]" in output for output in outputs)
        assert any("[end=win]" in output for output in outputs)
        assert outputs[-1] == "Game Over"

    def test_run_from_yaml_config(self, tmp_path: Path):
        config_file = tmp_path / "game.yaml"
        config_file.write_text(
            """
evaluator_type: stub
narrator_type: stub
levels:
  - bobs-plan.yaml
""".strip()
        )

        inputs = iter(["increase confidence", "increase confidence"])
        outputs = []

        def input_fn(prompt: str) -> str:
            return next(inputs)

        def output_fn(event) -> None:
            outputs.append(event.text)

        run_game_from_config(config_path=config_file, input_fn=input_fn, output_fn=output_fn)

        assert any("[end=win]" in output for output in outputs)
        assert outputs[-1] == "Game Over"
