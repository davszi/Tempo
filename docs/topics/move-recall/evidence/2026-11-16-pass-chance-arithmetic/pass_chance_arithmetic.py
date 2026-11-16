"""Reproduce the design arithmetic in the move-recall records.

Assumes each player move of a line is recalled independently with the
per-move FSRS recall R (binomial), and the session-grading mistake limits
L(M) = 0 (M <= 3), 1 (4-7), 2 (8-12), 3 (13+). Example player: decay C = 0.5,
stability S = 10 days. Prints:

1. the per-move target R*(M) at which the pass chance equals 0.9, and the
   interval it gives for the example player, and the pass chance at
   per-move recall 0.8, 0.9 and 0.98;
2. how well one FSRS forgetting curve fits each candidate label over 0-40
   days, per line length and with one shared curve for all lengths;
3. Fisher information about R carried by one review: the pass/fail bit
   versus the mistake count.

Design arithmetic, not a simulation or a measurement.
Usage, from the repository root: python -I <this file>   (needs numpy, scipy)
"""
from math import comb

import numpy as np
from scipy.optimize import brentq, least_squares

TARGET = 0.9
C, S = 0.5, 10.0


def limit(m):
    return 0 if m <= 3 else 1 if m <= 7 else 2 if m <= 12 else 3


def p_pass(r, m):
    return sum(comb(m, k) * (1 - r) ** k * r ** (m - k) for k in range(limit(m) + 1))


def recall(t, s, c):
    return (1 + (TARGET ** (-1 / c) - 1) * t / s) ** (-c)


def days(r, s=S, c=C):
    return s / (TARGET ** (-1 / c) - 1) * (r ** (-1 / c) - 1)


print("1. per-move target R*(M); interval for C=0.5, S=10")
print("M  L  R*      days   pass chance at R=0.8 / 0.9 / 0.98")
for m in list(range(1, 15)) + [18]:
    r_star = brentq(lambda r: p_pass(r, m) - TARGET, 0.3, 1 - 1e-9)
    print(f"{m:<2} {limit(m)}  {r_star:.4f}  {days(r_star):5.1f}  {p_pass(0.8, m):.3f} / {p_pass(0.9, m):.3f} / {p_pass(0.98, m):.3f}")

t = np.linspace(0.1, 40, 200)
r_true = recall(t, S, C)


def fit(curves, link):
    res = lambda q: np.concatenate([link(recall(t, q[0], q[1]), m) - y for m, y in curves])
    out = least_squares(res, [5, 0.5], bounds=([0.01, 0.05], [1e4, 20]))
    return out.x, np.abs(out.fun).max()


print("\n2. one FSRS curve fitted to each label (C upper bound 20)")
labels = {
    "no mistakes (R^M)": lambda r, m: r ** m,
    "new rule pass chance": p_pass,
    "accuracy (mean R)": lambda r, m: r,
}
for name, truth in labels.items():
    for m in (3, 6, 10, 14):
        (s, c), err = fit([(m, truth(r_true, m))], lambda r, _m: r)
        print(f"{name:22s} M={m:<2}  S={s:7.2f}  C={c:6.3f}  max error={err:.3f}")
curves = [(m, p_pass(r_true, m)) for m in (3, 6, 10, 14)]
for name, link in (("plain FSRS", lambda r, m: r), ("FSRS + pass chance", p_pass)):
    (s, c), err = fit(curves, link)
    print(f"shared over 3/6/10/14 moves, {name:18s} S={s:6.2f}  C={c:6.3f}  max error={err:.4f}")

print("\n3. information about R in one review")
for r in (0.9, 0.97):
    for m in (3, 6, 10, 14):
        h = 1e-6
        d = (p_pass(r + h, m) - p_pass(r - h, m)) / (2 * h)
        p = p_pass(r, m)
        bit, count = d * d / (p * (1 - p)), m / (r * (1 - r))
        print(f"R={r} M={m:<2}  pass bit={bit:6.1f}  mistake count={count:6.1f}  ratio={count / bit:5.2f}")
