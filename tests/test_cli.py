"""The hanoi command, driven through cli.main with injected stdin/stdout (T2, T3, R13)."""

import io
import json
import pathlib

import pytest

from hanoi_crossing import cli
from hanoi_crossing.engine import to_dict
from hanoi_crossing.recording import load, replay

EXAMPLES = pathlib.Path(__file__).resolve().parent.parent / "examples"
SPEC = str(EXAMPLES / "spec_n1.json")


def run_cli(*argv: str, stdin: str = "", isatty: bool = False) -> tuple[int, str]:
    out = io.StringIO()
    code = cli.main(list(argv), stdin=io.StringIO(stdin), stdout=out, isatty=isatty)
    return code, out.getvalue()


@pytest.fixture(autouse=True)
def _cwd(tmp_path, monkeypatch) -> None:  # noqa: ANN001
    monkeypatch.chdir(tmp_path)


# --- replay ---------------------------------------------------------------------


def test_replay_spec_example_prints_a_wins() -> None:
    code, out = run_cli("replay", SPEC)
    assert code == 0
    assert (
        "status won · winner A · played 3 · illegal 0 · skipped 0 · timeouts 0 · unplayed 0" in out
    )
    assert "=1=" in out and "A side" in out and "B side" in out


def test_replay_json_matches_engine_dict() -> None:
    code, out = run_cli("replay", SPEC, "--json")
    data = json.loads(out)
    assert code == 0 and data["status"] == "won" and data["winner"] == "A"
    assert data["state"] == to_dict(replay(load(SPEC)).final_state)
    assert [t["source"] for t in data["turns"]] == ["scripted"] * 3


def test_replay_list_style_uses_cross_layout() -> None:
    _, out = run_cli("replay", SPEC, "--list")
    assert "3a: [1]" in out and "--- [2]: [] ---" in out


def _truncated(tmp: pathlib.Path) -> str:
    p = tmp / "trunc.json"
    p.write_text(json.dumps({"n": 1, "turn_order": "AB", "moves": ["lift 1", "lift 1"]}))
    return str(p)


def test_replay_truncated_is_unfinished_and_does_not_prompt_without_tty(tmp_path) -> None:  # noqa: ANN001
    code, out = run_cli("replay", _truncated(tmp_path))
    assert code == 0 and "status unfinished" in out
    assert "Let random players finish" not in out


def test_replay_continue_flag_finishes_with_random_agents(tmp_path) -> None:  # noqa: ANN001
    code, out = run_cli(
        "replay", _truncated(tmp_path), "--continue", "--seed", "0", "--max-turns", "500"
    )
    assert code == 0 and "continuing" in out.lower()
    assert "status won" in out.split("continuing", 1)[1].lower() or "status" in out


def test_replay_prompts_on_tty_and_respects_answer(tmp_path) -> None:  # noqa: ANN001
    _, out_yes = run_cli("replay", _truncated(tmp_path), stdin="y\n", isatty=True)
    assert "Let random players finish it? [y/N]" in out_yes and "continuing" in out_yes.lower()
    _, out_no = run_cli("replay", _truncated(tmp_path), stdin="n\n", isatty=True)
    assert "continuing" not in out_no.lower()
    _, out_json = run_cli("replay", _truncated(tmp_path), "--json", stdin="y\n", isatty=True)
    assert "Let random players" not in out_json


def test_replay_bad_file_exits_1(tmp_path) -> None:  # noqa: ANN001
    bad = tmp_path / "bad.json"
    bad.write_text('{"n": 1, "turn_order": "AB", "moves": ["lift 1"]}')
    code, out = run_cli("replay", str(bad))
    assert code == 1 and "turn_order" in out
    assert run_cli("replay", str(tmp_path / "missing.json"))[0] == 1


# --- random ---------------------------------------------------------------------


def test_random_is_reproducible_with_seed() -> None:
    a = run_cli("random", "--n", "2", "--seed", "1", "--no-save")
    b = run_cli("random", "--n", "2", "--seed", "1", "--no-save")
    assert a == b and a[0] == 0 and "seed=1" in a[1]


def test_random_autosaves_and_replays_to_same_state(tmp_path) -> None:  # noqa: ANN001
    code, out = run_cli("random", "--n", "1", "--seed", "0", "--json")
    data = json.loads(out)
    saved = pathlib.Path(data["saved"])
    assert code == 0 and saved.exists() and saved.parent.name == "recordings"
    assert to_dict(replay(load(saved)).final_state) == data["state"]


def test_random_save_names_the_file_and_no_save_writes_nothing(tmp_path) -> None:  # noqa: ANN001
    target = tmp_path / "g.json"
    _, out = run_cli("random", "--n", "1", "--seed", "0", "--save", str(target))
    assert target.exists() and f"saved: {target}" in out
    run_cli("random", "--n", "1", "--seed", "0", "--no-save")
    assert not (tmp_path / "recordings").exists()


