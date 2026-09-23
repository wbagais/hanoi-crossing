"""The JSON recording format and the files that hold it (T2, T9)::

    {"n": 2, "turn_order": "AABBAABAA", "moves": ["lift 1", "place 2", "skip"],
     "sources": ["human", "human", "timeout"]}

``turn_order`` is separate because the spec calls the turn order external;
``sources`` is optional and informational. A replay restarts from the initial
position, so the file holds moves, never board states.
"""

import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .agents import ScriptedAgent
from .engine import PLAYERS, Action, check, initial_state, is_positive_int
from .runner import RunResult, parse_schedule, run

SOURCES = ("human", "random", "scripted", "timeout")
KEYS = {"n", "turn_order", "moves", "sources"}


class RecordingFormatError(ValueError):
    """The recording text or dict is not a valid recording."""


@dataclass(frozen=True)
class Recording:
    """A whole game as moves. Validated on construction, however it was built."""

    n: int
    turn_order: str
    moves: tuple[Action, ...]
    sources: tuple[str, ...] | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "moves", tuple(self.moves))
        if self.sources is not None:
            object.__setattr__(self, "sources", tuple(self.sources))
        invalid = RecordingFormatError
        check(is_positive_int(self.n), f"n must be a positive integer, got {self.n!r}", invalid)
        check(isinstance(self.turn_order, str), "turn_order must be a string of A and B", invalid)
        try:
            parse_schedule(self.turn_order)
        except ValueError as e:
            raise invalid(str(e)) from None
        check(
            len(self.turn_order) == len(self.moves),
            f"turn_order has {len(self.turn_order)} entries, moves has {len(self.moves)}",
            invalid,
        )
        check(all(isinstance(m, Action) for m in self.moves), "moves must be Actions", invalid)
        if self.sources is not None:
            check(len(self.sources) == len(self.moves), "sources need one entry per move", invalid)
            check(all(isinstance(s, str) for s in self.sources), "sources must be strings", invalid)
            unknown = sorted(set(self.sources) - set(SOURCES))
            check(not unknown, f"unknown sources {unknown}; expected {SOURCES}", invalid)


# --- text and files ------------------------------------------------------------------


def loads(text: str) -> Recording:
    invalid = RecordingFormatError
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise invalid(f"not valid JSON: {e}") from None
    shape = isinstance(data, dict) and {"n", "turn_order", "moves"} <= set(data) <= KEYS
    check(shape, "recording must be an object: n, turn_order, moves[, sources]", invalid)
    moves, sources = data["moves"], data.get("sources")
    check(isinstance(moves, list) and isinstance(sources, list | None), "expected lists", invalid)
    try:
        actions = tuple(Action.parse(m) for m in moves)
    except ValueError as e:
        raise invalid(str(e)) from None
    return Recording(data["n"], data["turn_order"], actions, sources)


def dumps(rec: Recording) -> str:
    data: dict = {"n": rec.n, "turn_order": rec.turn_order, "moves": [str(m) for m in rec.moves]}
    if rec.sources is not None:
        data["sources"] = list(rec.sources)
    return json.dumps(data, indent=2) + "\n"


def load(path: str | Path) -> Recording:
    try:
        text = Path(path).read_text(encoding="utf-8")
    except UnicodeDecodeError as e:
        raise RecordingFormatError(f"not UTF-8 text: {e}") from None
    return loads(text)


def dump(rec: Recording, path: str | Path) -> None:
    Path(path).write_text(dumps(rec), encoding="utf-8")


def autosave_path(folder: Path, mode: str, n: int, seed: int) -> Path:
    """A fresh file name such as ``20260921-221500-random-n2-seed0.json``; creates the folder."""
    folder.mkdir(parents=True, exist_ok=True)
    stem = f"{datetime.now():%Y%m%d-%H%M%S}-{mode}-n{n}-seed{seed}"
    path, k = folder / f"{stem}.json", 1
    while path.exists():
        path, k = folder / f"{stem}-{k}.json", k + 1
    return path


def seed_in_name(path: Path) -> str | None:
    """The seed written into an autosaved file name, if there is one."""
    match = re.search(r"seed(-?\d+)", path.name)
    return match.group(1) if match else None


# --- games <-> recordings ------------------------------------------------------------


def from_run(n: int, result: RunResult) -> Recording:
    """Turn a played game into a recording that ``replay`` reproduces exactly."""
    return Recording(
        n=n,
        turn_order="".join(t.player for t in result.turns),
        moves=tuple(t.action for t in result.turns),
        sources=tuple(t.source for t in result.turns),
    )


def append_run(rec: Recording, result: RunResult) -> Recording:
    """``rec`` followed by the turns of ``result``: the whole continued game (D35)."""
    tail = from_run(rec.n, result)
    head_sources = rec.sources or ("scripted",) * len(rec.moves)
    return Recording(
        rec.n,
        rec.turn_order + tail.turn_order,
        rec.moves + tail.moves,
        head_sources + tail.sources,
    )


def replay(rec: Recording) -> RunResult:
    """Re-play a recording from the initial position through the one runner."""
    moves_of: dict[str, list[Action]] = {p: [] for p in PLAYERS}
    for player, move in zip(rec.turn_order, rec.moves, strict=True):
        moves_of[player].append(move)
    agents = {p: ScriptedAgent(moves) for p, moves in moves_of.items()}
    return run(initial_state(rec.n), parse_schedule(rec.turn_order), agents)
