"""Line selection, session grading and FSRS scheduling."""

import csv
from datetime import datetime
import json
from math import isfinite


class MLEngine:
    @classmethod
    def from_weights_file(cls, path, *, baseline_ms=0):
        """Load one ordered FSRS-6 parameter vector from a training export."""
        from fsrs import Scheduler

        columns = [f"w{index}" for index in range(21)]
        with open(path, encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames != columns:
                raise ValueError("The weights file must have columns w0 through w20 in order")
            row = next(reader, None)
            if row is None or None in row or next(reader, None) is not None:
                raise ValueError("The weights file must contain one complete parameter row")
        try:
            weights = tuple(float(row[column]) for column in columns)
        except (TypeError, ValueError) as error:
            raise ValueError("Each FSRS weight must be numeric") from error
        if not all(map(isfinite, weights)):
            raise ValueError("Each FSRS weight must be finite")

        scheduler = Scheduler(parameters=weights)
        if tuple(scheduler.parameters) != weights:
            raise ValueError("FSRS adjusted the supplied weights. Check the parameter bounds")
        return cls(scheduler, baseline_ms=baseline_ms)

    def __init__(self, scheduler=None, *, baseline_ms=0):
        if not isfinite(baseline_ms) or baseline_ms < 0:
            raise ValueError("The grading baseline must be finite and nonnegative")
        if scheduler is None:
            from fsrs import Scheduler

            scheduler = Scheduler()
        self.scheduler = scheduler
        self.baseline_ms = baseline_ms

    @staticmethod
    def select_line(repertoire, now):
        due = [line for line in repertoire if datetime.fromisoformat(line["next_review_at"]) <= now]
        if not due:
            return None
        return min(due, key=lambda line: (
            line["next_review_at"], line["learned_at"], line["line_id"]
        ))["line_id"]

    @staticmethod
    def grade_session(attempts, baseline_ms):
        """Apply the review-dataset grading rule to completed move attempts."""
        if not attempts:
            raise ValueError("A review must contain at least one move")
        if any(not attempt["is_correct"] for attempt in attempts):
            return "Again"

        move_count = len({attempt["move_index"] for attempt in attempts})
        delay_ms = sum(attempt["response_time_ms"] for attempt in attempts) / move_count - baseline_ms
        if delay_ms < 500:
            return "Easy"
        if delay_ms <= 1800:
            return "Good"
        return "Hard"

    def initial_schedule(self, now):
        from fsrs import Card

        card = Card(due=now)
        return card.due, json.dumps(card.to_dict())

    @staticmethod
    def stability_days(state):
        """Return the FSRS card's current stability, if a review has initialized it."""
        from fsrs import Card

        return Card.from_dict(json.loads(state)).stability

    def schedule_review(self, state, attempts, now):
        from fsrs import Card, Rating

        grade = self.grade_session(attempts, self.baseline_ms)
        card = Card.from_dict(json.loads(state))
        card, _ = self.scheduler.review_card(card, Rating[grade], review_datetime=now)
        return grade, card.due, json.dumps(card.to_dict())
