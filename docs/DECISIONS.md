# Decision log

Every design decision, recorded when it was made. Numbers are chronological and
stable (the README, `docs/USAGE.md`, `plans/PLAN.md` and commit messages cite them);
entries are grouped by topic. Each gives the choice and why, and names the rejected
alternative when the call was close. Reversed decisions are kept and marked, because
the reversal is part of the journey.

**Origin** in the index says where the decision came from:

| Origin | Meaning |
|---|---|
| 🟦 spec (ID) | the spec requires it; the entry decides *how* (IDs from `docs/REQUIREMENTS.md`) |
| 🟨 interpretation (I#) | the spec is silent on a rule; we decided |
| 🟪 engineering | an engineering choice within the required scope |
| 🟩 addition (A#) | a feature beyond the spec, listed in `docs/REQUIREMENTS.md` |

## Index

| # | Decision | Topic | Origin | Status |
|---|---|---|---|---|
| D1 | Rule interpretations I1–I7 | Rules | 🟨 interpretation (I1–I7) | active |
| D8 | Three end states | Rules | 🟨 interpretation (I5) | active |
| D43 | Random players never make illegal moves | Rules | 🟦 spec (T3) | active |
| D2 | Pure functions over an immutable state | Engine | 🟦 spec (T5, T6) | active |
| D3 | Disks are plain integers; no ownership after setup | Engine | 🟨 interpretation (I7) | active |
| D4 | Fixed action space of seven, player-relative | Engine | 🟦 spec (R3, T5) | active |
| D22 | `State` hashes by content despite mapping fields | Engine | 🟪 engineering | amended by D57 |
| D23 | Malformed input raises, illegal moves explain | Engine | 🟨 interpretation (I3) | amended by D51 |
| D24 | `bool` is not an int | Engine | 🟪 engineering | active |
| D25 | Engine size | Engine | 🟦 spec (C1) | active |
| D5 | Agent contract | Agents and runner | 🟦 spec (T8) | active |
| D6 | One runner | Agents and runner | 🟪 engineering | active |
| D9 | External agent with timeout, fallback, move source | Agents and runner | 🟩 addition (A1, A2) | superseded by D48 |
| D26 | Agents carry `kind` and `last_fell_back` | Agents and runner | 🟩 addition (A2) | superseded by D47 |
| D27 | The injected `ask` owns the waiting | Agents and runner | 🟩 addition (A1) | superseded by D48 |
| D28 | Stalemate counts (state, player) pairs | Agents and runner | 🟨 interpretation (I5) | active |
| D29 | Status checked before each entry and after the loop | Agents and runner | 🟪 engineering | active |
| D32 | `run` gains `on_turn` | Agents and runner | 🟩 addition (A1) | active |
| D44 | Ending a game early (`StopGame`) | Agents and runner | 🟩 addition (A1) | active |
| D7 | Recording format | Recording | 🟦 spec (T2, T9) | active |
| D30 | Validation in `Recording.__post_init__` | Recording | 🟪 engineering | active |
| D31 | `replay` is `run` with scripted agents | Recording | 🟦 spec (T2) | active |
| D18 | Autosave | Recording | 🟩 addition (A3) | active |
| D35 | Continuation recordings are the whole game | Recording | 🟩 addition (A3, A4) | active |
| D36 | `hanoi recordings` replays each file | Recording | 🟩 addition (A3) | active |
| D12 | CLI shape | CLI | 🟦 spec (T2, T3) | active |
| D13 | Schedule flags | CLI | 🟦 spec (R10) | active |
| D14 | Seed default 0 | CLI | 🟪 engineering | active |
| D15 | Repetition limit default 10 | CLI | 🟨 interpretation (I5) | superseded by D42 |
| D16 | Move timeout default 30 s | CLI | 🟩 addition (A1) | active |
| D33 | Stdin timeout via reader thread | CLI | 🟩 addition (A1) | active |
| D34 | End of input counts as no answer | CLI | 🟩 addition (A1) | active |
| D41 | `--max-turns` defaults to 200 · 3ⁿ | CLI | 🟪 engineering | active |
| D42 | Repetition limit off by default | CLI | 🟨 interpretation (I5) | active |
| D17 | Drawn towers by default | Output | 🟦 spec (T9) | active |
| D38 | Full game trace by default | Output | 🟪 engineering | superseded by D40 |
| D39 | Bot turns spell out their effect | Output | 🟩 addition (A5) | extended by D49 |
| D40 | Default output is the final state only | Output | 🟪 engineering | active |
| D10 | Tooling | Process | 🟦 spec (C2) | active |
| D11 | TDD visible in git | Process | 🟦 spec (S1) | active |
| D21 | Where the documents live | Documentation | 🟦 spec (T11) | active |
| D37 | README structure | Documentation | 🟦 spec (T11) | active |
| D19 | Interfaces and their purposes | Scope | 🟦 spec (T5, T6) | active |
| D20 | Scope beyond the spec | Scope | 🟦 spec (S3) | active |
| D45 | Four rings; restructure, keep every feature | Structure | 🟪 engineering | active |
| D46 | `Outcome` carries the moved disk; `Action` owns its text | Structure | 🟪 engineering | active |
| D47 | One `source` label per agent | Structure | 🟩 addition (A2) | active |
| D48 | Human play is its own frontend module | Structure | 🟩 addition (A1) | active |
| D49 | One wording for what a turn did | Structure | 🟩 addition (A5) | active |
| D50 | Recording owns its files; CLI only wires | Structure | 🟪 engineering | active |
| D51 | An `Action` is checked when it is built | Structure | 🟪 engineering | active |
| D52 | `--no-skip` and the `Agent` protocol removed | Structure | 🟪 engineering | active |
| D53 | Plain tuples instead of `Literal` aliases | Structure | 🟪 engineering | active |
| D54 | `Outcome` keeps only what it cannot derive | Structure | 🟪 engineering | active |
| D55 | Nothing is kept for a caller that does not exist | Structure | 🟪 engineering | active |
| D56 | The board style is a boolean, not a string | Structure | 🟪 engineering | active |
| D57 | Review pass: bad input fails as an error, not a traceback | Structure | 🟪 engineering | active |

## Rules

### D1. Rule interpretations
- I1-I7 in `docs/REQUIREMENTS.md`: pole 3 must hold a disk to win; pole numbers are
  player-relative; malformed input raises while an illegal move wastes the turn; a
  finished game is frozen; three end states; both players checked after every step;
  no ownership after setup. Each keeps the engine simple and the rules text literal.
- **Rejected:** requiring a player's own disks on pole 3, and treating an empty board
  as a win — the spec says neither.

### D8. Three end states
- *won* (engine), *unfinished* (schedule exhausted) and *stalemate* (same position
  and player to move seen K times), the last two owned by the runner. Skip is always
  legal, so "no legal moves" can never end a game; the runner must supply the exits.
- **Rejected:** the schedule as the only bound — a deliberate stall would run it all.

### D43. Random players never make illegal moves
- `RandomAgent` picks only from `legal_actions`, so the spec's "random valid moves"
  (T3) holds by construction. Illegal moves enter a game only from a human or a
  recording, and are wasted turns as the rules say.
- **Rejected:** sampling all seven actions and letting the engine refuse some.

## Engine

### D2. Pure functions over an immutable state
- Frozen dataclasses; `step(state, player, action)` returns a new state and an
  outcome; no I/O, randomness or counters; `winner(state)` is recomputed from the
  board. A service can hold thousands of games as plain values, and an observation
  can never disagree with the board (T5, T6).
- **Rejected:** a mutable `Game` object with internal counters — needs locks and
  copying in a service, and is harder to snapshot and replay.

### D3. Disks are plain integers; no ownership after setup
- A disk is its size; nothing records whose it was, because after setup ownership
  affects no rule (R2, R8, I7).
- **Rejected:** a `(size, owner)` pair: unused data that invites wrong rules.

### D4. Fixed action space of seven, player-relative
- `lift 1|2|3`, `place 1|2|3`, `skip` in a fixed order (`ALL_ACTIONS`), numbered from
  the acting player's side, with `legal_actions` as the mask. A policy can output an
  index, and the opponent's poles cannot be named at all (R3, T5).
- **Rejected:** absolute pole names in actions, which would need a visibility check
  on every call.

### D22. `State` hashes by content despite mapping fields (amended by D57)
- `poles` and `hands` stay mappings for readable key access, and `__hash__` runs over
  their values in fixed key order, which is what makes stalemate detection a
  `Counter` lookup. D57 made both read-only so a state cannot change its own hash.
- **Rejected:** tuple-of-tuples storage with positional access: unreadable.

### D23. Malformed input raises, illegal moves explain (amended by D51)
- I3 separates the two: a malformed action raises `ValueError`, a well-formed one
  gets a reason string or `None`, and `legal_actions` is defined as "the actions
  whose reason is `None`", so the two can never disagree. D51 moved the malformed
  check into `Action` itself.
- **Rejected:** a separate legality table consulted by both `step` and `legal_actions`.

### D24. `bool` is not an int
- `bool` subclasses `int` in Python, so JSON `true` could arrive as disk size 1.
  `is_positive_int` rejects it wherever a number is read.

### D25. Engine size
- Under the spec's 500 lines (C1) on the strictest reading, `wc -l` including blanks
  and docstrings, with a test that enforces it forever.
- **Rejected:** counting only code lines — weaker than what a reviewer will apply.

## Agents and runner

### D5. Agent contract
- `choose(observation, legal_actions) -> Action`; an agent never sees the full
  `State`, and the random agent takes an injected seeded RNG. This is what an RL
  policy or a network client would receive (T8).
- **Rejected:** passing the `State` and trusting agents to look only at their side.

### D6. One runner
- One loop in `runner.py` (`play_turn`, `run`); replay, random play, human play and
  continuation differ only in agents and start state. One place owns the status
  checks and the turn log.
- **Rejected:** a "game type" concept — it loses mixed agents, which RL needs.

### D9. External agent with timeout, fallback, move source (superseded by D48)
- **At the time:** `ExternalAgent(ask, timeout, fallback)` served a keyboard, a UI or
  a model alike; on timeout the fallback played and the turn was marked `timeout`.
- **Why superseded:** only human play ever used it, so D48 moved it to the frontend.

### D26. Agents carry `kind` and `last_fell_back` (superseded by D47)
- **At the time:** two attributes the runner combined into `Turn.source`, to keep
  `choose` a plain action-returning call.
- **Why superseded:** one `source` label says it without the runner deciding (D47).

### D27. The injected `ask` owns the waiting (superseded by D48)
- **At the time:** the agent passed its timeout to an injected `ask` and reacted to a
  `Timeout` or a `None`, so no clock or thread lived in `agents.py`.
- **Why superseded:** D48 gave the waiting to `human.py`, where the terminal is.

### D28. Stalemate counts (state, player) pairs
- `run` keeps a `Counter` keyed on the frozen state plus the player about to move;
  reaching the limit ends the game before that turn. Mutual skipping and longer
  cycles both repeat that pair, and content hashing (D22) makes it a lookup.
- **Rejected:** counting consecutive no-change turns, which misses longer cycles.

### D29. Status checked before each entry and after the loop
- A win found at the top of an entry counts every remaining entry as unplayed; a win
  on the last entry is still reported by the post-loop check.
- **Rejected:** checking only after each turn, which misses a schedule that starts on
  an already-finished position.

### D32. `run` gains `on_turn`
- `run(..., on_turn=None)` calls back after every played turn, so a frontend can
  print live without owning a second loop. (D57 reduced it to the turn alone.)
- **Rejected:** driving `play_turn` from the CLI, which duplicates the status logic;
  printing inside agents, which must stay free of I/O.

### D44. Ending a game early (`StopGame`)
- An agent may raise `StopGame` and `run` returns the game so far as `unfinished`
  with the rest unplayed. The frontend raises it on `quit`, on Ctrl-C at a prompt,
  and on the `--max-timeouts`-th unanswered prompt, so at most K-1 moves are played
  for an absent human. The result is rendered and autosaved, so it can be continued.
  Ctrl-C outside a prompt exits 130 with nothing saved.
- **Rejected:** a fourth status `abandoned` — the recording is simply unfinished.

## Recording

### D7. Recording format
- JSON `{n, turn_order, moves, sources?}`: the turn order is a separate string
  because the spec calls it external, and moves are player-relative. Readable in a
  diff.
- **Rejected:** one list of player-tagged steps, which makes turn order implicit.

### D30. Validation in `Recording.__post_init__`
- Every recording, loaded or built from a run, is validated on construction, so a
  bad one can never be written; `loads` checks the JSON shape and key names first.
- **Rejected:** validating only on load.

### D31. `replay` is `run` with scripted agents
- The moves are split per player in turn order and played from `initial_state(n)`
  through the one runner, so recorded illegal moves are wasted again (R9).
- **Rejected:** a dedicated replay loop, a second path to keep in step with the rules.

### D18. Autosave
- Every finished game, whatever its status, is written once at the end to
  `recordings/<date>-<time>-<mode>-n<N>-seed<S>.json`; `--save` renames and
  `--no-save` disables. Recordings are the only way to review or continue a game.
- **Rejected:** writing after every turn; saving only on request.

### D35. Continuation recordings are the whole game
- Continuing an unfinished replay saves the original moves followed by the
  continuation, so replaying the file reproduces the whole game from the start.
- **Rejected:** saving only the continuation.

### D36. `hanoi recordings` replays each file
- The listing shows n, seed, turns, status, winner and modification time, with the
  status from a real replay: files are small, replay is instant, and a stored status
  could lie.

## CLI

### D12. CLI shape
- One `hanoi` entry point with `replay`, `random`, `play` and `recordings`. `random`
  is `play --a random --b random`, kept so the spec's mode is visible by name.

### D13. Schedule flags
- `--schedule PATTERN` (default `AB`) repeated to fill `--max-turns`, and `--first`
  rotating the pattern to that player's first occurrence. Any turn order the spec
  allows can be expressed.
- **Rejected:** a seed-chosen starter (surprising); alternating only (cannot express
  A moving twice).

### D14. Seed default 0
- `--seed` defaults to 0 and is always printed: reproducible by default, another
  number for a different game.

### D15. Repetition limit default 10 (superseded by D42)
- **At the time:** 10 by default, since 3 as in chess would end most random games as
  stalemates. **Why superseded:** any positive default fires on large random games.

### D16. Move timeout default 30 s
- `--move-timeout` defaults to 30 and `0` disables it; the random fallback plays and
  the turn is marked `timeout`. Long enough to think, short enough not to stall.

### D33. Stdin timeout via reader thread
- One daemon thread pumps stdin into a queue for the whole session; a prompt waits
  with `queue.get(timeout)` and end of input is a sentinel put back for later
  prompts. One deadline covers a whole turn, re-prompts included.
- **Rejected:** `select` on stdin (not portable); `signal.alarm` (Unix, main thread).

### D34. End of input counts as no answer
- At EOF the prompt returns nothing, the fallback plays and the turn is `timeout`, so
  a closed stdin can never hang or crash a game.

### D41. `--max-turns` defaults to 200 · 3ⁿ
- Measured random play needs roughly three times more turns per extra disk (medians
  10, 44, 136, 474, 1434 for n = 1..5; worst cases about three times the median), so
  the default is 200 · 3ⁿ: about three times the observed worst case.
- **Rejected:** a flat number, wrong for every n but one.

### D42. Repetition limit off by default (reverses D15)
- With D41's larger caps every ten-disk random game ended `stalemate`: random walkers
  revisit positions by chance. A repeated position is a stalemate only when players
  *choose* to repeat, and a stalling human is covered by the timeout.

## Output

### D17. Drawn towers by default
- Towers for the per-turn view and the final board, `--list` for the spec's cross
  layout, `--json` for machines, `--trace` for every turn with its source.

### D38. Full game trace by default (superseded by D40)
- **At the time:** the trace printed before the final board, with `--no-trace`.
  **Why superseded:** a 44-turn replay showed it was too much by default.

### D39. Bot turns spell out their effect (extended by D49)
- A human placed a disk on the shared pole and "did not see it" next turn: the random
  opponent had lifted it and the line `lift 2` hid that. Bot lines now describe the
  effect and name the shared pole.
- **Rejected:** redrawing the human's view after every bot turn, which is noisy.

### D40. Default output is the final state only (reverses D38)
- Every command prints the final board and summary; `--trace` adds the whole game.
  Human play still shows every turn live.

## Process

### D10. Tooling
- uv; pytest, ruff and pre-commit with ruff hooks only; Python 3.12; Markdown docs.
  The spec's own example is uv, and there are no runtime dependencies.
- **Rejected:** Poetry; Docker (`uv sync` is the whole setup); a pytest pre-commit
  hook, which would block red TDD commits; HTML docs.

### D11. TDD visible in git
- Per unit: a `test:` commit that fails, a `feat:` commit that passes, an optional
  `refactor:`, and a `docs:` commit to close a stage. The spec asks for the journey
  (S1).
- **Rejected:** squashing.

## Documentation

### D21. Where the documents live
- `SPEC.md` is the task verbatim, `docs/REQUIREMENTS.md` restates it with IDs, this
  log holds the decisions, `docs/USAGE.md` is the flag reference, `plans/PLAN.md` the
  plan as approved, `CLAUDE.md` the module blueprint. A reviewer can see what was
  given versus what we chose.

### D37. README structure
- The README summarizes this log and the requirements rather than repeating them, in
  reviewer order: quick start, the game, using it, design, reuse, beyond the spec,
  project notes.
- **Rejected:** copying the decision log into the README; a separate ARCHITECTURE.md.

## Scope

### D19. Interfaces and their purposes
- The CLI serves the spec, the developer and the reviewer; the Python API is the RL
  path. Not built: a web UI for people, an HTTP API for remote programs.
- **Rejected:** the CLI as an RL interface — one process per command cannot hold
  state across thousands of steps.

### D20. Scope beyond the spec
- Built: human play, move sources, autosave, continuation, early ending. Described
  only: web UI and HTTP API, RL wrapper, LLM agent. Stages 0-3 are a complete
  submission on their own.
- **Rejected:** building the web UI first.

## Structure

Reworked after review feedback that the code was not cleanly abstracted. Every
feature was kept; what changed is where each one lives.

### D45. Four rings
- Additions had been attached to the nearest module: five of ten features had logic
  in `cli.py` (498 lines, bigger than the engine), `recording` imported the runner,
  `render` re-stepped whole games to describe them.
- **Choice:** core (`engine`) <- play (`agents`, `runner`) <- frontends (`recording`,
  `render`, `human`) <- entry (`cli`). Imports point inward only and an addition may
  not change the core; `CLAUDE.md` holds the table and
  `tests/test_architecture.py` enforces it.
- **Rejected:** cutting back to the spec's two modes, which hides the problem.

### D46. Facts are carried, not recomputed
- `Outcome.disk` reports the disk lifted or placed; `str(action)` and `Action.parse`
  live on `Action`; `SIDES` is the one pole table and `is_positive_int` the one
  integer check. Three places used to work out which disk moved, one by replaying the
  whole game, and action text was formatted in two modules and parsed in a third.
- **Rejected:** a text-format module — a move's text belongs to the action space.

### D47. One `source` label per agent (supersedes D26)
- An agent carries `source`, the label of the move it just chose, and the runner
  copies it onto the turn. The agent knows who chose; the runner was combining two
  flags to guess.
- **Rejected:** `choose` returning `(action, source)`, which leaks display into the
  contract an RL policy implements.

### D48. Human play is its own frontend (supersedes D9, D27)
- `human.py` holds `LineReader`, `Console` and `HumanAgent`; `agents.py` keeps only
  `RandomAgent` and `ScriptedAgent`. The prompt, reader thread and timeout counting
  had been in `cli.py`, and `ExternalAgent` sat in the core although only human play
  used it. One class now replaces `ExternalAgent`, its `ask` callback and the prompt
  object.
- **Rejected:** a generic injected-`ask` agent for a future UI or LLM, not built.

### D49. One wording for what a turn did (extends D39)
- `render.describe_turn` (`took disk 1 from pole 1`, `put disk 3 on the shared pole`,
  `illegal: ... Turn wasted.`) serves the trace, the bot lines and human feedback
  alike, replacing three phrasings of the same fact, each derived differently.

### D50. Recording owns its files; the CLI only wires
- `recording.py` gained `autosave_path`, `seed_in_name` and `append_run`;
  `Recording.moves` are `Action`s, text only in `loads`/`dumps`; validation lives in
  `Recording` alone. File naming and continuation glue had been in `cli.py`, which
  went from 498 to 262 lines.
- **Rejected:** a separate `files.py` for three small functions.

### D51. An `Action` is checked when it is built
- `Action.__post_init__` rejects a malformed move, so `engine._validate` is gone and
  nothing downstream asks again; `check(ok, message, error)` replaces the repeated
  `if ...: raise ...` pairs.
- **Rejected:** a table-driven `add_argument` loop, tried and reverted: longer once
  formatted, and harder to read.

### D52. `--no-skip` and the `Agent` protocol removed
- Neither had a requirement behind it, no type checker ran the protocol, and
  `allow_skip` made a game-wide preference a per-agent one. The agent contract is now
  two sentences in the `agents` docstring.
- **Rejected:** keeping `--no-skip` for shorter games; `--max-turns` already bounds one.

### D53. Plain tuples instead of `Literal` aliases
- `PLAYERS`, `VERBS`, `POLES`, `POLE_KEYS`, with `str` / `int` hints. Each value had
  been written twice, as a type and as data, with nothing verifying the narrower
  version; six `# type: ignore` comments went with them.
- **Rejected:** `get_args(Literal[...])`, which keeps the hints but adds a layer.

### D54. `Outcome` keeps only what it cannot derive
- `Outcome` stores `reason`, `winner` and `disk`, with `legal` as a property. Five
  fields had held three facts and could contradict each other. `pole_key` went too:
  the public functions check the player once and the internals index `SIDES`, instead
  of re-checking up to seven times a turn.

### D55. Nothing is kept for a caller that does not exist
- Audited every class and function for a real user. `Outcome.done` and
  `engine.from_dict` had none outside the tests and are gone; `to_dict` stays because
  `--json` prints it; `play_turn` stays because `run` calls it. `from_dict` had been
  kept for a service that might load a board, but this project's persistence is
  moves, never board states (D7).
- **Rejected:** keeping the round trip symmetric for its own sake.

### D56. The board style is a boolean, not a string
- `render_view`, `render_board` and `Console` take `as_list: bool`, straight from the
  `--list` flag, instead of a two-value string compared against literals in four
  places. One `_agents` helper builds the players for both commands.

### D57. Review pass: bad input fails as an error, not a traceback
- Three reviewers went file by file over the restructured code; every finding below
  was reproduced before it was fixed.
- **Rules and loop:** a repetition limit below 2 is rejected instead of declaring an
  instant stalemate; `State` and `Observation` hold read-only mappings, so a frozen
  board can no longer change its hash or let an agent edit its own view; `Action`
  rejects `True` as a pole.
- **Files and text:** a recording whose sources are not strings, whose bytes are not
  UTF-8, or whose path is a directory is reported as invalid (exit 1) instead of a
  traceback; the list board no longer mistakes disk 2 on pole 1b for the shared-pole
  label; tower columns stay aligned once disks reach two digits.
- **CLI:** `--max-turns` below 1 is an argument error, and every error message
  follows the console, so `--json` keeps stdout to one object.
- **Rejected:** a cap on `n` in a recording — a huge `n` makes replay slow, but the
  file is the user's own and a cap would be an arbitrary game limit.
