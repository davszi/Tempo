"""Trainers: FSRS-6 step functions against py-fsrs, the input layout and the fit."""

import numpy as np
import pytest

from tempo_ml.fsrs import model as M
from tempo_ml.evaluate.metrics import auc
from tempo_ml.fsrs.train import fit, objective, split_clients

fsrs = pytest.importorskip("fsrs")


@pytest.fixture(scope="module")
def sched():
    return fsrs.Scheduler()


def test_defaults_and_bounds_match_py_fsrs():
    from fsrs import scheduler as S

    assert np.allclose(M.DEFAULT_PARAMETERS, S.DEFAULT_PARAMETERS)
    assert np.allclose(M.LOWER_BOUNDS, S.LOWER_BOUNDS_PARAMETERS)
    assert np.allclose(M.UPPER_BOUNDS, S.UPPER_BOUNDS_PARAMETERS)


def test_step_functions_match_py_fsrs(sched):
    rng = np.random.default_rng(0)
    w = M.DEFAULT_PARAMETERS
    R = fsrs.Rating
    for _ in range(300):
        g = int(rng.integers(1, 5))
        s = float(rng.uniform(0.05, 200))
        d = float(rng.uniform(1, 10))
        t = float(rng.uniform(0, 300))
        r = float(M.forgetting_curve(w, np.array(t), np.array(s)))
        assert r == pytest.approx((1 + sched._FACTOR * t / s) ** sched._DECAY)
        ga = np.array([g])
        assert M.initial_stability(w, ga)[0] == pytest.approx(sched._initial_stability(rating=R(g)))
        assert M.initial_difficulty(w, ga)[0] == pytest.approx(sched._initial_difficulty(rating=R(g), clamp=True))
        assert M.next_difficulty(w, np.array([d]), ga)[0] == pytest.approx(sched._next_difficulty(difficulty=d, rating=R(g)))
        assert M.short_term_stability(w, np.array([s]), ga)[0] == pytest.approx(sched._short_term_stability(stability=s, rating=R(g)))
        assert M.next_stability(w, np.array([d]), np.array([s]), np.array([r]), ga)[0] == pytest.approx(
            sched._next_stability(difficulty=d, stability=s, retrievability=r, rating=R(g)))


def _write_sessions(path, rows):
    import csv
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["agent_name", "opening_name", "review_status", "t_days", "grade", "total_time_ms", "accuracy"])
        w.writerows(rows)


def test_load_cards_and_masks(tmp_path):
    p = tmp_path / "s.csv"
    _write_sessions(p, [
        ("a", "L1", "new", 0.0, 3, 1000, 1.0),
        ("a", "L1", "review", 0.01, 3, 1000, 1.0),   # same day: not in loss
        ("a", "L2", "new", 0.0, 4, 1000, 1.0),
        ("a", "L1", "review", 2.0, 1, 1000, 0.5),    # in loss, failure
        ("a", "L1", "relearning", 1.5, 3, 1000, 1.0),  # in loss, success
    ])
    c = M.load_cards(p)
    assert c.t.shape == (2, 4)
    assert c.loss_mask.sum() == 2
    assert list(c.y[c.loss_mask]) == [0.0, 1.0]
    assert list(c.row[0]) == [0, 1, 3, 4]


def test_predict_first_step_and_padding():
    t = np.array([[0.0, 1.0, 0.0], [0.0, 3.0, 2.0]])
    g = np.array([[3, 3, 0], [1, 3, 3]])
    valid = np.array([[True, True, False], [True, True, True]])
    p = M.predict(M.DEFAULT_PARAMETERS, t, g, valid)
    assert np.isnan(p[:, 0]).all() and np.isnan(p[0, 2])
    s0 = M.DEFAULT_PARAMETERS[2]  # Good -> w[2]
    assert p[0, 1] == pytest.approx(float(M.forgetting_curve(M.DEFAULT_PARAMETERS, np.array(1.0), np.array(s0))))


def test_fit_recovers_known_parameters():
    """Data drawn from FSRS itself: fitting from defaults lowers the loss toward the truth."""
    rng = np.random.default_rng(1)
    w_true = M.DEFAULT_PARAMETERS.copy()
    w_true[20] = 0.4
    w_true[0:4] = [0.5, 2.0, 4.0, 12.0]
    n, steps = 1500, 12
    t = rng.uniform(1, 20, (n, steps)); t[:, 0] = 0
    valid = np.ones((n, steps), bool)
    g = np.zeros((n, steps), int)
    g[:, 0] = rng.integers(2, 5, n)
    s = M.initial_stability(w_true, g[:, 0]); d = M.initial_difficulty(w_true, g[:, 0])
    for k in range(1, steps):
        r = M.forgetting_curve(w_true, t[:, k], s)
        ok = rng.random(n) < r
        g[:, k] = np.where(ok, 3, 1)
        s, d = M.next_stability(w_true, d, s, r, g[:, k]), M.next_difficulty(w_true, d, g[:, k])
    Cards = M.Cards
    c = Cards(agent=np.array(["x"] * n), t=t, g=g, valid=valid, y=(g > 1).astype(float),
              loss_mask=np.c_[np.zeros((n, 1), bool), valid[:, 1:]], row=np.zeros((n, steps), int))
    l_def = objective(M.DEFAULT_PARAMETERS, c, c.loss_mask)
    l_true = objective(w_true, c, c.loss_mask)
    w_fit, info = fit(M.DEFAULT_PARAMETERS, c, c.loss_mask, maxiter=150)
    assert info["loss"] < l_def
    assert info["loss"] <= l_true + 0.005


def test_auc_simple():
    assert auc(np.array([0.1, 0.2, 0.8, 0.9]), np.array([0, 0, 1, 1])) == 1.0
    assert auc(np.array([0.5, 0.5]), np.array([0, 1])) == 0.5


def test_split_is_disjoint_and_stratified():
    import pandas as pd
    clients = pd.DataFrame({"agent_name": [f"c{i}" for i in range(30)], "archetype": ["a", "b", "c"] * 10})
    parts = split_clients(clients, 0)
    allc = parts["fit"] | parts["validation"] | parts["test"]
    assert len(allc) == 30 and sum(len(v) for v in parts.values()) == 30
    assert len(parts["test"]) == 6
