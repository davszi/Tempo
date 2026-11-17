"""Arm A1: fit FSRS-6 with the official py-fsrs Optimizer on the fit clients.

    python experiments/2026-11-16-move-recall/train_pyfsrs.py --data <generated dir> --out <dir> [--seed 7]

Same split (``split_clients``, seed 7) and scoring (``tempo_ml.evaluate.metrics.score``,
link ``line``) as the shared-trainer arms of ``tempo_ml.fsrs.train``.
py-fsrs 6.3.2 with its default settings (Adam, learning rate 0.04, 5 epochs,
batch 512), started at the FSRS-6 defaults. py-fsrs runs on the CPU.

Clock: every session gets a real timestamp (a fixed start plus its exact
simulation day); py-fsrs counts whole elapsed days between timestamps, as the
app's scheduler does. Scoring uses the same app clock (``load_cards`` default).
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
from tempo_ml.fsrs.model import DEFAULT_PARAMETERS, line_lengths, load_cards
from tempo_ml.fsrs.train import split_clients

T0 = datetime(2026, 1, 5, tzinfo=timezone.utc)


def review_logs(sessions: pd.DataFrame, days: np.ndarray):
    from fsrs import Rating, ReviewLog
    card = pd.factorize(sessions["agent_name"] + "\x1f" + sessions["opening_name"])[0]
    return [ReviewLog(card_id=int(c), rating=Rating(int(g)), review_datetime=T0 + timedelta(days=float(d)),
                      review_duration=int(ms))
            for c, g, d, ms in zip(card, sessions["grade"], days, sessions["total_time_ms"])]


def main(argv: list[str] | None = None) -> None:
    import fsrs
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

    cards, truth = load_cards(a.data / "sessions.csv", line_lengths(a.data)), Truth(a.data)
    horizon = float(json.loads((a.data / "manifest.json").read_text())["config"]["horizon_days"])
    test = cards.subset(np.isin(cards.agent, sorted(parts["test"])))
    fit_cards = cards.subset(np.isin(cards.agent, sorted(parts["fit"])))
    m = test.loss_mask
    base_rate = float(fit_cards.y[fit_cards.loss_mask].mean())
    results = {
        "arm": "A1", "link": "line", "clock": "app", "trainer": "py-fsrs Optimizer (default settings)",
        "test": {
            "constant_base_rate": metrics(np.full(int(m.sum()), base_rate), test.y[m], truth.p_pass[test.row[m]]),
            "fsrs6_default": score(DEFAULT_PARAMETERS, test, truth, horizon, "line"),
            "fsrs6_trained": score(w, test, truth, horizon, "line"),
        },
        "base_rate": base_rate,
        "trained_on": {"clients": len(parts["fit"]), "sessions": int(fit_rows.sum()),
                       "reviews": int(fit_cards.loss_mask.sum())},
        "seconds_fit": seconds,
        "split": {k: sorted(v) for k, v in parts.items()},
        "environment": {"python": platform.python_version(), "numpy": np.__version__, "pandas": pd.__version__,
                        "fsrs": getattr(fsrs, "__version__", "6.3.2"), "platform": platform.platform()},
    }
    params = {"model": "FSRS-6", "arm": "A1", "recall_means": "the line", "clock": "app",
              "trainer": "py-fsrs Optimizer", "parameters": [round(float(x), 6) for x in w],
              "default_parameters": DEFAULT_PARAMETERS.tolist(),
              "trained_on": {"data": str(a.data), **results["trained_on"], "base_rate": base_rate}}
    (a.out / "fsrs6_general_parameters.json").write_text(json.dumps(params, indent=2) + "\n")
    (a.out / "metrics.json").write_text(json.dumps(results, indent=2) + "\n")
    print(json.dumps({k: round(v["log_loss"], 4) for k, v in results["test"].items()}), flush=True)


if __name__ == "__main__":
    main()
