"""Session grade (Again / Hard / Good / Easy) and the session record it is
written in (review-dataset record, sections 2 and 3).

Maps one session's blunder count and latency onto the FSRS 4-point scale.
Latency is normalised by the number of repertoire moves ``M`` so lines of
different depth are graded on the same footing.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

AGAIN = 1
HARD = 2
GOOD = 3
EASY = 4

# Thresholds on the average cognitive delay per move, in milliseconds
# (review-dataset record, section 3.2).
EASY_MAX_DELAY_MS = 500.0
GOOD_MAX_DELAY_MS = 1800.0


def calculate_session_grade(
    blunder_count: int,
    total_time_ms: float,
    num_moves: int,
    baseline_ms: float,
) -> int:
    """Return the FSRS grade (1-4) for one session.

    Args:
        blunder_count: Number of moves whose first attempt was wrong.
        total_time_ms: Wall-clock time summed over all repertoire moves.
        num_moves: Number of repertoire moves ``M`` in the line (> 0).
        baseline_ms: The player's physical motor/board-scan latency floor.

    Any blunder gives Again. Otherwise the average cognitive delay
    ``total_time_ms / M - baseline_ms`` decides Easy (< 500 ms),
    Good (500-1800 ms) or Hard (> 1800 ms).
    """
    if num_moves <= 0:
        raise ValueError(f"num_moves must be positive, got {num_moves}")
    if blunder_count < 0:
        raise ValueError(f"blunder_count must be >= 0, got {blunder_count}")

    if blunder_count > 0:
        return AGAIN

    cognitive_delay = total_time_ms / num_moves - baseline_ms
    if cognitive_delay < EASY_MAX_DELAY_MS:
        return EASY
    if cognitive_delay <= GOOD_MAX_DELAY_MS:
        return GOOD
    return HARD


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
