"""The ``hanoi`` command: replay, random, play, recordings.

Follows plans/PLAN.md §4: Build game (here) -> the one runner loop -> Render ->
autosave. Everything testable is reachable through ``main(argv, stdin, stdout,
isatty)`` so tests never spawn a subprocess.
"""

from __future__ import annotations

import argparse
import json
import queue
import random
import re
import sys
import threading
import time
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import IO

from .agents import Agent, ExternalAgent, RandomAgent, Timeout
from .engine import Action, Observation, State, initial_state, pole_key, to_dict
from .recording import Recording, RecordingFormatError, dump, from_run, load, parse_action, replay
from .render import (
    counts,
    describe_outcome,
    render_board,
    render_summary,
    render_trace,
    render_view,
)
from .runner import RunResult, Turn, repeat, rotate_to, run

EXIT_OK, EXIT_BAD_FILE, EXIT_BAD_ARGS = 0, 1, 2


def default_max_turns(n: int) -> int:
    """Schedule length when --max-turns is not given.

    Random games need roughly three times more turns per extra disk (measured
    medians 10, 44, 136, 474, 1434 for n = 1..5; worst cases about 3x the median).
    200 * 3**n clears every observed worst case with headroom (D41).
    """
    return 200 * 3**n


PROMPT_HELP = "not a move, try again: lift N | place N | skip  (N = 1, 2, 3)"


# --- argument parsing ---------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--json", action="store_true", help="machine-readable output; no prompts")
    common.add_argument("--list", action="store_true", help="bracket lists instead of towers")
    common.add_argument("--trace", action="store_true", help="one line per turn before the board")
    common.add_argument("--seed", type=int, default=0, help="seed for random agents (default 0)")

    game = argparse.ArgumentParser(add_help=False)
    game.add_argument("--schedule", default="AB", help="turn-order pattern, repeated (default AB)")
    game.add_argument(
        "--max-turns", type=int, default=None, help="schedule length (default 200 * 3**n)"
    )
    game.add_argument(
        "--repetition-limit",
        type=int,
        default=0,
        help="end as stalemate after K repeats of a position; 0 = off (default)",
    )

    fresh = argparse.ArgumentParser(add_help=False)
    fresh.add_argument("--n", type=int, required=True, help="disks per player")
    fresh.add_argument("--first", choices=("A", "B"), default="A", help="who takes turn 1")
    fresh.add_argument("--no-skip", action="store_true", help="random agents avoid skip")
    fresh.add_argument("--save", metavar="FILE", help="recording file name (default: autosave)")
    fresh.add_argument("--no-save", action="store_true", help="do not write a recording")

    parser = argparse.ArgumentParser(prog="hanoi", description="Hanoi Crossing")
    sub = parser.add_subparsers(dest="command", required=True)

    p_replay = sub.add_parser("replay", parents=[common, game], help="re-play a recording")
    p_replay.add_argument("file", metavar="FILE")
    grp = p_replay.add_mutually_exclusive_group()
    grp.add_argument("--continue", dest="cont", action="store_true")
    grp.add_argument("--no-continue", dest="no_cont", action="store_true")

    sub.add_parser("random", parents=[common, game, fresh], help="two random players")

    p_play = sub.add_parser("play", parents=[common, game, fresh], help="any mix of players")
    p_play.add_argument("--a", choices=("random", "human"), required=True)
    p_play.add_argument("--b", choices=("random", "human"), required=True)
    p_play.add_argument(
        "--move-timeout", type=float, default=30, help="seconds per human move; 0 disables"
    )

    p_rec = sub.add_parser("recordings", parents=[common], help="list saved games")
    p_rec.add_argument("--dir", default="recordings")
    return parser


# --- stdin with a timeout ----------------------------------------------------------------


class LineReader:
    """Reads stdin lines on a thread so a prompt can give up after a timeout."""

    def __init__(self, stream: IO[str]) -> None:
        self._queue: queue.Queue[str | None] = queue.Queue()
        self._started = False
        self._stream = stream

    def _pump(self) -> None:
        for line in self._stream:
            self._queue.put(line)
        self._queue.put(None)

    def get(self, timeout: float | None) -> str | None:
        """Next line, or None at end of input. Raises Timeout when time runs out."""
        if not self._started:
            self._started = True
            threading.Thread(target=self._pump, daemon=True).start()
        try:
            line = self._queue.get(timeout=timeout)
        except queue.Empty:
            raise Timeout from None
        if line is None:
            self._queue.put(None)
        return line


# --- the session -------------------------------------------------------------------------


@dataclass
class Session:
    args: argparse.Namespace
    out: IO[str]
    reader: LineReader
    isatty: bool
    turn_count: int = 0

    @property
    def style(self) -> str:
        return "list" if self.args.list else "tower"

    def say(self, text: str = "") -> None:
        if not self.args.json:
            self.out.write(text + "\n")

    def human(self, player: str, n: int, rng: random.Random) -> ExternalAgent:
        timeout = self.args.move_timeout or None
        prompt = _Prompt(self, player, n, timeout)
        return ExternalAgent(prompt, timeout=timeout, fallback=RandomAgent(rng))


