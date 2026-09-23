# Decision log

Every design decision, recorded when it was made. Numbers are chronological and
stable (the README, `docs/USAGE.md`, `plans/PLAN.md`, and commit messages cite
them); entries are grouped by topic. Two decisions were later reversed and are
kept, marked **superseded**, because the reversal is part of the journey.

Each entry has the same four parts: **Context** (what raised the question),
**Choice**, **Reason**, **Rejected** (alternatives and why not).

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
| D22 | `State` hashes by content despite dict fields | Engine | 🟪 engineering | active |
| D23 | `_validate` raises, `_illegal_reason` explains | Engine | 🟨 interpretation (I3) | active |
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

## Rules

### D1. Rule interpretations
- **Context:** the spec leaves several situations open.
- **Choice:** I1–I7 in `docs/REQUIREMENTS.md`: pole 3 must be non-empty to win;
  player-relative pole numbers; malformed input raises, illegal moves waste the
  turn; a finished game is frozen; three end states; both players checked after
  every step; no ownership after setup.
- **Reason:** each keeps the engine simple and the rules text literal.
- **Rejected:** requiring all of a player's own disks on pole 3 (the spec never
  says so); treating all-empty as a win (reads against "only pole 3 has disks").

### D8. Three end states
- **Context:** the spec names only winning; two players skipping forever, or
  cycling, must still terminate.
- **Choice:** *won* (engine), *unfinished* (schedule exhausted, runner),
  *stalemate* (same position with the same player to move seen K times, runner,
  optional).
- **Reason:** skip is always legal, so a "no legal moves" exit can never exist; the
  runner must supply the other exits.
- **Rejected:** letting the schedule be the only bound (a deliberate stall would
  run the whole schedule).

### D43. Random players never make illegal moves
- **Context:** asked while reviewing the CLI: "can the random make an illegal move?"
- **Choice:** `RandomAgent` chooses only from `legal_actions`, so every random move
  is legal by construction; the invariants test asserts it over thousands of turns.
  Illegal moves enter a game only from a human or from a recording, and are wasted
  turns as the rules say.
- **Reason:** the spec's random mode is "random *valid* moves" (T3).
- **Rejected:** sampling all seven actions and letting the engine reject some
  (legal, but inflates wasted turns for no benefit).

## Engine

### D2. Pure functions over an immutable state
- **Context:** the engine must be reusable unchanged by an RL loop and by a
  service holding many games (T5, T6).
- **Choice:** frozen dataclasses; `step(state, player, action)` returns a new state
  and an outcome; no I/O, randomness, counters, or stored "finished" flag;
  `winner(state)` is recomputed from the board; `to_dict` / `from_dict`.
- **Reason:** thousands of games can be held as plain values; serialization is
  trivial; a state loaded from JSON needs no bookkeeping; an observation can never
  disagree with the board.
- **Rejected:** a mutable `Game` object with internal counters (needs locks and
  copying in a service; harder to snapshot and replay).

### D3. Disks are plain integers; no ownership after setup
- **Context:** disks can cross sides (R2, R8) and the win condition never mentions
  ownership.
- **Choice:** a disk is its size; nothing records whose it was.
- **Reason:** after setup ownership affects no rule.
- **Rejected:** a `(size, owner)` pair (unused data that invites wrong rules).

### D4. Fixed action space of seven, player-relative
- **Context:** an RL policy needs an indexable action space; R3 forbids naming the
  opponent's poles.
- **Choice:** `lift 1|2|3`, `place 1|2|3`, `skip`, in a fixed order (`ALL_ACTIONS`),
  numbered from the acting player's side. `legal_actions` is the mask.
- **Reason:** a policy outputs an index; the opponent's poles are inexpressible.
- **Rejected:** absolute pole names (`1a`, `3b`) in actions (would need a
  visibility check on every call).

### D22. `State` hashes by content despite dict fields
- **Context:** frozen dataclasses with dict fields are not hashable by default;
  states must work as set members and dict keys (stalemate detection, caching).
- **Choice:** keep `poles` / `hands` as plain dicts for readable key access; define
  `__hash__` over the values in fixed key order; `__post_init__` copies the
  mappings and converts pole sequences to tuples.
