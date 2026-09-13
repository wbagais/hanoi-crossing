# Decision log

Every design decision, recorded when it was made. Entry format: context, choice,
reason, alternatives rejected. Stages append to this file in the same commit that
makes the decision. The README's design section is a summary of this log.

## Planning (before stage 0)

### D1. Rule interpretations
- **Context:** the spec leaves several situations open.
- **Choice:** I1–I7 in `docs/REQUIREMENTS.md` (pole 3 must be non-empty to win;
  player-relative pole numbers; malformed raises, illegal wastes; finished game is
  frozen; three end states; both players checked each step; no ownership).
- **Reason:** each keeps the engine simple and the rules text literal.
- **Rejected:** requiring all of a player's own disks on pole 3 (spec never says
  so); treating all-empty as a win (reads against "only pole 3 has disks").

### D2. Engine style: pure functions over an immutable state
- **Context:** engine must be reusable by an RL loop and a concurrent service.
- **Choice:** frozen dataclasses; `step(state, player, action)` returns a new state
  and an outcome; no I/O, randomness, counters, or stored "finished" flag;
  `winner(state)` recomputed from the board; `to_dict` / `from_dict`.
- **Reason:** thousands of games can be held as plain values; serialization is
  trivial; a state loaded from JSON needs no bookkeeping; observation can never
  disagree with the board.
- **Rejected:** mutable `Game` object with internal counters (needs locks and
  copying in a service; harder to snapshot).

### D3. Disks are plain integers; no ownership after setup
- **Reason:** after setup ownership never affects any rule.

### D4. Fixed action space of seven, player-relative
- **Choice:** `lift 1|2|3`, `place 1|2|3`, `skip` in a fixed order (`ALL_ACTIONS`).
- **Reason:** an RL policy can output an index; `legal_actions` is the mask.

### D5. Agent contract
- **Choice:** `choose(observation, legal_actions) -> Action`; an agent never sees
  the full `State`. Random agent takes an injected seeded RNG.
- **Reason:** this is exactly what an external RL or network agent would receive;
  the random player proves the seam (T8).

### D6. One runner
- **Choice:** one loop in `runner.py` (`play_turn`, `run`). Replay, random play,
  human play, and continuation are the same loop with different agents and start
  states. `recording.py` is a file format, not a second runner.
- **Rejected:** a "game type" concept (loses mixed agents; RL needs a learning agent
  vs a fixed opponent).

### D7. Recording format
- **Choice:** JSON `{n, turn_order, moves, sources?}`; turn order is a separate
  string because the spec calls it external.
- **Rejected:** a single list of player-tagged steps (turn order becomes implicit);
  plain text lines (no room for metadata).

### D8. Three end states
- **Choice:** won (engine), unfinished (schedule exhausted, runner), stalemate
  (position with same player to move repeated K times, runner, optional).
- **Reason:** mutual skipping or cycling must terminate; skip is always legal so a
  "no moves" exit never exists.

### D9. External agent with timeout and fallback; move source tracking
- **Choice:** `ExternalAgent(ask, timeout, fallback)`; the injected `ask` owns the
  waiting; on timeout the random fallback plays and the turn is marked `timeout`.
  Every `Turn` carries `source` (human / random / scripted / timeout).
- **Reason:** a human who walks away must not hang the game; output should show who
  chose each move.

### D10. Tooling
- **Choice:** uv; pytest, ruff, pre-commit with ruff hooks only; Python 3.12 pin;
  Markdown docs only.
- **Rejected:** Poetry (spec's own example is uv); Docker (no runtime deps; `uv sync`
  is the whole setup); pytest pre-commit hook (would block red TDD commits); HTML
  docs (reviewers read Markdown on GitHub).

### D11. TDD visible in git
- **Choice:** per unit, a `test:` commit that fails, then a `feat:` commit that
  passes, then optional `refactor:`.

### D12. CLI shape
- **Choice:** one `hanoi` entry point with `replay`, `random`, `play`, `recordings`.
  `random` is shorthand for `play --a random --b random`, kept so the spec's mode is
  visible by name.
- **Rejected:** dropping replay (it is a required deliverable and needs no human).

### D13. Schedule flags
- **Choice:** `--schedule PATTERN` (default `AB`) repeated to fill `--max-turns`;
  `--first A|B` (default A) rotates the pattern to that player's first occurrence.
- **Rejected:** starter chosen by the seed (surprising); alternating only (cannot
  express A moving twice).

### D14. Seed default 0
- **Choice:** `--seed` optional, default `0`, always printed.
- **Reason:** reproducible by default; pass another number for a different game.
- **Rejected:** fresh random seed each run.

### D15. Repetition limit default 10
- **Choice:** `--repetition-limit` default 10 in the CLI, `0` disables; runner
  default off.
