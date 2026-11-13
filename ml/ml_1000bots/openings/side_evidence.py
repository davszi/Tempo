"""Which side's players keep choosing each opening family, from real games.

    python openings/side_evidence.py <parquet file> [<parquet file> ...]

Input: files of the Lichess standard-chess-games dataset on Hugging Face.
Bot games are dropped. The old name "Russian Game" is read as "Petrov's
Defense" (Lichess renamed it).

Writes openings/family_side_evidence.csv. Idea: a player who chooses an opening
plays it again and again; the opponent only meets it when paired with such a
player. For each family and colour: P(a player's next game with that colour is
the same family) divided by the family's overall share. side_ratio = white
value / black value. Only families with >= 100 game pairs on each side get a
verdict.
"""
import os
import sys

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from classify import split_name  # noqa: E402

cols = ["White", "Black", "WhiteTitle", "BlackTitle", "UTCDate", "UTCTime", "Opening"]
g = pd.concat([pq.read_table(f, columns=cols).to_pandas() for f in sys.argv[1:]])
g = g[(g.WhiteTitle != "BOT") & (g.BlackTitle != "BOT")]
g = g.sort_values(["UTCDate", "UTCTime"], kind="stable")
g["fam"] = g.Opening.map(lambda n: split_name(n)[0] if isinstance(n, str) else None)
g["fam"] = g.fam.replace({"Russian Game": "Petrov's Defense"})
base = g.fam.value_counts(normalize=True)
side = {}
for col in ("White", "Black"):
    x = g[[col, "fam"]].rename(columns={col: "p"})
    x["nxt"] = x.groupby("p").fam.shift(-1)
    x = x.dropna(subset=["fam", "nxt"])
    x["same"] = x.fam == x.nxt
    r = x.groupby("fam").same.agg(["size", "mean"])
    side[col] = pd.DataFrame({"n": r["size"], "lift": r["mean"] / base.reindex(r.index)})
ev = side["White"].merge(side["Black"], left_index=True, right_index=True, suffixes=("_w", "_b"), how="outer")
ev["side_ratio"] = ev.lift_w / ev.lift_b
ev["n_games"] = ev[["n_w", "n_b"]].min(axis=1)
enough = (ev.n_games >= 100) & (ev.lift_w > 0) & (ev.lift_b > 0)
ev["side_in_games"] = np.where(~enough, "", np.where(ev.side_ratio >= 2, "white",
                               np.where(ev.side_ratio <= 0.5, "black", "both")))
ev.loc[~enough, "side_ratio"] = np.nan
ev = ev.rename_axis("family").reset_index()
ev[["family", "side_in_games", "side_ratio", "n_games"]].round(2).to_csv(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "family_side_evidence.csv"), index=False)
print(f"{enough.sum()} families with a verdict -> openings/family_side_evidence.csv "
      f"({len(sys.argv) - 1} files, {len(g)} games, days {g.UTCDate.min()}..{g.UTCDate.max()})")
