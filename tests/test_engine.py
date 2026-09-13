"""Tests for the core engine. IDs in names refer to docs/REQUIREMENTS.md."""

import pytest

from hanoi_crossing import engine
from hanoi_crossing.engine import (
    ALL_ACTIONS,
    Action,
    Observation,
    Outcome,
    State,
    initial_state,
    legal_actions,
    observe,
    step,
)

# --- types --------------------------------------------------------------------


def test_action_space_is_fixed_seven_in_order() -> None:
    assert ALL_ACTIONS == (
        Action("lift", 1),
        Action("lift", 2),
        Action("lift", 3),
        Action("place", 1),
        Action("place", 2),
        Action("place", 3),
        Action("skip"),
    )


def test_state_is_immutable_and_hashable() -> None:
    s = initial_state(1)
    with pytest.raises(AttributeError):
        s.n = 2  # type: ignore[misc]
    assert hash(s) == hash(initial_state(1))
    assert s == initial_state(1)
    assert s != initial_state(2)


# --- initial_state: R1, R4 -----------------------------------------------------


@pytest.mark.parametrize(
    ("n", "a", "b"),
    [(1, (1,), (2,)), (2, (3, 1), (4, 2)), (3, (5, 3, 1), (6, 4, 2))],
)
def test_initial_state_layout(n: int, a: tuple[int, ...], b: tuple[int, ...]) -> None:
    s = initial_state(n)
    assert s.n == n
    assert s.poles == {"1a": a, "2": (), "3a": (), "1b": b, "3b": ()}
    assert s.hands == {"A": None, "B": None}


@pytest.mark.parametrize("bad", [0, -1, 1.5, "2"])
def test_initial_state_rejects_bad_n(bad: object) -> None:
    with pytest.raises(ValueError):
        initial_state(bad)  # type: ignore[arg-type]


# --- observe: R3, R12 ----------------------------------------------------------


def test_observe_shows_only_own_side_and_shared_pole() -> None:
    s = State(
        n=2,
        poles={"1a": (3,), "2": (1,), "3a": (), "1b": (4,), "3b": (2,)},
        hands={"A": None, "B": None},
    )
    assert observe(s, "A") == Observation(poles={1: (3,), 2: (1,), 3: ()}, hand=None)
    assert observe(s, "B") == Observation(poles={1: (4,), 2: (1,), 3: (2,)}, hand=None)


def test_observe_shows_own_hand_not_opponents() -> None:
    s = State(
        n=1,
        poles={"1a": (), "2": (), "3a": (), "1b": (), "3b": ()},
        hands={"A": 1, "B": 2},
    )
    assert observe(s, "A").hand == 1
    assert observe(s, "B").hand == 2
    assert "hands" not in vars(observe(s, "A"))


def test_observe_rejects_unknown_player() -> None:
    with pytest.raises(ValueError):
        observe(initial_state(1), "C")  # type: ignore[arg-type]


def test_engine_module_has_no_io_or_randomness() -> None:
    src = open(engine.__file__, encoding="utf-8").read()
    for banned in ("import random", "import os", "import sys", "print(", "open("):
        assert banned not in src


# --- helpers -------------------------------------------------------------------


def make(poles: dict[str, tuple[int, ...]], hands: dict[str, int | None] | None = None) -> State:
    full = {"1a": (), "2": (), "3a": (), "1b": (), "3b": ()}
    full.update(poles)
    return State(n=3, poles=full, hands=hands or {"A": None, "B": None})


# --- legal_actions and step: R5, R6, R7, R8, R9, R2 ------------------------------


def test_legal_actions_at_start_are_lift_1_and_skip() -> None:
    s = initial_state(2)
    for p in ("A", "B"):
        assert legal_actions(s, p) == [Action("lift", 1), Action("skip")]


def test_legal_actions_after_lift_respect_size_rule() -> None:
    s = make({"1a": (3,), "2": (1,), "3a": ()}, {"A": 5, "B": None})
    # holding 5: can go on empty 3a only; 1a top 3 and pole 2 top 1 are smaller
    assert legal_actions(s, "A") == [Action("place", 3), Action("skip")]