class _Prompt:
    """The injected ``ask``: show the view, read a move, re-prompt on garbage."""

    def __init__(self, session: Session, player: str, n: int, timeout: float | None) -> None:
        self.s, self.player, self.n, self.timeout = session, player, n, timeout
        self.last_hand: int | None = None

    def __call__(
        self, observation: Observation, legal: Sequence[Action], timeout: float | None
    ) -> Action | None:
        self.last_hand = observation.hand
        index = self.s.turn_count + 1
        self.s.say()
        self.s.say(
            render_view(observation, self.player, index, self.n, legal, self.s.style, timeout)
        )
        deadline = None if timeout is None else time.monotonic() + timeout
        while True:
            self.s.out.write(f"{self.player}> ")
            self.s.out.flush()
            remaining = None if deadline is None else max(0.0, deadline - time.monotonic())
            try:
                line = self.s.reader.get(remaining)
            except Timeout:
                self.s.say()
                raise
            if line is None:
                self.s.say()
                return None
            try:
                return parse_action(line.strip())
            except RecordingFormatError:
                self.s.say(f"  {PROMPT_HELP}")


def _on_turn_factory(session: Session, agents: dict[str, Agent], prompts: dict[str, _Prompt]):
    live = any(a.kind == "human" for a in agents.values())

    def on_turn(turn: Turn, state: State) -> None:
        session.turn_count = turn.index
        if not live:
            return
        if turn.source == "timeout":
            session.say(
                f"  time is up: random move played for {turn.player}: "
                f"{_fmt(turn.action)}   [timeout]"
            )
        elif turn.source == "human":
            before = prompts[turn.player].last_hand
            session.say(
                "  " + describe_outcome(turn.action, turn.outcome, state.hands[turn.player], before)
            )
        else:
            session.say(f"Turn {turn.index}, player {turn.player}: {_describe_bot(turn, state)}")

    return on_turn


def _describe_bot(turn: Turn, state: State) -> str:
    """A bot's move with its effect spelled out, so shared-pole events stand out."""
    action, player = turn.action, turn.player
    if action.verb == "skip":
        return "skip"
    text = _fmt(action)
    if not turn.outcome.legal:
        return f"{text} → illegal: {turn.outcome.reason}. Turn wasted."
    shared = action.pole == 2
    if action.verb == "lift":
        held = state.hands[player]
        where = "from the shared pole" if shared else f"from pole {action.pole}"
        return f"{text} → took disk {held} {where}"
    disk = state.poles[pole_key(player, action.pole)][-1]  # type: ignore[arg-type]
    where = "on the shared pole" if shared else f"on pole {action.pole}"
    return f"{text} → put disk {disk} {where}"


def _fmt(action: Action) -> str:
    return action.verb if action.verb == "skip" else f"{action.verb} {action.pole}"


# --- output ----------------------------------------------------------------------------------


def _emit(
    session: Session, result: RunResult, start: State, meta: dict, saved: Path | None
) -> None:
    if session.args.json:
        payload = {
            **meta,
            "status": result.status,
            "winner": result.winner,
            "state": to_dict(result.final_state),
            "counts": counts(result),
            "turns": [
                {
                    "index": t.index,
                    "player": t.player,
                    "action": _fmt(t.action),
                    "legal": t.outcome.legal,
                    "reason": t.outcome.reason,
                    "source": t.source,
                }
                for t in result.turns
            ],
            "saved": str(saved) if saved else None,
        }
        session.out.write(json.dumps(payload, indent=2) + "\n")
        return
    if session.args.trace and result.turns:
        session.say()
        session.say(render_trace(result.turns, start=start))
    session.say()
    session.say(render_board(result.final_state, session.style))
    session.say()
    session.say(render_summary(result))
    if saved:
        session.say(f"saved: {saved}")


