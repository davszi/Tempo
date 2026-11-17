"""First review timing from docs/open/first-review-timing.md.

A newly learned line is first due when the player's next day starts (DAY_STARTS_AT_HOUR local time),
Learning sets no FSRS memory, and the first Repeating review initializes it.
"""
import json
import shutil
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
from zoneinfo import ZoneInfo

from backend.ml_engine import first_review_due, player_zone
from backend.practice_controller import create_backend
from backend.store import LEARNABLE

DEMO = Path(__file__).resolve().parents[1] / "tempo_demo.sqlite"
BERLIN = ZoneInfo("Europe/Berlin")
NEW_YORK = ZoneInfo("America/New_York")


def utc(*parts):
    return datetime(*parts, tzinfo=timezone.utc)


def local(zone, *parts):
    return datetime(*parts, tzinfo=zone)


class FirstReviewDue(unittest.TestCase):
    def test_evening_lesson_is_due_at_four_next_morning(self):
        due = first_review_due(local(BERLIN, 2026, 11, 17, 21, 0), BERLIN)
        self.assertEqual(due, local(BERLIN, 2026, 11, 18, 4, 0))
        self.assertEqual(due.tzinfo, timezone.utc)

    def test_morning_lesson_is_due_next_morning(self):
        self.assertEqual(first_review_due(local(BERLIN, 2026, 11, 17, 9, 30), BERLIN),
                         local(BERLIN, 2026, 11, 18, 4, 0))

    def test_lesson_at_exactly_four_belongs_to_that_day(self):
        self.assertEqual(first_review_due(local(BERLIN, 2026, 11, 17, 4, 0), BERLIN),
                         local(BERLIN, 2026, 11, 18, 4, 0))

    def test_lesson_after_midnight_belongs_to_the_day_before(self):
        # 01:30 is still the previous day, so the next day starts at 04:00 the same morning.
        self.assertEqual(first_review_due(local(BERLIN, 2026, 11, 18, 1, 30), BERLIN),
                         local(BERLIN, 2026, 11, 18, 4, 0))

    def test_local_day_differs_from_the_utc_day(self):
        # 22:00 in New York is 03:00 UTC: by UTC days the line would be due one hour later.
        learned = local(NEW_YORK, 2026, 11, 17, 22, 0)
        self.assertEqual(first_review_due(learned, NEW_YORK), local(NEW_YORK, 2026, 11, 18, 4, 0))
        self.assertEqual(first_review_due(learned), utc(2026, 11, 18, 4, 0))

    def test_daylight_saving_change_keeps_four_local(self):
        # Europe/Berlin leaves summer time on 2026-10-25 at 03:00.
        due = first_review_due(local(BERLIN, 2026, 10, 24, 20, 0), BERLIN)
        self.assertEqual(due, utc(2026, 10, 25, 3, 0))
        self.assertEqual(due.astimezone(BERLIN).hour, 4)

    def test_missing_zone_means_utc(self):
        self.assertEqual(player_zone(None), timezone.utc)

    def test_unknown_zone_is_refused(self):
        for name in ("Mars/Olympus", "", 5):
            with self.subTest(name=name), self.assertRaises(ValueError):
                player_zone(name)


class LearningSchedulesTheFirstReview(unittest.TestCase):
    def setUp(self):
        folder = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, folder, ignore_errors=True)
        shutil.copy(DEMO, folder / "db.sqlite")
        self.backend = create_backend(folder / "db.sqlite")
        self.now = local(BERLIN, 2026, 11, 17, 21, 0).astimezone(timezone.utc)
        self.backend.now = lambda: self.now
        self.player = uuid4().hex
        with self.backend.store.transaction() as db:
            self.line = db.execute(
                f"SELECT line_id, moves_uci FROM opening_lines AS o WHERE {LEARNABLE} ORDER BY line_id LIMIT 1"
            ).fetchone()

    def learn(self, **options):
        view = self.backend.start_learning(self.player, self.line["line_id"], "white", **options)
        while view["status"] == "play":
            view = self.backend.submit_move(self.player, view["session_id"], view["move_index"], view["hint"],
                                            response_time_ms=800)
        return view

    def progress(self):
        with self.backend.store.transaction() as db:
            return db.execute(
                "SELECT next_review_at, fsrs_state FROM player_lines WHERE player_id = ? AND line_id = ?",
                (self.player, self.line["line_id"]),
            ).fetchone()

    def test_learned_line_is_due_on_the_players_next_day_with_no_memory(self):
        self.learn(time_zone="Europe/Berlin")
        row = self.progress()
        self.assertEqual(datetime.fromisoformat(row["next_review_at"]), local(BERLIN, 2026, 11, 18, 4, 0))
        self.assertIsNone(json.loads(row["fsrs_state"])["stability"])

    def test_without_a_zone_the_next_utc_day_is_used(self):
        self.learn()
        self.assertEqual(datetime.fromisoformat(self.progress()["next_review_at"]), utc(2026, 11, 18, 4, 0))

    def test_unknown_zone_is_refused_before_the_lesson_opens(self):
        with self.assertRaises(ValueError):
            self.backend.start_learning(self.player, self.line["line_id"], "white", time_zone="Nowhere/Here")

    def test_nothing_is_due_the_same_day_and_the_first_review_sets_memory(self):
        self.learn(time_zone="Europe/Berlin")
        self.assertEqual(self.backend.start_repeating(self.player)["status"], "none_due")

        self.now = local(BERLIN, 2026, 11, 18, 4, 0).astimezone(timezone.utc)
        review = self.backend.start_repeating(self.player)
        self.assertEqual(review["line_id"], self.line["line_id"])
        review = self.backend.choose_review_side(self.player, review["session_id"], "white")
        moves = self.line["moves_uci"].split()
        while review["status"] == "play":
            review = self.backend.submit_move(self.player, review["session_id"], review["move_index"],
                                              moves[review["move_index"]], response_time_ms=2000)
        self.assertIsNotNone(json.loads(self.progress()["fsrs_state"])["stability"])

    def test_a_chosen_line_cannot_be_reviewed_before_its_first_review_opens(self):
        self.learn(time_zone="Europe/Berlin")
        with self.assertRaises(ValueError):
            self.backend.start_review_line(self.player, self.line["line_id"])
        self.now = local(BERLIN, 2026, 11, 18, 4, 0).astimezone(timezone.utc)
        self.assertEqual(self.backend.start_review_line(self.player, self.line["line_id"])["mode"], "repeating")

    def test_practice_after_learning_leaves_the_schedule_alone(self):
        self.learn(time_zone="Europe/Berlin")
        before = self.progress()
        self.now = local(BERLIN, 2026, 11, 17, 22, 0).astimezone(timezone.utc)
        self.learn(time_zone="Europe/Berlin")      # "Practise without hints" is another Learning session
        self.assertEqual(tuple(self.progress()), tuple(before))


if __name__ == "__main__":
    unittest.main()
