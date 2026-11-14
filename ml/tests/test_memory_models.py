"""Hidden memory models of the synthetic clients (in memory, no dataset)."""

import pytest

from tempo_ml.simulator import ARCHETYPES, MultiplicativeStability, next_reps, retrievability


@pytest.mark.parametrize("arch", list(ARCHETYPES))
def test_retrievability_is_0_9_at_t_equals_S(arch):
    C = ARCHETYPES[arch].C
    assert retrievability(3.0, 3.0, C) == pytest.approx(0.9)


def test_retrievability_boundaries():
    assert retrievability(0.0, 2.0, 0.5) == 1.0
    assert retrievability(1000.0, 1.0, 0.5) < 0.2
    assert retrievability(1.0, 2.0, 0.5) > retrievability(5.0, 2.0, 0.5)


def test_reps_soft_penalty():
    assert next_reps(5, blundered=False) == 6
    assert next_reps(5, blundered=True) == 3
    assert next_reps(1, blundered=True) == 0


def test_lapse_never_increases_stability():
    m = MultiplicativeStability()
    assert m.after_lapse(10.0, 0.3) == pytest.approx(3.0)
    assert m.after_lapse(2.0, 0.3) == pytest.approx(1.0)
    assert m.after_lapse(0.5, 0.3) == 0.5


# ---- FSRS-6 memory (memory/fsrs.py) ----

import numpy as np  # noqa: E402

from tempo_ml.fsrs.model import DEFAULT_PARAMETERS, LOWER_BOUNDS, UPPER_BOUNDS, predict_states  # noqa: E402
from tempo_ml.simulator.memory.fsrs import FSRSMemory  # noqa: E402


def test_fsrs_memory_sample_keeps_C_and_same_day_weights():
    m = FSRSMemory.sample(0.5, np.random.default_rng(0))
    w = np.array(m.weights)
    assert w[20] == pytest.approx(0.5)
    assert np.allclose(w[17:20], DEFAULT_PARAMETERS[17:20])
    assert (w >= LOWER_BOUNDS - 1e-12).all() and (w <= UPPER_BOUNDS + 1e-12).all()
    assert (np.diff(w[0:4]) >= 0).all()


def test_fsrs_memory_follows_the_fsrs6_model():
    """Without lapses, the hidden stability is exactly FSRS-6's (same weights)."""
    m = FSRSMemory.sample(0.4, np.random.default_rng(3))
    w = np.array(m.weights)
    t = np.array([[0.0, 0.002, 2.5, 6.0, 14.2, 31.0]])
    g = np.array([[3, 4, 3, 2, 3, 4]])
    _, s_after = predict_states(w, t, g, np.ones_like(t, bool))
    s, d = m.start(3)
    out = [s]
    for k in range(1, t.shape[1]):
        r = retrievability(t[0, k], s, 0.4)
        s, d = m.update(s, d, t[0, k], r, int(g[0, k]))
        out.append(s)
    assert np.allclose(out, s_after[0])


def test_fsrs_memory_lapse_floor():
    m = FSRSMemory(weights=tuple(DEFAULT_PARAMETERS))
    s, d = m.update(20.0, 5.0, 30.0, retrievability(30.0, 20.0, 0.15), 1)
    assert 1.0 <= s <= 20.0
    s_low, _ = m.update(0.5, 5.0, 3.0, 0.4, 1)
    assert s_low == 0.5  # the floor never lifts a lower stability
