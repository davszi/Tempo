"""Initialize the hosted database and build the production WSGI app."""

import logging
import os
from contextlib import closing
from pathlib import Path
from sqlite3 import connect

from .demo_repertoire import seed_demo_repertoire
from .store import Store
from .web import BACKEND, create_app


def hosted_app():
    database = Path(os.environ["TEMPO_DATABASE"])
    store = Store(database)
    with store.transaction(write=True) as db:
        if not db.execute("SELECT 1 FROM opening_lines LIMIT 1").fetchone():
            seed = (BACKEND / "tempo_demo.sqlite").as_uri() + "?mode=ro"
            db.execute("PRAGMA defer_foreign_keys = ON")
            with closing(connect(seed, uri=True)) as catalog:
                db.executemany(
                    "INSERT INTO opening_families (family_id, name, family_side) VALUES (?, ?, ?)",
                    catalog.execute("SELECT family_id, name, family_side FROM opening_families"),
                )
                db.executemany(
                    "INSERT INTO opening_lines (line_id, family_id, parent_line_id, name, eco, moves_uci) VALUES (?, ?, ?, ?, ?, ?)",
                    catalog.execute("SELECT line_id, family_id, parent_line_id, name, eco, moves_uci FROM opening_lines"),
                )

    weights = BACKEND / "fitted_global.csv"
    app = create_app(database, weights, os.getenv("TEMPO_GOOGLE_CLIENT_ID"), secure_cookies=True)
    demo_email = os.getenv("TEMPO_DEMO_REPERTOIRE_EMAIL")
    if demo_email:
        logger = logging.getLogger("gunicorn.error")
        added = seed_demo_repertoire(store, weights, demo_email)
        if added is None:
            logger.warning("Demo repertoire account was not found")
        else:
            logger.info("Demo repertoire seed added %d lines", added)
    return app
