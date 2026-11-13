"""Load the TEMPO opening library (``openings/opening_lines.csv``).

Each row is one line (variation). A player learns a line from one side; the
number of repertoire moves M they must recall is ``white_moves`` or
``black_moves`` for that side.

Which side a line belongs to follows the library README's suggested filter:
a line is offered to a player of ``side`` when ``family_side == side`` or
``side_in_games`` is ``side`` or ``"both"``. ``family_side == "both"`` counts
for both sides.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from .synthetic_clients.client import Line

SIDES = ("white", "black")

# ml_engine/src/tempo_ml/openings.py -> repository root is parents[3]
DEFAULT_LINES_CSV = Path(__file__).resolve().parents[3] / "openings" / "opening_lines.csv"


@dataclass(frozen=True)
class OpeningLine:
    """One row of the opening library."""

    line_id: str
    eco: str
    family: str
    name: str
    pgn: str
    plies: int
    white_moves: int
    black_moves: int
    family_side: str
    side_in_games: str
    family_games: int  # n_games of the family in the Lichess evidence (0 if unknown)

    def playable_by(self, side: str) -> bool:
        if side not in SIDES:
            raise ValueError(f"side must be one of {SIDES}, got {side!r}")
        return (
            self.family_side in (side, "both")
            or self.side_in_games in (side, "both")
        )

    def moves_for(self, side: str) -> int:
        return self.white_moves if side == "white" else self.black_moves

    def as_line(self, side: str) -> Line:
        """The ``Line`` a synthetic client practises from ``side``."""
        return Line(opening_name=self.name, num_moves=self.moves_for(side), line_id=self.line_id)


def load_opening_lines(path: str | Path = DEFAULT_LINES_CSV) -> list[OpeningLine]:
    """Read the library CSV. ``line_id`` is ``<eco>-<row number>`` (row 1 = first line)."""
    lines: list[OpeningLine] = []
    with Path(path).open(encoding="utf-8-sig", newline="") as handle:
        for i, row in enumerate(csv.DictReader(handle), start=1):
            n_games = row.get("n_games") or ""
            lines.append(
                OpeningLine(
                    line_id=f"{row['eco']}-{i:04d}",
                    eco=row["eco"],
                    family=row["family"],
                    name=row["name"],
                    pgn=row["pgn"],
                    plies=int(row["plies"]),
                    white_moves=int(row["white_moves"]),
                    black_moves=int(row["black_moves"]),
                    family_side=row["family_side"],
                    side_in_games=row.get("side_in_games") or "",
                    family_games=int(float(n_games)) if n_games else 0,
                )
            )
    return lines
