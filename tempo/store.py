"""SQLite persistence for the three TEMPO tables."""

from contextlib import contextmanager
from datetime import timezone
from sqlite3 import Row, connect


OPENING_SIDE_COLUMNS = ("family_side", "side_in_games")
SIDE_VALUES = "('white', 'black', 'both')"

SCHEMA = f"""
CREATE TABLE IF NOT EXISTS opening_lines (
    line_id INTEGER PRIMARY KEY,
    opening_family TEXT NOT NULL,
    name TEXT NOT NULL,
    eco TEXT NOT NULL,
    moves_uci TEXT NOT NULL,
    family_side TEXT CHECK (family_side IN {SIDE_VALUES}),
    side_in_games TEXT CHECK (side_in_games IN {SIDE_VALUES})
);

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
        with self.transaction() as db:
            db.executescript(SCHEMA)
        with self.transaction(write=True) as db:
            columns = {row["name"] for row in db.execute("PRAGMA table_info(opening_lines)")}
            for column in OPENING_SIDE_COLUMNS:
                if column not in columns:
                    db.execute(
                        f"ALTER TABLE opening_lines ADD COLUMN {column} TEXT "
                        f"CHECK ({column} IN {SIDE_VALUES})"
                    )

    @contextmanager
    def transaction(self, *, write=False):
        db = connect(self.path)
        db.row_factory = Row
        try:
            db.execute("PRAGMA foreign_keys = ON")
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
            cursor = db.execute(
                """INSERT INTO opening_lines (
                       opening_family, name, eco, moves_uci, family_side, side_in_games
                   ) VALUES (?, ?, ?, ?, ?, ?)""",
                (opening_family, name, eco, " ".join(moves), family_side, side_in_games),
            )
            return cursor.lastrowid

    def list_lines(self):
        with self.transaction() as db:
            return [dict(row) for row in db.execute(
                """SELECT line_id, opening_family, name, eco, family_side, side_in_games
                   FROM opening_lines
                   ORDER BY opening_family, name, line_id"""
            )]


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
