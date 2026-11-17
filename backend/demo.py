"""Run a Learning and Repeating walkthrough against a TEMPO database."""

import argparse
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from .ml_engine import T_EASY_MS, T_SLOW_MS, T_VERY_SLOW_MS, mistake_limit
from .practice_controller import create_backend
from .store import LEARNABLE


# Simulated seconds per move that give each grade under the session grading rule
# (docs/topics/session-grading/session-grading.md): Easy is fast with no mistakes,
# Good is in the normal band, Hard is very slow with no mistakes, and Again plays at
# normal speed but makes one more first-attempt mistake than the line allows.
NORMAL_SECONDS = (T_EASY_MS + T_SLOW_MS) / 2 / 1000
RESPONSE_SECONDS = {
    "Easy": T_EASY_MS / 2 / 1000,
    "Good": NORMAL_SECONDS,
    "Hard": (T_VERY_SLOW_MS + 1000) / 1000,
    "Again": NORMAL_SECONDS,
}


def run_demo(database, weights, expected_grade, side):
    backend = create_backend(database, weights_file=weights)
    player = f"demo_{uuid4().hex[:12]}"
    with backend.store.transaction() as db:
        lines = db.execute(
            f"SELECT line_id, name, moves_uci FROM opening_lines AS o WHERE {LEARNABLE} ORDER BY line_id"
        ).fetchall()
    line = next((line for line in lines if len(line["moves_uci"].split()) >= 2), None)
    if line is None:
        raise ValueError("The demo needs an imported opening line with moves for both sides")
    moves = line["moves_uci"].split()

    # Use repeatable response times and a fixed review timestamp within this run.
    elapsed = 0.0
    now = datetime.now(timezone.utc)
    backend.timer = lambda: elapsed
    backend.now = lambda: now

    learning = backend.start_learning(player, line["line_id"], side)
    while learning["status"] == "play":
        elapsed += 0.7
        learning = backend.submit_move(
            player, learning["session_id"], learning["move_index"], learning["hint"]
        )

    # A learned line is first due on the player's next day; move the clock there.
    if backend.start_repeating(player)["status"] != "none_due":
        raise RuntimeError("The learned line was due before the next day")
    with backend.store.transaction() as db:
        first_due = db.execute(
            "SELECT next_review_at FROM player_lines WHERE player_id = ? AND line_id = ?",
            (player, line["line_id"]),
        ).fetchone()["next_review_at"]
    now = datetime.fromisoformat(first_due)

    suggestion = backend.start_repeating(player)
    if suggestion["status"] != "choose_side" or suggestion["line_id"] != line["line_id"]:
        raise RuntimeError("Repeating did not suggest the learned line")
    review = backend.choose_review_side(player, suggestion["session_id"], side)
    player_moves = len(moves[review["move_index"]::1 if side == "both" else 2])
    # Again needs more first-attempt mistakes than the line's limit, on different moves.
    wrong_moves = mistake_limit(player_moves) + 1 if expected_grade == "Again" else 0

    while review["status"] == "play":
        index = review["move_index"]
        if wrong_moves:
            wrong_moves -= 1
            elapsed += RESPONSE_SECONDS[expected_grade]
            retry = backend.submit_move(player, review["session_id"], index, "0000")
            if retry["correct"] or retry["move_index"] != index:
                raise RuntimeError("The wrong move did not trigger a retry")
        elapsed += RESPONSE_SECONDS[expected_grade]
        review = backend.submit_move(player, review["session_id"], index, moves[index])
    grade = review["fsrs_rating"]
    if grade != expected_grade:
        raise RuntimeError(f"Expected grade {expected_grade}, got {grade}")
    grading = review["grading"]

    with backend.store.transaction() as db:
        progress = db.execute(
            "SELECT next_review_at, fsrs_state FROM player_lines WHERE player_id = ? AND line_id = ?",
            (player, line["line_id"]),
        ).fetchone()
    stability = backend.ml.engine.stability_days(progress["fsrs_state"])
    if stability is None or stability <= 0 or datetime.fromisoformat(progress["next_review_at"]) <= now:
        raise RuntimeError("The review did not persist a valid stability and future due date")

    print(f"Player: {player}\nOpening: {line['name']} ({side})")
    print(f"Learning complete. Review grade: {grade}")
    print(f"Grading: {grading['mistakes']} mistakes (limit {grading['limit']}) in {grading['moves']} moves, "
          f"mean {grading['mean_ms']} ms ({grading['band'].replace('_', ' ')})")
    print(f"FSRS stability: {stability:.4f} days\nNext review (UTC): {progress['next_review_at']}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", required=True, type=Path)
    parser.add_argument("--weights", type=Path, help="One-row FSRS parameter CSV")
    parser.add_argument("--grade", choices=RESPONSE_SECONDS, default="Good")
    parser.add_argument("--side", choices=("white", "black", "both"), default="both")
    args = parser.parse_args()
    if not args.database.is_file():
        parser.error("the database file does not exist")
    run_demo(args.database, args.weights, args.grade, args.side)


if __name__ == "__main__":
    main()
