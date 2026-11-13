"""Generate offline review telemetry from synthetic TEMPO clients."""

import argparse
from collections import Counter
from contextlib import closing
import csv
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from math import exp
from pathlib import Path
from random import Random
from sqlite3 import connect
from tempfile import NamedTemporaryFile

from .ml_engine import MLEngine


CSV_FIELDS = (
    "agent_name", "opening_name", "review_status", "t_days",
    "grade", "total_time_ms", "accuracy",
)
GRADE_NUMBER = {"Again": 1, "Hard": 2, "Good": 3, "Easy": 4}
START = datetime(2026, 1, 1, tzinfo=timezone.utc)
DEMO_LINES = (
    ("Sicilian Defence", "e2e4 c7c5 g1f3 d7d6"),
    ("Italian Game", "e2e4 e7e5 g1f3 b8c6 f1c4"),
)


@dataclass(frozen=True)
class Profile:
    name: str
    baseline_ms: int
    mu: float
    sigma: float
    beta: float
    alpha: float
    decay: float

    def retrievability(self, days, stability):
        scale = 0.9 ** (-1 / self.decay) - 1
        return (1 + scale * days / stability) ** (-self.decay)

    def latency(self, rng, recall, familiarity):
        hesitation = rng.lognormvariate(self.mu, self.sigma) * 1000
        strain = exp(self.beta * (1 - recall))
        return round(self.baseline_ms + hesitation * strain / (1 + self.alpha * familiarity))


PROFILES = (
    Profile("fast", 220, -0.6, 0.45, 0.4, 0.35, 0.65),
    Profile("balanced", 300, -0.2, 0.40, 1.0, 0.25, 0.50),
    Profile("diligent", 380, 0.3, 0.35, 2.2, 0.20, 0.35),
)


def simulate_line(profile, agent_name, opening, move_count, sessions, rng, scheduler):
    engine = MLEngine(scheduler, baseline_ms=profile.baseline_ms)
    _, state = engine.initial_schedule(START)
    previous = START
    now = START
    familiarity = 0
    status = "new"

    for _ in range(sessions):
        days = (now - previous).total_seconds() / 86400
        recall = 1.0 if status == "new" else profile.retrievability(days, engine.stability_days(state))
        attempts = []
        first_correct = 0
        for index in range(move_count):
            correct = rng.random() < recall
            first_correct += correct
            attempts.append(dict(
                move_index=index, is_correct=correct,
                response_time_ms=profile.latency(rng, recall, familiarity),
            ))
            if not correct:
                # Model a successful retry after the failed first recall.
                attempts.append(dict(
                    move_index=index, is_correct=True,
                    response_time_ms=profile.latency(rng, 1.0, familiarity),
                ))

        grade, due, state = engine.schedule_review(state, attempts, now)
        yield dict(
            agent_name=agent_name,
            opening_name=opening,
            review_status=status,
            t_days=days,
            grade=GRADE_NUMBER[grade],
            total_time_ms=sum(attempt["response_time_ms"] for attempt in attempts),
            accuracy=first_correct / move_count,
        )
        lapse = grade == "Again"
        familiarity = max(0, familiarity - 2) if lapse else familiarity + 1
        status = "relearning" if lapse else "review"
        previous = now
        # Vary attendance around the due time so the dataset includes early and late recall.
        delay = max((due - now) * rng.uniform(0.5, 2.0), timedelta(seconds=1))
        now += delay


def generate_dataset(lines, *, clients_per_profile, sessions, seed):
    from fsrs import Scheduler

    rng = Random(seed)
    scheduler = Scheduler(enable_fuzzing=False)
    for profile in PROFILES:
        for number in range(1, clients_per_profile + 1):
            agent = f"synth_{profile.name}_{number:02d}"
            for name, moves in lines:
                yield from simulate_line(
                    profile, agent, name, len(moves.split()), sessions, rng, scheduler
                )


def read_lines(database, *, one_line_per_family=False):
    # Open the live database read-only. Synthetic events go exclusively to the CSV.
    uri = database.resolve().as_uri() + "?mode=ro"
    with closing(connect(uri, uri=True)) as db:
        lines = db.execute(
            """SELECT o.line_id, o.name, o.moves_uci, f.name
               FROM opening_lines AS o
               JOIN opening_families AS f USING (family_id)
               ORDER BY o.line_id"""
        ).fetchall()
    names = Counter(name for _, name, _, _ in lines)
    if one_line_per_family:
        representatives = {}
        for line in lines:
            representatives.setdefault(line[3], line)
        lines = representatives.values()
    return [
        (f"{name} [line {line_id}]" if names[name] > 1 else name, moves)
        for line_id, name, moves, _ in lines
    ]


def write_dataset(output, rows):
    count = 0
    temporary = None
    try:
        with NamedTemporaryFile(
            mode="w", newline="", encoding="utf-8", dir=output.parent, delete=False
        ) as handle:
            temporary = Path(handle.name)
            writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
            writer.writeheader()
            for row in rows:
                writer.writerow(row)
                count += 1
        temporary.replace(output)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return count


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--database", type=Path, help="Read opening lines from this SQLite database")
    parser.add_argument("--one-line-per-family", action="store_true",
                        help="Use the first catalog line in each opening family")
    parser.add_argument("--clients-per-profile", type=int, default=1)
    parser.add_argument("--sessions", type=int, default=12, help="Sessions per client and line")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    if args.clients_per_profile < 1 or args.sessions < 1:
        parser.error("client and session counts must be positive")
    if args.database and args.database.resolve() == args.output.resolve():
        parser.error("the CSV output must differ from the SQLite database")
    if args.one_line_per_family and not args.database:
        parser.error("--one-line-per-family requires --database")
    lines = read_lines(args.database, one_line_per_family=args.one_line_per_family) if args.database else DEMO_LINES
    if not lines or any(not moves.split() for _, moves in lines):
        parser.error("opening lines must contain at least one move")
    rows = generate_dataset(
        lines, clients_per_profile=args.clients_per_profile, sessions=args.sessions, seed=args.seed
    )
    print(f"Wrote {write_dataset(args.output, rows)} sessions to {args.output}")


if __name__ == "__main__":
    main()
