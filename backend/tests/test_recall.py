"""Current recall shown in the repertoire: the FSRS-6 forgetting curve with fractional elapsed days."""
import json
import unittest
from datetime import datetime, timedelta, timezone

from fsrs import Card, Rating

from backend.ml_engine import MLEngine

REVIEWED = datetime(2026, 11, 17, 9, 0, tzinfo=timezone.utc)


class CurrentRecall(unittest.TestCase):
    def setUp(self):
        self.engine = MLEngine()
        card, _ = self.engine.scheduler.review_card(Card(due=REVIEWED), Rating.Good, review_datetime=REVIEWED)
        self.state = json.dumps(card.to_dict())
        self.stability = card.stability

    def recall(self, after):
        return self.engine.memory(self.state, REVIEWED + after)[1]

    def test_recall_falls_within_the_first_day(self):
        # py-fsrs counts whole days and would report exactly 1.0 here.
        twelve_hours = self.recall(timedelta(hours=12))
        self.assertLess(twelve_hours, 1.0)
        self.assertLess(self.recall(timedelta(hours=23)), twelve_hours)

    def test_recall_is_full_right_after_the_review(self):
        self.assertAlmostEqual(self.recall(timedelta(0)), 1.0)

    def test_recall_reaches_the_target_after_stability_days(self):
        self.assertAlmostEqual(self.recall(timedelta(days=self.stability)), 0.9, places=9)

    def test_whole_days_agree_with_py_fsrs(self):
        card = Card.from_dict(json.loads(self.state))
        for days in (1, 3, 10):
            with self.subTest(days=days):
                now = REVIEWED + timedelta(days=days)
                self.assertAlmostEqual(self.engine.memory(self.state, now)[1],
                                       self.engine.scheduler.get_card_retrievability(card, current_datetime=now))

    def test_untested_card_has_no_recall(self):
        _, state = self.engine.initial_schedule(REVIEWED)
        self.assertEqual(self.engine.memory(state, REVIEWED + timedelta(days=1)), (None, None))


if __name__ == "__main__":
    unittest.main()
