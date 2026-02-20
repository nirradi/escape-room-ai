"""Tests for phase-specific prompt composition in llm.narrate."""

from engine.state import GameState, StrictState, VibeState
from game.level import Level
import llm.narrate as narrate_mod


class _FakeResponse:
    def __init__(self, content: str):
        self.content = content


class _FakeLLM:
    def __init__(self):
        self.last_messages = None

    def invoke(self, messages):
        self.last_messages = messages
        return _FakeResponse("narration")


def _state() -> GameState:
    return GameState(
        strict=StrictState(
            gameCounter=2,
            level=1,
            currentLevelAttempsts=1,
            solutionConfidenceScore=0.5,
        ),
        vibe=VibeState(
            name="player",
            dialogue=[
                {"role": "narrator", "content": "You enter the room."},
                {"role": "player", "content": "I inspect the panel."},
            ],
            urgency="MODERATE URGENCY",
            last_evaluator_classification="SOME_UNDERSTANDING",
        ),
    )


def _level() -> Level:
    return Level(
        level_id=1,
        title="Test",
        context="General context",
        narration_prompt="General narration guidance",
        win_narration_prompt="Win-only guidance",
        lose_narration_prompt="Lose-only guidance",
        key_player_requirement=None,
        max_turns=10,
    )


def test_win_phase_uses_only_win_specific_prompt(monkeypatch):
    fake_llm = _FakeLLM()
    monkeypatch.setattr(narrate_mod, "_get_llm", lambda: fake_llm)

    output = narrate_mod.narrate("open door", _state(), _level(), phase="win_end")

    assert output.text == "narration"
    assert fake_llm.last_messages is not None
    system_text = fake_llm.last_messages[0].content
    assert "Win ending narration guidelines:\nWin-only guidance" in system_text
    assert "Lose ending narration guidelines:\nLose-only guidance" not in system_text


def test_lose_phase_uses_only_lose_specific_prompt(monkeypatch):
    fake_llm = _FakeLLM()
    monkeypatch.setattr(narrate_mod, "_get_llm", lambda: fake_llm)

    output = narrate_mod.narrate("wait", _state(), _level(), phase="lose_end")

    assert output.text == "narration"
    assert fake_llm.last_messages is not None
    system_text = fake_llm.last_messages[0].content
    assert "Lose ending narration guidelines:\nLose-only guidance" in system_text
    assert "Win ending narration guidelines:\nWin-only guidance" not in system_text


def test_turn_phase_does_not_include_end_specific_prompts(monkeypatch):
    fake_llm = _FakeLLM()
    monkeypatch.setattr(narrate_mod, "_get_llm", lambda: fake_llm)

    output = narrate_mod.narrate("look around", _state(), _level(), phase="turn")

    assert output.text == "narration"
    assert fake_llm.last_messages is not None
    system_text = fake_llm.last_messages[0].content
    assert "Win ending narration guidelines:\nWin-only guidance" not in system_text
    assert "Lose ending narration guidelines:\nLose-only guidance" not in system_text
