"""The one game loop: ``play_turn`` for one turn, ``run`` over a schedule.

Replay, random play, human play and continuing a game are all ``run`` with
different agents and start states. The runner owns what the engine does not: the
schedule (R10), the turn log, and the non-winning exits ``unfinished`` and
``stalemate`` (I5).
"""

from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from .engine import PLAYERS, Action, Outcome, State, legal_actions, observe, step, winner


class StopGame(Exception):
    """Raised inside an agent to end the game now; ``run`` returns it as ``unfinished``."""


@dataclass(frozen=True)
class Turn:
    """One played turn. ``source`` is the label the agent gave its move."""

    index: int
    player: str
    action: Action
    outcome: Outcome
    source: str


@dataclass(frozen=True)
class RunResult:
    final_state: State
    turns: tuple[Turn, ...]
    status: str  # won | unfinished | stalemate
    winner: str | None
    unplayed: int


# --- schedules -------------------------------------------------------------------


def parse_schedule(text: str) -> tuple[str, ...]:
    """``"ABA"`` -> ``("A", "B", "A")``. Only A and B are allowed."""
    bad = sorted(set(text) - set(PLAYERS))
    if bad:
        raise ValueError(f"schedule may only contain A and B, got {bad}")
    return tuple(text)


def repeat(pattern: str, length: int) -> tuple[str, ...]:
    """Repeat ``pattern`` (e.g. ``"AB"``, ``"AAB"``) to exactly ``length`` entries."""
    players = parse_schedule(pattern)
    if not players:
        raise ValueError("schedule pattern must not be empty")
    return tuple(players[i % len(players)] for i in range(length))


def rotate_to(pattern: str, first: str) -> str:
    """Rotate ``pattern`` so it starts at the first occurrence of ``first``."""
    parse_schedule(pattern)
    if first not in pattern:
        raise ValueError(f"player {first} does not appear in schedule pattern {pattern!r}")
    i = pattern.index(first)
    return pattern[i:] + pattern[:i]


# --- the loop --------------------------------------------------------------------


def play_turn(state: State, player: str, agent: Any, index: int) -> tuple[State, Turn]:
    """Observe -> choose -> step -> record, for one schedule entry (see ``agents``)."""
    action = agent.choose(observe(state, player), legal_actions(state, player))
    new_state, outcome = step(state, player, action)
    return new_state, Turn(index, player, action, outcome, agent.source)


def run(
    state: State,
    schedule: Sequence[str],
    agents: Mapping[str, Any],
    repetition_limit: int | None = None,
    on_turn: Callable[[Turn, State], None] | None = None,
) -> RunResult:
    """Play ``schedule`` from ``state`` until a win, a stalemate, or the last entry.

    The status is checked before each entry, so an opponent's winning move ends the
    game with the rest counted unplayed. ``repetition_limit`` ends a repeated
    (state, player-to-move) pair as a stalemate. ``on_turn`` lets a frontend print
    each turn without owning the loop.
    """
    turns: list[Turn] = []
    seen: Counter[tuple[State, str]] = Counter()
    for i, player in enumerate(schedule):
        unplayed = len(schedule) - i
        won = winner(state)
        if won is not None:
            return RunResult(state, tuple(turns), "won", won, unplayed)
        if repetition_limit:
            seen[(state, player)] += 1
            if seen[(state, player)] >= repetition_limit:
                return RunResult(state, tuple(turns), "stalemate", None, unplayed)
        try:
            state, turn = play_turn(state, player, agents[player], i + 1)
        except StopGame:
            return RunResult(state, tuple(turns), "unfinished", None, unplayed)
        turns.append(turn)
        if on_turn is not None:
            on_turn(turn, state)
    won = winner(state)
    return RunResult(state, tuple(turns), "won" if won else "unfinished", won, 0)
