"""How a move is chosen.

An agent receives only what a player may see, an ``Observation`` and the list of
legal actions, and returns one ``Action``. It never sees the full ``State`` (R3,
T8). This is exactly the contract an RL policy, an LLM, or a network client would
implement; the random agent proves the seam.

Three kinds are provided:

* ``RandomAgent``: uniform pick from the legal list, seeded by the caller.
* ``ScriptedAgent``: replays recorded moves verbatim, ignoring legality, so a
  recorded illegal move is reproduced as a wasted turn.
* ``ExternalAgent``: the move comes from an injected function (a stdin prompt, a
  UI handler, a model call). If the function times out, an optional fallback agent
  answers instead and the choice is flagged so the runner can label it.

No I/O, clock, or randomness lives here beyond the injected ``random.Random``.
"""

from __future__ import annotations

import random
from collections.abc import Callable, Iterable, Sequence
from typing import Protocol

from .engine import Action, Observation

AskFn = Callable[[Observation, Sequence[Action], "float | None"], "Action | None"]


class Timeout(Exception):
    """Raised by an ``ask`` function when no answer arrived in time."""


class Agent(Protocol):
    """The external-agent contract. ``kind`` labels turns; ``last_fell_back`` marks
    a choice made by a fallback agent instead of this one."""

    kind: str
    last_fell_back: bool

    def choose(self, observation: Observation, legal: Sequence[Action]) -> Action: ...


class RandomAgent:
    """Uniform choice among the legal actions (T3)."""

    kind = "random"

    def __init__(self, rng: random.Random, allow_skip: bool = True) -> None:
        self.rng = rng
        self.allow_skip = allow_skip
        self.last_fell_back = False

    def choose(self, observation: Observation, legal: Sequence[Action]) -> Action:
        choices = list(legal)
        if not self.allow_skip and len(choices) > 1:
            choices = [a for a in choices if a.verb != "skip"]
        if not choices:
            raise RuntimeError("no legal actions to choose from")
        return self.rng.choice(choices)


class ScriptedAgent:
    """Replays a fixed sequence of actions, one per call, legal or not."""

    kind = "scripted"

    def __init__(self, actions: Iterable[Action]) -> None:
        self._actions = iter(actions)
        self.last_fell_back = False

    def choose(self, observation: Observation, legal: Sequence[Action]) -> Action:
        try:
            return next(self._actions)
        except StopIteration:
            raise RuntimeError("scripted agent has no more moves") from None


class ExternalAgent:
    """A move supplied from outside through ``ask(observation, legal, timeout)``.

    ``ask`` owns the waiting: it returns an ``Action``, or ``None`` / raises
    ``Timeout`` when the answer did not arrive within ``timeout`` seconds. Then
    ``fallback.choose`` answers and ``last_fell_back`` is set for this turn.
    """

    def __init__(
        self,
        ask: AskFn,
        timeout: float | None = None,
        fallback: Agent | None = None,
        kind: str = "human",
    ) -> None:
        self.ask = ask
        self.timeout = timeout
        self.fallback = fallback
        self.kind = kind
        self.last_fell_back = False

    def choose(self, observation: Observation, legal: Sequence[Action]) -> Action:
        self.last_fell_back = False
        try:
            action = self.ask(observation, legal, self.timeout)
        except Timeout:
            action = None
        if action is not None:
            return action
        if self.fallback is None:
            raise RuntimeError("no answer in time and no fallback agent configured")
        self.last_fell_back = True
        return self.fallback.choose(observation, legal)
