"""How a move is chosen: an ``Observation`` and the legal actions in, an ``Action`` out.

An agent never sees the full ``State`` (R3, T8) - this is the contract an RL policy,
an LLM, or a network client would implement. A person at the keyboard is a frontend
concern and lives in ``human``.
"""

from __future__ import annotations

import random
from collections.abc import Iterable, Sequence
from typing import Protocol

from .engine import Action, Observation


class Agent(Protocol):
    """``source`` labels the move just chosen; the runner copies it onto the turn."""

    source: str

    def choose(self, observation: Observation, legal: Sequence[Action]) -> Action: ...


class RandomAgent:
    """Uniform choice among the legal actions (T3)."""

    source = "random"

    def __init__(self, rng: random.Random, allow_skip: bool = True) -> None:
        self.rng = rng
        self.allow_skip = allow_skip

    def choose(self, observation: Observation, legal: Sequence[Action]) -> Action:
        choices = list(legal)
        if not self.allow_skip and len(choices) > 1:
            choices = [a for a in choices if a.verb != "skip"]
        if not choices:
            raise RuntimeError("no legal actions to choose from")
        return self.rng.choice(choices)


class ScriptedAgent:
    """Replays recorded actions, legal or not, so a recorded illegal move is wasted again."""

    source = "scripted"

    def __init__(self, actions: Iterable[Action]) -> None:
        self._actions = iter(actions)

    def choose(self, observation: Observation, legal: Sequence[Action]) -> Action:
        try:
            return next(self._actions)
        except StopIteration:
            raise RuntimeError("scripted agent has no more moves") from None
