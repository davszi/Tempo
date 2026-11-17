"""Trainers: FSRS-6 step functions against py-fsrs, the input layout and the fit."""

import numpy as np
import pytest

from tempo_ml.fsrs import model as M
from tempo_ml.evaluate.metrics import auc
import torch

from tempo_ml.fsrs.train import Objective, fit, split_clients
from tempo_ml.pass_chance import mistake_limit

CPU = torch.device("cpu")

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
    c = M.load_cards(p, {("a", "L1"): 6, ("a", "L2"): 4})
    assert c.t.shape == (2, 4)
    assert c.loss_mask.sum() == 2
    assert list(c.y[c.loss_mask]) == [0.0, 1.0]
    assert list(c.row[0]) == [0, 1, 3, 4]
    assert list(c.t[0]) == [0.0, 0.0, 2.0, 1.0]          # app clock: whole elapsed days
    assert list(c.acc[c.loss_mask]) == [0.5, 1.0]
    assert list(c.m) == [6, 4]
    exact = M.load_cards(p, clock="exact")
    assert list(exact.t[0]) == [0.0, 0.01, 2.0, 1.5] and list(exact.m) == [0, 0]


def test_predict_first_step_and_padding():
    t = np.array([[0.0, 1.0, 0.0], [0.0, 3.0, 2.0]])
    g = np.array([[3, 3, 0], [1, 3, 3]])
    valid = np.array([[True, True, False], [True, True, True]])
    p = M.predict(M.DEFAULT_PARAMETERS, t, g, valid)
    assert np.isnan(p[:, 0]).all() and np.isnan(p[0, 2])
    s0 = M.DEFAULT_PARAMETERS[2]  # Good -> w[2]
    assert p[0, 1] == pytest.approx(float(M.forgetting_curve(M.DEFAULT_PARAMETERS, np.array(1.0), np.array(s0))))


def simulate_cards(w_true, n, steps, rng, per_move=False):
    """Cards drawn from FSRS itself. ``per_move``: R is per move, lines of 3-14 moves are
    graded pass (Good) when mistakes are within L(M), as in the simulator."""
    t = np.floor(rng.uniform(1, 20, (n, steps))); t[:, 0] = 0
    valid = np.ones((n, steps), bool)
    g = np.zeros((n, steps), int)
    acc = np.ones((n, steps))
    m = rng.integers(3, 15, n) if per_move else np.ones(n, int)
    g[:, 0] = rng.integers(2, 5, n)
    s = M.initial_stability(w_true, g[:, 0]); d = M.initial_difficulty(w_true, g[:, 0])
    for k in range(1, steps):
        r = M.forgetting_curve(w_true, t[:, k], s)
        mistakes = rng.binomial(m, 1 - r)
        g[:, k] = np.where(mistakes <= mistake_limit(m), 3, 1)
        acc[:, k] = (m - mistakes) / m
        s, d = M.next_stability(w_true, d, s, r, g[:, k]), M.next_difficulty(w_true, d, g[:, k])
    return M.Cards(agent=np.array(["x"] * n), t=t, g=g, valid=valid, y=(g > 1).astype(float),
                   loss_mask=np.c_[np.zeros((n, 1), bool), valid[:, 1:]], row=np.zeros((n, steps), int),
                   acc=acc, m=m)


W_TRUE = M.DEFAULT_PARAMETERS.copy()
W_TRUE[20] = 0.4
W_TRUE[0:4] = [0.5, 2.0, 4.0, 12.0]


def test_fit_recovers_known_parameters():
    """Line-level data from FSRS itself: fitting from defaults reaches the true weights' loss."""
    c = simulate_cards(W_TRUE, 1500, 12, np.random.default_rng(1))
    obj = Objective(c, c.loss_mask, "line", device=CPU)
    l_def, l_true = obj(M.DEFAULT_PARAMETERS)[0], obj(W_TRUE)[0]
    w_fit, info = fit(M.DEFAULT_PARAMETERS, c, c.loss_mask, arm="line", device=CPU)
    assert info["loss"] < l_def
    assert info["loss"] <= l_true + 1e-3


@pytest.mark.parametrize("arm", ["pass", "accuracy"])
def test_per_move_arms_recover_the_decay(arm):
    """Per-move data with the new pass rule: both per-move arms find the true decay w20,
    and their loss at the fit is no worse than at the true weights."""
    c = simulate_cards(W_TRUE, 2000, 12, np.random.default_rng(3), per_move=True)
    obj = Objective(c, c.loss_mask, arm, device=CPU)
    w_fit, info = fit(M.DEFAULT_PARAMETERS, c, c.loss_mask, arm=arm, device=CPU)
    assert info["loss"] <= obj(W_TRUE)[0] + 1e-6
    assert w_fit[20] == pytest.approx(0.4, abs=0.08)


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
