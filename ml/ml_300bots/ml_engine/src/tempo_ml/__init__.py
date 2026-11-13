"""TEMPO ML engine.

Implemented so far:

- ``tempo_ml.synthetic_clients``: simulated players that produce review-session
  telemetry (docs/topics/synthetic-clients/record.md).
- ``tempo_ml.review_dataset``: the session CSV schema and the FSRS session
  grading function (docs/topics/review-dataset/record.md).

Not implemented yet: FSRS fitting, the review planner, training loops, and the
Stage 2 human calibration pipeline.
"""
