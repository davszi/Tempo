"""Does a personal FSRS-6 fit beat the global one?

    python experiments/personal.py data/tempo_v1 runs/2026-11-11-first-training

For every val agent: the first 70% of their review days are their own
training history, the last 30% are scored. Compared on the same scored
reviews: default weights, the global fit (runs/2026-11-11-first-training/fitted_global.csv,
trained on other agents), a personal fit (py-fsrs Optimizer on the agent's
own first 70%), a 50/50 blend of global and personal predictions, and the
true weights. Writes personal.csv and personal.txt.

Note: py-fsrs Optimizer returns the DEFAULT weights unchanged when it gets
fewer than 512 review-state reviews (mini_batch_size). A val agent has ~56
reviews in its first 70%, so on tempo_v1 every "personal" fit is the default
vector. See experiments/personal_light.py for a fit that works on little data.
"""
import os
import sys

import numpy as np
import pandas as pd
import torch
from fsrs import Optimizer

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tempo_sim.evaluate import metrics, replay, to_fsrs_review_logs  # noqa: E402
from tempo_sim.fsrs6 import DEFAULT_W  # noqa: E402

torch.set_num_threads(4)
d, out = sys.argv[1], sys.argv[2]
rv = pd.read_csv(f"{d}/reviews.csv")
split = pd.read_csv(f"{d}/split.csv")
agents = pd.read_csv(f"{d}/hidden/agents.csv").set_index("agent_name")
wcols = [f"w{i}" for i in range(21)]
w_global = pd.read_csv(f"{out}/fitted_global.csv")[wcols].iloc[0].to_numpy()
val_ids = split.loc[split.split == "val", "agent_name"]

rows = []
for k, a in enumerate(val_ids):
    h = rv[rv.agent_name == a].copy()
    cut = h.day.min() + 0.7 * (h.day.max() - h.day.min())
    hist = h[h.day <= cut]
    try:
        w_pers = Optimizer(to_fsrs_review_logs(hist)).compute_optimal_parameters()
    except Exception as e:           # too little history
        print(a, "personal fit failed:", e)
        w_pers = w_global
    scored = (h.day > cut) & (h.review_status != "new")
    for name, w in (("default", DEFAULT_W), ("global", w_global), ("personal", w_pers),
                    ("oracle", agents.loc[a, wcols].to_numpy())):
        h[name] = replay(h, lambda _: w)
    h["blend"] = 0.5 * h["global"] + 0.5 * h["personal"]
    s = h[scored]
    rows.append(pd.DataFrame({"agent_name": a, "archetype": agents.loc[a, "archetype"],
                              "n_hist": int((hist.review_status != "new").sum()),
                              "y": (s.grade > 1).astype(int),
                              **{m: s[m] for m in ("default", "global", "personal", "blend", "oracle")}}))
    if k % 25 == 0:
        print(f"{k}/{len(val_ids)}", flush=True)

r = pd.concat(rows)
r.to_csv(f"{out}/personal.csv", index=False)
lines = [f"# Personal vs global fit on {d}",
         f"val agents: {r.agent_name.nunique()}, scored reviews: {len(r)}, "
         f"own history per agent: median {r.groupby('agent_name').n_hist.first().median():.0f} reviews", "",
         "| weights | log-loss | RMSE(bins) | AUC |", "|---|---|---|---|"]
for m in ("default", "global", "personal", "blend", "oracle"):
    x = metrics(r.y, r[m])
    lines.append(f"| {m} | {x['log_loss']:.4f} | {x['rmse_bins']:.4f} | {x['auc']:.3f} |")
lines += ["", "log-loss by archetype:", ""]
by = r.groupby("archetype").apply(lambda g: pd.Series({m: metrics(g.y, g[m])["log_loss"]
                                   for m in ("default", "global", "personal", "blend", "oracle")}),
                                  include_groups=False)
lines.append(by.round(4).to_string())
open(f"{out}/personal.txt", "w").write("\n".join(lines) + "\n")
print("\n".join(lines))
