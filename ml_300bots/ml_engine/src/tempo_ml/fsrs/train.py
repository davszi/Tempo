"""Fit FSRS-6 on a synthetic session dataset, evaluate, and personalise.

    python -m tempo_ml.fsrs.train --data <generated dir> --out <dir> [--seed N]

Protocol (fixed in the experiment README before running):

1. Split clients by archetype into fit (70 %), validation (10 %) and test (20 %).
2. General model: start from FSRS-6 defaults, minimise mean binary cross-entropy
   of predicted R vs session success on the fit clients (L-BFGS-B within the
   py-fsrs parameter bounds, finite-difference gradients).
3. Evaluate on test clients against two baselines: FSRS-6 default parameters,
   and a constant predictor equal to the fit clients' success rate. Metrics:
   log loss, Brier score, AUC, and mean absolute error against the generator's
   hidden true clean-session probability p_clean = R_move ** M.
4. Personalisation: for each client, the first 60 % of its tested reviews
   (in time order) fine-tune the general parameters with an L2 pull toward
   them; the last 40 % evaluate. The pull strength is chosen on validation
   clients only, then applied to test clients.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import minimize

from .data import Cards, load_cards
from .model import DEFAULT_PARAMETERS, LOWER_BOUNDS, UPPER_BOUNDS, predict

EPS = 1e-6
SPAN = UPPER_BOUNDS - LOWER_BOUNDS
LAMBDA_GRID = (0.01, 0.1, 1.0, 10.0)


def bce(p: np.ndarray, y: np.ndarray) -> np.ndarray:
    p = np.clip(p, EPS, 1 - EPS)
    return -(y * np.log(p) + (1 - y) * np.log(1 - p))


def objective(w, cards: Cards, mask: np.ndarray, prior=None, lam: float = 0.0) -> float:
    p = predict(w, cards.t, cards.g, cards.valid)
    loss = float(bce(p[mask], cards.y[mask]).mean())
    if prior is not None and lam > 0:
        loss += lam * float(np.mean(((w - prior) / SPAN) ** 2))
    return loss


def fit(w0, cards: Cards, mask: np.ndarray, prior=None, lam: float = 0.0, maxiter: int = 300):
    res = minimize(
        objective, np.clip(w0, LOWER_BOUNDS, UPPER_BOUNDS), args=(cards, mask, prior, lam),
        method="L-BFGS-B", bounds=list(zip(LOWER_BOUNDS, UPPER_BOUNDS)),
        options={"maxiter": maxiter, "eps": 1e-6},
    )
    return res.x, {"loss": float(res.fun), "iterations": int(res.nit), "evaluations": int(res.nfev),
                   "converged": bool(res.success), "message": str(res.message)}


def auc(p: np.ndarray, y: np.ndarray) -> float:
    order = np.argsort(p, kind="mergesort")
    ranks = np.empty(len(p))
    ranks[order] = np.arange(1, len(p) + 1)
    # average ranks for ties
    _, inv, counts = np.unique(p, return_inverse=True, return_counts=True)
    ranks = np.bincount(inv, ranks)[inv] / counts[inv]
    pos = y == 1
    n_pos, n_neg = pos.sum(), (~pos).sum()
    return float((ranks[pos].sum() - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg))


def metrics(p: np.ndarray, y: np.ndarray, truth: np.ndarray | None = None) -> dict:
    out = {
        "reviews": int(len(y)),
        "log_loss": float(bce(p, y).mean()),
        "brier": float(np.mean((p - y) ** 2)),
        "auc": auc(p, y),
        "mean_predicted": float(p.mean()),
        "observed_success": float(y.mean()),
    }
    if truth is not None:
        out["mae_vs_true_p_clean"] = float(np.mean(np.abs(p - truth)))
    return out


def split_clients(clients: pd.DataFrame, seed: int) -> dict[str, set[str]]:
    rng = np.random.default_rng(seed)
    parts = {"fit": set(), "validation": set(), "test": set()}
    for _, grp in clients.groupby("archetype", sort=True):
        names = grp["agent_name"].to_numpy()[rng.permutation(len(grp))]
        n_test, n_val = round(0.2 * len(names)), round(0.1 * len(names))
        parts["test"].update(names[:n_test])
        parts["validation"].update(names[n_test:n_test + n_val])
        parts["fit"].update(names[n_test + n_val:])
    return parts


def time_split(cards: Cards, frac: float = 0.6):
    """Per agent: first ``frac`` of tested reviews (by CSV row = time order) vs the rest."""
    early = np.zeros_like(cards.loss_mask)
    late = np.zeros_like(cards.loss_mask)
    for a in np.unique(cards.agent):
        sel = cards.agent == a
        m = cards.loss_mask & sel[:, None]
        rows = np.sort(cards.row[m])
        if len(rows) < 10:
            continue
        cut = rows[int(frac * len(rows))]
        early |= m & (cards.row < cut)
        late |= m & (cards.row >= cut)
    return early, late


def personalise(cards: Cards, w_general, lam: float):
    """Fine-tune per agent on its early reviews; return predictions for every card."""
    early, late = time_split(cards)
    p_gen = predict(w_general, cards.t, cards.g, cards.valid)
    p_per = p_gen.copy()
    per_agent = []
    for a in np.unique(cards.agent):
        sel = cards.agent == a
        sub = cards.subset(sel)
        e, l = early[sel], late[sel]
        if e.sum() < 10 or l.sum() < 5:
            continue
        w_a, info = fit(w_general, sub, e, prior=w_general, lam=lam, maxiter=100)
        p_a = predict(w_a, sub.t, sub.g, sub.valid)
        p_per[sel] = p_a
        per_agent.append({
            "agent_name": a, "early_reviews": int(e.sum()), "late_reviews": int(l.sum()),
            "late_log_loss_general": float(bce(p_gen[sel][l], sub.y[l]).mean()),
            "late_log_loss_personal": float(bce(p_a[l], sub.y[l]).mean()),
            "iterations": info["iterations"],
        })
    return p_gen, p_per, late, pd.DataFrame(per_agent)


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="Fit FSRS-6 on a synthetic session dataset")
    ap.add_argument("--data", type=Path, required=True, help="directory written by the generator")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--seed", type=int, default=7)
    a = ap.parse_args(argv)
    a.out.mkdir(parents=True, exist_ok=True)
    started = time.time()
    log = lambda msg: print(f"[{time.time() - started:7.1f}s] {msg}", flush=True)

    cards = load_cards(a.data / "sessions.csv")
    truth_all = pd.read_csv(a.data / "ground_truth.csv", usecols=["p_clean"])["p_clean"].to_numpy()
    clients = pd.read_csv(a.data / "clients.csv")
    archetype = dict(zip(clients["agent_name"], clients["archetype"]))
    parts = split_clients(clients, a.seed)
    in_part = {k: np.isin(cards.agent, sorted(v)) for k, v in parts.items()}
    log(f"{len(cards.agent)} cards, {cards.n_reviews} tested reviews; "
        + ", ".join(f"{k}: {len(v)} clients / {int(cards.loss_mask[in_part[k]].sum())} reviews" for k, v in parts.items()))

    fit_cards = cards.subset(in_part["fit"])
    test_cards = cards.subset(in_part["test"])
    val_cards = cards.subset(in_part["validation"])

    # ---- general model
    log("fitting general FSRS-6 parameters on fit clients ...")
    w_gen, info = fit(DEFAULT_PARAMETERS, fit_cards, fit_cards.loss_mask)
    log(f"done: {info}")

    # ---- evaluation on test clients
    m = test_cards.loss_mask
    y = test_cards.y[m]
    truth = truth_all[test_cards.row[m]]
    base_rate = float(fit_cards.y[fit_cards.loss_mask].mean())
    p_def = predict(DEFAULT_PARAMETERS, test_cards.t, test_cards.g, test_cards.valid)
    p_gen = predict(w_gen, test_cards.t, test_cards.g, test_cards.valid)
    results = {
        "test": {
            "constant_base_rate": metrics(np.full(len(y), base_rate), y, truth),
            "fsrs6_default": metrics(p_def[m], y, truth),
            "fsrs6_trained": metrics(p_gen[m], y, truth),
        },
        "test_by_archetype": {},
        "fit": {"fsrs6_trained": metrics(predict(w_gen, fit_cards.t, fit_cards.g, fit_cards.valid)[fit_cards.loss_mask],
                                         fit_cards.y[fit_cards.loss_mask])},
        "optimizer": info,
    }
    arch_card = np.array([archetype[x] for x in test_cards.agent])
    for arch in sorted(set(arch_card)):
        mm = m & (arch_card == arch)[:, None]
        yy, tt = test_cards.y[mm], truth_all[test_cards.row[mm]]
        results["test_by_archetype"][arch] = {
            "fsrs6_default": metrics(p_def[mm], yy, tt),
            "fsrs6_trained": metrics(p_gen[mm], yy, tt),
        }
    log("test: " + json.dumps({k: round(v["log_loss"], 4) for k, v in results["test"].items()}))

    # ---- personalisation: choose lambda on validation clients
    lam_scores = {}
    for lam in LAMBDA_GRID:
        pg, pp, late, _ = personalise(val_cards, w_gen, lam)
        lam_scores[lam] = {"general": float(bce(pg[late], val_cards.y[late]).mean()),
                           "personal": float(bce(pp[late], val_cards.y[late]).mean())}
        log(f"validation lambda={lam}: {lam_scores[lam]}")
    best_lam = min(LAMBDA_GRID, key=lambda l: lam_scores[l]["personal"])
    use_personal = lam_scores[best_lam]["personal"] < lam_scores[best_lam]["general"]

    pg, pp, late, per_agent = personalise(test_cards, w_gen, best_lam)
    yl, tl = test_cards.y[late], truth_all[test_cards.row[late]]
    results["personalisation"] = {
        "lambda_grid_validation": {str(k): v for k, v in lam_scores.items()},
        "chosen_lambda": best_lam,
        "validation_says_personalise": use_personal,
        "test_late_reviews": {
            "fsrs6_default": metrics(predict(DEFAULT_PARAMETERS, test_cards.t, test_cards.g, test_cards.valid)[late], yl, tl),
            "fsrs6_general": metrics(pg[late], yl, tl),
            "fsrs6_personalised": metrics(pp[late], yl, tl),
        },
        "clients_improved": int((per_agent.late_log_loss_personal < per_agent.late_log_loss_general).sum()),
        "clients": int(len(per_agent)),
    }
    per_agent["archetype"] = per_agent.agent_name.map(archetype)
    per_agent.to_csv(a.out / "personalisation_test_clients.csv", index=False)
    log("personalisation (test, late reviews): " + json.dumps(
        {k: round(v["log_loss"], 4) for k, v in results["personalisation"]["test_late_reviews"].items()}))

    params = {"model": "FSRS-6", "parameters": [round(float(x), 6) for x in w_gen],
              "default_parameters": DEFAULT_PARAMETERS.tolist(),
              "trained_on": {"data": str(a.data), "clients": len(parts["fit"]),
                             "reviews": int(fit_cards.loss_mask.sum())}}
    (a.out / "fsrs6_general_parameters.json").write_text(json.dumps(params, indent=2) + "\n")
    results["split"] = {k: sorted(v) for k, v in parts.items()}
    results["seconds"] = round(time.time() - started, 1)
    (a.out / "metrics.json").write_text(json.dumps(results, indent=2) + "\n")
    log(f"wrote {a.out}")


if __name__ == "__main__":
    main()
