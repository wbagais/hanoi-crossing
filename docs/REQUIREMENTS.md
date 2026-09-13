# Requirements

The task specification (`SPEC.md`) restated as checkable items. IDs are used in
`plans/PLAN.md` (traceability table) and in test names. The final section lists
what we decided where the spec is silent, and what we added beyond it.

## Game rules

| ID | Requirement |
|---|---|
| R1 | Two players. Each has three poles and N disks stacked on their pole 1, largest at the bottom. |
| R2 | The middle pole (pole 2) is shared: both players see it and either can interact with disks on it. |
| R3 | Neither player can see the other's poles 1 and 3, nor what the other holds in hand. |
| R4 | Player A starts with odd-sized disks (1, 3, 5, …); player B with even-sized disks (2, 4, 6, …). |
| R5 | Placement rule: a disk may only be placed on an empty pole or on a strictly larger disk. |
| R6 | Turn-based. On a turn a player performs exactly one action: lift the top disk of a visible pole into hand, place the held disk onto a visible pole, or skip. |
| R7 | A player holds at most one disk at a time. |
| R8 | Either player may lift any top disk from the shared pole. |
| R9 | An illegal action does not change the game state; the turn is wasted. |
| R10 | Turn order is external: a sequence saying which player acts on each step. The engine must not assume any turn-order pattern. |
| R11 | Win: a player wins when their hand is empty and, among their visible poles, only pole 3 has disks. |
| R12 | Board naming: A sees 1a – 2 – 3a; B sees 1b – 2 – 3b. |
| R13 | Worked example (N = 1, turn order A B A): A lifts disk 1 from 1a; B lifts disk 2 from 1b; A places disk 1 on 3a and wins. |

Board:

```
        1a
        |
 1b -- [2] -- 3b
        |
        3a
```

## Task

| ID | Requirement |
|---|---|
| T1 | A game engine in Python. |
| T2 | A replay CLI: reads pre-recorded moves plus turn order, outputs the final state. |
| T3 | A random-play mode: both players make random valid moves. |
| T4 | Tests exercise the engine directly. |
| T5 | The engine must later serve, unchanged, as the environment core of an RL training loop. |
| T6 | The engine must later serve, unchanged, as the core of an online simulation service holding many concurrent games. |
| T7 | Do not build the RL loop or the service. |
| T8 | The random player must consume the engine exactly the way such an external agent would. |
| T9 | Input format, output format, and internal model are ours to design. |
| T10 | Where the rules are open to interpretation, decide and document. |
| T11 | Describe choices and design decisions in a README. |

## Constraints

| ID | Requirement |
|---|---|
| C1 | Core engine under 500 lines of Python. |
| C2 | Standard project layout (e.g. uv). |

## Submission

| ID | Requirement |
|---|---|
| S1 | Mandatory git repository; the journey matters, not just the result. |
| S2 | Unrestricted AI use allowed; disclose what was used and how. |
| S3 | Expected effort about two hours; a PoC / WIP submission is acceptable. |

## Interpretations and additions

### Interpretations (spec is silent; we decided)

| # | Decision | Reason |
|---|---|---|
| I1 | All visible poles empty is **not** a win; pole 3 must hold at least one disk. | "Only pole 3 has disks" reads as pole 3 having disks. |
| I2 | Actions name poles 1, 2, 3 from the acting player's side; the opponent's poles cannot be expressed. | Removes a whole class of invalid input; matches R3. |
| I3 | Malformed input (bad verb or pole) raises an error; a well-formed but illegal move wastes the turn and reports a reason. | R9 covers illegal moves; garbage input is a programming error, not a move. |
| I4 | A finished game rejects every further action, including skip. | Keeps the final state frozen for replay and services. |
| I5 | Games end **won**, **stalemate** (same position with the same player to move seen K times) or **unfinished** (schedule exhausted). Schedule entries after the end count as unplayed. | R10 gives no end besides winning; mutual skipping or cycling must terminate. |
| I6 | Both players are checked for a win after every action. | An opponent's lift from pole 2 can complete your win. |
| I7 | Ownership of disks is not tracked after setup. | R2 and R8 let disks cross sides; the win condition never mentions ownership. |

### Additions beyond the spec (marked as such in the README)

| # | Addition | Why |
|---|---|---|
| A1 | `hanoi play`: human play against a random agent or another human, with a per-move timeout and random fallback. | Exercises the "external agent" seam with a real person. |
| A2 | Each recorded turn carries its **source** (human, random, scripted, timeout) for display. | Lets output show who chose each move. |
| A3 | Autosave of every finished game to `recordings/`; `hanoi recordings` lists them. | Gives replay fixtures for free and lets an unfinished game be continued. |
| A4 | Continue an unfinished replay with random agents (prompt or `--continue`). | Natural use of the same loop from a different start state. |
| A5 | Drawn tower output by default; `--list`, `--json`, `--trace` alternatives. | Readability. |
| A6 | Future work, not built: web UI + HTTP API, RL wrapper, LLM agent. | Described in the README to show the engine needs no change. |
