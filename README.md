# Hanoi Crossing

A two-player Tower of Hanoi variant with a shared middle pole: a pure Python game
engine, a replay frontend, and a random-play frontend. **Status: work in progress**
(stages 0–2 of 4 done; see `plans/PLAN.md`).

The task specification is in [`SPEC.md`](SPEC.md).

## Quick start

```bash
uv sync
uv run pytest
```

CLI commands arrive in stage 3 (`hanoi replay`, `hanoi random`, `hanoi play`).

## Rules as read

See [`docs/REQUIREMENTS.md`](docs/REQUIREMENTS.md) for the spec restated as
checkable items, and the worked N = 1 example in
[`examples/spec_n1.json`](examples/spec_n1.json).

## Design decisions

Every decision, with its reason and the alternatives rejected, is in
[`docs/DECISIONS.md`](docs/DECISIONS.md). This section will summarize it once the
engine and frontends exist.

## Engine

`src/hanoi_crossing/engine.py`, 267 lines, no dependencies, no I/O, no randomness.
Pure functions over an immutable `State`:

| Function | Purpose |
|---|---|
| `initial_state(n)` | starting position: A has odd disks, B even |
| `observe(state, player)` | the partial view that player may see |
| `legal_actions(state, player)` | the subset of the seven actions legal now |
| `step(state, player, action)` | apply one action; returns a new state and an outcome |
| `winner(state)` | who has won, computed from the board |
| `to_dict` / `from_dict` | JSON round trip |

The seven actions are `lift 1..3`, `place 1..3`, `skip`, numbered from the acting
player's side. An illegal move returns the same state object with a reason; a
finished game rejects everything. Both players are checked for a win after every
step because an opponent's lift from the shared pole can complete your win.

## Agents, runner, recording

- `agents.py` answers "how is a move chosen". An agent gets an `Observation` and
  the legal actions and returns one `Action`; it never sees the full state.
  `RandomAgent` picks uniformly (seeded), `ScriptedAgent` replays recorded moves
  verbatim, `ExternalAgent` asks an injected function (a prompt, a UI, a model)
  and falls back to another agent on timeout.
- `runner.py` is the only game loop: `play_turn` plays one turn, `run` loops it
  over an external schedule and stops on a win, a stalemate (repeated position),
  or the end of the schedule. Every turn is recorded with its outcome and source.
- `recording.py` is the JSON file format:

  ```json
  {"n": 1, "turn_order": "ABA", "moves": ["lift 1", "lift 1", "place 3"]}
  ```

  Replay is the same loop with both players scripted from the file, restarted
  from the initial position. A random game can be saved with `from_run` and
  replayed to the identical final state.

## Frontends

_Stage 3._

## Reuse: RL loop and simulation service (not built)

_Stage 4: how an RL wrapper and a game service would use the engine unchanged._

## AI usage

Claude Code (Claude Fable 5.1) was used throughout, under human direction:

- **Planning:** a long design conversation to read the rules, find their edge cases
  (opponent-assisted wins, disks crossing sides, stalemates), and settle every
  interpretation; the plan in `plans/PLAN.md` and the two docs in `docs/` came out
  of it. Every choice was proposed by the model and accepted, changed, or rejected
  by the author.
- **Stage 0:** scaffold, tooling, and documentation skeleton written by the model
  from the approved plan.
- **Stage 1:** engine tests written first, then the engine, in red/green commit
  pairs; the author reviewed each pair. Decisions D22–D25 logged.
- **Stage 2:** agents, runner, and recording format, same red/green pattern.
  Decisions D26–D31 logged.

Later stages append their own entry.

## Layout

```
SPEC.md               the task, verbatim
docs/REQUIREMENTS.md  spec restated with IDs; interpretations and additions
docs/DECISIONS.md     decision log
plans/PLAN.md         stage plan with status lines
examples/             recordings used as fixtures
src/hanoi_crossing/   the package
tests/                pytest suite
```
