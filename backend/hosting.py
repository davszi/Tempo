"""Initialize the hosted database and build the production WSGI app."""

import os
from contextlib import closing
from pathlib import Path
from sqlite3 import connect

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

    return create_app(database, BACKEND / "fitted_global.csv", os.getenv("TEMPO_GOOGLE_CLIENT_ID"),
                      secure_cookies=True)
