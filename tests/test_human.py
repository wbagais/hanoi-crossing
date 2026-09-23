"""Human play at the terminal: prompts, re-prompts, timeouts, quitting (A1, A2)."""

import io
import random

import pytest

from hanoi_crossing.agents import RandomAgent, ScriptedAgent
from hanoi_crossing.engine import Action, initial_state, legal_actions, observe
from hanoi_crossing.human import Console, HumanAgent, LineReader, Timeout
from hanoi_crossing.runner import StopGame


def _ask(stdin: str, fallback=None, timeout=None, max_timeouts=3):  # noqa: ANN001, ANN202
    """Play one human turn from ``stdin``; returns the move, the agent and what it printed."""
    chat = io.StringIO()
    console = Console(LineReader(io.StringIO(stdin)), chat)
    fallback = fallback or ScriptedAgent([Action("skip")])
    agent = HumanAgent("A", 1, console, fallback, timeout, max_timeouts)
    state = initial_state(1)
    return agent.choose(observe(state, "A"), legal_actions(state, "A")), agent, chat.getvalue()


def test_typed_move_is_returned_after_re_prompting_on_garbage() -> None:
    action, agent, printed = _ask("foo\nlift 1\n")
    assert action == Action("lift", 1) and agent.source == "human"
    assert "Turn 1, player A" in printed and "A> " in printed
    assert "not a move, try again" in printed


def test_end_of_input_lets_the_fallback_move_and_labels_it_timeout() -> None:
    action, agent, _ = _ask("")
    assert action == Action("skip") and agent.source == "timeout"


def test_no_answer_in_time_lets_the_fallback_move() -> None:
    class NeverAnswers(LineReader):
        def get(self, timeout: float | None) -> str | None:
            raise Timeout

    console = Console(NeverAnswers(io.StringIO()), io.StringIO())
    agent = HumanAgent("A", 1, console, RandomAgent(random.Random(0)), timeout=0.02)
    state = initial_state(1)
    assert agent.choose(observe(state, "A"), legal_actions(state, "A")).verb in ("lift", "skip")
    assert agent.source == "timeout"


def test_third_unanswered_prompt_ends_the_game() -> None:
    with pytest.raises(StopGame):
        _ask("", max_timeouts=1)


@pytest.mark.parametrize("word", ["quit", "q", "exit"])
def test_quit_words_end_the_game(word: str) -> None:
    with pytest.raises(StopGame):
        _ask(f"{word}\n")
