"""Session grading function (review-dataset record, section 3).

Maps one session's blunder count and latency onto the FSRS 4-point scale.
Latency is normalised by the number of repertoire moves ``M`` so lines of
different depth are graded on the same footing.
"""

from __future__ import annotations

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
