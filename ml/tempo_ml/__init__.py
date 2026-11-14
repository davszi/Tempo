"""TEMPO ML: synthetic clients, dataset generation, FSRS-6 training and evaluation.

- ``tempo_ml.catalog``: reads the opening catalog from ``backend/tempo_demo.sqlite``.
- ``tempo_ml.simulator``: virtual players and the dataset generator
  (docs/topics/synthetic-clients/record.md, docs/topics/review-dataset/record.md).
- ``tempo_ml.fsrs``: the vectorised FSRS-6 model and its trainer.
- ``tempo_ml.evaluate``: metrics and the error in days.

Not implemented yet: the review planner and the Stage 2 human calibration
pipeline.
"""
