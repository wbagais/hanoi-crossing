"""Text for the terminal: turn view, board, turn lines, summary, JSON result.

Pure builders; nothing here prints. Style ``tower`` draws disks to scale, ``list``
uses bracket lists in the spec's cross layout.
"""

from collections.abc import Sequence

from .engine import SIDES, Action, Observation, State, to_dict
from .runner import RunResult, Turn

MARGIN = "   "
GAP = "    "
TITLE_WIDTH = 37


# --- towers and lists ----------------------------------------------------------------


def _width(n: int) -> int:
    """Column width: the largest disk (2n) needs 4n+1 chars; labels need 7; keep it odd."""
    return max(4 * n + 1, 7)


def _disk(d: int) -> str:
    return "=" * d + str(d) + "=" * d


def _column(disks: Sequence[int], n: int) -> list[str]:
    """Rows top->bottom for one pole; height 2n so every disk could stack here."""
    height = 2 * n
    return [
        (_disk(disks[i]) if i < len(disks) else "|").center(_width(n))
        for i in reversed(range(height))
    ]


def _towers(columns: Sequence[tuple[str, Sequence[int]]], n: int) -> list[str]:
    w = _width(n)
    cols = [_column(disks, n) for _, disks in columns]
    lines = [(MARGIN + GAP.join(c[r] for c in cols)).rstrip() for r in range(2 * n)]
    lines.append(MARGIN + GAP.join("-" * w for _ in cols))
    lines.append((MARGIN + GAP.join(label.center(w) for label, _ in columns)).rstrip())
    return lines


def _hand(held: int | None, as_list: bool) -> str:
    if held is None:
        return "-"
    return str(held) if as_list else f"({held})"


def _brackets(disks: Sequence[int]) -> str:
    return "[" + ", ".join(str(d) for d in disks) + "]"


def render_view(
    observation: Observation,
    player: str,
    index: int,
    n: int,
    legal: Sequence[Action],
    as_list: bool = False,
    seconds: float | None = None,
) -> str:
    """One player's view before their move: header, poles, legal actions."""
    hand = _hand(observation.hand, as_list)
    header = f"{f'Turn {index}, player {player}':<{TITLE_WIDTH}}hand: {hand}"
    legal_text = "legal: " + ", ".join(str(a) for a in legal)
    if seconds is not None:
        legal_text += f"       ({seconds:g} s)"
    if as_list:
        poles = "   ".join(f"pole {i}: {_brackets(observation.poles[i])}" for i in (1, 2, 3))
        return "\n".join([header, "  " + poles, "  " + legal_text])
    columns = [(f"pole {i}", observation.poles[i]) for i in (1, 2, 3)]
    return "\n".join([header, "", *_towers(columns, n), "", "  " + legal_text])


def render_board(state: State, as_list: bool = False) -> str:
    """The full final board, both sides (R12)."""
    p, hands = state.poles, state.hands
    if as_list:
        middle = (
            f"  1b: {_brackets(p['1b'])} --- [2]: {_brackets(p['2'])} --- 3b: {_brackets(p['3b'])}"
        )
        pad = " " * middle.index("[2]")
        return "\n".join(
            [
                f"{pad}1a: {_brackets(p['1a'])}",
                f"{pad} |",
                middle,
                f"{pad} |",
                f"{pad}3a: {_brackets(p['3a'])}",
                f"  hand A: {_hand(hands['A'], True)}   hand B: {_hand(hands['B'], True)}",
            ]
        )
    lines: list[str] = []
    for player, side in SIDES.items():
        if lines:
            lines.append("")
        columns = [(side[1], p[side[1]]), ("[2]", p[side[2]]), (side[3], p[side[3]])]
        title = f"{player} side"
        lines += [f"{title:<{TITLE_WIDTH}}hand {player}: {_hand(hands[player], False)}", ""]
        lines += _towers(columns, state.n)
    return "\n".join(lines)


# --- turns ---------------------------------------------------------------------------


def describe_turn(turn: Turn) -> str:
    """What a turn did, in words: ``took disk 1 from the shared pole``."""
    outcome, action = turn.outcome, turn.action
    if not outcome.legal:
        return f"illegal: {outcome.reason}. Turn wasted."
    if action.verb == "skip":
        return "skip"
    where = "the shared pole" if action.pole == 2 else f"pole {action.pole}"
    if action.verb == "lift":
        return f"took disk {outcome.disk} from {where}"
    return f"put disk {outcome.disk} on {where}"


def move_text(turn: Turn) -> str:
    """The move and its effect: ``lift 2 → took disk 1 from the shared pole``."""
    if turn.action.verb == "skip" and turn.outcome.legal:
        return "skip"
    return f"{turn.action} → {describe_turn(turn)}"


def render_trace(turns: Sequence[Turn]) -> str:
    """One line per turn: ``index player move → effect [source]``.

    ``[human]`` and ``[timeout]`` are always shown; ``[random]`` / ``[scripted]``
    only when the game mixes sources.
    """
    mixed = len({t.source for t in turns}) > 1
    lines = []
    for t in turns:
        mark = f" [{t.source}]" if mixed or t.source in ("human", "timeout") else ""
        lines.append(f"{t.index} {t.player} {move_text(t)}{mark}")
    return "\n".join(lines)


# --- results -------------------------------------------------------------------------


def counts(result: RunResult) -> dict[str, int]:
    turns = result.turns
    return {
        "played": len(turns),
        "illegal": sum(1 for t in turns if not t.outcome.legal),
        "skipped": sum(1 for t in turns if t.outcome.legal and t.action.verb == "skip"),
        "timeouts": sum(1 for t in turns if t.source == "timeout"),
        "unplayed": result.unplayed,
    }


def render_summary(result: RunResult) -> str:
    c = counts(result)
    return (
        f"status {result.status} · winner {result.winner or '-'} · played {c['played']} · "
        f"illegal {c['illegal']} · skipped {c['skipped']} · timeouts {c['timeouts']} · "
        f"unplayed {c['unplayed']}"
    )


def result_dict(result: RunResult) -> dict:
    """The result as plain JSON data (for ``--json``)."""
    return {
        "status": result.status,
        "winner": result.winner,
        "state": to_dict(result.final_state),
        "counts": counts(result),
        "turns": [
            {
                "index": t.index,
                "player": t.player,
                "action": str(t.action),
                "legal": t.outcome.legal,
                "reason": t.outcome.reason,
                "source": t.source,
            }
            for t in result.turns
        ],
    }
