"""Fit FSRS-6 on a synthetic session dataset, evaluate, and personalise.

    python -m tempo_ml.fsrs.train --data <generated dir> --out <dir> [--seed N]
        [--target {pass,true}] [--no-personalise]

Protocol:

1. Split clients by archetype into fit (70 %), validation (10 %) and test (20 %).
2. General model: start from FSRS-6 defaults and minimise, on the fit clients,
   either (``--target pass``, default) the mean binary cross-entropy of
   predicted R against session success, or (``--target true``) the mean
   squared error of predicted R against the hidden true chance of a clean
   session ``p_clean`` (L-BFGS-B within the py-fsrs parameter bounds,
   finite-difference gradients). ``--target true`` reads ``ground_truth.csv``
   for the fit clients: it is a diagnostic that real players cannot support.
3. Evaluate on test clients against two baselines: FSRS-6 default parameters,
   and a constant predictor equal to the fit clients' success rate. Metrics:
   log loss, Brier score, RMSE(bins), AUC, RMSE and MAE against ``p_clean``,
   and the error in days (see ``tempo_ml.evaluate.days``).
4. Personalisation (skipped with ``--no-personalise``): for each client, the
   first 60 % of its tested reviews (in time order) fine-tune the general
   parameters with an L2 pull toward them; the last 40 % evaluate. The pull
   strength is chosen on validation clients only, then applied to test clients.
"""

from __future__ import annotations

import argparse
import json
import platform
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import minimize

from ..evaluate.metrics import Truth, bce, metrics, score
from .model import DEFAULT_PARAMETERS, LOWER_BOUNDS, UPPER_BOUNDS, Cards, load_cards, predict

SPAN = UPPER_BOUNDS - LOWER_BOUNDS
LAMBDA_GRID = (0.01, 0.1, 1.0, 10.0)


def objective(w, cards: Cards, mask: np.ndarray, target: np.ndarray | None = None,
              loss: str = "bce", prior=None, lam: float = 0.0) -> float:
    """Mean loss of predicted R against ``target`` (default: pass/fail ``cards.y``)."""
    target = cards.y if target is None else target
    p = predict(w, cards.t, cards.g, cards.valid)
    if loss == "bce":
        value = float(bce(p[mask], target[mask]).mean())
    elif loss == "mse":
        value = float(np.mean((p[mask] - target[mask]) ** 2))
    else:
        raise ValueError(f"unknown loss {loss!r}")
    if prior is not None and lam > 0:
        value += lam * float(np.mean(((w - prior) / SPAN) ** 2))
    return value