def _autosave(session: Session, rec: Recording, mode: str, seed: int) -> Path | None:
    args = session.args
    if getattr(args, "no_save", False):
        return None
    if getattr(args, "save", None):
        path = Path(args.save)
    else:
        folder = Path("recordings")
        folder.mkdir(exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        path = folder / f"{stamp}-{mode}-n{rec.n}-seed{seed}.json"
        k = 1
        while path.exists():
            path = folder / f"{stamp}-{mode}-n{rec.n}-seed{seed}-{k}.json"
            k += 1
    dump(rec, path)
    return path


# --- commands -----------------------------------------------------------------------------


def _schedule_pattern(args: argparse.Namespace, first: str) -> str:
    return rotate_to(args.schedule, first)  # ValueError -> exit 2 in main


def cmd_game(session: Session, sources: dict[str, str]) -> int:
    args = session.args
    rng = random.Random(args.seed)
    pattern = _schedule_pattern(args, args.first)
    agents: dict[str, Agent] = {}
    prompts: dict[str, _Prompt] = {}
    for p in ("A", "B"):
        if sources[p] == "human":
            agent = session.human(p, args.n, rng)
            prompts[p] = agent.ask  # type: ignore[assignment]
            agents[p] = agent
        else:
            agents[p] = RandomAgent(rng, allow_skip=not args.no_skip)
    mode = "random" if set(sources.values()) == {"random"} else "play"
    max_turns = args.max_turns or default_max_turns(args.n)
    session.say(
        f"Hanoi Crossing  n={args.n}  seed={args.seed}  schedule={pattern} "
        f"(repeats, max {max_turns} turns)"
    )
    session.say(f"A: {sources['A']}   B: {sources['B']}")
    start = initial_state(args.n)
    result = run(
        start,
        repeat(pattern, max_turns),
        agents,
        repetition_limit=args.repetition_limit or None,
        on_turn=_on_turn_factory(session, agents, prompts),
    )
    saved = _autosave(session, from_run(args.n, result), mode, args.seed)
    _emit(session, result, start, {"n": args.n, "seed": args.seed, "schedule": pattern}, saved)
    return EXIT_OK


def cmd_replay(session: Session) -> int:
    args = session.args
    try:
        rec = load(args.file)
    except (OSError, RecordingFormatError) as e:
        session.out.write(f"error: cannot replay {args.file}: {e}\n")
        return EXIT_BAD_FILE
    session.say(f"Hanoi Crossing  replay {args.file}  n={rec.n}  recorded turns={len(rec.moves)}")
    start = initial_state(rec.n)
    result = replay(rec)
    meta = {"n": rec.n, "seed": args.seed, "schedule": rec.turn_order, "file": args.file}
    if result.status != "unfinished" or not _wants_continue(session):
        _emit(session, result, start, meta, None)
        return EXIT_OK
    _emit(session, result, start, meta, None) if not args.json else None
    last = rec.turn_order[-1] if rec.turn_order else "B"
    pattern = _schedule_pattern(args, "B" if last == "A" else "A")
    rng = random.Random(args.seed)
    agents: dict[str, Agent] = {"A": RandomAgent(rng), "B": RandomAgent(rng)}
    max_turns = args.max_turns or default_max_turns(rec.n)
    session.say()
    session.say(
        f"continuing with random agents  seed={args.seed}  schedule={pattern} "
        f"(max {max_turns} turns)"
    )
    more = run(
        result.final_state,
        repeat(pattern, max_turns),
        agents,
        repetition_limit=args.repetition_limit or None,
    )
    tail = from_run(rec.n, more)
    combined = Recording(
        rec.n,
        rec.turn_order + tail.turn_order,
        rec.moves + tail.moves,
        (rec.sources or ("scripted",) * len(rec.moves)) + (tail.sources or ()),
    )
    saved = _autosave(session, combined, "continue", args.seed)
    _emit(
        session, more, result.final_state, {**meta, "schedule": pattern, "continued": True}, saved
    )
    return EXIT_OK


def _wants_continue(session: Session) -> bool:
    args = session.args
    if args.cont:
        return True
    if args.no_cont or args.json or not session.isatty:
        return False
    session.out.write("Game unfinished. Let random players finish it? [y/N] ")
    session.out.flush()
    try:
        answer = session.reader.get(None)
    except Timeout:
        return False
    return (answer or "").strip().lower() in ("y", "yes")


def cmd_recordings(session: Session) -> int:
    folder = Path(session.args.dir)
    files = sorted(folder.glob("*.json")) if folder.is_dir() else []
    if not files:
        session.out.write(f"no recordings in {folder}/\n")
        return EXIT_OK
    for path in files:
        try:
            rec = load(path)
        except RecordingFormatError as e:
            session.out.write(f"{path.name}  (invalid: {e})\n")
            continue
        m = re.search(r"seed(\d+)", path.name)
        seed = m.group(1) if m else "-"
        result = replay(rec)
        when = datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
        session.out.write(
            f"{path.name}  n={rec.n}  seed={seed}  turns={len(rec.moves)}  "
            f"status={result.status}  winner={result.winner or '-'}  {when}\n"
        )
    return EXIT_OK


# --- entry ---------------------------------------------------------------------------------


def main(
    argv: Sequence[str] | None = None,
    stdin: IO[str] | None = None,
    stdout: IO[str] | None = None,
    isatty: bool | None = None,
) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as e:
        return int(e.code) if isinstance(e.code, int) else EXIT_BAD_ARGS
    stdin = stdin if stdin is not None else sys.stdin
    out = stdout if stdout is not None else sys.stdout
    tty = isatty if isatty is not None else bool(getattr(stdin, "isatty", lambda: False)())
    session = Session(args, out, LineReader(stdin), tty)
    try:
        if args.command == "replay":
            return cmd_replay(session)
        if args.command == "random":
            return cmd_game(session, {"A": "random", "B": "random"})
        if args.command == "play":
            return cmd_game(session, {"A": args.a, "B": args.b})
        return cmd_recordings(session)
    except ValueError as e:  # bad --schedule / --first combinations
        out.write(f"error: {e}\n")
        return EXIT_BAD_ARGS


def entry() -> None:
    sys.exit(main())
