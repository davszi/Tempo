"""Score FSRS-6 weights on the hold-out clients (no fitting).

    python experiments/2026-11-13-fsrs-synthetic-v2/holdout_benchmark.py --data <new dataset dir> \
        --weights <name>=<fsrs6_general_parameters.json> [<name>=<file> ...] \
        --base-rate <rate> --out <metrics.json>

No fitting: every client in ``--data`` is scored with the FSRS-6 default
weights and with each set of given weights, with every metric of
``tempo_ml.evaluate.metrics.score`` (days included). A constant guess equal to ``--base-rate``
(the training clients' success rate) is included as a floor.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from tempo_ml.evaluate.metrics import Truth, metrics, score
from tempo_ml.fsrs.model import DEFAULT_PARAMETERS, load_cards


def _named(item: str) -> tuple[str, Path]:
    name, _, path = item.partition("=")
    if not path:
        raise argparse.ArgumentTypeError(f"expected <name>=<file>, got {item!r}")
    return name, Path(path)


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="Score FSRS-6 weights on new clients")
    ap.add_argument("--data", type=Path, required=True)
    ap.add_argument("--weights", type=_named, nargs="+", required=True, help="<name>=<parameters json>")
    ap.add_argument("--base-rate", type=float, required=True,
                    help="success rate of the training clients, for the constant guess")
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)

    cards = load_cards(a.data / "sessions.csv")
    truth = Truth(a.data)
    horizon = float(json.loads((a.data / "manifest.json").read_text())["config"]["horizon_days"])
    clients = pd.read_csv(a.data / "clients.csv")
    archetype = dict(zip(clients["agent_name"], clients["archetype"]))
    models = {"fsrs6_default": DEFAULT_PARAMETERS}
    for name, path in a.weights:
        models[name] = np.array(json.loads(path.read_text())["parameters"])

    m = cards.loss_mask
    y = cards.y[m]
    out = {
        "clients": int(len(clients)),
        "weights": {name: str(path) for name, path in a.weights},
        "overall": {"constant_guess": metrics(np.full(len(y), a.base_rate), y, truth.p_clean[cards.row[m]]),
                    **{k: score(w, cards, truth, horizon) for k, w in models.items()}},
        "by_archetype": {},
    }
    arch = np.array([archetype[x] for x in cards.agent])
    for name in sorted(set(arch)):
        sub = cards.subset(arch == name)
        out["by_archetype"][name] = {k: score(w, sub, truth, horizon) for k, w in models.items()}
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(out, indent=2) + "\n")
    for k, v in out["overall"].items():
        line = "  ".join(f"{x}={v[x]:.4f}" for x in ("log_loss", "brier", "rmse_bins", "auc", "rmse_vs_truth", "mean_predicted"))
        if "days" in v:
            line += f"  days_median_error={v['days']['median_error']:+.3f}"
        print(f"{k:16s} {line}")
    print(f"reviews={len(y)} observed_success={y.mean():.4f}")


if __name__ == "__main__":
    main()
