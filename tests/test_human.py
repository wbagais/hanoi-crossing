"""Human play at the terminal: prompts, re-prompts, timeouts, quitting (A1, A2)."""

import io
import random
import threading

import pytest

from hanoi_crossing.agents import RandomAgent, ScriptedAgent
from hanoi_crossing.engine import Action, initial_state, legal_actions, observe
from hanoi_crossing.human import Console, HumanAgent, LineReader
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


def test_line_reader_gives_up_when_no_line_arrives() -> None:
    typing = threading.Event()  # a stdin nobody types into, until we let it end

    class SilentStream(io.StringIO):
        def __iter__(self):  # noqa: ANN204
            typing.wait(5)
            return iter([])

    reader = LineReader(SilentStream())
    try:
        with pytest.raises(TimeoutError):
            reader.get(0.05)
    finally:
        typing.set()


class _NeverAnswers(LineReader):
    """A reader that never answers, and remembers the deadline it was handed."""

    def __init__(self) -> None:
        super().__init__(io.StringIO())
        self.deadlines: list[float | None] = []

    def get(self, timeout: float | None) -> str | None:
        self.deadlines.append(timeout)
        raise TimeoutError


def test_the_prompt_is_given_the_remaining_seconds() -> None:
    reader = _NeverAnswers()
    agent = HumanAgent("A", 1, Console(reader, io.StringIO()), ScriptedAgent([Action("skip")]), 5)
    state = initial_state(1)
    agent.choose(observe(state, "A"), legal_actions(state, "A"))
    assert reader.deadlines and 0 < reader.deadlines[0] <= 5, "a deadline must reach the reader"


def test_without_a_move_timeout_the_prompt_waits_forever() -> None:
    reader = _NeverAnswers()
    agent = HumanAgent("A", 1, Console(reader, io.StringIO()), ScriptedAgent([Action("skip")]))
    state = initial_state(1)
    agent.choose(observe(state, "A"), legal_actions(state, "A"))
    assert reader.deadlines == [None]


def test_no_answer_in_time_lets_the_fallback_move() -> None:
    console = Console(_NeverAnswers(), io.StringIO())
    agent = HumanAgent("A", 1, console, RandomAgent(random.Random(0)), timeout=0.05)
    state = initial_state(1)
    action = agent.choose(observe(state, "A"), legal_actions(state, "A"))
    assert action in legal_actions(state, "A") and agent.source == "timeout"


def test_the_third_unanswered_prompt_in_a_row_ends_the_game() -> None:
    chat = io.StringIO()
    console = Console(LineReader(io.StringIO("")), chat)
    agent = HumanAgent("A", 1, console, ScriptedAgent([Action("skip")] * 5), None, 3)
    state = initial_state(1)
    ask = lambda: agent.choose(observe(state, "A"), legal_actions(state, "A"))  # noqa: E731
    assert ask() == Action("skip") and ask() == Action("skip"), "the first two are played for them"
    with pytest.raises(StopGame):
        ask()
    assert "did not answer 3 prompts in a row" in chat.getvalue()


def test_an_answer_resets_the_unanswered_count() -> None:
    _, agent, _ = _ask("")  # one unanswered prompt
    assert agent.unanswered == 1
    console = Console(LineReader(io.StringIO("lift 1\n")), io.StringIO())
    agent.console = console
    state = initial_state(1)
    assert agent.choose(observe(state, "A"), legal_actions(state, "A")) == Action("lift", 1)
    assert agent.unanswered == 0


def test_ctrl_c_at_the_prompt_ends_the_game() -> None:
    class Interrupts(LineReader):
        def get(self, timeout: float | None) -> str | None:
            raise KeyboardInterrupt

    chat = io.StringIO()
    reader = Interrupts(io.StringIO())
    agent = HumanAgent("A", 1, Console(reader, chat), ScriptedAgent([Action("skip")]))
    state = initial_state(1)
    with pytest.raises(StopGame):
        agent.choose(observe(state, "A"), legal_actions(state, "A"))
    assert "game ended: interrupted" in chat.getvalue()


@pytest.mark.parametrize("word", ["quit", "q", "exit"])
def test_quit_words_end_the_game(word: str) -> None:
    with pytest.raises(StopGame):
        _ask(f"{word}\n")
