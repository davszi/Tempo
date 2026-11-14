"""Simulator: clients, recall, grading, the catalog reader and the generator.

Client tests run in memory; generator tests write only to pytest's tmp dir.
The ``Line`` objects below are test fixtures, not opening data."""

import math

import numpy as np
import pytest

import csv
import json
import sqlite3

from tempo_ml.catalog import DEFAULT_CATALOG_DB, load_opening_lines
from tempo_ml.simulator.generate import GenerationConfig, generate
from tempo_ml.simulator import (
    CSV_COLUMNS,
    SessionRecord,
    calculate_session_grade,
    ARCHETYPES,
    ClientTraits,
    Line,
    MultiplicativeStability,
    SyntheticClient,
    TraitDistribution,
    build_population,
    cognitive_strain,
    next_reps,
    practice_multiplier,
    retrievability,
)

LINE = Line("Test Opening: Line A", num_moves=6)


# ------------------------------------------------------------------ formulas

def test_F_matches_definition():
    t = ARCHETYPES["balanced"]
    assert t.F == pytest.approx(0.9 ** (-1 / t.C) - 1)


def test_strain_and_practice_boundaries():
    assert cognitive_strain(2.2, 1.0) == 1.0
    assert cognitive_strain(1.0, 0.0) == pytest.approx(math.e)
    assert practice_multiplier(0.25, 0) == 1.0
    assert practice_multiplier(0.25, 10_000) < 1e-3


def test_trait_validation():
    with pytest.raises(ValueError):
        ClientTraits(baseline_ms=100, mu=0, sigma=0.4, beta=1, alpha=0.25, C=0.5)
    with pytest.raises(ValueError):
        ClientTraits(baseline_ms=300, mu=0, sigma=0.4, beta=1, alpha=0.9, C=0.5)


def test_archetypes_match_record_table():
    b, m, d = ARCHETYPES["blitzer"], ARCHETYPES["balanced"], ARCHETYPES["diligent"]
    assert (b.baseline_ms, b.mu, b.sigma, b.beta, b.alpha, b.C) == (220, -0.6, 0.45, 0.4, 0.35, 0.65)
    assert (m.baseline_ms, m.mu, m.sigma, m.beta, m.alpha, m.C) == (300, -0.2, 0.40, 1.0, 0.25, 0.50)
    assert (d.baseline_ms, d.mu, d.sigma, d.beta, d.alpha, d.C) == (380, 0.3, 0.35, 2.2, 0.20, 0.35)


# ------------------------------------------------------------------- grading


def test_grading_function():
    assert calculate_session_grade(1, 100, 4, 300) == 1
    assert calculate_session_grade(0, 4 * (300 + 499), 4, 300) == 4
    assert calculate_session_grade(0, 4 * (300 + 500), 4, 300) == 3
    assert calculate_session_grade(0, 4 * (300 + 1800), 4, 300) == 3
    assert calculate_session_grade(0, 4 * (300 + 1801), 4, 300) == 2


# ------------------------------------------------------------------ sessions

def make(arch="balanced", seed=0, **kw):
    return SyntheticClient(name=f"synth_{arch}_01", traits=ARCHETYPES[arch], seed=seed, **kw)


def test_first_learn_is_new_then_learning():
    c = make()
    first = c.learn(LINE, day=0.0)
    assert first.record.review_status == "new"
    assert first.record.t_days == 0.0
    assert first.record.accuracy == 1.0
    assert first.stability_before is None
    assert first.stability_after == MultiplicativeStability().initial_days
    second = c.learn(LINE, day=1.0)
    assert second.record.review_status == "learning"
    assert second.record.t_days == 1.0


def test_review_requires_learned_line():
    with pytest.raises(ValueError):
        make().review(LINE, day=0.0)


def test_session_time_goes_backwards_rejected():
    c = make()
    c.learn(LINE, day=5.0)
    with pytest.raises(ValueError):
        c.review(LINE, day=4.0)


