"""Fit one global FSRS-6 weight vector on the train agents and compare it with
the hidden truth.

    python fit_global.py data/tempo_v1 [runs/2026-11-11-first-training]

Writes fitted_global.csv and fit.txt into the output folder (default: the
data folder itself; locked datasets need a separate folder).
"""
import os
import math
import sys

import pandas as pd
from fsrs import Optimizer

from tempo_sim.evaluate import metrics, param_recovery, replay, to_fsrs_review_logs
from tempo_sim.fsrs6 import DEFAULT_W

# Every line starts with a learn event graded 3, so only w2 sets the initial
# stability: w0, w1, w3 never touch the loss. w19 only acts on same-day
# reviews, which the simulator never produces. w17 and w18 also cap the
# stability after a lapse (min(long_term, S / exp(w17 * w18))), so they get a
# weak signal from Again reviews only.
NOT_IDENTIFIABLE = {0, 1, 3, 19}
WEAK = {17, 18}

d = sys.argv[1]
out_dir = sys.argv[2] if len(sys.argv) > 2 else d
os.makedirs(out_dir, exist_ok=True)
rv = pd.read_csv(f"{d}/reviews.csv")
split = pd.read_csv(f"{d}/split.csv")
agents = pd.read_csv(f"{d}/hidden/agents.csv")  # evaluation only, never training

train_ids = split.loc[split.split == "train", "agent_name"]
train = rv[rv.agent_name.isin(train_ids)]

logs = to_fsrs_review_logs(train)
w = Optimizer(logs).compute_optimal_parameters(verbose=False)

wcols = [f"w{i}" for i in range(21)]
pd.DataFrame([w], columns=wcols).to_csv(f"{out_dir}/fitted_global.csv", index=False)
fitted = pd.DataFrame([{"agent_name": a, **dict(zip(wcols, w))} for a in agents.agent_name])

rec = param_recovery(fitted, agents)
rec["default"] = DEFAULT_W
rec["identifiable"] = ["no" if i in NOT_IDENTIFIABLE else "weak" if i in WEAK else "yes"
                       for i in range(21)]

# Initial difficulty after a grade-3 learn is w4 - exp(2*w5) + 1: only this
# combination is identified, not w4 and w5 separately.
t = agents[wcols].median()
d0_true = t.w4 - math.exp(2 * t.w5) + 1
d0_fit = w[4] - math.exp(2 * w[5]) + 1

lines = [
    f"# Global fit on {d} ({len(train_ids)} train agents, {len(train)} rows)",
    "",
    rec.rename(columns={"true_median": "true", "fit_median": "fitted"})
       .round(4).to_string(index=False),
    "",
    f"D0 after learn = w4 - exp(2*w5) + 1: true {d0_true:.4f}, fitted {d0_fit:.4f}, "
    f"rel err {abs(d0_fit - d0_true) / abs(d0_true):.4f}",
]
ok = rec[rec.identifiable == "yes"]
lines.append(f"identifiable weights: median rel err {ok.median_rel_err.median():.4f}, "
             f"worst {ok.loc[ok.median_rel_err.idxmax(), 'weight']} "
             f"{ok.median_rel_err.max():.4f}")
# The real test: predict pass (grade > 1) on the val agents the fit never saw.
val_ids = set(split.loc[split.split == "val", "agent_name"])
val = rv[rv.agent_name.isin(val_ids)].copy()
true_w = agents.set_index("agent_name")[wcols]
lines += ["", "## Predicting pass (grade > 1) on val agents", "",
          "| weights | log-loss | RMSE(bins) | AUC |", "|---|---|---|---|"]
for name, wf in (("true (oracle)", lambda a: true_w.loc[a].values),
                 ("fitted", lambda a: w),
                 ("default", lambda a: DEFAULT_W)):
    val["p"] = replay(val, wf)
    v = val[val.review_status != "new"]
    m = metrics((v.grade > 1).astype(int), v.p)
    lines.append(f"| {name} | {m['log_loss']:.4f} | {m['rmse_bins']:.4f} | {m['auc']:.3f} |")

out = "\n".join(lines)
print(out)
with open(f"{out_dir}/fit.txt", "w") as f:
    f.write(out + "\n")
