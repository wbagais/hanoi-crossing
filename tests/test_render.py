"""Text rendering: tower view, list view, final board, trace, summary (R12, T9)."""

from hanoi_crossing.engine import Action, Outcome, State, initial_state, observe
from hanoi_crossing.render import (
    describe_outcome,
    render_board,
    render_summary,
    render_trace,
    render_view,
)
from hanoi_crossing.runner import RunResult, Turn


def _state(n: int, poles: dict, hands: dict | None = None) -> State:
    full = {"1a": (), "2": (), "3a": (), "1b": (), "3b": ()}
    full.update(poles)
    return State(n=n, poles=full, hands=hands or {"A": None, "B": None})


# --- tower view -------------------------------------------------------------------


def test_tower_view_draws_disks_to_scale_and_labels_poles() -> None:
    s = _state(2, {"1a": (3,), "2": (1,)}, {"A": 4, "B": None})
    text = render_view(observe(s, "A"), player="A", index=4, n=2, legal=[Action("skip")])
    lines = text.splitlines()
    assert lines[0].startswith("Turn 4, player A") and lines[0].endswith("hand: (4)")
    assert "===3===" in text and "=1=" in text
    assert "pole 1" in lines[-3] and "pole 2" in lines[-3] and "pole 3" in lines[-3]
    assert lines[-1].strip() == "legal: skip"
    # height = 2n disk rows: rows between header/blank and the base line
    base_idx = next(i for i, line in enumerate(lines) if set(line.strip()) == {"-", " "})
    assert base_idx - 2 == 2 * 2


def test_tower_view_column_width_scales_with_n() -> None:
    for n in (1, 2, 3):
        s = initial_state(n)
        text = render_view(observe(s, "B"), player="B", index=1, n=n, legal=[])
        base = next(line for line in text.splitlines() if set(line.strip()) == {"-", " "})
        width = len(base.split()[0])
        assert width >= 4 * n + 1 and width % 2 == 1
        biggest = "=" * (2 * n) + str(2 * n) + "=" * (2 * n)
        assert biggest in text


def test_tower_view_shows_countdown_when_given() -> None:
    text = render_view(observe(initial_state(1), "A"), "A", 1, 1, [Action("skip")], seconds=30)
    assert text.rstrip().endswith("legal: skip       (30 s)") or "(30 s)" in text


# --- list view ------------------------------------------------------------------


def test_list_view_uses_bracket_lists() -> None:
    s = _state(2, {"1a": (3,), "2": (1,)}, {"A": 4, "B": None})
    text = render_view(observe(s, "A"), "A", 4, 2, [Action("place", 3)], style="list")
    assert text.splitlines()[0].endswith("hand: 4")
    assert "pole 1: [3]   pole 2: [1]   pole 3: []" in text
    assert "legal: place 3" in text


# --- final board ----------------------------------------------------------------


def test_board_tower_style_shows_both_sides() -> None:
    s = _state(1, {"3a": (1,)}, {"A": None, "B": 2})
    text = render_board(s)
    assert "1a" in text and "[2]" in text and "3a" in text and "1b" in text and "3b" in text
    assert "hand A: -" in text and "hand B: (2)" in text
    assert "=1=" in text


def test_board_list_style_uses_spec_cross_layout() -> None:
    s = _state(2, {"1a": (3, 1), "1b": (4,), "3b": (2,)})
    text = render_board(s, style="list")
    lines = [line.rstrip() for line in text.splitlines()]
    assert lines[0].strip() == "1a: [3, 1]"
    assert lines[1].strip() == "|"
    assert lines[2].strip() == "1b: [4] --- [2]: [] --- 3b: [2]"
    assert lines[3].strip() == "|"
    assert lines[4].strip() == "3a: []"
    assert "hand A: -" in lines[5] and "hand B: -" in lines[5]


# --- outcome text, trace, summary ----------------------------------------------------


def test_describe_outcome() -> None:
    ok = Outcome(True, None, None, False)
    assert describe_outcome(Action("lift", 1), ok, held_after=1) == "ok, holding 1"
    assert describe_outcome(Action("place", 2), ok, held_after=None, disk=1) == (
        "ok, placed 1 on pole 2"
    )
    assert describe_outcome(Action("skip"), ok) == "skip"
    bad = Outcome(False, "disk 2 cannot go on disk 1", None, False)
    assert describe_outcome(Action("place", 2), bad) == (
        "illegal: disk 2 cannot go on disk 1. Turn wasted."
    )


def _result(turns: list[Turn], status: str = "won", winner: str | None = "A") -> RunResult:
    return RunResult(initial_state(1), tuple(turns), status, winner, 0)  # type: ignore[arg-type]


def _turn(i: int, p: str, a: Action, legal: bool = True, source: str = "random") -> Turn:
    out = Outcome(legal, None if legal else "hand is empty", None, False)
    return Turn(i, p, a, out, source)  # type: ignore[arg-type]


def test_trace_marks_sources_only_when_relevant() -> None:
    same = [_turn(1, "A", Action("lift", 1)), _turn(2, "B", Action("skip"))]
    text = render_trace(same, n=1)
    assert "[random]" not in text
    assert text.splitlines()[0].startswith("1 A lift 1")
    mixed = [_turn(1, "A", Action("lift", 1), source="human"), _turn(2, "B", Action("skip"))]
    text = render_trace(mixed, n=1)
    assert "[human]" in text.splitlines()[0] and "[random]" in text.splitlines()[1]
    timed = [_turn(1, "A", Action("lift", 1), source="timeout")]
    assert "[timeout]" in render_trace(timed, n=1)


def test_summary_counts() -> None:
    turns = [
        _turn(1, "A", Action("lift", 1)),
        _turn(2, "B", Action("place", 1), legal=False),
        _turn(3, "A", Action("skip")),
        _turn(4, "B", Action("lift", 1), source="timeout"),
    ]
    text = render_summary(_result(turns))
    assert text == (
        "status won · winner A · played 4 · illegal 1 · skipped 1 · timeouts 1 · unplayed 0"
    )
    assert render_summary(_result([], "unfinished", None)).startswith(
        "status unfinished · winner -"
    )
