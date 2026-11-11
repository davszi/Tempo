"""Run a Learning and Repeating walkthrough against a TEMPO database."""

import argparse
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from .practice_controller import create_backend


RESPONSE_SECONDS = {"Again": 0.7, "Hard": 2.0, "Good": 0.7, "Easy": 0.3}


def run_demo(database, weights, expected_grade, side):
    backend = create_backend(database, weights_file=weights)
    player = f"demo_{uuid4().hex[:12]}"
    with backend.store.transaction() as db:
        lines = db.execute("SELECT line_id, name, moves_uci FROM opening_lines ORDER BY line_id").fetchall()
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

    suggestion = backend.start_repeating(player)
    if suggestion["status"] != "choose_side" or suggestion["line_id"] != line["line_id"]:
        raise RuntimeError("Repeating did not suggest the learned line")
    review = backend.choose_review_side(player, suggestion["session_id"], side)
    if expected_grade == "Again":
        elapsed += RESPONSE_SECONDS[expected_grade]
        retry = backend.submit_move(player, review["session_id"], review["move_index"], "0000")
        if retry["correct"] or retry["move_index"] != review["move_index"]:
            raise RuntimeError("The wrong move did not trigger a retry")

    while review["status"] == "play":
        elapsed += RESPONSE_SECONDS[expected_grade]
        index = review["move_index"]
        review = backend.submit_move(player, review["session_id"], index, moves[index])
    grade = review["fsrs_rating"]
    if grade != expected_grade:
        raise RuntimeError(f"Expected grade {expected_grade}, got {grade}")

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
