"""Opening catalogue, move-level telemetry and the session grader.

Client model: docs/topics/synthetic-clients/record.md (sections 3.3-3.5).
Grader:       docs/topics/review-dataset/record.md (section 3).
"""
from __future__ import annotations

import math
import os
import re
from dataclasses import dataclass

import numpy as np

from .config import SimConfig
from .persona import Persona


# --------------------------------------------------------------------------
# Opening catalogue
# --------------------------------------------------------------------------
@dataclass
class OpeningLine:
    line_id: str               # stable id; for library lines the row in the library
    color: str                 # side the player studies
    plies: np.ndarray          # ply number of each move the player must produce
    name: str = ""             # opening name (Lichess name for library lines)
    pgn: str = ""

    @property
    def n_moves(self) -> int:
        return len(self.plies)


def make_catalogue(cfg: SimConfig, rng: np.random.Generator) -> list[OpeningLine]:
    if cfg.openings_file:
        return _library_catalogue(cfg, rng)
    return _synthetic_catalogue(cfg, rng)


def _library_catalogue(cfg: SimConfig, rng: np.random.Generator) -> list[OpeningLine]:
    """Real named lines from the opening library (Lichess chess-openings, CC0).

    The player studies the family's side (family_side from the classified
    library); "both" families, or a plain TSV without that column, get a
    random side. Lines where that side has fewer or more moves than
    cfg.user_moves are skipped. line_id is the row of the line in the
    library, so it is the same in every dataset.
    """
    import pandas as pd

    path = cfg.openings_file
    if not os.path.isabs(path):
        path = os.path.join(os.path.dirname(os.path.dirname(__file__)), path)
    df = pd.read_csv(path, sep="\t" if path.endswith(".tsv") else ",", keep_default_na=False)
    lines = []
    for i in rng.permutation(len(df)):
        row = df.iloc[i]
        n_plies = len([t for t in row.pgn.split() if not re.match(r"^\d+\.", t)])
        side = row.get("family_side", "")
        color = side if side in ("white", "black") else ("white" if rng.random() < 0.5 else "black")
        first = 1 if color == "white" else 2
        n = (n_plies - first) // 2 + 1
        if not cfg.user_moves[0] <= n <= cfg.user_moves[1]:
            continue
        lines.append(OpeningLine(f"line_{i:04d}", color, first + 2 * np.arange(n),
                                 row["name"], row.pgn))
        if len(lines) == cfg.n_openings:
            break
    return lines


def _synthetic_catalogue(cfg: SimConfig, rng: np.random.Generator) -> list[OpeningLine]:
    """Made-up lines (the original stand-in)."""
    lines = []
    for i in range(cfg.n_openings):
        n = int(rng.integers(cfg.user_moves[0], cfg.user_moves[1] + 1))
        color = "white" if rng.random() < 0.5 else "black"
        first = 1 if color == "white" else 2
        lines.append(OpeningLine(f"op_{i:03d}", color, first + 2 * np.arange(n),
                                 f"Synthetic line {i:03d}"))
    return lines


# --------------------------------------------------------------------------
# One unassisted attempt (Repeating Mode)
# --------------------------------------------------------------------------
@dataclass
class Attempt:
    recalled: bool              # hidden: did the line come back? (recall_mode "line")
    correct: np.ndarray         # first-attempt correctness per move
    time_ms: np.ndarray         # final_time_ms per move

    @property
    def accuracy(self) -> float:
        return float(self.correct.mean())

    @property
    def total_time_ms(self) -> float:
        return float(self.time_ms.sum())

    @property
    def clean(self) -> bool:
        return bool(self.correct.all())


def play_line(p: Persona, line: OpeningLine, r_true: float, reps: int,
              rng: np.random.Generator, recall_mode: str = "line") -> Attempt:
    """Unassisted attempt at a line.

    Accuracy (effort does not change it, synthetic-clients record 2.2):
      recall_mode "line": one dice roll against R decides whether the line is
        recalled. Recalled: every move right. Forgotten: one random move is a
        blunder, every other move is right with probability R.
      recall_mode "move": every move is right with probability R (record 3.3).
    A blunder is taken back and retried; only the first attempt counts.

    Time per move (record 3.4):
      baseline_ms + lognormal(mu, sigma) * 1000 * exp(beta (1 - R)) / (1 + alpha reps)
    No depth or sharpness multiplier (deferred in the record, section 5).
    """
    n = line.n_moves
    if recall_mode == "line":
        recalled = rng.random() < r_true
        if recalled:
            correct = np.ones(n, bool)
        else:
            correct = rng.random(n) < r_true
            correct[rng.integers(n)] = False
    else:
        correct = rng.random(n) < r_true
        recalled = bool(correct.all())

    raw_s = rng.lognormal(p.mu, p.sigma, n)
    strain = math.exp(p.beta * (1.0 - r_true))
    m_practice = 1.0 / (1.0 + p.alpha * reps)
    return Attempt(bool(recalled), correct, p.baseline_ms + raw_s * 1000.0 * strain * m_practice)


def next_reps(reps: int, clean: bool) -> int:
    """Practice accumulation (record 3.5): +1 after a clean session, -2 after a blunder."""
    return reps + 1 if clean else max(0, reps - 2)


# --------------------------------------------------------------------------
# Session grader (review-dataset record, section 3)
# --------------------------------------------------------------------------
def grade(accuracy: float, total_time_ms: float, n_moves: int, baseline_ms: float,
          cfg: SimConfig) -> int:
    if accuracy < 1.0:
        return 1                                     # Again: any blunder
    delay = total_time_ms / n_moves - baseline_ms    # mean cognitive delay per move
    if delay < cfg.easy_ms:
        return 4                                     # Easy
    if delay <= cfg.hard_ms:
        return 3                                     # Good
    return 2                                         # Hard
