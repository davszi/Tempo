"""Minimal FSRS-6 memory model (pure Python / numpy).

Mirrors the formulas of py-fsrs 6.3.2 (open-spaced-repetition/py-fsrs) so that
the synthetic agents' hidden memory and the TEMPO optimizer speak exactly the
same model. tests/test_fsrs6.py checks this against the reference package.

Forgetting curve (slide 5):  R(t) = (1 + F * t / S) ** (-C)
In FSRS-6, C = w[20] and F is *derived* from C so that R(t=S) = 0.9:
    F = 0.9 ** (-1 / C) - 1
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

DEFAULT_W = np.array([
    0.212, 1.2931, 2.3065, 8.2956, 6.4133, 0.8334, 3.0194, 0.001, 1.8722,
    0.1666, 0.796, 1.4835, 0.0614, 0.2629, 1.6483, 0.6014, 1.8729, 0.5425,
    0.0912, 0.0658, 0.1542,
])

S_MIN = 0.001
LOWER_W = np.array([
    S_MIN, S_MIN, S_MIN, S_MIN, 1.0, 0.001, 0.001, 0.001, 0.0, 0.0, 0.001,
    0.001, 0.001, 0.001, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.1,
])
UPPER_W = np.array([
    100.0, 100.0, 100.0, 100.0, 10.0, 4.0, 4.0, 0.75, 4.5, 0.8, 3.5, 5.0,
    0.25, 0.9, 4.0, 1.0, 6.0, 2.0, 2.0, 0.8, 0.8,
])
D_MIN, D_MAX = 1.0, 10.0

AGAIN, HARD, GOOD, EASY = 1, 2, 3, 4


def forgetting_factor(decay_c: float) -> float:
    """F as a function of C (the FSRS-6 constraint R(S) = 0.9)."""
    return 0.9 ** (-1.0 / decay_c) - 1.0


@dataclass
class MemoryState:
    stability: float
    difficulty: float


class FSRS6:
    def __init__(self, w=DEFAULT_W):
        self.w = np.asarray(w, dtype=float)
        if self.w.shape != (21,):
            raise ValueError("FSRS-6 needs exactly 21 weights")
        self.C = self.w[20]
        self.F = forgetting_factor(self.C)

    # ---- forgetting curve -------------------------------------------------
    def retrievability(self, elapsed_days: float, stability: float) -> float:
        return (1.0 + self.F * elapsed_days / stability) ** (-self.C)

    def interval_for(self, stability: float, desired_retention: float) -> float:
        """Days until R drops to desired_retention (unrounded)."""
        return stability / self.F * (desired_retention ** (-1.0 / self.C) - 1.0)

    # ---- state transitions ------------------------------------------------
    def _init_difficulty(self, g: int) -> float:
        return self.w[4] - math.exp(self.w[5] * (g - 1)) + 1.0

    def init_state(self, g: int) -> MemoryState:
        s = max(self.w[g - 1], S_MIN)
        d = min(max(self._init_difficulty(g), D_MIN), D_MAX)
        return MemoryState(s, d)

    def next_difficulty(self, d: float, g: int) -> float:
        delta = -self.w[6] * (g - 3)
        d2 = d + (10.0 - d) * delta / 9.0
        d3 = self.w[7] * self._init_difficulty(EASY) + (1 - self.w[7]) * d2
        return min(max(d3, D_MIN), D_MAX)

    def short_term_stability(self, s: float, g: int) -> float:
        inc = math.exp(self.w[17] * (g - 3 + self.w[18])) * s ** (-self.w[19])
        if g >= HARD:
            inc = max(inc, 1.0)
        return max(s * inc, S_MIN)

    def next_stability(self, d: float, s: float, r: float, g: int) -> float:
        w = self.w
        if g == AGAIN:
            long_term = (w[11] * d ** (-w[12]) * ((s + 1) ** w[13] - 1)
                         * math.exp((1 - r) * w[14]))
            short_term = s / math.exp(w[17] * w[18])
            out = min(long_term, short_term)
        else:
            hard = w[15] if g == HARD else 1.0
            easy = w[16] if g == EASY else 1.0
            out = s * (1 + math.exp(w[8]) * (11 - d) * s ** (-w[9])
                       * (math.exp((1 - r) * w[10]) - 1) * hard * easy)
        return max(out, S_MIN)

    def step(self, state: MemoryState, elapsed_days: float, g: int) -> MemoryState:
        """One review: stability is updated with the *old* difficulty, as in py-fsrs."""
        if elapsed_days < 1:
            s = self.short_term_stability(state.stability, g)
        else:
            r = self.retrievability(elapsed_days, state.stability)
            s = self.next_stability(state.difficulty, state.stability, r, g)
        d = self.next_difficulty(state.difficulty, g)
        return MemoryState(s, d)
