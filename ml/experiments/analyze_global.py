"""Deeper look at the global fit on a dataset.

    python experiments/analyze_global.py data/tempo_v1 runs/2026-11-11-first-training

1. Bootstrap over val agents: is the gain over the defaults real?
2. Score per archetype.
3. Archetype fits: one FSRS-6 fit per archetype (train agents only), each val
   agent scored with its archetype's weights. Upper bound for the cohort idea
   in the review-dataset record (4.2), since the archetype is known here.
Writes analysis.txt.
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

torch.set_num_threads(6)
d, out = sys.argv[1], sys.argv[2]
rv = pd.read_csv(f"{d}/reviews.csv")
split = pd.read_csv(f"{d}/split.csv").set_index("agent_name").split
agents = pd.read_csv(f"{d}/hidden/agents.csv").set_index("agent_name")
wcols = [f"w{i}" for i in range(21)]
wg = pd.read_csv(f"{out}/fitted_global.csv")[wcols].iloc[0].to_numpy()
rv["arch"] = rv.agent_name.map(agents.archetype)

w_arch = {}
for a in sorted(agents.archetype.unique()):
    tr = rv[(rv.arch == a) & (rv.agent_name.map(split) == "train")]
    w_arch[a] = Optimizer(to_fsrs_review_logs(tr)).compute_optimal_parameters()

val = rv[rv.agent_name.map(split) == "val"].copy()
val["default"] = replay(val, lambda _: DEFAULT_W)
val["global"] = replay(val, lambda _: wg)
val["archetype_fit"] = replay(val, lambda a: w_arch[agents.archetype[a]])
val["oracle"] = replay(val, lambda a: agents.loc[a, wcols].to_numpy())
v = val[val.review_status != "new"].copy()
v["y"] = (v.grade > 1).astype(int)
models = ["default", "global", "archetype_fit", "oracle"]

lines = [f"# Analysis of the global fit on {d}", "", "| weights | log-loss | RMSE(bins) | AUC |", "|---|---|---|---|"]
for m in models:
    x = metrics(v.y, v[m])
    lines.append(f"| {m} | {x['log_loss']:.4f} | {x['rmse_bins']:.4f} | {x['auc']:.3f} |")

# per-agent summed log-loss for bootstrap
eps = 1e-6
for m in models:
    p = v[m].clip(eps, 1 - eps)
    v["ll_" + m] = -(v.y * np.log(p) + (1 - v.y) * np.log(1 - p))
per = v.groupby("agent_name")[["ll_" + m for m in models]].sum()
n_rev = v.groupby("agent_name").size()
rng = np.random.default_rng(0)
ids = per.index.to_numpy()
boot = []
for _ in range(2000):
    s = rng.choice(ids, len(ids))
    tot = per.loc[s].sum() / n_rev.loc[s].sum()
    boot.append({"default-global": tot.ll_default - tot.ll_global,
                 "global-archetype": tot.ll_global - tot.ll_archetype_fit,
                 "global-oracle": tot.ll_global - tot.ll_oracle})
b = pd.DataFrame(boot)
lines += ["", "Bootstrap over val agents (2000 resamples), log-loss difference, 95% interval:", ""]
for c in b:
    lines.append(f"- {c}: {b[c].mean():.4f}  [{b[c].quantile(.025):.4f}, {b[c].quantile(.975):.4f}]"
                 f"  share > 0: {(b[c] > 0).mean():.3f}")
gap = (b["default-global"] / (b["default-global"] + b["global-oracle"]))
lines.append(f"- share of the default->oracle gap closed by the global fit: {gap.mean():.0%} "
             f"[{gap.quantile(.025):.0%}, {gap.quantile(.975):.0%}]")

lines += ["", "log-loss by archetype (val):", ""]
by = v.groupby("arch").apply(lambda g: pd.Series({**{m: metrics(g.y, g[m])['log_loss'] for m in models},
                                                  "pass_rate": g.y.mean(), "n": len(g)}), include_groups=False)
lines.append(by.round(4).to_string())
lines += ["", "mean predicted pass vs observed, by archetype (calibration-in-the-large):", ""]
cal = v.groupby("arch").apply(lambda g: pd.Series({"observed": g.y.mean(), **{m: g[m].mean() for m in models}}),
                              include_groups=False)
lines.append(cal.round(3).to_string())
lines += ["", "C (w20): true median by archetype vs fits:", ""]
lines.append(pd.DataFrame({"true": agents.groupby("archetype").w20.median(),
                           "archetype_fit": pd.Series({a: w[20] for a, w in w_arch.items()}),
                           "global": wg[20]}).round(3).to_string())
open(f"{out}/analysis.txt", "w").write("\n".join(lines) + "\n")
print("\n".join(lines))
