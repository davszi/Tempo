"""Benchmark FSRS-6 weights on a separate dataset of new synthetic clients.

    python -m tempo_ml.fsrs.benchmark --data <new dataset dir> --weights <fsrs6_general_parameters.json> --out <metrics.json>

No fitting: every client in ``--data`` is scored with the FSRS-6 default
weights and with the given trained weights. A constant guess equal to the
success rate stored in the weights file's training data is included as a floor.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from .data import load_cards
from .model import DEFAULT_PARAMETERS, predict
from .train import metrics


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="Score FSRS-6 weights on new clients")
    ap.add_argument("--data", type=Path, required=True)
    ap.add_argument("--weights", type=Path, required=True)
    ap.add_argument("--base-rate", type=float, required=True,
                    help="success rate of the training clients, for the constant guess")
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)

    cards = load_cards(a.data / "sessions.csv")
    truth_all = pd.read_csv(a.data / "ground_truth.csv", usecols=["p_clean"])["p_clean"].to_numpy()
    clients = pd.read_csv(a.data / "clients.csv")
    archetype = dict(zip(clients["agent_name"], clients["archetype"]))
    w_trained = np.array(json.loads(a.weights.read_text())["parameters"])

    m = cards.loss_mask
    y, truth = cards.y[m], truth_all[cards.row[m]]
    p_def = predict(DEFAULT_PARAMETERS, cards.t, cards.g, cards.valid)
    p_tr = predict(w_trained, cards.t, cards.g, cards.valid)
    out = {
        "clients": int(len(clients)),
        "overall": {
            "constant_guess": metrics(np.full(len(y), a.base_rate), y, truth),
            "fsrs6_default": metrics(p_def[m], y, truth),
            "fsrs6_trained": metrics(p_tr[m], y, truth),
        },
        "by_archetype": {},
    }
    arch = np.array([archetype[x] for x in cards.agent])
    for name in sorted(set(arch)):
        mm = m & (arch == name)[:, None]
        yy, tt = cards.y[mm], truth_all[cards.row[mm]]
        out["by_archetype"][name] = {
            "fsrs6_default": metrics(p_def[mm], yy, tt),
            "fsrs6_trained": metrics(p_tr[mm], yy, tt),
        }
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(out, indent=2) + "\n")
    for k, v in out["overall"].items():
        print(f"{k:16s} " + "  ".join(f"{x}={v[x]:.4f}" for x in ("log_loss", "brier", "auc", "mae_vs_true_p_clean", "mean_predicted")))
    print(f"reviews={len(y)} observed_success={y.mean():.4f}")


if __name__ == "__main__":
    main()
