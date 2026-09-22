"""Human play at the terminal: prompts, re-prompts, timeouts, quitting (A1, A2)."""

import io
import random

import pytest

from hanoi_crossing.agents import RandomAgent, ScriptedAgent
from hanoi_crossing.engine import Action, initial_state, legal_actions, observe
from hanoi_crossing.human import Console, HumanAgent, LineReader, Timeout
from hanoi_crossing.runner import StopGame

LEGAL_START = [Action("lift", 1), Action("skip")]


def _human(stdin: str, timeout: float | None = None, max_timeouts: int = 3):  # noqa: ANN202
    chat = io.StringIO()
    console = Console(LineReader(io.StringIO(stdin)), chat)
    fallback = ScriptedAgent([Action("skip")] * 10)
    return HumanAgent("A", 1, console, fallback, timeout, max_timeouts), chat


def _choose(agent: HumanAgent) -> Action:
    state = initial_state(1)
    return agent.choose(observe(state, "A"), legal_actions(state, "A"))


def test_typed_move_is_returned_and_labelled_human() -> None:
    agent, chat = _human("lift 1\n")
    assert _choose(agent) == Action("lift", 1) and agent.source == "human"
    assert "Turn 1, player A" in chat.getvalue() and "A> " in chat.getvalue()


def test_garbage_is_reprompted_and_illegal_moves_are_passed_through() -> None:
    agent, chat = _human("foo\nlift 2\n")
    assert _choose(agent) == Action("lift", 2)
    assert "not a move, try again" in chat.getvalue()


def test_end_of_input_lets_the_fallback_move_and_labels_it_timeout() -> None:
    agent, _ = _human("")
    assert _choose(agent) == Action("skip") and agent.source == "timeout"


class NeverAnswers(LineReader):
    def get(self, timeout: float | None) -> str | None:
        raise Timeout


def test_timeout_lets_the_fallback_move() -> None:
    console = Console(NeverAnswers(io.StringIO()), io.StringIO())
    agent = HumanAgent("A", 1, console, RandomAgent(random.Random(0)), timeout=0.02)
    assert _choose(agent) in LEGAL_START and agent.source == "timeout"


def test_unanswered_prompts_in_a_row_end_the_game() -> None:
    agent, _ = _human("", max_timeouts=3)
    _choose(agent)
    _choose(agent)
    assert agent.unanswered == 2
    with pytest.raises(StopGame):
        _choose(agent)


@pytest.mark.parametrize("word", ["quit", "q", "exit"])
def test_quit_words_end_the_game(word: str) -> None:
    agent, chat = _human(f"{word}\n")
    with pytest.raises(StopGame):
        _choose(agent)
    assert "game ended: player A quit" in chat.getvalue()
