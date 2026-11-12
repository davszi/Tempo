"""Generate a TEMPO synthetic dataset.

    python generate.py --out data/synth_v1 [--config cfg.json] [--agents 300] [--seed 7]

Writes
  <out>/reviews.csv          what the optimizer may see (one row per learn/review);
                             first 7 columns = review-dataset record schema
  <out>/moves.csv            move-level telemetry (for grader / latency work)
  <out>/openings.csv         the opening lines used (line_id -> name, moves, side)
  <out>/split.csv            agent_name -> train / val   (split BY AGENT)
  <out>/config.json          exact config used (reproducibility)
  <out>/hidden/agents.csv    ground-truth persona parameters  (NEVER train on)
  <out>/hidden/truth.csv     per-review R_true, S, D          (NEVER train on)
"""
import argparse
import os

import numpy as np
import pandas as pd

from tempo_sim.config import SimConfig
from tempo_sim.simulate import simulate


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--config")
    ap.add_argument("--agents", type=int)
    ap.add_argument("--seed", type=int)
    a = ap.parse_args()

    cfg = SimConfig.load(a.config)
    if a.agents:
        cfg.n_agents = a.agents
    if a.seed is not None:
        cfg.seed = a.seed

    personas, catalogue, reviews, moves, truth = simulate(cfg)

    os.makedirs(os.path.join(a.out, "hidden"), exist_ok=True)
    rv = pd.DataFrame(reviews)
    for c in ("total_time_ms", "n_correct"):
        rv[c] = rv[c].astype("Int64")
    rv.to_csv(os.path.join(a.out, "reviews.csv"), index=False)
    pd.DataFrame(moves).to_csv(os.path.join(a.out, "moves.csv"), index=False)
    pd.DataFrame([{
        "line_id": l.line_id, "opening_name": l.name, "pgn": l.pgn,
        "color": l.color, "n_moves": l.n_moves,
        "plies": " ".join(map(str, l.plies))} for l in catalogue
    ]).to_csv(os.path.join(a.out, "openings.csv"), index=False)

    rng = np.random.default_rng(cfg.seed + 1)
    ids = np.array([p.agent_name for p in personas])
    rng.shuffle(ids)
    n_train = int(round(cfg.train_frac * len(ids)))
    pd.DataFrame({"agent_name": ids,
                  "split": ["train"] * n_train + ["val"] * (len(ids) - n_train)}
                 ).sort_values("agent_name").to_csv(os.path.join(a.out, "split.csv"), index=False)

    pd.DataFrame([p.hidden_row() for p in personas]).to_csv(
        os.path.join(a.out, "hidden", "agents.csv"), index=False)
    pd.DataFrame(truth).to_csv(os.path.join(a.out, "hidden", "truth.csv"), index=False)
    with open(os.path.join(a.out, "config.json"), "w") as f:
        f.write(cfg.to_json())

    n_rev = int((rv.review_status != "new").sum())
    print(f"{len(personas)} agents, {len(rv)} rows ({n_rev} reviews), "
          f"{len(moves)} moves -> {a.out}")


if __name__ == "__main__":
    main()
