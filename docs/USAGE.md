# Usage reference

Every command, flag, default, and exit code of the `hanoi` CLI. The README has the
short version; `uv run hanoi <command> --help` prints the same defaults from the
code.

```
uv run hanoi replay FILE [options]
uv run hanoi random --n N [options]
uv run hanoi play --a SRC --b SRC --n N [options]
uv run hanoi recordings [--dir DIR]
```

## Flags shared by every command

| Flag | Required | Default | What it does |
|---|---|---|---|
| `--json` | optional | off | Print one JSON object instead of text: `n`, `seed`, `schedule`, `status`, `winner`, `state` (the engine's `to_dict`), `counts`, `turns` (index, player, action, legal, reason, source), `saved`. Also disables every prompt. |
| `--list` | optional | off | Show poles as bracket lists in the spec's cross layout instead of drawn towers. |
| `--trace` | optional | off | Print the full game before the final board: one line per turn, `index player action → result [source]`. |
| `--seed S` | optional | `0` | Seeds the random players (and the random fallback for humans). Same seed, same game. Pass any other integer for a different game. |
| `--max-turns N` | optional | `200 · 3ⁿ` | Schedule length; reaching it ends the game as `unfinished`. The default follows measured random play: 600, 1 800, 5 400, 16 200, 48 600 for N = 1..5. For `replay` it is the length of the continuation. |
| `--repetition-limit K` | optional | off (`0`) | End as `stalemate` when the same position with the same player to move has occurred K times. Off by default because random players revisit positions by chance, not by choice. For `replay` it applies to the continuation. |

`recordings` takes none of the game flags.

## `hanoi replay FILE`

Reads a recording, restarts from the initial position, re-plays every recorded move
through the runner with two scripted players, and prints the final state. Recorded
illegal moves are wasted again, as they were originally.

| Flag | Required | Default | What it does |
|---|---|---|---|
| `FILE` | required | — | Path to a recording JSON file (`n`, `turn_order`, `moves`, optional `sources`). Find one with `hanoi recordings`. |
| `--continue` | optional | ask | If the recording ends unfinished, let random players finish it without asking. |
| `--no-continue` | optional | ask | Never continue, never ask. |
| `--schedule P` | optional | `AB` | Turn-order pattern for the continuation, rotated to start with the player after the last recorded turn. |

When the recording ends unfinished and stdin is a terminal, replay asks
`Game unfinished. Let random players finish it? [y/N]`. With `--json`, or when
stdin is not a terminal, it never asks. A continued game is autosaved as one
recording containing the original moves followed by the continuation.

## `hanoi random --n N`

Both players random. Identical to `play --a random --b random`; kept as its own
command so the spec's mode is visible by name.

| Flag | Required | Default | What it does |
|---|---|---|---|
| `--n N` | required | — | Disks per player. A gets sizes 1, 3, …, 2N−1; B gets 2, 4, …, 2N. |
| `--first A\|B` | optional | `A` | Who takes turn 1. Rotates the schedule pattern to that player's first occurrence: `AB` → `BA`, `AAB` → `BAA`. Error (exit 2) if the pattern has no such player. |
| `--schedule P` | optional | `AB` | Turn-order pattern, letters A and B only, repeated to fill `--max-turns`. `AAB` gives A two turns then B one; `A` lets A play alone. Printed before turn 1. |
| `--no-skip` | optional | off | Random players never choose skip unless it is the only legal action. |
| `--save FILE` | optional | autosave | Write the recording to `FILE` instead of the autosave name. |
| `--no-save` | optional | off | Do not write a recording. |

Autosave: every finished game, whatever its status, is written once at the end to
`recordings/<date>-<time>-<mode>-n<N>-seed<S>.json`, and the path is printed. The
folder is git-ignored.

## `hanoi play --a SRC --b SRC --n N`

Any mix of players. Takes every flag of `random` plus:

| Flag | Required | Default | What it does |
|---|---|---|---|
| `--a SRC` | required | — | Player A's move source: `random` or `human`. |
| `--b SRC` | required | — | Player B's move source: `random` or `human`. |
| `--move-timeout S` | optional | `30` | Seconds a human has to answer the prompt. When it runs out, a random legal move is played for them and the turn is marked `timeout`. `0` disables the limit. |
| `--max-timeouts K` | optional | `3` | The K-th unanswered prompt in a row ends the game as `unfinished` (the first K−1 are played by the random fallback). `1` means never play for me; `0` never ends the game this way. |

A human turn prints that player's view only (own poles 1 and 3, the shared pole 2,
own hand), the legal actions, the remaining seconds, and the prompt `A>` or `B>`.
Accepted input: `lift N`, `place N`, `skip`, with N = 1, 2, 3 from that player's
side. Text that is not a move is re-prompted at no cost; a move that breaks a rule
wastes the turn, as the rules say. End of input on stdin counts as no answer.
Opponent turns print one line each, for example
`Turn 4, player B: lift 2 → took disk 1 from the shared pole`. Two humans on one
terminal see each other's turns.

### Ending a game early

| How | Effect |
|---|---|
| type `quit` (or `q`, `exit`) at the prompt | game ends as `unfinished`, is autosaved, prints `game ended: player A quit` |
| Ctrl-C during a human turn | same, with `game ended: interrupted` |
| K unanswered prompts in a row (`--max-timeouts`, default 3) | same, with `game ended: player A did not answer 3 prompts in a row` |
| Ctrl-C during a random game or replay | exits with code 130; nothing is saved |

An unfinished autosaved game can be picked up later with
`hanoi replay <file> --continue`.

### Who can make an illegal move

Random players never do: they choose only from the legal actions. Illegal moves
come from a human typing one, or from a recording that contains one, and are
replayed as the wasted turns they were.

## `hanoi recordings`

| Flag | Required | Default | What it does |
|---|---|---|---|
| `--dir D` | optional | `recordings/` | Folder to list. |

Prints one line per file: name, `n`, seed (from the file name), turns, status,
winner, modification time. Status comes from replaying the file. Prints
`no recordings in recordings/` when the folder is empty or missing.

## Exit codes

| Code | Meaning |
|---|---|
| 0 | Normal, whatever the game's status. |
| 1 | The recording file is missing or invalid; the message names the problem. |
| 2 | Bad arguments, including `--first` naming a player absent from `--schedule`. |

## Game end statuses

| Status | Meaning |
|---|---|
| `won` | A player's hand is empty, their pole 1 and the shared pole are empty, and their pole 3 has disks. Checked for both players after every action. |
| `unfinished` | The game stopped before anyone won: the schedule ran out (`--max-turns`); the recording stopped; a human typed `quit` or pressed Ctrl-C; or a human failed to answer `--max-timeouts` prompts in a row (default 3) and is treated as gone. The printed `game ended: …` line says which. The game is autosaved and can be continued with `replay --continue`. |
| `stalemate` | Only with `--repetition-limit`: the same position with the same player to move recurred K times. |

## Examples

```bash
uv run hanoi replay examples/spec_n1.json                   # the spec's example
uv run hanoi replay examples/n3_blocked_win.json --trace    # 44 turns, every one shown
uv run hanoi replay examples/n2_unfinished.json --continue  # finish it with random players
uv run hanoi random --n 3 --seed 7 --list                   # compact board
uv run hanoi random --n 2 --first B --schedule AAB --trace  # B starts, A gets double turns
uv run hanoi play --a human --b random --n 2 --move-timeout 0   # no clock
uv run hanoi play --a human --b human --n 1 --repetition-limit 5
uv run hanoi recordings
```
