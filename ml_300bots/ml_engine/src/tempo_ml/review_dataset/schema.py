"""Review-session CSV schema (review-dataset record, section 2)."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

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
