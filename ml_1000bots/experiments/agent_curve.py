"""How many training agents does a global FSRS-6 fit need?

    python experiments/agent_curve.py data/tempo_v1 runs/2026-11-11-first-training
    python experiments/agent_curve.py data/tempo_v1 runs/2026-11-11-first-training --plot   # redraw only

Draws nested subsets of the TRAIN agents (25 ... all), fits one global weight
vector on each, and scores it on the fixed val agents. Small sizes are
repeated with different draws. Writes agent_curve.csv and agent_curve.png.
"""
import os
import sys
import time

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import torch
from fsrs import Optimizer

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tempo_sim.evaluate import metrics, replay, to_fsrs_review_logs  # noqa: E402
from tempo_sim.fsrs6 import DEFAULT_W  # noqa: E402

torch.set_num_threads(4)
d, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)
rv = pd.read_csv(f"{d}/reviews.csv")
split = pd.read_csv(f"{d}/split.csv")
agents = pd.read_csv(f"{d}/hidden/agents.csv").set_index("agent_name")
wcols = [f"w{i}" for i in range(21)]
train_ids = split.loc[split.split == "train", "agent_name"].to_numpy()
val = rv[rv.agent_name.isin(split.loc[split.split == "val", "agent_name"])].copy()
is_rev = val.review_status != "new"
y = (val.grade[is_rev] > 1).astype(int)


def plot(res):
    fit = res[res.kind == "fitted"].groupby("n_agents").log_loss.agg(["mean", "min", "max"])
    fig, ax = plt.subplots(figsize=(7, 4.2))
    ax.plot(fit.index, fit["mean"], marker="o", color="#2a6f97", label="global fit (val agents)")
    ax.fill_between(fit.index, fit["min"], fit["max"], color="#2a6f97", alpha=0.15, lw=0)
    for kind, col in (("default", "#e07a5f"), ("oracle", "#3d9970")):
        ax.axhline(res[res.kind == kind].log_loss.iloc[0], color=col, ls="--", lw=1.2,
                   label="default FSRS-6" if kind == "default" else "true weights (oracle)")
    ax.set_xscale("log")
    ax.minorticks_off()
    ax.set_xticks(fit.index, [str(i) for i in fit.index])
    ax.set_xlabel("training agents")
    ax.set_ylabel("val log-loss (lower is better)")
    ax.set_title("How many players does a global fit need?", loc="left")
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.legend(frameon=False, fontsize=9)
    fig.tight_layout()
    fig.savefig(f"{out}/agent_curve.png", dpi=130)


if sys.argv[3:] == ["--plot"]:
    plot(pd.read_csv(f"{out}/agent_curve.csv"))
    sys.exit()


def score(wf):
    p = replay(val, wf)[is_rev]
    return metrics(y, p)


rows = [{"n_agents": 0, "rep": 0, **score(lambda a: DEFAULT_W), "kind": "default"},
        {"n_agents": 0, "rep": 0, **score(lambda a: agents.loc[a, wcols].values), "kind": "oracle"}]
sizes = [s for s in (25, 50, 100, 200, 400) if s < len(train_ids)] + [len(train_ids)]
for rep in range(3):
    order = np.random.default_rng(100 + rep).permutation(train_ids)
    for n in sizes:
        if rep > 0 and n > 200:
            continue                      # large subsets barely vary between draws
        sub = rv[rv.agent_name.isin(order[:n])]
        t = time.time()
        w = Optimizer(to_fsrs_review_logs(sub)).compute_optimal_parameters()
        m = score(lambda a: w)
        rows.append({"n_agents": n, "rep": rep, **m, "kind": "fitted",
                     "n_reviews": int((sub.review_status != "new").sum()),
                     "fit_s": round(time.time() - t, 1), "C_fit": w[20]})
        print(f"rep {rep} n {n:4d}: log-loss {m['log_loss']:.4f} rmse {m['rmse_bins']:.4f} "
              f"C {w[20]:.3f} ({time.time() - t:.0f}s)", flush=True)

res = pd.DataFrame(rows)
res.to_csv(f"{out}/agent_curve.csv", index=False)

plot(res)
print(res.round(4).to_string(index=False))
