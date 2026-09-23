# Hanoi Crossing — plan

The plan as approved before implementation, kept as part of the journey: what was
decided up front, how the work was cut into stages, and which requirement each stage
answers. It is not a description of the code. Flags changed after stage 4 (D38-D44)
and the modules were restructured after review (D45-D57), so `CLAUDE.md` holds the
current blueprint, `docs/USAGE.md` the current flags, `README.md` the design, and
`docs/DECISIONS.md` the reasoning. The architecture and dataflow sections that used
to sit here were superseded by those files and removed.

## 1. Decisions

### 1.1 Rules as read

- Players A and B; private poles 1 and 3 each; pole 2 shared. A has odd disks, B
  even, N each, on pole 1.
- One action per turn: lift, place, skip. One disk in hand. Size rule on every pole.
  Illegal action: nothing changes, turn lost.
- Turn order is an input; the engine takes the acting player on every call.
- Win: hand empty, own pole 1 empty, pole 2 empty, own pole 3 non-empty. Both
  players checked after every action; first win ends the game; no ties possible.
- Ownership never matters after setup; disks may end up on the other side.

### 1.2 Interpretations (go into `docs/DECISIONS.md` and docstrings)

1. All visible poles empty is not a win; pole 3 must hold a disk.
2. Actions name poles 1–3 from the actor's side; the opponent's poles are inexpressible.
3. Malformed input raises; well-formed but illegal wastes the turn with a reason.
4. A finished game rejects every further action, including skip.
5. Game ends won, stalemate (same position and player to move K times), or
   unfinished (schedule exhausted); later schedule entries count as unplayed.

### 1.3 Tooling and process

- uv; dev deps pytest, ruff, pre-commit (ruff hooks only, so failing-test commits
  pass). `.python-version` 3.12. No Poetry, Docker, or CI.
- TDD visible in git: per unit `test:` (red) then `feat:` (green), optional `refactor:`.
- One stage = one session; it reads its section of `plans/PLAN.md`, implements only
  that, ends with commits, green tests, status line updated, `docs/DECISIONS.md` and
  the README AI-usage log appended. Every decision is logged when made.
- All docs are Markdown: `README.md`, `SPEC.md`, `docs/REQUIREMENTS.md`,
  `docs/DECISIONS.md`, `plans/PLAN.md`.

## 2. Requirements traceability

