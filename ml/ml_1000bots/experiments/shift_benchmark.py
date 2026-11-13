"""Stress test the trained weights on NEW populations that differ from training.

    python experiments/shift_benchmark.py data/tempo_v1 <fitted_global.csv> runs/2026-11-11-first-training/control [--control]

--control runs only the control scenario (same rules as training, new players).

Each scenario changes the tempo_v1 config, generates 200 fresh agents (new
seed, never used for training) and scores four weight sets on ALL their
reviews: default FSRS-6, the global fit, one fit per archetype (trained on the
tempo_v1 train agents; fitted once and saved), and the true weights (oracle).
Writes shift_benchmark.csv, shift_benchmark.md and shift_benchmark.png.
"""
import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import torch
from fsrs import Optimizer

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tempo_sim.config import SimConfig  # noqa: E402
from tempo_sim.evaluate import metrics, replay, to_fsrs_review_logs  # noqa: E402
from tempo_sim.fsrs6 import DEFAULT_W  # noqa: E402
from tempo_sim.simulate import simulate  # noqa: E402

torch.set_num_threads(6)
d, global_csv, out = sys.argv[1], sys.argv[2], sys.argv[3]
os.makedirs(out, exist_ok=True)
wcols = [f"w{i}" for i in range(21)]
w_global = pd.read_csv(global_csv)[wcols].iloc[0].to_numpy()

# ---- one fit per archetype on the tempo_v1 train agents (cached) ----
arch_csv = os.path.join(out, "fitted_archetype.csv")
if not os.path.exists(arch_csv):
    rv = pd.read_csv(f"{d}/reviews.csv")
    split = pd.read_csv(f"{d}/split.csv").set_index("agent_name").split
    arch = pd.read_csv(f"{d}/hidden/agents.csv").set_index("agent_name").archetype
    rows = []
    for a in sorted(arch.unique()):
        tr = rv[(rv.agent_name.map(arch) == a) & (rv.agent_name.map(split) == "train")]
        w = Optimizer(to_fsrs_review_logs(tr)).compute_optimal_parameters()
        rows.append({"archetype": a, **dict(zip(wcols, w))})
        print(f"archetype fit {a}: C = {w[20]:.3f}", flush=True)
    pd.DataFrame(rows).to_csv(arch_csv, index=False)
w_arch = pd.read_csv(arch_csv).set_index("archetype")[wcols]

base = json.load(open(f"{d}/config.json"))
only = lambda a: {"archetypes": {a: {**base["archetypes"][a], "weight": 1.0}}}  # noqa: E731
SCENARIOS = {
    "control (same as training)": {},
    "only fast players": only("fast"),
    "only balanced players": only("balanced"),
    "only diligent players": only("diligent"),
    "long breaks (often 20-60 days off)": {"break_prob": 0.05, "break_days": [20, 60]},
    "one year of practice": {"horizon_days": 365},
    "long lines only (10-16 moves)": {"user_moves": [10, 16]},
    "short lines only (4-6 moves)": {"user_moves": [4, 6]},
    "more diverse players (weight noise 0.30)": {"weight_noise": 0.30},
    "slower learners (weaker, slower-growing memory)": {
        "archetypes": {a: {**v, "init_stability_mult": 0.6, "growth_shift": -0.4}
                       for a, v in base["archetypes"].items()}},
}

if "--control" in sys.argv:
    SCENARIOS = dict(list(SCENARIOS.items())[:1])

