"""Every recording in examples/ replays to the outcome its name promises."""

import pathlib

import pytest

from hanoi_crossing.recording import load, replay

EXAMPLES = pathlib.Path(__file__).resolve().parent.parent / "examples"

EXPECTED = {
    "spec_n1.json": ("won", "A", 3, 0),
    "n1_b_wins.json": ("won", "B", 3, 0),
    "n2_illegal_and_skip.json": ("won", "A", 9, 1),
    "n1_steal.json": ("unfinished", None, 6, 1),
    "n2_unfinished.json": ("unfinished", None, 4, 1),
    "n3_blocked_win.json": ("won", "A", 44, 2),
}


def test_every_example_file_is_listed() -> None:
    assert {p.name for p in EXAMPLES.glob("*.json")} == set(EXPECTED)


@pytest.mark.parametrize(("name", "expected"), sorted(EXPECTED.items()))
def test_example_replays_as_promised(name: str, expected: tuple) -> None:
    status, winner, turns, illegal = expected
    result = replay(load(EXAMPLES / name))
    assert (result.status, result.winner, len(result.turns)) == (status, winner, turns)
    assert sum(1 for t in result.turns if not t.outcome.legal) == illegal


def test_blocked_win_is_handed_over_by_the_opponents_lift() -> None:
    result = replay(load(EXAMPLES / "n3_blocked_win.json"))
    last = result.turns[-1]
    assert last.player == "B" and last.action.verb == "lift" and last.action.pole == 2
    assert last.outcome.winner == "A"
    assert result.final_state.hands["B"] == 6
