"""Hidden memory state of one line for one synthetic client.

Specified (synthetic-clients record, sections 3.2 and 3.5):
- per-move retrievability R(t, S) = (1 + F * t / S) ** (-C), F = 0.9^(-1/C) - 1
- reps update: +1 after a passed review, max(0, reps - 2) after a lapse (Again)

Stability and difficulty evolve through the FSRS-6 memory (``memory/fsrs.py``).
"""

from __future__ import annotations

from dataclasses import dataclass

BLUNDER_REPS_PENALTY = 2


def retrievability(t_days: float, stability: float, C: float) -> float:
    """Power-law forgetting curve R(t, S) with F = 0.9^(-1/C) - 1."""
    if t_days < 0.0:
        raise ValueError(f"t_days must be >= 0, got {t_days}")
    if stability <= 0.0:
        raise ValueError(f"stability must be > 0, got {stability}")
    F = 0.9 ** (-1.0 / C) - 1.0
    return float((1.0 + F * t_days / stability) ** (-C))


def next_reps(reps: int, lapsed: bool) -> int:
    """Practice accumulation with the soft 2-step lapse penalty."""
    if lapsed:
        return max(0, reps - BLUNDER_REPS_PENALTY)
    return reps + 1


@dataclass
class LineMemory:
    """Ground-truth memory of one line, hidden from the planner.

    Attributes:
        stability: Current S in days (None until the line is first seen).
        difficulty: Current FSRS-6 difficulty D (None until the line is first seen).
        reps: Accumulated practice count driving m_practice.
        last_session_day: Simulation day of the last session on this line.
        last_review_lapsed: Whether the last Repeating Mode session was graded Again.
        sessions: Number of sessions so far (both modes).
    """

    stability: float | None = None
    difficulty: float | None = None
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
