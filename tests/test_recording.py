"""JSON recording format: parse, validate, write, files, and the conversions to the runner."""

import json
import random

import pytest

from hanoi_crossing.agents import RandomAgent
from hanoi_crossing.engine import Action, initial_state
from hanoi_crossing.recording import (
    Recording,
    RecordingFormatError,
    append_run,
    autosave_path,
    dump,
    dumps,
    from_run,
    load,
    loads,
    replay,
    seed_in_name,
)
from hanoi_crossing.runner import repeat, run

SPEC = {"n": 1, "turn_order": "ABA", "moves": ["lift 1", "lift 1", "place 3"]}
L1, P3, SKIP = Action("lift", 1), Action("place", 3), Action("skip")


# --- loads / dumps ------------------------------------------------------------------


def test_loads_spec_example() -> None:
    rec = loads(json.dumps(SPEC))
    assert rec == Recording(n=1, turn_order="ABA", moves=(L1, L1, P3))
    assert rec.sources is None


def test_dumps_loads_round_trip_with_sources() -> None:
    rec = Recording(n=2, turn_order="AB", moves=(L1, SKIP), sources=("human", "timeout"))
    assert loads(dumps(rec)) == rec
    assert json.loads(dumps(rec))["sources"] == ["human", "timeout"]


def test_dumps_omits_sources_when_absent() -> None:
    assert "sources" not in json.loads(dumps(loads(json.dumps(SPEC))))


def test_load_and_dump_files(tmp_path) -> None:  # noqa: ANN001
    path = tmp_path / "g.json"
    rec = loads(json.dumps(SPEC))
    dump(rec, path)
    assert load(path) == rec
    assert load("examples/spec_n1.json") == rec


def _with(**changes: object) -> str:
    d = dict(SPEC)
    d.update(changes)
    return json.dumps(d)


@pytest.mark.parametrize(
    "text",
    [
        "[]",
        "not json",
        json.dumps({"n": 1, "moves": []}),
        _with(n=0),
        _with(n="1"),
        _with(turn_order="ABC"),
        _with(turn_order="AB"),  # length mismatch
        _with(moves=["lift 1", "lift 1", "jump 3"]),
        _with(moves=["lift 1", "lift 1", "place 9"]),
        _with(moves=["lift 1", "lift 1", "skip 3"]),
        _with(sources=["human"]),  # wrong length
        _with(sources=["human", "human", "alien"]),
        _with(extra=1),
    ],
)
def test_loads_rejects_bad_recordings(text: str) -> None:
    with pytest.raises(RecordingFormatError):
        loads(text)


def test_recording_rejects_text_moves() -> None:
    with pytest.raises(RecordingFormatError):
        Recording(n=1, turn_order="A", moves=("lift 1",))  # type: ignore[arg-type]


def test_autosave_path_is_fresh_and_names_the_seed(tmp_path) -> None:  # noqa: ANN001
    first = autosave_path(tmp_path / "recordings", "random", 2, 7)
    assert first.parent.is_dir() and first.name.endswith("-random-n2-seed7.json")
    first.write_text("{}")
    second = autosave_path(tmp_path / "recordings", "random", 2, 7)
    assert second != first and not second.exists()
    assert seed_in_name(first) == "7" and seed_in_name(tmp_path / "game.json") is None


# --- replay / from_run / append_run -----------------------------------------------------


def test_replay_spec_example_a_wins() -> None:
    result = replay(loads(json.dumps(SPEC)))
    assert result.status == "won" and result.winner == "A" and len(result.turns) == 3


def test_replay_truncated_recording_is_unfinished() -> None:
    result = replay(loads(_with(turn_order="AB", moves=["lift 1", "lift 1"])))
    assert result.status == "unfinished" and result.final_state.hands == {"A": 1, "B": 2}


def test_replay_reproduces_illegal_moves_as_wasted_turns() -> None:
    rec = loads(_with(n=2, turn_order="AABB", moves=["lift 1", "place 2", "lift 1", "place 2"]))
    result = replay(rec)
    assert not result.turns[3].outcome.legal
    assert result.turns[3].outcome.reason == "disk 2 cannot go on disk 1"


def test_from_run_then_replay_gives_identical_final_state() -> None:
    rng = random.Random(11)
    result = run(
        initial_state(3), repeat("AB", 5000), {"A": RandomAgent(rng), "B": RandomAgent(rng)}
    )
    rec = from_run(3, result)
    assert len(rec.moves) == len(result.turns)
    assert rec.turn_order == "".join(t.player for t in result.turns)
    assert rec.sources == tuple("random" for _ in result.turns)
    again = replay(loads(dumps(rec)))
    assert again.final_state == result.final_state
    assert again.status == result.status == "won" and again.winner == result.winner


def test_append_run_keeps_the_recorded_part_and_adds_the_new_turns() -> None:
    rec = loads(_with(turn_order="AB", moves=["lift 1", "lift 1"]))
    rng = random.Random(0)
    more = run(
        replay(rec).final_state, repeat("AB", 600), {"A": RandomAgent(rng), "B": RandomAgent(rng)}
    )
    whole = append_run(rec, more)
    assert whole.moves[:2] == rec.moves and len(whole.moves) == 2 + len(more.turns)
    assert whole.sources == ("scripted", "scripted") + ("random",) * len(more.turns)
    assert replay(whole).final_state == more.final_state