- **Reason:** readability and hashability at once.
- **Rejected:** tuple-of-tuples storage with positional access (unreadable);
  `MappingProxyType` (still unhashable).

### D23. `_validate` raises, `_illegal_reason` explains
- **Context:** I3 separates malformed input from illegal moves.
- **Choice:** malformed player/verb/pole raises `ValueError` before anything else;
  a well-formed action gets a reason string or `None`. `legal_actions` is defined
  as "the actions whose reason is None", so the two can never disagree.
- **Reason:** one source of truth for legality.
- **Rejected:** a separate legality table consulted by both `step` and
  `legal_actions`.

### D24. `bool` is not an int
- **Context:** `bool` subclasses `int` in Python; JSON `true` could arrive as disk
  size 1.
- **Choice:** `initial_state` and `from_dict` reject `True` / `False` for `n`,
  disks, and hands.
- **Reason:** a silent type confusion would corrupt a game.
- **Rejected:** trusting the caller.

### D25. Engine size
- **Context:** C1, under 500 lines.
- **Choice:** 267 lines including the module docstring; a test enforces the strict
  `wc -l` reading and stays forever.
- **Reason:** the strictest reading is the one a reviewer will apply.
- **Rejected:** counting only code lines (weaker than what will be checked).

## Agents and runner

### D5. Agent contract
- **Context:** T8, the random player must consume the engine exactly as an external
  agent would.
- **Choice:** `choose(observation, legal_actions) -> Action`; an agent never sees
  the full `State`. The random agent takes an injected seeded RNG.
- **Reason:** this is what an RL policy or network client would receive.
- **Rejected:** passing the `State` and trusting agents to look only at their side.

### D6. One runner
- **Context:** replay, random play, human play, and continuation all need a loop.
- **Choice:** one loop in `runner.py` (`play_turn`, `run`); the modes differ only in
  agents and start state. `recording.py` is a file format, not a second runner.
- **Reason:** one place for status checks and the turn log.
- **Rejected:** a "game type" concept (loses mixed agents; RL needs a learning agent
  versus a fixed opponent).

### D9. External agent with timeout, fallback, move source (superseded by D48)
- **Context:** a human who walks away must not hang the game; output should show
  who chose each move.
- **Choice:** `ExternalAgent(ask, timeout, fallback)`; the injected `ask` owns the
  waiting; on timeout the random fallback plays and the turn is marked `timeout`.
  Every `Turn` carries `source` (human / random / scripted / timeout).
- **Reason:** the same class serves a keyboard, a UI, or a model.
- **Rejected:** a human-only agent class (the RL or LLM case is the same shape).

### D26. Agents carry `kind` and `last_fell_back` (superseded by D47)
- **Context:** `Turn.source` must be known without changing the `choose` signature
  an RL policy would implement.
- **Choice:** two attributes on the agent; the runner reads them after `choose`
  and writes `source` (`timeout` when `last_fell_back` is set, else `kind`).
- **Reason:** keeps `choose` a plain action-returning call.
- **Rejected:** `choose` returning an `(action, source)` pair (leaks a display
  concern into the agent contract).

### D27. The injected `ask` owns the waiting (superseded by D48)
- **Context:** the CLI waits on stdin, a UI on a request deadline, tests on a fake.
- **Choice:** `ExternalAgent.choose` passes the timeout to `ask` and reacts to a
  `Timeout` exception or a `None` return. No clock, thread, or `input()` in
  `agents.py`.
- **Reason:** the agent should not care how waiting is implemented.
- **Rejected:** a clock inside the agent.

### D28. Stalemate counts (state, player) pairs
- **Context:** D8's stalemate needs a definition of "repeated position".
- **Choice:** `run` keeps a `Counter` keyed on the frozen `State` plus the player
  about to move; reaching the limit ends the game before that turn. Off when the
  limit is `None` or `0`.
- **Reason:** mutual skipping and cycles both repeat this pair; content hashing
  (D22) makes the counter trivial.
- **Rejected:** counting only consecutive no-change turns (misses longer cycles).

### D29. Status checked before each entry and after the loop
- **Choice:** a win found at the top of an entry counts every remaining entry as
  unplayed; a win on the very last entry is still reported as `won` by the
  post-loop check.
