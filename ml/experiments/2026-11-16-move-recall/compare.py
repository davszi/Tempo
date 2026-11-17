"""Score every arm from its saved weights and run the comparisons fixed in PLAN.md.

    python experiments/2026-11-16-move-recall/compare.py --data data/move-recall \
        --results experiments/2026-11-16-move-recall/results --out experiments/2026-11-16-move-recall/results

Reads ``<data>/seed-<s>/{train,holdout}`` and ``<results>/seed-<s>/<arm>/fsrs6_general_parameters.json``.
Scores with the numpy scorer ``tempo_ml.evaluate.metrics.score`` on the app
clock. Writes ``scores.json`` and ``tables.md``.

Version 2 (2026-11-17, after the run): adds the perfect predictor (every
scored review predicted with its hidden true pass chance), the gap closed
against it beside the planned gap against A1c-R, and the pass rate by line
length on test clients. Version 1, run on the cluster, is kept in
``results/compare-v1-cluster/``; the fields it wrote are unchanged.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from tempo_ml.evaluate.metrics import Truth, bce, metrics, predicted_pass, score
from tempo_ml.fsrs.model import DEFAULT_PARAMETERS, line_lengths, load_cards, predict
from tempo_ml.fsrs.train import split_clients

SEEDS = (20261111, 20261121, 20261131)
ARMS = {  # name -> (results subdirectory, link)
    "A1": ("A1", "line"), "A1c": ("A1c", "line"), "A1c-pass": ("A1c-pass", "move"),
    "A1c-acc": ("A1c-acc", "move"), "A1c-R": ("A1c-R", "move"),
    "A1c (60 d)": ("reduced-A1c", "line"), "A1c-pass (60 d)": ("reduced-A1c-pass", "move"),
    "A1c-acc (60 d)": ("reduced-A1c-acc", "move"),
}
COMPARISONS = [  # (question, arm a, arm b): difference = loss(b) - loss(a); negative = b better
    ("Q1 meaning of R", "A1c", "A1c-pass"),
    ("Q2 training target", "A1c-pass", "A1c-acc"),
    ("Q2 training target, 60 days", "A1c-pass (60 d)", "A1c-acc (60 d)"),
    ("Q3 trainer", "A1", "A1c"),
]
N_BOOT = 2000


def per_client_loss(w, cards, link: str) -> pd.Series:
    r = np.nan_to_num(predict(w, cards.t, cards.g, cards.valid), nan=1.0)
    p = predicted_pass(r, cards.m_grid(), link)
    m = cards.loss_mask
    agent = np.broadcast_to(cards.agent[:, None], m.shape)[m]
    return pd.Series(bce(p[m], cards.y[m])).groupby(agent).mean()


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--data", type=Path, required=True)
    ap.add_argument("--results", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    rng = np.random.default_rng(20261116)
    scores, client_loss, weights, by_len_raw = {}, {}, {}, []
    for seed in SEEDS:
        ds = {k: a.data / f"seed-{seed}" / k for k in ("train", "holdout")}
        cards = load_cards(ds["train"] / "sessions.csv", line_lengths(ds["train"]))
        hold = load_cards(ds["holdout"] / "sessions.csv", line_lengths(ds["holdout"]))
        truth, truth_h = Truth(ds["train"]), Truth(ds["holdout"])
        horizon = float(json.loads((ds["train"] / "manifest.json").read_text())["config"]["horizon_days"])
        parts = split_clients(pd.read_csv(ds["train"] / "clients.csv"), 7)
        test = cards.subset(np.isin(cards.agent, sorted(parts["test"])))
        scores[seed] = {"defaults": {"test": score(DEFAULT_PARAMETERS, test, truth, horizon, "line"),
                                     "holdout": score(DEFAULT_PARAMETERS, hold, truth_h, horizon, "line")}}
        client_loss[seed] = {"defaults": per_client_loss(DEFAULT_PARAMETERS, test, "line")}
        perfect = {}
        for part, c, tr in (("test", test, truth), ("holdout", hold, truth_h)):
            m = c.loss_mask
            perfect[part] = metrics(truth_p := tr.p_pass[c.row[m]], c.y[m], truth_p)
        scores[seed]["perfect"] = perfect
        mt = test.loss_mask
        Mv, yv = test.m_grid()[mt], test.y[mt]
        by_len_seed = {}
        for arm, (sub, link) in ARMS.items():
            f = a.results / f"seed-{seed}" / sub / "fsrs6_general_parameters.json"
            if not f.exists():
                continue
            w = np.array(json.loads(f.read_text())["parameters"], float)
            weights.setdefault(arm, {})[seed] = w.tolist()
            scores[seed][arm] = {"test": score(w, test, truth, horizon, link),
                                 "holdout": score(w, hold, truth_h, horizon, link)}
            client_loss[seed][arm] = per_client_loss(w, test, link)
            if arm in ("A1c", "A1c-pass", "A1c-acc"):
                r = np.nan_to_num(predict(w, test.t, test.g, test.valid), nan=1.0)
                by_len_seed[arm] = predicted_pass(r, test.m_grid(), link)[mt]
        rd = np.nan_to_num(predict(DEFAULT_PARAMETERS, test.t, test.g, test.valid), nan=1.0)
        by_len_seed["defaults"] = rd[mt]
        by_len_seed["truth"] = truth.p_pass[test.row[mt]]
        by_len_raw.append((Mv, yv, by_len_seed))

    results = {"scores": {str(k): v for k, v in scores.items()}, "weights": weights, "comparisons": []}
    gap = {}
    for part in ("test", "holdout"):
        for arm in ["A1", *ARMS.keys()]:
            if not all(arm in scores[s] for s in SEEDS):
                continue
            ll = lambda a: np.mean([scores[s][a][part]["log_loss"] for s in SEEDS])
            gap.setdefault(part, {})[arm] = {
                "vs_perfect": float((ll("defaults") - ll(arm)) / (ll("defaults") - ll("perfect"))),
                "vs_A1c_R_planned": float((ll("defaults") - ll(arm)) / (ll("defaults") - ll("A1c-R")))}
    results["gap_closed"] = gap
    M = np.concatenate([b[0] for b in by_len_raw]); Y = np.concatenate([b[1] for b in by_len_raw])
    keys = by_len_raw[0][2].keys()
    P = {k: np.concatenate([b[2][k] for b in by_len_raw]) for k in keys}
    results["by_length_test"] = {}
    for b in sorted(set(np.minimum(M, 13).tolist())):
        sel = np.minimum(M, 13) == b
        results["by_length_test"][str(int(b))] = {"reviews": int(sel.sum()), "observed": float(Y[sel].mean()),
                                                  **{k: float(P[k][sel].mean()) for k in keys}}
    for question, arm_a, arm_b in COMPARISONS:
        if not all(arm_a in client_loss[s] and arm_b in client_loss[s] for s in SEEDS):
            continue
        per_seed = {s: float((client_loss[s][arm_b] - client_loss[s][arm_a]).mean()) for s in SEEDS}
        diff = np.concatenate([(client_loss[s][arm_b] - client_loss[s][arm_a]).to_numpy() for s in SEEDS])
        boot = np.array([diff[rng.integers(0, len(diff), len(diff))].mean() for _ in range(N_BOOT)])
        lo, hi = np.percentile(boot, [2.5, 97.5])
        same_sign = len({np.sign(v) for v in per_seed.values()}) == 1
        excludes = lo > 0 or hi < 0
        verdict = "established" if excludes and same_sign else "inconclusive" if excludes else "no difference shown"
        results["comparisons"].append({"question": question, "a": arm_a, "b": arm_b,
                                       "mean_difference_b_minus_a": float(diff.mean()),
                                       "ci95": [float(lo), float(hi)], "clients": int(len(diff)),
                                       "per_seed": {str(k): v for k, v in per_seed.items()},
                                       "verdict": verdict})
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "scores.json").write_text(json.dumps(results, indent=2) + "\n")

    arms = ["defaults", "perfect"] + [x for x in ARMS if all(x in scores[s] for s in SEEDS)]
    mean = lambda arm, part, key: np.mean([scores[s][arm][part][key] for s in SEEDS])
    lines = ["# Results (mean over the three seeds; app clock)", "",
             "Test log-loss per seed and mean; lower is better. Difference columns: arm b minus arm a.", "",
             "| Arm | " + " | ".join(str(s) for s in SEEDS) + " | Mean | Hold-out mean | RMSE vs true pass chance | AUC | Median abs days error |",
             "|---|" + "---|" * (len(SEEDS) + 5)]
    for arm in arms:
        per = " | ".join(f"{scores[s][arm]['test']['log_loss']:.4f}" for s in SEEDS)
        days = ("—" if arm == "perfect" else
                f"{np.mean([scores[s][arm]['test']['days']['median_abs_error'] for s in SEEDS]):.2f}")
        lines.append(f"| {arm} | {per} | {mean(arm, 'test', 'log_loss'):.4f} | {mean(arm, 'holdout', 'log_loss'):.4f} | "
                     f"{mean(arm, 'test', 'rmse_vs_truth'):.4f} | {mean(arm, 'test', 'auc'):.3f} | {days} |")
    lines += ["", "Gap closed (mean log-loss over the seeds): against the perfect predictor, and against A1c-R as planned.", "",
              "| Arm | Test, vs perfect | Hold-out, vs perfect | Test, vs A1c-R | Hold-out, vs A1c-R |", "|---|---|---|---|---|"]
    for arm in gap.get("test", {}):
        g = lambda part, k: f"{100 * gap[part][arm][k]:.1f}%"
        lines.append(f"| {arm} | {g('test', 'vs_perfect')} | {g('holdout', 'vs_perfect')} | {g('test', 'vs_A1c_R_planned')} | {g('holdout', 'vs_A1c_R_planned')} |")
    pl = lambda part: np.mean([scores[s]["perfect"][part]["log_loss"] for s in SEEDS])
    lines += ["", f"Perfect predictor log-loss: test {pl('test'):.4f}, hold-out {pl('holdout'):.4f}.", "",
              "Pass rate by player moves, test clients of all seeds (13 = 13 or more):", "",
              "| Moves | Reviews | Observed | Hidden pass chance | Untrained | A1c | A1c-pass | A1c-acc |", "|---|---|---|---|---|---|---|---|"]
    for b, e in results["by_length_test"].items():
        lines.append(f"| {b} | {e['reviews']} | {100 * e['observed']:.1f}% | {100 * e['truth']:.1f}% | {100 * e['defaults']:.1f}% | "
                     f"{100 * e['A1c']:.1f}% | {100 * e['A1c-pass']:.1f}% | {100 * e['A1c-acc']:.1f}% |")
    lines += ["", "| Question | a | b | Mean difference (b − a) | 95 % interval | Per seed | Verdict |",
              "|---|---|---|---|---|---|---|"]
    for c in results["comparisons"]:
        per = ", ".join(f"{v:+.4f}" for v in c["per_seed"].values())
        lines.append(f"| {c['question']} | {c['a']} | {c['b']} | {c['mean_difference_b_minus_a']:+.4f} | "
                     f"[{c['ci95'][0]:+.4f}, {c['ci95'][1]:+.4f}] | {per} | {c['verdict']} |")
    (a.out / "tables.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
