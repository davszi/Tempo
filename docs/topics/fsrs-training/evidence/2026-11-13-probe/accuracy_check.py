"""Score default / fitted / oracle FSRS-6 weights on tempo_v1 val agents.

Re-implements tempo_sim.evaluate.replay without pandas, then reports the
repo's metrics (log-loss, RMSE(bins), AUC) as a sanity check, plus:
  - Brier = MSE of predicted p vs observed pass (0/1)
  - MSE / RMSE / MAE of predicted p vs hidden true R (truth.csv)
  - classification accuracy at threshold 0.5 and the always-pass baseline
Usage: python accuracy_check.py <ml_1000bots dir>
"""
import csv
import math
import sys
from collections import defaultdict

import numpy as np

root = sys.argv[1]
sys.path.insert(0, root)
from tempo_sim.fsrs6 import DEFAULT_W, FSRS6  # noqa: E402

d = f"{root}/data/tempo_v1"
split = {r["agent_name"]: r["split"] for r in csv.DictReader(open(f"{d}/split.csv"))}
wcols = [f"w{i}" for i in range(21)]
true_w = {r["agent_name"]: [float(r[c]) for c in wcols]
          for r in csv.DictReader(open(f"{d}/hidden/agents.csv"))}
fitted = [float(x) for x in next(csv.DictReader(
    open(f"{root}/runs/2026-11-11-first-training/fitted_global.csv"))).values()]
r_true = {}
for r in csv.DictReader(open(f"{d}/hidden/truth.csv")):
    if r["R_true"]:
        r_true[int(r["review_id"])] = float(r["R_true"])

rows = [r for r in csv.DictReader(open(f"{d}/reviews.csv")) if split[r["agent_name"]] == "val"]
for r in rows:
    r["day"] = int(r["day"]); r["review_id"] = int(r["review_id"]); r["grade"] = int(r["grade"])
rows.sort(key=lambda r: (r["agent_name"], r["line_id"], r["day"], r["review_id"]))
groups = defaultdict(list)
for r in rows:
    groups[(r["agent_name"], r["line_id"])].append(r)


def replay(weights_for):
    out, cache = {}, {}
    for (agent, _), grp in groups.items():
        m = cache.setdefault(agent, FSRS6(weights_for(agent)))
        st, last = None, None
        for r in grp:
            if st is None:
                st = m.init_state(r["grade"])
            else:
                t = r["day"] - last
                out[r["review_id"]] = m.retrievability(t, st.stability)
                st = m.step(st, t, r["grade"])
            last = r["day"]
    return out


scored = [r for r in rows if r["review_status"] != "new"]
ids = [r["review_id"] for r in scored]
y = np.array([1.0 if r["grade"] > 1 else 0.0 for r in scored])
R = np.array([r_true[i] for i in ids])
print(f"val reviews scored: {len(y)}, observed pass rate: {y.mean():.4f}, mean true R: {R.mean():.4f}\n")


def auc(p, y):
    order = np.argsort(p, kind="mergesort")
    ranks = np.empty(len(p)); ranks[order] = np.arange(1, len(p) + 1)
    _, inv, cnt = np.unique(p, return_inverse=True, return_counts=True)
    ranks = np.bincount(inv, ranks)[inv] / cnt[inv]
    n1, n0 = y.sum(), len(y) - y.sum()
    return (ranks[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)


def rmse_bins(p, y, n_bins=20):
    b = np.minimum((p * n_bins).astype(int), n_bins - 1)
    num = den = 0.0
    for k in np.unique(b):
        s = b == k
        num += s.sum() * (y[s].mean() - p[s].mean()) ** 2; den += s.sum()
    return math.sqrt(num / den)


preds = {
    "always pass (p=1)": np.ones_like(y),
    "constant = pass rate": np.full_like(y, y.mean()),
    "default FSRS-6": None, "global fit": None, "oracle (true w)": None,
}
wf = {"default FSRS-6": lambda a: DEFAULT_W, "global fit": lambda a: fitted,
      "oracle (true w)": lambda a: true_w[a]}
for k, f in wf.items():
    o = replay(f); preds[k] = np.array([o[i] for i in ids])

hdr = f"{'predictor':22s} {'logloss':>8s} {'RMSEbin':>8s} {'AUC':>6s} {'Brier':>7s} {'MSE_R':>8s} {'RMSE_R':>7s} {'MAE_R':>7s} {'acc@.5':>7s} {'meanP':>6s}"
print(hdr); print("-" * len(hdr))
for k, p in preds.items():
    pc = np.clip(p, 1e-6, 1 - 1e-6)
    ll = -np.mean(y * np.log(pc) + (1 - y) * np.log(1 - pc))
    print(f"{k:22s} {ll:8.4f} {rmse_bins(pc, y):8.4f} {auc(pc, y):6.3f} "
          f"{np.mean((p - y) ** 2):7.4f} {np.mean((p - R) ** 2):8.5f} "
          f"{math.sqrt(np.mean((p - R) ** 2)):7.4f} {np.mean(np.abs(p - R)):7.4f} "
          f"{np.mean((p >= 0.5) == (y == 1)):7.4f} {p.mean():6.3f}")

# Brier decomposition check: Brier = MSE_vs_R + irreducible noise E[R(1-R)]
print(f"\nirreducible Brier floor E[R(1-R)] = {np.mean(R * (1 - R)):.4f}")
