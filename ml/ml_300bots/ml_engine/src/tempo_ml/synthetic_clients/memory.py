"""Hidden memory state of one line for one synthetic client.

Specified (synthetic-clients record, sections 3.2 and 3.5):
- retrievability R(t, S) = (1 + F * t / S) ** (-C)
- reps update: +1 after a clean session, max(0, reps - 2) after a blunder

Stability S evolves through a pluggable ``StabilityModel``; the default is
``MultiplicativeStability``. FSRS's own stability update is deliberately not
used as ground truth: FSRS fitted on such data would only recover its own
generator.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import numpy as np

BLUNDER_REPS_PENALTY = 2


def retrievability(t_days: float, stability: float, C: float) -> float:
    """Power-law forgetting curve R(t, S) with F = 0.9^(-1/C) - 1."""
    if t_days < 0.0:
        raise ValueError(f"t_days must be >= 0, got {t_days}")
    if stability <= 0.0:
        raise ValueError(f"stability must be > 0, got {stability}")
    F = 0.9 ** (-1.0 / C) - 1.0
    return float((1.0 + F * t_days / stability) ** (-C))


def next_reps(reps: int, blundered: bool) -> int:
    """Practice accumulation with the soft 2-step blunder penalty."""
    if blundered:
        return max(0, reps - BLUNDER_REPS_PENALTY)
    return reps + 1


class StabilityModel(Protocol):
    """How a line's stability S evolves. Pluggable; see module docstring."""

    def initial(self) -> float:
        """Stability (days) after the first exposure to a line."""
        ...

    def after_success(self, stability: float, R: float) -> float:
        """Stability after a clean session that started at retrievability R."""
        ...

    def after_lapse(self, stability: float, R: float) -> float:
        """Stability after a session with at least one blunder."""
        ...


@dataclass(frozen=True)
class MultiplicativeStability:
    """Default ground-truth stability dynamics.

    - first exposure: S = initial_days
    - clean session:  S <- S * (1 + growth * exp(spacing_gain * (1 - R)))
      (always grows; grows more when retrieval was harder, i.e. a spacing effect)
    - lapse:          S <- min(S, max(min_days, S * lapse_factor))

    The default values are not calibrated on human data; Stage 2 calibration
    is expected to retune them.
    """

    initial_days: float = 1.0
    growth: float = 1.5
    spacing_gain: float = 2.0
    lapse_factor: float = 0.3
    # A lapse ends with the client retrying until the line is played correctly,
    # which is itself a relearning pass, so a lapse never leaves the line weaker
    # than a freshly learned one (initial_days). With 0.1 a lapsed line could
    # not recover: a clean session needs all M moves, probability R**M.
    min_days: float = 1.0

    def initial(self) -> float:
        return self.initial_days

    def after_success(self, stability: float, R: float) -> float:
        return stability * (1.0 + self.growth * float(np.exp(self.spacing_gain * (1.0 - R))))

    def after_lapse(self, stability: float, R: float) -> float:
        # The floor never lifts a stability that is already below it.
        return min(stability, max(self.min_days, stability * self.lapse_factor))


@dataclass
class LineMemory:
    """Ground-truth memory of one line, hidden from the planner.

    Attributes:
        stability: Current S in days (None until the line is first seen).
        reps: Accumulated practice count driving m_practice.
        last_session_day: Simulation day of the last session on this line.
        last_review_lapsed: Whether the last Repeating Mode session had a blunder.
        sessions: Number of sessions so far (both modes).
    """

    stability: float | None = None
    reps: int = 0
    last_session_day: float | None = None
    last_review_lapsed: bool = False
    sessions: int = 0

    @property
    def seen(self) -> bool:
        return self.stability is not None

    def elapsed(self, now_day: float) -> float:
        if self.last_session_day is None:
            return 0.0
        t = now_day - self.last_session_day
        if t < 0.0:
            raise ValueError(
                f"session day {now_day} is before the last session day {self.last_session_day}"
            )
        return t
