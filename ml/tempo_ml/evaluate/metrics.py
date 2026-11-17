"""Scores for FSRS-6 predictions on synthetic clients.

Pass-chance metrics: log-loss, Brier, calibration (RMSE(bins)), AUC, and RMSE
and MAE against the hidden true pass chance ``p_pass``. ``score`` adds the
error in days from ``days.py``.

``link`` says what the fitted R means (move-recall record, section 3.4):
``line`` - R is the chance of passing the line, the prediction is R and the
predicted interval is the fitted stability; ``move`` - R is the recall of one
move, the prediction is ``p_pass(R, M)`` and the interval is when it falls to
0.9. Move-link scores also compare R with the hidden per-move recall.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from ..fsrs.model import Cards, predict_states
from ..pass_chance import p_pass
from .days import days_metrics, days_to_pass_target, true_days

EPS = 1e-6
TRUTH_COLUMNS = ["agent_name", "mode", "num_moves", "retrievability", "p_pass", "stability_after"]
LINKS = ("line", "move")


def bce(p: np.ndarray, y: np.ndarray) -> np.ndarray:
    p = np.clip(p, EPS, 1 - EPS)
    return -(y * np.log(p) + (1 - y) * np.log(1 - p))


def auc(p: np.ndarray, y: np.ndarray) -> float:
    order = np.argsort(p, kind="mergesort")
    ranks = np.empty(len(p))
    ranks[order] = np.arange(1, len(p) + 1)
    # average ranks for ties
    _, inv, counts = np.unique(p, return_inverse=True, return_counts=True)
    ranks = np.bincount(inv, ranks)[inv] / counts[inv]
    pos = y == 1
    n_pos, n_neg = pos.sum(), (~pos).sum()
    return float((ranks[pos].sum() - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg))


def rmse_bins(p: np.ndarray, y: np.ndarray, n_bins: int = 20) -> float:
    """Calibration: weighted RMSE between mean prediction and observed rate per bin
    (the definition the removed ml_1000bots evaluation used)."""
    p = np.clip(p, EPS, 1 - EPS)
    b = np.minimum((p * n_bins).astype(int), n_bins - 1)
    num = den = 0.0
    for k in np.unique(b):
        s = b == k
        num += s.sum() * (y[s].mean() - p[s].mean()) ** 2
        den += s.sum()
    return float(np.sqrt(num / den))


def metrics(p: np.ndarray, y: np.ndarray, truth: np.ndarray | None = None) -> dict:
    """Scores of predictions ``p`` against outcomes ``y`` (and the true chance ``truth``)."""
    out = {
        "reviews": int(len(y)),
        "log_loss": float(bce(p, y).mean()),
        "brier": float(np.mean((p - y) ** 2)),
        "rmse_bins": rmse_bins(p, y),
        "auc": auc(p, y),
        "mean_predicted": float(p.mean()),
        "observed_success": float(y.mean()),
    }
    if truth is not None:
        out["rmse_vs_truth"] = float(np.sqrt(np.mean((p - truth) ** 2)))
        out["mae_vs_truth"] = float(np.mean(np.abs(p - truth)))
    return out


class Truth:
    """Hidden per-session truth, aligned with ``sessions.csv`` rows. Evaluation,
    and the fit clients of the simulator-only reference arm."""

    def __init__(self, data_dir: Path):
        gt = pd.read_csv(data_dir / "ground_truth.csv", usecols=TRUTH_COLUMNS)
        clients = pd.read_csv(data_dir / "clients.csv")
        c_by_agent = dict(zip(clients["agent_name"], clients["C"]))
        self.p_pass = gt["p_pass"].to_numpy(float)
        self.r_move = gt["retrievability"].to_numpy(float)
        self.d_true = true_days(gt["stability_after"].to_numpy(float), gt["num_moves"].to_numpy(float),
                                gt["agent_name"].map(c_by_agent).to_numpy(float))
        self.learning = (gt["mode"] == "learning").to_numpy()

    def grid(self, cards: Cards, values: np.ndarray) -> np.ndarray:
        """Per-row values laid out like the cards' (cards, steps) arrays; NaN where empty."""
        return np.where(cards.row >= 0, values[np.maximum(cards.row, 0)], np.nan)


def predicted_pass(r: np.ndarray, m_grid: np.ndarray, link: str) -> np.ndarray:
    """Predicted pass chance from the fitted R (see module docstring)."""
    if link == "line":
        return r
    if link == "move":
        if (m_grid <= 0).any():
            raise ValueError("move link needs every card's line length M")
        return p_pass(r, m_grid)
    raise ValueError(f"link must be one of {LINKS}, got {link!r}")


def predicted_days(w, s_after: np.ndarray, m: np.ndarray, link: str) -> np.ndarray:
    """Predicted days until a 90 % pass chance after each session."""
    if link == "line":
        return s_after
    return days_to_pass_target(s_after, float(w[20]), m)


def score(w, cards: Cards, truth: Truth, horizon_days: float, link: str = "line") -> dict:
    """All metrics of weights ``w`` on ``cards``: tested reviews, plus days over every session."""
    w = np.asarray(w, dtype=float)
    r, s_after = predict_states(w, cards.t, cards.g, cards.valid)
    mg = cards.m_grid()
    m = cards.loss_mask
    p = predicted_pass(np.where(m, r, 1.0), mg, link)
    out = metrics(p[m], cards.y[m], truth.p_pass[cards.row[m]])
    if link == "move":
        rows = cards.row[m]
        out["move_recall"] = {"rmse_vs_truth": float(np.sqrt(np.mean((r[m] - truth.r_move[rows]) ** 2))),
                              "mae_vs_truth": float(np.mean(np.abs(r[m] - truth.r_move[rows])))}
    v = cards.valid
    rows = cards.row[v]
    d_pred = predicted_days(w, s_after[v], mg[v], link)
    out["days"] = days_metrics(d_pred, truth.d_true[rows], truth.learning[rows], horizon_days)
    return out
