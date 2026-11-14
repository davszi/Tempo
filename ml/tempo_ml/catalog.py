"""Load the TEMPO opening catalog from the backend SQLite database.

The catalog is the tables ``opening_lines`` and ``opening_families`` in
``backend/tempo_demo.sqlite``. The database is opened read-only.

Each row is one line (variation). A player learns a line from one side; the
number of repertoire moves M they must recall is ``white_moves`` or
``black_moves`` for that side, derived from the line's UCI moves.

A line is offered to a player of ``side`` when its family's ``family_side``
is that side; the catalog has only ``white`` and ``black`` families
(docs/topics/opening-catalog/opening-catalog.md).
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from .simulator.clients import Line

SIDES = ("white", "black")

# ml/tempo_ml/catalog.py -> repository root is parents[2]
DEFAULT_CATALOG_DB = Path(__file__).resolve().parents[2] / "backend" / "tempo_demo.sqlite"

CATALOG_QUERY = """
SELECT l.line_id, l.name, l.eco, l.moves_uci,
       f.name AS family, f.family_side
FROM opening_lines AS l JOIN opening_families AS f USING (family_id)
ORDER BY l.line_id
"""


@dataclass(frozen=True)
class OpeningLine:
    """One line of the opening catalog."""

    line_id: str  # backend opening_lines.line_id
    eco: str
    family: str
    name: str
    moves_uci: str
    plies: int
    white_moves: int
    black_moves: int
    family_side: str

    def playable_by(self, side: str) -> bool:
        if side not in SIDES:
            raise ValueError(f"side must be one of {SIDES}, got {side!r}")
        return self.family_side == side

    def moves_for(self, side: str) -> int:
        return self.white_moves if side == "white" else self.black_moves

    def as_line(self, side: str) -> Line:
        """The ``Line`` a synthetic client practises from ``side``."""
        return Line(opening_name=self.name, num_moves=self.moves_for(side), line_id=self.line_id)


def load_opening_lines(db: str | Path = DEFAULT_CATALOG_DB) -> list[OpeningLine]:
    """Read every line of the catalog, ordered by ``line_id``."""
    uri = Path(db).resolve().as_uri() + "?mode=ro"
    con = sqlite3.connect(uri, uri=True)
    try:
        rows = con.execute(CATALOG_QUERY).fetchall()
    finally:
        con.close()
    lines: list[OpeningLine] = []
    for line_id, name, eco, moves_uci, family, family_side in rows:
        plies = len(moves_uci.split())
        lines.append(
            OpeningLine(
                line_id=str(line_id),
                eco=eco,
                family=family,
                name=name,
                moves_uci=moves_uci,
                plies=plies,
                white_moves=(plies + 1) // 2,
                black_moves=plies // 2,
                family_side=family_side,
            )
        )
    return lines
