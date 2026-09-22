# CLAUDE.md

## Project Overview
Hanoi Crossing: a two-player Tower of Hanoi engine with partial visibility and a
shared pole, built as a take-home (see `SPEC.md`). The engine must later serve, unchanged,
an RL loop or a multi-game service; the CLI replays recordings and plays random games.

## Features
Spec (required):
- Rules engine: step, legal actions, observation, winner, state to/from dict
- `replay`: re-play a recording file, print the final state
- `random`: two random players, seeded, any turn-order pattern

Additions (beyond the spec; each can be removed without touching the core):
- Human play: any mix of human and random players (`play`)
- Move timeout: random fallback, quit, Ctrl-C, max unanswered prompts
- Continue an unfinished replay with random players
- Autosave and the `recordings` listing
- Stalemate after repeated positions
- Output options: tower/list, `--trace`, `--json`

Ideas only (not built): web UI, HTTP API, RL wrapper, LLM agent.

## Architectural Blueprint
Four rings; a module imports only from rings further in.
1. core      — `engine`: the rules. Pure: no I/O, clock, randomness.
2. play      — `agents`, `runner`: who moves, and the one game loop.
3. frontends — `recording` (files), `render` (text), `human` (terminal play).
4. entry     — `cli`: parses arguments and wires rings 1–3. No game logic.

Where a new feature goes: find the innermost ring that can own it.
An addition must live in ring 3 or 4; it may not change ring 1.
Facts are carried forward (e.g. `Outcome.disk`), never recomputed by re-stepping.
Enforced by: `tests/test_architecture.py` (fails on an outward import).

## Tech Stack
Python 3.12, uv, no runtime dependencies. Dev: pytest, ruff, pre-commit.

## Coding Conventions
- Engine stays under 500 lines (spec constraint, guarded by a test).
- Every design decision is logged in `docs/DECISIONS.md` in the same commit.
- Ruff, line length 100.

## Common Commands
- Install: `uv sync`
- Test: `uv run pytest`
- Lint / format: `uv run ruff check --fix . && uv run ruff format .`
- Run: `uv run hanoi random --n 2`, `uv run hanoi replay examples/spec_n1.json`
