"""Agents choose moves from an Observation and the legal list only (T8, R3)."""

import random

import pytest

from hanoi_crossing.agents import RandomAgent, ScriptedAgent
from hanoi_crossing.engine import Action, Observation, initial_state, legal_actions, observe

LEGAL_START = [Action("lift", 1), Action("skip")]


def _obs() -> Observation:
    return observe(initial_state(2), "A")


# --- RandomAgent -----------------------------------------------------------------


def test_random_agent_picks_from_legal_only() -> None:
    agent = RandomAgent(random.Random(0))
    for _ in range(50):
        assert agent.choose(_obs(), LEGAL_START) in LEGAL_START


def test_random_agent_is_seed_reproducible() -> None:
    legal = legal_actions(initial_state(3), "A")
    a = [RandomAgent(random.Random(7)).choose(_obs(), legal) for _ in range(1)]
    seq1 = [RandomAgent(random.Random(7)).choose(_obs(), legal) for _ in range(20)]
    seq2 = [RandomAgent(random.Random(7)).choose(_obs(), legal) for _ in range(20)]
    assert a[0] == seq1[0] and seq1 == seq2
    agent1, agent2 = RandomAgent(random.Random(3)), RandomAgent(random.Random(3))
    assert [agent1.choose(_obs(), legal) for _ in range(30)] == [
        agent2.choose(_obs(), legal) for _ in range(30)
    ]


def test_random_agent_refuses_an_empty_legal_list() -> None:
    with pytest.raises(RuntimeError):
        RandomAgent(random.Random(0)).choose(_obs(), [])


def test_random_agent_never_receives_a_state() -> None:
    class Spy(RandomAgent):
        def choose(self, observation, legal):  # type: ignore[override]
            assert isinstance(observation, Observation)
            assert not hasattr(observation, "hands")
            return super().choose(observation, legal)

    assert Spy(random.Random(0)).choose(_obs(), LEGAL_START) in LEGAL_START


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
