"""Turn-by-turn game state.

The 2020 version tracked the match with a single ``self.games`` counter that
was compared against ``5``.  That had two consequences: player one got three
turns to player two's two, and a draw left the match in a state it could never
leave (the counter sailed past five, so the end-of-game check never fired
again).  This module replaces it with an explicit state machine that gives
every player the same number of turns and settles draws with a sudden-death
roll-off.
"""

from __future__ import annotations

import random
from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import Enum

from .rules import TurnResult, play_turn, roll_die

DEFAULT_ROUNDS = 5


class GameError(RuntimeError):
    """Raised when the game is asked to do something the rules forbid."""


class GameState(Enum):
    IN_PROGRESS = "in_progress"
    TIE_BREAK = "tie_break"
    FINISHED = "finished"


@dataclass(frozen=True)
class GameConfig:
    """Tunable match settings."""

    rounds: int = DEFAULT_ROUNDS
    #: The classic specification never lets a score drop below zero.
    floor_at_zero: bool = True

    def __post_init__(self) -> None:
        if self.rounds < 1:
            raise ValueError("a match needs at least one round")


@dataclass(frozen=True)
class TurnEvent:
    """A record of one completed turn, used for the on-screen log and tests."""

    player: str
    round_number: int
    score_before: int
    score_after: int
    result: TurnResult | None = None
    tie_break_roll: int | None = None

    @property
    def is_tie_break(self) -> bool:
        return self.tie_break_roll is not None

    def describe(self) -> str:
        if self.result is not None:
            return f"{self.player}: {self.result.describe()} = {self.score_after}"
        return f"{self.player}: tie-break roll {self.tie_break_roll}"


@dataclass
class DiceGame:
    """A match between two (or more) players.

    Drive it by calling :meth:`take_turn` until :attr:`is_finished` is true;
    the front ends only render what the engine reports.
    """

    players: Sequence[str]
    config: GameConfig = field(default_factory=GameConfig)
    rng: random.Random = field(default_factory=random.Random)

    def __post_init__(self) -> None:
        names = list(self.players)
        if len(names) < 2:
            raise GameError("a match needs at least two players")
        if len(set(names)) != len(names):
            raise GameError("each player must have a distinct name")
        self.players = names
        self.scores: dict[str, int] = dict.fromkeys(names, 0)
        self.history: list[TurnEvent] = []
        self.tie_break_rolls: dict[str, int] = {}
        self._contenders: list[str] = list(names)
        self._turn_index = 0
        self._round = 1
        self._state = GameState.IN_PROGRESS
        self._winner: str | None = None

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------
    @property
    def state(self) -> GameState:
        return self._state

    @property
    def is_finished(self) -> bool:
        return self._state is GameState.FINISHED

    @property
    def winner(self) -> str | None:
        return self._winner

    @property
    def round_number(self) -> int:
        """The round being played (or the last one played, once finished)."""
        return self._round

    @property
    def current_player(self) -> str | None:
        if self.is_finished:
            return None
        return self._contenders[self._turn_index]

    @property
    def leader(self) -> str | None:
        """The single player in front, or ``None`` while the lead is shared."""
        best = max(self.scores.values())
        leaders = [name for name, score in self.scores.items() if score == best]
        return leaders[0] if len(leaders) == 1 else None

    def standings(self) -> list[tuple]:
        """Scores highest first, ties broken by name for a stable display."""
        return sorted(self.scores.items(), key=lambda item: (-item[1], item[0]))

    def status_line(self) -> str:
        if self.is_finished:
            return f"{self._winner} wins with {self.scores[self._winner]} points"
        if self._state is GameState.TIE_BREAK:
            return f"Tie-break! {self.current_player} to roll"
        return f"Round {self._round} of {self.config.rounds} - {self.current_player} to roll"

    # ------------------------------------------------------------------
    # Play
    # ------------------------------------------------------------------
    def take_turn(self) -> TurnEvent:
        """Play the current player's turn and advance the match."""
        if self.is_finished:
            raise GameError("the match is already over")
        if self._state is GameState.TIE_BREAK:
            return self._take_tie_break_turn()
        return self._take_scoring_turn()

    def _take_scoring_turn(self) -> TurnEvent:
        player = self._contenders[self._turn_index]
        result = play_turn(self.rng)
        before = self.scores[player]
        after = before + result.points
        if self.config.floor_at_zero:
            after = max(0, after)
        self.scores[player] = after

        event = TurnEvent(
            player=player,
            round_number=self._round,
            score_before=before,
            score_after=after,
            result=result,
        )
        self.history.append(event)
        self._advance_scoring_turn()
        return event

    def _advance_scoring_turn(self) -> None:
        self._turn_index += 1
        if self._turn_index < len(self._contenders):
            return
        # Everyone has played this round.
        self._turn_index = 0
        if self._round < self.config.rounds:
            self._round += 1
            return
        self._resolve(list(self.players))

    def _take_tie_break_turn(self) -> TurnEvent:
        player = self._contenders[self._turn_index]
        roll = roll_die(self.rng)
        self.tie_break_rolls[player] = roll

        event = TurnEvent(
            player=player,
            round_number=self._round,
            score_before=self.scores[player],
            score_after=self.scores[player],
            tie_break_roll=roll,
        )
        self.history.append(event)

        self._turn_index += 1
        if self._turn_index < len(self._contenders):
            return event

        # Every contender has rolled - highest roll takes it, else roll again.
        best = max(self.tie_break_rolls.values())
        survivors = [n for n in self._contenders if self.tie_break_rolls[n] == best]
        self._turn_index = 0
        if len(survivors) == 1:
            self._finish(survivors[0])
        else:
            self._contenders = survivors
            self.tie_break_rolls = {}
        return event

    def _resolve(self, contenders: Sequence[str]) -> None:
        """Declare a winner, or drop into sudden death if the scores are level."""
        best = max(self.scores[name] for name in contenders)
        tied = [name for name in contenders if self.scores[name] == best]
        if len(tied) == 1:
            self._finish(tied[0])
        else:
            self._state = GameState.TIE_BREAK
            self._contenders = tied
            self.tie_break_rolls = {}
            self._turn_index = 0

    def _finish(self, winner: str) -> None:
        self._state = GameState.FINISHED
        self._winner = winner
        self._contenders = list(self.players)

    def reset(self) -> None:
        """Start a fresh match with the same players and settings."""
        self.__post_init__()
