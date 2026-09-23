"""Hanoi Crossing rules engine: pure functions over an immutable ``State``.

The caller names the acting player on every call, so any turn order works (R10).
Actions are player-relative, which is also what hides the opponent's side (R3).
Rule interpretations I1-I7 are in docs/REQUIREMENTS.md, the reasons in
docs/DECISIONS.md.
"""

from collections.abc import Mapping
from dataclasses import dataclass

PLAYERS = ("A", "B")
VERBS = ("lift", "place", "skip")
POLES = (1, 2, 3)
SHARED = "2"  # the middle pole both players can reach
POLE_KEYS = ("1a", SHARED, "3a", "1b", "3b")  # serialization order

SIDES: dict[str, dict[int, str]] = {
    "A": {1: "1a", 2: SHARED, 3: "3a"},
    "B": {1: "1b", 2: SHARED, 3: "3b"},
}
"""Each player's poles 1, 2, 3 as State pole keys. The one place the board layout lives."""


def is_positive_int(value: object) -> bool:
    """True for 1, 2, 3, ...; False for 0, floats, strings, and bools."""
    return isinstance(value, int) and not isinstance(value, bool) and value >= 1


def check(ok: object, message: str, error: type[Exception] = ValueError) -> None:
    """Raise ``error(message)`` unless ``ok``. One line per rule, wherever input is validated."""
    if not ok:
        raise error(message)


@dataclass(frozen=True)
class Action:
    """One move, checked on construction: lift/place need a pole, skip must not have one (I3)."""

    verb: str
    pole: int | None = None

    def __post_init__(self) -> None:
        check(self.verb in VERBS, f"unknown verb {self.verb!r}")
        if self.verb == "skip":
            check(self.pole is None, "skip takes no pole")
        else:
            check(self.pole in POLES, f"pole must be 1, 2 or 3, got {self.pole!r}")

    def __str__(self) -> str:
        return self.verb if self.pole is None else f"{self.verb} {self.pole}"

    @classmethod
    def parse(cls, text: object) -> "Action":
        """``"lift 1"`` / ``"place 3"`` / ``"skip"`` -> Action. Inverse of ``str``."""
        parts = text.split() if isinstance(text, str) else []
        if parts == ["skip"]:
            return cls("skip")
        if len(parts) == 2 and parts[0] in ("lift", "place") and parts[1] in ("1", "2", "3"):
            return cls(parts[0], int(parts[1]))
        raise ValueError(f"bad move {text!r}; expected 'lift N', 'place N' (N=1..3) or 'skip'")


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
    hands: Mapping[str, int | None]

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
    """Result of one ``step``. ``winner``/``done`` reflect the returned state.

    ``disk`` is the disk that was lifted or placed; None for skip and illegal moves.
    """

    legal: bool
    reason: str | None
    winner: str | None
    done: bool
    disk: int | None = None


def _require_player(player: object) -> str:
    if player not in PLAYERS:
        raise ValueError(f"unknown player {player!r}; expected one of {PLAYERS}")
    return player


def pole_key(player: str, pole: int) -> str:
    """Map a player-relative pole number (1, 2, 3) to a State pole key."""
    try:
        return SIDES[_require_player(player)][pole]
    except KeyError:
        raise ValueError(f"pole must be 1, 2 or 3, got {pole!r}") from None


def initial_state(n: int) -> State:
    """Starting position: A has odd disks 2n-1..1 on 1a, B has even 2n..2 on 1b (R1, R4)."""
    check(is_positive_int(n), f"n must be a positive integer, got {n!r}")
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


def observe(state: State, player: str) -> Observation:
    """The partial view a player is allowed to see (R3). Never the opponent's side."""
    side = SIDES[_require_player(player)]
    return Observation(
        poles={i: state.poles[key] for i, key in side.items()},
        hand=state.hands[player],
    )


