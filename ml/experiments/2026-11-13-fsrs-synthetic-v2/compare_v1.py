"""Score the v1, A2 and B2 weights and the defaults on the same v2 clients.

    python experiments/2026-11-13-fsrs-synthetic-v2/compare_v1.py   (from ml/)

No fitting. Every weight set is scored with ``tempo_ml.evaluate.metrics.score``
on the 60 test clients of ``data/fsrs-synthetic-v2/train`` (split seed 7) and
on the 60 hold-out clients. The v1 weights come from commit 09f8a22, where the
removed v1 experiment still lives. Writes ``results/v1_comparison.json``.

Run on 2026-11-13 from the earlier layout (``ml_300bots/ml_engine``); this copy
only has its paths updated.
"""

import json
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd

from tempo_ml.evaluate.metrics import Truth, score
from tempo_ml.fsrs.model import DEFAULT_PARAMETERS, load_cards
from tempo_ml.fsrs.train import split_clients

HERE = Path(__file__).resolve().parent
DATA = HERE.parents[1] / "data" / "fsrs-synthetic-v2"
V1 = "09f8a22:ml/ml_300bots/ml_engine/experiments/fsrs-synthetic-v1/results/fsrs6_general_parameters.json"

v1 = json.loads(subprocess.run(["git", "show", V1], capture_output=True, text=True, check=True, cwd=HERE).stdout)
W = {"default": DEFAULT_PARAMETERS, "v1": np.array(v1["parameters"])}
for name, sub in [("A2", "binary"), ("B2", "true-recall")]:
    W[name] = np.array(json.loads((HERE / "results" / sub / "fsrs6_general_parameters.json").read_text())["parameters"])

out = {}
for setname, d in [("test", DATA / "train"), ("holdout", DATA / "holdout")]:
    cards, truth = load_cards(d / "sessions.csv"), Truth(d)
    horizon = float(json.loads((d / "manifest.json").read_text())["config"]["horizon_days"])
    if setname == "test":
        parts = split_clients(pd.read_csv(d / "clients.csv"), 7)
        cards = cards.subset(np.isin(cards.agent, list(parts["test"])))
    out[setname] = {k: score(w, cards, truth, horizon) for k, w in W.items()}
    for k, v in out[setname].items():
        b = v["days"]["bands"]
        print(setname, k, f"rmse_truth={v['rmse_vs_truth']*100:.1f} cal={v['rmse_bins']*100:.1f} auc={v['auc']:.3f} "
              f"mean={v['mean_predicted']*100:.1f} ll={v['log_loss']:.4f} days_med={v['days']['median_error']:+.2f} "
              f"ge30={b['ge30']['median_error']:+.1f}")
(HERE / "results" / "v1_comparison.json").write_text(
    json.dumps({"weights": {k: list(map(float, w)) for k, w in W.items()}, **out}, indent=2))
