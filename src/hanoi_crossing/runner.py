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

from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Literal

from .agents import Agent
from .engine import PLAYERS, Action, Outcome, Player, State, legal_actions, observe, step, winner

Status = Literal["won", "unfinished", "stalemate"]


class StopGame(Exception):
    """Raised from inside an agent to end the game now.

    ``run`` catches it and returns the game so far as ``unfinished``, so a quit,
    an interrupt, or an abandoned human turn still yields a result that can be
    rendered, saved, and continued later.
    """


@dataclass(frozen=True)
class Turn:
    """One played turn. ``source`` is the label the agent gave its move."""

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


def parse_schedule(text: str) -> tuple[Player, ...]:
    """``"ABA"`` -> ``("A", "B", "A")``. Only A and B are allowed."""
    bad = sorted(set(text) - set(PLAYERS))
    if bad:
        raise ValueError(f"schedule may only contain A and B, got {bad}")
    return tuple(text)  # type: ignore[return-value]


def repeat(pattern: str, length: int) -> tuple[Player, ...]:
    """Repeat ``pattern`` (e.g. ``"AB"``, ``"AAB"``) to exactly ``length`` entries."""
    players = parse_schedule(pattern)
    if not players:
        raise ValueError("schedule pattern must not be empty")
    return tuple(players[i % len(players)] for i in range(length))


def rotate_to(pattern: str, first: Player) -> str:
    """Rotate ``pattern`` so it starts at the first occurrence of ``first``."""
    parse_schedule(pattern)
    if first not in pattern:
        raise ValueError(f"player {first} does not appear in schedule pattern {pattern!r}")
    i = pattern.index(first)
    return pattern[i:] + pattern[:i]


# --- the loop --------------------------------------------------------------------


def play_turn(state: State, player: Player, agent: Agent, index: int) -> tuple[State, Turn]:
    """Observe -> choose -> step -> record, for one schedule entry."""
    action = agent.choose(observe(state, player), legal_actions(state, player))
    new_state, outcome = step(state, player, action)
    return new_state, Turn(index, player, action, outcome, agent.source)


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