| ID | Requirement | Stage | Done |
|---|---|---|---|
| R1 | Two players, 3 poles each, N disks on pole 1, largest at bottom | 1 | ✓ engine tests: initial layouts |
| R2 | Pole 2 shared, both can interact | 1 | ✓ engine test: lift opponent's disk from pole 2 |
| R3 | Opponent's poles 1, 3 and hand are hidden | 1 `observe`; 2 agents see only `Observation` | ✓ engine test: observe hides opponent; agents tests |
| R4 | A odd sizes, B even sizes | 1 | ✓ engine tests: initial layouts |
| R5 | Place only on empty pole or strictly larger disk | 1 | ✓ engine tests: size-rule reasons |
| R6 | Exactly one action per turn: lift, place, skip | 1, 2 | ✓ engine legal_actions; runner one action per entry |
| R7 | At most one disk in hand | 1 | ✓ engine test: hand is not empty |
| R8 | Either player may lift any top disk from pole 2 | 1 | ✓ engine test: either player lifts from pole 2 |
| R9 | Illegal action changes nothing, turn wasted | 1 `step`; 2 runner records it | ✓ engine test: identical object on illegal; runner records wasted turns |
| R10 | Turn order external, no pattern assumed | 1; 2 schedules | ✓ engine solo-solve test; runner schedules |
| R11 | Win condition | 1 `winner` | ✓ engine winner tests |
| R12 | Pole naming 1a, 2, 3a, 1b, 3b | 1; 3 render | ✓ engine pole keys; render board tests |
| R13 | N=1 example plays as written | 1, 2, 3 | ✓ spec_n1.json in engine, runner, recording, CLI tests |
| T1 | Engine in Python | 1 | ✓ engine.py |
| T2 | Replay CLI: moves + turn order in, final state out | 2, 3 | ✓ hanoi replay; recording.replay |
| T3 | Random-play mode | 2, 3 | ✓ hanoi random; RandomAgent |
| T4 | Tests exercise the engine directly | 1 | ✓ tests/test_engine.py |
| T5 | Reusable as RL environment core, unchanged | 1; 4 README | ✓ README Reuse; observe / ALL_ACTIONS / no clock |
| T6 | Reusable as concurrent-service core, unchanged | 1; 4 README | ✓ README Reuse; immutable hashable State |
| T7 | Do not build RL or service | all; §4 | ✓ nothing built; README Future work |
| T8 | Random player consumes engine as an external agent would | 2 | ✓ agents receive only an Observation and the legal list |
| T9 | Design input, output, internal model | 1, 2, 3 | ✓ engine model, recording format, render output |
| T10 | Decide and document open rules | 1; 4 | ✓ docs/REQUIREMENTS.md I1–I7; engine docstring |
| T11 | README with design decisions | 0; 4 | ✓ README |
| C1 | Engine under 500 lines | 1 | ✓ test guards < 500 |
| C2 | Standard layout, uv | 0 | ✓ uv, src layout |
| S1 | Git repo, journey visible | 0; all | ✓ red/green commit pairs per unit |
| S2 | Disclose AI usage | 0; all; 4 | ✓ README AI usage; docs/DECISIONS.md |
| S3 | ~2 h, WIP OK | stages 0–3 are a complete submission | ✓ stages 0–3 complete; stage 4 docs |

## 3. Stages

One stage per session: read this section, implement only its scope, TDD with a
failing `test:` commit then a passing `feat:`, log every decision in
`docs/DECISIONS.md` as it is made. All four are done.

### Stage 0 — Scaffold
Runnable empty project, no game logic: uv package, pytest/ruff/pre-commit, ruff
line-length 100, `.gitignore` for `recordings/`, `SPEC.md` verbatim, the spec's N=1
example as `examples/spec_n1.json`, and the docs skeleton. Done when a smoke test
passes and ruff is clean.

### Stage 1 — Engine
`engine.py`: the whole rules as pure functions over an immutable state, under the
spec's 500-line cap (C1), with frozen `Action`, `State`, `Observation`, `Outcome`
and the functions `initial_state`, `observe`, `legal_actions`, `step`, `winner`.
Tests cover the layouts, hidden information, every illegal-move reason, the win
condition including an opponent-assisted win, and invariants under random play. Done
when the suite is green and the file is under 500 lines.

### Stage 2 — Agents, runner, recording
Play a whole game from Python: `RandomAgent` and `ScriptedAgent`, one `run` loop over
an external schedule with a turn log and the non-winning exits, and the JSON
recording format with its round trip. Done when a random N=3 game can be saved and
replayed to the same final state.

### Stage 3 — CLI
The spec's two frontends, `replay` and `random`, plus the additions: human play with
a move timeout, autosave, `hanoi recordings`, continuing an unfinished replay, and
the text output (towers, list layout, trace, JSON). Everything reachable through
`main(argv, stdin, stdout, ...)` so tests never spawn a process. Done when the spec
example and a random game run from the command line.

### Stage 4 — Write-up
The README the spec asks for, assembled from `docs/DECISIONS.md` and
`docs/REQUIREMENTS.md`: the game, how to use it, the design, the reuse story for RL
and a service, the additions marked as such, and the AI-usage log. Done when the
traceability table above is checked off.

### After stage 4
Fixes from playing the game (D38-D44), then the restructure this repository now
carries (D45-D57): same features, four rings, with the reasoning in the decision log.

## 4. Future work

Described in the README, not implemented: web UI and HTTP API, an RL wrapper, an LLM
agent. Nothing in the engine changes for any of them.
