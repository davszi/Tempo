"""Hidden memory models of the synthetic clients.

``multiplicative``: per-line stability multiplied after a clean session and
cut after a lapse; per-move recall follows the forgetting curve
(docs/topics/synthetic-clients/record.md). The default.

``fsrs``: FSRS-6 itself with per-client weights; stability and difficulty
follow the graded FSRS-6 update. Selected with ``"memory": "fsrs"``.
"""