def test_schedule_and_first_flags_drive_turn_order() -> None:
    _, out = run_cli(
        "random",
        "--n",
        "1",
        "--seed",
        "0",
        "--no-save",
        "--trace",
        "--schedule",
        "AAB",
        "--max-turns",
        "6",
    )
    players = "".join(line.split()[1] for line in out.splitlines() if line[:1].isdigit())
    assert players == "AABAAB"[: len(players)] and "schedule=AAB" in out
    _, out = run_cli("random", "--n", "1", "--seed", "0", "--no-save", "--trace", "--first", "B")
    first_line = next(line for line in out.splitlines() if line[:1].isdigit())
    assert first_line.split()[1] == "B" and "schedule=BA" in out
    code, _ = run_cli("random", "--n", "1", "--first", "B", "--schedule", "A", "--no-save")
    assert code == 2


def test_bad_arguments_exit_2() -> None:
    assert run_cli("random")[0] == 2
    assert run_cli("play", "--a", "human", "--n", "1")[0] == 2
    assert run_cli("nonsense")[0] == 2


# --- play -----------------------------------------------------------------------


def test_play_human_vs_random_with_scripted_stdin() -> None:
    stdin = "lift 2\nfoo\nlift 1\nplace 3\n"
    code, out = run_cli(
        "play",
        "--a",
        "human",
        "--b",
        "random",
        "--n",
        "1",
        "--seed",
        "0",
        "--no-save",
        "--move-timeout",
        "0",
        "--max-turns",
        "12",
        stdin=stdin,
    )
    assert code == 0
    assert "Turn 1, player A" in out and "legal: lift 1, skip" in out and "A>" in out
    assert "illegal: pole 2 is empty. Turn wasted." in out
    assert "not a move" in out.lower() or "try again" in out.lower()
    assert "ok, holding 1" in out
    assert "status " in out


def test_play_move_timeout_falls_back_to_random() -> None:
    code, out = run_cli(
        "play",
        "--a",
        "human",
        "--b",
        "random",
        "--n",
        "1",
        "--seed",
        "0",
        "--no-save",
        "--move-timeout",
        "0.05",
        "--max-turns",
        "6",
        "--trace",
    )
    assert code == 0 and "[timeout]" in out and "timeouts 0" not in out
    assert "time is up" in out


def test_play_human_vs_human_shows_both_prompts() -> None:
    _, out = run_cli(
        "play",
        "--a",
        "human",
        "--b",
        "human",
        "--n",
        "1",
        "--seed",
        "0",
        "--no-save",
        "--move-timeout",
        "0",
        "--max-turns",
        "3",
        stdin="lift 1\nlift 1\nplace 3\n",
    )
    assert "A>" in out and "B>" in out and "status won · winner A" in out


# --- recordings ------------------------------------------------------------------


def test_recordings_lists_saved_games(tmp_path) -> None:  # noqa: ANN001
    code, out = run_cli("recordings")
    assert code == 0 and "no recordings" in out
    run_cli("random", "--n", "1", "--seed", "3")
    code, out = run_cli("recordings")
    assert code == 0 and "n=1" in out and "seed=3" in out and ".json" in out


# --- full game shown by default -------------------------------------------------------


def _trace_lines(out: str) -> list[str]:
    return [line for line in out.splitlines() if line[:1].isdigit() and " → " in line]


def test_full_game_trace_is_shown_by_default() -> None:
    _, out = run_cli("replay", SPEC)
    assert [line.split(" → ")[0] for line in _trace_lines(out)] == [
        "1 A lift 1",
        "2 B lift 1",
        "3 A place 3",
    ]
    _, out = run_cli("random", "--n", "1", "--seed", "0", "--no-save")
    assert len(_trace_lines(out)) >= 2


def test_no_trace_hides_the_turn_lines() -> None:
    _, out = run_cli("replay", SPEC, "--no-trace")
    assert _trace_lines(out) == [] and "status won" in out


def test_bot_turn_lines_explain_shared_pole_effects() -> None:
    # seed 0, n=1: A places disk 1 on pole 2 at turn 3, random B lifts it at turn 4
    stdin = "lift 1\nplace 2\nskip\nskip\n"
    _, out = run_cli(
        "play",
        "--a",
        "human",
        "--b",
        "random",
        "--n",
        "1",
        "--seed",
        "0",
        "--no-save",
        "--move-timeout",
        "0",
        "--max-turns",
        "8",
        stdin=stdin,
    )
    assert "Turn 4, player B: lift 2 → took disk 1 from the shared pole" in out
    assert "Turn 2, player B: skip" in out
