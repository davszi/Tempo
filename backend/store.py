"""SQLite persistence for the TEMPO catalog and practice history."""

from contextlib import contextmanager
from datetime import timezone
from sqlite3 import Row, connect


SIDE_VALUES = "('white', 'black', 'both')"

FAMILY_SCHEMA = f"""
CREATE TABLE IF NOT EXISTS opening_families (
    family_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    family_side TEXT CHECK (family_side IN {SIDE_VALUES})
)"""

LINE_SCHEMA = f"""
CREATE TABLE IF NOT EXISTS {{table}} (
    line_id INTEGER PRIMARY KEY,
    family_id INTEGER NOT NULL REFERENCES opening_families,
    name TEXT NOT NULL,
    eco TEXT NOT NULL,
    moves_uci TEXT NOT NULL UNIQUE,
    side_in_games TEXT CHECK (side_in_games IN {SIDE_VALUES})
)"""

SCHEMA = f"""
{FAMILY_SCHEMA};
{LINE_SCHEMA.format(table="opening_lines")};
CREATE INDEX IF NOT EXISTS opening_lines_family ON opening_lines (family_id);
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


def timestamp(value):
    return value.astimezone(timezone.utc).isoformat(timespec="microseconds")


class Store:
    """Open a short-lived connection for each database operation."""

    def __init__(self, path):
        self.path = path
        # SQLite table rebuilds require foreign keys off on this connection.
        # Check all references before committing the rebuild.
        with self.transaction(write=True, foreign_keys=False) as db:
            columns = {row["name"] for row in db.execute("PRAGMA table_info(opening_lines)")}
            if "opening_family" in columns:
                self._split_opening_families(db, columns)
            for statement in SCHEMA.strip().rstrip(";").split(";"):
                db.execute(statement)

    @staticmethod
    def _split_opening_families(db, columns):
        family_side = "family_side" if "family_side" in columns else "NULL"
        game_side = "o.side_in_games" if "side_in_games" in columns else "NULL"
        db.execute(FAMILY_SCHEMA)
        db.execute(f"""
            INSERT INTO opening_families (name, family_side)
            SELECT opening_family,
                   CASE WHEN COUNT(DISTINCT {family_side}) = 1 THEN MAX({family_side}) END
            FROM opening_lines
            GROUP BY opening_family
            ORDER BY opening_family
        """)
        db.execute(LINE_SCHEMA.format(table="new_opening_lines"))
        db.execute(f"""
            INSERT INTO new_opening_lines (line_id, family_id, name, eco, moves_uci, side_in_games)
            SELECT o.line_id, f.family_id, o.name, o.eco, o.moves_uci, {game_side}
            FROM opening_lines AS o
            JOIN opening_families AS f ON f.name = o.opening_family
        """)
        db.execute("DROP TABLE opening_lines")
        db.execute("ALTER TABLE new_opening_lines RENAME TO opening_lines")
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

    def add_line(self, opening_family, name, eco, moves_uci, *, family_side=None, side_in_games=None):
        moves = moves_uci.split()
        if not moves:
            raise ValueError("An opening line must contain at least one move")
        with self.transaction(write=True) as db:
            db.execute(
                """INSERT INTO opening_families (name, family_side) VALUES (?, ?)
                   ON CONFLICT(name) DO UPDATE SET
                       family_side = COALESCE(opening_families.family_side, excluded.family_side)""",
                (opening_family, family_side),
            )
            family_id = db.execute(
                "SELECT family_id FROM opening_families WHERE name = ?", (opening_family,)
            ).fetchone()["family_id"]
            cursor = db.execute(
                """INSERT INTO opening_lines (
                       family_id, name, eco, moves_uci, side_in_games
                   ) VALUES (?, ?, ?, ?, ?)""",
                (family_id, name, eco, " ".join(moves), side_in_games),
            )
            return cursor.lastrowid

    def list_lines(self):
        with self.transaction() as db:
            return [dict(row) for row in db.execute(
                """SELECT o.line_id, f.name AS opening_family, o.name, o.eco,
                          f.family_side, o.side_in_games
                   FROM opening_lines AS o
                   JOIN opening_families AS f USING (family_id)
                   ORDER BY f.name, o.name, o.line_id"""
            )]

    def learning_catalog(self, player_id):
        with self.transaction() as db:
            return [
                {**dict(row), "learned": bool(row["learned"])}
                for row in db.execute(
                    """SELECT o.line_id, f.name AS opening_family, o.name, o.eco, o.moves_uci,
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
