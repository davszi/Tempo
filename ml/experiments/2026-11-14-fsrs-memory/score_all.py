"""Score the defaults and arms A1, A1c, B1 on the test and hold-out clients.

    python experiments/2026-11-14-fsrs-memory/score_all.py --train data/fsrs-memory/train \
        --holdout data/fsrs-memory/holdout --results experiments/2026-11-14-fsrs-memory/results

Every weight set is scored with ``tempo_ml.evaluate.metrics.score`` (the
metrics of arms A2 and B2) under two clocks: exact elapsed time (``t_days``,
the clock of the shared trainer, used for A1c and B1) and calendar days (the
clock of py-fsrs and of a real app, used for A1). Test clients: the
``split_clients`` test part (seed 7); hold-out: every client of the hold-out
dataset. Paired 95% intervals of the log-loss difference come from 1,000
resamples of whole clients. Writes ``results/scores.json``.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from tempo_ml.evaluate.metrics import Truth, bce, metrics, score
from tempo_ml.fsrs.model import DEFAULT_PARAMETERS, load_cards, predict
from tempo_ml.fsrs.train import split_clients

sys.path.insert(0, str(Path(__file__).parent))
from train_pyfsrs import calendar_cards  # noqa: E402

ARMS = {"A1": "pyfsrs", "A1c": "binary", "B1": "true-recall"}


def load(data: Path, agents=None):
    cards, truth = load_cards(data / "sessions.csv"), Truth(data)
    day = pd.read_csv(data / "ground_truth.csv", usecols=["day"])["day"].to_numpy(float)
    if agents is not None:
        cards = cards.subset(np.isin(cards.agent, sorted(agents)))
    horizon = float(json.loads((data / "manifest.json").read_text())["config"]["horizon_days"])
    return {"exact": cards, "calendar": calendar_cards(cards, day)}, truth, horizon


def paired(cards, truth, wa, wb, n=1000, seed=0):
    """Mean log-loss gain of wb over wa, with a 95% interval over resampled clients."""
    m = cards.loss_mask
    la = bce(predict(wa, cards.t, cards.g, cards.valid)[m], cards.y[m])
    lb = bce(predict(wb, cards.t, cards.g, cards.valid)[m], cards.y[m])
    agent = np.broadcast_to(cards.agent[:, None], m.shape)[m]
    df = pd.DataFrame({"a": agent, "d": la - lb}).groupby("a")["d"].agg(["sum", "count"])
    rng = np.random.default_rng(seed)
    idx = [rng.integers(0, len(df), len(df)) for _ in range(n)]
    boots = [df["sum"].to_numpy()[i].sum() / df["count"].to_numpy()[i].sum() for i in idx]
    return [float(la.mean() - lb.mean()), *map(float, np.quantile(boots, [0.025, 0.975]))]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--train", type=Path, required=True)
    ap.add_argument("--holdout", type=Path, required=True)
    ap.add_argument("--results", type=Path, required=True)
    ap.add_argument("--seed", type=int, default=7)
    a = ap.parse_args()
    W = {"default": np.array(DEFAULT_PARAMETERS, float)}
    for arm, sub in ARMS.items():
        W[arm] = np.array(json.loads((a.results / sub / "fsrs6_general_parameters.json").read_text())["parameters"])
    clients = pd.read_csv(a.train / "clients.csv")
    parts = split_clients(clients, a.seed)
    fit_cards, _, _ = load(a.train, parts["fit"])
    fc = fit_cards["exact"]
    base_rate = float(fc.y[fc.loss_mask].mean())

    out = {"weights": {k: [round(float(x), 6) for x in v] for k, v in W.items()}, "base_rate": base_rate, "sets": {}}
    for name, (data, agents) in {"test": (a.train, parts["test"]), "holdout": (a.holdout, None)}.items():
        cards_by_clock, truth, horizon = load(data, agents)
        res = {}
        for clock, cards in cards_by_clock.items():
            m = cards.loss_mask
            r = {"constant_base_rate": metrics(np.full(int(m.sum()), base_rate), cards.y[m], truth.p_clean[cards.row[m]])}
            r.update({k: score(w, cards, truth, horizon) for k, w in W.items()})
            r["paired"] = {f"{b} vs {x}": paired(cards, truth, W[x], W[b])
                           for x, b in [("default", "A1"), ("default", "A1c"), ("default", "B1"), ("A1c", "B1"), ("A1", "A1c")]}
            res[clock] = r
        out["sets"][name] = {"clients": int(len(np.unique(cards_by_clock["exact"].agent))),
                             "reviews": int(cards_by_clock["exact"].loss_mask.sum()), **res}
        ex, ca = res["exact"], res["calendar"]
        print(name, "| exact:", {k: round(ex[k]["log_loss"], 4) for k in W}, "| calendar:", {k: round(ca[k]["log_loss"], 4) for k in W}, flush=True)
    (a.results / "scores.json").write_text(json.dumps(out, indent=2) + "\n")


if __name__ == "__main__":
    main()
