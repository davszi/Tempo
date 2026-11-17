"""FSRS-6 state replay in torch, for exact gradients on CPU or GPU.

The same formulas as ``model.py`` (numpy), which stays the reference:
``tests/test_trainers.py`` checks that both give the same predictions and that
the torch gradient matches finite differences of the numpy objective.

All tensors are float64. ``replay`` returns, for every (card, step), the
predicted retrievability before the review and the stability after it.
"""

from __future__ import annotations

import torch

from .model import MAX_DIFFICULTY, MIN_DIFFICULTY, STABILITY_MIN

DTYPE = torch.float64


def default_device() -> torch.device:
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


def forgetting_curve(w, t, s):
    decay = -w[20]
    factor = torch.pow(torch.tensor(0.9, dtype=DTYPE, device=w.device), 1.0 / decay) - 1.0
    return (1.0 + factor * t / s) ** decay


def initial_difficulty(w, g, clamp: bool = True):
    d = w[4] - torch.exp(w[5] * (g - 1)) + 1.0
    return d.clamp(MIN_DIFFICULTY, MAX_DIFFICULTY) if clamp else d


def next_difficulty(w, d, g):
    arg1 = w[4] - torch.exp(w[5] * 3.0) + 1.0
    delta = -(w[6] * (g - 3))
    arg2 = d + (10.0 - d) * delta / 9.0
    return (w[7] * arg1 + (1.0 - w[7]) * arg2).clamp(MIN_DIFFICULTY, MAX_DIFFICULTY)


def short_term_stability(w, s, g):
    inc = torch.exp(w[17] * (g - 3 + w[18])) * s ** (-w[19])
    inc = torch.where(g >= 2, inc.clamp_min(1.0), inc)
    return (s * inc).clamp_min(STABILITY_MIN)


def next_stability(w, d, s, r, g):
    one = torch.ones_like(s)
    hard = torch.where(g == 2, w[15] * one, one)
    easy = torch.where(g == 4, w[16] * one, one)
    recall = s * (1.0 + torch.exp(w[8]) * (11.0 - d) * s ** (-w[9]) * (torch.exp((1.0 - r) * w[10]) - 1.0) * hard * easy)
    long_term = w[11] * d ** (-w[12]) * ((s + 1.0) ** w[13] - 1.0) * torch.exp((1.0 - r) * w[14])
    forget = torch.minimum(long_term, s / torch.exp(w[17] * w[18]))
    return torch.where(g == 1, forget, recall).clamp_min(STABILITY_MIN)


def replay(w, t, g, valid):
    """Predicted R before every review and stability after it.

    Args:
        w: (21,) weights tensor.
        t: (cards, steps) elapsed days (step 0 ignored).
        g: (cards, steps) grades as float (3 at invalid positions).
        valid: (cards, steps) bool.

    Returns:
        (r, s_after): (cards, steps) tensors. ``r[:, 0]`` and invalid
        positions hold 1.0 (no prediction); ``s_after`` holds the stability
        once review k is applied, carried over at invalid positions.
    """
    n, steps = t.shape
    g0 = g[:, 0]
    s = w[(g0 - 1).long()].clamp_min(STABILITY_MIN)
    d = initial_difficulty(w, g0)
    rs = [torch.ones(n, dtype=DTYPE, device=t.device)]
    ss = [s]
    for k in range(1, steps):
        v = valid[:, k]
        tk, gk = t[:, k], g[:, k]
        r = forgetting_curve(w, tk, s)
        s_new = torch.where(tk < 1.0, short_term_stability(w, s, gk), next_stability(w, d, s, r, gk))
        d_new = next_difficulty(w, d, gk)
        rs.append(torch.where(v, r, torch.ones_like(r)))
        s = torch.where(v, s_new, s)
        d = torch.where(v, d_new, d)
        ss.append(s)
    return torch.stack(rs, 1), torch.stack(ss, 1)
