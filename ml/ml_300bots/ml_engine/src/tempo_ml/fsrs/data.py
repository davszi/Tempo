"""Turn a review-session CSV into padded per-card arrays for FSRS.

Only the review-dataset schema columns are used, so the same code works on
human data. A card is (agent_name, opening_name); rows must be chronological
per card (generator output is). Same-day reviews (t_days < 1) still update the
card but are excluded from the loss, as in the FSRS optimizers; so are
Learning Mode sessions (``new``/``learning``), which test nothing because the
arrow shows the move.

Label: success = grade > 1, i.e. the whole line was played without a blunder.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

TEST_STATUSES = ("review", "relearning")


@dataclass
class Cards:
    agent: np.ndarray        # (n,) agent name per card
    t: np.ndarray            # (n, steps) days since previous review
    g: np.ndarray            # (n, steps) grade
    valid: np.ndarray        # (n, steps) review exists
    y: np.ndarray            # (n, steps) 1.0 if grade > 1
    loss_mask: np.ndarray    # (n, steps) review counts toward loss/metrics
    row: np.ndarray          # (n, steps) row number in the CSV, -1 if none

    def subset(self, keep: np.ndarray) -> "Cards":
        return Cards(*(getattr(self, f)[keep] for f in self.__dataclass_fields__))

    @property
    def n_reviews(self) -> int:
        return int(self.loss_mask.sum())


def load_cards(sessions_csv: str | Path) -> Cards:
    df = pd.read_csv(sessions_csv)
    df["row"] = np.arange(len(df))
    key = df["agent_name"] + "\x1f" + df["opening_name"]
    df["card"] = pd.factorize(key)[0]
    df["step"] = df.groupby("card").cumcount()
    n, steps = df["card"].max() + 1, df["step"].max() + 1

    def grid(values, fill, dtype):
        a = np.full((n, steps), fill, dtype=dtype)
        a[df["card"].to_numpy(), df["step"].to_numpy()] = values
        return a

    valid = grid(True, False, bool)
    t = grid(df["t_days"].to_numpy(float), 0.0, float)
    g = grid(df["grade"].to_numpy(int), 3, int)
    row = grid(df["row"].to_numpy(int), -1, int)
    tested = grid(df["review_status"].isin(TEST_STATUSES).to_numpy(), False, bool)
    loss_mask = valid & tested & (t >= 1.0)
    loss_mask[:, 0] = False
    agent = df.groupby("card")["agent_name"].first().to_numpy()
    return Cards(agent=agent, t=t, g=g, valid=valid, y=(g > 1).astype(float), loss_mask=loss_mask, row=row)