- **Reason:** both "already over" and "just ended" must produce the right status.
- **Rejected:** checking only after each turn (misses a schedule that starts on a
  finished position).

### D32. `run` gains `on_turn`
- **Context:** human play needs live output per turn without the CLI owning a
  second loop.
- **Choice:** `run(..., on_turn=None)` calls back after every played turn with the
  turn and the new state.
- **Reason:** the loop stays the only loop.
- **Rejected:** driving `play_turn` from the CLI (duplicates status logic);
  printing inside agents (agents must stay I/O-free).

### D44. Ending a game early (`StopGame`)
- **Context:** an absent human left the game playing itself, one full timeout per
  turn, for up to `--max-turns` turns; Ctrl-C threw the game away.
- **Choice:** `runner.StopGame`: an agent, or the function it asks, may raise it and
  `run` returns the game so far as `unfinished` with the remaining schedule
  unplayed. The CLI raises it on `quit` / `q` / `exit`, on Ctrl-C during a prompt,
  and when the `--max-timeouts`-th (default 3) unanswered prompt in a row arrives,
  so at most K−1 moves are ever played for an absent human. The result is rendered
  and autosaved, so it can be continued with `replay --continue`. Ctrl-C outside a
  prompt exits 130 with nothing saved.
- **Reason:** every way out should leave a continuable recording.
- **Rejected:** a fourth status `abandoned` (the recording is simply unfinished;
  the printed reason says why); switching the absent human to a random player for
  the rest of the game (the game would end without them ever seeing it).

## Recording

### D7. Recording format
- **Context:** the spec calls the turn order external and leaves the format to us.
- **Choice:** JSON `{n, turn_order, moves, sources?}`; turn order is a separate
  string; moves are player-relative strings.
- **Reason:** mirrors the spec's own wording; human-readable in a diff.
- **Rejected:** a single list of player-tagged steps (turn order becomes implicit);
  plain text lines (no room for metadata).

### D30. Validation in `Recording.__post_init__`
- **Choice:** any `Recording`, loaded or built by `from_run`, is validated on
  construction; `loads` checks JSON shape and key names first; unknown top-level
  keys are rejected.
- **Reason:** one place to enforce the format; a bad recording can never be
  written.
- **Rejected:** validating only on load.

### D31. `replay` is `run` with scripted agents
- **Choice:** `to_agents` splits the moves per player in turn order; `replay` calls
  the one runner from `initial_state(n)`. Recorded illegal moves are wasted again,
  as R9 requires.
- **Reason:** no second code path to keep in step with the rules.
- **Rejected:** a dedicated replay loop.

### D18. Autosave
- **Context:** recordings are the only way to review or continue a game, and
  asking for `--save` every time would lose most of them.
- **Choice:** every finished game (any end status) is written once, at the end, to
  `recordings/<date>-<mode>-n<N>-seed<S>.json`; `--save` renames; `--no-save`
  disables. Replay reads only files, never another game's memory.
- **Reason:** free replay fixtures and resumable games.
- **Rejected:** writing after every turn (unnecessary); saving only on request.

### D35. Continuation recordings are the whole game
- **Choice:** when an unfinished replay is continued, the autosaved recording is
  the original moves followed by the continuation moves (sources `scripted` for
  the original part).
- **Reason:** replaying it reproduces the full game from the initial position.
- **Rejected:** saving only the continuation (would not replay from the start).

### D36. `hanoi recordings` replays each file
- **Choice:** the listing shows n, seed (parsed from the file name), turns,
  status, winner, and modification time; status comes from a real replay.
- **Reason:** files are small and replay is instant; a stored status could lie.
- **Rejected:** storing status in the file.

## CLI

### D12. CLI shape
- **Choice:** one `hanoi` entry point with `replay`, `random`, `play`,
  `recordings`. `random` is shorthand for `play --a random --b random`, kept so the
  spec's mode is visible by name.
- **Reason:** the spec names replay and random play as the deliverables.
- **Rejected:** dropping replay (it is required and needs no human).

### D13. Schedule flags
- **Choice:** `--schedule PATTERN` (default `AB`) repeated to fill `--max-turns`;
  `--first A|B` (default A) rotates the pattern to that player's first occurrence.
