"""The ``hanoi`` command: replay, random, play, recordings.

Only argument parsing and wiring: each command builds agents, calls the one runner
and prints through ``render``. All of it is reachable through ``main(argv, stdin,
stdout, isatty, stderr)``, so tests never spawn a process. ``out`` carries the
result, the console carries interaction; with ``--json`` the console moves to
stderr so stdout is exactly one JSON object.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path
from typing import IO, Any

from .agents import RandomAgent
from .engine import Player, State, initial_state
from .human import Console, HumanAgent, LineReader
from .recording import (
    Recording,
    RecordingFormatError,
    append_run,
    autosave_path,
    dump,
    from_run,
    load,
    replay,
    seed_in_name,
)
from .render import render_board, render_summary, render_trace, result_dict
from .runner import RunResult, repeat, rotate_to, run

EXIT_OK, EXIT_BAD_FILE, EXIT_BAD_ARGS, EXIT_INTERRUPTED = 0, 1, 2, 130
RECORDINGS = Path("recordings")


def default_max_turns(n: int) -> int:
    """Schedule length when --max-turns is not given: clears every measured worst case (D41)."""
    return 200 * 3**n


# --- arguments -----------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    """Four subcommands over four groups of shared flags."""
    output = argparse.ArgumentParser(add_help=False)  # every command
    output.add_argument("--json", action="store_true", help="machine-readable output; no prompts")
    output.add_argument("--list", action="store_true", help="bracket lists instead of towers")
    output.add_argument("--trace", action="store_true", help="one line per turn before the board")
    output.add_argument("--seed", type=int, default=0, help="seed for random agents (default 0)")

    game = argparse.ArgumentParser(add_help=False)  # commands that play or replay a game
    game.add_argument("--schedule", default="AB", help="turn-order pattern, repeated (default AB)")
    game.add_argument("--max-turns", type=int, help="schedule length (default 200 * 3**n)")
    game.add_argument("--repetition-limit", type=int, default=0, help="stalemate after K repeats")
    game.add_argument("--save", metavar="FILE", help="recording file name (default: autosave)")
    game.add_argument("--no-save", action="store_true", help="do not write a recording")

    fresh = argparse.ArgumentParser(add_help=False)  # commands starting a new game
    fresh.add_argument("--n", type=int, required=True, help="disks per player")
    fresh.add_argument("--first", choices=("A", "B"), default="A", help="who takes turn 1")

    human = argparse.ArgumentParser(add_help=False)  # only where a person can play
    human.add_argument("--a", choices=("random", "human"), required=True, help="A's moves")
    human.add_argument("--b", choices=("random", "human"), required=True, help="B's moves")
    human.add_argument("--move-timeout", type=float, default=30, help="seconds per human move")
    human.add_argument("--max-timeouts", type=int, default=3, help="end after K silent prompts")

    parser = argparse.ArgumentParser(prog="hanoi", description="Hanoi Crossing")
    sub = parser.add_subparsers(dest="command", required=True)

    p_replay = sub.add_parser("replay", parents=[output, game], help="re-play a recording")
    p_replay.add_argument("file", metavar="FILE")
    choice = p_replay.add_mutually_exclusive_group()
    choice.add_argument("--continue", dest="cont", action="store_true")
    choice.add_argument("--no-continue", dest="no_cont", action="store_true")

    sub.add_parser("random", parents=[output, game, fresh], help="two random players")

    sub.add_parser("play", parents=[output, game, fresh, human], help="any mix of players")

    p_rec = sub.add_parser("recordings", parents=[output], help="list saved games")
    p_rec.add_argument("--dir", default=str(RECORDINGS))
    return parser


# --- shared steps --------------------------------------------------------------------


def _play(
    args: argparse.Namespace,
    console: Console,
    start: State,
    agents: dict[Player, Any],
    first: Player,
    title: str,
) -> tuple[RunResult, str]:
    """Run a fresh schedule from ``start``; returns the result and the pattern used."""
    pattern = rotate_to(args.schedule, first)  # ValueError -> exit 2 in main
    max_turns = args.max_turns or default_max_turns(start.n)
    console.say(f"{title}  seed={args.seed}  schedule={pattern} (repeats, max {max_turns} turns)")
    live = any(isinstance(a, HumanAgent) for a in agents.values())
    result = run(
        start,
        repeat(pattern, max_turns),
        agents,
        repetition_limit=args.repetition_limit or None,
        on_turn=console.on_turn if live else None,
    )
    return result, pattern


def _save(args: argparse.Namespace, rec: Recording, mode: str) -> Path | None:
    if args.no_save:
        return None
    path = Path(args.save) if args.save else autosave_path(RECORDINGS, mode, rec.n, args.seed)
    dump(rec, path)
    return path


def _report(
    args: argparse.Namespace, out: IO[str], result: RunResult, meta: dict, saved: Path | None
) -> None:
    if args.json:
        payload = {**meta, **result_dict(result), "saved": str(saved) if saved else None}
        out.write(json.dumps(payload, indent=2) + "\n")
        return
    style = "list" if args.list else "tower"
    if args.trace and result.turns:
        out.write("\n" + render_trace(result.turns) + "\n")
    out.write("\n" + render_board(result.final_state, style) + "\n")
    out.write("\n" + render_summary(result) + "\n")
    if saved:
        out.write(f"saved: {saved}\n")


# --- commands ------------------------------------------------------------------------


def cmd_game(
    args: argparse.Namespace, out: IO[str], console: Console, kinds: dict[Player, str]
) -> int:
    """``random`` and ``play``: a fresh game between the given kinds of player."""
    rng = random.Random(args.seed)
    agents: dict[Player, Any] = {}
    for player, kind in kinds.items():
        if kind == "human":
            timeout = args.move_timeout or None
            agents[player] = HumanAgent(
                player, args.n, console, RandomAgent(rng), timeout, args.max_timeouts
            )
        else:
            agents[player] = RandomAgent(rng)
    title = f"Hanoi Crossing  n={args.n}  A: {kinds['A']}  B: {kinds['B']}"
    result, pattern = _play(args, console, initial_state(args.n), agents, args.first, title)
    mode = "random" if set(kinds.values()) == {"random"} else "play"
    saved = _save(args, from_run(args.n, result), mode)
    _report(args, out, result, {"n": args.n, "seed": args.seed, "schedule": pattern}, saved)
    return EXIT_OK


def cmd_replay(args: argparse.Namespace, out: IO[str], console: Console, isatty: bool) -> int:
    """Re-play a recording; offer to let random players finish an unfinished game."""
    try:
        rec = load(args.file)
    except (OSError, RecordingFormatError) as e:
        out.write(f"error: cannot replay {args.file}: {e}\n")
        return EXIT_BAD_FILE
    console.say(f"Hanoi Crossing  replay {args.file}  n={rec.n}  recorded turns={len(rec.moves)}")
    result = replay(rec)
    meta = {"n": rec.n, "seed": args.seed, "schedule": rec.turn_order, "file": args.file}
    if result.status != "unfinished" or not _wants_continue(args, console, isatty):
        _report(args, out, result, meta, None)
        return EXIT_OK

    if not args.json:
        _report(args, out, result, meta, None)  # the recorded part, before continuing
    rng = random.Random(args.seed)
    agents: dict[Player, Any] = {"A": RandomAgent(rng), "B": RandomAgent(rng)}
    first: Player = "B" if rec.turn_order.endswith("A") else "A"
    console.say()
    more, pattern = _play(
        args, console, result.final_state, agents, first, "continuing with random agents"
    )
    saved = _save(args, append_run(rec, more), "continue")
    _report(args, out, more, {**meta, "schedule": pattern, "continued": True}, saved)
    return EXIT_OK


def _wants_continue(args: argparse.Namespace, console: Console, isatty: bool) -> bool:
    if args.cont:
        return True
    if args.no_cont or args.json or not isatty:
        return False
    answer = console.prompt("Game unfinished. Let random players finish it? [y/N] ")
    return (answer or "").strip().lower() in ("y", "yes")


def cmd_recordings(args: argparse.Namespace, out: IO[str]) -> int:
    """One line per saved game: its size, seed, length, and how it ends."""
    folder = Path(args.dir)
    files = sorted(folder.glob("*.json")) if folder.is_dir() else []
    if not files:
        out.write(f"no recordings in {folder}/\n")
    for path in files:
        try:
            rec = load(path)
        except RecordingFormatError as e:
            out.write(f"{path.name}  (invalid: {e})\n")
            continue
        result = replay(rec)
        when = datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
        out.write(
            f"{path.name}  n={rec.n}  seed={seed_in_name(path) or '-'}  turns={len(rec.moves)}  "
            f"status={result.status}  winner={result.winner or '-'}  {when}\n"
        )
    return EXIT_OK


# --- entry ---------------------------------------------------------------------------


def main(
    argv: Sequence[str] | None = None,
    stdin: IO[str] | None = None,
    stdout: IO[str] | None = None,
    isatty: bool | None = None,
    stderr: IO[str] | None = None,
) -> int:
    try:
        args = build_parser().parse_args(argv)
    except SystemExit as e:
        return e.code if isinstance(e.code, int) else EXIT_BAD_ARGS
    stdin = stdin or sys.stdin
    out = stdout or sys.stdout
    tty = isatty if isatty is not None else stdin.isatty()
    chat = (stderr or sys.stderr) if args.json else out
    console = Console(LineReader(stdin), chat, "list" if args.list else "tower")
    try:
        if args.command == "replay":
            return cmd_replay(args, out, console, tty)
        if args.command == "random":
            return cmd_game(args, out, console, {"A": "random", "B": "random"})
        if args.command == "play":
            return cmd_game(args, out, console, {"A": args.a, "B": args.b})
        return cmd_recordings(args, out)
    except ValueError as e:  # bad --schedule / --first combinations
        out.write(f"error: {e}\n")
        return EXIT_BAD_ARGS
    except KeyboardInterrupt:  # Ctrl-C outside a human prompt: nothing to save
        out.write("\ninterrupted\n")
        return EXIT_INTERRUPTED


def entry() -> None:
    sys.exit(main())
