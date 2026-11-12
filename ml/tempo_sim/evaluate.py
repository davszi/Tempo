"""Evaluation helpers the optimizer team can reuse.

replay(reviews, weights_for)  -> predicted R before every review
metrics(y, p)                 -> log-loss, RMSE(bins), AUC
param_recovery(fitted, agents)-> error of fitted weights vs hidden truth
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .fsrs6 import FSRS6, MemoryState


def replay(reviews: pd.DataFrame, weights_for) -> pd.Series:
    """Replay each (agent, opening) history with FSRS-6 and return the model's
    predicted recall right before each review. weights_for(agent_name) -> 21 floats.
    Only uses columns the optimizer is allowed to see."""
    out = pd.Series(np.nan, index=reviews.index, dtype=float)
    rv = reviews.sort_values(["agent_name", "line_id", "day", "review_id"])
    cache = {}
    for (agent, _), grp in rv.groupby(["agent_name", "line_id"], sort=False):
        if agent not in cache:
            cache[agent] = FSRS6(weights_for(agent))
        m = cache[agent]
        st: MemoryState | None = None
        last = None
        for idx, row in zip(grp.index, grp.itertuples()):
            g = int(row.grade)
            if st is None:
                st = m.init_state(g)
            else:
                t = row.day - last
                out[idx] = m.retrievability(t, st.stability)
                st = m.step(st, t, g)
            last = row.day
    return out


def metrics(y: np.ndarray, p: np.ndarray, n_bins: int = 20) -> dict:
    y = np.asarray(y, float)
    p = np.clip(np.asarray(p, float), 1e-6, 1 - 1e-6)
    logloss = float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))
    bins = np.minimum((p * n_bins).astype(int), n_bins - 1)
    df = pd.DataFrame({"b": bins, "y": y, "p": p}).groupby("b").agg(
        y=("y", "mean"), p=("p", "mean"), n=("y", "size"))
    rmse_bins = float(np.sqrt(np.average((df.y - df.p) ** 2, weights=df.n)))
    # AUC via rank statistic; tied predictions share their average rank,
    # so a constant prediction gives exactly 0.5
    ranks = pd.Series(p).rank(method="average").to_numpy()
    n1, n0 = y.sum(), len(y) - y.sum()
    auc = float((ranks[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)) if n1 and n0 else float("nan")
    return {"log_loss": logloss, "rmse_bins": rmse_bins, "auc": auc, "n": int(len(y))}


def param_recovery(fitted: pd.DataFrame, agents: pd.DataFrame) -> pd.DataFrame:
    """fitted / agents: one row per agent_name with columns w0..w20.
    Returns per-weight median relative error. For a *global* fit, pass the
    same fitted row for every agent (compare to the population)."""
    wcols = [f"w{i}" for i in range(21)]
    m = agents[["agent_name"] + wcols].merge(fitted[["agent_name"] + wcols],
                                            on="agent_name", suffixes=("_true", "_fit"))
    rows = []
    for c in wcols:
        rel = (m[c + "_fit"] - m[c + "_true"]).abs() / m[c + "_true"].abs().clip(lower=1e-3)
        rows.append({"weight": c, "median_rel_err": float(rel.median()),
                     "true_median": float(m[c + "_true"].median()),
                     "fit_median": float(m[c + "_fit"].median())})
    return pd.DataFrame(rows)


def to_fsrs_review_logs(reviews: pd.DataFrame, start_date: str = "2026-01-05"):
    """Convert reviews.csv rows to py-fsrs ReviewLog objects for fsrs.Optimizer.

    Timestamps are placed at midnight UTC of the study day on purpose: py-fsrs
    computes elapsed time as timedelta.days (floor of 24h), so real clock times
    (e.g. 22:00 then 07:00 next day) would turn a 1-day gap into a "same-day"
    review. Use calendar-day differences in the player's local time in the real
    app too (this is what Anki does).
    """
    from datetime import datetime, timedelta, timezone

    from fsrs import Rating, ReviewLog

    t0 = datetime.fromisoformat(start_date).replace(tzinfo=timezone.utc)
    keys = {k: i for i, k in enumerate(
        reviews[["agent_name", "line_id"]].drop_duplicates().itertuples(index=False))}
    logs = []
    for row in reviews.itertuples():
        dur = None if pd.isna(row.total_time_ms) else int(row.total_time_ms)
        logs.append(ReviewLog(card_id=keys[(row.agent_name, row.line_id)],
                              rating=Rating(int(row.grade)),
                              review_datetime=t0 + timedelta(days=int(row.day)),
                              review_duration=dur))
    return logs
