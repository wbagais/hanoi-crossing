"""How a move is chosen: an ``Observation`` and the legal actions in, an ``Action`` out.

An agent never sees the full ``State`` (R3, T8) - this is the contract an RL policy,
an LLM, or a network client would implement. A person at the keyboard is a frontend
concern and lives in ``human``.

An agent is anything with ``choose(observation, legal) -> Action`` and a ``source``
string labelling the move it just chose; the runner copies that label onto the turn.
"""

from __future__ import annotations

import random
from collections.abc import Iterable, Sequence

from .engine import Action, Observation


class RandomAgent:
    """Uniform choice among the legal actions (T3)."""

    source = "random"

    def __init__(self, rng: random.Random) -> None:
        self.rng = rng

    def choose(self, observation: Observation, legal: Sequence[Action]) -> Action:
        if not legal:
            raise RuntimeError("no legal actions to choose from")
        return self.rng.choice(list(legal))


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
