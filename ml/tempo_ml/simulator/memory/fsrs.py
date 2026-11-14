"""FSRS-6 as the hidden memory of the synthetic clients.

Selected with ``"memory": "fsrs"`` in a generation config; the default stays
``multiplicative``. Everything else (per-move recall, retries, grading, the
practice policy) is shared, so the two memory models differ only here.

Each client gets its own 21 FSRS-6 weights: the FSRS-6 defaults with
log-normal noise on w0-w16 (w17-w19 stay at the defaults), w0-w3 sorted so
that a better first grade never gives a weaker start, all clipped to the
FSRS-6 bounds, and w20 set to the client's decay C so that the forgetting
curve is the one the client already uses (``retrievability``).

Per line the state is the stability S and the difficulty D. A session's
grade drives the update, exactly as in FSRS-6 (``tempo_ml.fsrs.model``):
same-day sessions use the short-term update, later ones the recall or
forget update. After a lapse S never falls below ``min_days`` unless it was
already lower, as for the multiplicative model: the client retries until the
line is played correctly, which is itself a relearning pass.

Because the clients' memory then follows FSRS-6 exactly, FSRS-6 is correctly
specified for each move; with per-move recall a whole line passes with
probability R**M, which FSRS-6 does not model.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

import numpy as np

from ...fsrs.model import (DEFAULT_PARAMETERS, LOWER_BOUNDS, UPPER_BOUNDS, initial_difficulty,
                           initial_stability, next_difficulty, next_stability, short_term_stability)

FROZEN = slice(17, 20)  # same-day weights stay at the defaults


@dataclass(frozen=True)
class FSRSMemory:
    """FSRS-6 memory of one client. ``graded``: the update needs the session grade."""

    weights: tuple[float, ...]
    min_days: float = 1.0
    graded: ClassVar[bool] = True

    @classmethod
    def sample(cls, C: float, rng: np.random.Generator, noise: float = 0.15,
               min_days: float = 1.0) -> "FSRSMemory":
        w = np.array(DEFAULT_PARAMETERS, dtype=float)
        mult = np.exp(rng.normal(0.0, noise, 21))
        mult[FROZEN] = 1.0
        mult[20] = 1.0
        w = w * mult
        w[0:4] = np.sort(w[0:4])
        w[20] = C
        w = np.clip(w, LOWER_BOUNDS, UPPER_BOUNDS)
        return cls(weights=tuple(float(x) for x in w), min_days=min_days)

    def _w(self) -> np.ndarray:
        return np.asarray(self.weights, dtype=float)

    def start(self, grade: int) -> tuple[float, float]:
        """(S, D) after the first exposure, graded ``grade``."""
        w, g = self._w(), np.asarray(grade)
        return float(initial_stability(w, g)), float(initial_difficulty(w, g))

    def update(self, stability: float, difficulty: float, t_days: float, R: float,
               grade: int) -> tuple[float, float]:
        """(S, D) after a session ``t_days`` after the previous one, started at R."""
        w, g = self._w(), np.asarray(grade)
        s, d = np.asarray(stability, dtype=float), np.asarray(difficulty, dtype=float)
        if t_days < 1.0:
            s_new = float(short_term_stability(w, s, g))
        else:
            s_new = float(next_stability(w, d, s, np.asarray(R, dtype=float), g))
        if grade == 1:
            s_new = min(stability, max(self.min_days, s_new))
        return s_new, float(next_difficulty(w, d, g))