- **Reason:** any turn order the spec allows can be expressed.
- **Rejected:** starter chosen by the seed (surprising); alternating only (cannot
  express A moving twice).

### D14. Seed default 0
- **Choice:** `--seed` optional, default `0`, always printed.
- **Reason:** reproducible by default; pass another number for a different game.
- **Rejected:** a fresh random seed each run.

### D15. Repetition limit default 10 — superseded by D42
- **Choice at the time:** `--repetition-limit` default 10 in the CLI, `0`
  disables; runner default off.
- **Reason then:** 3 as in chess would end most random games as stalemates.
- **Why superseded:** any positive default fires on large random games; see D42.

### D16. Move timeout default 30 s
- **Choice:** `--move-timeout` default 30, `0` disables; random fallback; source
  `timeout`.
- **Reason:** long enough to think, short enough that an absent player does not
  stall the game.
- **Rejected:** no timeout by default.

### D33. Stdin timeout via reader thread
- **Choice:** one daemon thread pumps stdin lines into a queue for the whole
  session; the prompt waits with `queue.get(timeout)`; end of input is a `None`
  sentinel put back for later prompts. A deadline covers the whole turn, including
  re-prompts after unparseable text.
- **Reason:** portable; works with a redirected stdin in tests.
- **Rejected:** `select` on stdin (not portable); `signal.alarm` (Unix only, main
  thread only).

### D34. End of input counts as no answer
- **Choice:** the human prompt returns `None` at EOF, so the fallback plays and the
  turn is marked `timeout`; every human agent in the CLI always has a fallback.
- **Reason:** a closed stdin must never hang or crash the game.
- **Rejected:** treating EOF as an error.

### D41. `--max-turns` defaults to 200 · 3ⁿ
- **Context:** with a flat default of 1000, every random game above n = 3 ended
  `unfinished`; ten disks need 2046 turns even for a perfect solo player.
- **Choice:** default schedule length 200 · 3ⁿ (600, 1800, 5400, 16200, 48600, …),
  from measured random play (medians 10, 44, 136, 474, 1434 turns for n = 1..5;
  worst cases 43, 152, 510, 2427, 4175; roughly ×3 per disk). `--max-turns`
  overrides; same default for continuing a replay.
- **Reason:** about three times the observed worst case.
- **Rejected:** a flat number (wrong for every n but one); 4ⁿ (grows faster than
  the data).

### D42. Repetition limit off by default (reverses D15)
- **Context:** with D41's larger caps, every ten-disk random game ended
  `stalemate`: random walkers on a finite board revisit positions by chance, and
  near the start each player has only two legal moves.
- **Choice:** `--repetition-limit` defaults to 0 (off) on every command.
- **Reason:** a repeated position is a stalemate only when players *choose* to
  repeat; random agents never do, and a stalling human is covered by the timeout.
- **Rejected:** 10 by default (D15); off for random only (two defaults for one
  flag).

## Output

### D17. Drawn towers by default
- **Choice:** per-turn view and final board drawn as towers; `--list` for bracket
  lists in the spec's cross layout; `--json`; `--trace` with source marks.
- **Reason:** readable at a glance.
- **Rejected:** bare space-separated numbers.

### D38. Full game trace by default — superseded by D40
- **Choice at the time:** print the trace before the final board; `--no-trace`.
- **Why superseded:** a 44-turn replay showed it was too much by default.

### D39. Bot turns spell out their effect
- **Context:** a human placed a disk on the shared pole and "did not see it" next
  turn; the random opponent had lifted it, and the line `lift 2` hid that.
- **Choice:** bot lines describe the effect and name the shared pole, e.g.
  `Turn 4, player B: lift 2 → took disk 1 from the shared pole`.
- **Reason:** shared-pole events are the whole game.
- **Rejected:** redrawing the human's view after every bot turn (noisy).

### D40. Default output is the final state only (reverses D38)
- **Choice:** default prints the final board and summary for every command;
  `--trace` adds the full game; `--no-trace` removed. Human play still shows every
  turn live.
- **Reason:** the result is what most runs want; the game is one flag away.
- **Rejected:** trace by default (D38).

## Process