- **Rejected:** 3 as in chess (random agents revisit positions often on a small
  board; most random games would end as stalemates).

### D16. Move timeout default 30 s
- **Choice:** `--move-timeout` default 30, `0` disables; random fallback; source
  `timeout`.

### D17. Output: drawn towers by default
- **Choice:** per-turn view and final board drawn as towers; `--list` for bracket
  lists in the spec's cross layout; `--json`; `--trace` with source marks.
- **Rejected:** bare space-separated numbers.

### D18. Autosave
- **Choice:** every finished game (any end status) is written once, at the end, to
  `recordings/<date>-<mode>-n<N>-seed<S>.json`; `--save` renames; `--no-save`
  disables. Replay reads only files, never another game's memory.
- **Rejected:** writing after every turn; saving only on request.

### D19. Interfaces and their purposes
- **Choice:** CLI for the spec, developer, and reviewer; Python API (the engine's
  own functions) as the primary RL path. Future, not built: web UI for people,
  HTTP API for remote programs.
- **Rejected:** using the CLI as an RL interface (one process per command cannot
  hold state across thousands of steps).

### D20. Scope beyond the spec
- **Choice:** build human play, source tracking, autosave, continuation. Describe
  but do not build: web UI + HTTP API, RL wrapper, LLM agent.
- **Reason:** ~2 hour budget; stages 0–3 are a complete submission on their own.

## Stage 0

### D21. Requirements and decisions live in `docs/`, plan in `plans/`
- **Choice:** `docs/REQUIREMENTS.md` restates the spec with IDs; this log holds
  decisions; `plans/PLAN.md` is the working plan with a status line per stage.
- **Reason:** a reviewer can see what was given versus what we chose.

## Stage 1

### D22. `State` hashes by content despite dict fields
- **Context:** frozen dataclasses with dict fields are not hashable by default.
- **Choice:** keep `poles` / `hands` as plain dicts (readable key access) and
  define `__hash__` over the values in fixed key order; `__post_init__` copies the
  mappings and converts pole sequences to tuples.
- **Reason:** states must be usable as set members and dict keys (stalemate
  detection in the runner, caching in a service) while staying readable.
- **Rejected:** tuple-of-tuples storage with positional access (unreadable);
  `MappingProxyType` (still unhashable).

### D23. Validation split: `_validate` raises, `_illegal_reason` explains
- **Choice:** malformed player/verb/pole raises `ValueError` before anything else;
  a well-formed action gets a reason string or `None`. `legal_actions` is defined
  as "the actions whose reason is None", so the two can never disagree.
- **Rejected:** a separate legality table that `step` and `legal_actions` each
  consult (two sources of truth).

### D24. `bool` is not an int here
- **Choice:** `initial_state` and `from_dict` reject `True`/`False` for `n`, disks,
  and hands even though `bool` subclasses `int`.
- **Reason:** a JSON `true` sneaking in as disk size 1 would be a silent bug.

### D25. Engine size
- **Result:** 267 lines including the module docstring; the test
  `test_engine_is_under_500_lines_including_blanks_and_docstrings` enforces C1 on
  the strict `wc -l` reading.

## Stage 2

### D26. Agents carry `kind` and `last_fell_back`; the runner derives `Turn.source`
- **Context:** turns must show who chose each move (A2) without changing the
  `choose` signature that an RL policy would implement.
- **Choice:** two attributes on the agent instead of a richer return type. The
  runner reads them after `choose` and writes `source` (`timeout` when
  `last_fell_back` is set, else `kind`).
- **Rejected:** `choose` returning a `(action, source)` pair (leaks a display
  concern into the agent contract).

### D27. The injected `ask` owns the waiting
- **Choice:** `ExternalAgent.choose` passes the timeout to `ask` and reacts to a
  `Timeout` exception or a `None` return. No clock, thread, or `input()` in
  `agents.py`.
- **Reason:** the CLI (stdin thread), a UI (request deadline), and tests (a fake)
  each wait differently; the agent should not care.

### D28. Stalemate counts (state, player-to-move) pairs at the top of each turn
- **Choice:** `run` keeps a `Counter` keyed on the frozen `State` plus the player
  about to move; reaching `repetition_limit` ends the game before that turn is
  played. Off when the limit is `None` or `0`.
- **Reason:** mutual skipping and cycles both repeat this pair; hashing the state
  by content (D22) makes the counter trivial.

### D29. `run` checks status before each entry and once after the loop
- **Choice:** a win found at the top of an entry counts every remaining entry as
  unplayed; a win on the very last entry is still reported as `won` by the
  post-loop check.

### D30. Recording validation lives in `Recording.__post_init__`
- **Choice:** any `Recording`, whether loaded from JSON or built by `from_run`,
  is validated on construction; `loads` only checks JSON shape and key names
  first. Unknown top-level keys are rejected.