def test_legal_actions_order_follows_all_actions() -> None:
    s = make({"1a": (5,), "2": (3,), "3a": (1,)}, {"A": None, "B": None})
    assert legal_actions(s, "A") == [
        Action("lift", 1),
        Action("lift", 2),
        Action("lift", 3),
        Action("skip"),
    ]


def test_step_lift_and_place_change_state() -> None:
    s0 = initial_state(1)
    s1, out = step(s0, "A", Action("lift", 1))
    assert out == Outcome(legal=True, reason=None, winner=None, done=False)
    assert s1.poles["1a"] == () and s1.hands["A"] == 1
    assert s0.poles["1a"] == (1,), "old state must be untouched"
    s2, out = step(s1, "A", Action("place", 2))
    assert out.legal and s2.poles["2"] == (1,) and s2.hands["A"] is None


def test_step_skip_is_legal_and_changes_nothing() -> None:
    s = initial_state(1)
    s2, out = step(s, "B", Action("skip"))
    assert out.legal and s2 == s


@pytest.mark.parametrize(
    ("state", "player", "action", "reason"),
    [
        (make({"1a": (1,)}), "A", Action("lift", 2), "pole 2 is empty"),
        (make({"1a": (1,)}), "A", Action("lift", 3), "pole 3 is empty"),
        (make({"1a": (1,)}, {"A": 3, "B": None}), "A", Action("lift", 1), "hand is not empty"),
        (make({"1a": (1,)}), "A", Action("place", 3), "hand is empty"),
        (
            make({"2": (2,)}, {"A": 3, "B": None}),
            "A",
            Action("place", 2),
            "disk 3 cannot go on disk 2",
        ),
        (
            make({"1b": (4,)}, {"A": None, "B": 6}),
            "B",
            Action("place", 1),
            "disk 6 cannot go on disk 4",
        ),
    ],
)
def test_step_illegal_reports_reason_and_returns_same_object(
    state: State, player: str, action: Action, reason: str
) -> None:
    s2, out = step(state, player, action)  # type: ignore[arg-type]
    assert s2 is state
    assert out == Outcome(legal=False, reason=reason, winner=None, done=False)


@pytest.mark.parametrize(
    ("player", "action"),
    [
        ("C", Action("skip")),
        ("A", Action("jump", 1)),  # type: ignore[arg-type]
        ("A", Action("lift", 4)),  # type: ignore[arg-type]
        ("A", Action("lift", None)),
        ("A", Action("place", 0)),  # type: ignore[arg-type]
        ("A", Action("skip", 1)),
        ("A", "lift 1"),
    ],
)
def test_step_malformed_raises(player: str, action: object) -> None:
    with pytest.raises(ValueError):
        step(initial_state(1), player, action)  # type: ignore[arg-type]


def test_either_player_may_lift_opponents_disk_from_shared_pole() -> None:
    s = make({"2": (6, 1)})  # A's disk 1 on top of B's disk 6
    s2, out = step(s, "B", Action("lift", 2))
    assert out.legal and s2.hands["B"] == 1 and s2.poles["2"] == (6,)
    s3, out = step(s2, "B", Action("place", 3))  # B keeps A's disk on 3b
    assert out.legal and s3.poles["3b"] == (1,)


def test_placing_opponents_disk_on_own_pole_follows_size_rule() -> None:
    s = make({"3a": (5,)}, {"A": 6, "B": None})
    _, out = step(s, "A", Action("place", 3))
    assert not out.legal and out.reason == "disk 6 cannot go on disk 5"
    s2, out = step(s, "A", Action("place", 1))  # 1a empty: B's disk 6 becomes A's base
    assert out.legal and s2.poles["1a"] == (6,)


def test_opponents_private_poles_are_unreachable() -> None:
    # A can only name poles 1-3 from A's side; there is no way to address 1b or 3b.
    s = make({"1b": (2,)})
    for a in ALL_ACTIONS:
        s2, _ = step(s, "A", a)
        assert s2.poles["1b"] == (2,) and s2.poles["3b"] == ()
