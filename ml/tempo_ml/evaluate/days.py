"""Error in days: predicted minus true days until the chance of a clean
session drops to 90 % (negative = the review would come too early).

Definition: docs/topics/fsrs-training/retraining-plan.md (days metric).
"""

from __future__ import annotations

import numpy as np

TARGET_RETENTION = 0.9


def true_days(stability, num_moves, C, retention: float = TARGET_RETENTION):
    """Days until the true chance of a clean session drops to ``retention``.

    The hidden memory is per move, R(t) = (1 + F t / S) ** -C with
    F = 0.9 ** (-1 / C) - 1, and a clean session needs all M moves, so the
    chance is R(t) ** M. Solving R(t) ** M = retention gives
    t = S / F * ((retention ** (1 / M)) ** (-1 / C) - 1). For M = 1 and
    retention 0.9 this is S.
    """
    stability, num_moves, C = (np.asarray(x, dtype=float) for x in (stability, num_moves, C))
    F = 0.9 ** (-1.0 / C) - 1.0
    r_move = retention ** (1.0 / num_moves)
    return stability / F * (r_move ** (-1.0 / C) - 1.0)


def days_metrics(d_pred: np.ndarray, d_true: np.ndarray, after_learning: np.ndarray,
                 horizon_days: float) -> dict:
    """Error in days, predicted minus true days to 90 % (negative = review too early)."""
    e = d_pred - d_true

    def block(sel: np.ndarray) -> dict:
        if not sel.any():
            return {"sessions": 0}
        return {"sessions": int(sel.sum()),
                "median_error": float(np.median(e[sel])),
                "median_abs_error": float(np.median(np.abs(e[sel]))),
                "median_rel_error": float(np.median(e[sel] / d_true[sel]))}

    out = block(np.ones_like(e, bool))
    out.update({
        "share_too_early": float(np.mean(e < 0)),
        "mean_error": float(e.mean()),
        "n_beyond_horizon": int((d_true > horizon_days).sum()),
        "median_true_days": float(np.median(d_true)),
        "median_pred_days": float(np.median(d_pred)),
        "bands": {"lt7": block(d_true < 7), "7to30": block((d_true >= 7) & (d_true < 30)),
                  "ge30": block(d_true >= 30)},
        "session_type": {"after_learning": block(after_learning), "after_review": block(~after_learning)},
    })
    return out
