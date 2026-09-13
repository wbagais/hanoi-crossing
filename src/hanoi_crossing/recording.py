"""The JSON recording format (T2, T9). A format, not a runner.

.. code-block:: json

    {"n": 2, "turn_order": "AABBAABAA",
     "moves": ["lift 1", "place 2", "skip"],
     "sources": ["human", "human", "timeout"]}

``turn_order`` is kept separate from ``moves`` because the spec calls the turn
order external. ``sources`` is optional and informational: a replay reproduces
the moves exactly and keeps the original sources for display. A replay always
restarts from the initial position; the file holds moves, never board states.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .agents import ScriptedAgent
from .engine import PLAYERS, Action, Player, initial_state
from .runner import RunResult, from_string, run

SOURCES = ("human", "random", "scripted", "timeout")


class RecordingFormatError(ValueError):
    """The recording text or dict is not a valid recording."""


@dataclass(frozen=True)
class Recording:
    n: int
    turn_order: str
    moves: tuple[str, ...]
    sources: tuple[str, ...] | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "moves", tuple(self.moves))
        if self.sources is not None:
            object.__setattr__(self, "sources", tuple(self.sources))
        _validate(self)


def parse_action(text: str) -> Action:
    """``"lift 1"`` / ``"place 3"`` / ``"skip"`` -> Action."""
    if not isinstance(text, str):
        raise RecordingFormatError(f"move must be a string, got {text!r}")
    parts = text.split()
    if parts == ["skip"]:
        return Action("skip")
    if len(parts) == 2 and parts[0] in ("lift", "place") and parts[1] in ("1", "2", "3"):
        return Action(parts[0], int(parts[1]))  # type: ignore[arg-type]
    raise RecordingFormatError(
        f"bad move {text!r}; expected 'lift N', 'place N' (N=1..3) or 'skip'"
    )


def format_action(action: Action) -> str:
    return action.verb if action.verb == "skip" else f"{action.verb} {action.pole}"


def _validate(rec: Recording) -> None:
    if not isinstance(rec.n, int) or isinstance(rec.n, bool) or rec.n < 1:
        raise RecordingFormatError(f"n must be a positive integer, got {rec.n!r}")
    if not isinstance(rec.turn_order, str):
        raise RecordingFormatError("turn_order must be a string of A and B")
    try:
        from_string(rec.turn_order)
    except ValueError as e:
        raise RecordingFormatError(str(e)) from None
    if len(rec.turn_order) != len(rec.moves):
        raise RecordingFormatError(
            f"turn_order has {len(rec.turn_order)} entries but moves has {len(rec.moves)}"
        )
    for move in rec.moves:
        parse_action(move)
    if rec.sources is not None:
        if len(rec.sources) != len(rec.moves):
            raise RecordingFormatError("sources must have one entry per move")
        bad = sorted(set(rec.sources) - set(SOURCES))
        if bad:
            raise RecordingFormatError(f"unknown sources {bad}; expected {SOURCES}")


def loads(text: str) -> Recording:
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise RecordingFormatError(f"not valid JSON: {e}") from None
    if not isinstance(data, dict):
        raise RecordingFormatError("recording must be a JSON object")
    allowed = {"n", "turn_order", "moves", "sources"}
    if not {"n", "turn_order", "moves"} <= set(data) or not set(data) <= allowed:
        raise RecordingFormatError(
            f"recording keys must be n, turn_order, moves[, sources]; got {sorted(data)}"
        )
    if not isinstance(data["moves"], list):
        raise RecordingFormatError("moves must be a list")
    sources = data.get("sources")
    if sources is not None and not isinstance(sources, list):
        raise RecordingFormatError("sources must be a list")
    return Recording(
        data["n"], data["turn_order"], tuple(data["moves"]), sources and tuple(sources)
    )


def dumps(rec: Recording) -> str:
    data: dict = {"n": rec.n, "turn_order": rec.turn_order, "moves": list(rec.moves)}
    if rec.sources is not None:
        data["sources"] = list(rec.sources)
    return json.dumps(data, indent=2) + "\n"


def load(path: str | Path) -> Recording:
    return loads(Path(path).read_text(encoding="utf-8"))


def dump(rec: Recording, path: str | Path) -> None:
    Path(path).write_text(dumps(rec), encoding="utf-8")


def to_agents(rec: Recording) -> dict[Player, ScriptedAgent]:
    """Split the moves into one scripted agent per player, in turn order."""
    per_player: dict[Player, list[Action]] = {p: [] for p in PLAYERS}
    for player, move in zip(rec.turn_order, rec.moves, strict=True):
        per_player[player].append(parse_action(move))  # type: ignore[index]
    return {p: ScriptedAgent(moves) for p, moves in per_player.items()}


def from_run(n: int, result: RunResult) -> Recording:
    """Turn a played game into a recording that ``replay`` reproduces exactly."""
    return Recording(
        n=n,
        turn_order="".join(t.player for t in result.turns),
        moves=tuple(format_action(t.action) for t in result.turns),
        sources=tuple(t.source for t in result.turns),
    )


def replay(rec: Recording) -> RunResult:
    """Re-play a recording from the initial position through the one runner."""
    return run(initial_state(rec.n), from_string(rec.turn_order), to_agents(rec))