def test_record_fields_consistent():
    c = make(seed=3)
    c.learn(LINE, day=0.0)
    out = c.review(LINE, day=2.0)
    r = out.record
    assert isinstance(r, SessionRecord)
    assert set(r.to_row()) == set(CSV_COLUMNS)
    assert r.agent_name == "synth_balanced_01"
    assert r.t_days == 2.0
    assert r.total_time_ms == round(sum(m.time_ms for m in out.moves))
    assert r.accuracy == (LINE.num_moves - out.blunder_count) / LINE.num_moves
    assert out.retrievability == pytest.approx(retrievability(2.0, 1.0, ARCHETYPES["balanced"].C))
    expected_grade = calculate_session_grade(
        out.blunder_count, sum(m.time_ms for m in out.moves), LINE.num_moves, 300
    )
    assert r.grade == expected_grade
    assert all(t >= 300 for m in out.moves for t in m.attempt_times_ms)


def test_blunder_gives_again_relearning_and_penalty():
    # Force a lapse: tiny stability, long gap -> R near 0.
    c = make(seed=1, stability_model=MultiplicativeStability(initial_days=0.01))
    c.learn(LINE, 0.0)
    c.learn(LINE, 0.0)
    c.learn(LINE, 0.0)
    reps_before = c.memory(LINE).reps
    out = c.review(LINE, day=10_000.0)
    assert out.blunder_count > 0
    assert out.record.grade == 1
    assert out.record.accuracy < 1.0
    assert out.reps_after == max(0, reps_before - 2)
    assert out.stability_after <= out.stability_before
    assert any(len(m.attempt_times_ms) > 1 for m in out.moves)
    assert all(len(m.attempt_times_ms) <= c.max_attempts_per_move for m in out.moves)
    nxt = c.review(LINE, day=10_000.0)
    assert nxt.record.review_status == "relearning"


def test_clean_review_grows_stability_and_reps():
    c = make(seed=2)
    c.learn(LINE, 0.0)
    out = c.review(LINE, day=0.0)  # R = 1 -> always clean
    assert out.blunder_count == 0
    assert out.record.review_status == "review"
    assert out.reps_after == out.reps_before + 1
    assert out.stability_after > out.stability_before


def test_determinism_same_seed():
    def run(seed):
        c = make(seed=seed)
        c.learn(LINE, 0.0)
        return [c.review(LINE, d).record for d in (1.0, 3.0, 9.0)]

    assert run(42) == run(42)
    assert run(42) != run(43)


def test_practice_drives_latency_toward_baseline():
    t = ARCHETYPES["diligent"]
    rng = np.random.default_rng(0)
    from tempo_ml.simulator import sample_move_time_ms

    fresh = np.mean([sample_move_time_ms(t, 1.0, 0, rng) for _ in range(2000)])
    drilled = np.mean([sample_move_time_ms(t, 1.0, 500, rng) for _ in range(2000)])
    assert drilled < fresh
    assert drilled - t.baseline_ms < 0.05 * (fresh - t.baseline_ms)


def test_low_R_increases_latency_for_high_effort():
    t = ARCHETYPES["diligent"]
    rng = np.random.default_rng(0)
    from tempo_ml.simulator import sample_move_time_ms

    high = np.median([sample_move_time_ms(t, 1.0, 0, rng) for _ in range(3000)])
    low = np.median([sample_move_time_ms(t, 0.2, 0, rng) for _ in range(3000)])
    assert low > high


# ---------------------------------------------------------------- population


def test_build_population_names_and_traits():
    pop = build_population({"blitzer": 2, "diligent": 3}, seed=7)
    assert [c.name for c in pop] == [
        "synth_blitzer_01",
        "synth_blitzer_02",
        "synth_diligent_01",
        "synth_diligent_02",
        "synth_diligent_03",
    ]
    assert all(c.traits == ARCHETYPES[c.archetype] for c in pop)


def test_population_reproducible_and_streams_differ():
    a = build_population({"balanced": 2}, seed=1)
    b = build_population({"balanced": 2}, seed=1)
    for c in a + b:
        c.learn(LINE, 0.0)
    ra = [c.review(LINE, 3.0).record.total_time_ms for c in a]
    rb = [c.review(LINE, 3.0).record.total_time_ms for c in b]
    assert ra == rb
    assert ra[0] != ra[1]


