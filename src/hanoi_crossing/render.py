"""Text rendering for the CLI: turn view, final board, trace, summary.

Pure string builders; nothing here prints. Two styles: ``tower`` (default) draws
disks to scale, ``list`` shows poles as bracket lists in the spec's cross layout.
"""

from __future__ import annotations

from collections.abc import Sequence

from .engine import Action, Observation, Outcome, State, initial_state, step
from .recording import format_action
from .runner import RunResult, Turn

MARGIN = "   "
GAP = "    "
TITLE_WIDTH = 37


def _width(n: int) -> int:
    """Column width: the largest disk (2n) needs 4n+1 chars; labels need 7; keep it odd."""
    return max(4 * n + 1, 7)


def _disk(d: int) -> str:
    return "=" * d + str(d) + "=" * d


def _column(disks: Sequence[int], n: int) -> list[str]:
    """Rows top->bottom for one pole; height 2n so every disk could stack here."""
    w, h = _width(n), 2 * n
    rows = []
    for r in range(h):
        i = h - 1 - r
        rows.append((_disk(disks[i]) if i < len(disks) else "|").center(w))
    return rows


def _towers(columns: Sequence[tuple[str, Sequence[int]]], n: int) -> list[str]:
    w = _width(n)
    cols = [_column(disks, n) for _, disks in columns]
    lines = [(MARGIN + GAP.join(c[r] for c in cols)).rstrip() for r in range(2 * n)]
    lines.append(MARGIN + GAP.join("-" * w for _ in cols))
    lines.append((MARGIN + GAP.join(label.center(w) for label, _ in columns)).rstrip())
    return lines


def _hand(held: int | None, style: str) -> str:
    if held is None:
        return "-"
    return f"({held})" if style == "tower" else str(held)


def _brackets(disks: Sequence[int]) -> str:
    return "[" + ", ".join(str(d) for d in disks) + "]"


def render_view(
    observation: Observation,
    player: str,
    index: int,
    n: int,
    legal: Sequence[Action],
    style: str = "tower",
    seconds: float | None = None,
) -> str:
    """One player's view before their move: header, poles, legal actions."""
    header = (
        f"{f'Turn {index}, player {player}':<{TITLE_WIDTH}}hand: {_hand(observation.hand, style)}"
    )
    legal_text = "legal: " + ", ".join(format_action(a) for a in legal)
    if seconds is not None:
        legal_text += f"       ({seconds:g} s)"
    if style == "list":
        poles = "   ".join(f"pole {i}: {_brackets(observation.poles[i])}" for i in (1, 2, 3))
        return "\n".join([header, "  " + poles, "  " + legal_text])
    columns = [(f"pole {i}", observation.poles[i]) for i in (1, 2, 3)]
    return "\n".join([header, "", *_towers(columns, n), "", "  " + legal_text])


def render_board(state: State, style: str = "tower") -> str:
    """The full final board, both sides (R12)."""
    p = state.poles
    if style == "list":
        middle = (
            f"  1b: {_brackets(p['1b'])} --- [2]: {_brackets(p['2'])} --- 3b: {_brackets(p['3b'])}"
        )
        col = middle.index("[2]")
        pad = " " * col
        return "\n".join(
            [
                f"{pad}1a: {_brackets(p['1a'])}",
                f"{pad} |",
                middle,
                f"{pad} |",
                f"{pad}3a: {_brackets(p['3a'])}",
                f"  hand A: {_hand(state.hands['A'], style)}   "
                f"hand B: {_hand(state.hands['B'], style)}",
            ]
        )
    n = state.n
    side_a = _towers([("1a", p["1a"]), ("[2]", p["2"]), ("3a", p["3a"])], n)
    side_b = _towers([("1b", p["1b"]), ("[2]", p["2"]), ("3b", p["3b"])], n)
    head_a = f"{'A side':<{TITLE_WIDTH}}hand A: {_hand(state.hands['A'], style)}"
    head_b = f"{'B side':<{TITLE_WIDTH}}hand B: {_hand(state.hands['B'], style)}"
    return "\n".join([head_a, "", *side_a, "", head_b, "", *side_b])


def describe_outcome(
    action: Action, outcome: Outcome, held_after: int | None = None, disk: int | None = None
) -> str:
    if not outcome.legal:
        return f"illegal: {outcome.reason}. Turn wasted."
    if action.verb == "skip":
        return "skip"
    if action.verb == "lift":
        return f"ok, holding {held_after}"
    return f"ok, placed {disk} on pole {action.pole}"


def _describe_by_replay(turns: Sequence[Turn], start: State) -> list[str]:
    """Re-step the turns to learn which disk moved, for human-readable lines."""
    out: list[str] = []
    state = start
    for t in turns:
        before = state.hands[t.player]
        state, _ = step(state, t.player, t.action)
        out.append(describe_outcome(t.action, t.outcome, state.hands[t.player], before))
    return out


def render_trace(turns: Sequence[Turn], n: int | None = None, start: State | None = None) -> str:
    """One line per turn: ``idx player action -> result [source]``.

    ``[human]`` and ``[timeout]`` are always shown; ``[random]`` / ``[scripted]``
    only when the game mixes sources.
    """
    start = start or initial_state(n or 1)
    texts = _describe_by_replay(turns, start)
    kinds = {t.source for t in turns}
    lines = []
    for t, text in zip(turns, texts, strict=True):
        mark = f" [{t.source}]" if t.source in ("human", "timeout") or len(kinds) > 1 else ""
        lines.append(f"{t.index} {t.player} {format_action(t.action)} → {text}{mark}")
    return "\n".join(lines)


def counts(result: RunResult) -> dict[str, int]:
    return {
        "played": len(result.turns),
        "illegal": sum(1 for t in result.turns if not t.outcome.legal),
        "skipped": sum(1 for t in result.turns if t.outcome.legal and t.action.verb == "skip"),
        "timeouts": sum(1 for t in result.turns if t.source == "timeout"),
        "unplayed": result.unplayed,
    }


def render_summary(result: RunResult) -> str:
    c = counts(result)
    return (
        f"status {result.status} · winner {result.winner or '-'} · played {c['played']} · "
        f"illegal {c['illegal']} · skipped {c['skipped']} · timeouts {c['timeouts']} · "
        f"unplayed {c['unplayed']}"
    )
