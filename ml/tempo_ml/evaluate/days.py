"""Error in days: predicted minus true days until the chance of passing the
line drops to 90 % (negative = the review would come too early).

Definition: docs/topics/move-recall/move-recall.md, section 3.5. A pass is a
review with at most L(M) mistakes; with per-move recall R it has chance
``p_pass(R, M)``, which falls to 0.9 when R falls to ``per_move_target(M)``.
"""

from __future__ import annotations

from functools import lru_cache

import numpy as np

from ..pass_chance import TARGET_PASS, per_move_target


@lru_cache(maxsize=None)
def _target(m: int) -> float:
    return per_move_target(m, TARGET_PASS)


def per_move_targets(num_moves) -> np.ndarray:
    """R*(M) for an array of line lengths."""
    m = np.asarray(num_moves, dtype=int)
    table = {int(x): _target(int(x)) for x in np.unique(m)}
    return np.vectorize(table.get, otypes=[float])(m)


def days_to_pass_target(stability, decay, num_moves):
    """Days after a review until the pass chance falls to 0.9.

    Per-move recall follows R(t) = (1 + F t / S) ** -C with F = 0.9 ** (-1/C) - 1,
    so it reaches R*(M) at t = S / F * (R*(M) ** (-1/C) - 1). For one move this is S.
    Used for the hidden truth (the client's S and C) and for per-move arms
    (fitted S and decay w20).
    """
    stability, decay = (np.asarray(x, dtype=float) for x in (stability, decay))
    F = 0.9 ** (-1.0 / decay) - 1.0
    return stability / F * (per_move_targets(num_moves) ** (-1.0 / decay) - 1.0)


def true_days(stability, num_moves, C):
    """True days until the hidden pass chance drops to 0.9."""
    return days_to_pass_target(stability, C, num_moves)


def days_metrics(d_pred: np.ndarray, d_true: np.ndarray, after_learning: np.ndarray,
                 horizon_days: float) -> dict:
    """Error in days, predicted minus true days to a 90 % pass chance (negative = review too early)."""
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
