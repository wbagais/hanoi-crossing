"""Agents choose moves from an Observation and the legal list only (T8, R3)."""

import random

import pytest

from hanoi_crossing.agents import RandomAgent, ScriptedAgent
from hanoi_crossing.engine import Action, Observation, initial_state, legal_actions, observe
from hanoi_crossing.runner import play_turn

LEGAL_START = [Action("lift", 1), Action("skip")]


def _obs() -> Observation:
    return observe(initial_state(2), "A")


# --- RandomAgent -----------------------------------------------------------------


def test_random_agent_picks_from_legal_only() -> None:
    agent = RandomAgent(random.Random(0))
    for _ in range(50):
        assert agent.choose(_obs(), LEGAL_START) in LEGAL_START


def test_random_agent_is_seed_reproducible_and_actually_random() -> None:
    legal = legal_actions(initial_state(3), "A")
    agent1, agent2 = RandomAgent(random.Random(3)), RandomAgent(random.Random(3))
    seq1 = [agent1.choose(_obs(), legal) for _ in range(30)]
    seq2 = [agent2.choose(_obs(), legal) for _ in range(30)]
    assert seq1 == seq2, "same seed, same sequence"
    assert len(set(seq1)) > 1, "a sequence of one repeated action is not a random choice"
    assert seq1 != [RandomAgent(random.Random(4)).choose(_obs(), legal) for _ in range(30)]


def test_random_agent_refuses_an_empty_legal_list() -> None:
    with pytest.raises(RuntimeError):
        RandomAgent(random.Random(0)).choose(_obs(), [])


def test_an_agent_is_handed_a_view_not_the_board() -> None:
    """The R3/T8 seam: what the runner passes in, not what this test passes in."""
    seen: list[object] = []

    class Spy:
        source = "spy"

        def choose(self, observation, legal):  # noqa: ANN001, ANN202
            seen.append(observation)
            return legal[0]

    state = initial_state(2)
    play_turn(state, "A", Spy(), index=1)
    assert seen == [observe(state, "A")]
    assert isinstance(seen[0], Observation) and not hasattr(seen[0], "hands")


def test_random_agent_source() -> None:
    assert RandomAgent(random.Random(0)).source == "random"


# --- ScriptedAgent ---------------------------------------------------------------


def test_scripted_agent_returns_actions_in_order_ignoring_legal() -> None:
    script = [Action("lift", 1), Action("place", 2), Action("place", 2)]
    agent = ScriptedAgent(script)
    assert agent.source == "scripted"
    assert [agent.choose(_obs(), []) for _ in range(3)] == script


def test_scripted_agent_raises_when_exhausted() -> None:
    agent = ScriptedAgent([Action("skip")])
    agent.choose(_obs(), LEGAL_START)
    with pytest.raises(RuntimeError):
        agent.choose(_obs(), LEGAL_START)
