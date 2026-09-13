# Hanoi Crossing

A two-player Tower of Hanoi variant with a shared middle pole: a pure Python game
engine, a replay frontend, and a random-play frontend. **Status: work in progress**
(stage 0 of 4 done; see `plans/PLAN.md`).

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

_Stage 1._

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