def test_trait_distribution_sampling_clamps():
    dist = TraitDistribution.diagonal(ARCHETYPES["balanced"], {"baseline_ms": 400, "alpha": 1.0})
    pop = build_population({"balanced": 50}, seed=0, distributions={"balanced": dist})
    assert len({c.traits for c in pop}) > 1
    assert all(150 <= c.traits.baseline_ms <= 500 for c in pop)
    assert all(0.1 <= c.traits.alpha <= 0.5 for c in pop)


def test_unknown_archetype_rejected():
    with pytest.raises(KeyError):
        build_population({"grandmaster": 1}, seed=0)


def test_memory_keyed_by_line_id_not_name():
    c = make(seed=5)
    a = Line("Same Name", num_moves=4, line_id="X-1")
    b = Line("Same Name", num_moves=6, line_id="X-2")
    c.learn(a, 0.0)
    assert c.knows(a) and not c.knows(b)


# ------------------------------------------------------------------ catalog and generator

MOVES = "e2e4 e7e5 g1f3 b8c6 f1c4 f8c5 c2c3 g8f6 d2d4"


@pytest.fixture
def tiny_catalog(tmp_path):
    """A catalog with the backend schema: 3 families, 12 lines."""
    db = tmp_path / "catalog.sqlite"
    con = sqlite3.connect(db)
    con.executescript("""
        CREATE TABLE opening_families (family_id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE,
                                       family_side TEXT);
        CREATE TABLE opening_lines (line_id INTEGER PRIMARY KEY, family_id INTEGER NOT NULL,
                                    name TEXT NOT NULL, eco TEXT NOT NULL,
                                    moves_uci TEXT NOT NULL UNIQUE);
    """)
    con.executemany("INSERT INTO opening_families VALUES (?, ?, ?)",
                    [(1, "Italian Game", "white"), (2, "Sicilian Defense", "black"), (3, "Queen's Pawn", "white")])
    rows = []
    for i in range(12):
        plies = 7 + i % 3
        moves = " ".join(MOVES.split()[:plies - 1] + [f"x{i}"])  # unique move strings
        rows.append((100 + i, 1 + i % 3, f"Line {i}", "C50", moves))
    con.executemany("INSERT INTO opening_lines VALUES (?, ?, ?, ?, ?)", rows)
    con.commit()
    con.close()
    return db


def test_tiny_catalog_fields(tiny_catalog):
    lines = load_opening_lines(tiny_catalog)
    assert len(lines) == 12
    first = lines[0]
    assert first.line_id == "100" and first.family == "Italian Game" and first.family_side == "white"
    assert (first.plies, first.white_moves, first.black_moves) == (7, 4, 3)
    assert first.as_line("black").num_moves == first.black_moves
    assert lines[2].playable_by("white") and not lines[2].playable_by("black")


def test_backend_catalog_loads():
    if not DEFAULT_CATALOG_DB.exists():
        pytest.skip("backend catalog not present")
    lines = load_opening_lines()
    assert len({l.line_id for l in lines}) == len(lines) > 0
    assert min(l.white_moves for l in lines) >= 4  # cleaned catalog: at least four White moves


def test_generate_tiny_dataset(tmp_path, tiny_catalog):
    cfg = GenerationConfig(seed=3, clients_per_archetype=2, horizon_days=20)
    m = generate(tmp_path / "out", cfg, tiny_catalog)
    assert m["counts"]["clients"] == 6
    assert m["inputs"]["opening_catalog"]["lines"] == 12
    with open(tmp_path / "out" / "sessions.csv") as f:
        rows = list(csv.DictReader(f))
    assert tuple(rows[0]) == CSV_COLUMNS
    assert len(rows) == m["counts"]["sessions"]
    # (agent, opening_name) starts with a "new" session
    first = {}
    for r in rows:
        first.setdefault((r["agent_name"], r["opening_name"]), r["review_status"])
    assert set(first.values()) == {"new"}
    # reproducible
    m2 = generate(tmp_path / "again", cfg, tiny_catalog)
    assert m2["outputs"]["sessions.csv"] == m["outputs"]["sessions.csv"]
    json.dumps(m)
