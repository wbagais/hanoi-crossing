"""The one game loop: play_turn, run, schedules (R6, R9, R10, R13, T2, T3, I5)."""

import random

import pytest

from hanoi_crossing.agents import RandomAgent, ScriptedAgent
from hanoi_crossing.engine import Action, State, initial_state, winner
from hanoi_crossing.runner import (
    RunResult,
    StopGame,
    Turn,
    parse_schedule,
    play_turn,
    repeat,
    rotate_to,
    run,
)

L1, P2, P3, SKIP = Action("lift", 1), Action("place", 2), Action("place", 3), Action("skip")


# --- schedules -----------------------------------------------------------------


def test_parse_schedule() -> None:
    assert parse_schedule("ABA") == ("A", "B", "A")
    assert parse_schedule("") == ()


@pytest.mark.parametrize("bad", ["ABC", "ab", "A B"])
def test_parse_schedule_rejects_other_letters(bad: str) -> None:
    with pytest.raises(ValueError):
        parse_schedule(bad)


def test_repeat_fills_length() -> None:
    assert repeat("AB", 5) == ("A", "B", "A", "B", "A")
    assert repeat("AAB", 4) == ("A", "A", "B", "A")
    assert repeat("A", 3) == ("A", "A", "A")
    assert repeat("AB", 0) == ()
    with pytest.raises(ValueError):
        repeat("", 3)


def test_rotate_to_starts_at_first_occurrence() -> None:
    assert rotate_to("AB", "B") == "BA"
    assert rotate_to("AAB", "B") == "BAA"
    assert rotate_to("AAB", "A") == "AAB"
    with pytest.raises(ValueError):
        rotate_to("A", "B")


# --- play_turn -------------------------------------------------------------------


def test_play_turn_records_action_outcome_and_source() -> None:
    s = initial_state(1)
    s2, turn = play_turn(s, "A", ScriptedAgent([L1]), index=1)
    assert s2.hands["A"] == 1
    assert turn == Turn(index=1, player="A", action=L1, outcome=turn.outcome, source="scripted")
    assert turn.outcome.legal


class Labelled:
    """An agent that labels each move itself, as a human agent does after a timeout."""

    def __init__(self, source: str) -> None:
        self.source = source

    def choose(self, observation, legal):  # noqa: ANN001, ANN201
        return legal[0]


def test_play_turn_copies_the_agents_source_label() -> None:
    _, turn = play_turn(initial_state(1), "B", Labelled("timeout"), index=3)
    assert turn.source == "timeout" and turn.index == 3 and turn.player == "B"


# --- run: spec example, unplayed, unfinished, stalemate -----------------------------


def _scripted(a: list[Action], b: list[Action]) -> dict:
    return {"A": ScriptedAgent(a), "B": ScriptedAgent(b)}


def test_run_spec_n1_example() -> None:
    result = run(initial_state(1), parse_schedule("ABA"), _scripted([L1, P3], [L1]))
    assert isinstance(result, RunResult)
    assert result.status == "won" and result.winner == "A"
    assert [t.player for t in result.turns] == ["A", "B", "A"]
    assert result.unplayed == 0
    assert result.final_state.poles["3a"] == (1,) and result.final_state.hands["B"] == 2


def test_run_counts_unplayed_entries_after_the_win() -> None:
    result = run(initial_state(1), parse_schedule("ABABB"), _scripted([L1, P3], [L1, SKIP, SKIP]))
    assert result.status == "won" and len(result.turns) == 3 and result.unplayed == 2


def test_run_schedule_exhausted_is_unfinished() -> None:
    result = run(initial_state(1), parse_schedule("AB"), _scripted([L1], [L1]))
    assert result.status == "unfinished" and result.winner is None and result.unplayed == 0
    assert result.final_state.hands == {"A": 1, "B": 2}


def test_run_empty_schedule() -> None:
    result = run(initial_state(1), (), _scripted([], []))
    assert result.status == "unfinished" and result.turns == ()


