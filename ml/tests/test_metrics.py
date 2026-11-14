"""Truth metrics, days metric and the target/loss options of the trainer."""

import numpy as np
import pytest

from tempo_ml.fsrs import model as M
from tempo_ml.evaluate.days import days_metrics, true_days
from tempo_ml.evaluate.metrics import metrics, rmse_bins
from tempo_ml.fsrs.model import Cards
from tempo_ml.fsrs.train import objective


def test_true_days_one_move_equals_stability():
    for C in (0.2, 0.5, 0.8):
        assert true_days(12.5, 1, C) == pytest.approx(12.5)


def test_true_days_solves_clean_session_chance():
    S, M_, C = 20.0, 6, 0.45
    t = true_days(S, M_, C)
    F = 0.9 ** (-1 / C) - 1
    assert ((1 + F * t / S) ** (-C)) ** M_ == pytest.approx(0.9)


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


def test_mse_objective_is_zero_at_the_generating_weights():
    rng = np.random.default_rng(2)
    n, steps = 40, 6
    t = rng.uniform(1, 10, (n, steps)); t[:, 0] = 0
    g = rng.integers(1, 5, (n, steps))
    valid = np.ones((n, steps), bool)
    mask = np.c_[np.zeros((n, 1), bool), valid[:, 1:]]
    c = Cards(agent=np.array(["x"] * n), t=t, g=g, valid=valid, y=(g > 1).astype(float),
              loss_mask=mask, row=np.zeros((n, steps), int))
    w = M.DEFAULT_PARAMETERS
    target = M.predict(w, t, g, valid)
    assert objective(w, c, mask, target=target, loss="mse") == pytest.approx(0.0)
    w2 = w.copy(); w2[20] = 0.4
    assert objective(w2, c, mask, target=target, loss="mse") > 0
