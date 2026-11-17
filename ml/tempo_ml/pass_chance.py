"""Mistake limits and the pass chance of a line from per-move recall.

Owners: docs/topics/session-grading/session-grading.md (mistake limits,
section 3.2) and docs/topics/move-recall/move-recall.md (pass chance and the
per-move scheduling target, sections 2 and 3.3).

A review passes when it has at most ``L(M)`` mistakes. When each of the M
player moves is right independently with per-move recall R, the pass chance is

    p_pass(R, M) = sum_{k=0..L(M)} C(M, k) (1 - R)^k R^(M - k).

``per_move_target(M)`` is the R at which ``p_pass(R, M)`` equals the target
(0.9): a line is due when its per-move recall falls to it.

``p_pass`` works on numpy arrays and torch tensors alike (only arithmetic).
"""

from __future__ import annotations

from math import comb

import numpy as np

from .simulator.grading import mistake_limit as _scalar_limit

TARGET_PASS = 0.9
MAX_LIMIT = 3  # largest mistake limit (13 or more moves)


def mistake_limit(num_moves):
    """L(M) for a scalar or an array of line lengths; the rule itself is
    ``simulator.grading.mistake_limit`` (session-grading record, section 3.2)."""
    m = np.asarray(num_moves)
    out = np.vectorize(_scalar_limit, otypes=[int])(m) if m.ndim else _scalar_limit(int(m))
    return int(out) if np.ndim(out) == 0 else out


def binomial_terms(num_moves) -> np.ndarray:
    """(..., MAX_LIMIT + 1) coefficients C(M, k) for k <= L(M), else 0."""
    m = np.asarray(num_moves, dtype=int)
    lim = np.asarray(mistake_limit(m))
    coef = np.zeros(m.shape + (MAX_LIMIT + 1,))
    for k in range(MAX_LIMIT + 1):
        c = np.vectorize(lambda x, k=k: comb(int(x), k), otypes=[float])(m) if m.ndim else comb(int(m), k)
        coef[..., k] = np.where(k <= lim, c, 0.0)
    return coef


def p_pass(R, num_moves, coef=None):
    """Chance of at most L(M) mistakes with per-move recall R.

    ``R`` and ``num_moves`` broadcast together. ``coef`` (from
    ``binomial_terms``, shaped like the broadcast plus a last axis of 4) may be
    passed to avoid recomputing it; it must be a torch tensor when ``R`` is.
    """
    if coef is None:
        coef = binomial_terms(num_moves)
    m = num_moves
    total = 0.0
    for k in range(MAX_LIMIT + 1):
        total = total + coef[..., k] * (1.0 - R) ** k * R ** (m - k)
    return total


def per_move_target(num_moves: int, target: float = TARGET_PASS) -> float:
    """R*(M): the per-move recall at which the pass chance equals ``target``."""
    m = int(num_moves)
    if m < 1:
        raise ValueError(f"num_moves must be >= 1, got {m}")
    lo, hi = 0.0, 1.0  # p_pass increases with R: bisection to machine precision
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if p_pass(mid, m) < target:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)
