"""Coordinate SQLite and the ML engine for Repeating."""

from .store import add_event, timestamp


class MLController:
    def __init__(self, store, engine):
        self.store = store
        self.engine = engine

    def suggest(self, player_id, now):
        with self.store.transaction(write=True) as db:
            repertoire = db.execute(
                "SELECT * FROM player_lines WHERE player_id = ?", (player_id,)
            ).fetchall()
            if not repertoire:
                return "learn_first", None
            line_id = self.engine.select_line(repertoire, now)
            if line_id is None:
                return "none_due", None
            add_event(db, player_id, line_id, "line_suggested", "repeating", now)
            return "ready", line_id

    def initialize_progress(self, db, player_id, line_id, now):
        existing = db.execute(
            "SELECT 1 FROM player_lines WHERE player_id = ? AND line_id = ?",
            (player_id, line_id),
        ).fetchone()
        if existing:
            return
        due, state = self.engine.initial_schedule(now)
        db.execute(
            """INSERT INTO player_lines (player_id, line_id, learned_at, next_review_at, fsrs_state)
               VALUES (?, ?, ?, ?, ?)""",
            (player_id, line_id, timestamp(now), timestamp(due), state),
        )

    def complete_review(self, db, player_id, line_id, session_id, now):
        progress = db.execute(
            "SELECT fsrs_state FROM player_lines WHERE player_id = ? AND line_id = ?",
            (player_id, line_id),
        ).fetchone()
        attempts = db.execute(
            """SELECT move_index, is_correct, response_time_ms FROM practice_events
               WHERE player_id = ? AND line_id = ? AND session_id = ?
                 AND event_type = 'move_attempted' ORDER BY event_id""",
            (player_id, line_id, session_id),
        ).fetchall()
        grade, due, state = self.engine.schedule_review(
            progress["fsrs_state"], attempts, now
        )
        db.execute(
            """UPDATE player_lines SET last_reviewed_at = ?, next_review_at = ?, fsrs_state = ?
               WHERE player_id = ? AND line_id = ?""",
            (timestamp(now), timestamp(due), state, player_id, line_id),
        )
        return grade
