"""Line selection, session grading and FSRS scheduling."""

import csv
from datetime import datetime, time, timedelta, timezone
import json
from math import isfinite
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


# Session grading rule, from docs/topics/session-grading/session-grading.md (section 3).
CAP_MS = 20000
T_EASY_MS = 1500
T_SLOW_MS = 3500
T_VERY_SLOW_MS = 8000


# First review timing, from docs/open/first-review-timing.md: a learned line is first
# due when the player's next day starts, at this local hour (as in Anki's day rollover).
DAY_STARTS_AT_HOUR = 4


def player_zone(name):
    """The player's IANA time zone, or UTC when the browser sent none."""
    if name is None:
        return timezone.utc
    if not isinstance(name, str) or not name:
        raise ValueError("time_zone must be an IANA time zone name")
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError) as error:
        raise ValueError(f"Unknown time zone: {name}") from error


def first_review_due(learned_at, zone=timezone.utc):
    """Start of the player's next day after learning: DAY_STARTS_AT_HOUR local time, returned in UTC.

    A day runs from DAY_STARTS_AT_HOUR to DAY_STARTS_AT_HOUR, so a line learned at 01:00 belongs
    to the day before and is due at 04:00 that morning.
    """
    local = learned_at.astimezone(zone)
    learning_day = (local - timedelta(hours=DAY_STARTS_AT_HOUR)).date()
    due = datetime.combine(learning_day + timedelta(days=1), time(DAY_STARTS_AT_HOUR), tzinfo=zone)
    return due.astimezone(timezone.utc)


def mistake_limit(moves):
    """Most first-attempt mistakes a review of a line with this many player moves may have and stay non-Again."""
    if moves <= 3:
        return 0
    if moves <= 7:
        return 1
    if moves <= 12:
        return 2
    return 3


def time_band(mean_ms):
    """Fast, normal, slow or very_slow, from the mean of the capped times of the timed moves."""
    if mean_ms is None or T_EASY_MS <= mean_ms <= T_SLOW_MS:
        return "normal"
    if mean_ms < T_EASY_MS:
        return "fast"
    if mean_ms <= T_VERY_SLOW_MS:
        return "slow"
    return "very_slow"


class MLEngine:
    @classmethod
    def from_weights_file(cls, path):
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

        scheduler = Scheduler(parameters=weights, learning_steps=(), relearning_steps=())
        if tuple(scheduler.parameters) != weights:
            raise ValueError("FSRS adjusted the supplied weights. Check the parameter bounds")
        return cls(scheduler)

    def __init__(self, scheduler=None):
        if scheduler is None:
            from fsrs import Scheduler

            scheduler = Scheduler(learning_steps=(), relearning_steps=())
        self.scheduler = scheduler

    @staticmethod
    def select_line(repertoire, now):
        due = [line for line in repertoire if datetime.fromisoformat(line["next_review_at"]) <= now]
        if not due:
            return None
        return min(due, key=lambda line: (
            line["next_review_at"], line["learned_at"], line["line_id"]
        ))["line_id"]

    @staticmethod
    def grade_details(attempts):
        """Grade one review and explain it. `attempts` are the move attempts in the order they were made.

        Only each move's first attempt counts. A timed move is a correct first attempt that is not the
        line's first player move; its time is capped at CAP_MS.
        """
        if not attempts:
            raise ValueError("A review must contain at least one move")
        by_move = {}
        for attempt in attempts:
            by_move.setdefault(attempt["move_index"], []).append(attempt)
        moves = sorted(by_move)
        first = {index: by_move[index][0] for index in moves}
        player_moves = len(moves)
        mistakes = sum(1 for index in moves if not first[index]["is_correct"])
        timed = [
            min(first[index]["response_time_ms"], CAP_MS)
            for index in moves[1:]
            if first[index]["is_correct"]
        ]
        mean_ms = sum(timed) / len(timed) if timed else None
        band = time_band(mean_ms)
        limit = mistake_limit(player_moves)

        if mistakes > limit:
            grade = "Again"
        elif mistakes == limit and mistakes > 0:
            grade = "Hard"
        elif mistakes == 0:
            grade = {"fast": "Easy", "very_slow": "Hard"}.get(band, "Good")
        else:
            grade = "Good" if band in ("fast", "normal") else "Hard"
        return {
            "grade": grade,
            "moves": player_moves,
            "mistakes": mistakes,
            "limit": limit,
            "mean_ms": None if mean_ms is None else round(mean_ms),
            "band": band,
        }

    @classmethod
    def grade_session(cls, attempts):
        return cls.grade_details(attempts)["grade"]

    def initial_schedule(self, now, zone=timezone.utc):
        """An empty FSRS card for a newly learned line, first due on the player's next day.

        Learning sets no memory: the first Repeating review initializes stability and difficulty.
        """
        from fsrs import Card

        card = Card(due=first_review_due(now, zone))
        return card.due, json.dumps(card.to_dict())

    @property
    def target_recall(self):
        """The recall probability reviews are scheduled at (the scheduler's desired retention)."""
        return self.scheduler.desired_retention

    def memory(self, state, now):
        """Return (stability in days, chance of recall now), or (None, None) before the first review."""
        from fsrs import Card

        card = Card.from_dict(json.loads(state))
        if card.stability is None:
            return None, None
        return card.stability, self.scheduler.get_card_retrievability(card, current_datetime=now)

    @staticmethod
    def stability_days(state):
        """Return the FSRS card's current stability, if a review has initialized it."""
        from fsrs import Card

        return Card.from_dict(json.loads(state)).stability

    def schedule_review(self, state, attempts, now, grade=None):
        from fsrs import Card, Rating

        grade = grade or self.grade_session(attempts)
        card = Card.from_dict(json.loads(state))
        card, _ = self.scheduler.review_card(card, Rating[grade], review_datetime=now)
        return grade, card.due, json.dumps(card.to_dict())
