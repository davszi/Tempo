"""Fit FSRS-6 on a synthetic session dataset, evaluate, and personalise.

    python -m tempo_ml.fsrs.train --data <generated dir> --out <dir> [--seed N]
        [--arm {line,pass,accuracy,true-recall}] [--device {auto,cpu,cuda}]
        [--clock {app,exact}] [--no-personalise]

Arms (move-recall record, section 3.4; training approaches record):

- ``line`` (A1c): R is the chance of passing the line; log-loss of R against
  pass/fail (grade > 1).
- ``pass`` (A1c-pass): R is the recall of one move; log-loss of
  ``p_pass(R, M)`` against pass/fail.
- ``accuracy`` (A1c-acc): R is the recall of one move; binary cross-entropy of
  R against the review's accuracy (M - k) / M, weighted by M, i.e. the binomial
  likelihood of the mistakes.
- ``true-recall`` (A1c-R): as ``accuracy`` with the hidden per-move recall as
  target. Reads ``ground_truth.csv`` for the fit clients: a simulator-only
  reference that real players cannot support.

Protocol:

1. Split clients by archetype into fit (70 %), validation (10 %) and test (20 %).
2. General model: start from the FSRS-6 defaults and minimise the arm's mean
   loss on the fit clients with L-BFGS-B within the py-fsrs parameter bounds.
   The FSRS-6 replay and its exact gradient are computed in torch
   (``torch_model.py``) on the GPU when available.
3. Evaluate on test clients against two baselines, the FSRS-6 defaults and a
   constant equal to the fit clients' pass rate, with
   ``tempo_ml.evaluate.metrics.score`` (numpy, independent of the torch code).
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
import scipy
import torch
from scipy.optimize import minimize

from ..evaluate.metrics import Truth, bce, metrics, predicted_pass, score
from ..pass_chance import binomial_terms, p_pass
from .model import DEFAULT_PARAMETERS, LOWER_BOUNDS, UPPER_BOUNDS, Cards, line_lengths, load_cards, predict
from .torch_model import DTYPE, default_device, replay

SPAN = UPPER_BOUNDS - LOWER_BOUNDS
LAMBDA_GRID = (0.01, 0.1, 1.0, 10.0)
EPS = 1e-6
ARMS = {  # arm -> (link, target)
    "line": ("line", "pass"),
    "pass": ("move", "pass"),
    "accuracy": ("move", "accuracy"),
    "true-recall": ("move", "true-recall"),
}


class Objective:
    """Mean loss of an arm on the masked reviews of ``cards``, with its exact gradient.

    ``target`` is required for ``true-recall`` (hidden per-move recall laid
    out like the cards' arrays) and ignored otherwise.
    """

    def __init__(self, cards: Cards, mask: np.ndarray, arm: str, target: np.ndarray | None = None,
                 prior=None, lam: float = 0.0, device: torch.device | None = None):
        if arm not in ARMS:
            raise ValueError(f"unknown arm {arm!r}")
        self.link, kind = ARMS[arm]
        dev = self.device = device or default_device()
        as_t = lambda a, dt=DTYPE: torch.as_tensor(np.ascontiguousarray(a), dtype=dt, device=dev)
        self.t, self.g = as_t(cards.t), as_t(np.where(cards.valid, cards.g, 3))
        self.valid = as_t(cards.valid, torch.bool)
        self.mask = as_t(mask, torch.bool)
        mg = cards.m_grid()[mask]
        if self.link == "move" and (mg <= 0).any():
            raise ValueError("per-move arms need every card's line length M")
        self.m = as_t(mg)
        self.coef = as_t(binomial_terms(mg)) if self.link == "move" else None
        if kind == "pass":
            self.y, self.weight = as_t(cards.y[mask]), None
        elif kind == "accuracy":
            self.y, self.weight = as_t(cards.acc[mask]), self.m
        else:
            if target is None:
                raise ValueError("true-recall needs the hidden per-move recall")
            self.y, self.weight = as_t(target[mask]), self.m
        self.prior = None if prior is None else as_t(prior)
        self.span = as_t(SPAN)
        self.lam = lam
        self.calls = 0

    def loss(self, w: torch.Tensor) -> torch.Tensor:
        r, _ = replay(w, self.t, self.g, self.valid)
        r = r[self.mask]
        p = p_pass(r, self.m, self.coef) if (self.link == "move" and self.weight is None) else r
        p = p.clamp(EPS, 1 - EPS)
        per = -(self.y * torch.log(p) + (1 - self.y) * torch.log(1 - p))
        value = per.mean() if self.weight is None else (per * self.weight).sum() / self.weight.sum()
        if self.prior is not None and self.lam > 0:
            value = value + self.lam * (((w - self.prior) / self.span) ** 2).mean()
        return value

    def __call__(self, w_np: np.ndarray):
        self.calls += 1
        w = torch.tensor(w_np, dtype=DTYPE, device=self.device, requires_grad=True)
        value = self.loss(w)
        value.backward()
        return float(value.detach().cpu()), w.grad.detach().cpu().numpy().astype(float)


def fit(w0, cards: Cards, mask: np.ndarray, arm: str = "line", target: np.ndarray | None = None,
        prior=None, lam: float = 0.0, maxiter: int = 2000, ftol: float = 1e-12, gtol: float = 1e-7,
        device: torch.device | None = None):
    """L-BFGS-B within the FSRS-6 bounds, exact gradients from torch.

    Stops when the relative loss change is below ``ftol``, the projected
    gradient below ``gtol``, or after ``maxiter`` iterations.
    """
    obj = Objective(cards, mask, arm, target, prior, lam, device)
    res = minimize(obj, np.clip(np.asarray(w0, float), LOWER_BOUNDS, UPPER_BOUNDS), jac=True,
                   method="L-BFGS-B", bounds=list(zip(LOWER_BOUNDS, UPPER_BOUNDS)),
                   options={"maxiter": maxiter, "ftol": ftol, "gtol": gtol})
    return res.x, {"loss": float(res.fun), "iterations": int(res.nit), "evaluations": int(res.nfev),
                   "converged": bool(res.success), "message": str(res.message),
                   "max_abs_projected_gradient": float(np.max(np.abs(np.where(
                       (res.x <= LOWER_BOUNDS) & (res.jac > 0) | (res.x >= UPPER_BOUNDS) & (res.jac < 0),
                       0.0, res.jac)))),
                   "device": str(obj.device)}


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


def personalise(cards: Cards, w_general, lam: float, arm: str = "line", target: np.ndarray | None = None,
                device: torch.device | None = None):
    """Fine-tune per agent on its early reviews; return pass predictions for every card."""
    link = ARMS[arm][0]
    mg = cards.m_grid()
    early, late = time_split(cards)
    pred = lambda w, c, m: predicted_pass(np.nan_to_num(predict(w, c.t, c.g, c.valid), nan=1.0), m, link)
    p_gen = pred(w_general, cards, mg)
    p_per = p_gen.copy()
    per_agent = []
    for a in np.unique(cards.agent):
        sel = cards.agent == a
        sub = cards.subset(sel)
        e, l = early[sel], late[sel]
        if e.sum() < 10 or l.sum() < 5:
            continue
        w_a, info = fit(w_general, sub, e, arm=arm, target=None if target is None else target[sel],
                        prior=w_general, lam=lam, maxiter=100, device=device)
        p_a = pred(w_a, sub, mg[sel])
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
    ap.add_argument("--arm", choices=sorted(ARMS), default="line",
                    help="line: R = line pass chance; pass: p_pass(R, M) on pass/fail; "
                         "accuracy: R on accuracy; true-recall: R on the hidden per-move recall (diagnostic)")
    ap.add_argument("--clock", choices=("app", "exact"), default="app")
    ap.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto")
    ap.add_argument("--no-personalise", action="store_true", help="skip the per-client fine-tuning step")
    a = ap.parse_args(argv)
    a.out.mkdir(parents=True, exist_ok=True)
    device = default_device() if a.device == "auto" else torch.device(a.device)
    link = ARMS[a.arm][0]
    started = time.time()
    log = lambda msg: print(f"[{time.time() - started:7.1f}s] {msg}", flush=True)

    cards = load_cards(a.data / "sessions.csv", line_lengths(a.data), clock=a.clock)
    truth = Truth(a.data)
    gen_manifest = json.loads((a.data / "manifest.json").read_text())
    horizon = float(gen_manifest["config"]["horizon_days"])
    clients = pd.read_csv(a.data / "clients.csv")
    archetype = dict(zip(clients["agent_name"], clients["archetype"]))
    parts = split_clients(clients, a.seed)
    in_part = {k: np.isin(cards.agent, sorted(v)) for k, v in parts.items()}
    log(f"{len(cards.agent)} cards, {cards.n_reviews} tested reviews; device {device}; "
        + ", ".join(f"{k}: {len(v)} clients / {int(cards.loss_mask[in_part[k]].sum())} reviews" for k, v in parts.items()))

    fit_cards = cards.subset(in_part["fit"])
    test_cards = cards.subset(in_part["test"])
    val_cards = cards.subset(in_part["validation"])
    target_of = (lambda c: truth.grid(c, truth.r_move)) if a.arm == "true-recall" else (lambda c: None)

    # ---- general model
    log(f"fitting general FSRS-6 parameters on fit clients (arm={a.arm}, link={link}, clock={a.clock}) ...")
    w_gen, info = fit(DEFAULT_PARAMETERS, fit_cards, fit_cards.loss_mask, arm=a.arm,
                      target=target_of(fit_cards), device=device)
    log(f"done: {info}")

    # ---- evaluation on test clients
    m = test_cards.loss_mask
    y = test_cards.y[m]
    base_rate = float(fit_cards.y[fit_cards.loss_mask].mean())
    results = {
        "arm": a.arm,
        "link": link,
        "clock": a.clock,
        "test": {
            "constant_base_rate": metrics(np.full(len(y), base_rate), y, truth.p_pass[test_cards.row[m]]),
            "fsrs6_default": score(DEFAULT_PARAMETERS, test_cards, truth, horizon, link),
            "fsrs6_trained": score(w_gen, test_cards, truth, horizon, link),
        },
        "test_by_archetype": {},
        "fit": {"fsrs6_trained": score(w_gen, fit_cards, truth, horizon, link)},
        "optimizer": info,
        "base_rate": base_rate,
    }
    arch_card = np.array([archetype[x] for x in test_cards.agent])
    for arch in sorted(set(arch_card)):
        sub = test_cards.subset(arch_card == arch)
        results["test_by_archetype"][arch] = {
            "fsrs6_default": score(DEFAULT_PARAMETERS, sub, truth, horizon, link),
            "fsrs6_trained": score(w_gen, sub, truth, horizon, link),
        }
    log("test: " + json.dumps({k: round(v["log_loss"], 4) for k, v in results["test"].items()}))

    # ---- personalisation: choose lambda on validation clients
    if a.no_personalise:
        results["personalisation"] = "skipped (--no-personalise)"
    else:
        lam_scores = {}
        for lam in LAMBDA_GRID:
            pg, pp, late, _ = personalise(val_cards, w_gen, lam, a.arm, target_of(val_cards), device)
            lam_scores[lam] = {"general": float(bce(pg[late], val_cards.y[late]).mean()),
                               "personal": float(bce(pp[late], val_cards.y[late]).mean())}
            log(f"validation lambda={lam}: {lam_scores[lam]}")
        best_lam = min(LAMBDA_GRID, key=lambda l: lam_scores[l]["personal"])
        use_personal = lam_scores[best_lam]["personal"] < lam_scores[best_lam]["general"]

        pg, pp, late, per_agent = personalise(test_cards, w_gen, best_lam, a.arm, target_of(test_cards), device)
        yl, tl = test_cards.y[late], truth.p_pass[test_cards.row[late]]
        p_def = predicted_pass(np.nan_to_num(predict(DEFAULT_PARAMETERS, test_cards.t, test_cards.g,
                                                     test_cards.valid), nan=1.0), test_cards.m_grid(), link)
        results["personalisation"] = {
            "lambda_grid_validation": {str(k): v for k, v in lam_scores.items()},
            "chosen_lambda": best_lam,
            "validation_says_personalise": use_personal,
            "test_late_reviews": {
                "fsrs6_default": metrics(p_def[late], yl, tl),
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

    params = {"model": "FSRS-6", "arm": a.arm, "recall_means": "one move" if link == "move" else "the line",
              "clock": a.clock, "parameters": [round(float(x), 6) for x in w_gen],
              "default_parameters": DEFAULT_PARAMETERS.tolist(),
              "trained_on": {"data": str(a.data), "clients": len(parts["fit"]),
                             "reviews": int(fit_cards.loss_mask.sum()), "base_rate": base_rate}}
    (a.out / "fsrs6_general_parameters.json").write_text(json.dumps(params, indent=2) + "\n")
    results["split"] = {k: sorted(v) for k, v in parts.items()}
    results["environment"] = {"python": platform.python_version(), "numpy": np.__version__,
                              "pandas": pd.__version__, "scipy": scipy.__version__, "torch": torch.__version__,
                              "device": str(device),
                              "gpu": torch.cuda.get_device_name(0) if device.type == "cuda" else None,
                              "platform": platform.platform()}
    results["seconds"] = round(time.time() - started, 1)
    (a.out / "metrics.json").write_text(json.dumps(results, indent=2) + "\n")
    log(f"wrote {a.out}")


if __name__ == "__main__":
    main()