def test_run_n2_example_with_illegal_move_and_skip() -> None:
    a = [L1, P2, L1, P3, Action("lift", 2), P3]
    b = [L1, P2, SKIP]
    result = run(initial_state(2), parse_schedule("AABBAABAA"), _scripted(a, b))
    assert result.status == "won" and result.winner == "A" and len(result.turns) == 9
    t4 = result.turns[3]
    assert t4.player == "B" and not t4.outcome.legal
    assert t4.outcome.reason == "disk 2 cannot go on disk 1"
    assert result.turns[6].action == SKIP and result.turns[6].outcome.legal
    assert result.final_state.poles["3a"] == (3, 1)


def test_run_stalemate_on_repeated_position() -> None:
    skippers = _scripted([SKIP] * 10, [SKIP] * 10)
    result = run(initial_state(1), repeat("AB", 10), skippers, repetition_limit=3)
    # (state, A) seen at entries 1, 3, 5 -> third time triggers before turn 5
    assert result.status == "stalemate" and result.winner is None
    assert len(result.turns) == 4 and result.unplayed == 6


@pytest.mark.parametrize("limit", [1, -3])
def test_run_rejects_a_repetition_limit_below_two(limit: int) -> None:
    with pytest.raises(ValueError):
        run(initial_state(1), repeat("AB", 4), _scripted([SKIP] * 4, [SKIP] * 4), limit)


def test_run_without_repetition_limit_runs_to_unfinished() -> None:
    skippers = _scripted([SKIP] * 10, [SKIP] * 10)
    result = run(initial_state(1), repeat("AB", 10), skippers)
    assert result.status == "unfinished" and len(result.turns) == 10


@pytest.mark.parametrize("n", [1, 2, 3])
def test_random_vs_random_finishes_with_a_winner(n: int) -> None:
    rng = random.Random(n)
    agents = {"A": RandomAgent(rng), "B": RandomAgent(rng)}
    result = run(initial_state(n), repeat("AB", 5000), agents)
    assert result.status == "won", result.status
    assert winner(result.final_state) == result.winner
    for turn in result.turns:
        assert turn.source == "random"
        assert turn.outcome.legal, "random agents only pick legal actions"


def _agent(kind: str, rng: random.Random, script: list[Action]):  # noqa: ANN202
    if kind == "random":
        return RandomAgent(rng)
    if kind == "scripted":
        return ScriptedAgent(script)
    return Labelled("human")


@pytest.mark.parametrize("kind_a", ["random", "scripted", "external"])
@pytest.mark.parametrize("kind_b", ["random", "scripted", "external"])
def test_all_nine_agent_combinations_run_cleanly(kind_a: str, kind_b: str) -> None:
    rng = random.Random(hash((kind_a, kind_b)) % 1000)
    script = [L1, P3] + [SKIP] * 200
    agents = {"A": _agent(kind_a, rng, list(script)), "B": _agent(kind_b, rng, list(script))}
    result = run(initial_state(1), repeat("AB", 200), agents)
    assert result.status in ("won", "unfinished")
    expected = {"random": "random", "scripted": "scripted", "external": "human"}
    for turn in result.turns:
        assert turn.source == expected[kind_a if turn.player == "A" else kind_b]
    assert isinstance(result.final_state, State)


def test_run_calls_on_turn_after_every_played_turn() -> None:
    seen: list[tuple[int, str, str]] = []

    def on_turn(turn: Turn) -> None:
        seen.append((turn.index, turn.player, str(turn.action)))

    run(initial_state(1), parse_schedule("ABA"), _scripted([L1, P3], [L1]), on_turn=on_turn)
    assert seen == [(1, "A", "lift 1"), (2, "B", "lift 1"), (3, "A", "place 3")]


def test_stop_game_raised_by_an_agent_ends_the_run_as_unfinished() -> None:
    class Quitter:
        source = "human"

        def choose(self, observation, legal):  # noqa: ANN001, ANN202
            raise StopGame("player quit")

    agents = {"A": ScriptedAgent([L1, P3]), "B": Quitter()}
    result = run(initial_state(1), parse_schedule("ABAB"), agents)
    assert result.status == "unfinished" and result.winner is None
    assert len(result.turns) == 1 and result.unplayed == 3
    assert result.final_state.hands["A"] == 1
