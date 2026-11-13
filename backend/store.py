"""SQLite persistence for the TEMPO catalog and practice history."""

from contextlib import contextmanager
from datetime import timezone
from sqlite3 import Row, connect


FAMILY_SIDES = ("white", "black")

# Family-side decisions from docs/topics/opening-catalog/opening-catalog.md.
SIDE_OVERRIDES = {
    "Queen's Gambit": "white",
    "Benko Gambit": "black",
    "Four Knights Game": "white",
}
VARIATION_SUFFIXES = (" Accepted", " Declined")

CATALOG_SCHEMA = """
CREATE TABLE IF NOT EXISTS opening_families (
    family_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    family_side TEXT NOT NULL CHECK (family_side IN ('white', 'black'))
);

CREATE TABLE IF NOT EXISTS opening_lines (
    line_id INTEGER PRIMARY KEY,
    family_id INTEGER NOT NULL REFERENCES opening_families,
    parent_line_id INTEGER REFERENCES opening_lines,
    name TEXT NOT NULL,
    eco TEXT NOT NULL,
    moves_uci TEXT NOT NULL UNIQUE
);

CREATE INDEX IF NOT EXISTS opening_lines_family ON opening_lines (family_id);
CREATE INDEX IF NOT EXISTS opening_lines_parent ON opening_lines (parent_line_id);
"""

PRACTICE_SCHEMA = """
CREATE TABLE IF NOT EXISTS practice_events (
    event_id INTEGER PRIMARY KEY,
    player_id TEXT NOT NULL,
    line_id INTEGER NOT NULL REFERENCES opening_lines,
    session_id TEXT,
    event_type TEXT NOT NULL CHECK (
        event_type IN ('line_suggested', 'move_attempted', 'session_completed')
    ),
    mode TEXT NOT NULL CHECK (mode IN ('learning', 'repeating')),
    side TEXT CHECK (side IN ('white', 'black', 'both')),
    occurred_at TEXT NOT NULL,
    move_index INTEGER,
    is_correct INTEGER CHECK (is_correct IN (0, 1)),
    response_time_ms INTEGER CHECK (response_time_ms >= 0),
    fsrs_rating TEXT CHECK (fsrs_rating IN ('Again', 'Hard', 'Good', 'Easy'))
);

CREATE TABLE IF NOT EXISTS player_lines (
    player_id TEXT NOT NULL,
    line_id INTEGER NOT NULL REFERENCES opening_lines,
    learned_at TEXT NOT NULL,
    last_reviewed_at TEXT,
    next_review_at TEXT NOT NULL,
    fsrs_state TEXT NOT NULL,
    PRIMARY KEY (player_id, line_id)
);

CREATE INDEX IF NOT EXISTS practice_events_player ON practice_events (player_id, event_id);
CREATE INDEX IF NOT EXISTS player_lines_due ON player_lines (player_id, next_review_at);
"""

# A line can be learned when no other line extends it.
LEARNABLE = "NOT EXISTS (SELECT 1 FROM opening_lines AS c WHERE c.parent_line_id = o.line_id)"


def timestamp(value):
    return value.astimezone(timezone.utc).isoformat(timespec="microseconds")


def run_statements(db, script):
    # executescript would commit the open transaction, so run each statement on its own.
    for statement in script.strip().rstrip(";").split(";"):
        db.execute(statement)


def family_name(name):
    """Fold an Accepted or Declined family into its gambit."""
    for suffix in VARIATION_SUFFIXES:
        if name.endswith(suffix):
            return name[: -len(suffix)]
    return name


def family_side(name, known_sides=()):
    """Return the side a family belongs to, or raise when it cannot be decided."""
    if name in SIDE_OVERRIDES:
        return SIDE_OVERRIDES[name]
    if "Defense" in name or "Defence" in name:
        return "black"
    sides = {side for side in known_sides if side in FAMILY_SIDES}
    if len(sides) == 1:
        return sides.pop()
    raise ValueError(f"Opening family {name!r} needs a side: white or black")


def link_parents(db):
    """Point each line at the longest other line of its family that it extends."""
    families = {}
    lines = db.execute("SELECT line_id, family_id, moves_uci FROM opening_lines").fetchall()
    for line in lines:
        families.setdefault(line["family_id"], {})[line["moves_uci"]] = line["line_id"]
    updates = []
    for line in lines:
        known = families[line["family_id"]]
        moves = line["moves_uci"].split()
        parent = next(
            (known[prefix] for prefix in (" ".join(moves[:size]) for size in range(len(moves) - 1, 0, -1))
             if prefix in known),
            None,
        )
        updates.append((parent, line["line_id"]))
    db.executemany("UPDATE opening_lines SET parent_line_id = ? WHERE line_id = ?", updates)


def is_learnable(db, line_id):
    row = db.execute(
        f"SELECT {LEARNABLE} AS learnable FROM opening_lines AS o WHERE o.line_id = ?", (line_id,)
    ).fetchone()
    if row is None:
        raise LookupError("Unknown opening line")
    return bool(row["learnable"])


