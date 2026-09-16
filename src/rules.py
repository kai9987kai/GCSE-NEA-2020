"""The dice rules, expressed as pure functions.

Keeping the rules free of Tkinter (and of ``time.sleep``) means they can be
unit tested, replayed deterministically with a seeded ``random.Random``, and
reused by both the GUI and the terminal front end.
"""

from __future__ import annotations

import random
from collections.abc import Sequence
from dataclasses import dataclass

#: Number of faces on each die.
DIE_FACES = 6
#: Awarded when the two dice add up to an even number.
EVEN_BONUS = 10
#: Deducted when the two dice add up to an odd number.
ODD_PENALTY = -5


@dataclass(frozen=True)
class TurnResult:
    """The outcome of a single turn.

    ``dice`` holds the two scoring dice, ``bonus_die`` the extra die rolled
    after a double, and ``adjustment`` the even/odd modifier.
    """

    dice: tuple[int, ...]
    adjustment: int
    bonus_die: int | None = None

    @property
    def dice_total(self) -> int:
        return sum(self.dice)

    @property
    def is_double(self) -> bool:
        return len(set(self.dice)) == 1 and len(self.dice) > 1

    @property
    def points(self) -> int:
        """Points this turn is worth, before any per-game score floor."""
        return self.dice_total + self.adjustment + (self.bonus_die or 0)

    def describe(self) -> str:
        """A one-line, human readable summary used by both front ends."""
        dice = " + ".join(str(die) for die in self.dice)
        parts = [f"rolled {dice} = {self.dice_total}"]
        parts.append(f"{'even' if self.dice_total % 2 == 0 else 'odd'} {self.adjustment:+d}")
        if self.bonus_die is not None:
            parts.append(f"double! bonus die {self.bonus_die:+d}")
        return f"{', '.join(parts)} -> {self.points:+d}"


def roll_die(rng: random.Random | None = None) -> int:
    """Roll a single fair die."""
    generator = rng or random
    return generator.randint(1, DIE_FACES)


def roll_dice(count: int = 2, rng: random.Random | None = None) -> tuple[int, ...]:
    """Roll *count* dice and return them in the order they were thrown."""
    return tuple(roll_die(rng) for _ in range(count))


def score_dice(dice: Sequence[int]) -> int:
    """Return the even/odd adjustment for an already-thrown pair of dice."""
    return EVEN_BONUS if sum(dice) % 2 == 0 else ODD_PENALTY


def play_turn(rng: random.Random | None = None) -> TurnResult:
    """Play one full turn: two dice, the even/odd modifier, and a double bonus."""
    dice = roll_dice(2, rng)
    bonus = roll_die(rng) if len(set(dice)) == 1 else None
    return TurnResult(dice=dice, adjustment=score_dice(dice), bonus_die=bonus)
