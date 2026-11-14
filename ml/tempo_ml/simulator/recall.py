"""Per-move recall and move latency of a synthetic client.

Owner: docs/topics/synthetic-clients/record.md, sections 3.3 and 3.4.

Recall is per move: in Repeating Mode each repertoire move's first attempt is
correct with probability R, and a wrong move is taken back and retried (at
most ``DEFAULT_MAX_ATTEMPTS_PER_MOVE`` attempts). A session is clean only when
every first attempt is correct, so its chance is R ** M.

Latency of one attempt:
final_time_ms = baseline_ms + total_hesitation_ms
total_hesitation_ms = raw_hesitation_s * 1000 * exp(beta * (1 - R)) / (1 + alpha * reps)
raw_hesitation_s ~ Lognormal(mu, sigma)

Context multipliers m_depth and m_sharpness (record section 5) are deferred.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from .clients import ClientTraits

DEFAULT_MAX_ATTEMPTS_PER_MOVE = 5


@dataclass(frozen=True)
class MoveEvent:
    """One repertoire move in a session.

    Attributes:
        index: 0-based position of the move within the line's repertoire moves.
        attempt_times_ms: Latency of each attempt; all but the last were wrong
            (Repeating Mode retracts a wrong move and the client retries).
        first_attempt_correct: Whether the first attempt was the repertoire move.
    """

    index: int
    attempt_times_ms: tuple[float, ...]
    first_attempt_correct: bool

    @property
    def time_ms(self) -> float:
        return float(sum(self.attempt_times_ms))


def cognitive_strain(beta: float, R: float) -> float:
    """exp(beta * (1 - R)); 1.0 when R = 1."""
    return math.exp(beta * (1.0 - R))


def practice_multiplier(alpha: float, reps: int) -> float:
    """1 / (1 + alpha * reps); tends to 0 as reps grows."""
    return 1.0 / (1.0 + alpha * reps)


def sample_move_time_ms(
    traits: "ClientTraits",
    R: float,
    reps: int,
    rng: np.random.Generator,
) -> float:
    """Sample one move's latency in milliseconds."""
    raw_hesitation_s = rng.lognormal(mean=traits.mu, sigma=traits.sigma)
    hesitation_ms = (
        raw_hesitation_s
        * 1000.0
        * cognitive_strain(traits.beta, R)
        * practice_multiplier(traits.alpha, reps)
    )
    return traits.baseline_ms + hesitation_ms


def play_move(index: int, R: float, reps: int, traits: "ClientTraits", rng: np.random.Generator,
              max_attempts: int = DEFAULT_MAX_ATTEMPTS_PER_MOVE) -> MoveEvent:
    """One repertoire move in Repeating Mode: attempts until correct or ``max_attempts``."""
    times: list[float] = []
    first_correct = False
    for attempt in range(max_attempts):
        times.append(sample_move_time_ms(traits, R, reps, rng))
        correct = rng.random() < R
        if attempt == 0:
            first_correct = correct
        if correct:
            break
    return MoveEvent(index=index, attempt_times_ms=tuple(times), first_attempt_correct=first_correct)
