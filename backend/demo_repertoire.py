"""Seed a demo account with repertoire and review history through the production FSRS engine."""

import json
from datetime import datetime, timedelta, timezone

from fsrs import Card

from .ml_engine import MLEngine
from .store import LEARNABLE, add_event, timestamp


SEED_SESSION = "tempo-repertoire-demo-v1"

# The last scheduled review lands this many days from the demo setup time.
# Zero means already due today. Empty grade histories represent first recalls.
DEMO_LINES = (
    ("London System", -4, ("Good", "Again")),
    ("London System", 3, ("Good", "Good")),
    ("Italian Game", -2, ("Hard", "Good")),
    ("Italian Game", 5, ("Good", "Easy")),
    ("Caro-Kann Defense", -1, ("Again", "Hard")),
    ("Caro-Kann Defense", 0, ("Good", "Hard")),
    ("Scandinavian Defense", 0, ()),
    ("Scandinavian Defense", 2, ("Good", "Good")),
    ("Colle System", 1, ()),
    ("Four Knights Game", 3, ("Good", "Easy")),
    ("Scotch Game", 5, ("Good", "Good")),
    ("Queen's Gambit", 7, ("Good", "Good")),
    ("Queen's Gambit", 10, ("Good", "Easy")),
    ("Slav Defense", 10, ("Good", "Easy")),
    ("French Defense", 14, ("Good", "Good", "Easy")),
    ("Vienna Game", 14, ("Good", "Good", "Easy")),
)


def demo_schedule(engine, now, days_until_due, grades):
    """Replay grades and move the history in time so its schedule fits the demo calendar."""
    due, state = engine.initial_schedule(now)
    reviewed_at = now
    reviews = []
    for grade in grades:
        reviewed_at = min(due, reviewed_at + timedelta(days=2))
        _, due, state = engine.schedule_review(state, (), reviewed_at, grade=grade)
        reviews.append((reviewed_at, grade))

    target = now + timedelta(days=days_until_due)
    if grades and days_until_due == 0:
        target -= timedelta(minutes=1)
    if not grades:
        target = target.replace(hour=0, minute=0, second=0, microsecond=0)
    shift = target - due
    card = Card.from_dict(json.loads(state))
    card.due = target
    if card.last_review is not None:
        card.last_review += shift
        if card.last_review > now:
            raise ValueError("Demo review interval is shorter than the requested calendar offset")

    return now + shift, target, json.dumps(card.to_dict()), [
        (at + shift, grade) for at, grade in reviews
    ]


def seed_demo_repertoire(store, weights, email):
    """Add the demo once for an existing account. None means the account was absent."""
    now = datetime.now(timezone.utc)
    with store.transaction(write=True) as db:
        user = db.execute("SELECT user_id FROM users WHERE email = ?", (email.strip().lower(),)).fetchone()
        if user is None:
            return None
        player_id = user["user_id"]
        if db.execute(
            "SELECT 1 FROM practice_events WHERE player_id = ? AND session_id = ?",
            (player_id, SEED_SESSION),
        ).fetchone():
            return 0

        engine = MLEngine.from_weights_file(weights)
        added = 0
        for family, offset, grades in DEMO_LINES:
            line = db.execute(
                f"""SELECT o.line_id, f.family_side
                    FROM opening_lines AS o JOIN opening_families AS f USING (family_id)
                    WHERE f.name = ? AND {LEARNABLE}
                      AND NOT EXISTS (
                          SELECT 1 FROM player_lines AS p WHERE p.player_id = ? AND p.line_id = o.line_id
                      )
                    ORDER BY length(o.moves_uci), o.line_id LIMIT 1""",
                (family, player_id),
            ).fetchone()
            if line is None:
                continue
            line_id, side = line["line_id"], line["family_side"]
            learned, due, state, reviews = demo_schedule(engine, now, offset, grades)
            last_review = timestamp(reviews[-1][0]) if reviews else None
            db.execute(
                """INSERT INTO player_lines
                   (player_id, line_id, learned_at, last_reviewed_at, next_review_at, fsrs_state)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (player_id, line_id, timestamp(learned), last_review, timestamp(due), state),
            )
            add_event(db, player_id, line_id, "session_completed", "learning", learned,
                      session_id=SEED_SESSION, side=side)
            for index, (reviewed, grade) in enumerate(reviews):
                add_event(db, player_id, line_id, "session_completed", "repeating", reviewed,
                          session_id=f"{SEED_SESSION}:{line_id}:{index}", side=side, fsrs_rating=grade)
            added += 1
        return added
