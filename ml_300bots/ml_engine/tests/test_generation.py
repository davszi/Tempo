"""Opening loader and generator on a tiny config (writes only to pytest's tmp dir)."""

import csv
import json

from tempo_ml.openings import load_opening_lines
from tempo_ml.review_dataset import CSV_COLUMNS
from tempo_ml.synthetic_data import GenerationConfig, generate


def test_library_loads_with_unique_ids():
    lines = load_opening_lines()
    assert len(lines) == 3865
    assert len({l.line_id for l in lines}) == len(lines)
    sic = next(l for l in lines if l.name.startswith("Sicilian Defense"))
    assert sic.playable_by("black")
    assert sic.as_line("black").num_moves == sic.black_moves


def test_generate_tiny_dataset(tmp_path):
    cfg = GenerationConfig(seed=3, clients_per_archetype=2, horizon_days=20)
    m = generate(tmp_path, cfg)
    assert m["counts"]["clients"] == 6
    with open(tmp_path / "sessions.csv") as f:
        rows = list(csv.DictReader(f))
    assert tuple(rows[0]) == CSV_COLUMNS
    assert len(rows) == m["counts"]["sessions"]
    # (agent, opening_name) starts with a "new" session
    first = {}
    for r in rows:
        first.setdefault((r["agent_name"], r["opening_name"]), r["review_status"])
    assert set(first.values()) == {"new"}
    # reproducible
    m2 = generate(tmp_path / "again", cfg)
    assert m2["outputs"]["sessions.csv"] == m["outputs"]["sessions.csv"]
    json.dumps(m)
