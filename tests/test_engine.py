"""Tests for the core engine. IDs in names refer to docs/REQUIREMENTS.md."""

import pytest

from hanoi_crossing import engine
from hanoi_crossing.engine import (
    ALL_ACTIONS,
    Action,
    Observation,
    State,
    initial_state,
    observe,
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
