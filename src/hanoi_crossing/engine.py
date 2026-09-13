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


def winner(state: State) -> Player | None:
    """The player who has won, if any (R11, I1). Checked A then B.

    A player wins when their hand is empty, their pole 1 and the shared pole are
    empty, and their pole 3 holds at least one disk. At most one player can
    satisfy this in any reachable state, so the first match is the winner.
    """
    for p in PLAYERS:
        if (
            state.hands[p] is None
            and not state.poles[pole_key(p, 1)]
            and not state.poles[SHARED]
            and state.poles[pole_key(p, 3)]
        ):
            return p
    return None


def _validate(player: object, action: object) -> None:
    """Raise ValueError for input that is not even a well-formed move (I3)."""
    _require_player(player)
    if not isinstance(action, Action):
        raise ValueError(f"action must be an Action, got {action!r}")
    if action.verb == "skip":
        if action.pole is not None:
            raise ValueError("skip takes no pole")
    elif action.verb in ("lift", "place"):
        if action.pole not in (1, 2, 3):
            raise ValueError(f"pole must be 1, 2 or 3, got {action.pole!r}")
    else:
        raise ValueError(f"unknown verb {action.verb!r}")


def _illegal_reason(state: State, player: Player, action: Action) -> str | None:
    """Why a well-formed action is illegal in this position, or None if legal."""
    if action.verb == "skip":
        return None
    key = pole_key(player, action.pole)  # type: ignore[arg-type]
    held = state.hands[player]
    if action.verb == "lift":
        if held is not None:
            return "hand is not empty"
        if not state.poles[key]:
            return f"pole {action.pole} is empty"
        return None
    if held is None:
        return "hand is empty"
    pole = state.poles[key]
    if pole and pole[-1] < held:
        return f"disk {held} cannot go on disk {pole[-1]}"
    return None


def legal_actions(state: State, player: Player) -> list[Action]:
    """Actions ``step`` would accept now, in ALL_ACTIONS order. Empty once the game is over."""
    _require_player(player)
    if winner(state) is not None:
        return []
    return [a for a in ALL_ACTIONS if _illegal_reason(state, player, a) is None]


def step(state: State, player: Player, action: Action) -> tuple[State, Outcome]:
    """Apply one action for ``player``.

    Order of checks: game already over -> malformed input -> illegal here ->
    apply -> check both players for a win. An illegal action returns the very
    same ``state`` object so the caller can detect a wasted turn cheaply (R9).
    """
    _validate(player, action)
    already = winner(state)
    if already is not None:
        return state, Outcome(False, "game is over", already, True)
    reason = _illegal_reason(state, player, action)
    if reason is not None:
        return state, Outcome(False, reason, None, False)
    if action.verb == "skip":
        return state, Outcome(True, None, None, False)
    key = pole_key(player, action.pole)  # type: ignore[arg-type]
    poles = dict(state.poles)
    hands = dict(state.hands)
    if action.verb == "lift":
        hands[player] = poles[key][-1]
        poles[key] = poles[key][:-1]
    else:
        poles[key] = poles[key] + (hands[player],)  # type: ignore[operator]
        hands[player] = None
    new = State(n=state.n, poles=poles, hands=hands)
    won = winner(new)
    return new, Outcome(True, None, won, won is not None)