- **Reason:** one place to enforce the format; a bad recording can never be
  written.

### D31. `replay` is `run` with scripted agents
- **Choice:** `to_agents` splits the moves per player in turn order; `replay`
  calls the one runner from `initial_state(n)`. Recorded illegal moves are
  wasted again, exactly as the spec requires (R9).

## Stage 3

### D32. `run` gains an optional `on_turn` callback
- **Context:** human play needs live output per turn (bot moves, results,
  timeouts) without the CLI owning a second loop.
- **Choice:** `run(..., on_turn=None)` calls back after every played turn with
  the turn and the new state. The loop stays the only loop.
- **Rejected:** driving `play_turn` from the CLI (duplicates status and stalemate
  logic); printing inside agents (agents must stay I/O-free).

### D33. Stdin timeout via a reader thread and a queue
- **Choice:** one daemon thread pumps stdin lines into a queue for the whole
  session; the prompt waits with `queue.get(timeout)`. End of input is a `None`
  sentinel that is put back so later prompts see it immediately.
- **Reason:** portable (no signals, works with a redirected stdin in tests); a
  deadline covers the whole turn, including re-prompts after unparseable text.
- **Rejected:** `select` on stdin (not portable); `signal.alarm` (Unix only, main
  thread only).

### D34. End of input counts as "no answer"
- **Choice:** the human prompt returns `None` at EOF, so the random fallback
  plays and the turn is marked `timeout`. Every human agent in the CLI always has
  a fallback, even with `--move-timeout 0`.
- **Reason:** a closed stdin must never hang or crash the game.

### D35. Continuation recordings are the whole game
- **Choice:** when an unfinished replay is continued, the autosaved recording is
  the original moves followed by the continuation moves (sources `scripted` for
  the original part), so replaying it reproduces the full game from the initial
  position.
- **Rejected:** saving only the continuation (would not replay from the start).

### D36. `hanoi recordings` replays each file to report its status
- **Choice:** the listing shows n, seed (parsed from the file name), turns,
  status, winner, and modification time. Status comes from a real replay.
- **Reason:** files are small and replay is instant; a stored status could lie.

## Stage 4

### D37. README structure
- **Choice:** the README summarizes this log and `docs/REQUIREMENTS.md` rather
  than repeating them: game, interpretations, design per module, frontends, reuse
  (with an RL wrapper sketch that is explicitly not shipped), additions, rejected
  alternatives, future work, layout, AI usage, journey.
- **Reason:** a reviewer reads the README first; the detail is one link away.
- **Rejected:** copying the decision log into the README (too long); a separate
  ARCHITECTURE.md (the README's design section is short enough).

## After stage 4

### D38. The full game is shown by default
- **Context:** after playing a game the user wants to see every turn, not only the
  final board and summary.
- **Choice:** the turn-by-turn trace (index, player, action, result, source) is
  printed before the final board for every command; `--no-trace` hides it.
  `--trace` is still accepted as a no-op so old invocations keep working.
- **Rejected:** keeping the trace opt-in (the default output hid the game).

### D39. Bot turns spell out their effect
- **Context:** a human placed a disk on the shared pole and "did not see it" on the
  next turn: the random opponent had lifted it, and the one-line bot message
  `lift 2` did not make that obvious.
- **Choice:** bot turn lines describe the effect, e.g.
  `Turn 4, player B: lift 2 → took disk 1 from the shared pole`, and name the
  shared pole explicitly for both lifts and places.
- **Rejected:** redrawing the human's view after every bot turn (noisy for long
  random stretches).

### D40. Default output is the final state only (reverses D38)
- **Context:** after trying a 44-turn replay, the full trace by default was too
  much; during human play every turn is already printed live.
- **Choice:** default prints the final board and summary; `--trace` adds the full
  game. `--no-trace` is removed.
- **Rejected:** trace by default (D38).

### D41. `--max-turns` defaults to 200 · 3ⁿ
- **Context:** with a flat default of 1000, every random game above n = 3 ended
  `unfinished`; ten disks need 2046 turns even for a perfect solo player.
- **Measurement:** random-vs-random games over 20 seeds needed median 10, 44,
  136, 474, 1434 turns for n = 1..5, worst cases 43, 152, 510, 2427, 4175. Roughly
  ×3 per disk.
- **Choice:** default schedule length 200 · 3ⁿ (600, 1800, 5400, 16200, 48600, …),
  about three times the observed worst case; `--max-turns` still overrides. Same
  default for continuing an unfinished replay.
- **Rejected:** a flat number (wrong for every n but one); 4ⁿ (grows faster than
  the data and makes large n slow for no benefit).
