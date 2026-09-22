"""Human play at the terminal (an addition beyond the spec, A1/A2).

``Console`` is the terminal side of one game: it reads lines from stdin (with a
timeout) and prints what happened after each turn. ``HumanAgent`` is a player at
that console. It implements the same ``choose`` contract as every other agent, so
the runner cannot tell a person from a program.

When a person does not answer in time (or input ends), the fallback agent moves
for them and the turn is labelled ``timeout``. The game ends (``StopGame``) on
``quit``, on Ctrl-C, or after ``max_timeouts`` unanswered prompts in a row, so an
absent person never leaves the game playing itself for hours.
"""

from __future__ import annotations

import queue
import threading
import time
from collections.abc import Sequence
from typing import IO

from .agents import Agent
from .engine import Action, Observation, State
from .render import describe_turn, move_text, render_view
from .runner import StopGame, Turn

QUIT_WORDS = ("quit", "q", "exit")
PROMPT_HELP = "not a move, try again: lift N | place N | skip  (N = 1, 2, 3)"


class Timeout(Exception):
    """No line arrived before the deadline."""


class LineReader:
    """Reads stdin lines on a thread so a prompt can give up after a timeout."""

    def __init__(self, stream: IO[str]) -> None:
        self._stream = stream
        self._queue: queue.Queue[str | None] = queue.Queue()
        self._started = False

    def _pump(self) -> None:
        for line in self._stream:
            self._queue.put(line)
        self._queue.put(None)

    def get(self, timeout: float | None) -> str | None:
        """Next line, or None at end of input. Raises Timeout when time runs out."""
        if not self._started:
            self._started = True
            threading.Thread(target=self._pump, daemon=True).start()
        try:
            line = self._queue.get(timeout=timeout)
        except queue.Empty:
            raise Timeout from None
        if line is None:
            self._queue.put(None)  # stay at end of input for every later call
        return line


class Console:
    """The terminal side of one game: prompts in, turn results out."""

    def __init__(self, reader: LineReader, chat: IO[str], style: str = "tower") -> None:
        self.reader = reader
        self.chat = chat
        self.style = style
        self.turns_played = 0

    def say(self, text: str = "") -> None:
        self.chat.write(text + "\n")

    def prompt(self, text: str, timeout: float | None = None) -> str | None:
        """Show ``text`` without a newline and read one line (None at end of input)."""
        self.chat.write(text)
        self.chat.flush()
        return self.reader.get(timeout)

    def on_turn(self, turn: Turn, state: State) -> None:
        """Runner callback: print each turn as it happens."""
        self.turns_played = turn.index
        if turn.source == "human":
            self.say(f"  {describe_turn(turn)}")
        elif turn.source == "timeout":
            self.say(
                f"  time is up: random move played for {turn.player}: {turn.action}   [timeout]"
            )
        else:
            self.say(f"Turn {turn.index}, player {turn.player}: {move_text(turn)}")


class HumanAgent:
    """A person typing moves at a ``Console``."""

    def __init__(
        self,
        player: str,
        n: int,
        console: Console,
        fallback: Agent,
        timeout: float | None = None,
        max_timeouts: int = 3,
    ) -> None:
        self.player, self.n, self.console = player, n, console
        self.fallback, self.timeout, self.max_timeouts = fallback, timeout, max_timeouts
        self.unanswered = 0
        self.source = "human"

    def choose(self, observation: Observation, legal: Sequence[Action]) -> Action:
        console = self.console
        index = console.turns_played + 1
        console.say()
        console.say(
            render_view(observation, self.player, index, self.n, legal, console.style, self.timeout)
        )
        action = self._read_move()
        if action is not None:
            self.unanswered = 0
            self.source = "human"
            return action
        self.unanswered += 1
        if self.max_timeouts and self.unanswered >= self.max_timeouts:
            self._end(f"player {self.player} did not answer {self.unanswered} prompts in a row")
        self.source = "timeout"
        return self.fallback.choose(observation, legal)

    def _read_move(self) -> Action | None:
        """The typed move; None when time ran out or input ended. Re-prompts on garbage."""
        deadline = None if self.timeout is None else time.monotonic() + self.timeout
        while True:
            remaining = None if deadline is None else max(0.0, deadline - time.monotonic())
            try:
                line = self.console.prompt(f"{self.player}> ", remaining)
            except Timeout:
                line = None
            except KeyboardInterrupt:
                self.console.say()
                self._end("interrupted")
            if line is None:
                self.console.say()
                return None
            text = line.strip().lower()
            if text in QUIT_WORDS:
                self._end(f"player {self.player} quit")
            try:
                return Action.parse(text)
            except ValueError:
                self.console.say(f"  {PROMPT_HELP}")

    def _end(self, reason: str) -> None:
        self.console.say(f"  game ended: {reason}")
        raise StopGame(reason)
