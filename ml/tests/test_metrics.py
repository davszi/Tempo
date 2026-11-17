"""Pass chance, truth metrics, the days metric and the trainer's objectives."""

from itertools import product

import numpy as np
import pytest
import torch

from tempo_ml.fsrs import model as M
from tempo_ml.evaluate.days import days_metrics, per_move_targets, true_days
from tempo_ml.evaluate.metrics import metrics, predicted_pass, rmse_bins
from tempo_ml.fsrs.model import Cards
from tempo_ml.fsrs.train import Objective
from tempo_ml.pass_chance import mistake_limit, p_pass, per_move_target


def brute_force_pass(r, m):
    """Independent reference: enumerate all 2^M right/wrong outcomes and add the passing ones."""
    limit = {1: 0, 2: 0, 3: 0}.get(m, 1 if m <= 7 else 2 if m <= 12 else 3)
    total = 0.0
    for outcome in product((True, False), repeat=m):
        k = outcome.count(False)
        if k <= limit:
            total += r ** (m - k) * (1 - r) ** k
    return total


def test_mistake_limits_match_record():
    assert [mistake_limit(m) for m in (1, 3, 4, 7, 8, 12, 13, 18)] == [0, 0, 1, 1, 2, 2, 3, 3]


@pytest.mark.parametrize("m", [1, 2, 3, 4, 6, 7, 8, 10, 12, 13, 14])
def test_p_pass_matches_enumeration(m):
    for r in (0.5, 0.8, 0.9, 0.97):
        assert float(p_pass(r, m)) == pytest.approx(brute_force_pass(r, m), abs=1e-12)


def test_p_pass_torch_matches_numpy():
    from tempo_ml.pass_chance import binomial_terms
    m = np.array([3, 6, 10, 14])
    r = np.array([0.9, 0.85, 0.95, 0.8])
    coef = torch.tensor(binomial_terms(m))
    t = p_pass(torch.tensor(r), torch.tensor(m, dtype=torch.float64), coef)
    assert np.allclose(t.numpy(), p_pass(r, m), atol=1e-14)


def test_per_move_target_table_from_record():
    # move-recall record, section 3.3 (design arithmetic, four decimals)
    expected = {1: 0.9000, 2: 0.9487, 3: 0.9655, 4: 0.8574, 6: 0.9074, 8: 0.8531, 10: 0.8842,
                13: 0.8584, 14: 0.8691, 18: 0.8994}
    for m, r in expected.items():
        assert per_move_target(m) == pytest.approx(r, abs=5e-5)
        assert brute_force_pass(per_move_target(m), m) == pytest.approx(0.9, abs=1e-9)


def test_true_days_one_move_equals_stability():
    for C in (0.2, 0.5, 0.8):
        assert true_days(12.5, 1, C) == pytest.approx(12.5)


@pytest.mark.parametrize("m", [3, 6, 10, 14])
def test_true_days_solves_pass_chance(m):
    S, C = 20.0, 0.45
    t = float(true_days(S, m, C))
    F = 0.9 ** (-1 / C) - 1
    assert brute_force_pass((1 + F * t / S) ** (-C), m) == pytest.approx(0.9, abs=1e-9)


def test_record_example_six_moves():
    # move-recall approaches: C = 0.5, S = 10, 6 moves -> due after about 9.1 days, not 1.5
    assert float(true_days(10.0, 6, 0.5)) == pytest.approx(9.14, abs=0.01)
    assert per_move_targets([6, 6]).shape == (2,)


def test_fsrs_reaches_90_percent_at_stability():
    w = M.DEFAULT_PARAMETERS
    for s in (0.5, 3.0, 40.0):
        assert float(M.forgetting_curve(w, np.array(s), np.array(s))) == pytest.approx(0.9)


def test_predict_states_matches_predict():
    rng = np.random.default_rng(0)
    n, steps = 50, 8
    t = rng.uniform(0, 15, (n, steps)); t[:, 0] = 0
    g = rng.integers(1, 5, (n, steps))
    valid = np.ones((n, steps), bool); valid[:10, 5:] = False
    r, s_after = M.predict_states(M.DEFAULT_PARAMETERS, t, g, valid)
    assert np.allclose(r, M.predict(M.DEFAULT_PARAMETERS, t, g, valid), equal_nan=True)
    assert np.isnan(s_after[:10, 5:]).all() and not np.isnan(s_after[10:]).any()
    assert np.allclose(s_after[:, 0], M.initial_stability(M.DEFAULT_PARAMETERS, g[:, 0]))


