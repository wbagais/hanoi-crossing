"""Hanoi Crossing rules engine.

Pure functions over an immutable ``State``. The engine holds nothing between
calls, performs no I/O, uses no randomness, and keeps no turn counter: the
caller passes the acting player on every call, so any turn order works (R10).

Interpretations of the spec (see docs/REQUIREMENTS.md, I1-I7):

* A player wins only if pole 3 holds at least one disk; all-empty is not a win.
* Actions name poles 1, 2, 3 from the acting player's side. The opponent's
  private poles cannot be expressed, so they cannot be touched (R3).
* Malformed input raises ``ValueError``. A well-formed but illegal move returns
  the *same* state object with a reason; the turn is wasted (R9).
* A finished game rejects every further action, including skip.
* Disk ownership is not tracked after setup: any player may lift any top disk
  from the shared pole and place it on their own poles (R2, R8).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal

Player = Literal["A", "B"]
Verb = Literal["lift", "place", "skip"]
PoleIndex = Literal[1, 2, 3]

PLAYERS: tuple[Player, ...] = ("A", "B")
POLE_KEYS: tuple[str, ...] = ("1a", "2", "3a", "1b", "3b")
SHARED = "2"

_PRIVATE_KEYS: dict[tuple[Player, int], str] = {
    ("A", 1): "1a",
    ("A", 3): "3a",
    ("B", 1): "1b",
    ("B", 3): "3b",
}


@dataclass(frozen=True)
class Action:
    """One move. ``pole`` is required for lift/place and must be None for skip."""

    verb: Verb
    pole: PoleIndex | None = None


ALL_ACTIONS: tuple[Action, ...] = (
    Action("lift", 1),
    Action("lift", 2),
    Action("lift", 3),
    Action("place", 1),
    Action("place", 2),
    Action("place", 3),
    Action("skip"),
)
"""The fixed action space, size 7. Index-stable so a policy can output an index."""


@dataclass(frozen=True)
class State:
    """Full board. ``poles`` maps POLE_KEYS to disks bottom->top; disks are sizes."""

    n: int
    poles: Mapping[str, tuple[int, ...]]
    hands: Mapping[Player, int | None]

    def __post_init__(self) -> None:
        object.__setattr__(self, "poles", {k: tuple(v) for k, v in self.poles.items()})
        object.__setattr__(self, "hands", dict(self.hands))

    def __hash__(self) -> int:
        return hash(
            (
                self.n,
                tuple(self.poles[k] for k in POLE_KEYS),
                tuple(self.hands[p] for p in PLAYERS),
            )
        )


@dataclass(frozen=True)
class Observation:
    """What one player may see: own poles 1 and 3, the shared pole as 2, own hand."""

    poles: Mapping[int, tuple[int, ...]]
    hand: int | None


@dataclass(frozen=True)
class Outcome:
    """Result of one ``step``. ``winner``/``done`` reflect the returned state."""

    legal: bool
    reason: str | None
    winner: Player | None
    done: bool


def _require_player(player: object) -> Player:
    if player not in PLAYERS:
        raise ValueError(f"unknown player {player!r}; expected one of {PLAYERS}")
    return player  # type: ignore[return-value]


def pole_key(player: Player, pole: int) -> str:
    """Map a player-relative pole number (1, 2, 3) to a State pole key."""
    _require_player(player)
    if pole == 2:
        return SHARED
    try:
        return _PRIVATE_KEYS[(player, pole)]
    except KeyError:
        raise ValueError(f"pole must be 1, 2 or 3, got {pole!r}") from None


def initial_state(n: int) -> State:
    """Starting position: A has odd disks 2n-1..1 on 1a, B has even 2n..2 on 1b (R1, R4)."""
    if not isinstance(n, int) or isinstance(n, bool) or n < 1:
        raise ValueError(f"n must be a positive integer, got {n!r}")
    return State(
        n=n,
        poles={
            "1a": tuple(range(2 * n - 1, 0, -2)),
            SHARED: (),
            "3a": (),
            "1b": tuple(range(2 * n, 0, -2)),
            "3b": (),
        },
        hands={"A": None, "B": None},
    )


def observe(state: State, player: Player) -> Observation:
    """The partial view a player is allowed to see (R3). Never the opponent's side."""
    _require_player(player)
    return Observation(
        poles={
            1: state.poles[pole_key(player, 1)],
            2: state.poles[SHARED],
            3: state.poles[pole_key(player, 3)],
        },
        hand=state.hands[player],
    )