def fit(w0, cards: Cards, mask: np.ndarray, target: np.ndarray | None = None, loss: str = "bce",
        prior=None, lam: float = 0.0, maxiter: int = 300,
        ftol: float | None = None, gtol: float | None = None):
    """L-BFGS-B within the FSRS-6 bounds. ``ftol``/``gtol`` optionally tighten
    scipy's stopping tolerances (defaults otherwise): an MSE loss is about 1e-7
    near its optimum, and with the defaults a fit can stop early."""
    options = {"maxiter": maxiter, "eps": 1e-6}
    if ftol is not None:
        options["ftol"] = ftol
    if gtol is not None:
        options["gtol"] = gtol
    res = minimize(
        objective, np.clip(w0, LOWER_BOUNDS, UPPER_BOUNDS), args=(cards, mask, target, loss, prior, lam),
        method="L-BFGS-B", bounds=list(zip(LOWER_BOUNDS, UPPER_BOUNDS)),
        options=options,
    )
    return res.x, {"loss": float(res.fun), "iterations": int(res.nit), "evaluations": int(res.nfev),
                   "converged": bool(res.success), "message": str(res.message)}


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
    ap.add_argument("--target", choices=("pass", "true"), default="pass",
                    help="pass: log-loss on pass/fail; true: MSE on the hidden p_clean (diagnostic)")
    ap.add_argument("--no-personalise", action="store_true", help="skip the per-client fine-tuning step")
    a = ap.parse_args(argv)
    a.out.mkdir(parents=True, exist_ok=True)
    started = time.time()
    log = lambda msg: print(f"[{time.time() - started:7.1f}s] {msg}", flush=True)

    cards = load_cards(a.data / "sessions.csv")
    truth = Truth(a.data)
    gen_manifest = json.loads((a.data / "manifest.json").read_text())
    horizon = float(gen_manifest["config"]["horizon_days"])
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
    if a.target == "pass":
        target, loss = None, "bce"
    else:  # hidden truth, fit clients only (fit_cards holds no other client)
        target, loss = truth.grid(fit_cards, truth.p_clean), "mse"
    log(f"fitting general FSRS-6 parameters on fit clients (target={a.target}, loss={loss}) ...")
    w_gen, info = fit(DEFAULT_PARAMETERS, fit_cards, fit_cards.loss_mask, target=target, loss=loss)
    log(f"done: {info}")

    # ---- evaluation on test clients
    m = test_cards.loss_mask
    y = test_cards.y[m]
    base_rate = float(fit_cards.y[fit_cards.loss_mask].mean())
    results = {
        "target": a.target,
        "loss": loss,
        "test": {
            "constant_base_rate": metrics(np.full(len(y), base_rate), y, truth.p_clean[test_cards.row[m]]),
            "fsrs6_default": score(DEFAULT_PARAMETERS, test_cards, truth, horizon),
            "fsrs6_trained": score(w_gen, test_cards, truth, horizon),
        },
        "test_by_archetype": {},
        "fit": {"fsrs6_trained": score(w_gen, fit_cards, truth, horizon)},
        "optimizer": info,
        "base_rate": base_rate,
    }
    arch_card = np.array([archetype[x] for x in test_cards.agent])
    for arch in sorted(set(arch_card)):
        sub = test_cards.subset(arch_card == arch)
        results["test_by_archetype"][arch] = {
            "fsrs6_default": score(DEFAULT_PARAMETERS, sub, truth, horizon),
            "fsrs6_trained": score(w_gen, sub, truth, horizon),
        }
    log("test: " + json.dumps({k: round(v["log_loss"], 4) for k, v in results["test"].items()}))

    # ---- personalisation: choose lambda on validation clients
    if a.no_personalise:
        results["personalisation"] = "skipped (--no-personalise)"
    else:
        lam_scores = {}
        for lam in LAMBDA_GRID:
            pg, pp, late, _ = personalise(val_cards, w_gen, lam)
            lam_scores[lam] = {"general": float(bce(pg[late], val_cards.y[late]).mean()),
                               "personal": float(bce(pp[late], val_cards.y[late]).mean())}
            log(f"validation lambda={lam}: {lam_scores[lam]}")
        best_lam = min(LAMBDA_GRID, key=lambda l: lam_scores[l]["personal"])
        use_personal = lam_scores[best_lam]["personal"] < lam_scores[best_lam]["general"]

        pg, pp, late, per_agent = personalise(test_cards, w_gen, best_lam)
        yl, tl = test_cards.y[late], truth.p_clean[test_cards.row[late]]
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

    params = {"model": "FSRS-6", "target": a.target, "loss": loss,
              "parameters": [round(float(x), 6) for x in w_gen],
              "default_parameters": DEFAULT_PARAMETERS.tolist(),
              "trained_on": {"data": str(a.data), "clients": len(parts["fit"]),
                             "reviews": int(fit_cards.loss_mask.sum()), "base_rate": base_rate}}
    (a.out / "fsrs6_general_parameters.json").write_text(json.dumps(params, indent=2) + "\n")
    results["split"] = {k: sorted(v) for k, v in parts.items()}
    results["environment"] = {"python": platform.python_version(), "numpy": np.__version__,
                              "pandas": pd.__version__, "platform": platform.platform()}
    results["seconds"] = round(time.time() - started, 1)
    (a.out / "metrics.json").write_text(json.dumps(results, indent=2) + "\n")
    log(f"wrote {a.out}")


if __name__ == "__main__":
    main()
