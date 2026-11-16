"""Session grading rule from docs/topics/session-grading/session-grading.md, section 3.

The vectors are the ones in section 3.7 of that record. A move is a number (its first attempt was right and took
that many milliseconds) or None (its first attempt was wrong; a correct retry follows, which must not count).
"""
import unittest

from backend.ml_engine import MLEngine
from backend.practice_controller import checked_response_time


def review(spec):
    attempts = []
    for index, move in enumerate(spec):
        move_index = index * 2
        if move is None:
            attempts.append({"move_index": move_index, "is_correct": False, "response_time_ms": 1500})
            attempts.append({"move_index": move_index, "is_correct": True, "response_time_ms": 700})
        else:
            attempts.append({"move_index": move_index, "is_correct": True, "response_time_ms": move})
    return attempts


VECTORS = [
    (1, [5000, 900, 1100], "Easy"),
    (2, [900, 900, None], "Again"),
    (3, [900, 20000, 1000], "Hard"),
    (4, [900, 20000, 1000, 1000], "Good"),
    (5, [900, 2000, 2500, 3000, 2600], "Good"),
    (6, [900, 1000, None, 1200, 1100, 1300], "Hard"),
    (7, [900, None, None, 1000, 1000, 1000], "Again"),
    (8, [900, None] + [1000] * 8, "Good"),
    (9, [900, None] + [4000] * 8, "Hard"),
    (10, [900, None, None] + [1000] * 7, "Hard"),
    (11, [900, None, None] + [2000] * 10, "Good"),
    (12, [900, None, None, None] + [2000] * 9, "Hard"),
    (13, [900] + [9000] * 7, "Hard"),
    (14, [900, 30000] + [1000] * 6, "Good"),
]


class SessionGradingVectors(unittest.TestCase):
    def test_section_3_7_vectors(self):
        for number, spec, expected in VECTORS:
            with self.subTest(vector=number):
                self.assertEqual(MLEngine.grade_session(review(spec)), expected)

    def test_vector_3_timed_mean_is_capped(self):
        details = MLEngine.grade_details(review([900, 20000, 1000]))
        self.assertEqual(details["mean_ms"], 10500)
        self.assertEqual(details["band"], "very_slow")

    def test_vector_14_cap_gives_the_stated_mean(self):
        details = MLEngine.grade_details(review([900, 30000] + [1000] * 6))
        self.assertEqual(details["mean_ms"], 3714)
        self.assertEqual(details["band"], "slow")

    def test_first_player_move_is_never_timed(self):
        # A very slow first move must not change the band of an otherwise fast review.
        details = MLEngine.grade_details(review([9000, 1000, 1000]))
        self.assertEqual(details["mean_ms"], 1000)
        self.assertEqual(details["grade"], "Easy")

    def test_retry_time_is_ignored(self):
        attempts = review([900, None, 1000, 1000])
        attempts[1]["response_time_ms"] = 30000   # the wrong first attempt, very slow: not timed anyway
        self.assertEqual(MLEngine.grade_details(attempts)["mistakes"], 1)

    def test_no_baseline_is_subtracted(self):
        # 1400 ms is "Easy" only if nothing is subtracted from it: fast band needs a mean below 1500.
        self.assertEqual(MLEngine.grade_session(review([900, 1400, 1400])), "Easy")


class ResponseTimeCheck(unittest.TestCase):
    def test_accepts_whole_and_fractional_milliseconds(self):
        self.assertEqual(checked_response_time(0), 0)
        self.assertEqual(checked_response_time(1234.6), 1235)

    def test_rejects_negative_huge_and_non_numeric_values(self):
        for bad in (-1, 3_600_001, "900", None, True):
            with self.subTest(value=bad), self.assertRaises(ValueError):
                checked_response_time(bad)


if __name__ == "__main__":
    unittest.main()
