"""The one game loop: play_turn, run, schedules (R6, R9, R10, R13, T2, T3, I5)."""

import random

import pytest
from hanoi_crossing.runner import (
    RunResult,
    Turn,
    from_string,
    play_turn,
    random_schedule,
    repeat,
    rotate_to,
    run,
    to_string,
)

from hanoi_crossing.agents import ExternalAgent, RandomAgent, ScriptedAgent, Timeout
from hanoi_crossing.engine import Action, State, initial_state, winner

L1, P2, P3, SKIP = Action("lift", 1), Action("place", 2), Action("place", 3), Action("skip")


# --- schedules -----------------------------------------------------------------


def test_from_string_and_to_string() -> None:
    assert from_string("ABA") == ("A", "B", "A")
    assert to_string(("A", "B", "A")) == "ABA"
    assert from_string("") == ()


@pytest.mark.parametrize("bad", ["ABC", "ab", "A B"])
def test_from_string_rejects_other_letters(bad: str) -> None:
    with pytest.raises(ValueError):
        from_string(bad)


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


def test_random_schedule_is_seeded_and_only_a_b() -> None:
    s1 = random_schedule(random.Random(4), 20)
    s2 = random_schedule(random.Random(4), 20)
    assert s1 == s2 and len(s1) == 20 and set(s1) <= {"A", "B"}


# --- play_turn -------------------------------------------------------------------


def test_play_turn_records_action_outcome_and_source() -> None:
    s = initial_state(1)
    s2, turn = play_turn(s, "A", ScriptedAgent([L1]), index=1)
    assert s2.hands["A"] == 1
    assert turn == Turn(index=1, player="A", action=L1, outcome=turn.outcome, source="scripted")
    assert turn.outcome.legal


def test_play_turn_source_is_timeout_when_fallback_answered() -> None:
    def ask(o, lg, t):  # noqa: ANN001
        raise Timeout

    agent = ExternalAgent(ask, timeout=0.01, fallback=RandomAgent(random.Random(0)))
    _, turn = play_turn(initial_state(1), "B", agent, index=3)
    assert turn.source == "timeout" and turn.index == 3 and turn.player == "B"


# --- run: spec example, unplayed, unfinished, stalemate -----------------------------


def _scripted(a: list[Action], b: list[Action]) -> dict:
    return {"A": ScriptedAgent(a), "B": ScriptedAgent(b)}


def test_run_spec_n1_example() -> None:
    result = run(initial_state(1), from_string("ABA"), _scripted([L1, P3], [L1]))
    assert isinstance(result, RunResult)
    assert result.status == "won" and result.winner == "A"
    assert [t.player for t in result.turns] == ["A", "B", "A"]
    assert result.unplayed == 0
    assert result.final_state.poles["3a"] == (1,) and result.final_state.hands["B"] == 2


def test_run_counts_unplayed_entries_after_the_win() -> None:
    result = run(initial_state(1), from_string("ABABB"), _scripted([L1, P3], [L1, SKIP, SKIP]))
    assert result.status == "won" and len(result.turns) == 3 and result.unplayed == 2


def test_run_schedule_exhausted_is_unfinished() -> None:
    result = run(initial_state(1), from_string("AB"), _scripted([L1], [L1]))
    assert result.status == "unfinished" and result.winner is None and result.unplayed == 0
    assert result.final_state.hands == {"A": 1, "B": 2}


def test_run_empty_schedule() -> None:
    result = run(initial_state(1), (), _scripted([], []))
    assert result.status == "unfinished" and result.turns == ()


def test_run_n2_example_with_illegal_move_and_skip() -> None:
    a = [L1, P2, L1, P3, Action("lift", 2), P3]
    b = [L1, P2, SKIP]
    result = run(initial_state(2), from_string("AABBAABAA"), _scripted(a, b))
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


def _fake_ask(rng: random.Random):  # noqa: ANN202
    def ask(observation, legal, timeout):  # noqa: ANN001
        return rng.choice(list(legal))

    return ask


def _agent(kind: str, rng: random.Random, script: list[Action]):  # noqa: ANN202
    if kind == "random":
        return RandomAgent(rng)
    if kind == "scripted":
        return ScriptedAgent(script)
    return ExternalAgent(_fake_ask(rng))


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