### D10. Tooling
- **Choice:** uv; pytest, ruff, pre-commit with ruff hooks only; Python 3.12 pin;
  Markdown docs only.
- **Reason:** the spec's own example is uv; no runtime dependencies.
- **Rejected:** Poetry; Docker (`uv sync` is the whole setup); a pytest pre-commit
  hook (would block red TDD commits); HTML docs (reviewers read Markdown on GitHub).

### D11. TDD visible in git
- **Choice:** per unit, a `test:` commit that fails, then a `feat:` commit that
  passes, then optional `refactor:`; a `docs:` commit closes each stage.
- **Reason:** the spec asks for the journey, not just the result (S1).
- **Rejected:** squashing.

## Documentation

### D21. Where the documents live
- **Choice:** `docs/REQUIREMENTS.md` restates the spec with IDs; this log holds
  decisions; `docs/USAGE.md` is the flag reference; `plans/PLAN.md` is the working
  plan with a status line per stage; `SPEC.md` is the task verbatim.
- **Reason:** a reviewer can see what was given versus what we chose.
- **Rejected:** everything in the README.

### D37. README structure
- **Choice:** the README summarizes this log and the requirements rather than
  repeating them, in reviewer order: quick start, the game, using it, design,
  reuse, beyond the spec, project notes.
- **Reason:** the README is read first; the detail is one link away.
- **Rejected:** copying the decision log into the README; a separate
  ARCHITECTURE.md.

## Scope

### D19. Interfaces and their purposes
- **Choice:** CLI for the spec, developer, and reviewer; the Python API (the
  engine's own functions) as the primary RL path. Future, not built: web UI for
  people, HTTP API for remote programs.
- **Reason:** each audience gets the thinnest thing that serves it.
- **Rejected:** using the CLI as an RL interface (one process per command cannot
  hold state across thousands of steps).

### D20. Scope beyond the spec
- **Choice:** build human play, source tracking, autosave, continuation, early
  ending. Describe but do not build: web UI + HTTP API, RL wrapper, LLM agent.
- **Reason:** the ~2 hour budget; stages 0–3 are a complete submission on their own.
- **Rejected:** building the web UI first (not asked for; would eat the budget).

## Structure

### D45. Four rings; restructure, keep every feature
- **Context:** review feedback: the code was not cleanly abstracted. Additions had
  been attached to the nearest module: five of ten features had logic in `cli.py`
  (498 lines, bigger than the engine), `recording` imported the runner, `render`
  re-stepped whole games.
- **Choice:** keep every feature; reorganise into four rings, each importing only
  inward: core (`engine`), play (`agents`, `runner`), frontends (`recording`,
  `render`, `human`), entry (`cli`). Additions live in rings 3–4 and may not change
  ring 1. The blueprint is in `CLAUDE.md`.
- **Reason:** the problem was structure, not scope; one rule tells where anything goes.
- **Rejected:** cutting back to the spec's two modes (hides the problem instead of
  fixing it).

### D46. `Outcome` carries the moved disk; `Action` owns its text
- **Context:** three places worked out which disk moved (one replayed the game), and
  action text was formatted in two modules and parsed in a third.
- **Choice:** `Outcome.disk` is the disk lifted or placed; `str(action)` and
  `Action.parse(text)` live on `Action`. `SIDES` is the one table of each player's
  pole keys; `is_positive_int` the one integer check.
- **Reason:** carry facts forward instead of recomputing them; one source of truth.
- **Rejected:** a separate text-format module (the action's text is part of the
  action space an RL or network client uses).

### D47. One `source` label per agent
- **Context:** D26 gave agents two attributes, and the runner combined them into
  `Turn.source`: display bookkeeping inside the core loop.
- **Choice:** an agent has one attribute, `source`, the label of the move it just
  chose; the runner copies it. `HumanAgent` sets `timeout` when its fallback moved.
- **Reason:** the agent knows who chose; the runner should not decide it.
- **Rejected:** `choose` returning `(action, source)` (still leaks into the contract
  an RL policy implements).

### D48. Human play is its own frontend module
- **Context:** the prompt, the threaded stdin reader, quit handling, and timeout
  counting sat in `cli.py`, while `ExternalAgent` and `Timeout` sat in the core
  `agents.py` although only human play used them.