def winner(state: State) -> str | None:
    """The player whose hand, pole 1 and shared pole are empty and pole 3 is not (R11, I1).

    At most one player can satisfy this in a reachable state, so the first match wins.
    """
    for p in PLAYERS:
        side = SIDES[p]
        if (
            state.hands[p] is None
            and not state.poles[side[1]]
            and not state.poles[SHARED]
            and state.poles[side[3]]
        ):
            return p
    return None


def _illegal_reason(state: State, player: str, action: Action) -> str | None:
    """Why a well-formed action is illegal in this position, or None if legal."""
    if action.verb == "skip":
        return None
    pole = state.poles[pole_key(player, action.pole)]
    held = state.hands[player]
    if action.verb == "lift":
        if held is not None:
            return "hand is not empty"
        if not pole:
            return f"pole {action.pole} is empty"
        return None
    if held is None:
        return "hand is empty"
    if pole and pole[-1] < held:
        return f"disk {held} cannot go on disk {pole[-1]}"
    return None


def legal_actions(state: State, player: str) -> list[Action]:
    """Actions ``step`` would accept now, in ALL_ACTIONS order. Empty once the game is over."""
    _require_player(player)
    if winner(state) is not None:
        return []
    return [a for a in ALL_ACTIONS if _illegal_reason(state, player, a) is None]


def step(state: State, player: str, action: Action) -> tuple[State, Outcome]:
    """Apply one action: over? -> malformed? -> illegal here? -> apply -> who won?

    An illegal action returns the very same ``state`` object, so a wasted turn is
    cheap to detect (R9).
    """
    _require_player(player)
    check(isinstance(action, Action), f"action must be an Action, got {action!r}")
    already = winner(state)
    if already is not None:
        return state, Outcome(False, "game is over", already, True)
    reason = _illegal_reason(state, player, action)
    if reason is not None:
        return state, Outcome(False, reason, None, False)
    if action.verb == "skip":
        return state, Outcome(True, None, None, False)
    key = pole_key(player, action.pole)
    poles = dict(state.poles)
    hands = dict(state.hands)
    if action.verb == "lift":
        disk = poles[key][-1]
        poles[key] = poles[key][:-1]
        hands[player] = disk
    else:
        disk = hands[player]
        poles[key] = poles[key] + (disk,)
        hands[player] = None
    new = State(n=state.n, poles=poles, hands=hands)
    won = winner(new)
    return new, Outcome(True, None, won, won is not None, disk)


def to_dict(state: State) -> dict:
    """Plain JSON-compatible dict: ints, lists, None. Inverse of ``from_dict``."""
    return {
        "n": state.n,
        "poles": {k: list(state.poles[k]) for k in POLE_KEYS},
        "hands": {p: state.hands[p] for p in PLAYERS},
    }


def from_dict(data: object) -> State:
    """Rebuild a State from ``to_dict`` output, validating shape and types."""
    check(isinstance(data, dict), "state must be a dict with the keys n, poles, hands")
    check(set(data) == {"n", "poles", "hands"}, "state needs the keys n, poles, hands")
    n, poles, hands = data["n"], data["poles"], data["hands"]
    check(is_positive_int(n), f"n must be a positive integer, got {n!r}")
    check(isinstance(poles, dict) and set(poles) == set(POLE_KEYS), f"poles need keys {POLE_KEYS}")
    check(isinstance(hands, dict) and set(hands) == set(PLAYERS), f"hands need keys {PLAYERS}")
    for key, disks in poles.items():
        ok = isinstance(disks, list | tuple) and all(is_positive_int(d) for d in disks)
        check(ok, f"pole {key} must be a list of positive ints, got {disks!r}")
    for p, held in hands.items():
        ok = held is None or is_positive_int(held)
        check(ok, f"hand {p} must be a positive int or null, got {held!r}")
    return State(n=n, poles={k: tuple(poles[k]) for k in POLE_KEYS}, hands=dict(hands))
