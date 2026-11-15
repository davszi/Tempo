"""Backend entry points for a chess UI."""

from dataclasses import dataclass
from datetime import datetime, timezone
from threading import Lock
from time import monotonic
from uuid import uuid4

from .ml_controller import MLController
from .ml_engine import MLEngine
from .store import Store, add_event, is_learnable, repertoire_rows, timestamp


def utc_now():
    return datetime.now(timezone.utc)


@dataclass
class Session:
    player_id: str
    line_id: int
    mode: str
    name: str
    moves: tuple[str, ...]
    side: str | None = None
    move_index: int = 0
    move_started: float = 0.0


class PracticeController:
    """Own active sessions, move checking and feedback for one app process."""

    def __init__(self, store, ml, *, now=utc_now, timer=monotonic):
        self.store = store
        self.ml = ml
        self.now = now
        self.timer = timer
        self.sessions = {}
        self.lock = Lock()

    def list_lines(self):
        return self.store.list_lines()

    def learning_catalog(self, player_id):
        return self.store.learning_catalog(player_id)

    def start_learning(self, player_id, line_id, side, resume_at=0):
        """Open a Learning session, optionally at a saved position where the player is to move."""
        with self.lock:
            view = self._open_line(player_id, line_id, "learning", side)
            if resume_at:
                session_id, session = self.sessions[player_id]
                own_turn = side == "both" or resume_at % 2 == (side == "black")
                if not (isinstance(resume_at, int) and 0 < resume_at < len(session.moves) and own_turn):
                    raise ValueError("The saved position does not belong to this line and side")
                session.move_index = resume_at
                view = self._view(session_id, session)
            return view

    def repertoire(self, player_id):
        """Every learned line with its schedule, current chance of recall and review history."""
        now = self.now()
        engine = self.ml.engine
        with self.store.transaction() as db:
            rows = repertoire_rows(db, player_id)
        lines = []
        for row in rows:
            stability, recall = engine.memory(row.pop("fsrs_state"), now)
            lines.append({**row, "stability_days": stability, "recall": recall})
        return {"now": timestamp(now), "target_recall": engine.target_recall, "lines": lines}

    def start_review_line(self, player_id, line_id):
        """Review one chosen repertoire line now, from its opening family's side."""
        with self.lock:
            with self.store.transaction() as db:
                row = db.execute(
                    """SELECT f.family_side FROM player_lines AS p
                       JOIN opening_lines AS o USING (line_id)
                       JOIN opening_families AS f USING (family_id)
                       WHERE p.player_id = ? AND p.line_id = ?""",
                    (player_id, line_id),
                ).fetchone()
            if row is None:
                raise LookupError("This line is not in your repertoire")
            return self._open_line(player_id, line_id, "repeating", row["family_side"])

    def abandon_review(self, player_id, session_id):
        """Close a review the player stopped after a mistake to re-learn the line; it is graded Again."""
        with self.lock:
            session = self._get_session(player_id, session_id)
            if session.mode != "repeating" or session.side is None:
                raise ValueError("Only a running review can be closed early")
            now = self.now()
            with self.store.transaction(write=True) as db:
                mistake = db.execute(
                    """SELECT 1 FROM practice_events WHERE player_id = ? AND session_id = ?
                         AND event_type = 'move_attempted' AND is_correct = 0 LIMIT 1""",
                    (player_id, session_id),
                ).fetchone()
                if mistake is None:
                    raise ValueError("Only a review with a mistake can be closed early")
                grade = self.ml.complete_review(db, player_id, session.line_id, session_id, now)
                add_event(
                    db, player_id, session.line_id, "session_completed", session.mode, now,
                    session_id=session_id, side=session.side, fsrs_rating=grade,
                )
            del self.sessions[player_id]
            return {"status": "closed", "line_id": session.line_id, "fsrs_rating": grade}

    def start_repeating(self, player_id):
        with self.lock:
            status, line_id = self.ml.suggest(player_id, self.now())
            if line_id is None:
                return {"status": status}
            return self._open_line(player_id, line_id, "repeating")

    def _open_line(self, player_id, line_id, mode, side=None):
        with self.store.transaction() as db:
            line = db.execute(
                "SELECT name, moves_uci FROM opening_lines WHERE line_id = ?", (line_id,)
            ).fetchone()
            if line is None:
                raise LookupError("Unknown opening line")
            if mode == "learning" and not is_learnable(db, line_id):
                raise ValueError("This line is extended by longer lines; learn one of those instead")

        session_id = uuid4().hex
        session = Session(player_id, line_id, mode, line["name"], tuple(line["moves_uci"].split()))
        if side is not None:
            self._choose_side(session, side)
        elif mode == "learning":
            raise ValueError("Learning requires a side")

        # One active session per player in this app process.
        self.sessions[player_id] = (session_id, session)
        return self._view(session_id, session)

    def choose_review_side(self, player_id, session_id, side):
        with self.lock:
            session = self._get_session(player_id, session_id)
            if session.mode != "repeating" or session.side is not None:
                raise ValueError("The review is not waiting for a side")
            self._choose_side(session, side)
            return self._view(session_id, session)

    def _get_session(self, player_id, session_id):
        active = self.sessions.get(player_id)
        if active is None or active[0] != session_id:
            raise LookupError("Unknown or closed practice session")
        return active[1]

    @staticmethod
    def _available_sides(session):
        return ["white", "black", "both"] if len(session.moves) >= 2 else ["white"]

    def _choose_side(self, session, side):
        if side not in self._available_sides(session):
            raise ValueError("This line cannot be played from the selected side")
        session.side = side
        session.move_index = int(side == "black")
        session.move_started = self.timer()

    @staticmethod
    def _view(session_id, session):
        index = session.move_index
        complete = index == len(session.moves)
        status = "choose_side" if session.side is None else "complete" if complete else "play"
        return {
            "status": status,
            "session_id": session_id,
            "line_id": session.line_id,
            "name": session.name,
            "mode": session.mode,
            "side": session.side,
            "available_sides": PracticeController._available_sides(session),
            "move_index": index,
            "total_plies": len(session.moves),
            "played_moves": list(session.moves[:index]),
            "hint": session.moves[index] if session.mode == "learning" and not complete else None,
        }

    def submit_move(self, player_id, session_id, move_index, move_uci):
        with self.lock:
            session = self._get_session(player_id, session_id)
            if session.side is None or move_index != session.move_index:
                raise ValueError("The move does not belong to the current position")

            correct = move_uci == session.moves[move_index]
            next_index = move_index
            if correct:
                step = 1 if session.side == "both" else 2
                next_index = min(move_index + step, len(session.moves))
            complete = next_index == len(session.moves)
            now = self.now()
            elapsed_ms = max(0, round((self.timer() - session.move_started) * 1000))
            grade = None

            with self.store.transaction(write=True) as db:
                add_event(
                    db, player_id, session.line_id, "move_attempted", session.mode, now,
                    session_id=session_id, side=session.side, move_index=move_index,
                    is_correct=correct, response_time_ms=elapsed_ms,
                )
                if complete:
                    if session.mode == "learning":
                        self.ml.initialize_progress(db, player_id, session.line_id, now)
                    else:
                        grade = self.ml.complete_review(db, player_id, session.line_id, session_id, now)
                    add_event(
                        db, player_id, session.line_id, "session_completed", session.mode, now,
                        session_id=session_id, side=session.side, fsrs_rating=grade,
                    )

            session.move_index = next_index
            session.move_started = self.timer()
            if complete:
                del self.sessions[player_id]
            # After a wrong move in Repeating, name the expected move so the app can show it once.
            expected = session.moves[move_index] if not correct and session.mode == "repeating" else None
            return {**self._view(session_id, session), "correct": correct, "fsrs_rating": grade,
                    "expected_move": expected}


def create_backend(database_path, *, baseline_ms=0, weights_file=None):
    """Build a controller for a file-backed SQLite database."""
    engine = (
        MLEngine(baseline_ms=baseline_ms) if weights_file is None
        else MLEngine.from_weights_file(weights_file, baseline_ms=baseline_ms)
    )
    store = Store(database_path)
    return PracticeController(store, MLController(store, engine))
