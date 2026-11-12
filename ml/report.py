"""Sanity report for a generated dataset.

    python report.py data/tempo_v1

Writes <dir>/report.png and <dir>/report.md. Checks that the data looks like
plausible human practice AND that it carries enough signal to learn from:
the oracle (true hidden weights) must beat default FSRS-6 on log-loss; the gap
between the two is the room your optimizer has to improve.
"""
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from tempo_sim.evaluate import metrics, replay
from tempo_sim.fsrs6 import DEFAULT_W

INK, MUTED, GRID = "#1f2933", "#6b7280", "#e5e7eb"
SERIES = ["#2a6f97", "#e07a5f", "#3d9970", "#9b6dc6", "#d4a017"]
GRADE_COL = {1: "#c0392b", 2: "#e6a23c", 3: "#2a6f97", 4: "#3d9970"}


def style(ax, title):
    ax.set_title(title, loc="left", fontsize=11, color=INK, pad=8)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(GRID)
    ax.tick_params(colors=MUTED, labelsize=8)
    ax.grid(axis="y", color=GRID, linewidth=0.6)
    ax.set_axisbelow(True)


def main(d):
    rv = pd.read_csv(os.path.join(d, "reviews.csv"))
    mv = pd.read_csv(os.path.join(d, "moves.csv"))
    truth = pd.read_csv(os.path.join(d, "hidden", "truth.csv"))
    agents = pd.read_csv(os.path.join(d, "hidden", "agents.csv"))
    split = pd.read_csv(os.path.join(d, "split.csv"))
    wcols = [f"w{i}" for i in range(21)]
    true_w = agents.set_index("agent_name")[wcols]

    rv["p_oracle"] = replay(rv, lambda a: true_w.loc[a].values)
    rv["p_default"] = replay(rv, lambda a: DEFAULT_W)
    v = (rv[rv.review_status != "new"].merge(truth, on="review_id")
         .merge(agents[["agent_name", "archetype"]], on="agent_name")
         .merge(split, on="agent_name"))
    v["y"] = (v.grade > 1).astype(int)
    val = v[v.split == "val"]

    res = {
        "oracle (true weights)": metrics(val.y, val.p_oracle),
        "default FSRS-6": metrics(val.y, val.p_default),
        "constant mean": metrics(val.y, np.full(len(val), v[v.split == "train"].y.mean())),
    }

    # ------------------------------------------------------------------ plot
    fig, axs = plt.subplots(2, 3, figsize=(15, 8.5))
    fig.patch.set_facecolor("white")

    ax = axs[0, 0]
    ct = pd.crosstab(v.archetype, v.grade, normalize="index")
    left = np.zeros(len(ct))
    for g in (1, 2, 3, 4):
        vals = ct.get(g, pd.Series(0, index=ct.index)).values
        ax.barh(ct.index, vals, left=left, color=GRADE_COL[g], height=0.6,
                label=["Again", "Hard", "Good", "Easy"][g - 1], edgecolor="white")
        left += vals
    style(ax, "Grade mix by archetype")
    ax.grid(False)
    ax.set_xlim(0, 1)
    ax.legend(ncol=4, fontsize=8, frameon=False, loc="upper center",
              bbox_to_anchor=(0.5, -0.06))

    ax = axs[0, 1]
    ax.hist(v.R_true, bins=np.linspace(0, 1, 41), color=SERIES[0])
    style(ax, "True recall at review time (coverage)")
    ax.set_xlabel("R_true", color=MUTED, fontsize=9)

    ax = axs[0, 2]
    ax.hist(np.log10(v.t_days), bins=40, color=SERIES[0])
    style(ax, "Elapsed days between reviews")
    ticks = [1, 3, 10, 30, 100]
    ax.set_xticks(np.log10(ticks), [str(t) for t in ticks])

    ax = axs[1, 0]
    t = mv.time_ms / 1000
    ax.hist(t[t < 15], bins=60, color=SERIES[0])
    style(ax, "Per-move time (s)")
    ax.axvline(t.median(), color=INK, lw=1, ls="--")
    ax.text(t.median(), ax.get_ylim()[1] * 0.92, f"  median {t.median():.1f}s",
            fontsize=8, color=INK)

    ax = axs[1, 1]
    clean = v[v.grade > 1]
    delay = clean.total_time_ms / clean.n_moves - clean.baseline_ms
    ax.hist(delay[delay < 5000] / 1000, bins=60, color=SERIES[0])
    ax.axvline(0.5, color=INK, lw=1, ls="--")
    ax.axvline(1.8, color=INK, lw=1, ls="--")
    style(ax, "Clean sessions: mean delay per move (s)\nEasy < 0.5 < Good < 1.8 < Hard")

    ax = axs[1, 2]
    for name, col, c in (("oracle", "p_oracle", SERIES[2]), ("default", "p_default", SERIES[1])):
        b = pd.cut(val[col], np.linspace(0, 1, 21))
        g = val.groupby(b, observed=True).agg(p=(col, "mean"), y=("y", "mean"), n=("y", "size"))
        g = g[g.n >= 30]
        ax.plot(g.p, g.y, marker="o", ms=3, color=c, label=name)
    ax.plot([0, 1], [0, 1], color=GRID, lw=1)
    lo = max(0.0, min(val.p_oracle.quantile(0.01), val.p_default.quantile(0.01)) - 0.05)
    ax.set_xlim(lo, 1)
    ax.set_ylim(lo, 1)
    style(ax, "Calibration on val agents")
    ax.set_xlabel("predicted R", color=MUTED, fontsize=9)
    ax.set_ylabel("observed pass rate", color=MUTED, fontsize=9)
    ax.legend(fontsize=8, frameon=False, loc="upper left")

    fig.tight_layout(h_pad=2.5)
    fig.savefig(os.path.join(d, "report.png"), dpi=130)

    # --------------------------------------------------------------- summary
    gm = v.grade.value_counts(normalize=True).sort_index()
    lines = [
        f"# Dataset sanity report: {d}", "",
        f"- agents: {rv.agent_name.nunique()} ({(split.split=='train').sum()} train / {(split.split=='val').sum()} val, split by agent)",
        f"- rows: {len(rv)}  (new {int((rv.review_status=='new').sum())}, review/relearning {len(v)})",
        f"- reviews per agent: median {v.groupby('agent_name').size().median():.0f}",
        f"- grade mix: " + ", ".join(f"{['Again','Hard','Good','Easy'][g-1]} {gm.get(g,0):.1%}" for g in (1, 2, 3, 4)),
        f"- R_true at review: median {v.R_true.median():.3f}, share < 0.7: {(v.R_true<0.7).mean():.1%}",
        f"- per-move time: median {mv.time_ms.median()/1000:.2f}s, p90 {mv.time_ms.quantile(.9)/1000:.2f}s",
        f"- label noise: P(pass | line recalled) {v[v.recalled==1].y.mean():.3f}, P(pass | forgotten) {v[v.recalled==0].y.mean():.3f}",
        "", "## Predicting pass (grade > 1) on val agents", "",
        "| model | log-loss | RMSE(bins) | AUC |", "|---|---|---|---|",
    ]
    for k, m in res.items():
        lines.append(f"| {k} | {m['log_loss']:.4f} | {m['rmse_bins']:.4f} | {m['auc']:.3f} |")
    lines += ["", "Your optimizer should land between *default* and *oracle*."]
    with open(os.path.join(d, "report.md"), "w") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "data/tempo_v1")
