"""The one game loop.

``play_turn`` plays a single turn for one player with one agent; ``run`` loops it
over an external schedule. Replay, random play, human play, and continuing an
unfinished game are all ``run`` with different agents and start states; there is
no other loop in the codebase.

The runner owns what the engine deliberately does not: the schedule (R10), the
turn log, and the two non-winning exits of interpretation I5: ``unfinished`` when
the schedule is exhausted and ``stalemate`` when the same position with the same
player to move has occurred ``repetition_limit`` times.
"""

from __future__ import annotations

import random
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Literal

from .agents import Agent
from .engine import PLAYERS, Action, Outcome, Player, State, legal_actions, observe, step, winner

Status = Literal["won", "unfinished", "stalemate"]


class StopGame(Exception):
    """Raised from inside an agent (or the function it asks) to end the game now.

    ``run`` catches it and returns the game so far as ``unfinished``, so a quit,
    an interrupt, or an abandoned human turn still yields a result that can be
    rendered, saved, and continued later.
    """


@dataclass(frozen=True)
class Turn:
    """One played turn. ``source`` is the agent kind, or ``timeout`` when a
    fallback agent answered for an external agent."""

    index: int
    player: Player
    action: Action
    outcome: Outcome
    source: str


@dataclass(frozen=True)
class RunResult:
    final_state: State
    turns: tuple[Turn, ...]
    status: Status
    winner: Player | None
    unplayed: int


# --- schedules -------------------------------------------------------------------


def from_string(text: str) -> tuple[Player, ...]:
    """``"ABA"`` -> ``("A", "B", "A")``. Only A and B are allowed."""
    bad = sorted(set(text) - set(PLAYERS))
    if bad:
        raise ValueError(f"schedule may only contain A and B, got {bad}")
    return tuple(text)  # type: ignore[return-value]


def to_string(schedule: Sequence[Player]) -> str:
    return "".join(schedule)


def repeat(pattern: str, length: int) -> tuple[Player, ...]:
    """Repeat ``pattern`` (e.g. ``"AB"``, ``"AAB"``) to exactly ``length`` entries."""
    if not pattern:
        raise ValueError("schedule pattern must not be empty")
    players = from_string(pattern)
    return tuple(players[i % len(players)] for i in range(length))


def rotate_to(pattern: str, first: Player) -> str:
    """Rotate ``pattern`` so it starts at the first occurrence of ``first``."""
    from_string(pattern)
    if first not in pattern:
        raise ValueError(f"player {first} does not appear in schedule pattern {pattern!r}")
    i = pattern.index(first)
    return pattern[i:] + pattern[:i]


def random_schedule(rng: random.Random, length: int) -> tuple[Player, ...]:
    return tuple(rng.choice(PLAYERS) for _ in range(length))


# --- the loop --------------------------------------------------------------------


def play_turn(state: State, player: Player, agent: Agent, index: int) -> tuple[State, Turn]:
    """Observe -> choose -> step -> record, for one schedule entry."""
    observation = observe(state, player)
    legal = legal_actions(state, player)
    action = agent.choose(observation, legal)
    new_state, outcome = step(state, player, action)
    source = "timeout" if agent.last_fell_back else agent.kind
    return new_state, Turn(index, player, action, outcome, source)


def run(
    state: State,
    schedule: Sequence[Player],
    agents: Mapping[Player, Agent],
    repetition_limit: int | None = None,
    on_turn: Callable[[Turn, State], None] | None = None,
) -> RunResult:
    """Play ``schedule`` from ``state``. Stops at a win, a stalemate, or the end.

    Before each entry the game status is checked: a winner ends the game with
    the remaining entries counted as unplayed; with ``repetition_limit`` set, a
    (state, player-to-move) pair seen that many times ends it as a stalemate.
    ``on_turn`` is called after every played turn with the turn and the new
    state, so a frontend can print live without owning the loop. An agent may
    raise ``StopGame`` to end the game early; the result is then ``unfinished``.
    """
    turns: list[Turn] = []
    seen: Counter[tuple[State, Player]] = Counter()
    for i, player in enumerate(schedule):
        won = winner(state)
        if won is not None:
            return RunResult(state, tuple(turns), "won", won, len(schedule) - i)
        if repetition_limit:
            seen[(state, player)] += 1
            if seen[(state, player)] >= repetition_limit:
                return RunResult(state, tuple(turns), "stalemate", None, len(schedule) - i)
        try:
            state, turn = play_turn(state, player, agents[player], i + 1)
        except StopGame:
            return RunResult(state, tuple(turns), "unfinished", None, len(schedule) - i)
        turns.append(turn)
        if on_turn is not None:
            on_turn(turn, state)
    won = winner(state)
    return RunResult(state, tuple(turns), "won" if won else "unfinished", won, 0)
