"""FSRS-6 memory model, vectorised over many cards with numpy.

A *card* is one (player, line) pair. The formulas, default parameters and
bounds are those of py-fsrs 6.3.2 (``fsrs.scheduler``); ``tests/test_trainers.py``
checks every step function against that package. Like the FSRS optimizers,
this uses the long-term model without learning-step states: the first review
sets stability and difficulty from its grade, a review less than one day after
the previous one uses the short-term stability update, every other review uses
the recall or forget update.

Predicted retrievability before review k:  R = (1 + FACTOR * t / S) ** DECAY,
DECAY = -w[20], FACTOR = 0.9 ** (1 / DECAY) - 1.

Input layout (``Cards``, ``load_cards``): a review-session CSV turned into
padded per-card arrays.

Only the review-dataset schema columns are used, so the same code works on
human data. A card is (agent_name, opening_name); rows must be chronological
per card (generator output is). Same-day reviews (t_days < 1) still update the
card but are excluded from the loss, as in the FSRS optimizers; so are
Learning Mode sessions (``new``/``learning``), which test nothing because the
arrow shows the move.

Label: success = grade > 1, i.e. the whole line was played without a blunder.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

DEFAULT_PARAMETERS = np.array([
    0.212, 1.2931, 2.3065, 8.2956, 6.4133, 0.8334, 3.0194, 0.001, 1.8722, 0.1666,
    0.796, 1.4835, 0.0614, 0.2629, 1.6483, 0.6014, 1.8729, 0.5425, 0.0912, 0.0658,
    0.1542,
])
STABILITY_MIN = 0.001
LOWER_BOUNDS = np.array([
    STABILITY_MIN, STABILITY_MIN, STABILITY_MIN, STABILITY_MIN, 1.0, 0.001, 0.001, 0.001,
    0.0, 0.0, 0.001, 0.001, 0.001, 0.001, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.1,
])
UPPER_BOUNDS = np.array([
    100.0, 100.0, 100.0, 100.0, 10.0, 4.0, 4.0, 0.75, 4.5, 0.8, 3.5, 5.0, 0.25, 0.9,
    4.0, 1.0, 6.0, 2.0, 2.0, 0.8, 0.8,
])
MIN_DIFFICULTY, MAX_DIFFICULTY = 1.0, 10.0


def forgetting_curve(w: np.ndarray, t: np.ndarray, s: np.ndarray) -> np.ndarray:
    decay = -w[20]
    factor = 0.9 ** (1.0 / decay) - 1.0
    return (1.0 + factor * t / s) ** decay


def initial_stability(w: np.ndarray, g: np.ndarray) -> np.ndarray:
    return np.maximum(w[g - 1], STABILITY_MIN)


def initial_difficulty(w: np.ndarray, g: np.ndarray, clamp: bool = True) -> np.ndarray:
    d = w[4] - np.exp(w[5] * (g - 1)) + 1.0
    return np.clip(d, MIN_DIFFICULTY, MAX_DIFFICULTY) if clamp else d


def next_difficulty(w: np.ndarray, d: np.ndarray, g: np.ndarray) -> np.ndarray:
    arg1 = initial_difficulty(w, np.full_like(g, 4), clamp=False)
    delta = -(w[6] * (g - 3))
    arg2 = d + (10.0 - d) * delta / 9.0
    return np.clip(w[7] * arg1 + (1.0 - w[7]) * arg2, MIN_DIFFICULTY, MAX_DIFFICULTY)


def short_term_stability(w: np.ndarray, s: np.ndarray, g: np.ndarray) -> np.ndarray:
    inc = np.exp(w[17] * (g - 3 + w[18])) * s ** (-w[19])
    inc = np.where(g >= 2, np.maximum(inc, 1.0), inc)
    return np.maximum(s * inc, STABILITY_MIN)


def recall_stability(w, d, s, r, g):
    hard = np.where(g == 2, w[15], 1.0)
    easy = np.where(g == 4, w[16], 1.0)
    return s * (1.0 + np.exp(w[8]) * (11.0 - d) * s ** (-w[9]) * (np.exp((1.0 - r) * w[10]) - 1.0) * hard * easy)


def forget_stability(w, d, s, r):
    long_term = w[11] * d ** (-w[12]) * ((s + 1.0) ** w[13] - 1.0) * np.exp((1.0 - r) * w[14])
    short_term = s / np.exp(w[17] * w[18])
    return np.minimum(long_term, short_term)


def next_stability(w, d, s, r, g):
    out = np.where(g == 1, forget_stability(w, d, s, r), recall_stability(w, d, s, r, g))
    return np.maximum(out, STABILITY_MIN)


def predict_states(w: np.ndarray, t: np.ndarray, g: np.ndarray, valid: np.ndarray):
    """Like :func:`predict`, and also the stability after every review.

    Returns:
        (r, s_after): both (cards, steps). ``r`` is :func:`predict`'s output;
        ``s_after[:, k]`` is the stability in days once review k is applied
        (step 0 included), NaN at invalid positions. FSRS-6 predicts 90%
        recall exactly ``s_after`` days after the review.
    """
    w = np.asarray(w, dtype=float)
    g = np.where(valid, g, 3).astype(int)
    n, steps = t.shape
    out = np.full((n, steps), np.nan)
    s_after = np.full((n, steps), np.nan)
    s = initial_stability(w, g[:, 0])
    d = initial_difficulty(w, g[:, 0])
    s_after[:, 0] = np.where(valid[:, 0], s, np.nan)
    for k in range(1, steps):
        v = valid[:, k]
        if not v.any():
            break
        tk, gk = t[:, k], g[:, k]
        r = forgetting_curve(w, tk, s)
        out[:, k] = np.where(v, r, np.nan)
        s_new = np.where(tk < 1.0, short_term_stability(w, s, gk), next_stability(w, d, s, r, gk))
        d_new = next_difficulty(w, d, gk)
        s = np.where(v, s_new, s)
        d = np.where(v, d_new, d)
        s_after[:, k] = np.where(v, s, np.nan)
    return out, s_after


def predict(w: np.ndarray, t: np.ndarray, g: np.ndarray, valid: np.ndarray) -> np.ndarray:
    """Predicted retrievability before every review.

    Args:
        w: 21 FSRS-6 parameters.
        t: (cards, steps) days since the previous review of the same card
           (step 0 is the first review; its t is ignored).
        g: (cards, steps) grades 1-4 (anything at invalid positions).
        valid: (cards, steps) bool, True where a review exists.

    Returns:
        (cards, steps) predicted R; NaN at step 0 and invalid positions.
    """
    w = np.asarray(w, dtype=float)
    g = np.where(valid, g, 3).astype(int)
    n, steps = t.shape
    out = np.full((n, steps), np.nan)
    s = initial_stability(w, g[:, 0])
    d = initial_difficulty(w, g[:, 0])
    for k in range(1, steps):
        v = valid[:, k]
        if not v.any():
            break
        tk, gk = t[:, k], g[:, k]
        r = forgetting_curve(w, tk, s)
        out[:, k] = np.where(v, r, np.nan)
        s_new = np.where(tk < 1.0, short_term_stability(w, s, gk), next_stability(w, d, s, r, gk))
        d_new = next_difficulty(w, d, gk)
        s = np.where(v, s_new, s)
        d = np.where(v, d_new, d)
    return out


# ---- input layout

TEST_STATUSES = ("review", "relearning")


@dataclass
class Cards:
    agent: np.ndarray        # (n,) agent name per card
    t: np.ndarray            # (n, steps) days since previous review
    g: np.ndarray            # (n, steps) grade
    valid: np.ndarray        # (n, steps) review exists
    y: np.ndarray            # (n, steps) 1.0 if grade > 1
    loss_mask: np.ndarray    # (n, steps) review counts toward loss/metrics
    row: np.ndarray          # (n, steps) row number in the CSV, -1 if none

    def subset(self, keep: np.ndarray) -> "Cards":
        return Cards(*(getattr(self, f)[keep] for f in self.__dataclass_fields__))

    @property
    def n_reviews(self) -> int:
        return int(self.loss_mask.sum())


def load_cards(sessions_csv: str | Path) -> Cards:
    df = pd.read_csv(sessions_csv)
    df["row"] = np.arange(len(df))
    key = df["agent_name"] + "\x1f" + df["opening_name"]
    df["card"] = pd.factorize(key)[0]
    df["step"] = df.groupby("card").cumcount()
    n, steps = df["card"].max() + 1, df["step"].max() + 1

    def grid(values, fill, dtype):
        a = np.full((n, steps), fill, dtype=dtype)
        a[df["card"].to_numpy(), df["step"].to_numpy()] = values
        return a

    valid = grid(True, False, bool)
    t = grid(df["t_days"].to_numpy(float), 0.0, float)
    g = grid(df["grade"].to_numpy(int), 3, int)
    row = grid(df["row"].to_numpy(int), -1, int)
    tested = grid(df["review_status"].isin(TEST_STATUSES).to_numpy(), False, bool)
    loss_mask = valid & tested & (t >= 1.0)
    loss_mask[:, 0] = False
    agent = df.groupby("card")["agent_name"].first().to_numpy()
    return Cards(agent=agent, t=t, g=g, valid=valid, y=(g > 1).astype(float), loss_mask=loss_mask, row=row)