class Store:
    """Open a short-lived connection for each database operation."""

    def __init__(self, path):
        self.path = path
        # SQLite table rebuilds require foreign keys off on this connection.
        # Check all references before committing the rebuild.
        with self.transaction(write=True, foreign_keys=False) as db:
            columns = {row["name"] for row in db.execute("PRAGMA table_info(opening_lines)")}
            if columns and ("parent_line_id" not in columns
                            or columns & {"opening_family", "side_in_games"}):
                self._rebuild_catalog(db, columns)
            run_statements(db, CATALOG_SCHEMA + PRACTICE_SCHEMA)

    @staticmethod
    def _rebuild_catalog(db, columns):
        """Move an older catalog to the current layout, keeping every line ID."""
        if "opening_family" in columns:
            side = "family_side" if "family_side" in columns else "NULL"
            rows = db.execute(f"""
                SELECT line_id, opening_family AS family, NULL AS family_id,
                       {side} AS side, name, eco, moves_uci
                FROM opening_lines
            """).fetchall()
        else:
            rows = db.execute("""
                SELECT o.line_id, f.name AS family, f.family_id, f.family_side AS side,
                       o.name, o.eco, o.moves_uci
                FROM opening_lines AS o
                JOIN opening_families AS f USING (family_id)
            """).fetchall()

        own_sides, merged_sides, kept_ids = {}, {}, {}
        for row in rows:
            name = family_name(row["family"])
            merged_sides.setdefault(name, set()).add(row["side"])
            if name == row["family"]:
                own_sides.setdefault(name, set()).add(row["side"])
                if row["family_id"] is not None:
                    kept_ids[name] = row["family_id"]
        sides = {
            name: family_side(name, own_sides.get(name) or merged_sides[name])
            for name in merged_sides
        }

        db.execute("DROP TABLE opening_lines")
        db.execute("DROP TABLE IF EXISTS opening_families")
        run_statements(db, CATALOG_SCHEMA)
        for name in sorted(sides, key=lambda name: (name not in kept_ids, name)):
            db.execute(
                "INSERT INTO opening_families (family_id, name, family_side) VALUES (?, ?, ?)",
                (kept_ids.get(name), name, sides[name]),
            )
        family_ids = {
            row["name"]: row["family_id"]
            for row in db.execute("SELECT family_id, name FROM opening_families")
        }
        db.executemany(
            "INSERT INTO opening_lines (line_id, family_id, name, eco, moves_uci) VALUES (?, ?, ?, ?, ?)",
            [
                (row["line_id"], family_ids[family_name(row["family"])], row["name"], row["eco"], row["moves_uci"])
                for row in rows
            ],
        )
        link_parents(db)
        if db.execute("PRAGMA foreign_key_check").fetchone():
            raise ValueError("Opening catalog migration would leave invalid references")

    @contextmanager
    def transaction(self, *, write=False, foreign_keys=True):
        db = connect(self.path)
        db.row_factory = Row
        try:
            db.execute("PRAGMA foreign_keys = ON" if foreign_keys else "PRAGMA foreign_keys = OFF")
            with db:
                if write:
                    db.execute("BEGIN IMMEDIATE")
                yield db
        finally:
            db.close()

    def add_line(self, opening_family, name, eco, moves_uci, *, side=None):
        """Insert a line, or update the line with the same moves, and return its ID."""
        moves = " ".join(moves_uci.split())
        if not moves:
            raise ValueError("An opening line must contain at least one move")
        family = family_name(opening_family)
        with self.transaction(write=True) as db:
            row = db.execute(
                "SELECT family_id FROM opening_families WHERE name = ?", (family,)
            ).fetchone()
            if row is None:
                family_id = db.execute(
                    "INSERT INTO opening_families (name, family_side) VALUES (?, ?)",
                    (family, family_side(family, [side])),
                ).lastrowid
            else:
                family_id = row["family_id"]
            db.execute(
                """INSERT INTO opening_lines (family_id, name, eco, moves_uci) VALUES (?, ?, ?, ?)
                   ON CONFLICT(moves_uci) DO UPDATE SET
                       family_id = excluded.family_id, name = excluded.name, eco = excluded.eco""",
                (family_id, name, eco, moves),
            )
            link_parents(db)
            return db.execute(
                "SELECT line_id FROM opening_lines WHERE moves_uci = ?", (moves,)
            ).fetchone()["line_id"]

    def list_lines(self):
        with self.transaction() as db:
            return [
                {**dict(row), "learnable": bool(row["learnable"])}
                for row in db.execute(
                    f"""SELECT o.line_id, f.name AS opening_family, o.name, o.eco,
                               f.family_side, o.parent_line_id, {LEARNABLE} AS learnable
                        FROM opening_lines AS o
                        JOIN opening_families AS f USING (family_id)
                        ORDER BY f.name, o.name, o.line_id"""
                )
            ]

    def learning_catalog(self, player_id):
        with self.transaction() as db:
            return [
                {**dict(row), "learned": bool(row["learned"]), "learnable": bool(row["learnable"])}
                for row in db.execute(
                    f"""SELECT o.line_id, f.name AS opening_family, f.family_side, o.name, o.eco,
                               o.moves_uci, o.parent_line_id, {LEARNABLE} AS learnable,
                               p.line_id IS NOT NULL AS learned
                        FROM opening_lines AS o
                        JOIN opening_families AS f USING (family_id)
                        LEFT JOIN player_lines AS p ON p.line_id = o.line_id AND p.player_id = ?
                        ORDER BY f.name, o.name, o.line_id""",
                    (player_id,),
                )
            ]


def add_event(db, player_id, line_id, event_type, mode, at, *, session_id=None,
              side=None, move_index=None, is_correct=None, response_time_ms=None,
              fsrs_rating=None):
    db.execute(
        """INSERT INTO practice_events (
               player_id, line_id, session_id, event_type, mode, side, occurred_at,
               move_index, is_correct, response_time_ms, fsrs_rating
           ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (player_id, line_id, session_id, event_type, mode, side, timestamp(at),
         move_index, is_correct, response_time_ms, fsrs_rating),
    )
