"""Light personalisation: adjust only the decay C (w20) per player.

    python experiments/personal_light.py data/tempo_v1 runs/2026-11-11-first-training

py-fsrs refuses to fit fewer than 512 reviews (it returns the default
weights), and a player has ~56 reviews after 4 months, so a full personal
fit is out of reach. Here each val agent keeps the global weights and only C
is chosen on the agent's first 70% of review days, by minimising
    sum of log-loss + (ln(C / C_global))^2 / (2 * prior_sd^2)
over a grid. prior_sd = inf means no pull towards the global value. Scored
on the last 30%, the same reviews as experiments/personal.py.
Writes personal_light.txt.
"""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tempo_sim.evaluate import metrics, replay  # noqa: E402
from tempo_sim.fsrs6 import DEFAULT_W  # noqa: E402

d, out = sys.argv[1], sys.argv[2]
rv = pd.read_csv(f"{d}/reviews.csv")
split = pd.read_csv(f"{d}/split.csv")
agents = pd.read_csv(f"{d}/hidden/agents.csv").set_index("agent_name")
wcols = [f"w{i}" for i in range(21)]
wg = pd.read_csv(f"{out}/fitted_global.csv")[wcols].iloc[0].to_numpy()
grid = np.clip(wg[20] * np.exp(np.linspace(-1.2, 1.2, 25)), 0.1, 0.8)
priors = {"C, no prior": np.inf, "C, prior sd 0.5": 0.5, "C, prior sd 0.25": 0.25}


def nll(y, p):
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return float(-(y * np.log(p) + (1 - y) * np.log(1 - p)).sum())


rows, chosen = [], []
for a in split.loc[split.split == "val", "agent_name"]:
    h = rv[rv.agent_name == a]
    cut = h.day.min() + 0.7 * (h.day.max() - h.day.min())
    fit_m = ((h.day <= cut) & (h.review_status != "new")).to_numpy()
    sc_m = ((h.day > cut) & (h.review_status != "new")).to_numpy()
    y = (h.grade > 1).astype(int).to_numpy()
    preds = []
    for c in grid:
        w = wg.copy()
        w[20] = c
        preds.append(replay(h, lambda _: w).to_numpy())
    losses = np.array([nll(y[fit_m], p[fit_m]) for p in preds])
    out_row = {"y": y[sc_m], "global": replay(h, lambda _: wg).to_numpy()[sc_m],
               "default": replay(h, lambda _: DEFAULT_W).to_numpy()[sc_m],
               "oracle": replay(h, lambda _: agents.loc[a, wcols].to_numpy()).to_numpy()[sc_m]}
    ch = {"agent_name": a, "archetype": agents.loc[a, "archetype"], "C_true": agents.loc[a, "w20"]}
    for name, sd in priors.items():
        pen = 0 if np.isinf(sd) else np.log(grid / wg[20]) ** 2 / (2 * sd ** 2)
        k = int(np.argmin(losses + pen))
        out_row[name] = preds[k][sc_m]
        ch[name] = grid[k]
    rows.append(pd.DataFrame({"agent_name": a, "archetype": ch["archetype"], **out_row}))
    chosen.append(ch)

r = pd.concat(rows)
ch = pd.DataFrame(chosen)
models = ["default", "global", *priors, "oracle"]
lines = [f"# Light personalisation (only C) on {d}",
         f"global C = {wg[20]:.3f}; val agents {r.agent_name.nunique()}, scored reviews {len(r)}", "",
         "| weights | log-loss | RMSE(bins) | AUC |", "|---|---|---|---|"]
for m in models:
    x = metrics(r.y, r[m])
    lines.append(f"| {m} | {x['log_loss']:.4f} | {x['rmse_bins']:.4f} | {x['auc']:.3f} |")
lines += ["", "log-loss by archetype:", ""]
by = r.groupby("archetype").apply(lambda g: pd.Series({m: metrics(g.y, g[m])["log_loss"] for m in models}),
                                  include_groups=False)
lines.append(by.round(4).to_string())
lines += ["", "chosen C (median) by archetype vs true C:", ""]
lines.append(ch.groupby("archetype")[["C_true", *priors]].median().round(3).to_string())
open(f"{out}/personal_light.txt", "w").write("\n".join(lines) + "\n")
print("\n".join(lines))
