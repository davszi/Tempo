"""Arm A1: fit FSRS-6 with the official py-fsrs Optimizer on the fit clients.

    python experiments/2026-11-14-fsrs-memory/train_pyfsrs.py --data data/fsrs-memory/train \
        --out experiments/2026-11-14-fsrs-memory/results/pyfsrs --seed 7

Same split as ``tempo_ml.fsrs.train`` (``split_clients``, by archetype, seed 7)
and the same scoring (``tempo_ml.evaluate.metrics.score``), so A1 compares
directly with the shared-trainer arms. py-fsrs 6.3.2, default settings (Adam,
learning rate 0.04, 5 epochs, batch 512), started at the FSRS-6 defaults.

Clock: py-fsrs counts elapsed time in whole days between review timestamps.
Reviews are stamped at midnight of their calendar day (``floor(day)`` of
``ground_truth.csv``; the app knows when a session happened, so this is not
hidden information), as a real app counts days. ``score`` replays with the
exact elapsed time ``t_days``; the metrics are also reported with calendar
days (``*_calendar``) because the two clocks differ for same-day and
overnight gaps.
"""

from __future__ import annotations

import argparse
import json
import platform
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from tempo_ml.evaluate.metrics import Truth, metrics, score
from tempo_ml.fsrs.model import DEFAULT_PARAMETERS, load_cards
from tempo_ml.fsrs.train import split_clients


def review_logs(sessions: pd.DataFrame, days: np.ndarray):
    from fsrs import Rating, ReviewLog

    t0 = datetime(2026, 1, 5, tzinfo=timezone.utc)
    card = pd.factorize(sessions["agent_name"] + "\x1f" + sessions["opening_name"])[0]
    return [ReviewLog(card_id=int(c), rating=Rating(int(g)),
                      review_datetime=t0 + timedelta(days=int(np.floor(d))), review_duration=int(ms))
            for c, g, d, ms in zip(card, sessions["grade"], days, sessions["total_time_ms"])]


def calendar_cards(cards, day: np.ndarray):
    """The same cards with t = difference of calendar days (floor of the session day)."""
    cal = np.where(cards.row >= 0, np.floor(day[np.maximum(cards.row, 0)]), np.nan)
    t = np.zeros_like(cards.t)
    t[:, 1:] = np.where(cards.valid[:, 1:], cal[:, 1:] - cal[:, :-1], 0.0)
    out = type(cards)(**{f: getattr(cards, f) for f in cards.__dataclass_fields__})
    out.t = t
    return out


def main(argv: list[str] | None = None) -> None:
    from fsrs import Optimizer

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--data", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--seed", type=int, default=7)
    a = ap.parse_args(argv)
    a.out.mkdir(parents=True, exist_ok=True)
    started = time.time()

    sessions = pd.read_csv(a.data / "sessions.csv")
    day = pd.read_csv(a.data / "ground_truth.csv", usecols=["day"])["day"].to_numpy(float)
    clients = pd.read_csv(a.data / "clients.csv")
    parts = split_clients(clients, a.seed)
    fit_rows = sessions["agent_name"].isin(parts["fit"]).to_numpy()

    w = np.array(Optimizer(review_logs(sessions[fit_rows], day[fit_rows])).compute_optimal_parameters(), float)
    seconds = round(time.time() - started, 1)

    cards, truth = load_cards(a.data / "sessions.csv"), Truth(a.data)
    horizon = float(json.loads((a.data / "manifest.json").read_text())["config"]["horizon_days"])
    test = cards.subset(np.isin(cards.agent, sorted(parts["test"])))
    fit_cards = cards.subset(np.isin(cards.agent, sorted(parts["fit"])))
    m = test.loss_mask
    base_rate = float(fit_cards.y[fit_cards.loss_mask].mean())
    test_cal = calendar_cards(test, day)
    results = {
        "arm": "A1", "trainer": "py-fsrs Optimizer (default settings)", "clock": "calendar days",
        "test": {
            "constant_base_rate": metrics(np.full(int(m.sum()), base_rate), test.y[m], truth.p_clean[test.row[m]]),
            "fsrs6_default": score(DEFAULT_PARAMETERS, test, truth, horizon),
            "fsrs6_trained": score(w, test, truth, horizon),
            "fsrs6_default_calendar": score(DEFAULT_PARAMETERS, test_cal, truth, horizon),
            "fsrs6_trained_calendar": score(w, test_cal, truth, horizon),
        },
        "base_rate": base_rate,
        "trained_on": {"clients": len(parts["fit"]), "sessions": int(fit_rows.sum()),
                       "reviews": int(fit_cards.loss_mask.sum())},
        "seconds_fit": seconds,
        "environment": {"python": platform.python_version(), "numpy": np.__version__,
                        "pandas": pd.__version__, "fsrs": __import__("fsrs").__version__ if hasattr(__import__("fsrs"), "__version__") else "6.3.2",
                        "platform": platform.platform()},
    }
    params = {"model": "FSRS-6", "arm": "A1", "trainer": "py-fsrs 6.3.2 Optimizer",
              "parameters": [round(float(x), 6) for x in w], "default_parameters": DEFAULT_PARAMETERS.tolist(),
              "trained_on": {"data": str(a.data), **results["trained_on"], "base_rate": base_rate}}
    (a.out / "fsrs6_general_parameters.json").write_text(json.dumps(params, indent=2) + "\n")
    (a.out / "metrics.json").write_text(json.dumps(results, indent=2) + "\n")
    print(json.dumps({k: round(v["log_loss"], 4) for k, v in results["test"].items()}), flush=True)


if __name__ == "__main__":
    main()
