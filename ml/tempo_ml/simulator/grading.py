"""Session grade (Again / Hard / Good / Easy) and the session record it is
written in (review-dataset record, sections 2 and 3).

Maps one session's first-attempt mistakes and move times onto the FSRS 4-point scale.
Latency is normalised by the number of repertoire moves ``M`` so lines of
different depth are graded on the same footing.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

AGAIN = 1
HARD = 2
GOOD = 3
EASY = 4

# Session grading rule: docs/topics/session-grading/session-grading.md, section 3.
CAP_MS = 20000.0          # section 3.3: each timed move is capped at this time
T_EASY_MS = 1500.0        # section 3.4: fast below this mean
T_SLOW_MS = 3500.0        # section 3.4: slow above this mean
T_VERY_SLOW_MS = 8000.0   # section 3.4: very slow above this mean


def mistake_limit(num_moves: int) -> int:
    """Most first-attempt mistakes a review of this many player moves may have and stay non-Again (section 3.2)."""
    if num_moves <= 3:
        return 0
    if num_moves <= 7:
        return 1
    if num_moves <= 12:
        return 2
    return 3


def time_band(mean_ms: float | None) -> str:
    """Fast, normal, slow or very_slow from the mean of the capped timed moves (section 3.4).

    With no timed moves the band is normal (section 3.3, step 5).
    """
    if mean_ms is None or T_EASY_MS <= mean_ms <= T_SLOW_MS:
        return "normal"
    if mean_ms < T_EASY_MS:
        return "fast"
    if mean_ms <= T_VERY_SLOW_MS:
        return "slow"
    return "very_slow"


def calculate_session_grade(first_correct: Sequence[bool], first_times_ms: Sequence[float]) -> int:
    """Return the FSRS grade (1-4) for one finished review (section 3.5).

    Args:
        first_correct: For each of the line's ``M`` player moves, whether its first attempt was right.
        first_times_ms: For each move, the time of its first attempt in milliseconds (browser-measured
            in the app; the simulated physical move time, including the baseline, here).

    The first player move is never timed. Mistakes are the moves whose first attempt was wrong.
    """
    num_moves = len(first_correct)
    if num_moves <= 0:
        raise ValueError(f"a review must contain at least one move, got {num_moves}")
    if len(first_times_ms) != num_moves:
        raise ValueError("first_correct and first_times_ms must have one entry per move")

    mistakes = sum(1 for correct in first_correct if not correct)
    timed = [min(time, CAP_MS) for correct, time in zip(first_correct[1:], first_times_ms[1:]) if correct]
    mean_ms = sum(timed) / len(timed) if timed else None
    band = time_band(mean_ms)
    limit = mistake_limit(num_moves)

    if mistakes > limit:
        return AGAIN
    if mistakes == limit and mistakes > 0:
        return HARD
    if mistakes == 0:
        if band == "fast":
            return EASY
        return HARD if band == "very_slow" else GOOD
    return GOOD if band in ("fast", "normal") else HARD


# ---- review-session CSV schema (review-dataset record, section 2)

CSV_COLUMNS: tuple[str, ...] = (
    "agent_name",
    "opening_name",
    "review_status",
    "t_days",
    "grade",
    "total_time_ms",
    "accuracy",
)

REVIEW_STATUSES: frozenset[str] = frozenset({"new", "learning", "review", "relearning"})


@dataclass(frozen=True)
class SessionRecord:
    """One row of the review-session dataset."""

    agent_name: str
    opening_name: str
    review_status: str
    t_days: float
    grade: int
    total_time_ms: int
    accuracy: float

    def __post_init__(self) -> None:
        if self.review_status not in REVIEW_STATUSES:
            raise ValueError(f"unknown review_status {self.review_status!r}")
        if self.t_days < 0.0:
            raise ValueError(f"t_days must be >= 0, got {self.t_days}")
        if self.grade not in (1, 2, 3, 4):
            raise ValueError(f"grade must be 1-4, got {self.grade}")
        if self.total_time_ms < 0:
            raise ValueError(f"total_time_ms must be >= 0, got {self.total_time_ms}")
        if not 0.0 <= self.accuracy <= 1.0:
            raise ValueError(f"accuracy must be in [0, 1], got {self.accuracy}")

    def to_row(self) -> dict[str, object]:
        return {name: getattr(self, name) for name in CSV_COLUMNS}


def write_sessions_csv(records: Iterable[SessionRecord], path: str | Path) -> int:
    """Write records to ``path`` with the schema header. Returns rows written."""
    count = 0
    with Path(path).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        for record in records:
            writer.writerow(record.to_row())
            count += 1
    return count
