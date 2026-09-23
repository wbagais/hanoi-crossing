"""The hanoi command, driven through cli.main with injected stdin/stdout (T2, T3, R13)."""

import io
import json
import pathlib
import re

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
    assert code == 0 and "status won · winner A" in out
    assert "=1=" in out and "A side" in out and "B side" in out
    assert _trace_lines(out) == [], "the whole game only appears with --trace"


def test_replay_json_matches_engine_dict() -> None:
    code, out = run_cli("replay", SPEC, "--json")
    data = json.loads(out)
    assert code == 0 and data["status"] == "won" and data["winner"] == "A"
    assert set(data) == {
        "n",
        "seed",
        "schedule",
        "file",
        "status",
        "winner",
        "state",
        "counts",
        "turns",
        "saved",
    }
    assert (data["n"], data["seed"], data["schedule"], data["file"]) == (1, 0, "ABA", SPEC)
    assert data["state"] == to_dict(replay(load(SPEC)).final_state)
    assert data["counts"] == {"played": 3, "illegal": 0, "skipped": 0, "timeouts": 0, "unplayed": 0}
    assert [t["source"] for t in data["turns"]] == ["scripted"] * 3
    assert data["turns"][0] == {
        "index": 1,
        "player": "A",
        "action": "lift 1",
        "legal": True,
        "reason": None,
        "source": "scripted",
    }


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
    assert code == 0 and "continuing with random agents" in out
    assert "status won · winner B" in out.split("continuing", 1)[1]


def test_replay_continue_json_reports_the_continuation_and_saves_the_whole_game(
    tmp_path,  # noqa: ANN001
) -> None:
    _, out = run_cli(
        "replay", _truncated(tmp_path), "--continue", "--seed", "0", "--max-turns", "500", "--json"
    )
    data = json.loads(out)
    assert data["continued"] is True and data["status"] == "won" and data["winner"] == "B"
    saved = pathlib.Path(data["saved"])
    assert saved.exists() and "continue" in saved.name
    whole = load(saved)
    assert whole.moves[:2] == load(_truncated(tmp_path)).moves  # the recorded part is kept
    assert to_dict(replay(whole).final_state) == data["state"]


def test_replay_no_continue_never_asks_even_on_a_tty(tmp_path) -> None:  # noqa: ANN001
    code, out = run_cli("replay", _truncated(tmp_path), "--no-continue", stdin="y\n", isatty=True)
    assert code == 0 and "Let random players" not in out and "continuing" not in out


def test_replay_prompts_on_tty_and_respects_answer(tmp_path) -> None:  # noqa: ANN001
    _, out_yes = run_cli("replay", _truncated(tmp_path), stdin="y\n", isatty=True)
    assert "Let random players finish it? [y/N]" in out_yes and "continuing" in out_yes.lower()
    _, out_no = run_cli("replay", _truncated(tmp_path), stdin="n\n", isatty=True)
    assert "continuing" not in out_no.lower()
    _, out_json = run_cli("replay", _truncated(tmp_path), "--json", stdin="y\n", isatty=True)
    data = json.loads(out_json)
    assert data["status"] == "unfinished" and "continued" not in data


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


def test_random_autosaves_and_replays_to_same_state() -> None:
    code, out = run_cli("random", "--n", "1", "--seed", "0", "--json")
    data = json.loads(out)
    saved = pathlib.Path(data["saved"])
    assert code == 0 and saved.exists() and saved.parent.name == "recordings"
    assert re.fullmatch(r"\d{8}-\d{6}-random-n1-seed0(-\d+)?\.json", saved.name), saved.name
    assert to_dict(replay(load(saved)).final_state) == data["state"]


def test_play_mode_names_its_own_recordings() -> None:
    _, out = run_cli(
        "play",
        "--a",
        "random",
        "--b",
        "human",
        "--n",
        "1",
        "--seed",
        "0",
        "--json",
        "--move-timeout",
        "0",
        "--max-turns",
        "4",
    )
    saved = pathlib.Path(json.loads(out)["saved"])
    assert re.fullmatch(r"\d{8}-\d{6}-play-n1-seed0(-\d+)?\.json", saved.name), saved.name


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


def test_ctrl_c_outside_a_prompt_exits_130(monkeypatch) -> None:  # noqa: ANN001
    def interrupt(*_args: object) -> int:
        raise KeyboardInterrupt

    monkeypatch.setattr(cli, "cmd_recordings", interrupt)
    code, out = run_cli("recordings")
    assert code == 130 and "interrupted" in out


def test_bad_arguments_exit_2() -> None:
    assert run_cli("random")[0] == 2
    assert run_cli("play", "--a", "human", "--n", "1")[0] == 2
    assert run_cli("nonsense")[0] == 2
    code, out = run_cli("random", "--n", "1", "--no-save", "--max-turns", "0")
    assert code == 2 and "--max-turns must be 1 or more" in out
    assert run_cli("random", "--n", "1", "--no-save", "--repetition-limit", "1")[0] == 2


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
    assert "  took disk 1 from pole 1" in out
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