results = []
for k, (name, change) in enumerate(SCENARIOS.items()):
    cfg = SimConfig()
    for key, val in {**base, **change, "n_agents": 200, "seed": 2000 + k}.items():
        if key == "archetypes":
            from tempo_sim.config import Archetype
            cfg.archetypes = {n: Archetype(**a) for n, a in val.items()}
        else:
            setattr(cfg, key, tuple(val) if isinstance(val, list) else val)
    personas, _, reviews, _, _ = simulate(cfg)
    rv = pd.DataFrame(reviews)
    true_w = {p.agent_name: p.w for p in personas}
    arch_of = {p.agent_name: p.archetype for p in personas}
    preds = {"default": replay(rv, lambda a: DEFAULT_W),
             "global fit": replay(rv, lambda a: w_global),
             "archetype fit": replay(rv, lambda a: w_arch.loc[arch_of[a]].to_numpy()),
             "oracle": replay(rv, lambda a: true_w[a])}
    m = (rv.review_status != "new").to_numpy()
    y = (rv.grade[m] > 1).astype(int).to_numpy()
    row = {"scenario": name, "reviews": int(m.sum()), "pass_rate": y.mean()}
    ll = {}
    for wname, p in preds.items():
        x = metrics(y, p[m])
        ll[wname] = x["log_loss"]
        row.update({f"{wname} log-loss": x["log_loss"], f"{wname} RMSE": x["rmse_bins"],
                    f"{wname} AUC": x["auc"]})
    # bootstrap over agents: global fit minus default (negative = fit is better)
    eps = 1e-6
    df = pd.DataFrame({"a": rv.agent_name[m].to_numpy(), "y": y,
                       "g": preds["global fit"][m].clip(eps, 1 - eps).to_numpy(),
                       "d": preds["default"][m].clip(eps, 1 - eps).to_numpy()})
    for c in ("g", "d"):
        df["l" + c] = -(df.y * np.log(df[c]) + (1 - df.y) * np.log(1 - df[c]))
    per = df.groupby("a")[["lg", "ld"]].sum()
    n = df.groupby("a").size()
    rng = np.random.default_rng(0)
    diffs = []
    for _ in range(1000):
        s = rng.choice(per.index.to_numpy(), len(per))
        diffs.append((per.loc[s, "ld"].sum() - per.loc[s, "lg"].sum()) / n.loc[s].sum())
    diffs = np.array(diffs)
    row["fit gain vs default"] = ll["default"] - ll["global fit"]
    row["gain 95% low"], row["gain 95% high"] = np.quantile(diffs, [0.025, 0.975])
    gap = ll["default"] - ll["oracle"]
    row["gap closed"] = (ll["default"] - ll["global fit"]) / gap if gap > 0 else np.nan
    results.append(row)
    print(f"{name}: default {ll['default']:.4f} | global {ll['global fit']:.4f} | "
          f"archetype {ll['archetype fit']:.4f} | oracle {ll['oracle']:.4f} | "
          f"gain {row['fit gain vs default']:+.4f} [{row['gain 95% low']:+.4f}, {row['gain 95% high']:+.4f}]",
          flush=True)

res = pd.DataFrame(results)
res.to_csv(f"{out}/shift_benchmark.csv", index=False)

W = ["default", "global fit", "archetype fit", "oracle"]
lines = ["# Shift benchmark: trained weights on new populations", "",
         f"Global fit: `{global_csv}`. 200 fresh agents per scenario; every review scored.", "",
         "## log-loss (lower is better)", "",
         "| scenario | reviews | " + " | ".join(W) + " | gain of global fit vs default [95%] | gap closed |",
         "|---|---|" + "---|" * len(W) + "---|---|"]
for r in results:
    lines.append(f"| {r['scenario']} | {r['reviews']} | " +
                 " | ".join(f"{r[w + ' log-loss']:.4f}" for w in W) +
                 f" | {r['fit gain vs default']:+.4f} [{r['gain 95% low']:+.4f}, {r['gain 95% high']:+.4f}]"
                 f" | {r['gap closed']:.0%} |")
for metric, better in (("RMSE", "lower"), ("AUC", "higher")):
    lines += ["", f"## {metric} ({better} is better)", "",
              "| scenario | " + " | ".join(W) + " |", "|---|" + "---|" * len(W)]
    for r in results:
        lines.append(f"| {r['scenario']} | " + " | ".join(f"{r[w + ' ' + metric]:.4f}" for w in W) + " |")
open(f"{out}/shift_benchmark.md", "w").write("\n".join(lines) + "\n")

fig, ax = plt.subplots(figsize=(9, 5.2))
yy = np.arange(len(res))[::-1]
ax.errorbar(res["fit gain vs default"], yy,
            xerr=[res["fit gain vs default"] - res["gain 95% low"], res["gain 95% high"] - res["fit gain vs default"]],
            fmt="o", color="#2a6f97", ecolor="#9fbfd3", capsize=3)
ax.axvline(0, color="#c0392b", lw=1)
ax.set_yticks(yy, res.scenario, fontsize=9)
ax.set_xlabel("log-loss gain of the global fit over default FSRS-6 (right = better, bars = 95%)")
ax.set_title("Do the trained weights still help on different players?", loc="left")
for s in ("top", "right"):
    ax.spines[s].set_visible(False)
fig.tight_layout()
fig.savefig(f"{out}/shift_benchmark.png", dpi=130)
print("\n".join(lines))
