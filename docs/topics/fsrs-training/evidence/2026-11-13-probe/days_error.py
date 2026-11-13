"""Accuracy in days on tempo_v1 val players.

After every session (learn or review) the app picks the next review day: the
day the predicted chance falls to the player's target retention. Compare that
with the ideal day from the player's hidden memory (true weights + true S).
error = predicted days - true days  (negative = model thinks the player forgets
sooner than they really do = review comes too early).
"""
import csv
import sys
from collections import defaultdict

import numpy as np

root = sys.argv[1]
sys.path.insert(0, root)
from tempo_sim.fsrs6 import DEFAULT_W, FSRS6  # noqa: E402

d = f"{root}/data/tempo_v1"
split = {r["agent_name"]: r["split"] for r in csv.DictReader(open(f"{d}/split.csv"))}
wcols = [f"w{i}" for i in range(21)]
agents = {r["agent_name"]: r for r in csv.DictReader(open(f"{d}/hidden/agents.csv"))}
fitted = [float(x) for x in next(csv.DictReader(
    open(f"{root}/runs/2026-11-11-first-training/fitted_global.csv"))).values()]
s_true = {int(r["review_id"]): float(r["S_after"]) for r in csv.DictReader(open(f"{d}/hidden/truth.csv"))}

rows = [r for r in csv.DictReader(open(f"{d}/reviews.csv")) if split[r["agent_name"]] == "val"]
for r in rows:
    r["day"] = int(r["day"]); r["review_id"] = int(r["review_id"]); r["grade"] = int(r["grade"])
rows.sort(key=lambda r: (r["agent_name"], r["line_id"], r["day"], r["review_id"]))
groups = defaultdict(list)
for r in rows:
    groups[(r["agent_name"], r["line_id"])].append(r)


def intervals(w_for):
    """(review_id, status, predicted_days, true_days) after every session."""
    out = []
    for (agent, _), grp in groups.items():
        a = agents[agent]
        model, truth = FSRS6(w_for(agent)), FSRS6([float(a[c]) for c in wcols])
        dr = float(a["desired_retention"])
        st, last = None, None
        for r in grp:
            if st is None:
                st = model.init_state(r["grade"])
            else:
                st = model.step(st, r["day"] - last, r["grade"])
            last = r["day"]
            out.append((r["review_status"],
                        model.interval_for(st.stability, dr),
                        truth.interval_for(s_true[r["review_id"]], dr)))
    return out


def report(name, res):
    st = np.array([x[0] for x in res]); p = np.array([x[1] for x in res]); t = np.array([x[2] for x in res])
    e = p - t
    print(f"\n{name}  ({len(e)} scheduling decisions)")
    print(f"  mean error   {e.mean():+6.2f} days   median {np.median(e):+6.2f} days   "
          f"mean |error| {np.abs(e).mean():5.2f} days   median |error| {np.median(np.abs(e)):5.2f} days")
    print(f"  median relative error {np.median(e / t):+6.1%}   share too early {np.mean(e < 0):5.1%}")
    for label, s in (("after learning", st == "new"), ("after a review", st != "new")):
        print(f"    {label:16s} n={s.sum():6d}  true interval median {np.median(t[s]):5.1f} d  "
              f"mean error {e[s].mean():+6.2f} d  median {np.median(e[s]):+6.2f} d  "
              f"mean |err| {np.abs(e[s]).mean():5.2f} d  median rel {np.median(e[s] / t[s]):+6.1%}")
    for lo, hi in ((0, 7), (7, 30), (30, 1e9)):
        s = (t >= lo) & (t < hi)
        print(f"    true interval {lo:>2.0f}-{'' if hi > 1e8 else f'{hi:.0f}':>3s} d  n={s.sum():6d}  "
              f"mean error {e[s].mean():+6.2f} d  median {np.median(e[s]):+6.2f} d  "
              f"mean |err| {np.abs(e[s]).mean():5.2f} d  median rel {np.median(e[s] / t[s]):+6.1%}")
    s = t >= 30
    print("    30+ d band, true  days p10/p50/p90/max:", np.percentile(t[s], [10, 50, 90, 100]).round(0))
    print("    30+ d band, model days p10/p50/p90/max:", np.percentile(p[s], [10, 50, 90, 100]).round(0))


report("DEFAULT weights", intervals(lambda a: DEFAULT_W))
report("TRAINED weights", intervals(lambda a: fitted))