def test_recordings_lists_saved_games() -> None:
    code, out = run_cli("recordings")
    assert code == 0 and "no recordings" in out
    run_cli("random", "--n", "1", "--seed", "3")
    code, out = run_cli("recordings")
    line = next(li for li in out.splitlines() if li.endswith(".json") or ".json" in li)
    assert code == 0 and "n=1" in line and "seed=3" in line
    assert "status=won" in line and "winner=" in line and "turns=" in line


def test_recordings_reads_another_folder_and_survives_a_bad_file(tmp_path) -> None:  # noqa: ANN001
    folder = tmp_path / "elsewhere"
    folder.mkdir()
    (folder / "broken.json").write_text("not json")
    run_cli("random", "--n", "1", "--seed", "5", "--save", str(folder / "good.json"))
    code, out = run_cli("recordings", "--dir", str(folder))
    assert code == 0
    assert "broken.json  (invalid:" in out and "good.json" in out


# --- full game shown by default -------------------------------------------------------


def _trace_lines(out: str) -> list[str]:
    return [line for line in out.splitlines() if line[:1].isdigit() and " → " in line]


def test_trace_flag_shows_the_full_game() -> None:
    _, out = run_cli("replay", SPEC, "--trace")
    assert [line.split(" → ")[0] for line in _trace_lines(out)] == [
        "1 A lift 1",
        "2 B lift 1",
        "3 A place 3",
    ]
    _, out = run_cli("random", "--n", "1", "--seed", "0", "--no-save", "--trace")
    assert len(_trace_lines(out)) >= 2


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


# --- max-turns default scales with n ------------------------------------------------------


def test_default_max_turns_is_200_times_3_to_the_n() -> None:
    assert cli.default_max_turns(1) == 600
    assert cli.default_max_turns(4) == 16200
    _, out = run_cli("random", "--n", "2", "--seed", "0", "--no-save")
    assert "max 1800 turns" in out
    _, out = run_cli("random", "--n", "2", "--seed", "0", "--no-save", "--max-turns", "7")
    assert "max 7 turns" in out


@pytest.mark.parametrize("n", [1, 2, 3, 4])
def test_random_games_finish_within_the_default_cap(n: int) -> None:
    for seed in range(3):
        _, out = run_cli("random", "--n", str(n), "--seed", str(seed), "--no-save", "--json")
        assert json.loads(out)["status"] == "won"


# --- repetition limit is off unless asked for ---------------------------------------------


def test_repetition_limit_defaults_to_off_everywhere() -> None:
    parser = cli.build_parser()
    assert parser.parse_args(["random", "--n", "1"]).repetition_limit == 0
    assert (
        parser.parse_args(["play", "--a", "human", "--b", "random", "--n", "1"]).repetition_limit
        == 0
    )
    assert parser.parse_args(["replay", "x.json"]).repetition_limit == 0
    assert (
        parser.parse_args(["random", "--n", "1", "--repetition-limit", "3"]).repetition_limit == 3
    )


def test_random_game_with_explicit_repetition_limit_can_stalemate() -> None:
    # n=1, seed 0: the initial position recurs quickly with a limit of 2
    _, out = run_cli(
        "random", "--n", "1", "--seed", "0", "--no-save", "--json", "--repetition-limit", "2"
    )
    assert json.loads(out)["status"] == "stalemate"
    _, out = run_cli("random", "--n", "1", "--seed", "0", "--no-save", "--json")
    assert json.loads(out)["status"] == "won"


# --- ending a game early -----------------------------------------------------------------


def _play(stdin: str, *extra: str) -> tuple[int, str]:
    return run_cli(
        "play",
        "--a",
        "human",
        "--b",
        "random",
        "--n",
        "2",
        "--seed",
        "0",
        "--no-save",
        "--json",
        "--max-turns",
        "200",
        *extra,
        stdin=stdin,
    )


def test_typing_quit_ends_the_game_unfinished() -> None:
    code, out = _play("lift 1\nquit\n", "--move-timeout", "0")
    data = json.loads(out)
    assert code == 0 and data["status"] == "unfinished"
    assert [t["action"] for t in data["turns"][:1]] == ["lift 1"]
    assert len(data["turns"]) <= 3


def test_three_consecutive_timeouts_end_the_game() -> None:
    code, out = _play("", "--move-timeout", "0.05")
    data = json.loads(out)
    assert code == 0 and data["status"] == "unfinished"
    # the third unanswered prompt ends the game; the first two were played by the fallback
    human_turns = [t for t in data["turns"] if t["player"] == "A"]
    assert len(human_turns) == 2 and all(t["source"] == "timeout" for t in human_turns)


def test_max_timeouts_flag_changes_the_count_and_zero_disables() -> None:
    _, out = _play("", "--move-timeout", "0.02", "--max-timeouts", "1")
    assert len([t for t in json.loads(out)["turns"] if t["player"] == "A"]) == 0
    _, out = _play("", "--move-timeout", "0.02", "--max-timeouts", "0", "--max-turns", "10")
    assert len([t for t in json.loads(out)["turns"] if t["player"] == "A"]) == 5


def test_quit_message_is_printed_in_text_mode() -> None:
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
        stdin="quit\n",
    )
    assert "game ended: player A quit" in out and "status unfinished" in out