def test_days_metrics_zero_for_perfect_and_sign():
    d = np.array([1.0, 5.0, 40.0])
    learn = np.array([True, False, False])
    perfect = days_metrics(d, d, learn, 180)
    assert perfect["median_abs_error"] == 0 and perfect["mean_error"] == 0
    early = days_metrics(d - 1, d, learn, 180)
    assert early["median_error"] == -1 and early["share_too_early"] == 1.0
    assert early["bands"]["ge30"]["sessions"] == 1


def test_truth_metrics_zero_when_prediction_is_truth():
    p = np.array([0.2, 0.7, 0.9])
    m = metrics(p, np.array([0.0, 1.0, 1.0]), truth=p)
    assert m["rmse_vs_truth"] == 0 and m["mae_vs_truth"] == 0
    assert rmse_bins(np.full(4, 0.75), np.array([1.0, 1.0, 1.0, 0.0])) == pytest.approx(0.0)


def test_predicted_pass_links():
    r = np.array([[0.9, 0.9]])
    mg = np.array([[1, 6]])
    assert np.allclose(predicted_pass(r, mg, "line"), r)
    assert np.allclose(predicted_pass(r, mg, "move"), [[0.9, brute_force_pass(0.9, 6)]])
    with pytest.raises(ValueError):
        predicted_pass(r, np.array([[0, 6]]), "move")


def toy_cards(seed=2, n=40, steps=6):
    rng = np.random.default_rng(seed)
    t = np.floor(rng.uniform(1, 10, (n, steps))); t[:, 0] = 0
    g = rng.integers(1, 5, (n, steps))
    valid = np.ones((n, steps), bool)
    mask = np.c_[np.zeros((n, 1), bool), valid[:, 1:]]
    m = rng.integers(3, 15, n)
    acc = rng.uniform(0.5, 1.0, (n, steps))
    return Cards(agent=np.array(["x"] * n), t=t, g=g, valid=valid, y=(g > 1).astype(float),
                 loss_mask=mask, row=np.zeros((n, steps), int), acc=acc, m=m), mask


def numpy_loss(w, c, mask, arm, target=None):
    """Independent numpy version of each arm's loss (reference for the torch objective)."""
    r = M.predict(w, c.t, c.g, c.valid)[mask]
    mg = c.m_grid()[mask]
    bce = lambda p, y: -(y * np.log(p) + (1 - y) * np.log(1 - p))
    if arm == "line":
        return bce(np.clip(r, 1e-6, 1 - 1e-6), c.y[mask]).mean()
    if arm == "pass":
        p = np.array([brute_force_pass(ri, int(mi)) for ri, mi in zip(r, mg)])
        return bce(np.clip(p, 1e-6, 1 - 1e-6), c.y[mask]).mean()
    y = c.acc[mask] if arm == "accuracy" else target[mask]
    return (mg * bce(np.clip(r, 1e-6, 1 - 1e-6), y)).sum() / mg.sum()


@pytest.mark.parametrize("arm", ["line", "pass", "accuracy", "true-recall"])
def test_torch_objective_matches_numpy_and_finite_differences(arm):
    c, mask = toy_cards()
    target = np.clip(M.predict(M.DEFAULT_PARAMETERS, c.t, c.g, c.valid), 0, 1) if arm == "true-recall" else None
    obj = Objective(c, mask, arm, target=target, device=torch.device("cpu"))
    w = M.DEFAULT_PARAMETERS.copy(); w[20] = 0.3
    value, grad = obj(w)
    assert value == pytest.approx(numpy_loss(w, c, mask, arm, target), rel=1e-10)
    for i in (0, 3, 8, 10, 11, 15, 20):
        h = 1e-6 * max(1.0, abs(w[i]))
        up, dn = w.copy(), w.copy(); up[i] += h; dn[i] -= h
        fd = (numpy_loss(up, c, mask, arm, target) - numpy_loss(dn, c, mask, arm, target)) / (2 * h)
        assert grad[i] == pytest.approx(fd, rel=1e-4, abs=1e-8), f"w{i}"


def test_true_recall_loss_is_smallest_at_the_generating_weights():
    c, mask = toy_cards(seed=4)
    w = M.DEFAULT_PARAMETERS
    target = M.predict(w, c.t, c.g, c.valid)
    obj = Objective(c, mask, "true-recall", target=target, device=torch.device("cpu"))
    w2 = w.copy(); w2[20] = 0.4
    assert obj(w)[0] < obj(w2)[0]