- **Choice:** `human.py` holds `LineReader`, `Console` (prompts in, turn lines out),
  and `HumanAgent` (prompt, re-prompt, fallback on timeout, `StopGame`). `agents.py`
  keeps only `RandomAgent` and `ScriptedAgent`.
- **Reason:** an addition lives in the frontend ring and can be removed without
  touching the core; one class replaces `ExternalAgent` + the `ask` callback + the
  prompt object.
- **Rejected:** keeping a generic injected-`ask` agent for a future UI or LLM (not
  built; such an agent is one small class when it is).

### D49. One wording for what a turn did
- **Context:** three texts described a turn: `ok, holding 1` after a human move,
  `lift 2 → took disk 1 from the shared pole` for bots, and the trace, each derived
  differently.
- **Choice:** `render.describe_turn` (`took disk 1 from pole 1`, `put disk 3 on the
  shared pole`, `illegal: … Turn wasted.`) is used by the trace, bot lines, and human
  feedback; it reads `Outcome.disk` (D46).
- **Reason:** one source of truth; shared-pole events read the same everywhere.
- **Rejected:** keeping `ok, holding N` for humans (a second phrasing of the same fact).

### D50. Recording owns its files; CLI only wires
- **Context:** autosave naming, the seed-from-file-name regex, and gluing a continued
  game onto its recording were in `cli.py`; recordings stored moves as text and
  re-parsed them on every use.
- **Choice:** `recording.py` gains `autosave_path`, `seed_in_name`, `append_run`;
  `Recording.moves` are `Action`s, converted to text only in `loads`/`dumps`, and
  validation lives only in `Recording`. The CLI builds agents, calls the runner, and
  prints; `--save`/`--no-save` now also apply to a continued replay.
- **Reason:** each concern in the module that owns it; `cli.py` 498 → 280 lines.
- **Rejected:** a separate `files.py` (one more module for three small functions).

### D51. An `Action` is checked when it is built
- **Context:** after the restructure the code was better organised but barely
  smaller, so the author asked for a real reduction with every feature kept.
- **Choice:** `Action.__post_init__` rejects a malformed move, so `engine._validate`
  disappears and `step` only checks the player and the type; one `check(ok, message,
  error)` helper replaces the repeated `if ...: raise ...` pairs in `from_dict` and
  `Recording`; module docstrings were cut to a few lines each, with the reasoning
  left here where it belongs.
- **Reason:** a malformed action can no longer exist, so nothing downstream has to
  ask; `src/` is 1 329 -> 1 183 lines (801 of them code) with all ten features.
- **Rejected:** a table-driven `add_argument` loop (tried: 7 lines longer once
  formatted, and harder to read); deleting features (they were asked to stay).

### D52. `--no-skip` and the `Agent` protocol removed
- **Context:** going through the code file by file, two things had no owner: the
  `Agent` protocol, which no type checker in this project ever checks, and
  `--no-skip`, an option in no requirement, no decision, and nothing but a row in
  docs/USAGE.md. `allow_skip` also made a game-wide preference a per-agent one.
- **Choice:** delete both. The agent contract is two sentences in the `agents`
  docstring; `RandomAgent` now takes only the generator and picks from `legal`.
- **Reason:** nothing asked for either, and each cost lines in three files.
- **Rejected:** keeping `--no-skip` for shorter random games (`--max-turns` and
  `--repetition-limit` already bound a game).

### D53. Plain tuples instead of `Literal` aliases
- **Context:** `Player`, `Verb`, `PoleIndex` and `Status` were `Literal` types, and
  the same values were written again as runtime tuples and as inline checks. No type
  checker runs here, so the aliases only cost a second copy of each value.
- **Choice:** keep one tuple per set (`PLAYERS`, `VERBS`, `POLES`, `POLE_KEYS`) and
  hint with `str` / `int`. `Action.__post_init__` checks against `VERBS` and `POLES`,
  so every value is written once. The 6 `# type: ignore` comments the aliases needed
  are gone too.
- **Reason:** one source per value; nothing was verifying the narrower hints.
- **Rejected:** `get_args(Literal[...])` to derive the tuples (keeps the meaning in
  the hints, but adds an import and a layer for a reader to follow).
