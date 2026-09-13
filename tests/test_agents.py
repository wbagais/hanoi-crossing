"""Agents choose moves from an Observation and the legal list only (T8, R3)."""

import random

import pytest
from hanoi_crossing.agents import ExternalAgent, RandomAgent, ScriptedAgent, Timeout

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


def test_random_agent_no_skip_avoids_skip_unless_only_option() -> None:
    agent = RandomAgent(random.Random(0), allow_skip=False)
    for _ in range(50):
        assert agent.choose(_obs(), LEGAL_START) == Action("lift", 1)
    assert agent.choose(_obs(), [Action("skip")]) == Action("skip")


def test_random_agent_never_receives_a_state() -> None:
    class Spy(RandomAgent):
        def choose(self, observation, legal):  # type: ignore[override]
            assert isinstance(observation, Observation)
            assert not hasattr(observation, "hands")
            return super().choose(observation, legal)

    assert Spy(random.Random(0)).choose(_obs(), LEGAL_START) in LEGAL_START


def test_random_agent_kind_and_fallback_flag() -> None:
    agent = RandomAgent(random.Random(0))
    assert agent.kind == "random" and agent.last_fell_back is False


# --- ScriptedAgent ---------------------------------------------------------------


def test_scripted_agent_returns_actions_in_order_ignoring_legal() -> None:
    script = [Action("lift", 1), Action("place", 2), Action("place", 2)]
    agent = ScriptedAgent(script)
    assert agent.kind == "scripted"
    assert [agent.choose(_obs(), []) for _ in range(3)] == script


def test_scripted_agent_raises_when_exhausted() -> None:
    agent = ScriptedAgent([Action("skip")])
    agent.choose(_obs(), LEGAL_START)
    with pytest.raises(RuntimeError):
        agent.choose(_obs(), LEGAL_START)


# --- ExternalAgent ---------------------------------------------------------------


def test_external_agent_returns_what_ask_returns() -> None:
    seen: list[tuple[Observation, list[Action], float | None]] = []

    def ask(observation: Observation, legal: list[Action], timeout: float | None) -> Action:
        seen.append((observation, legal, timeout))
        return Action("skip")

    agent = ExternalAgent(ask, timeout=5.0)
    assert agent.kind == "human"
    assert agent.choose(_obs(), LEGAL_START) == Action("skip")
    assert seen == [(_obs(), LEGAL_START, 5.0)]
    assert agent.last_fell_back is False


def test_external_agent_uses_fallback_on_timeout_and_flags_it() -> None:
    def ask(observation: Observation, legal: list[Action], timeout: float | None) -> Action:
        raise Timeout

    agent = ExternalAgent(ask, timeout=0.01, fallback=RandomAgent(random.Random(0)))
    action = agent.choose(_obs(), LEGAL_START)
    assert action in LEGAL_START
    assert agent.last_fell_back is True
    # flag resets on the next successful answer
    agent2 = ExternalAgent(lambda o, lg, t: Action("skip"), timeout=1, fallback=agent)
    agent2.choose(_obs(), LEGAL_START)
    assert agent2.last_fell_back is False


def test_external_agent_treats_none_as_no_answer() -> None:
    agent = ExternalAgent(lambda o, lg, t: None, fallback=ScriptedAgent([Action("skip")]))
    assert agent.choose(_obs(), LEGAL_START) == Action("skip")
    assert agent.last_fell_back is True


def test_external_agent_without_fallback_raises_on_timeout() -> None:
    def ask(observation: Observation, legal: list[Action], timeout: float | None) -> Action:
        raise Timeout

    with pytest.raises(RuntimeError):
        ExternalAgent(ask, timeout=0.01).choose(_obs(), LEGAL_START)


def test_external_agent_kind_can_be_named() -> None:
    assert ExternalAgent(lambda o, lg, t: Action("skip"), kind="llm").kind == "llm"
