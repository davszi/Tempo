"""Hidden memory of the synthetic clients.

``state``: per-line memory state, the per-move forgetting curve and practice reps.
``fsrs``: FSRS-6 with per-client weights; stability and difficulty follow the
graded FSRS-6 update. The only memory model (move-recall record, section 3.1).
"""
